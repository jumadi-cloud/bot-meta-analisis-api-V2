
# Node definitions for workflow (moved after AggregationState)
"""
workflows/aggregation_workflow.py
Contoh workflow LangGraph untuk agregasi data campaign.
"""
from langgraph.graph import StateGraph, END
from pydantic import BaseModel


from services.aggregation import (
    aggregate_main_metrics,
    aggregate_daily_weekly_cost,
    aggregate_breakdown,
    aggregate_age_gender,
    aggregate_age_gender_monthly,
    aggregate_region,  # ADDITIVE: Region breakdown
    # ADDITIVE: Enhanced aggregation functions
    aggregate_breakdown_enhanced,
    aggregate_age_gender_enhanced,
    aggregate_by_period_enhanced,
    aggregate_outbound_clicks
)

# Move AggregationState class definition to the top so all functions can reference it
from pydantic import BaseModel
class AggregationState(BaseModel):
    sheet_data: list
    question: str = None  # Tambah field question agar selalu ada di state
    main_metrics: dict = None
    daily_weekly: tuple = None
    breakdown_adset: dict = None
    breakdown_ad: dict = None
    age_gender: dict = None
    region_breakdown: dict = None  # ADDITIVE: Region breakdown
    llm_answer: str = None
    intent: str = None  # New: detected intent
    bulan_list: list = None  # New: extracted unique months if relevant
    trend_months: int = 0  # Jumlah bulan untuk analisis tren (jika ada)
    monthly_stats: dict = None  # Hasil agregasi bulanan
    # ADDITIVE: Enhanced aggregation results
    breakdown_adset_enhanced: dict = None  # Enhanced adset breakdown
    breakdown_ad_enhanced: dict = None     # Enhanced ad breakdown
    age_gender_enhanced: dict = None       # Enhanced age & gender
    period_stats_daily: dict = None        # Daily stats with full metrics
    period_stats_weekly: dict = None       # Weekly stats with full metrics
    period_stats_monthly: dict = None      # Monthly stats with full metrics
    outbound_clicks: dict = None           # Outbound clicks breakdown
    sorted_months: list = None  # Urutan bulan hasil agregasi
    adsets_by_sheet: dict = None  # New: hasil ekstraksi ad set per sheet


# Node: Tren/agregasi bulanan segmented age|gender (additive)
def node_aggregate_age_gender_monthly(state: AggregationState):
    question = getattr(state, 'question', '').lower()
    if state.intent != 'tanya_tren':
        return state
    import re
    age_match = re.search(r'(\d{2}-\d{2}|\d{2}\+)', question)
    gender_match = re.search(r'(wanita|perempuan|female|pria|laki|male)', question)
    if not (age_match and gender_match):
        return state
    age = age_match.group(1)
    gender = gender_match.group(1)
    gender_norm = 'female' if gender in ['wanita','perempuan','female'] else 'male' if gender in ['pria','laki','male'] else gender
    key = f"{age}|{gender_norm}"
    monthly_stats = aggregate_age_gender_monthly(state.sheet_data)
    filtered = {k: v for k, v in monthly_stats.items() if k[0].lower() == key.lower()}
    sorted_months = sorted([k[1] for k in filtered.keys()])
    print(f"[DEBUG] AGG_SEG key={key}")
    print(f"[DEBUG] AGG_SEG filtered.keys(): {list(filtered.keys())}")
    print(f"[DEBUG] AGG_SEG sorted_months: {sorted_months}")
    print(f"[DEBUG] AGG_SEG filtered: {filtered}")
    return state.copy(update={"monthly_stats": filtered, "sorted_months": sorted_months})
from services.llm_summary import llm_summarize_aggregation
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
# Node: Jawab pertanyaan umum/non-analitik langsung ke LLM (tidak dipakai lagi, intent di route)
graph = StateGraph(AggregationState)
def node_main_metrics(state: AggregationState):
    return state.copy(update={"main_metrics": aggregate_main_metrics(state.sheet_data), "question": state.question})

def node_daily_weekly(state: AggregationState):
    return state.copy(update={"daily_weekly": aggregate_daily_weekly_cost(state.sheet_data), "question": state.question})

def node_breakdown_adset(state: AggregationState):
    return state.copy(update={"breakdown_adset": aggregate_breakdown(state.sheet_data, by="Ad set"), "question": state.question})

def node_breakdown_ad(state: AggregationState):
    # ADDITIVE: Skip old ad breakdown for large datasets (performance optimization)
    # Enhanced version is more useful and will also be skipped
    if len(state.sheet_data) > 5000:
        print(f"[DEBUG] node_breakdown_ad: SKIPPED - dataset too large ({len(state.sheet_data)} rows)")
        return state.copy(update={"breakdown_ad": {}, "question": state.question})
    return state.copy(update={"breakdown_ad": aggregate_breakdown(state.sheet_data, by="Ad"), "question": state.question})

def node_age_gender(state: AggregationState):
    return state.copy(update={"age_gender": aggregate_age_gender(state.sheet_data), "question": state.question})

# ADDITIVE: Node untuk region breakdown
def node_region(state: AggregationState):
    print("[DEBUG] node_region: executing aggregate_region")
    region_data = aggregate_region(state.sheet_data)
    print(f"[DEBUG] node_region: aggregated {len(region_data)} regions")
    return state.copy(update={"region_breakdown": region_data, "question": state.question})

# ADDITIVE: Enhanced aggregation nodes
def node_breakdown_adset_enhanced(state: AggregationState):
    """Enhanced adset breakdown dengan metrik lengkap (CPM, CPC, CPLC, Frequency, dll)"""
    print("[DEBUG] node_breakdown_adset_enhanced: executing")
    data = aggregate_breakdown_enhanced(state.sheet_data, by="Ad set")
    print(f"[DEBUG] node_breakdown_adset_enhanced: aggregated {len(data)} adsets")
    return state.copy(update={"breakdown_adset_enhanced": data, "question": state.question})

