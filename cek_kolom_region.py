# Script untuk cek kolom di worksheet MSA - Data - Region
from routes.sheet_routes import get_gsheet_by_id
import os
from dotenv import load_dotenv

load_dotenv()

sheet_id = os.getenv('GOOGLE_SHEET_ID')
print(f"Sheet ID: {sheet_id}")

sh = get_gsheet_by_id(sheet_id)
ws = sh.worksheet('MSA - Data - Region')
data = ws.get_all_records(head=1)

if data:
    print(f"\nTotal baris: {len(data)}")
    print(f"\nKolom yang tersedia di worksheet 'MSA - Data - Region':")
    print("-" * 80)
    for idx, col in enumerate(data[0].keys(), 1):
        print(f"{idx}. {col}")
    
    print("\n" + "=" * 80)
    print("Sample data (3 baris pertama):")
    print("=" * 80)
    for i, row in enumerate(data[:3], 1):
        print(f"\nBaris {i}:")
        for k, v in list(row.items())[:10]:  # Limit to first 10 columns for readability
            print(f"  {k}: {v}")
else:
    print("Tidak ada data di worksheet ini")
