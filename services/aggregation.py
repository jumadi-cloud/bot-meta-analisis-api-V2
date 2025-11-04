# Additive: Breakdown metrik utama per worksheet di semua file
def aggregate_metrics_by_worksheet(sheet_data):
    """
    Mengembalikan dict: {(sheet_id, worksheet): {total_cost, total_impressions, ...}}
    """
    stats = defaultdict(lambda: {
        'total_cost': 0,
        'total_impressions': 0,
        'total_clicks': 0,
        'total_link_clicks': 0,
        'total_leads_wa': 0,
        'total_leads_fb': 0,
        'total_lead_form': 0,
        'total_msg_conv': 0
    })
    # Fallbacks for column names
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default

    for r in sheet_data:
        sheet_id = r.get('sheet_id', r.get('Sheet ID', 'Unknown'))
        worksheet = r.get('worksheet', r.get('Worksheet', 'Unknown'))
        key = (sheet_id, worksheet)
        stats[key]['total_cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['total_impressions'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['total_clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['total_link_clicks'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        stats[key]['total_leads_wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
        stats[key]['total_leads_fb'] += safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads']))
        stats[key]['total_lead_form'] += safe_float(col_fallback(r, ['lead form', 'Lead Form']))
        stats[key]['total_msg_conv'] += safe_float(col_fallback(r, ['messaging conversations started', 'Messaging Conversations Started']))
    return stats
"""
services/aggregation.py
Modul untuk fungsi-fungsi agregasi dan summary data campaign.
"""
from collections import defaultdict
from datetime import datetime

# Mapping nama bulan Indonesia & Inggris ke angka bulan
MONTH_NAME_MAP = {
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
import re

def safe_float(val):
    try:
        s = str(val)
        # Ambil semua digit, titik, koma setelah prefix non-angka
        m = re.search(r"[-+]?\d[\d.,]*", s)
        if not m:
            # Fallback: jika ada angka dengan separator ribuan saja (misal 1.000.000)
            # Tangkap pola ribuan baik dengan titik maupun koma (misal 1.000.000 atau 1,000,000)
            m2 = re.search(r"(\d{1,3}(?:[.,]\d{3})+)", s)
            if m2:
                num = m2.group(1)
                # Jika hanya ada titik dan tidak ada koma, atau hanya koma dan tidak ada titik, treat as ribuan
                if ('.' in num and ',' not in num) or (',' in num and '.' not in num):
                    num = num.replace('.', '').replace(',', '')
                    return float(num)
            return 0.0
            return 0.0
        num = m.group(0)
        # Case 1: Both ',' and '.' present
        if ',' in num and '.' in num:
            if num.rfind(',') > num.rfind('.'):
                # Eropa: 1.234,56 -> 1234.56
                num = num.replace('.', '').replace(',', '.')
            else:
                # US: 1,234.56 -> 1234.56
                num = num.replace(',', '')
        # Case 2: Only ',' present
        elif ',' in num:
            if num.count(',') > 1:
                # 1,234,567 -> 1234567
                num = num.replace(',', '')
            else:
                # Satu koma, cek apakah di 3 digit terakhir (desimal) atau ribuan
                parts = num.split(',')
                if len(parts[-1]) == 3 and len(parts) > 1:
                    # 1,234 -> 1234 (ribuan)
                    num = num.replace(',', '')
                else:
                    # 4,56 -> 4.56 (desimal)
                    num = num.replace(',', '.')
        # Case 3: Only '.' present (asumsi ribuan jika semua segmen 3 digit, atau desimal jika tidak)
        elif '.' in num:
            parts = num.split('.')
            if all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
                # 1.000.000 -> 1000000 (semua segmen 3 digit, ribuan)
                num = num.replace('.', '')
        return float(num)
    except:
        return 0.0

def aggregate_main_metrics(sheet_data):
    """Hitung total cost, impressions, clicks, link clicks, leads, dsb."""
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default

    total_cost = sum(safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya'])) for r in sheet_data)
    total_impressions = sum(safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp'])) for r in sheet_data)
    total_clicks = sum(safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks'])) for r in sheet_data)
    total_link_clicks = sum(safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link'])) for r in sheet_data)
    total_leads_wa = sum(safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads'])) for r in sheet_data)
    total_leads_fb = sum(safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads'])) for r in sheet_data)
    total_lead_form = sum(safe_float(col_fallback(r, ['lead form', 'Lead Form'])) for r in sheet_data)
    total_msg_conv = sum(safe_float(col_fallback(r, ['messaging conversations started', 'Messaging Conversations Started'])) for r in sheet_data)
    return {
        'total_cost': total_cost,
        'total_impressions': total_impressions,
        'total_clicks': total_clicks,
        'total_link_clicks': total_link_clicks,
        'total_leads_wa': total_leads_wa,
        'total_leads_fb': total_leads_fb,
        'total_lead_form': total_lead_form,
        'total_msg_conv': total_msg_conv
    }

def aggregate_daily_weekly_cost(sheet_data):
    daily_cost = {}
    weekly_cost = {}
    rows_by_date = defaultdict(list)
    for r in sheet_data:
        tgl = None
        for k in r:
            if k.lower() in ["tanggal", "date", "tgl"] and r[k]:
                vstr = str(r[k])
                try:
                    if re.match(r"\d{4}-\d{2}-\d{2}", vstr):
                        tgl = datetime.strptime(vstr, "%Y-%m-%d")
                    elif re.match(r"\d{2}/\d{2}/\d{4}", vstr):
                        tgl = datetime.strptime(vstr, "%d/%m/%Y")
                except:
                    continue
        if tgl:
            def col_fallback(row, names, default=0):
                for n in names:
                    for k in row.keys():
                        if k.strip().lower() == n.strip().lower():
                            return row[k]
                return default
            c = safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
            daily_cost.setdefault(tgl.date(), 0)
            daily_cost[tgl.date()] += c
            week = tgl.isocalendar()[1]
            weekly_cost.setdefault(week, 0)
            weekly_cost[week] += c
            rows_by_date[tgl.date()].append(r)
    return daily_cost, weekly_cost, rows_by_date

def aggregate_breakdown(sheet_data, by="Ad set"):
    stats = defaultdict(lambda: {'cost':0,'wa':0,'cpwa':0,'impr':0,'clicks':0,'link':0,'ctr':0,'lctr':0})
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default

    for r in sheet_data:
        key = r.get(by, r.get(by.title(), 'Unknown'))
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
    for key, d in stats.items():
        d['cpwa'] = (d['cost']/d['wa']) if d['wa'] else 0
        d['ctr'] = (d['clicks']/d['impr']*100) if d['impr'] else 0
        d['lctr'] = (d['link']/d['impr']*100) if d['impr'] else 0
    return stats

def aggregate_age_gender(sheet_data):
    stats = defaultdict(lambda: {'cost':0,'wa':0,'cpwa':0,'impr':0,'clicks':0,'link':0,'ctr':0,'lctr':0})
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default

    for r in sheet_data:
        age = r.get('Age', 'Unknown')
        gender = r.get('Gender', 'Unknown')
        key = f"{age}|{gender}"
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
    for key, d in stats.items():
        d['cpwa'] = (d['cost']/d['wa']) if d['wa'] else 0
        d['ctr'] = (d['clicks']/d['impr']*100) if d['impr'] else 0
        d['lctr'] = (d['link']/d['impr']*100) if d['impr'] else 0
    return stats

# Additive: agregasi tren CTR per bulan untuk setiap kombinasi age|gender
def aggregate_age_gender_monthly(sheet_data):
    """
    Mengembalikan dict: {(age|gender, yyyy-mm): {cost, impr, clicks, ctr, ...}}
    """
    stats = defaultdict(lambda: {'cost':0,'wa':0,'impr':0,'clicks':0,'link':0})
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default

    for r in sheet_data:
        age = r.get('Age', 'Unknown')
        gender = r.get('Gender', 'Unknown')
        key = f"{age}|{gender}"
        # Ambil bulan dari kolom tanggal (robust: support nama bulan Indonesia/Inggris)
        tgl = None
        for k in r:
            if k.lower() in ["tanggal", "date", "tgl"] and r[k]:
                vstr = str(r[k]).strip()
                try:
                    if re.match(r"\d{4}-\d{2}-\d{2}", vstr):
                        tgl = datetime.strptime(vstr, "%Y-%m-%d")
                    elif re.match(r"\d{2}/\d{2}/\d{4}", vstr):
                        tgl = datetime.strptime(vstr, "%d/%m/%Y")
                    else:
                        # Cek jika hanya nama bulan (Indonesia/Inggris) atau "Mei 2025", "May 2025", dst
                        parts = vstr.lower().replace('.', '').split()
                        if len(parts) == 2 and parts[0] in MONTH_NAME_MAP and parts[1].isdigit():
                            tgl = datetime(int(parts[1]), MONTH_NAME_MAP[parts[0]], 1)
                        elif vstr.lower() in MONTH_NAME_MAP:
                            tgl = datetime(datetime.now().year, MONTH_NAME_MAP[vstr.lower()], 1)
                except Exception:
                    continue
        if tgl:
            month_key = f"{tgl.year}-{tgl.month:02d}"
            stat_key = (key, month_key)
            stats[stat_key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
            stats[stat_key]['wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
            stats[stat_key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
            stats[stat_key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
            stats[stat_key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
    # Hitung metrik turunan
    for stat_key, d in stats.items():
        d['cpwa'] = (d['cost']/d['wa']) if d['wa'] else 0
        d['ctr'] = (d['clicks']/d['impr']*100) if d['impr'] else 0
        d['lctr'] = (d['link']/d['impr']*100) if d['impr'] else 0
    return stats

# ADDITIVE: Agregasi breakdown per region (wilayah geografis)
def aggregate_region(sheet_data):
    """
    Agregasi metrik per region untuk analisis performa geografis.
    Returns: dict dengan key=region, value=dict metrik (cost, impressions, clicks, link_clicks, reach, frequency, cpm, cpc, ctr, lctr)
    """
    stats = defaultdict(lambda: {'cost':0,'impr':0,'clicks':0,'link':0,'reach':0,'freq':0,'cpm':0,'cpc':0,'ctr':0,'lctr':0})
    
    def col_fallback(row, names, default=0):
        for n in names:
            for k in row.keys():
                if k.strip().lower() == n.strip().lower():
                    return row[k]
        return default
    
    print(f"[DEBUG] aggregate_region: processing {len(sheet_data)} rows")
    
    for r in sheet_data:
        region = r.get('Region', r.get('region', 'Unknown'))
        if not region or str(region).strip() == '':
            region = 'Unknown'
        
        stats[region]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[region]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[region]['clicks'] += safe_float(col_fallback(r, ['clicks all', 'all clicks', 'Clicks all', 'All Clicks', 'clicks', 'Clicks']))
        stats[region]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        stats[region]['reach'] += safe_float(col_fallback(r, ['reach', 'Reach']))
        # Frequency adalah average, jadi kita sum dulu nanti average di akhir
        freq_val = safe_float(col_fallback(r, ['frequency', 'Frequency']))
        if freq_val > 0:
            stats[region]['freq'] += freq_val
    
    # Hitung metrik turunan
    for region, d in stats.items():
        d['cpm'] = (d['cost']/d['impr']*1000) if d['impr'] else 0
        d['cpc'] = (d['cost']/d['clicks']) if d['clicks'] else 0
        d['ctr'] = (d['clicks']/d['impr']*100) if d['impr'] else 0
        d['lctr'] = (d['link']/d['impr']*100) if d['impr'] else 0
        # Frequency adalah rata-rata (simplified: total freq / jumlah rows untuk region tersebut)
        # Untuk simplicity, kita pakai total frequency yang sudah di-sum (bisa di-improve later)
    
    print(f"[DEBUG] aggregate_region: found {len(stats)} unique regions")
    return stats
