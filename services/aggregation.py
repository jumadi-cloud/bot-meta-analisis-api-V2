"""
services/aggregation.py
Modul untuk fungsi-fungsi agregasi dan summary data campaign.
"""
from collections import defaultdict
from datetime import datetime
import re

# ============================================================================
# HELPER: Safe column fallback (handles non-string column keys from Sheets)
# ============================================================================
def col_fallback(row, names, default=0):
    """
    ADDITIVE: Safe column name fallback dengan str() conversion.
    Google Sheets dapat return column keys sebagai int/float/date, bukan hanya string.
    ALSO handles non-string items in names list (defensive programming).
    """
    for n in names:
        for k in row.keys():
            # DEFENSIVE: Both k and n must be safely converted to string
            k_str = str(k).strip().lower() if k is not None else ""
            n_str = str(n).strip().lower() if n is not None else ""
            if k_str == n_str:
                # ADDITIVE DEBUG: Log when WhatsApp column is found
                if 'whatsapp' in n_str and row[k] != 0:
                    print(f"[DEBUG col_fallback] Found {k}={row[k]} (matched with '{n}')")
                return row[k]
    return default

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

# ============================================================================
# ADDITIVE: Restore aggregate_metrics_by_worksheet (was accidentally removed)
# ============================================================================
def aggregate_metrics_by_worksheet(sheet_data):
    """
    Mengembalikan dict: {(sheet_id, worksheet): {total_cost, total_impressions, ...}}
    ADDITIVE: Function ini digunakan di chat_routes.py line 990, tidak boleh dihapus!
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

def aggregate_main_metrics(sheet_data):
    """Hitung total cost, impressions, clicks, link clicks, leads, dsb."""
    # Uses global col_fallback helper

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
            # Uses global col_fallback helper
            c = safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
            daily_cost.setdefault(tgl.date(), 0)
            daily_cost[tgl.date()] += c
            week = tgl.isocalendar()[1]
            weekly_cost.setdefault(week, 0)
            weekly_cost[week] += c
            rows_by_date[tgl.date()].append(r)
    return daily_cost, weekly_cost, rows_by_date

# ADDITIVE: Enhanced daily/weekly/monthly aggregation dengan metrik lengkap
def aggregate_by_period_enhanced(sheet_data, period='daily'):
    """
    Enhanced period agregasi dengan metrik lengkap.
    period: 'daily', 'weekly', 'monthly'
    
    Returns: dict dengan key=(date/week/month), value=dict metrik lengkap
    
    ADDITIVE: Tidak menghapus aggregate_daily_weekly_cost lama
    """
    stats = defaultdict(lambda: {
        'cost': 0,
        'wa': 0,
        'fb_leads': 0,
        'lead_form': 0,
        'impr': 0,
        'reach': 0,
        'clicks': 0,
        'link': 0,
        'cpwa': 0,
        'cpm': 0,
        'cpc': 0,
        'cplc': 0,
        'ctr': 0,
        'lctr': 0,
        'conversion_rate': 0
    })
    
    # Uses global col_fallback helper
    
    print(f"[DEBUG] aggregate_by_period_enhanced: processing {len(sheet_data)} rows, period='{period}'")
    
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
                break
        
        if not tgl:
            continue
        
        # Determine period key
        if period == 'daily':
            key = tgl.date()
        elif period == 'weekly':
            key = f"{tgl.year}-W{tgl.isocalendar()[1]:02d}"
        elif period == 'monthly':
            key = f"{tgl.year}-{tgl.month:02d}"
        else:
            key = tgl.date()  # Default to daily
        
        # Aggregate metrics
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['reach'] += safe_float(col_fallback(r, ['reach', 'Reach']))
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        stats[key]['wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
        stats[key]['fb_leads'] += safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads', 'Facebook Leads']))
        stats[key]['lead_form'] += safe_float(col_fallback(r, ['lead form', 'Lead Form', 'LeadForm']))
    
    # Calculate derived metrics
    for key, d in stats.items():
        d['cpwa'] = (d['cost'] / d['wa']) if d['wa'] > 0 else 0
        d['cpm'] = (d['cost'] / d['impr'] * 1000) if d['impr'] > 0 else 0
        d['cpc'] = (d['cost'] / d['clicks']) if d['clicks'] > 0 else 0
        d['cplc'] = (d['cost'] / d['link']) if d['link'] > 0 else 0
        d['ctr'] = (d['clicks'] / d['impr'] * 100) if d['impr'] > 0 else 0
        d['lctr'] = (d['link'] / d['impr'] * 100) if d['impr'] > 0 else 0
        
        total_leads = d['wa'] + d['fb_leads'] + d['lead_form']
        d['conversion_rate'] = (total_leads / d['clicks'] * 100) if d['clicks'] > 0 else 0
    
    print(f"[DEBUG] aggregate_by_period_enhanced: found {len(stats)} unique periods")
    return stats

# ADDITIVE: Outbound clicks breakdown dan proportion analysis
def aggregate_outbound_clicks(sheet_data):
    """
    Agregasi outbound clicks per channel (WhatsApp, Website, Messaging/Form)
    Returns: dict dengan total dan proportion/percentage per channel
    
    ADDITIVE: Fungsi baru untuk analisis channel outbound clicks
    FIXED: Support kolom names dari both worksheets (age gender & region)
    """
    stats = {
        'whatsapp': 0,
        'website': 0,
        'messaging': 0,
        'form': 0,
        'total': 0,
        'proportion': {}  # Akan diisi dengan percentage
    }
    
    # Uses global col_fallback helper
    
    print(f"[DEBUG] aggregate_outbound_clicks: processing {len(sheet_data)} rows")
    
    for r in sheet_data:
        # WhatsApp outbound clicks - Support both "WhatsApp Leads" (age/gender) and actual "WhatsApp" columns
        stats['whatsapp'] += safe_float(col_fallback(r, [
            'outbound clicks - whatsapp', 'Outbound Clicks - WhatsApp',
            'whatsapp', 'WhatsApp', 'whatsapp leads', 'WhatsApp Leads',
            'whatsapp clicks', 'WhatsApp Clicks'
        ]))
        
        # Website outbound clicks - Support "Link Clicks" (from both worksheets)
        stats['website'] += safe_float(col_fallback(r, [
            'outbound clicks - website', 'Outbound Clicks - Website',
            'link clicks', 'Link Clicks',
            'website clicks', 'Website Clicks'
        ]))
        
        # Messaging outbound clicks - Support "Messaging Conversations Started" (from age/gender)
        stats['messaging'] += safe_float(col_fallback(r, [
            'outbound clicks - messaging', 'Outbound Clicks - Messaging',
            'messaging conversations started', 'Messaging Conversations Started',
            'messaging clicks', 'Messaging Clicks'
        ]))
        
        # Form clicks (if exists) - Support "Lead Form (On-Facebook)"
        stats['form'] += safe_float(col_fallback(r, [
            'outbound clicks - form', 'Outbound Clicks - Form',
            'lead form (on-facebook)', 'Lead Form (On-Facebook)',
            'form clicks', 'Form Clicks'
        ]))
    
    # Calculate total and proportions
    stats['total'] = stats['whatsapp'] + stats['website'] + stats['messaging'] + stats['form']
    
    if stats['total'] > 0:
        stats['proportion']['whatsapp'] = (stats['whatsapp'] / stats['total'] * 100)
        stats['proportion']['website'] = (stats['website'] / stats['total'] * 100)
        stats['proportion']['messaging'] = (stats['messaging'] / stats['total'] * 100)
        stats['proportion']['form'] = (stats['form'] / stats['total'] * 100)
    else:
        stats['proportion'] = {'whatsapp': 0, 'website': 0, 'messaging': 0, 'form': 0}
    
    print(f"[DEBUG] aggregate_outbound_clicks: total={stats['total']}, WhatsApp={stats['whatsapp']}, Website={stats['website']}, Messaging={stats['messaging']}, Form={stats['form']}")
    return stats

def aggregate_breakdown(sheet_data, by="Ad set"):
    stats = defaultdict(lambda: {'cost':0,'wa':0,'cpwa':0,'impr':0,'clicks':0,'link':0,'ctr':0,'lctr':0})
    # Uses global col_fallback helper

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
    stats = defaultdict(lambda: {'cost':0,'wa':0,'cpwa':0,'impr':0,'clicks':0,'link':0,'ctr':0,'lctr':0,'fb':0,'lead_form':0,'frequency':0,'reach':0,'cpm':0,'cpc':0,'cplc':0})
    # Uses global col_fallback helper
    
    # ADDITIVE DEBUG: Print first row keys to check column names
    if sheet_data and len(sheet_data) > 0:
        print(f"[DEBUG aggregate_age_gender] First row keys: {list(sheet_data[0].keys())}")

    for r in sheet_data:
        age = r.get('Age', 'Unknown')
        gender = r.get('Gender', 'Unknown')
        key = f"{age}|{gender}"
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        # ADDITIVE: Extended WhatsApp column fallback - include Messaging Conversations and Offsite Leads
        wa_value = safe_float(col_fallback(r, [
            'whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads',
            'messaging conversations started', 'Messaging Conversations Started',
            'messaging conversations', 'Messaging Conversations',  # ADDITIVE: Shorter variant
            'leads (offsite/pixels)', 'Leads (Offsite/Pixels)',
            'offsite leads', 'Offsite Leads',
            'on-facebook leads', 'On-Facebook Leads'  # ADDITIVE: Facebook leads juga dihitung sebagai WA leads alternative
        ]))
        stats[key]['wa'] += wa_value
        # ADDITIVE: Facebook leads (On-Facebook Leads)
        fb_value = safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads', 'facebook leads', 'Facebook Leads']))
        stats[key]['fb'] += fb_value
        # ADDITIVE: Lead Form
        lead_form_value = safe_float(col_fallback(r, ['lead form', 'Lead Form', 'LeadForm']))
        stats[key]['lead_form'] += lead_form_value
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        stats[key]['frequency'] += safe_float(col_fallback(r, ['frequency', 'Frequency']))
        stats[key]['reach'] += safe_float(col_fallback(r, ['reach', 'Reach']))
    
    for key, d in stats.items():
        d['cpwa'] = (d['cost']/d['wa']) if d['wa'] else 0
        d['ctr'] = (d['clicks']/d['impr']*100) if d['impr'] else 0
        d['lctr'] = (d['link']/d['impr']*100) if d['impr'] else 0
        d['cpm'] = (d['cost']/d['impr']*1000) if d['impr'] else 0
        d['cpc'] = (d['cost']/d['clicks']) if d['clicks'] else 0
        d['cplc'] = (d['cost']/d['link']) if d['link'] else 0
    
    # ADDITIVE DEBUG: Print aggregated results to check WA leads
    print(f"[DEBUG aggregate_age_gender] Aggregated {len(stats)} segments")
    for key, d in list(stats.items())[:3]:  # Print first 3 segments
        print(f"[DEBUG aggregate_age_gender]   {key}: cost={d['cost']:.0f}, wa={d['wa']:.0f}, lead_form={d['lead_form']:.0f}, cpwa={d['cpwa']:.0f}")
    
    return stats

# ADDITIVE: Enhanced age & gender aggregation dengan metrik lengkap
def aggregate_age_gender_enhanced(sheet_data, adset_name=None):
    """
    Enhanced age & gender agregasi dengan metrik tambahan:
    - Reach, Frequency
    - CPM, CPC, CPLC
    - Website CTR
    - Lead Form, Facebook Leads
    - Conversion Rate
    
    ADDITIVE: Tidak menghapus aggregate_age_gender lama, ini versi enhanced
    ADDITIVE: Parameter adset_name optional (default None = semua adset)
    
    Args:
        sheet_data: List of data rows
        adset_name: Optional filter untuk adset spesifik (default: None, include all adsets)
    
    Returns:
        Dict dengan key=age|gender, value=dict metrik
    """
    stats = defaultdict(lambda: {
        'cost': 0,
        'wa': 0,           # WhatsApp leads
        'fb_leads': 0,     # Facebook leads
        'lead_form': 0,    # Lead Form
        'impr': 0,         # Impressions
        'reach': 0,        # Reach
        'freq_sum': 0,     # Frequency sum
        'freq_count': 0,   # Frequency count
        'clicks': 0,       # All clicks
        'link': 0,         # Link clicks
        # Derived metrics
        'cpwa': 0,
        'cpm': 0,
        'cpc': 0,
        'cplc': 0,
        'ctr': 0,
        'lctr': 0,         # Website CTR
        'frequency': 0,
        'conversion_rate': 0
    })
    
    # Uses global col_fallback helper
    
    # ADDITIVE: Filter by adset_name if provided (non-breaking, optional parameter)
    if adset_name:
        print(f"[DEBUG] aggregate_age_gender_enhanced: filtering by adset_name='{adset_name}'")
        original_count = len(sheet_data)
        sheet_data = [r for r in sheet_data if str(r.get('Ad set', r.get('Ad Set', r.get('Adset', '')))).lower() == adset_name.lower()]
        print(f"[DEBUG] aggregate_age_gender_enhanced: filtered {original_count} rows -> {len(sheet_data)} rows matching adset")
        if len(sheet_data) == 0:
            print(f"[WARN] aggregate_age_gender_enhanced: No data found for adset '{adset_name}'")
            return {}  # Return empty dict if no matching adset
    
    print(f"[DEBUG] aggregate_age_gender_enhanced: processing {len(sheet_data)} rows")
    
    # ADDITIVE DEBUG: Print first row keys to check column names
    if sheet_data and len(sheet_data) > 0:
        print(f"[DEBUG aggregate_age_gender_enhanced] First row keys: {list(sheet_data[0].keys())}")
    
    for r in sheet_data:
        age = r.get('Age', 'Unknown')
        gender = r.get('Gender', 'Unknown')
        key = f"{age}|{gender}"
        
        # Core metrics
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['reach'] += safe_float(col_fallback(r, ['reach', 'Reach']))
        
        # Frequency
        freq_val = safe_float(col_fallback(r, ['frequency', 'Frequency']))
        if freq_val > 0:
            stats[key]['freq_sum'] += freq_val
            stats[key]['freq_count'] += 1
        
        # Clicks
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        
        # Leads
        # ADDITIVE: Extended WhatsApp column fallback - include Messaging Conversations and Offsite Leads  
        wa_value = safe_float(col_fallback(r, [
            'whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads',
            'messaging conversations started', 'Messaging Conversations Started',
            'messaging conversations', 'Messaging Conversations',  # ADDITIVE: Shorter variant
            'leads (offsite/pixels)', 'Leads (Offsite/Pixels)',
            'offsite leads', 'Offsite Leads',
            'on-facebook leads', 'On-Facebook Leads'  # ADDITIVE: Facebook leads juga dihitung sebagai WA leads alternative
        ]))
        stats[key]['wa'] += wa_value
        stats[key]['fb_leads'] += safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads', 'Facebook Leads']))
        stats[key]['lead_form'] += safe_float(col_fallback(r, ['lead form', 'Lead Form', 'LeadForm']))
    
    # Calculate derived metrics
    for key, d in stats.items():
        # Cost metrics
        d['cpwa'] = (d['cost'] / d['wa']) if d['wa'] > 0 else 0
        d['cpm'] = (d['cost'] / d['impr'] * 1000) if d['impr'] > 0 else 0
        d['cpc'] = (d['cost'] / d['clicks']) if d['clicks'] > 0 else 0
        d['cplc'] = (d['cost'] / d['link']) if d['link'] > 0 else 0
        
        # Rate metrics
        d['ctr'] = (d['clicks'] / d['impr'] * 100) if d['impr'] > 0 else 0
        d['lctr'] = (d['link'] / d['impr'] * 100) if d['impr'] > 0 else 0  # Website CTR
        
        # Frequency average
        d['frequency'] = (d['freq_sum'] / d['freq_count']) if d['freq_count'] > 0 else 0
        
        # Conversion rate
        total_leads = d['wa'] + d['fb_leads'] + d['lead_form']
        d['conversion_rate'] = (total_leads / d['clicks'] * 100) if d['clicks'] > 0 else 0
    
    print(f"[DEBUG] aggregate_age_gender_enhanced: found {len(stats)} unique age|gender segments")
    
    # ADDITIVE DEBUG: Print first 3 segments to check WA leads
    for key, d in list(stats.items())[:3]:
        print(f"[DEBUG aggregate_age_gender_enhanced]   {key}: cost={d['cost']:.0f}, wa={d['wa']:.0f}, cpwa={d['cpwa']:.0f}")
    
    return stats

# Additive: agregasi tren CTR per bulan untuk setiap kombinasi age|gender
def aggregate_age_gender_monthly(sheet_data):
    """
    Mengembalikan dict: {(age|gender, yyyy-mm): {cost, impr, clicks, ctr, ...}}
    """
    stats = defaultdict(lambda: {'cost':0,'wa':0,'impr':0,'clicks':0,'link':0})
    # Uses global col_fallback helper

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
    
    # Uses global col_fallback helper
    
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

# ADDITIVE: Enhanced aggregate_breakdown untuk support reach, frequency, CPM, CPC, CPLC, website CTR
def aggregate_breakdown_enhanced(sheet_data, by="Ad set"):
    """
    Enhanced breakdown agregasi dengan metrik tambahan:
    - Reach, Frequency
    - CPM (Cost Per Mille), CPC (Cost Per Click), CPLC (Cost Per Link Click)
    - Website CTR (Link CTR)
    - Lead Form counts
    - Facebook Leads counts
    - Outbound clicks breakdown
    
    ADDITIVE: Tidak menghapus aggregate_breakdown lama, ini versi enhanced
    """
    stats = defaultdict(lambda: {
        'cost': 0,
        'wa': 0,           # WhatsApp leads
        'fb_leads': 0,     # Facebook leads
        'lead_form': 0,    # Lead Form
        'impr': 0,         # Impressions
        'reach': 0,        # Reach
        'freq_sum': 0,     # Frequency sum (for averaging)
        'freq_count': 0,   # Frequency count (for averaging)
        'clicks': 0,       # All clicks
        'link': 0,         # Link clicks
        'outbound_wa': 0,  # WhatsApp outbound clicks
        'outbound_web': 0, # Website outbound clicks
        'outbound_msg': 0, # Messaging outbound clicks
        # Derived metrics (calculated later)
        'cpwa': 0,         # Cost Per WhatsApp Lead
        'cpm': 0,          # Cost Per Mille (1000 impressions)
        'cpc': 0,          # Cost Per Click
        'cplc': 0,         # Cost Per Link Click
        'ctr': 0,          # Click Through Rate
        'lctr': 0,         # Link Click Through Rate (Website CTR)
        'frequency': 0,    # Average frequency
        'conversion_rate': 0  # Leads / Clicks ratio
    })
    
    # Uses global col_fallback helper (THIS IS THE ONE THAT WAS CRASHING AT LINE 599)
    
    print(f"[DEBUG] aggregate_breakdown_enhanced: processing {len(sheet_data)} rows, grouping by '{by}'")
    if sheet_data and len(sheet_data) > 0:
        first_row = sheet_data[0]
        first_keys = list(first_row.keys())
        print(f"[DEBUG] aggregate_breakdown_enhanced: First row has {len(first_keys)} columns")
        # Only print column names if trying "Ad set" to avoid spam
        if by and "set" in by.lower():
            print(f"[DEBUG] aggregate_breakdown_enhanced: Columns include: {first_keys[:10]}...")  # First 10 only
    
    # Build list of column name variants to try (ADDITIVE: more variants for robustness)
    column_variants = [by, by.title(), by.lower()]
    if ' ' in by:
        underscore_variant = by.replace(' ', '_')
        column_variants.extend([underscore_variant, underscore_variant.title(), underscore_variant.lower()])
    if ' ' in by:
        no_space_variant = by.replace(' ', '')
        column_variants.extend([no_space_variant, no_space_variant.title(), no_space_variant.lower()])
    column_variants = list(dict.fromkeys(column_variants))
    if by and "set" in by.lower():
        print(f"[DEBUG] aggregate_breakdown_enhanced: Trying column variants: {column_variants}")
    
    for r in sheet_data:
        # Try all variants
        key = None
        for col_var in column_variants:
            key = r.get(col_var)
            if key:
                break
        if not key:
            key = 'Unknown'
        
        # Core metrics
        stats[key]['cost'] += safe_float(col_fallback(r, ['cost', 'biaya', 'Cost', 'COST', 'Biaya']))
        stats[key]['impr'] += safe_float(col_fallback(r, ['impressions', 'Impressions', 'IMP', 'imp']))
        stats[key]['reach'] += safe_float(col_fallback(r, ['reach', 'Reach']))
        
        # Frequency (untuk averaging)
        freq_val = safe_float(col_fallback(r, ['frequency', 'Frequency']))
        if freq_val > 0:
            stats[key]['freq_sum'] += freq_val
            stats[key]['freq_count'] += 1
        
        # Clicks
        stats[key]['clicks'] += safe_float(col_fallback(r, ['all clicks', 'clicks all', 'All Clicks', 'Clicks all', 'clicks', 'Clicks']))
        stats[key]['link'] += safe_float(col_fallback(r, ['link clicks', 'Link Clicks', 'link', 'Link']))
        
        # Leads
        stats[key]['wa'] += safe_float(col_fallback(r, ['whatsapp', 'whatsapp leads', 'WhatsApp', 'WhatsApp Leads']))
        stats[key]['fb_leads'] += safe_float(col_fallback(r, ['on-facebook leads', 'On-Facebook Leads', 'Facebook Leads']))
        stats[key]['lead_form'] += safe_float(col_fallback(r, ['lead form', 'Lead Form', 'LeadForm']))
        
        # Outbound clicks breakdown
        stats[key]['outbound_wa'] += safe_float(col_fallback(r, ['outbound clicks - whatsapp', 'Outbound Clicks - WhatsApp', 'whatsapp clicks']))
        stats[key]['outbound_web'] += safe_float(col_fallback(r, ['outbound clicks - website', 'Outbound Clicks - Website', 'website clicks']))
        stats[key]['outbound_msg'] += safe_float(col_fallback(r, ['outbound clicks - messaging', 'Outbound Clicks - Messaging']))
    
    # Calculate derived metrics
    for key, d in stats.items():
        # Cost metrics
        d['cpwa'] = (d['cost'] / d['wa']) if d['wa'] > 0 else 0
        d['cpm'] = (d['cost'] / d['impr'] * 1000) if d['impr'] > 0 else 0
        d['cpc'] = (d['cost'] / d['clicks']) if d['clicks'] > 0 else 0
        d['cplc'] = (d['cost'] / d['link']) if d['link'] > 0 else 0
        
        # Rate metrics
        d['ctr'] = (d['clicks'] / d['impr'] * 100) if d['impr'] > 0 else 0
        d['lctr'] = (d['link'] / d['impr'] * 100) if d['impr'] > 0 else 0  # Website CTR
        
        # Frequency average
        d['frequency'] = (d['freq_sum'] / d['freq_count']) if d['freq_count'] > 0 else 0
        
        # Conversion rate (total leads / clicks)
        total_leads = d['wa'] + d['fb_leads'] + d['lead_form']
        d['conversion_rate'] = (total_leads / d['clicks'] * 100) if d['clicks'] > 0 else 0
    
    print(f"[DEBUG] aggregate_breakdown_enhanced: found {len(stats)} unique values for '{by}'")
    return stats


def aggregate_adset_by_age_gender(sheet_data, age_range=None, gender=None):
    """
    ADDITIVE: Aggregate by adset, filtered by specific age/gender segment.
    
    Use case: "Kelompok laki-laki 45-54 menghasilkan klik terbanyak di adset mana?"
    → Filter rows where age=45-54 AND gender=male, then aggregate by adset
    
    Args:
        sheet_data: List of row dicts from Google Sheets
        age_range: String like "45-54", "35-44", etc. (optional)
        gender: String like "male", "female", "laki-laki", "wanita", etc. (optional)
    
    Returns:
        dict: {adset_name: {metrics...}}
    """
    print(f"[DEBUG] aggregate_adset_by_age_gender: age_range={age_range}, gender={gender}")
    print(f"[DEBUG] aggregate_adset_by_age_gender: processing {len(sheet_data)} rows")
    
    # Filter data by age/gender first
    filtered_data = []
    
    for row in sheet_data:
        # Get age and gender from row
        row_age = str(col_fallback(row, ['age', 'Age', 'AGE', 'usia', 'Usia'], '')).strip()
        row_gender = str(col_fallback(row, ['gender', 'Gender', 'GENDER', 'jenis kelamin', 'Jenis Kelamin'], '')).strip().lower()
        
        # Normalize gender
        gender_normalized = None
        if row_gender:
            if row_gender in ['male', 'laki-laki', 'pria', 'm', 'l']:
                gender_normalized = 'male'
            elif row_gender in ['female', 'wanita', 'perempuan', 'f', 'p']:
                gender_normalized = 'female'
            else:
                gender_normalized = row_gender  # unknown, etc.
        
        # Check filters
        age_match = True
        gender_match = True
        
        if age_range:
            age_match = row_age == age_range
        
        if gender:
            gender_input_normalized = gender.lower()
            if gender_input_normalized in ['male', 'laki-laki', 'pria', 'm', 'l']:
                gender_input_normalized = 'male'
            elif gender_input_normalized in ['female', 'wanita', 'perempuan', 'f', 'p']:
                gender_input_normalized = 'female'
            gender_match = gender_normalized == gender_input_normalized
        
        if age_match and gender_match:
            filtered_data.append(row)
    
    print(f"[DEBUG] aggregate_adset_by_age_gender: filtered to {len(filtered_data)} rows (age={age_range}, gender={gender})")
    
    if len(filtered_data) == 0:
        print(f"[WARN] aggregate_adset_by_age_gender: No data found for age={age_range}, gender={gender}")
        return {}
    
    # Now aggregate filtered data by adset using existing function
    result = aggregate_breakdown_enhanced(filtered_data, by="Ad set")
    
    print(f"[DEBUG] aggregate_adset_by_age_gender: found {len(result)} adsets for age={age_range}, gender={gender}")
    return result