def node_breakdown_ad_enhanced(state: AggregationState):
    """Enhanced ad breakdown dengan metrik lengkap"""
    print("[DEBUG] node_breakdown_ad_enhanced: executing")
    # ADDITIVE: Skip ad-level aggregation for large datasets (performance optimization)
    # Ad-level creates 100+ unique keys for large datasets, causing timeout
    # Adset-level aggregation is usually sufficient and much faster
    if len(state.sheet_data) > 5000:
        print(f"[DEBUG] node_breakdown_ad_enhanced: SKIPPED - dataset too large ({len(state.sheet_data)} rows), ad-level aggregation disabled for performance")
        return state.copy(update={"breakdown_ad_enhanced": {}, "question": state.question})
    
    data = aggregate_breakdown_enhanced(state.sheet_data, by="Ad")
    print(f"[DEBUG] node_breakdown_ad_enhanced: aggregated {len(data)} ads")
    return state.copy(update={"breakdown_ad_enhanced": data, "question": state.question})

def node_age_gender_enhanced(state: AggregationState):
    """Enhanced age & gender breakdown dengan metrik lengkap"""
    print("[DEBUG] node_age_gender_enhanced: executing")
    data = aggregate_age_gender_enhanced(state.sheet_data)
    print(f"[DEBUG] node_age_gender_enhanced: aggregated {len(data)} age|gender segments")
    return state.copy(update={"age_gender_enhanced": data, "question": state.question})

def node_period_daily(state: AggregationState):
    """Daily aggregation dengan metrik lengkap"""
    print("[DEBUG] node_period_daily: executing")
    # ADDITIVE: Skip daily aggregation if dataset too large (performance optimization for production)
    # Daily creates too many unique keys for large datasets, causing timeout/OOM
    # Preserved for small datasets or specific use cases
    if len(state.sheet_data) > 5000:
        print(f"[DEBUG] node_period_daily: SKIPPED - dataset too large ({len(state.sheet_data)} rows), daily aggregation disabled for performance")
        return state.copy(update={"period_stats_daily": {}, "question": state.question})
    
    data = aggregate_by_period_enhanced(state.sheet_data, period='daily')
    print(f"[DEBUG] node_period_daily: aggregated {len(data)} days")
    return state.copy(update={"period_stats_daily": data, "question": state.question})

def node_period_weekly(state: AggregationState):
    """Weekly aggregation dengan metrik lengkap"""
    print("[DEBUG] node_period_weekly: executing")
    data = aggregate_by_period_enhanced(state.sheet_data, period='weekly')
    print(f"[DEBUG] node_period_weekly: aggregated {len(data)} weeks")
    return state.copy(update={"period_stats_weekly": data, "question": state.question})

def node_period_monthly(state: AggregationState):
    """Monthly aggregation dengan metrik lengkap"""
    print("[DEBUG] node_period_monthly: executing")
    data = aggregate_by_period_enhanced(state.sheet_data, period='monthly')
    print(f"[DEBUG] node_period_monthly: aggregated {len(data)} months")
    return state.copy(update={"period_stats_monthly": data, "question": state.question})

def node_outbound_clicks(state: AggregationState):
    """Outbound clicks proportion analysis"""
    print("[DEBUG] node_outbound_clicks: executing")
    data = aggregate_outbound_clicks(state.sheet_data)
    print(f"[DEBUG] node_outbound_clicks: total={data.get('total', 0)}")
    return state.copy(update={"outbound_clicks": data, "question": state.question})

# Node: Ekstrak ad set per sheet (work1/work2)
def node_extract_adsets(state: AggregationState):
    # Asumsi: sheet_data digabung dari dua worksheet, urutan: work1 lalu work2
    adsets_by_sheet = {"work1": set(), "work2": set()}
    # Deteksi batas pemisah work1/work2 dengan menandai perubahan worksheet jika ada kolom 'worksheet' atau dengan membagi dua jika tidak ada
    # Lebih robust: jika sheet_data panjang > 0 dan len dibagi 2, asumsikan separuh pertama work1, separuh kedua work2
    n = len(state.sheet_data)
    if n == 0:
        return state.copy(update={"adsets_by_sheet": adsets_by_sheet})
    # Cek apakah ada kolom 'worksheet' di data
    worksheet_col = None
    for k in state.sheet_data[0].keys():
        if k.lower() == 'worksheet':
            worksheet_col = k
            break
    if worksheet_col:
        for row in state.sheet_data:
            ws = str(row.get(worksheet_col, '')).lower()
            adset = row.get('Ad set') or row.get('Ad Set') or row.get('Adset')
            if adset:
                if 'work1' in ws:
                    adsets_by_sheet['work1'].add(str(adset))
                elif 'work2' in ws:
                    adsets_by_sheet['work2'].add(str(adset))
    else:
        # Asumsi urutan: work1 dulu, lalu work2
        mid = n // 2
        for i, row in enumerate(state.sheet_data):
            adset = row.get('Ad set') or row.get('Ad Set') or row.get('Adset')
            if adset:
                if i < mid:
                    adsets_by_sheet['work1'].add(str(adset))
                else:
                    adsets_by_sheet['work2'].add(str(adset))
    # Konversi ke list dan log
    adsets_by_sheet = {k: sorted(list(v)) for k, v in adsets_by_sheet.items()}
    print(f"[DEBUG] adsets_by_sheet: {adsets_by_sheet}")
    return state.copy(update={"adsets_by_sheet": adsets_by_sheet})

