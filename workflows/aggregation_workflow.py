
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
    aggregate_outbound_clicks,
    aggregate_adset_by_age_gender  # ADDITIVE: Aggregate by adset filtered by age/gender
)

# ADDITIVE: Helper function to extract month from date string
def extract_month_from_date(date_str):
    """Extract month number (1-12) from date string in various formats"""
    if not date_str:
        return None
    import re
    from datetime import datetime
    
    date_str = str(date_str).strip()
    
    # Try ISO format YYYY-MM-DD
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        return int(m.group(2))
    
    # Try DD/MM/YYYY
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if m:
        return int(m.group(2))
    
    # Try datetime parsing as fallback
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.month
    except:
        pass
    
    try:
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        return dt.month
    except:
        pass
    
    return None

# ADDITIVE: Helper function to extract week number from date string
def extract_week_from_date(date_str, month_num=None):
    """
    Extract week number (1-5) within a month from date string.
    If month_num provided, calculate week relative to that month's start.
    """
    if not date_str:
        return None
    import re
    from datetime import datetime
    
    date_str = str(date_str).strip()
    dt = None
    
    # Try ISO format YYYY-MM-DD
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if m:
        dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    
    # Try DD/MM/YYYY
    if not dt:
        m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if m:
            dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    
    # Try datetime parsing as fallback
    if not dt:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            try:
                dt = datetime.strptime(date_str, '%d/%m/%Y')
            except:
                return None
    
    if not dt:
        return None
    
    # Calculate week number within the month (1-based)
    # Week 1 = days 1-7, Week 2 = days 8-14, etc.
    day_of_month = dt.day
    week_of_month = ((day_of_month - 1) // 7) + 1
    
    return week_of_month

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
    chat_history: list = None  # ADDITIVE: Chat history for LLM context memory


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
    
    # ADDITIVE: Detect adset name in question for cross-filter (age/gender + adset)
    # If not found, function call remains unchanged (backward compatible)
    adset_name = None
    question_lower = state.question.lower()
    
    # Check for adset keywords followed by potential adset name
    # Patterns: "adset X", "pada adset X", "di adset X", etc.
    import re
    adset_patterns = [
        r'(?:pada|di|untuk|dari)\s+(?:ad\s*set|adset)\s+([a-zA-Z0-9_\-&]+)',  # pada adset vgardh2_oil&gas
        r'(?:ad\s*set|adset)\s+([a-zA-Z0-9_\-&]+)',  # adset vgardh2_oil&gas
    ]
    
    for pattern in adset_patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            adset_name = match.group(1)
            print(f"[DEBUG] node_age_gender_enhanced: detected adset_name='{adset_name}' from question")
            break
    
    # Call aggregate function with or without adset filter (ADDITIVE)
    if adset_name:
        data = aggregate_age_gender_enhanced(state.sheet_data, adset_name=adset_name)
        print(f"[DEBUG] node_age_gender_enhanced: aggregated {len(data)} age|gender segments (filtered by adset '{adset_name}')")
    else:
        data = aggregate_age_gender_enhanced(state.sheet_data)
        print(f"[DEBUG] node_age_gender_enhanced: aggregated {len(data)} age|gender segments")
    
    return state.copy(update={"age_gender_enhanced": data, "question": state.question})

def node_period_daily(state: AggregationState):
    """Daily aggregation dengan metrik lengkap"""
    print("[DEBUG] node_period_daily: executing")
    
    # ADDITIVE: Check if user query needs daily data
    question_lower = (state.question or "").lower()
    needs_daily = any(kw in question_lower for kw in ["tanggal", "date", "hari", "harian", "daily"])
    
    # DEBUG: Print state.question to verify it's passed correctly
    print(f"[DEBUG] node_period_daily: state.question = '{state.question}'")
    print(f"[DEBUG] node_period_daily: question_lower = '{question_lower}'")
    print(f"[DEBUG] node_period_daily: needs_daily = {needs_daily}")
    
    # ADDITIVE: Skip daily aggregation if dataset too large AND user doesn't need daily data
    # Daily creates too many unique keys for large datasets, causing timeout/OOM
    # EXCEPTION: Always run if user explicitly asks for date-specific data
    if len(state.sheet_data) > 5000 and not needs_daily:
        print(f"[DEBUG] node_period_daily: SKIPPED - dataset too large ({len(state.sheet_data)} rows), daily aggregation disabled for performance")
        return state.copy(update={"period_stats_daily": {}, "question": state.question})
    
    # ADDITIVE: If user needs daily data, run aggregation regardless of size
    if needs_daily and len(state.sheet_data) > 5000:
        print(f"[DEBUG] node_period_daily: ENABLED for date query despite large dataset ({len(state.sheet_data)} rows)")
    
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
    
    # ADDITIVE: Apply temporal filtering if question contains temporal keywords
    from services.llm_summary import detect_temporal_filter, filter_sheet_data_by_temporal
    
    question = getattr(state, 'question', '')
    sheet_data = state.sheet_data
    
    # Detect and apply temporal filter
    temporal_filter = detect_temporal_filter(question)
    if any([temporal_filter.get('week_num'), temporal_filter.get('month_num'), temporal_filter.get('year')]):
        print(f"[DEBUG] node_outbound_clicks: Applying temporal filter - week={temporal_filter.get('week_num')}, month={temporal_filter.get('month_num')}, year={temporal_filter.get('year')}")
        sheet_data = filter_sheet_data_by_temporal(sheet_data, temporal_filter)
        print(f"[DEBUG] node_outbound_clicks: Data filtered from {len(state.sheet_data)} to {len(sheet_data)} rows")
    
    data = aggregate_outbound_clicks(sheet_data)
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
    
    # ADDITIVE: Detect ranking queries FIRST (highest priority) - NEW PATTERN
    ranking_patterns = [
        r'\b(mana|adset|ad|region|segmen|age|gender|campaign)\b.{0,50}\b(tertinggi|terendah|terbesar|terkecil|terbanyak|tersedikit|paling tinggi|paling rendah|paling banyak|paling sedikit|maksimal|minimal)\b',
        r'\b(tertinggi|terendah|terbesar|terkecil|terbanyak|tersedikit|paling tinggi|paling rendah|paling banyak|paling sedikit|maksimal|minimal)\b.{0,50}\b(cost|biaya|spend|reach|clicks|ctr|impressions|leads|lead form)\b',
        r'\b(top|bottom|best|worst)\b.{0,30}\b(adset|ad|region|campaign)\b',
        r'\bmenyumbang\b.{0,30}\b(cost|biaya|spend|reach|clicks)\b.{0,30}\b(terbesar|tertinggi|terkecil|terendah|terbanyak|tersedikit)\b'
    ]
    ranking_match = any(re.search(p, question) for p in ranking_patterns)
    
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
    # Regex for bulan intent (month listing) - ONLY when not a ranking query
    bulan_patterns = [
        r'\bdata bulan\b',
        r'\bdaftar bulan\b',
        r'bulan apa( saja| aja)?',
        r'bulan yang (ada|tersedia)',
        r'bulan di data',
        r'periode apa( saja| aja)?',
        r'periode (tersedia|di data)',
        r'\bdata (periode|bulan)\b',
    ]
    bulan_match = any(re.search(p, question) for p in bulan_patterns) and not ranking_match  # MODIFIED: Exclude if ranking query
    
    # Deteksi intent tren multi-bulan (misal: "3 bulan terakhir", "4 bulan terakhir")
    trend_months = 0
    trend_match = re.search(r"(\d+) bulan terakhir", question)
    if trend_match:
        trend_months = int(trend_match.group(1))
    
    # MODIFIED Prioritization: tren > ranking > saran > performa > bulan > umum
    # Ranking queries should be treated as performa intent
    if trend_months > 0:
        intent = 'tanya_tren'
    elif ranking_match:
        intent = 'tanya_performa'  # Ranking is a type of performance query
        print(f"[DEBUG] Ranking query detected, intent set to 'tanya_performa'")
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
    import re
    
    # ADDITIVE: Handle query "kelompok usia/gender mana yang memiliki [metric] terendah/tertinggi?"
    # Pattern: ranking age/gender segments by metric (NEW HANDLER - HIGHEST PRIORITY)
    question = getattr(state, 'question', '').lower()
    
    # Detect pattern: "kelompok usia mana" or "gender mana" + "terendah/tertinggi" + metric
    if any(kw in question for kw in ["kelompok usia", "kelompok umur", "age group", "usia mana", "umur mana", "gender mana", "jenis kelamin mana"]) and any(kw in question for kw in ["terendah", "tertinggi", "terkecil", "terbesar", "paling rendah", "paling tinggi", "minimal", "maksimal", "lowest", "highest"]):
        print("[DEBUG] Detected query: ranking age/gender segments by metric")
        
        # Detect sorting order (ascending for terendah/terkecil, descending for tertinggi/terbesar)
        is_ascending = any(kw in question for kw in ["terendah", "terkecil", "paling rendah", "minimal", "lowest"])
        order_text = "terendah" if is_ascending else "tertinggi"
        
        # Extract month filter if present
        import calendar
        bulan_map = {
            'january': 1, 'jan': 1, 'januari': 1,
            'february': 2, 'feb': 2, 'februari': 2,
            'march': 3, 'mar': 3, 'maret': 3,
            'april': 4, 'apr': 4,
            'may': 5, 'mei': 5,
            'june': 6, 'jun': 6, 'juni': 6,
            'july': 7, 'jul': 7, 'juli': 7,
            'august': 8, 'aug': 8, 'agustus': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'oktober': 10, 'okt': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12, 'desember': 12, 'des': 12
        }
        month_filter = None
        month_name = None
        for nama_bulan, idx_bulan in bulan_map.items():
            if nama_bulan in question:
                month_filter = idx_bulan
                month_name = nama_bulan.capitalize()
                break
        
        # ADDITIVE: Extract week filter if present (minggu ke 1, minggu ke 2, week 2, etc.)
        import re
        week_filter = None
        week_match = re.search(r'minggu ke[- ]?(\d+)|week[- ]?(\d+)', question)
        if week_match:
            week_filter = int(week_match.group(1) or week_match.group(2))
            print(f"[DEBUG] Week filter detected: minggu ke-{week_filter}")
        
        # Extract metric - TAMBAHKAN CPWA dan metric lainnya
        metric_map = {
            # Specific lead-related keywords FIRST (longest match first to avoid early matching)
            'lead form': 'lead_form',  # Lead Form metric - MUST come before 'lead'
            'lead_form': 'lead_form',
            'cost per wa': 'cpwa',
            'cost per whatsapp': 'cpwa',
            'biaya per wa': 'cpwa',
            'cost per click': 'cpc',
            'cost per mille': 'cpm',
            'cost per link click': 'cplc',
            'click through rate': 'ctr',
            'link ctr': 'lctr',
            'on-facebook leads': 'fb',
            # Generic single-word keywords (less specific)
            'cpwa': 'cpwa',
            'cpc': 'cpc',
            'cpm': 'cpm',
            'cplc': 'cplc',
            'ctr': 'ctr',
            'lctr': 'lctr',
            'klik': 'clicks',
            'click': 'clicks',
            'form': 'lead_form',  # After 'lead form', so it won't interfere
            'lead': 'wa',  # Default to WA leads (generic "lead" without "form") - LAST to not interfere with 'lead form'
            'leads': 'wa',
            'whatsapp': 'wa',
            'wa': 'wa',
            'facebook': 'fb',
            'fb': 'fb',
            'konversi': 'wa',
            'cost': 'cost',
            'biaya': 'cost',
            'spend': 'cost',
            'impresi': 'impr',
            'impression': 'impr',
            'jangkauan': 'reach',
            'reach': 'reach',
            'frequency': 'frequency',
            'frekuensi': 'frequency'
        }
        
        detected_metric = None
        for kw, metric_key in metric_map.items():
            if kw in question:
                detected_metric = metric_key
                print(f"[DEBUG] Metric detected: '{kw}' -> '{metric_key}'")
                break
        
        if not detected_metric:
            detected_metric = 'cpwa'  # Default to CPWA for this type of query
            print(f"[DEBUG] No metric detected, using default: '{detected_metric}'")
        
        # ADDITIVE: Updated debug print to include week info
        week_text = f", week={week_filter}" if week_filter else ""
        print(f"[DEBUG] Ranking query - metric={detected_metric}, order={order_text}, month={month_name}{week_text}")
        
        # Get age_gender breakdown
        age_gender = getattr(state, 'age_gender', None)
        if not age_gender or len(age_gender) == 0:
            # Aggregate if not yet done
            age_gender = aggregate_age_gender(state.sheet_data)
        
        if age_gender and len(age_gender) > 0:
            # ADDITIVE: Filter by month AND week if specified
            if month_filter or week_filter:
                filtered_data = state.sheet_data
                
                # Apply month filter
                if month_filter:
                    print(f"[DEBUG] Filtering data by month: {month_filter} ({month_name})")
                    filtered_data = [row for row in filtered_data if row.get('Date') and extract_month_from_date(row.get('Date')) == month_filter]
                
                # Apply week filter (only if month also specified, week is relative to month)
                if week_filter and month_filter:
                    print(f"[DEBUG] Filtering data by week: {week_filter} within month {month_name}")
                    filtered_data = [row for row in filtered_data if row.get('Date') and extract_week_from_date(row.get('Date'), month_filter) == week_filter]
                
                if len(filtered_data) > 0:
                    age_gender = aggregate_age_gender(filtered_data)
                    period_text = f"minggu ke-{week_filter} bulan {month_name}" if week_filter else f"bulan {month_name}"
                    print(f"[DEBUG] Filtered {len(state.sheet_data)} rows -> {len(filtered_data)} rows for {period_text}")
                else:
                    period_text = f"minggu ke-{week_filter} di bulan {month_name}" if week_filter else f"bulan {month_name}"
                    llm_answer = f"Tidak ditemukan data untuk {period_text}. Silakan cek periode yang tersedia."
                    return state.copy(update={"llm_answer": llm_answer})
            
            # Filter segments that have valid metric data (exclude 0 or None)
            valid_segments = {}
            total_wa_leads = 0  # ADDITIVE: Track total WA leads for better error message
            for segment_key, metrics in age_gender.items():
                metric_value = metrics.get(detected_metric, 0)
                # For CPWA, only include segments with WA leads > 0 (CPWA is cost/wa_leads)
                if detected_metric == 'cpwa':
                    wa_leads = metrics.get('wa', 0)
                    total_wa_leads += wa_leads  # ADDITIVE: Sum up WA leads
                    if wa_leads > 0 and metric_value > 0:
                        valid_segments[segment_key] = metrics
                # For lead_form, include ALL segments even if 0 (show complete ranking)
                elif detected_metric == 'lead_form':
                    valid_segments[segment_key] = metrics
                elif metric_value > 0:  # For other metrics, just check > 0
                    valid_segments[segment_key] = metrics
            
            if len(valid_segments) == 0:
                # ADDITIVE: More informative error message for CPWA when no WA leads
                if detected_metric == 'cpwa' and total_wa_leads == 0:
                    period_text = f"minggu ke-{week_filter} di bulan {month_name}" if (week_filter and month_name) else (f"bulan {month_name}" if month_name else "periode yang diminta")
                    llm_answer = f"📊 Tidak ditemukan data **WhatsApp Leads** untuk {period_text}.\n\n💡 **Penjelasan**: CPWA (Cost Per WhatsApp Lead) = Cost ÷ WhatsApp Leads. Karena tidak ada WhatsApp leads di {period_text}, CPWA tidak dapat dihitung.\n\n✅ **Saran**: Coba periode lain yang memiliki data WhatsApp leads, atau gunakan metrik lain seperti:\n- **Cost** (Total biaya)\n- **Clicks** (Total klik)\n- **CTR** (Click-through rate)\n- **Impressions** (Total tayangan)"
                else:
                    llm_answer = f"Tidak ditemukan data {detected_metric.upper()} yang valid untuk analisis" + (f" pada bulan {month_name}" if month_name else "") + "."
                return state.copy(update={"llm_answer": llm_answer})
            
            # Sort by metric
            sorted_segments = sorted(valid_segments.items(), key=lambda x: x[1].get(detected_metric, 0), reverse=not is_ascending)
            
            # Build answer
            metric_label_map = {
                'cpwa': 'CPWA (Cost Per WhatsApp Lead)',
                'cpc': 'CPC (Cost Per Click)',
                'cpm': 'CPM (Cost Per Mille)',
                'cplc': 'CPLC (Cost Per Link Click)',
                'ctr': 'CTR (Click Through Rate)',
                'lctr': 'LCTR (Link Click Through Rate)',
                'clicks': 'Clicks (Klik)',
                'wa': 'WhatsApp Leads',
                'fb': 'Facebook Leads',
                'lead_form': 'Lead Form (Form Leads)',
                'cost': 'Cost (Biaya)',
                'impr': 'Impressions',
                'reach': 'Reach (Jangkauan)',
                'frequency': 'Frequency (Frekuensi)'
            }
            metric_label = metric_label_map.get(detected_metric, detected_metric.upper())
            
            # ADDITIVE: Include week info in response text
            if week_filter and month_name:
                period_text = f" pada minggu ke-**{week_filter}** bulan **{month_name}**"
            elif month_name:
                period_text = f" pada bulan **{month_name}**"
            else:
                period_text = ""
            
            answer_lines = [
                f"Berdasarkan analisis data{period_text}, berikut adalah ranking kelompok usia berdasarkan **{metric_label} {order_text}**:\n"
            ]
            
            # Show top 5 segments
            for i, (segment_key, metrics) in enumerate(sorted_segments[:5], 1):
                age_group, gender = segment_key.split('|')
                metric_value = metrics.get(detected_metric, 0)
                cost = metrics.get('cost', 0)
                wa_leads = metrics.get('wa', 0)
                
                gender_text = "👨 Laki-laki" if gender.lower() == "male" else "👩 Wanita" if gender.lower() == "female" else gender
                
                # Format metric value based on type
                if detected_metric in ['ctr', 'lctr']:
                    metric_display = f"{metric_value:.2f}%"
                elif detected_metric in ['frequency']:
                    metric_display = f"{metric_value:.2f}x"
                elif detected_metric in ['cpwa', 'cpc', 'cpm', 'cplc', 'cost']:
                    metric_display = f"Rp {metric_value:,.0f}"
                else:
                    metric_display = f"{metric_value:,.0f}"
                
                answer_lines.append(
                    f"{i}. **{age_group} | {gender_text}**: {metric_display}"
                    + (f" (Cost: Rp {cost:,.0f}, WA Leads: {wa_leads:,.0f})" if detected_metric == 'cpwa' else f" (Cost: Rp {cost:,.0f})")
                )
            
            # Add insight
            winner_segment, winner_metrics = sorted_segments[0]
            winner_age, winner_gender = winner_segment.split('|')
            winner_value = winner_metrics.get(detected_metric, 0)
            gender_text = "laki-laki" if winner_gender.lower() == "male" else "wanita"
            
            if detected_metric in ['ctr', 'lctr']:
                value_display = f"{winner_value:.2f}%"
            elif detected_metric in ['frequency']:
                value_display = f"{winner_value:.2f}x"
            elif detected_metric in ['cpwa', 'cpc', 'cpm', 'cplc', 'cost']:
                value_display = f"Rp {winner_value:,.0f}"
            else:
                value_display = f"{winner_value:,.0f}"
            
            # ADDITIVE: Include week/month in insight
            insight_period = f" pada minggu ke-{week_filter} bulan {month_name}" if (week_filter and month_name) else (f" pada bulan {month_name}" if month_name else "")
            
            answer_lines.append(
                f"\n💡 **Insight**: Kelompok **{winner_age} {gender_text}** memiliki {metric_label} **{order_text}** dengan nilai **{value_display}**{insight_period}."
            )
            
            # Additional recommendation for CPWA
            if detected_metric == 'cpwa' and is_ascending:
                answer_lines.append(
                    f"\n📊 **Rekomendasi**: Fokuskan budget lebih banyak pada segmen **{winner_age} {gender_text}** karena memiliki efisiensi biaya per WhatsApp lead yang paling baik (CPWA terendah)."
                )
            
            llm_answer = "\n".join(answer_lines)
            print(f"[DEBUG] Generated answer for age/gender ranking by metric query")
            return state.copy(update={"llm_answer": llm_answer})
        else:
            llm_answer = "Tidak ditemukan data age & gender untuk analisis. Pastikan worksheet yang dipilih memiliki kolom Age dan Gender."
            return state.copy(update={"llm_answer": llm_answer})
    
    # NEW HANDLER: Ranking adsets by lead metrics (lead form, whatsapp, fb leads)
    # Pattern: "adset dengan lead form terbanyak/terendah" or "adset mana dengan lead form tertinggi"
    if any(kw in question for kw in ["lead form", "lead_form", "facebook leads", "whatsapp leads", "messaging"]) and any(kw in question for kw in ["adset", "ad set", "campaign"]) and any(kw in question for kw in ["terbanyak", "terendah", "tertinggi", "terkecil", "paling banyak", "paling sedikit", "top", "ranking"]):
        print("[DEBUG] NEW HANDLER: Detected query - ranking adsets by lead metrics")
        print(f"[DEBUG] ADSET HANDLER ENTRY: state.sheet_data has {len(state.sheet_data)} rows")
        try:
            # Define bulan_map for month filtering (ADDITIVE: moved from age/gender handler)
            bulan_map = {
                'january': 1, 'jan': 1, 'januari': 1,
                'february': 2, 'feb': 2, 'februari': 2,
                'march': 3, 'mar': 3, 'maret': 3,
                'april': 4, 'apr': 4,
                'may': 5, 'mei': 5,
                'june': 6, 'jun': 6, 'juni': 6,
                'july': 7, 'jul': 7, 'juli': 7,
                'august': 8, 'aug': 8, 'agustus': 8,
                'september': 9, 'sep': 9, 'sept': 9,
                'october': 10, 'oct': 10, 'oktober': 10, 'okt': 10,
                'november': 11, 'nov': 11,
                'december': 12, 'dec': 12, 'desember': 12, 'des': 12
            }
            
            # Determine which lead metric
            lead_metric = 'lead_form'
            if 'whatsapp' in question:
                lead_metric = 'wa'
            elif 'facebook' in question or 'on-facebook' in question:
                lead_metric = 'fb_leads'
            elif 'messaging' in question:
                lead_metric = 'wa'  # Messaging is counted as WA leads
            
            # Determine sort order
            is_ascending = any(kw in question for kw in ["terendah", "terkecil", "paling sedikit", "lowest", "minimum"])
            order_text = "terendah" if is_ascending else "terbanyak"
            
            # Extract month/week filter if present
            month_filter = None
            month_name = None
            for nama_bulan, idx_bulan in bulan_map.items():
                if nama_bulan in question:
                    month_filter = idx_bulan
                    month_name = nama_bulan.capitalize()
                    break
            
            # Extract week filter
            week_filter = None
            week_match = re.search(r'minggu ke[- ]?(\d+)|week[- ]?(\d+)', question)
            if week_match:
                week_filter = int(week_match.group(1) or week_match.group(2))
            
            # Filter data by month/week if specified
            filtered_data = state.sheet_data
            print(f"[DEBUG] ADSET HANDLER: Starting with {len(filtered_data)} total rows")
            print(f"[DEBUG] ADSET HANDLER: month_filter={month_filter}, month_name={month_name}")
            
            if month_filter:
                before_filter = len(filtered_data)
                filtered_data = [row for row in filtered_data if row.get('Date') and extract_month_from_date(row.get('Date')) == month_filter]
                after_filter = len(filtered_data)
                print(f"[DEBUG] ADSET HANDLER: After month filter {month_name}: {before_filter} → {after_filter} rows")
                period_text = f"minggu ke-{week_filter} bulan {month_name}" if week_filter else f"bulan {month_name}"
            else:
                period_text = ""
                print(f"[DEBUG] ADSET HANDLER: No month filter, using all {len(filtered_data)} rows")
            
            if week_filter and month_filter:
                before_week = len(filtered_data)
                filtered_data = [row for row in filtered_data if row.get('Date') and extract_week_from_date(row.get('Date'), month_filter) == week_filter]
                after_week = len(filtered_data)
                print(f"[DEBUG] ADSET HANDLER: After week filter week {week_filter}: {before_week} → {after_week} rows")
            
            # Aggregate by adset
            print(f"[DEBUG] ADSET HANDLER: Aggregating {len(filtered_data)} filtered rows by Ad set")
            if filtered_data and len(filtered_data) > 0:
                print(f"[DEBUG] ADSET HANDLER: Sample row Ad set value: {filtered_data[0].get('Ad set', 'MISSING')}")
            
            adset_breakdown = aggregate_breakdown_enhanced(filtered_data, by="Ad set")
            
            if adset_breakdown and len(adset_breakdown) > 0:
                print(f"[DEBUG] Adset breakdown: {len(adset_breakdown)} adsets found")
                
                # Sort by lead metric
                sorted_adsets = sorted(adset_breakdown.items(), key=lambda x: x[1].get(lead_metric, 0), reverse=not is_ascending)
                
                # ADDITIVE: Include ALL adsets regardless of lead_form value (like age/gender handler does)
                # This allows ranking even when all adsets have 0 leads (terendah will show 0s, terbanyak will show 0s)
                # Removed filter: if not is_ascending: sorted_adsets = [(name, m) for name, m in sorted_adsets if m.get(lead_metric, 0) > 0]
                
                # Map metric to label (MOVED BEFORE if block for availability in all branches)
                metric_labels = {
                    'lead_form': 'Lead Form',
                    'wa': 'WhatsApp Leads',
                    'fb_leads': 'Facebook Leads'
                }
                metric_label = metric_labels.get(lead_metric, lead_metric)
                
                if sorted_adsets:
                    answer_lines = [f"Berikut ranking adset berdasarkan {metric_label} {order_text}{f' untuk {period_text}' if period_text else ''}:\n"]
                    
                    for i, (adset_name, metrics) in enumerate(sorted_adsets[:10], 1):
                        lead_count = int(metrics.get(lead_metric, 0))
                        cost = int(metrics.get('cost', 0))
                        clicks = int(metrics.get('clicks', 0))
                        
                        # Calculate cost per lead if applicable
                        if lead_count > 0:
                            cost_per_lead = cost / lead_count if lead_count > 0 else 0
                            answer_lines.append(f"{i}. **{adset_name}**: {lead_count} {metric_label} | Cost: Rp {cost:,} | Cost/Lead: Rp {cost_per_lead:,.0f}")
                        else:
                            answer_lines.append(f"{i}. **{adset_name}**: {lead_count} {metric_label} | Cost: Rp {cost:,}")
                    
                    llm_answer = "\n".join(answer_lines)
                    print(f"[DEBUG] Generated answer for adset lead metric ranking query")
                    return state.copy(update={"llm_answer": llm_answer})
                else:
                    llm_answer = f"Tidak ada adset dengan {metric_label} {order_text}{f' untuk {period_text}' if period_text else ''}."
                    return state.copy(update={"llm_answer": llm_answer})
            else:
                llm_answer = "Tidak ditemukan data adset untuk analisis lead form."
                return state.copy(update={"llm_answer": llm_answer})
        except Exception as e:
            print(f"[ERROR] NEW HANDLER exception: {e}")
            import traceback
            traceback.print_exc()
            llm_answer = f"Terjadi error saat memproses query lead form: {str(e)}"
            return state.copy(update={"llm_answer": llm_answer})
    
    # ADDITIVE: Handle query "kelompok age/gender X menghasilkan metric Y di adset mana?"
    # Pattern: age/gender filter + ranking by adset
    
    # Detect pattern: "kelompok ... di adset mana" or "... terbanyak di adset mana"
    if ("di adset mana" in question or "adset mana" in question) and any(kw in question for kw in ["kelompok", "usia", "age", "laki", "pria", "male", "wanita", "female", "perempuan"]):
        print("[DEBUG] Detected query: age/gender filter + ranking by adset")
        
        # Extract age range
        age_match = re.search(r'(\d{2}[-–]\d{2})', question)
        age_range = age_match.group(1).replace('–', '-') if age_match else None
        
        # Extract gender
        gender = None
        if any(w in question for w in ["laki-laki", "laki", "pria", "male"]):
            gender = "male"
        elif any(w in question for w in ["wanita", "perempuan", "female"]):
            gender = "female"
        
        # Extract metric (clicks, leads, cost, impressions, CTR, CPWA, etc.)
        # ADDITIVE: Expanded metric_map to include ALL metrics (CTR, CPWA, CPC, CPM, CPLC, etc.)
        metric_map = {
            'ctr': 'ctr',
            'click through rate': 'ctr',
            'click-through rate': 'ctr',
            'lctr': 'lctr',
            'link ctr': 'lctr',
            'link click through rate': 'lctr',
            'cpwa': 'cpwa',
            'cost per whatsapp': 'cpwa',
            'cost per wa': 'cpwa',
            'biaya per wa': 'cpwa',
            'cpc': 'cpc',
            'cost per click': 'cpc',
            'biaya per klik': 'cpc',
            'cpm': 'cpm',
            'cost per mille': 'cpm',
            'biaya per seribu': 'cpm',
            'cplc': 'cplc',
            'cost per link click': 'cplc',
            'biaya per link click': 'cplc',
            'cpf': 'cpf',
            'cost per form': 'cpf',
            'biaya per form': 'cpf',
            'klik': 'clicks',
            'click': 'clicks',
            'clicks': 'clicks',
            'lead': 'fb_leads',
            'leads': 'fb_leads',
            'konversi': 'fb_leads',
            'cost': 'cost',
            'biaya': 'cost',
            'spend': 'cost',
            'pengeluaran': 'cost',
            'impresi': 'impr',
            'impression': 'impr',
            'impressions': 'impr',
            'tayangan': 'impr',
            'jangkauan': 'reach',
            'reach': 'reach',
            'frequency': 'frequency',
            'frekuensi': 'frequency'
        }
        
        detected_metric = 'clicks'  # default
        for kw, metric_key in metric_map.items():
            if kw in question.lower():
                detected_metric = metric_key
                print(f"[DEBUG] Detected metric in age/gender+adset query: '{kw}' -> '{metric_key}'")
                break
        
        print(f"[DEBUG] Extracted: age_range={age_range}, gender={gender}, metric={detected_metric}")
        
        # Aggregate by adset filtered by age/gender
        adset_data = aggregate_adset_by_age_gender(state.sheet_data, age_range=age_range, gender=gender)
        
        if adset_data:
            # Sort by metric descending
            sorted_adsets = sorted(adset_data.items(), key=lambda x: x[1].get(detected_metric, 0), reverse=True)
            
            # Build answer
            age_text = f"usia {age_range}" if age_range else "semua usia"
            gender_text = "laki-laki" if gender == "male" else "wanita" if gender == "female" else "semua gender"
            
            # ADDITIVE: Expanded metric_text mapping to include ALL metrics
            metric_text_map = {
                'clicks': 'klik',
                'fb_leads': 'leads',
                'cost': 'cost',
                'impr': 'impressions',
                'reach': 'reach',
                'ctr': 'CTR',
                'lctr': 'LCTR',
                'cpwa': 'CPWA',
                'cpc': 'CPC',
                'cpm': 'CPM',
                'cplc': 'CPLC',
                'cpf': 'CPF',
                'frequency': 'frequency',
                'wa': 'WhatsApp'
            }
            metric_text = metric_text_map.get(detected_metric, detected_metric.upper())
            
            answer_lines = [
                f"Berdasarkan data untuk kelompok **{gender_text} {age_text}**:\n",
                f"**Ranking Adset Berdasarkan {metric_text.upper()}:**\n"
            ]
            
            # Show top 5 adsets
            for i, (adset_name, metrics) in enumerate(sorted_adsets[:5], 1):
                value = metrics.get(detected_metric, 0)
                cost = metrics.get('cost', 0)
                answer_lines.append(f"{i}. **{adset_name}**: {value:,.0f} {metric_text} (Cost: Rp {cost:,.0f})")
            
            llm_answer = "\n".join(answer_lines)
            print(f"[DEBUG] Generated answer for age/gender + adset ranking query")
            return state.copy(update={"llm_answer": llm_answer})
        else:
            llm_answer = f"Tidak ditemukan data untuk kelompok {gender_text if gender else 'semua gender'} {age_text if age_range else 'semua usia'}."
            return state.copy(update={"llm_answer": llm_answer})
    
    # Jika pertanyaan meminta daftar ad set, jawab eksplisit
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
    
    # ADDITIVE: Include daily stats for date-specific queries
    # Check if query asks for specific date ("tanggal dengan...")
    question_lower = question.lower() if question else ""
    if "tanggal" in question_lower or "hari" in question_lower or "date" in question_lower:
        # PRIORITY 1: Use period_stats_daily (has full metrics including leads)
        period_stats_daily = getattr(state, 'period_stats_daily', None)
        if period_stats_daily and isinstance(period_stats_daily, dict) and len(period_stats_daily) > 0:
            print(f"[DEBUG] LLM_SUMMARY: period_stats_daily tersedia dengan {len(period_stats_daily)} days")
            
            # ADDITIVE: Smart filtering based on query temporal context
            from datetime import datetime, timedelta
            import re
            
            # Default: 30 days recent (increased from 15 for better coverage)
            max_days = 30
            filtered_days = None
            
            # SMART FILTER 1: Specific date mentioned (e.g., "2025-08-01")
            date_match = re.search(r'20\d{2}-\d{2}-\d{2}', question_lower)
            if date_match:
                target_date_str = date_match.group(0)
                try:
                    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
                    print(f"[DEBUG] LLM_SUMMARY: Detected specific date: {target_date}")
                    # Send ±7 days around target date (14 days total)
                    start_date = target_date - timedelta(days=7)
                    end_date = target_date + timedelta(days=7)
                    filtered_days = {k: v for k, v in period_stats_daily.items() 
                                   if start_date <= k <= end_date}
                    print(f"[DEBUG] LLM_SUMMARY: Filtered to ±7 days around {target_date}: {len(filtered_days)} days")
                except:
                    pass
            
            # SMART FILTER 2: Month mentioned (e.g., "Agustus", "September")
            if not filtered_days:
                month_keywords = {
                    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
                    'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
                    'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
                    'january': 1, 'february': 2, 'march': 3, 'may': 5,
                    'june': 6, 'july': 7, 'august': 8, 'september': 9,
                    'october': 10, 'november': 11, 'december': 12
                }
                for month_name, month_num in month_keywords.items():
                    if month_name in question_lower:
                        print(f"[DEBUG] LLM_SUMMARY: Detected month: {month_name} ({month_num})")
                        # Filter to all days in that month
                        filtered_days = {k: v for k, v in period_stats_daily.items() 
                                       if k.month == month_num}
                        print(f"[DEBUG] LLM_SUMMARY: Filtered to month {month_num}: {len(filtered_days)} days")
                        break
            
            # SMART FILTER 3: Week mentioned (handled by existing temporal filter, just take reasonable range)
            if not filtered_days and ("minggu" in question_lower or "week" in question_lower):
                print(f"[DEBUG] LLM_SUMMARY: Detected week query, using 45 days for context")
                max_days = 45  # Extend to ~6 weeks for week queries
            
            # FALLBACK: Use default max_days (30 or 45) if no specific filter applied
            if not filtered_days:
                print(f"[DEBUG] LLM_SUMMARY: No specific temporal filter, using last {max_days} days")
                sorted_all = sorted(period_stats_daily.items(), key=lambda x: x[0], reverse=True)
                filtered_days = dict(sorted_all[:max_days])
            
            # Generate summary from filtered days
            daily_summary = f"\n\nDaily Performance Breakdown ({len(filtered_days)} days):\n"
            # Sort by date descending
            sorted_days = sorted(filtered_days.items(), key=lambda x: x[0], reverse=True)
            for day, m in sorted_days:
                daily_summary += (
                    f"  - {day}: Cost={m.get('cost', 0):.0f}, Leads={m.get('fb_leads', 0):.0f}, "
                    f"Reach={m.get('reach', 0):.0f}, Clicks={m.get('link', 0):.0f}, "
                    f"CTR={m.get('ctr', 0):.2f}%, Conv Rate={m.get('conversion_rate', 0):.2f}%\n"
                )
            full_summary += daily_summary
            print(f"[DEBUG] LLM_SUMMARY: period_stats_daily (full metrics) added to context with {len(filtered_days)} days")
        else:
            # FALLBACK: Use daily_weekly (only has cost)
            daily_weekly = getattr(state, 'daily_weekly', None)
            if daily_weekly and isinstance(daily_weekly, tuple) and len(daily_weekly) >= 1:
                daily_cost = daily_weekly[0]  # daily_cost dict
                if daily_cost and isinstance(daily_cost, dict) and len(daily_cost) > 0:
                    print(f"[DEBUG] LLM_SUMMARY: daily_cost tersedia dengan {len(daily_cost)} days")
                    daily_summary = "\n\nDaily Cost Breakdown:\n"
                    # Sort by date
                    sorted_days = sorted(daily_cost.items(), key=lambda x: x[0], reverse=True)[:15]
                    for day, cost in sorted_days:
                        daily_summary += f"  - {day}: Cost={cost:.0f}\n"
                    full_summary += daily_summary
                    print(f"[DEBUG] LLM_SUMMARY: daily_cost (cost only) added to context")
                else:
                    print(f"[DEBUG] LLM_SUMMARY: daily_cost is empty or invalid")
            else:
                print(f"[DEBUG] LLM_SUMMARY: daily_weekly NOT available")
                # Add note that daily data is not available
                full_summary += "\n\nNote: Daily breakdown data is NOT available in this dataset. Data is aggregated at weekly and monthly levels only.\n"
    
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
    chat_history = getattr(state, 'chat_history', [])  # Get chat history from state
    llm_answer = llm_summarize_aggregation(full_summary, question, chat_history=chat_history)
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

def run_aggregation_workflow(sheet_data, question=None, chat_history=None):
    """
    Run aggregation workflow with optional chat history for context.
    
    ENHANCED: Added temporal filtering support (week-X, month-Y)
    
    Args:
        sheet_data: List of data rows from Google Sheets
        question: User query string
        chat_history: Optional list of previous chat messages for LLM context
    
    Returns:
        Workflow result dict with llm_answer and other aggregation data
    """
    # DEBUG: Print keys dan contoh data
    if sheet_data:
        print("[DEBUG] Kolom di sheet_data:", list(sheet_data[0].keys()))
        print("[DEBUG] 3 baris pertama sheet_data:")
        for i, row in enumerate(sheet_data[:3]):
            print(f"  Row {i+1}: {row}")
    else:
        print("[DEBUG] sheet_data kosong!")
    
    # ADDITIVE: Include chat_history in state for LLM context
    if chat_history:
        print(f"[DEBUG] Chat history provided: {len(chat_history)} messages")
    
    # ADDITIVE: Apply temporal filter BEFORE aggregation (non-breaking, new feature)
    original_data_count = len(sheet_data)
    if question:
        from services.llm_summary import detect_temporal_filter, filter_sheet_data_by_temporal
        temporal_filter = detect_temporal_filter(question)
        
        if any([temporal_filter.get("week_num"), temporal_filter.get("month_num"), temporal_filter.get("year")]):
            print(f"[DEBUG] Temporal filter detected: {temporal_filter}")
            sheet_data = filter_sheet_data_by_temporal(sheet_data, temporal_filter)
            print(f"[DEBUG] Data filtered by temporal constraint: {original_data_count} rows -> {len(sheet_data)} rows")
        else:
            print("[DEBUG] No temporal filter detected, using all data")
    
    # Pastikan question dikirim ke state agar intent detection bekerja
    state = AggregationState(
        sheet_data=sheet_data, 
        question=question,
        chat_history=chat_history if chat_history else []
    )
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
