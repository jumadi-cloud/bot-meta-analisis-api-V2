import os
import time
import threading
import re
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

chat_bp = Blueprint('chat', __name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print('DEBUG: Blueprint dan API key selesai, sebelum route')
DB_PATH = 'chat_history.db'
VERBOSE_LOG = os.environ.get('VERBOSE_LOG', '0') in ['1', 'true', 'True']
GSHEET_CACHE_TTL_ENV = os.environ.get('GSHEET_CACHE_TTL')
try:
    _GSHEET_CACHE_TTL = int(GSHEET_CACHE_TTL_ENV) if GSHEET_CACHE_TTL_ENV else 60 * 60
except Exception:
    pass
# CACHE GOOGLE SHEETS (TTL bisa diatur via env GSHEET_CACHE_TTL)
_gsheet_cache = {}
_gsheet_cache_lock = threading.Lock()

def get_cached_sheet_data(sheet_id, worksheet_name):
    cache_key = f"{sheet_id}:{worksheet_name}"
    now = time.time()
    with _gsheet_cache_lock:
        entry = _gsheet_cache.get(cache_key)
        if entry:
            data, ts = entry
            if now - ts < _GSHEET_CACHE_TTL:
                if VERBOSE_LOG:
                    print(f"[CACHE] HIT for {cache_key} (TTL: {_GSHEET_CACHE_TTL}s)")
                return data
            else:
                if VERBOSE_LOG:
                    print(f"[CACHE] EXPIRED for {cache_key} (TTL: {_GSHEET_CACHE_TTL}s)")
                del _gsheet_cache[cache_key]
        if VERBOSE_LOG:
            print(f"[CACHE] MISS for {cache_key} (TTL: {_GSHEET_CACHE_TTL}s)")
    return None

def set_cached_sheet_data(sheet_id, worksheet_name, data):
    cache_key = f"{sheet_id}:{worksheet_name}"
    with _gsheet_cache_lock:
        _gsheet_cache[cache_key] = (data, time.time())
        if VERBOSE_LOG:
            print(f"[CACHE] SET for {cache_key} (rows: {len(data)}) (TTL: {_GSHEET_CACHE_TTL}s)")

def clear_gsheet_cache():
    with _gsheet_cache_lock:
        _gsheet_cache.clear()
        if VERBOSE_LOG:
            print("[CACHE] CLEARED")
# Endpoint cache control (additive, setelah chat_bp didefinisikan)
@chat_bp.route('/cache/status', methods=['GET'])
def cache_status():
    """Endpoint untuk melihat status cache Google Sheets (additive, tidak mengubah logika lama)."""
    with _gsheet_cache_lock:
        status = []
        now = time.time()
        for key, (data, ts) in _gsheet_cache.items():
            sheet_id, worksheet_name = key.split(':', 1)
            age = now - ts
            status.append({
                "sheet_id": sheet_id,
                "worksheet": worksheet_name,
                "rows": len(data),
                "age_seconds": age,
                "ttl_seconds": _GSHEET_CACHE_TTL,
                "expired": age > _GSHEET_CACHE_TTL
            })
    return jsonify({"success": True, "cache": status, "count": len(status)})

@chat_bp.route('/cache/clear', methods=['POST'])
def cache_clear():
    """Endpoint untuk clear cache Google Sheets (additive, tidak mengubah logika lama)."""
    clear_gsheet_cache()
    return jsonify({"success": True, "message": "Cache Google Sheets cleared."})

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        message TEXT,
        timestamp TEXT
    )''')
    conn.commit()
    conn.close()

def add_history(session_id, role, message):
    timestamp = datetime.utcnow().isoformat()
    conn = get_db()
    c = conn.cursor()
    # Ensure session exists
    c.execute('INSERT OR IGNORE INTO sessions (session_id, created_at) VALUES (?, ?)', (session_id, timestamp))
    c.execute('INSERT INTO history (session_id, role, message, timestamp) VALUES (?, ?, ?, ?)', (session_id, role, message, timestamp))
    conn.commit()
    conn.close()

def get_history_db(session_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT role, message, timestamp FROM history WHERE session_id = ? ORDER BY id ASC', (session_id,))
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return history

# Inisialisasi DB saat import modul (harus di luar blok/fungsi)
init_db()
print('DEBUG: chat_routes.py loaded, sebelum Blueprint dan route')


@chat_bp.route('/chat', methods=['POST'])
def chat():
    # Additive: Inisialisasi agar tidak error UnboundLocalError
    worksheet_row_meta = []
    sheet_data = []
    # Inisialisasi global untuk mencegah error referenced before assignment
    from collections import defaultdict
    adset_costs = defaultdict(float)
    ad_costs = defaultdict(float)
    
    print('DEBUG: chat() function entered')
    try:
        try:
            data = request.get_json()
            print('DEBUG: request.get_json() success, data:', data)
        except Exception as e:
            print(f'[ERROR] request.get_json() failed: {e}')
            return jsonify({
                "success": False,
                "session_id": None,
                "chat_history": [],
                "llm_answer": f"Terjadi error saat membaca request: {e}",
                "worksheet_row_meta": []
            })
        # Support both 'message' and 'query' for backward compatibility
        user_prompt = data.get("message", "").strip()
        print('DEBUG: user_prompt (from message):', user_prompt)
        if not user_prompt:
            user_prompt = data.get("query", "").strip()
            print('DEBUG: user_prompt (from query):', user_prompt)
        if not user_prompt:
            print('[DEBUG] FINAL FALLBACK: user_prompt kosong, tidak memanggil LLM.')
            llm_answer = "Pertanyaan tidak boleh kosong. Silakan masukkan pertanyaan yang ingin Anda analisis."
            session_id = data.get("session_id")
            print('DEBUG: session_id (empty user_prompt):', session_id)
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            print('[DEBUG] RETURN: user_prompt kosong')
            return jsonify({
                "success": True,
                "session_id": session_id,
                "chat_history": chat_history,
                "llm_answer": llm_answer,
                "worksheet_row_meta": []
            })
        session_id = data.get("session_id")
        print('DEBUG: session_id:', session_id)
        print('DEBUG: sebelum add_history')
        add_history(session_id, 'User', user_prompt)
    except Exception as e:
        print(f'[ERROR] Exception global di awal chat(): {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "session_id": None,
            "chat_history": [],
            "llm_answer": f"Terjadi error internal: {e}",
            "worksheet_row_meta": []
        })

    # --- SELALU LOAD DATA WORKSHEET/KOLOM SEBELUM INTENT DETECTION ---
    from routes.sheet_routes import get_gsheet_by_id, get_worksheet
    import os
    sheet_ids = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
    print('DEBUG: sheet_ids loaded:', sheet_ids)
    all_data = []
    worksheet_row_meta = []  # metadata jumlah baris per worksheet per file
    for idx, sheet_id in enumerate(sheet_ids):
        print(f'\n[DEBUG] ===== Mulai iterasi ke-{idx+1} untuk sheet_id: {sheet_id} =====')
        if not sheet_id:
            print(f'[DEBUG] sheet_id kosong pada iterasi ke-{idx+1}, skip')
            print(f'[DEBUG] ===== Selesai iterasi ke-{idx+1} untuk sheet_id: {sheet_id} (KOSONG) =====\n')
            continue
        try:
            print(f'[DEBUG] Memanggil get_gsheet_by_id untuk sheet_id: {sheet_id}')
            sh = get_gsheet_by_id(sheet_id)
            print(f'[DEBUG] Sukses get_gsheet_by_id untuk sheet_id: {sheet_id}')
            worksheet_objs = sh.worksheets()
            worksheet_names = [ws.title for ws in worksheet_objs]
            print(f'[DEBUG] Sheet {sheet_id} worksheets: {worksheet_names}')
            for ws_name in worksheet_names:
                data = get_cached_sheet_data(sheet_id, ws_name)
                if data is None:
                    ws = None
                    try:
                        ws = sh.worksheet(ws_name)
                    except Exception as e_ws:
                        print(f'[DEBUG] Worksheet "{ws_name}" not found in sheet "{sheet_id}", fallback ke worksheet pertama. Error: {e_ws}')
                        worksheets = sh.worksheets()
                        if worksheets:
                            ws = worksheets[0]
                            ws_name = ws.title
                            print(f'[DEBUG] Fallback: Using first worksheet "{ws_name}" from sheet "{sheet_id}"')
                    if ws:
                        data = ws.get_all_records(head=1)
                        for row in data:
                            row['worksheet'] = ws_name
                        set_cached_sheet_data(sheet_id, ws_name, data)
                        print(f'[DEBUG] Loaded worksheet "{ws_name}" from sheet "{sheet_id}" with {len(data)} rows.')
                    else:
                        print(f'[DEBUG] Tidak ada worksheet valid di sheet "{sheet_id}"')
                        data = []
                else:
                    print(f'[DEBUG] Loaded worksheet "{ws_name}" from sheet "{sheet_id}" from cache with {len(data)} rows.')
                worksheet_row_meta.append({
                    'sheet_id': sheet_id,
                    'worksheet': ws_name,
                    'row_count': len(data)
                })
                print(f'[DEBUG] worksheet_row_meta appended: sheet_id={sheet_id}, worksheet={ws_name}, row_count={len(data)}')
                all_data.extend(data)
            print(f'[DEBUG] ===== Selesai iterasi ke-{idx+1} untuk sheet_id: {sheet_id} =====\n')
        except Exception as e:
            print(f'[ERROR] Exception pada iterasi ke-{idx+1} untuk sheet_id {sheet_id}: {e}')
            import traceback
            traceback.print_exc()
            print(f'[DEBUG] ===== Selesai iterasi ke-{idx+1} untuk sheet_id: {sheet_id} (ERROR) =====\n')
            continue
    sheet_data = all_data
    print('[DEBUG] Total sheet_data gabungan:', len(sheet_data))
    print('[DEBUG] Worksheet row meta:', worksheet_row_meta)
    for i, row in enumerate(sheet_data[:3]):
        print(f'  Row {i+1}:', row)
    print('[DEBUG] worksheet_row_meta FINAL:', worksheet_row_meta)

    # --- FAST INTENT DETECTION (regex, tanpa LLM, setelah worksheet/kolom di-load) ---
    print('[DEBUG] MULAI FAST INTENT DETECTION')
    print(f'[DEBUG] user_prompt untuk intent detection: {user_prompt}')
    import re
    question = user_prompt.lower()
    print(f'[DEBUG] question (lowercase): {question}')
    saran_patterns = [
        r'\bcara( terbaik| paling efektif| efektif| ampuh| mudah| cepat)?\b',
        r'\bbagaimana( cara| strategi| tips| solusi)?\b',
        r'\bstrategi\b', r'\btips\b', r'\bsolusi\b', r'\boptimasi\b', r'\befektif\b',
        r'\bmenurunkan\b', r'\bmenaikkan\b', r'\brekomendasi\b', r'\bsaran\b', r'\blangkah\b', r'\bupaya\b',
        r'apa yang harus', r'apa yang bisa', r'apa yang paling', r'bagusnya', r'baiknya', r'perbaikan', r'peningkatan', r'optimalkan', r'optimisasi', r'perlu dilakukan', r'perlu diperbaiki', r'perlu diubah', r'perlu ditingkatkan'
    ]
    performa_patterns = [
        r'\bperforma\b', r'\bperform\b', r'\btrend\b', r'\bnaik\b', r'\bturun\b', r'\bstagnan\b',
        r'\banalisis\b', r'\banalisa\b', r'\bpenyebab\b', r'\balasan\b', r'\bkenapa\b', r'\bmengapa\b',
        r'\bpenilaian\b', r'\bevaluasi\b', r'\bhasil\b', r'\bprogress\b', r'\bperkembangan\b', r'\bperubahan\b', r'\bperbandingan\b', r'\bbanding\b', r'\bkinerja\b', r'\bpenurunan\b', r'\bpeningkatan\b', r'\bpenjelasan\b'
    ]
    bulan_patterns = [
        r'\bdata bulan\b', r'\bdaftar bulan\b', r'\bperiode\b', r'\b(bulan|january|february|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\b',
        r'bulan apa( saja| aja)?', r'bulan yang (ada|tersedia)', r'bulan di data', r'periode apa( saja| aja)?', r'periode (tersedia|di data)', r'\bdata (periode|bulan)\b',
    ]
    trend_months = 0
    trend_match = re.search(r"(\d+) bulan terakhir", question)
    if trend_match:
        trend_months = int(trend_match.group(1))
    saran_match = any(re.search(p, question) for p in saran_patterns)
    performa_match = any(re.search(p, question) for p in performa_patterns)
    bulan_match = any(re.search(p, question) for p in bulan_patterns)
    if trend_months > 0:
        intent = 'tanya_tren'
    elif saran_match:
        intent = 'tanya_saran'
    elif performa_match:
        intent = 'tanya_performa'
    elif bulan_match:
        intent = 'tanya_bulan'
    else:
        intent = 'umum'
    
    print(f"[DEBUG] FAST INTENT RESULT: intent={intent}")
    print(f"[DEBUG] worksheet_row_meta sebelum handler: {worksheet_row_meta}")
    
    # --- JIKA UMUM, CEK APAKAH ADA KATA KUNCI WORKSHEET/SHEET/TAB/JUMLAH BARIS ---
    data_available_intent_kw = [
        "data apa saja", "data yang tersedia", "kolom apa saja", "kolom yang tersedia", "worksheet apa saja", "worksheet yang tersedia", "sheet apa saja", "sheet yang tersedia", "tab apa saja", "tab yang tersedia", "fitur apa saja", "fitur yang tersedia", "field apa saja", "field yang tersedia", "apa saja data", "apa saja kolom", "apa saja worksheet", "apa saja sheet", "apa saja tab", "apa saja fitur", "apa saja field", "data available", "available data", "available column", "available worksheet", "available sheet", "available tab", "available field"
    ]
    worksheet_intent_kw = [
        "jumlah baris", "struktur worksheet", "struktur tab", "struktur data", "jumlah data per worksheet", "jumlah data per tab", "jumlah data per sheet", "jumlah baris per worksheet", "jumlah baris per tab",
        "worksheet", "sheet", "tab", "data per worksheet", "data per sheet", "data per tab", "sheet 2", "worksheet 2", "tab 2", "lembar kerja", "lembar kerja kedua",
        "berapa worksheet", "berapa sheet", "ada berapa worksheet", "ada berapa sheet", "berapa banyak worksheet", "berapa banyak sheet", "daftar worksheet", "daftar sheet", "list worksheet", "list sheet"
    ]
    user_prompt_lc = user_prompt.lower() if user_prompt else ""
    
    print(f'[DEBUG] Checking keyword match for user_prompt_lc: {user_prompt_lc}')
    print(f'[DEBUG] data_available_intent_kw match: {any(kw in user_prompt_lc for kw in data_available_intent_kw)}')
    print(f'[DEBUG] worksheet_intent_kw match: {any(kw in user_prompt_lc for kw in worksheet_intent_kw)}')
    
    # ADDITIVE: Handler untuk analytic intent (performa/saran/tren) - Cek worksheet selection SEBELUM handler lain
    analytic_intents = ['tanya_tren', 'tanya_performa', 'tanya_saran']
    
    print(f'[DEBUG] Checking analytic intent: intent={intent}, analytic_intents={analytic_intents}')
    print(f'[DEBUG] Is analytic intent? {intent in analytic_intents}')
    
    if intent in analytic_intents:
        # ADDITIVE: Enhanced worksheet mention detection dengan multi-keyword matching
        # Step 1: Coba exact match dulu (preserved old behavior)
        mentioned_worksheet = None
        ambiguous_matches = []  # NEW: Track ambiguous matches untuk disambiguation
        
        for meta in worksheet_row_meta:
            ws_name_original = meta.get('worksheet', '')  # ADDITIVE FIX: Keep original case
            ws_name = ws_name_original.lower()
            if ws_name and ws_name in user_prompt_lc:
                mentioned_worksheet = ws_name_original  # ADDITIVE FIX: Use original case
                print(f'[DEBUG] Found mentioned worksheet (EXACT): {mentioned_worksheet}')
                break
        
        # Step 2: Jika tidak ada exact match, coba keyword-based detection (NEW ADDITIVE)
        if not mentioned_worksheet:
            print('[DEBUG] No exact worksheet match, trying keyword-based detection...')
            # ADDITIVE: Better tokenization - remove special chars and filter stopwords
            import re
            user_tokens = re.findall(r'\b\w+\b', user_prompt_lc)
            # Filter stopwords yang umum
            stopwords = {'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'pada', 'dengan', 'adalah', 'ini', 'itu', 'atau', 'dong', 'aja', 'saja'}
            user_keywords = set([t for t in user_tokens if t not in stopwords and len(t) > 1])
            print(f'[DEBUG] User keywords (filtered): {user_keywords}')
            
            worksheet_scores = []  # (worksheet_name, score, matched_keywords)
            for meta in worksheet_row_meta:
                ws_name = meta.get('worksheet', '')
                ws_name_lower = ws_name.lower()
                # ADDITIVE: Better tokenization untuk worksheet name juga
                ws_tokens = re.findall(r'\b\w+\b', ws_name_lower)
                ws_keywords = set([t for t in ws_tokens if len(t) > 1])  # Filter single chars
                
                # Hitung berapa keyword user yang match dengan worksheet
                matched_kw = user_keywords.intersection(ws_keywords)
                if len(matched_kw) >= 1:  # At least 1 keyword match
                    worksheet_scores.append((ws_name, len(matched_kw), list(matched_kw)))
                    print(f'[DEBUG] Keyword match: {ws_name} (score={len(matched_kw)}, keywords={list(matched_kw)})')
            
            if worksheet_scores:
                # Pilih worksheet dengan score tertinggi
                worksheet_scores.sort(key=lambda x: x[1], reverse=True)
                top_score = worksheet_scores[0][1]
                top_matches = [ws for ws in worksheet_scores if ws[1] == top_score]
                
                if len(top_matches) == 1:
                    mentioned_worksheet = top_matches[0][0]
                    print(f'[DEBUG] Found mentioned worksheet (KEYWORD): {mentioned_worksheet} (score={top_score})')
                else:
                    # ADDITIVE: Jangan set mentioned_worksheet, trigger disambiguation
                    ambiguous_matches = [ws[0] for ws in top_matches]
                    print(f'[DEBUG] Ambiguous keyword match: {len(ambiguous_matches)} worksheets with score {top_score}')
                    print(f'[DEBUG] Ambiguous worksheets: {ambiguous_matches}')
                    print(f'[DEBUG] Will trigger disambiguation below')
        
        print(f'[DEBUG] mentioned_worksheet: {mentioned_worksheet}')
        print(f'[DEBUG] ambiguous_matches: {ambiguous_matches}')
        
        # ADDITIVE: Handle ambiguous matches dengan disambiguation (NEW BRANCH)
        if ambiguous_matches and len(ambiguous_matches) > 1:
            print(f'[DEBUG] HANDLER: Ambiguous worksheet detection - triggering disambiguation')
            
            # Build disambiguation message
            lines = ["Saya menemukan beberapa worksheet yang cocok dengan query Anda:\n"]
            sheet_ids_env = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
            sheet_id_to_label = {}
            for idx, sheet_id in enumerate(sheet_ids_env):
                if sheet_id:
                    sheet_id_to_label[sheet_id] = f"File Sheet {idx+1}"
            
            for idx, ws_name in enumerate(ambiguous_matches, 1):
                # Find sheet_id for this worksheet
                sheet_id = None
                row_count = 0
                for meta in worksheet_row_meta:
                    if meta.get('worksheet') == ws_name:
                        sheet_id = meta.get('sheet_id')
                        row_count = meta.get('row_count', 0)
                        break
                
                sheet_label = sheet_id_to_label.get(sheet_id, "Unknown Sheet")
                lines.append(f"{idx}. **{ws_name}** ({sheet_label}, {row_count} baris)")
            
            lines.append("\n**Silakan pilih dengan:**")
            lines.append("- Ketik angka (1, 2, dst), atau")
            lines.append("- Sebutkan nama worksheet lebih spesifik (contoh: 'MSA Age Gender' atau 'Metland Region')")
            
            llm_answer = "\n".join(lines)
            print(f'[DEBUG] Disambiguation message created with {len(ambiguous_matches)} options')
            
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            
            print('[DEBUG] RETURN: Disambiguation needed - asking user to select specific worksheet')
            return jsonify({
                "success": True,
                "session_id": session_id,
                "chat_history": chat_history,
                "llm_answer": llm_answer,
                "worksheet_row_meta": worksheet_row_meta
            })
        
        if not mentioned_worksheet:
            print('[DEBUG] HANDLER: analytic intent WITHOUT worksheet mention - showing worksheet list')
            
            # Tampilkan daftar worksheet dikelompokkan per file sheet
            sheet_ids_env = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
            sheet_id_to_label = {}
            for idx, sheet_id in enumerate(sheet_ids_env):
                if sheet_id:
                    sheet_id_to_label[sheet_id] = f"File Sheet {idx+1}"
            # Fallback jika ada sheet_id lain
            for meta in worksheet_row_meta:
                sheet_id = meta.get('sheet_id')
                if sheet_id not in sheet_id_to_label:
                    sheet_id_to_label[sheet_id] = f"File Sheet ({sheet_id[:6]}...)"
            
            # Kelompokkan worksheet per sheet (hindari duplikasi)
            sheet_to_worksheets = {}
            seen_worksheets = set()
            for meta in worksheet_row_meta:
                sheet_id = meta.get('sheet_id')
                ws = meta.get('worksheet')
                row_count = meta.get('row_count')
                label = sheet_id_to_label.get(sheet_id, f"File Sheet ({sheet_id[:6]}...)")
                
                # Skip jika worksheet sudah pernah ditambahkan untuk sheet_id ini
                ws_key = (sheet_id, ws)
                if ws_key in seen_worksheets:
                    continue
                seen_worksheets.add(ws_key)
                
                if label not in sheet_to_worksheets:
                    sheet_to_worksheets[label] = []
                sheet_to_worksheets[label].append(f"  - '{ws}' ({row_count} baris)")
            
            lines = []
            for label in sorted(sheet_to_worksheets.keys()):
                ws_lines = sheet_to_worksheets[label]
                lines.append(f"\n**{label}** ({len(ws_lines)} worksheet):")
                lines.extend(ws_lines)
            
            llm_answer = (
                "Sebelum saya bisa memberikan insight atau analisis, silakan pilih worksheet yang ingin dianalisis dari daftar berikut:\n"
                + "\n".join(lines)
                + "\n\n**Silakan ketik nama worksheet yang ingin Anda analisis** (copy-paste nama lengkap untuk hasil terbaik)."
            )
            
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            
            print('[DEBUG] RETURN: analytic intent WITHOUT worksheet - prompting user to select')
            return jsonify({
                "success": True,
                "session_id": session_id,
                "chat_history": chat_history,
                "llm_answer": llm_answer,
                "worksheet_row_meta": worksheet_row_meta
            })
        else:
            print(f'[DEBUG] analytic intent WITH worksheet mention: {mentioned_worksheet} - will proceed to analysis')
            
            # ADDITIVE: Enhanced Smart Matching untuk worksheet detection
            # SKIP jika mentioned_worksheet sudah dari keyword detection (ADDITIVE FIX)
            # Enhanced matching ini HANYA untuk OLD FLOW dimana user sebut exact worksheet name di prompt
            # Keyword detection sudah handle fuzzy matching, jadi skip di sini
            print(f'[DEBUG] Skipping enhanced matching - worksheet already detected by keyword matching')
            
            # Filter data berdasarkan mentioned_worksheet (PRESERVED OLD LOGIC)
            matched_worksheets = [mentioned_worksheet]
            print(f'[DEBUG] Matched worksheet: {matched_worksheets[0]}')
            
            original_data_count = len(sheet_data)
            sheet_data = [row for row in sheet_data if row.get('worksheet') == mentioned_worksheet]
            filtered_data_count = len(sheet_data)
            print(f'[DEBUG] Data filtered: {original_data_count} rows -> {filtered_data_count} rows')
            
            worksheet_row_meta = [meta for meta in worksheet_row_meta if meta.get('worksheet') == mentioned_worksheet]
            print(f'[DEBUG] worksheet_row_meta filtered: {worksheet_row_meta}')
            # User sudah menyebut worksheet, data sudah di-filter, lanjut ke analisis (logic di bawah akan handle)
            
            # DEAD CODE: Enhanced matching logic (PRESERVED for reference, replaced by keyword detection above)
            # This code is now unreachable and commented out - keyword detection handles all fuzzy matching
            """
            # Step 2: Match worksheets dengan scoring system
            worksheet_matches = []  # List of (worksheet_name, match_score, match_type)
            
            for meta in worksheet_row_meta:
                ws_name = meta.get('worksheet', '')
                ws_name_lower = ws_name.lower()
                match_score = 0
                match_type = None
                
                # Exact match (highest priority)
                if mentioned_worksheet.lower() == ws_name_lower:
                    match_score = 100
                    match_type = "exact"
                    print(f'[DEBUG] EXACT MATCH found: {ws_name}')
                # Multi-keyword match (high priority)
                elif len(query_keywords) >= 2:
                    keywords_matched = sum(1 for kw in query_keywords if kw in ws_name_lower)
                    if keywords_matched >= 2:
                        match_score = 50 + (keywords_matched * 10)  # 60-90 score range
                        match_type = f"multi-keyword ({keywords_matched}/{len(query_keywords)})"
                        print(f'[DEBUG] MULTI-KEYWORD MATCH: {ws_name} - matched {keywords_matched}/{len(query_keywords)} keywords')
                # Single keyword partial match (lower priority)
                elif mentioned_worksheet.lower() in ws_name_lower:
                    match_score = 30
                    match_type = "partial"
                    print(f'[DEBUG] PARTIAL MATCH: {ws_name}')
                
                if match_score > 0:
                    worksheet_matches.append((ws_name, match_score, match_type))
            
            # Step 3: Sort by match score descending
            worksheet_matches.sort(key=lambda x: x[1], reverse=True)
            print(f'[DEBUG] Total worksheet matches: {len(worksheet_matches)}')
            for ws, score, mtype in worksheet_matches:
                print(f'[DEBUG]   - {ws}: score={score}, type={mtype}')
            
            # Step 4: Disambiguation logic (ADDITIVE - new feature)
            if len(worksheet_matches) == 0:
                # No match - preserved old behavior
                print(f'[WARN] No worksheet matched for mentioned_worksheet: {mentioned_worksheet}, will use all data')
            elif len(worksheet_matches) == 1:
                # Single match - proceed directly (preserved old behavior)
                matched_worksheets = [worksheet_matches[0][0]]
                print(f'[DEBUG] Single worksheet match, proceeding with: {matched_worksheets[0]}')
                
                # Filter data (PRESERVED logic)
                original_data_count = len(sheet_data)
                sheet_data = [row for row in sheet_data if row.get('worksheet') in matched_worksheets]
                filtered_data_count = len(sheet_data)
                print(f'[DEBUG] Data filtered: {original_data_count} rows -> {filtered_data_count} rows')
                
                worksheet_row_meta = [meta for meta in worksheet_row_meta if meta.get('worksheet') in matched_worksheets]
                print(f'[DEBUG] worksheet_row_meta filtered: {worksheet_row_meta}')
            else:
                # Multiple matches - DISAMBIGUATION (NEW ADDITIVE FEATURE)
                print(f'[DEBUG] AMBIGUOUS: {len(worksheet_matches)} worksheets matched - triggering disambiguation')
                
                # Build disambiguation message
                lines = ["Saya menemukan beberapa worksheet yang cocok dengan query Anda:\n"]
                sheet_id_to_label = {}
                sheet_ids_env = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
                for idx, sid in enumerate(sheet_ids_env):
                    if sid:
                        sheet_id_to_label[sid] = f"File Sheet {idx+1}"
                
                for idx, (ws_name, score, mtype) in enumerate(worksheet_matches, 1):
                    # Find sheet_id for this worksheet
                    sheet_id = None
                    row_count = 0
                    for meta in [m for m in worksheet_row_meta if m.get('worksheet') == ws_name]:
                        sheet_id = meta.get('sheet_id')
                        row_count = meta.get('row_count', 0)
                        break
                    
                    sheet_label = sheet_id_to_label.get(sheet_id, "Unknown Sheet")
                    lines.append(f"{idx}. **{ws_name}** ({sheet_label}, {row_count} baris)")
                
                lines.append("\n**Silakan pilih dengan:**")
                lines.append("- Ketik angka (1, 2, dst), atau")
                lines.append("- Sebutkan nama worksheet lebih spesifik (contoh: 'MSA Age Gender' atau 'Metland Region')")
                
                llm_answer = "\n".join(lines)
                print(f'[DEBUG] Disambiguation message created with {len(worksheet_matches)} options')
                
                try:
                    add_history(session_id, "LLM", llm_answer)
                except Exception as e:
                    print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
                
                chat_history = []
                try:
                    chat_history = get_history_db(session_id)
                except Exception as e:
                    print('WARNING: Gagal ambil chat history:', e)
                
                print('[DEBUG] RETURN: Disambiguation needed - asking user to select specific worksheet')
                return jsonify({
                    "success": True,
                    "session_id": session_id,
                    "chat_history": chat_history,
                    "llm_answer": llm_answer,
                    "worksheet_row_meta": worksheet_row_meta
                })
            # User sudah menyebut worksheet, data sudah di-filter, lanjut ke analisis (logic di bawah akan handle)
            """
    
    # Handler worksheet/kolom SELALU prioritas jika ada match kata kunci, return LANGSUNG agar tidak tertimpa handler lain
    if any(kw in user_prompt_lc for kw in data_available_intent_kw):
        # FINAL SAFEGUARD: If worksheet_row_meta is empty, always return a clear message and never call LLM
        if not worksheet_row_meta:
            print('[DEBUG] FINAL FALLBACK: worksheet_row_meta is empty for data available query. Returning static message, not calling LLM.')
            llm_answer = "Tidak ditemukan worksheet atau kolom pada data yang tersedia. Pastikan Google Sheets Anda memiliki worksheet dan data yang valid."
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            print('[DEBUG] RETURN: worksheet_row_meta is empty for data available query')
            return jsonify({
                "success": True,
                    "session_id": session_id,
                    "chat_history": chat_history,
                    "llm_answer": llm_answer,
                    "worksheet_row_meta": worksheet_row_meta
                })
    
    # ADDITIVE: Handler untuk pertanyaan tentang worksheet (berapa worksheet, daftar worksheet, dll)
    # TAPI SKIP jika ini adalah analytic intent dengan worksheet mention
    is_worksheet_listing_query = any(kw in user_prompt_lc for kw in worksheet_intent_kw)
    is_analytic_with_worksheet = (intent in analytic_intents) and mentioned_worksheet
    
    print(f'[DEBUG] is_worksheet_listing_query: {is_worksheet_listing_query}')
    print(f'[DEBUG] is_analytic_with_worksheet: {is_analytic_with_worksheet}')
    
    if is_worksheet_listing_query and not is_analytic_with_worksheet:
        print('[DEBUG] HANDLER: worksheet_intent_kw matched, tampilkan daftar worksheet per file sheet')
        
        # Mapping urutan sheet_id ke label "File Sheet 1", "File Sheet 2", dst
        sheet_ids_env = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
        sheet_id_to_label = {}
        for idx, sheet_id in enumerate(sheet_ids_env):
            if sheet_id:
                sheet_id_to_label[sheet_id] = f"File Sheet {idx+1}"
        
        # Fallback jika ada sheet_id lain
        for meta in worksheet_row_meta:
            sheet_id = meta.get('sheet_id')
            if sheet_id not in sheet_id_to_label:
                sheet_id_to_label[sheet_id] = f"File Sheet ({sheet_id[:6]}...)"
        
        # Kelompokkan worksheet per sheet (hindari duplikasi)
        sheet_to_worksheets = {}
        seen_worksheets = set()
        for meta in worksheet_row_meta:
            sheet_id = meta.get('sheet_id')
            ws = meta.get('worksheet')
            row_count = meta.get('row_count')
            label = sheet_id_to_label.get(sheet_id, f"File Sheet ({sheet_id[:6]}...)")
            
            # Skip jika worksheet sudah pernah ditambahkan untuk sheet_id ini
            ws_key = (sheet_id, ws)
            if ws_key in seen_worksheets:
                continue
            seen_worksheets.add(ws_key)
            
            if label not in sheet_to_worksheets:
                sheet_to_worksheets[label] = []
            sheet_to_worksheets[label].append(f"  - '{ws}' ({row_count} baris)")
        
        # Bangun response
        lines = []
        total_worksheets = 0
        for label in sorted(sheet_to_worksheets.keys()):
            ws_lines = sheet_to_worksheets[label]
            total_worksheets += len(ws_lines)
            lines.append(f"\n**{label}** ({len(ws_lines)} worksheet):")
            lines.extend(ws_lines)
        
        llm_answer = (
            f"Berikut adalah daftar worksheet di setiap file sheet Anda:\n"
            + "\n".join(lines)
            + f"\n\n**Total: {total_worksheets} worksheet** dari {len(sheet_to_worksheets)} file sheet.\n\n"
            + "Anda bisa menanyakan insight, tren, atau analisis berdasarkan worksheet tertentu dengan menyebutkan nama worksheetnya."
        )
        
        try:
            add_history(session_id, "LLM", llm_answer)
        except Exception as e:
            print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
        
        chat_history = []
        try:
            chat_history = get_history_db(session_id)
        except Exception as e:
            print('WARNING: Gagal ambil chat history:', e)
        
        print('[DEBUG] RETURN: worksheet listing handler')
        return jsonify({
            "success": True,
            "session_id": session_id,
            "chat_history": chat_history,
            "llm_answer": llm_answer,
            "worksheet_row_meta": worksheet_row_meta
        })
    
    # Fallback: LLM generik jika tidak ada match worksheet/kolom
    if intent == 'umum' and not any(kw in user_prompt_lc for kw in worksheet_intent_kw):
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.output_parsers import StrOutputParser
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
            output_parser = StrOutputParser()
            try:
                answer = llm.invoke(user_prompt)
                answer = output_parser.invoke(answer)
            except Exception as e:
                answer = f"Maaf, terjadi error saat menjawab pertanyaan: {e}"
            llm_answer = answer
            worksheet_row_meta = []
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            print('[DEBUG] RETURN: intent == "umum" dan bukan worksheet_intent_kw')
            print('[DEBUG] RETURN: analytic intent, user belum pilih worksheet')
            return jsonify({
                "success": True,
                "session_id": session_id,
                "chat_history": chat_history,
                "llm_answer": llm_answer,
                "worksheet_row_meta": worksheet_row_meta
            })
    
    # --- JIKA ANALITIK, LANJUT LOAD DATA DAN WORKFLOW ---
    # CRITICAL: Cek apakah sheet_data sudah di-load dan di-filter sebelumnya (untuk worksheet-specific analysis)
    # Jika sheet_data sudah ada dan sudah di-filter, JANGAN reload lagi agar filter tetap berlaku
    if 'sheet_data' not in locals() or sheet_data is None or len(sheet_data) == 0:
        print('[DEBUG] sheet_data not yet loaded or empty, loading from Google Sheets now...')
        # Multi-sheet support: load data dari dua file sheet (dari .env)
        from routes.sheet_routes import get_gsheet_by_id, get_worksheet
        import os
        sheet_ids = [os.getenv('GOOGLE_SHEET_ID'), os.getenv('GOOGLE_SHEET2_ID')]
        all_data = []
        for sheet_id in sheet_ids:
            if not sheet_id:
                continue
            try:
                sh = get_gsheet_by_id(sheet_id)
                worksheet_objs = sh.worksheets()
                worksheet_names = [ws.title for ws in worksheet_objs]
                print(f'[DEBUG] Sheet {sheet_id} worksheets: {worksheet_names}')
            except Exception as e:
                print(f'[DEBUG] Gagal mengambil daftar worksheet dari sheet "{sheet_id}": {e}')
                continue
            for ws_name in worksheet_names:
                    data = get_cached_sheet_data(sheet_id, ws_name)
                    if data is None:
                        try:
                            ws = None
                            try:
                                ws = sh.worksheet(ws_name)
                            except Exception as e_ws:
                                print(f'[DEBUG] Worksheet "{ws_name}" not found in sheet "{sheet_id}", fallback ke worksheet pertama. Error: {e_ws}')
                                worksheets = sh.worksheets()
                                if worksheets:
                                    ws = worksheets[0]
                                    ws_name = ws.title
                                    print(f'[DEBUG] Fallback: Using first worksheet "{ws_name}" from sheet "{sheet_id}"')
                            if ws:
                                data = ws.get_all_records(head=1)
                                for row in data:
                                    row['worksheet'] = ws_name
                                set_cached_sheet_data(sheet_id, ws_name, data)
                                print(f'[DEBUG] Loaded worksheet "{ws_name}" from sheet "{sheet_id}" with {len(data)} rows.')
                            else:
                                print(f'[DEBUG] Tidak ada worksheet valid di sheet "{sheet_id}"')
                                data = []
                        except Exception as e:
                            print(f'[DEBUG] Worksheet "{ws_name}" not found in sheet "{sheet_id}", skipping. Error: {e}')
                            data = []
                    else:
                        print(f'[DEBUG] Loaded worksheet "{ws_name}" from sheet "{sheet_id}" from cache with {len(data)} rows.')
                    worksheet_row_meta.append({
                        'sheet_id': sheet_id,
                        'worksheet': ws_name,
                        'row_count': len(data)
                    })
                    print(f'[DEBUG] worksheet_row_meta appended: sheet_id={sheet_id}, worksheet={ws_name}, row_count={len(data)}')
                    all_data.extend(data)
        sheet_data = all_data
        print('[DEBUG] Total sheet_data gabungan (fresh load):', len(sheet_data))
    else:
        print(f'[DEBUG] sheet_data ALREADY LOADED and possibly filtered: {len(sheet_data)} rows. Skipping reload to preserve filter.')
        print('[DEBUG] Total sheet_data (using existing filtered data):', len(sheet_data))
        print('[DEBUG] Worksheet row meta:', worksheet_row_meta)
        for i, row in enumerate(sheet_data[:3]):
            print(f'  Row {i+1}:', row)
        print('[DEBUG] worksheet_row_meta FINAL:', worksheet_row_meta)

        # Handler: Deteksi data/kolom/worksheet yang tersedia (SELALU prioritas jika query mengandung kata kunci data/kolom/worksheet)
        if any(kw in user_prompt_lc for kw in data_available_intent_kw):
            # FINAL SAFEGUARD: If worksheet_row_meta is empty, always return a clear message and never call LLM
            if not worksheet_row_meta:
                print('[DEBUG] FINAL FALLBACK: worksheet_row_meta is empty for data available query. Returning static message, not calling LLM.')
                llm_answer = "Tidak ditemukan worksheet atau kolom pada data yang tersedia. Pastikan Google Sheets Anda memiliki worksheet dan data yang valid."
                try:
                    add_history(session_id, "LLM", llm_answer)
                except Exception as e:
                    print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
                chat_history = []
                try:
                    chat_history = get_history_db(session_id)
                except Exception as e:
                    print('WARNING: Gagal ambil chat history:', e)
                return jsonify({
                    "success": True,
                    "session_id": session_id,
                    "chat_history": chat_history,
                    "llm_answer": llm_answer,
                    "worksheet_row_meta": worksheet_row_meta
                })
            worksheet_columns = {}
            for meta in worksheet_row_meta:
                sheet_id = meta.get('sheet_id')
                ws_name = meta.get('worksheet')
                key = (sheet_id, ws_name)
                ws_rows = [row for row in sheet_data if row.get('worksheet') == ws_name and row.get('sheet_id', sheet_id) == sheet_id]
                if ws_rows:
                    columns = list(ws_rows[0].keys())
                    worksheet_columns[key] = columns
                else:
                    worksheet_columns[key] = []
                print(f'[DEBUG] worksheet_columns[{key}]: {worksheet_columns[key]}')
            print('[DEBUG] worksheet_columns FINAL:', worksheet_columns)
            if worksheet_columns:
                lines = []
                for (sheet_id, ws), cols in worksheet_columns.items():
                    sheet_label = f"Sheet ID: {sheet_id}"
                    if cols:
                        lines.append(f"- {sheet_label} | Worksheet '{ws}': kolom yang tersedia: {', '.join(cols)}")
                    else:
                        lines.append(f"- {sheet_label} | Worksheet '{ws}': tidak ada data/kolom terdeteksi.")
                llm_answer = (
                    "Berikut daftar worksheet dan kolom yang tersedia di semua file Google Sheets Anda:\n" + "\n".join(lines) +
                    "\nAnda bisa menanyakan insight, tren, atau breakdown berdasarkan kolom-kolom di atas."
                )
            else:
                print('[DEBUG] Fallback: Tidak ditemukan worksheet atau kolom pada data yang tersedia. Tidak memanggil LLM.')
                llm_answer = "Tidak ditemukan worksheet atau kolom pada data yang tersedia. Pastikan Google Sheets Anda memiliki worksheet dan data yang valid."
            try:
                add_history(session_id, "LLM", llm_answer)
            except Exception as e:
                print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
            chat_history = []
            try:
                chat_history = get_history_db(session_id)
            except Exception as e:
                print('WARNING: Gagal ambil chat history:', e)
            print('[DEBUG] RETURN: intent == "umum" dan bukan worksheet_intent_kw')
            return jsonify({
                "success": True,
                "session_id": session_id,
                "chat_history": chat_history,
                "llm_answer": llm_answer,
                "worksheet_row_meta": worksheet_row_meta
            })
    # END of if/else block for sheet_data loading
    # Workflow execution runs REGARDLESS of reload or already loaded (ADDITIVE FIX - moved outside else block)
    
    from workflows.aggregation_workflow import run_aggregation_workflow
    workflow_result = run_aggregation_workflow(sheet_data, question=user_prompt)
    llm_answer = workflow_result.get("llm_answer")

    worksheet_intent_kw = [
        "jumlah baris", "struktur worksheet", "struktur tab", "struktur data", "jumlah data per worksheet", "jumlah data per tab", "jumlah data per sheet", "jumlah baris per worksheet", "jumlah baris per tab",
        "worksheet", "sheet", "tab", "data per worksheet", "data per sheet", "data per tab", "sheet 2", "worksheet 2", "tab 2", "lembar kerja", "lembar kerja kedua"
    ]
    metric_breakdown_kw = [
        "cost per worksheet", "cost per tab", "cost per sheet", "total cost per worksheet", "total cost per tab", "total cost per sheet", "biaya per worksheet", "biaya per tab", "biaya per sheet", "total cost dari worksheet", "total cost dari tab", "total cost dari sheet",
        "clicks per worksheet", "klik per worksheet", "leads per worksheet", "ctr per worksheet", "impressions per worksheet", "reach per worksheet", "cpwa per worksheet", "avg per worksheet", "rata-rata per worksheet", "min per worksheet", "max per worksheet"
    ]
    user_prompt_lc = user_prompt.lower()
    # Handler: dynamic metric breakdown per worksheet (DIPRIORITASKAN)
    if any(kw in user_prompt_lc for kw in metric_breakdown_kw):
        from services.aggregation import aggregate_metrics_by_worksheet, aggregate_main_metrics, aggregate_breakdown, aggregate_age_gender
        breakdown = aggregate_metrics_by_worksheet(sheet_data)
        lines = []
        total_cost = 0
        total_clicks = 0
        total_leads_wa = 0
        total_ctr_sum = 0
        total_ctr_count = 0
        for (sheet_id, worksheet), met in breakdown.items():
            # Cost
            cost = int(met.get('total_cost', 0))
            clicks = int(met.get('total_clicks', 0))
            leads_wa = int(met.get('total_leads_wa', 0))
            impressions = int(met.get('total_impressions', 0))
            ctr = (clicks / impressions * 100) if impressions else 0
            lines.append(f"Worksheet: {worksheet} | Cost: Rp {cost:,} | Clicks: {clicks:,} | WA Leads: {leads_wa:,} | CTR: {ctr:.2f}%")
            total_cost += cost
            total_clicks += clicks
            total_leads_wa += leads_wa
            if impressions:
                total_ctr_sum += ctr
                total_ctr_count += 1
        avg_ctr = (total_ctr_sum / total_ctr_count) if total_ctr_count else 0
        llm_answer = (
            "Breakdown metrik utama per worksheet:\n" + "\n".join(lines) +
            f"\nTotal gabungan semua worksheet: Cost Rp {total_cost:,}, Clicks {total_clicks:,}, WA Leads {total_leads_wa:,}, Avg CTR {avg_ctr:.2f}%"
        )
    # Handler: meta worksheet (jumlah baris)
    elif any(kw in user_prompt_lc for kw in worksheet_intent_kw):
        meta = []
        sheet2_id = os.getenv('GOOGLE_SHEET2_ID')
        if "sheet 2" in user_prompt_lc or "worksheet 2" in user_prompt_lc or "tab 2" in user_prompt_lc or "lembar kerja kedua" in user_prompt_lc:
            for meta_row in worksheet_row_meta:
                if meta_row.get('sheet_id') == sheet2_id:
                    meta.append(f"Worksheet: {meta_row['worksheet']} (Sheet 2), Jumlah Baris: {meta_row['row_count']}")
            if meta:
                llm_answer = "Berikut jumlah baris pada setiap worksheet di file Sheet 2 (dinamis):\n" + "\n".join(meta)
            else:
                llm_answer = "Tidak ditemukan worksheet pada file Sheet 2. Pastikan Sheet 2 memiliki worksheet yang valid."
        else:
            for meta_row in worksheet_row_meta:
                meta.append(f"Worksheet: {meta_row['worksheet']}, Jumlah Baris: {meta_row['row_count']}")
            if meta:
                llm_answer = "Berikut jumlah baris pada setiap worksheet di semua file (dinamis):\n" + "\n".join(meta)
            else:
                llm_answer = "Tidak ditemukan worksheet pada file manapun."
    try:
        add_history(session_id, "LLM", llm_answer)
    except Exception as e:
        print('WARNING: Gagal simpan chat LLM ke chat_history.db:', e)
    chat_history = []
    try:
        chat_history = get_history_db(session_id)
    except Exception as e:
        print('WARNING: Gagal ambil chat history:', e)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "chat_history": chat_history,
        "llm_answer": llm_answer,
        "worksheet_row_meta": worksheet_row_meta
    })
    # End of chat()
# Inisialisasi DB saat import modul
init_db()