import re
def node_detect_intent(state: AggregationState):
    question = getattr(state, 'question', '')
    if question is None:
        question = ''
    question = question.lower()
    # Regex for strategy/advice/insight intent (highest priority)
    saran_patterns = [
        r'\bcara( terbaik| paling efektif| efektif| ampuh| mudah| cepat)?\b',
        r'\bbagaimana( cara| strategi| tips| solusi)?\b',
        r'\bstrategi\b', r'\btips\b', r'\bsolusi\b', r'\boptimasi\b', r'\befektif\b',
        r'\bmenurunkan\b', r'\bmenaikkan\b', r'\brekomendasi\b', r'\bsaran\b', r'\blangkah\b', r'\bupaya\b',
        r'apa yang harus', r'apa yang bisa', r'apa yang paling', r'bagusnya', r'baiknya', r'perbaikan', r'peningkatan', r'optimalkan', r'optimisasi', r'perlu dilakukan', r'perlu diperbaiki', r'perlu diubah', r'perlu ditingkatkan'
    ]
    saran_match = any(re.search(p, question) for p in saran_patterns)
    # Regex for performa intent (performance analysis)
    performa_patterns = [
        r'\bperforma\b', r'\bperform\b', r'\btrend\b', r'\bnaik\b', r'\bturun\b', r'\bstagnan\b',
        r'\banalisis\b', r'\banalisa\b', r'\bpenyebab\b', r'\balasan\b', r'\bkenapa\b', r'\bmengapa\b',
        r'\bpenilaian\b', r'\bevaluasi\b', r'\bhasil\b', r'\bprogress\b', r'\bperkembangan\b', r'\bperubahan\b', r'\bperbandingan\b', r'\bbanding\b', r'\bkinerja\b', r'\bpenurunan\b', r'\bpeningkatan\b', r'\bpenjelasan\b'
    ]
    performa_match = any(re.search(p, question) for p in performa_patterns)
    # Regex for bulan intent (month listing)
    bulan_patterns = [
        r'\bdata bulan\b',
        r'\bdaftar bulan\b',
        r'\bperiode\b',
        r'\b(bulan|january|february|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\b',
        r'bulan apa( saja| aja)?',
        r'bulan yang (ada|tersedia)',
        r'bulan di data',
        r'periode apa( saja| aja)?',
        r'periode (tersedia|di data)',
        r'\bdata (periode|bulan)\b',
    ]
    bulan_match = any(re.search(p, question) for p in bulan_patterns)
    # Deteksi intent tren multi-bulan (misal: "3 bulan terakhir", "4 bulan terakhir")
    trend_months = 0
    trend_match = re.search(r"(\d+) bulan terakhir", question)
    if trend_match:
        trend_months = int(trend_match.group(1))
    # Prioritization: tren > saran > performa > bulan > umum
    # Jika ada pola tren multi-bulan, harus tanya_tren
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
    print(f"[DEBUG] Detected intent: {intent} | question: {question} | trend_months: {trend_months}")
    return state.copy(update={"intent": intent, "question": state.question, "trend_months": trend_months})

graph = StateGraph(AggregationState)
graph = StateGraph(AggregationState)
graph.add_node("detect_intent", node_detect_intent)
# Node: Tren/agregasi bulanan (khusus intent tanya_tren)

# New: Always aggregate monthly regardless of intent
def node_aggregate_monthly(state: AggregationState):
    debug_monthly = {}
    debug_failed_rows = []
    # Robust parsing: coba beberapa nama kolom dan format tanggal
    import re
    from collections import defaultdict
    import calendar
    from datetime import datetime

    monthly_stats = defaultdict(lambda: {'cost': 0, 'leads': 0, 'clicks': 0})
    # Deteksi kolom tanggal/bulan secara lebih robust, prioritaskan 'Date' (case-insensitive)
    date_keys = set()
    if state.sheet_data:
        # Prioritas: kolom persis 'Date' (case-insensitive)
        for k in state.sheet_data[0].keys():
            if k.strip().lower() == 'date':
                date_keys = {k}
                break
        if not date_keys:
            for k in state.sheet_data[0].keys():
                kl = str(k).lower()
                if any(x in kl for x in ["tanggal", "date", "tgl", "day", "dt", "bulan", "month"]):
                    date_keys.add(k)
    if not date_keys and state.sheet_data:
        # Fallback: cari kolom yang isinya mirip tanggal
        for k in state.sheet_data[0].keys():
            sample_val = str(state.sheet_data[0][k])
            if re.match(r"\d{4}-\d{2}-\d{2}", sample_val) or re.match(r"\d{2}/\d{2}/\d{4}", sample_val):
                date_keys.add(k)


    def clean_number(val):
        if val is None:
            return 0
        s = str(val)
        # Hilangkan simbol mata uang, spasi, titik, koma
        s = s.replace('Rp', '').replace('rp', '').replace('IDR', '').replace('idr', '')
        s = s.replace(',', '').replace('.', '').replace(' ', '')
        # Jika ada koma desimal (misal 1.234,56), ganti jadi titik
        s = s.replace(',', '.')
        try:
            return float(s)
        except Exception:
            try:
                return int(float(s))
            except Exception:
                return 0

    for idx, row in enumerate(state.sheet_data):
        tgl = None
        # Prioritaskan kolom yang nampak seperti tanggal
        for k in date_keys or row.keys():
            v = row.get(k)
            if not v:
                continue
            val = str(v).strip()
            try:
                # Format: YYYY-MM-DD
                if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                    tgl = datetime.strptime(val, "%Y-%m-%d")
                    break
                # Format: DD/MM/YYYY
                if re.match(r"^\d{2}/\d{2}/\d{4}$", val):
                    tgl = datetime.strptime(val, "%d/%m/%Y")
                    break
                # Format: YYYY-MM (bulan saja)
                if re.match(r"^\d{4}-\d{2}$", val):
                    tgl = datetime.strptime(val + "-01", "%Y-%m-%d")
                    break
                # Format: YYYY-MM or YYYY/MM
                m = re.match(r"^(\d{4})[-/](\d{1,2})$", val)
                if m:
                    y = int(m.group(1)); mo = int(m.group(2))
                    tgl = datetime(y, mo, 1)
                    break
                # Try to parse month names like 'May' or 'Mei' optionally with year
                m = re.match(r"^(?:(\d{4})\s*)?([A-Za-z]+)$", val)
                if m:
                    year = int(m.group(1)) if m.group(1) else None
                    mon_name = m.group(2)
                    try:
                        mo = list(calendar.month_name).index(mon_name.capitalize())
                        if mo:
                            tgl = datetime(year or datetime.now().year, mo, 1)
                            break
                    except Exception:
                        pass
            except Exception as parse_err:
                print(f"[DEBUG] Failed to parse date from row {idx}, key {k}, val {val}: {parse_err}")
                continue

        if tgl:
            try:
                key = (tgl.year, tgl.month)
                monthly_stats[key]['cost'] += clean_number(row.get('Cost', 0))
                # Coba beberapa kemungkinan kolom leads dengan safe get
                leads_val = 0
                for lead_col in ['WhatsApp', 'On-Facebook Leads', 'Lead Form', 'Messaging Conversations Started']:
                    if row.get(lead_col):
                        leads_val += clean_number(row.get(lead_col, 0))
                monthly_stats[key]['leads'] += int(leads_val)
                
                # Clicks dengan safe fallback
                clicks_val = 0
                for click_col in ['All Clicks', 'Clicks all', 'Link Clicks', 'link clicks']:
                    if row.get(click_col):
                        clicks_val += clean_number(row.get(click_col, 0))
                monthly_stats[key]['clicks'] += int(clicks_val)
                
                # Debug: hitung entry per bulan
                debug_monthly.setdefault(key, 0)
                debug_monthly[key] += 1
            except Exception as agg_err:
                print(f"[DEBUG] Failed to aggregate row {idx}: {agg_err}")
                debug_failed_rows.append((idx, row))
        else:
            debug_failed_rows.append((idx, row))

    sorted_months = sorted(monthly_stats.keys())
    print(f"[DEBUG] Hasil parsing bulan: {sorted_months}")
    print(f"[DEBUG] Jumlah entry per bulan: {debug_monthly}")
    print(f"[DEBUG] monthly_stats: {monthly_stats}")
    if debug_failed_rows:
        print(f"[DEBUG] Baris gagal parsing tanggal: {len(debug_failed_rows)} contoh: {debug_failed_rows[:3]}")
    return state.copy(update={"monthly_stats": dict(monthly_stats), "sorted_months": sorted_months})

