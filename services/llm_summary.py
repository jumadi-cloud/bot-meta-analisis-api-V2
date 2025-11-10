from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import re
from datetime import datetime
from collections import defaultdict

# Inisialisasi LLM Google Gemini (atau ganti dengan model lain jika perlu)
# Pastikan environment variable GOOGLE_API_KEY sudah di-set
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# ADDITIVE: Temporal filter helpers (non-breaking, new functionality)
def detect_temporal_filter(question: str) -> dict:
    """
    Deteksi filter temporal dari pertanyaan user.
    Returns: dict dengan keys: week_num, month_name, month_num, year
    
    ADDITIVE: Fungsi baru untuk support temporal filtering per minggu/bulan
    """
    result = {"week_num": None, "month_name": None, "month_num": None, "year": None}
    question_lower = question.lower()
    
    # Deteksi minggu ke-X (week-X, minggu ke-3, w3, week 3, dll)
    week_patterns = [
        r'minggu\s*ke[-\s]*(\d+)',
        r'week[-\s]*(\d+)',
        r'w[-]?(\d+)',
        r'pekan\s*ke[-\s]*(\d+)'
    ]
    for pattern in week_patterns:
        match = re.search(pattern, question_lower)
        if match:
            result["week_num"] = int(match.group(1))
            print(f"[DEBUG] Detected week filter: week-{result['week_num']}")
            break
    
    # Deteksi bulan (Indonesia & English)
    month_map = {
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
    
    for month_name, month_num in month_map.items():
        if month_name in question_lower:
            result["month_name"] = month_name.capitalize()
            result["month_num"] = month_num
            print(f"[DEBUG] Detected month filter: {result['month_name']} (month {month_num})")
            break
    
    # Deteksi tahun (YYYY)
    year_match = re.search(r'\b(20\d{2})\b', question_lower)
    if year_match:
        result["year"] = int(year_match.group(1))
        print(f"[DEBUG] Detected year filter: {result['year']}")
    
    return result

def filter_sheet_data_by_temporal(sheet_data: list, temporal_filter: dict) -> list:
    """
    Filter sheet_data berdasarkan temporal constraint (week_num, month_num, year).
    
    ADDITIVE: Fungsi baru untuk temporal filtering (non-breaking)
    ENHANCED: More robust date column detection and format parsing
    """
    week_num = temporal_filter.get("week_num")
    month_num = temporal_filter.get("month_num")
    year = temporal_filter.get("year")
    
    if not any([week_num, month_num, year]):
        print("[DEBUG] No temporal filter detected, returning all data")
        return sheet_data
    
    filtered_data = []
    total_rows = len(sheet_data)
    
    # ENHANCED: First pass to detect date column name
    date_column_name = None
    if sheet_data and len(sheet_data) > 0:
        for key in sheet_data[0].keys():
            key_lower = str(key).lower().strip()
            # More flexible matching for date columns
            if any(date_word in key_lower for date_word in ['date', 'tanggal', 'tgl', 'day', 'dt']):
                date_column_name = key
                print(f"[DEBUG] Detected date column: '{date_column_name}'")
                break
    
    if not date_column_name:
        print(f"[WARN] No date column found in sheet_data. Available columns: {list(sheet_data[0].keys()) if sheet_data else 'none'}")
        return sheet_data  # Return all data if no date column found
    
    parse_failed_count = 0
    
    for row in sheet_data:
        date_val = row.get(date_column_name)
        
        if not date_val:
            continue
        
        # Parse tanggal
        try:
            date_str = str(date_val).strip()
            parsed_date = None
            
            # Format YYYY-MM-DD
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            # Format DD/MM/YYYY
            elif re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                parsed_date = datetime.strptime(date_str, '%d/%m/%Y')
            # Format MM/DD/YYYY (US format)
            elif re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
                try:
                    parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
                except:
                    pass
            # Format YYYY/MM/DD
            elif re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
                parsed_date = datetime.strptime(date_str, '%Y/%m/%d')
            # Format DD-MM-YYYY
            elif re.match(r'^\d{2}-\d{2}-\d{4}$', date_str):
                parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
            
            if not parsed_date:
                parse_failed_count += 1
                if parse_failed_count <= 3:  # Only log first 3 failures
                    print(f"[DEBUG] Unable to parse date format: '{date_str}'")
                continue
            
            # Apply filters
            match = True
            
            if year and parsed_date.year != year:
                match = False
            
            if month_num and parsed_date.month != month_num:
                match = False
            
            if week_num:
                # FIXED: Calculate week-of-month (1-5), not ISO week
                # Week 1 = day 1-7, Week 2 = day 8-14, Week 3 = day 15-21, etc.
                week_of_month = ((parsed_date.day - 1) // 7) + 1
                if week_of_month != week_num:
                    match = False
                    print(f"[DEBUG] Week filter mismatch: date {parsed_date.date()} is week-{week_of_month} of month, need week-{week_num}")
            
            if match:
                filtered_data.append(row)
        
        except Exception as e:
            parse_failed_count += 1
            if parse_failed_count <= 3:  # Only log first 3 failures
                print(f"[DEBUG] Failed to parse date: {date_val}, error: {e}")
            continue
    
    if parse_failed_count > 3:
        print(f"[DEBUG] Total {parse_failed_count} rows failed date parsing (only first 3 logged)")
    
    print(f"[DEBUG] Temporal filter result: {len(filtered_data)}/{total_rows} rows match (week={week_num}, month={month_num}, year={year})")
    return filtered_data

prompt_template = ChatPromptTemplate.from_template(
    """
    Anda adalah asisten analisis Facebook Ads yang profesional, proaktif, dan komunikatif.
    
    {chat_history_context}
    
    Berdasarkan hasil agregasi berikut:
    {summary}
    
    {ranking_instruction}
    
    Lakukan analisis tren performa (apakah naik, turun, atau stagnan) dari data tersebut.
    Berikan reasoning (penjelasan logis) atas tren yang Anda temukan.
    Jika performa menurun, berikan analisis penyebab dan saran konkret untuk perbaikan.
    Jika performa naik, berikan insight dan tips optimasi lanjutan agar hasil makin baik.
    Jawaban harus selalu natural, relevan, dan mudah dipahami advertiser Facebook Ads.
    Jangan mengarang jika data tidak tersedia, dan jangan memberikan informasi yang tidak ada di data.
    Jika pertanyaan user tidak bisa dijawab dari data, jawab dengan jujur dan profesional, misal: "Maaf, data yang Anda minta tidak tersedia."
    Akhiri dengan bullet point saran atau rekomendasi jika memungkinkan.
    
    PENTING: Jika ada riwayat percakapan di atas, gunakan informasi tersebut untuk memberikan jawaban yang lebih kontekstual. Misalnya, jika user sudah memperkenalkan diri atau memberikan informasi pribadi, ingat dan gunakan informasi tersebut.
    
    Pertanyaan user:
    {question}
    """
)

output_parser = StrOutputParser()

def detect_ranking_query(question: str) -> dict:
    """
    Deteksi apakah user bertanya tentang ranking (tertinggi/terendah/terbesar/terkecil).
    Returns: dict dengan keys: is_ranking, direction (highest/lowest), dimension, metric
    
    ADDITIVE: Fungsi baru untuk support ranking queries (non-breaking)
    """
    result = {
        "is_ranking": False,
        "direction": None,  # 'highest' or 'lowest'
        "dimension": None,  # 'adset', 'ad', 'region', 'age', 'gender', dll
        "metric": None      # 'cost', 'clicks', 'reach', 'ctr', dll
    }
    
    question_lower = question.lower()
    
    # Deteksi direction (tertinggi vs terendah)
    highest_patterns = ['tertinggi', 'terbesar', 'paling tinggi', 'paling besar', 'maksimal', 'max', 'highest', 'largest', 'maximum', 'top']
    lowest_patterns = ['terendah', 'terkecil', 'paling rendah', 'paling kecil', 'minimal', 'min', 'lowest', 'smallest', 'minimum', 'bottom']
    
    for pattern in highest_patterns:
        if pattern in question_lower:
            result["direction"] = "highest"
            result["is_ranking"] = True
            break
    
    if not result["is_ranking"]:
        for pattern in lowest_patterns:
            if pattern in question_lower:
                result["direction"] = "lowest"
                result["is_ranking"] = True
                break
    
    if not result["is_ranking"]:
        return result
    
    # Deteksi dimension (adset, ad, region, age, gender, dll)
    dimension_map = {
        'adset': ['adset', 'ad set', 'ad-set'],
        'ad': ['ad ', ' ad', 'iklan'],
        'region': ['region', 'wilayah', 'daerah', 'lokasi'],
        'age': ['age', 'umur', 'usia'],
        'gender': ['gender', 'jenis kelamin'],
        'campaign': ['campaign', 'kampanye']
    }
    
    for dim, patterns in dimension_map.items():
        for pattern in patterns:
            if pattern in question_lower:
                result["dimension"] = dim
                print(f"[DEBUG] Detected dimension: {dim} (pattern: {pattern})")
                break
        if result["dimension"]:
            break
    
    # Deteksi metric (cost, clicks, reach, ctr, dll)
    metric_map = {
        'cost': ['cost', 'biaya', 'spend', 'pengeluaran'],
        'reach': ['reach', 'jangkauan'],
        'impressions': ['impressions', 'impr', 'tayangan'],
        'clicks': ['clicks', 'klik'],
        'ctr': ['ctr', 'click through rate'],
        'lctr': ['lctr', 'link ctr', 'website ctr'],
        'cpwa': ['cpwa', 'cost per wa', 'cost per whatsapp'],
        'cpm': ['cpm', 'cost per mille'],
        'cpc': ['cpc', 'cost per click'],
        'leads': ['leads', 'lead', 'konversi'],
        'frequency': ['frequency', 'frekuensi']
    }
    
    for metric, patterns in metric_map.items():
        for pattern in patterns:
            if pattern in question_lower:
                result["metric"] = metric
                print(f"[DEBUG] Detected metric: {metric} (pattern: {pattern})")
                break
        if result["metric"]:
            break
    
    print(f"[DEBUG] Ranking query detection: {result}")
    return result

def llm_summarize_aggregation(summary: str, question: str, chat_history: list = None) -> str:
    """
    Generate LLM summary with optional chat history for context.
    
    ENHANCED: Added support for ranking queries and temporal filtering context
    
    Args:
        summary: Data aggregation summary
        question: User query
        chat_history: Optional list of chat messages [{"role": "User"/"LLM", "message": "...", "timestamp": "..."}]
    
    Returns:
        LLM generated response string
    """
    # Format chat history for prompt context
    chat_history_context = ""
    if chat_history and len(chat_history) > 0:
        chat_history_context = "Riwayat percakapan sebelumnya:\n"
        for msg in chat_history[-10:]:  # Only use last 10 messages to avoid token limit
            role = msg.get("role", "Unknown")
            message = msg.get("message", "")
            if role and message:
                chat_history_context += f"- {role}: {message}\n"
        chat_history_context += "\n"
    else:
        chat_history_context = ""
    
    # ADDITIVE: Detect ranking query and add instruction
    ranking_info = detect_ranking_query(question)
    ranking_instruction = ""
    
    if ranking_info["is_ranking"]:
        direction_text = "tertinggi" if ranking_info["direction"] == "highest" else "terendah"
        dimension_text = ranking_info.get("dimension", "segmen")
        metric_text = ranking_info.get("metric", "metrik")
        
        ranking_instruction = (
            f"\n**INSTRUKSI RANKING:**\n"
            f"User bertanya tentang {dimension_text} dengan {metric_text} {direction_text}.\n"
            f"PRIORITAS TINGGI: Dalam jawaban Anda, HARUS menyebutkan:\n"
            f"1. Nama {dimension_text} yang memiliki {metric_text} {direction_text}\n"
            f"2. Nilai {metric_text} tersebut (angka pasti)\n"
            f"3. Konteks temporal jika ada filter minggu/bulan (misal: 'pada minggu ke-3 Oktober')\n"
            f"4. Ranking 3-5 teratas/terbawah jika data tersedia\n\n"
            f"Contoh format jawaban yang BENAR:\n"
            f"'Adset dengan cost tertinggi pada minggu ke-3 Oktober adalah **[Nama Adset]** dengan total cost Rp [Angka].'\n\n"
        )
    
    # ADDITIVE: Detect temporal filter for context
    temporal_filter = detect_temporal_filter(question)
    if any([temporal_filter.get("week_num"), temporal_filter.get("month_num")]):
        week_text = f"minggu ke-{temporal_filter['week_num']}" if temporal_filter.get("week_num") else ""
        month_text = temporal_filter.get("month_name", "")
        period_text = f"{week_text} {month_text}".strip()
        
        if ranking_instruction:
            ranking_instruction += f"\nPERIODE FILTER: Data sudah difilter untuk {period_text}. Pastikan menyebutkan periode ini dalam jawaban.\n"
        else:
            ranking_instruction = f"\n**PERIODE FILTER:** Data sudah difilter untuk {period_text}. Sebutkan periode ini dalam jawaban Anda.\n"
    
    chain = prompt_template | llm | output_parser
    return chain.invoke({
        "summary": summary, 
        "question": question,
        "chat_history_context": chat_history_context,
        "ranking_instruction": ranking_instruction
    })
