# Script untuk menampilkan semua bulan unik dari sheet_data Google Sheet
from routes.sheet_routes import get_gsheet, get_worksheet
import re
import calendar

def extract_bulan(sheet_data):
    bulan_set = set()
    for row in sheet_data:
        for k, v in row.items():
            k_lower = k.lower()
            if k_lower in ["bulan", "month"] and v:
                bulan_set.add(str(v).strip())
            elif k_lower in ["tanggal", "date", "tgl"] and v:
                val = str(v)
                m = re.match(r"(\d{4})-(\d{2})-(\d{2})", val)
                if m:
                    bulan_num = int(m.group(2))
                    bulan_set.add(calendar.month_name[bulan_num])
                m = re.match(r"(\d{2})/(\d{2})/(\d{4})", val)
                if m:
                    bulan_num = int(m.group(2))
                    bulan_set.add(calendar.month_name[bulan_num])
    return sorted(list(bulan_set))

if __name__ == "__main__":
    sh = get_gsheet()
    ws = get_worksheet(sh, 'work1')
    sheet_data = ws.get_all_records(head=1)
    bulan_list = extract_bulan(sheet_data)
    print("Bulan unik yang ditemukan di sheet_data:")
    for b in bulan_list:
        print("-", b)