# Node: Tren bulanan hanya untuk analisis tren, tidak agregasi
def node_tren_bulanan(state: AggregationState):
    # This node is now a passthrough, but can be extended for advanced trend logic
    return state

# Node: Extract unique months if intent is tanya_bulan
def node_extract_bulan(state: AggregationState):
    if state.intent != 'tanya_bulan':
        return state.copy(update={"question": state.question})
    bulan_set = set()
    for row in state.sheet_data:
        for k, v in row.items():
            k_lower = k.lower()
            if k_lower in ["bulan", "month"] and v:
                bulan_set.add(str(v).strip())
            elif k_lower in ["tanggal", "date", "tgl"] and v:
                import re
                import calendar
                val = str(v)
                # Format: YYYY-MM-DD
                m = re.match(r"(\d{4})-(\d{2})-(\d{2})", val)
                if m:
                    bulan_num = int(m.group(2))
                    bulan_set.add(calendar.month_name[bulan_num])
                # Format: DD/MM/YYYY
                m = re.match(r"(\d{2})/(\d{2})/(\d{4})", val)
                if m:
                    bulan_num = int(m.group(2))
                    bulan_set.add(calendar.month_name[bulan_num])
    bulan_list = sorted(list(bulan_set))
    print(f"[DEBUG] node_extract_bulan hasil bulan_list: {bulan_list}")
    return state.copy(update={"bulan_list": bulan_list, "question": state.question})

graph = StateGraph(AggregationState)

# Node registration (all after graph is defined)
graph.add_node("detect_intent", node_detect_intent)
graph.add_node("extract_bulan", node_extract_bulan)
graph.add_node("aggregate_monthly", node_aggregate_monthly)
graph.add_node("aggregate_age_gender_monthly", node_aggregate_age_gender_monthly)
graph.add_node("extract_adsets", node_extract_adsets)  # New node
graph.add_node("main_metrics", node_main_metrics)
graph.add_node("daily_weekly", node_daily_weekly)
graph.add_node("breakdown_adset", node_breakdown_adset)
graph.add_node("breakdown_ad", node_breakdown_ad)
graph.add_node("age_gender", node_age_gender)
graph.add_node("region", node_region)  # ADDITIVE: Region node
# ADDITIVE: Enhanced aggregation nodes
graph.add_node("breakdown_adset_enhanced", node_breakdown_adset_enhanced)
graph.add_node("breakdown_ad_enhanced", node_breakdown_ad_enhanced)
graph.add_node("age_gender_enhanced", node_age_gender_enhanced)
graph.add_node("period_daily", node_period_daily)
graph.add_node("period_weekly", node_period_weekly)
graph.add_node("period_monthly", node_period_monthly)
graph.add_node("outbound_clicks", node_outbound_clicks)
graph.add_node("tren_bulanan", node_tren_bulanan)

# Node LLM summary (will be updated in next step to use retrieved_docs)
def node_llm_summary(state: AggregationState):
    import calendar
    # Jika pertanyaan meminta daftar ad set, jawab eksplisit
    question = getattr(state, 'question', '').lower()
    adsets_by_sheet = getattr(state, 'adsets_by_sheet', None)
    if any(x in question for x in ["ad set apa", "adset apa", "daftar ad set", "ad set yang ada", "adset yang ada"]):
        if adsets_by_sheet:
            work1 = adsets_by_sheet.get('work1', [])
            work2 = adsets_by_sheet.get('work2', [])
            msg = []
            if work1:
                msg.append(f"Ad set di sheet 1 (work1): {', '.join(work1)}")
            else:
                msg.append("Tidak ada ad set terdeteksi di sheet 1 (work1).")
            if work2:
                msg.append(f"Ad set di sheet 2 (work2): {', '.join(work2)}")
            else:
                msg.append("Tidak ada ad set terdeteksi di sheet 2 (work2).")
            llm_answer = "\n".join(msg)
            print(f"[DEBUG] Jawaban ad set per sheet: {llm_answer}")
            return state.copy(update={"llm_answer": llm_answer})
        else:
            llm_answer = "Tidak ada data ad set yang bisa diekstrak dari kedua sheet."
            print(f"[DEBUG] Jawaban ad set per sheet: {llm_answer}")
            return state.copy(update={"llm_answer": llm_answer})
    # Always show monthly trend summary if possible
    if getattr(state, 'intent', None) == 'tanya_tren' and getattr(state, 'monthly_stats', None) and getattr(state, 'sorted_months', None):
        monthly_stats = state.monthly_stats
        sorted_months = state.sorted_months
        print(f"[DEBUG] LLM_SUMMARY monthly_stats: {monthly_stats}")
        print(f"[DEBUG] LLM_SUMMARY sorted_months: {sorted_months}")
        n = getattr(state, 'trend_months', 0)
        # --- Tambahan: summary tren segmented age|gender ---
        if len(monthly_stats) > 0 and len(sorted_months) >= 2:
            n = min(n if n > 0 else 3, len(sorted_months))
            months_to_show = sorted_months[-n:]
            ctrs = [monthly_stats[(list(monthly_stats.keys())[0][0], m)]['ctr'] for m in months_to_show if (list(monthly_stats.keys())[0][0], m) in monthly_stats]
            # m adalah tuple (tahun, bulan)
            month_names = [f"{calendar.month_name[int(m[1])]} {m[0]}" for m in months_to_show]
            if len(ctrs) >= 2:
                trend = 'naik' if ctrs[-1] > ctrs[0] else 'turun' if ctrs[-1] < ctrs[0] else 'stabil'
                llm_answer = (
                    f"Tren CTR untuk segmen yang diminta ({list(monthly_stats.keys())[0][0]}) selama {n} bulan terakhir: "
                    f"{', '.join([f'{mn}: {c:.2f}%' for mn, c in zip(month_names, ctrs)])}.\n"
                    f"Secara umum, tren CTR {trend} dari bulan pertama ke bulan terakhir."
                )
            else:
                llm_answer = (
                    f"Data tren CTR untuk segmen yang diminta ({list(monthly_stats.keys())[0][0]}) selama {n} bulan terakhir tidak cukup untuk analisis tren. "
                    f"Data tersedia untuk bulan: {', '.join(month_names) if month_names else 'tidak ada'}"
                )
            print(f"[DEBUG] Jawaban tren segmented: {llm_answer}")
            return state.copy(update={"llm_answer": llm_answer})
        # Fallback ke logic lama jika tidak segmented
        # ...existing code...
    # Debug intent dan bulan_list
    print(f"[DEBUG] node_llm_summary intent: {getattr(state, 'intent', None)} | bulan_list: {getattr(state, 'bulan_list', None)}")
    print(f"[DEBUG] node_llm_summary monthly_stats keys: {list(getattr(state, 'monthly_stats', {}).keys())}")
    
    # ADDITIVE SAFETY: If intent is tanya_bulan but monthly_stats is empty, provide fallback message
    if getattr(state, 'intent', None) == 'tanya_bulan':
        monthly_stats = getattr(state, 'monthly_stats', {})
        if not monthly_stats or len(monthly_stats) == 0:
            print("[WARN] Intent tanya_bulan but monthly_stats is empty - providing fallback message")
            fallback_msg = (
                "Maaf, saya tidak dapat menemukan data bulan pada dataset Anda. "
                "Pastikan kolom 'Date' atau 'Tanggal' tersedia dan berformat yang benar (YYYY-MM-DD atau DD/MM/YYYY). "
                "Atau coba tanyakan informasi lain seperti 'Apa saja worksheet yang tersedia?'"
            )
            return state.copy(update={"llm_answer": fallback_msg})
    
    # Jika intent tanya_bulan, cek apakah pertanyaan user minta total leads/metrik spesifik untuk bulan tertentu
    if getattr(state, 'intent', None) == 'tanya_bulan' and getattr(state, 'bulan_list', None):
        import re, calendar
        question = getattr(state, 'question', '').lower()
        bulan_list = state.bulan_list
        # Deteksi nama bulan di pertanyaan user (Indonesia & Inggris)
        bulan_map = {
            'january': 1, 'jan': 1, 'januari': 1,
            'february': 2, 'feb': 2, 'februari': 2,
            'march': 3, 'mar': 3, 'maret': 3,
            'april': 4, 'apr': 4,
            'may': 5, 'mei': 5,
            'june': 6, 'jun': 6, 'juni': 6,
            'july': 7, 'jul': 7, 'juli': 7,
            'august': 8, 'aug': 8, 'agustus': 8,
            'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'oktober': 10, 'okt': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12, 'desember': 12, 'des': 12
        }
        bulan_ditanya = None
        tahun_ditanya = None
        for nama_bulan, idx_bulan in bulan_map.items():
            if nama_bulan in question:
                bulan_ditanya = idx_bulan
                # Cek jika ada tahun di pertanyaan
                m = re.search(rf"{nama_bulan} (\d{{4}})", question)
                if m:
                    tahun_ditanya = int(m.group(1))
                break
        # Deteksi metrik yang ditanya user
        metrik_map = {
            'whatsapp': ['wa', 'whatsapp', 'whatsapp leads', 'wa lead', 'leads wa', 'lead wa', 'whatsapp lead', 'wa_lead', 'leads whatsapp', 'lead_whatsapp'],
            'facebook': ['fb', 'on-facebook', 'on-facebook leads', 'facebook leads', 'leads fb', 'lead fb', 'fb lead', 'lead_fb', 'leads_facebook', 'lead_facebook'],
            'lead form': ['lead form', 'form', 'leadform', 'lead_form', 'formulir', 'form lead', 'formulir lead', 'leadformulir', 'form_lead'],
            'messaging': ['messaging', 'messaging conversations started', 'msg_conv', 'msg conv', 'pesan', 'pesan masuk', 'percakapan pesan'],
            'cost': ['cost', 'biaya', 'spend', 'budget', 'pengeluaran', 'total cost', 'total biaya', 'total spend', 'total pengeluaran'],
            'impressions': ['impressions', 'imp', 'impr', 'impression', 'tayangan', 'total impressions', 'total imp', 'total impr', 'total impression', 'total tayangan'],
            'clicks': ['clicks', 'all clicks', 'link clicks', 'link', 'klik', 'total clicks', 'total klik', 'klik link', 'total link clicks', 'total link'],
        }
        metrik_ditanya = None
        for k, alias_list in metrik_map.items():
            for alias in alias_list:
                if alias in question:
                    metrik_ditanya = k
                    print(f"[DEBUG] METRIC ALIAS MATCH: '{alias}' -> '{k}'")
                    break
            if metrik_ditanya:
                break
        # Default ke whatsapp jika tidak terdeteksi
        if not metrik_ditanya:
            if 'lead' in question:
                metrik_ditanya = 'whatsapp'
            elif 'cost' in question or 'biaya' in question or 'spend' in question or 'budget' in question or 'pengeluaran' in question:
                metrik_ditanya = 'cost'
            elif 'impression' in question or 'tayangan' in question:
                metrik_ditanya = 'impressions'
            elif 'click' in question or 'klik' in question:
                metrik_ditanya = 'clicks'
            print(f"[DEBUG] METRIC FALLBACK: '{metrik_ditanya}'")
        # Jika ditemukan bulan yang ditanya
        if bulan_ditanya and metrik_ditanya:
            monthly_stats = getattr(state, 'monthly_stats', {})
            found = False
            total_val = 0
            tahun_keys = set()
            for (thn, bln), metrik in monthly_stats.items():
                if bln == bulan_ditanya and (tahun_ditanya is None or thn == tahun_ditanya):
                    # Pilih field sesuai metrik, fallback additive
                    if metrik_ditanya == 'whatsapp':
                        total_val += metrik.get('wa', metrik.get('leads', 0))
                        total_val += metrik.get('whatsapp', 0) + metrik.get('whatsapp leads', 0) + metrik.get('leads wa', 0) + metrik.get('lead wa', 0)
                    elif metrik_ditanya == 'facebook':
                        total_val += metrik.get('fb', metrik.get('leads_fb', 0))
                        total_val += metrik.get('facebook', 0) + metrik.get('facebook leads', 0) + metrik.get('leads fb', 0) + metrik.get('lead fb', 0)
                    elif metrik_ditanya == 'lead form':
                        total_val += metrik.get('lead form', metrik.get('lead_form', 0))
                        total_val += metrik.get('leadform', 0) + metrik.get('form', 0) + metrik.get('formulir', 0)
                    elif metrik_ditanya == 'messaging':
                        total_val += metrik.get('messaging', metrik.get('msg_conv', 0))
                        total_val += metrik.get('messaging conversations started', 0) + metrik.get('pesan', 0)
                    elif metrik_ditanya == 'cost':
                        total_val += metrik.get('cost', 0)
                        total_val += metrik.get('biaya', 0) + metrik.get('spend', 0) + metrik.get('budget', 0) + metrik.get('pengeluaran', 0)
                    elif metrik_ditanya == 'impressions':
                        total_val += metrik.get('impr', metrik.get('impressions', 0))
                        total_val += metrik.get('imp', 0) + metrik.get('tayangan', 0)
                    elif metrik_ditanya == 'clicks':
                        total_val += metrik.get('clicks', 0)
                        total_val += metrik.get('all clicks', 0) + metrik.get('link clicks', 0) + metrik.get('link', 0) + metrik.get('klik', 0)
                    tahun_keys.add(thn)
                    found = True
            print(f"[DEBUG] METRIC FILTER: bulan={bulan_ditanya}, metrik={metrik_ditanya}, total={total_val}")
            if found:
                nama_bulan_str = [k for k,v in bulan_map.items() if v==bulan_ditanya][0].capitalize()
                tahun_str = f" {tahun_ditanya}" if tahun_ditanya else (f" {max(tahun_keys)}" if tahun_keys else "")
                label = metrik_ditanya.replace('whatsapp','WhatsApp leads').replace('facebook','Facebook leads').replace('lead form','Lead Form').replace('messaging','Messaging Conversations Started').replace('cost','Cost').replace('impressions','Impressions').replace('clicks','Clicks')
                llm_answer = f"Total {label} pada bulan {nama_bulan_str}{tahun_str}: {int(total_val)}."
                print(f"[DEBUG] Jawaban agregasi bulan metrik: {llm_answer}")
                return state.copy(update={"llm_answer": llm_answer})
        # Jika tidak ditemukan data, fallback ke daftar bulan
        if len(bulan_list) == 1:
            llm_answer = f"Data yang tersedia hanya untuk bulan {bulan_list[0]}."
        else:
            bulan_str = ", ".join(bulan_list[:-1]) + f", dan {bulan_list[-1]}" if len(bulan_list) > 2 else " dan ".join(bulan_list)
            llm_answer = f"Data yang tersedia mencakup bulan: {bulan_str}."
        print(f"[DEBUG] Jawaban bulan fallback: {llm_answer}")
        return state.copy(update={"llm_answer": llm_answer})
    # Untuk intent tanya_saran atau tanya_performa, gunakan summary dan analisis
    mm = state.main_metrics or {}
    if isinstance(mm, dict):
        summary = "Main metrics:\n" + "\n".join(f"- {k}: {v}" for k, v in mm.items()) + "\n"
    else:
        summary = f"Main metrics: {mm}\n"
    full_summary = summary
    
    # ADDITIVE: Include age-gender breakdown jika tersedia
    age_gender = getattr(state, 'age_gender', None)
    if age_gender and isinstance(age_gender, dict) and len(age_gender) > 0:
        print(f"[DEBUG] LLM_SUMMARY: age_gender breakdown tersedia dengan {len(age_gender)} segmen")
        ag_summary = "\n\nBreakdown performa berdasarkan Age & Gender:\n"
        # Sort by cost descending untuk prioritaskan segmen dengan spend tertinggi
        sorted_age_gender = sorted(age_gender.items(), key=lambda x: x[1].get('cost', 0), reverse=True)
        for key, metrics in sorted_age_gender[:20]:  # Limit 20 segmen teratas untuk avoid context overflow
            age, gender = key.split('|')
            cost = metrics.get('cost', 0)
            impr = metrics.get('impr', 0)
            clicks = metrics.get('clicks', 0)
            link = metrics.get('link', 0)
            ctr = metrics.get('ctr', 0)
            lctr = metrics.get('lctr', 0)
            wa = metrics.get('wa', 0)
            cpwa = metrics.get('cpwa', 0)
            ag_summary += f"  - {age} | {gender}: cost={cost:.0f}, impressions={impr:.0f}, clicks={clicks:.0f}, link_clicks={link:.0f}, CTR={ctr:.2f}%, Link CTR={lctr:.2f}%, WA leads={wa:.0f}, CPWA={cpwa:.0f}\n"
        full_summary += ag_summary
        print(f"[DEBUG] LLM_SUMMARY: age_gender breakdown added to context ({len(sorted_age_gender)} segmen total)")
    else:
        print(f"[DEBUG] LLM_SUMMARY: age_gender breakdown NOT available or empty")
    
    # ADDITIVE: Include age-gender ENHANCED breakdown dengan CPM, CPC, CPLC, Reach, Frequency, Conversion Rate
    age_gender_enhanced = getattr(state, 'age_gender_enhanced', None)
    if age_gender_enhanced and isinstance(age_gender_enhanced, dict) and len(age_gender_enhanced) > 0:
        print(f"[DEBUG] LLM_SUMMARY: age_gender_enhanced tersedia dengan {len(age_gender_enhanced)} segmen")
        ag_enh_summary = "\n\nEnhanced Age & Gender Metrics (CPM, CPC, CPLC, Reach, Frequency, Conversion Rate):\n"
        # Sort by cost descending
        sorted_ag_enh = sorted(age_gender_enhanced.items(), key=lambda x: x[1].get('cost', 0), reverse=True)
        for key, m in sorted_ag_enh[:20]:  # Limit 20 segmen
            ag_enh_summary += (
                f"  - {key}: Reach={m.get('reach', 0):.0f}, Frequency={m.get('frequency', 0):.2f}, "
                f"CPM={m.get('cpm', 0):.0f}, CPC={m.get('cpc', 0):.0f}, CPLC={m.get('cplc', 0):.0f}, "
                f"Conv Rate={m.get('conversion_rate', 0):.2f}%, FB Leads={m.get('fb_leads', 0):.0f}, "
                f"Lead Form={m.get('lead_form', 0):.0f}\n"
            )
        full_summary += ag_enh_summary
        print(f"[DEBUG] LLM_SUMMARY: age_gender_enhanced added to context")
    else:
        print(f"[DEBUG] LLM_SUMMARY: age_gender_enhanced NOT available or empty")
    
    # ADDITIVE: Include region breakdown jika tersedia
    region_breakdown = getattr(state, 'region_breakdown', None)
    if region_breakdown and isinstance(region_breakdown, dict) and len(region_breakdown) > 0:
        print(f"[DEBUG] LLM_SUMMARY: region_breakdown tersedia dengan {len(region_breakdown)} regions")
        reg_summary = "\n\nBreakdown performa berdasarkan Region (Wilayah Geografis):\n"
        # Sort by cost descending untuk prioritaskan region dengan spend tertinggi
        sorted_regions = sorted(region_breakdown.items(), key=lambda x: x[1].get('cost', 0), reverse=True)
        for region, metrics in sorted_regions[:20]:  # Limit 20 regions teratas untuk avoid context overflow
            cost = metrics.get('cost', 0)
            impr = metrics.get('impr', 0)
            clicks = metrics.get('clicks', 0)
            link = metrics.get('link', 0)
            reach = metrics.get('reach', 0)
            cpm = metrics.get('cpm', 0)
            cpc = metrics.get('cpc', 0)
            ctr = metrics.get('ctr', 0)
            lctr = metrics.get('lctr', 0)
            reg_summary += f"  - {region}: cost={cost:.0f}, impressions={impr:.0f}, clicks={clicks:.0f}, link_clicks={link:.0f}, reach={reach:.0f}, CPM={cpm:.0f}, CPC={cpc:.0f}, CTR={ctr:.2f}%, Link CTR={lctr:.2f}%\n"
        full_summary += reg_summary
        print(f"[DEBUG] LLM_SUMMARY: region breakdown added to context ({len(sorted_regions)} regions total)")
    else:
        print(f"[DEBUG] LLM_SUMMARY: region breakdown NOT available or empty")
    
    # ADDITIVE: Include breakdown adset/ad ENHANCED dengan full metrics
    breakdown_adset_enhanced = getattr(state, 'breakdown_adset_enhanced', None)
    if breakdown_adset_enhanced and isinstance(breakdown_adset_enhanced, dict) and len(breakdown_adset_enhanced) > 0:
        print(f"[DEBUG] LLM_SUMMARY: breakdown_adset_enhanced tersedia dengan {len(breakdown_adset_enhanced)} adsets")
        adset_enh_summary = "\n\nEnhanced Adset Breakdown (Full Metrics):\n"
        sorted_adsets = sorted(breakdown_adset_enhanced.items(), key=lambda x: x[1].get('cost', 0), reverse=True)
        for adset, m in sorted_adsets[:15]:  # Limit 15 adsets
            adset_enh_summary += (
                f"  - {adset}: Cost={m.get('cost', 0):.0f}, Reach={m.get('reach', 0):.0f}, Freq={m.get('frequency', 0):.2f}, "
                f"CPM={m.get('cpm', 0):.0f}, CPC={m.get('cpc', 0):.0f}, CPLC={m.get('cplc', 0):.0f}, "
                f"CTR={m.get('ctr', 0):.2f}%, LCTR={m.get('lctr', 0):.2f}%, Conv Rate={m.get('conversion_rate', 0):.2f}%\n"
            )
        full_summary += adset_enh_summary
        print(f"[DEBUG] LLM_SUMMARY: breakdown_adset_enhanced added to context")
    else:
        print(f"[DEBUG] LLM_SUMMARY: breakdown_adset_enhanced NOT available")
    
    # ADDITIVE: Include outbound clicks proportion analysis
    outbound_clicks = getattr(state, 'outbound_clicks', None)
    if outbound_clicks and isinstance(outbound_clicks, dict):
        total_outbound = outbound_clicks.get('total', 0)
        if total_outbound > 0:
            print(f"[DEBUG] LLM_SUMMARY: outbound_clicks tersedia, total={total_outbound}")
            outbound_summary = "\n\nOutbound Clicks Channel Breakdown:\n"
            prop = outbound_clicks.get('proportion', {})
            outbound_summary += (
                f"  - Total Outbound Clicks: {total_outbound:.0f}\n"
                f"  - WhatsApp: {outbound_clicks.get('whatsapp', 0):.0f} ({prop.get('whatsapp', 0):.1f}%)\n"
                f"  - Website: {outbound_clicks.get('website', 0):.0f} ({prop.get('website', 0):.1f}%)\n"
                f"  - Messaging: {outbound_clicks.get('messaging', 0):.0f} ({prop.get('messaging', 0):.1f}%)\n"
                f"  - Form: {outbound_clicks.get('form', 0):.0f} ({prop.get('form', 0):.1f}%)\n"
            )
            full_summary += outbound_summary
            print(f"[DEBUG] LLM_SUMMARY: outbound_clicks added to context")
        else:
            print(f"[DEBUG] LLM_SUMMARY: outbound_clicks total is 0, skipping")
    else:
        print(f"[DEBUG] LLM_SUMMARY: outbound_clicks NOT available")
    
    # ADDITIVE: Include period stats (weekly/monthly) untuk tren temporal
    period_stats_weekly = getattr(state, 'period_stats_weekly', None)
    if period_stats_weekly and isinstance(period_stats_weekly, dict) and len(period_stats_weekly) > 0:
        print(f"[DEBUG] LLM_SUMMARY: period_stats_weekly tersedia dengan {len(period_stats_weekly)} weeks")
        weekly_summary = "\n\nWeekly Performance Trend (Top 8 Recent Weeks):\n"
        # Sort by period (week) descending untuk show recent weeks first
        sorted_weeks = sorted(period_stats_weekly.items(), key=lambda x: x[0], reverse=True)[:8]
        for week, m in sorted_weeks:
            weekly_summary += (
                f"  - {week}: Cost={m.get('cost', 0):.0f}, Reach={m.get('reach', 0):.0f}, "
                f"CPM={m.get('cpm', 0):.0f}, CTR={m.get('ctr', 0):.2f}%, Conv Rate={m.get('conversion_rate', 0):.2f}%\n"
            )
        full_summary += weekly_summary
        print(f"[DEBUG] LLM_SUMMARY: period_stats_weekly added to context")
    else:
        print(f"[DEBUG] LLM_SUMMARY: period_stats_weekly NOT available or empty")
    
    period_stats_monthly = getattr(state, 'period_stats_monthly', None)
    if period_stats_monthly and isinstance(period_stats_monthly, dict) and len(period_stats_monthly) > 0:
        print(f"[DEBUG] LLM_SUMMARY: period_stats_monthly tersedia dengan {len(period_stats_monthly)} months")
        monthly_summary = "\n\nMonthly Performance Trend (Top 6 Recent Months):\n"
        # Sort by period (month) descending
        sorted_months = sorted(period_stats_monthly.items(), key=lambda x: x[0], reverse=True)[:6]
        for month, m in sorted_months:
            monthly_summary += (
                f"  - {month}: Cost={m.get('cost', 0):.0f}, Reach={m.get('reach', 0):.0f}, "
                f"CPM={m.get('cpm', 0):.0f}, CTR={m.get('ctr', 0):.2f}%, Conv Rate={m.get('conversion_rate', 0):.2f}%\n"
            )
        full_summary += monthly_summary
        print(f"[DEBUG] LLM_SUMMARY: period_stats_monthly added to context")
    else:
        print(f"[DEBUG] LLM_SUMMARY: period_stats_monthly NOT available or empty")
    
    question = getattr(state, 'question', 'Berapa total cost dan leads bulan ini?')
    llm_answer = llm_summarize_aggregation(full_summary, question)
    return state.copy(update={"llm_answer": llm_answer})

graph.add_node("llm_summary", node_llm_summary)



graph.add_edge("detect_intent", "extract_bulan")
graph.add_edge("extract_bulan", "aggregate_monthly")
graph.add_edge("aggregate_monthly", "aggregate_age_gender_monthly")
graph.add_edge("aggregate_age_gender_monthly", "extract_adsets")
graph.add_edge("extract_adsets", "tren_bulanan")
graph.add_edge("tren_bulanan", "main_metrics")
graph.add_edge("main_metrics", "daily_weekly")
graph.add_edge("daily_weekly", "breakdown_adset")
graph.add_edge("breakdown_adset", "breakdown_ad")
graph.add_edge("breakdown_ad", "age_gender")
graph.add_edge("age_gender", "region")  # ADDITIVE: Add region to workflow
# ADDITIVE: Connect enhanced aggregation nodes (parallel processing after region)
graph.add_edge("region", "breakdown_adset_enhanced")
graph.add_edge("breakdown_adset_enhanced", "breakdown_ad_enhanced")
graph.add_edge("breakdown_ad_enhanced", "age_gender_enhanced")
graph.add_edge("age_gender_enhanced", "period_daily")
graph.add_edge("period_daily", "period_weekly")
graph.add_edge("period_weekly", "period_monthly")
graph.add_edge("period_monthly", "outbound_clicks")
graph.add_edge("outbound_clicks", "llm_summary")
graph.add_edge("llm_summary", END)

graph.set_entry_point("detect_intent")
workflow = graph.compile()

# Example usage

def run_aggregation_workflow(sheet_data, question=None):
    # DEBUG: Print keys dan contoh data
    if sheet_data:
        print("[DEBUG] Kolom di sheet_data:", list(sheet_data[0].keys()))
        print("[DEBUG] 3 baris pertama sheet_data:")
        for i, row in enumerate(sheet_data[:3]):
            print(f"  Row {i+1}: {row}")
    else:
        print("[DEBUG] sheet_data kosong!")
    # Pastikan question dikirim ke state agar intent detection bekerja
    state = AggregationState(sheet_data=sheet_data, question=question)
    result = workflow.invoke(state)
    return result

if __name__ == "__main__":
    # Contoh data dummy
    sheet_data = [
        {"Cost": 10000, "Impressions": 1000, "All Clicks": 50, "WhatsApp": 5, "Ad set": "A", "Ad": "X", "Age": "18-24", "Gender": "Male"},
        {"Cost": 20000, "Impressions": 2000, "All Clicks": 80, "WhatsApp": 10, "Ad set": "B", "Ad": "Y", "Age": "25-34", "Gender": "Female"},
    ]
    result = run_aggregation_workflow(sheet_data)
    print("Workflow result:", result)
