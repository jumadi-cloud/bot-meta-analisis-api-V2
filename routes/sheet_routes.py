def get_gsheet_by_id(sheet_id):
    import time
    print(f'[DEBUG] get_gsheet_by_id: mulai untuk sheet_id={sheet_id}')
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f'[DEBUG] get_gsheet_by_id: percobaan ke-{attempt+1} untuk sheet_id={sheet_id}')
            if not sheet_id:
                print('[DEBUG] get_gsheet_by_id: sheet_id tidak diberikan')
                raise Exception("sheet_id tidak diberikan")
            print('[DEBUG] get_gsheet_by_id: memanggil get_gsheet_creds()')
            creds = get_gsheet_creds()
            print('[DEBUG] get_gsheet_by_id: sukses get_gsheet_creds()')
            print('[DEBUG] get_gsheet_by_id: memanggil gspread.authorize')
            gc = gspread.authorize(creds)
            print('[DEBUG] get_gsheet_by_id: sukses gspread.authorize')
            print(f'[DEBUG] get_gsheet_by_id: memanggil gc.open_by_key({sheet_id})')
            sh = gc.open_by_key(sheet_id)
            print('[DEBUG] get_gsheet_by_id: sukses gc.open_by_key')
            _ = sh.title
            print(f"Successfully connected to Google Sheet: {sh.title}")
            return sh
        except Exception as e:
            print(f"[ERROR] get_gsheet_by_id: percobaan ke-{attempt+1} gagal untuk sheet_id={sheet_id}: {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise Exception(f"Gagal mengakses Google Sheet {sheet_id} setelah {max_retries} percobaan: {e}")
from flask import Blueprint, request, jsonify
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load .env file
load_dotenv()

sheet_bp = Blueprint('sheet', __name__)

# --- Helper & utilitas Google Sheet ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Fungsi kredensial dan akses sheet (bisa di-refactor ke services nanti)
def get_gsheet_creds():
    try:
        required_fields = ["GOOGLE_PROJECT_ID", "GOOGLE_PRIVATE_KEY", "GOOGLE_CLIENT_EMAIL"]
        missing_fields = [field for field in required_fields if not os.getenv(field)]
        if missing_fields:
            raise Exception(f"Missing required Google credentials: {', '.join(missing_fields)}")
        private_key = os.getenv("GOOGLE_PRIVATE_KEY")
        if private_key:
            private_key = private_key.replace('\\n', '\n')
            if not private_key.startswith('-----BEGIN'):
                raise Exception("Invalid private key format")
        info = {
            "type": os.getenv("GOOGLE_TYPE", "service_account"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": private_key,
            "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "auth_uri": os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
        }
        info = {k: v for k, v in info.items() if v is not None}
        return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    except Exception as e:
        print(f"Error creating Google credentials: {e}")
        raise Exception(f"Gagal membuat kredensial Google: {e}")

def get_gsheet(sheet_id=None):
    import time
    max_retries = 3
    sheet_key = sheet_id or GOOGLE_SHEET_ID
    for attempt in range(max_retries):
        try:
            if not sheet_key:
                raise Exception("GOOGLE_SHEET_ID tidak ditemukan di environment variables dan tidak diberikan sheet_id parameter")
            creds = get_gsheet_creds()
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(sheet_key)
            _ = sh.title
            print(f"Successfully connected to Google Sheet: {sh.title}")
            return sh
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise Exception(f"Gagal mengakses Google Sheet setelah {max_retries} percobaan: {e}")

def get_worksheet(sh, sheet_name='work1'):
    try:
        return sh.worksheet(sheet_name)
    except Exception as e:
        print(f"Failed to get worksheet '{sheet_name}': {e}")
        try:
            worksheets = sh.worksheets()
            if worksheets:
                print(f"Using first available worksheet: {worksheets[0].title}")
                return worksheets[0]
        except Exception as e2:
            print(f"Failed to get any worksheet: {e2}")
        raise Exception(f"Tidak dapat mengakses worksheet '{sheet_name}' atau worksheet lainnya: {e}")

# --- Endpoint Sheet ---
@sheet_bp.route('/sheet/read', methods=['GET'])
def sheet_read():
    try:
        sheet_id = request.args.get('sheet_id')
        sh = get_gsheet(sheet_id=sheet_id)
        ws = get_worksheet(sh, 'work1')
        data = ws.get_all_records(head=1)
        return jsonify({
            "data": data,
            "total_records": len(data),
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@sheet_bp.route('/sheet/info', methods=['GET'])
def sheet_info():
    try:
        sh = get_gsheet()
        ws = get_worksheet(sh, 'work1')
        all_data = ws.get_all_records(head=1)
        sheet_info = {
            "sheet_title": sh.title,
            "worksheet_title": ws.title,
            "total_rows": len(all_data),
            "total_columns": len(all_data[0].keys()) if all_data else 0,
            "columns": list(all_data[0].keys()) if all_data else [],
            "row_count": ws.row_count,
            "col_count": ws.col_count,
            "success": True
        }
        return jsonify(sheet_info)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@sheet_bp.route('/sheet/write', methods=['POST'])
def sheet_write():
    try:
        sh = get_gsheet()
        ws = get_worksheet(sh, 'work1')
        req = request.get_json()
        row = req.get("row")
        if not row:
            return jsonify({"error": "Data 'row' harus diisi."}), 400
        ws.append_row(row)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sheet_bp.route('/test_connection', methods=['GET'])
def test_connection():
    try:
        creds = get_gsheet_creds()
        sh = get_gsheet()
        ws = get_worksheet(sh, 'work1')
        test_data = ws.get_all_values()
        return jsonify({
            "success": True,
            "message": "Koneksi Google Sheet berhasil",
            "sheet_title": sh.title,
            "worksheet_title": ws.title,
            "total_rows": len(test_data),
            "sample_data": test_data[:3] if test_data else []
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Gagal koneksi ke Google Sheet"
        }), 500

@sheet_bp.route('/test_data_access', methods=['GET'])
def test_data_access():
    try:
        sh = get_gsheet()
        ws = get_worksheet(sh, 'work1')
        method1_data = []
        method2_data = []
        try:
            method1_data = ws.get_all_records()
        except Exception as e:
            print(f"Method 1 error: {e}")
        try:
            method2_data = ws.get_all_values()
        except Exception as e:
            print(f"Method 2 error: {e}")
        last_row = ws.row_count
        last_col = ws.col_count
        test_result = {
            "success": True,
            "sheet_title": sh.title,
            "worksheet_title": ws.title,
            "method1_records": len(method1_data),
            "method1_columns": list(method1_data[0].keys()) if method1_data else [],
            "method2_raw_rows": len(method2_data),
            "method2_raw_cols": len(method2_data[0]) if method2_data else 0,
            "sheet_dimensions": f"{last_row} rows x {last_col} columns",
            "sample_first_3_records": method1_data[:3] if len(method1_data) >= 3 else method1_data,
            "can_access_all_data": len(method1_data) > 0 or len(method2_data) > 0,
            "total_data_available": max(len(method1_data), len(method2_data) - 1 if method2_data else 0)
        }
        return jsonify(test_result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Gagal mengakses data sheet"
        }), 500

@sheet_bp.route('/debug_leads', methods=['GET'])
def debug_leads():
    try:
        sh = get_gsheet()
        ws = get_worksheet(sh, 'work1')
        all_data = ws.get_all_records()
        if not all_data:
            return jsonify({"error": "No data found"})
        available_columns = list(all_data[0].keys())
        leads_columns = {
            'facebook_leads': 'On-Facebook Leads',
            'messaging': 'Messaging Conversations Started',
            'lead_form': 'Lead Form',
            'whatsapp': 'WhatsApp'
        }
        found_leads_columns = {}
        for key, col_name in leads_columns.items():
            if col_name in available_columns:
                found_leads_columns[key] = col_name
        sample_rows = all_data[:5]
        leads_summary = {}
        total_smart_leads = 0
        for key, col_name in found_leads_columns.items():
            total = sum(int(row.get(col_name, 0) or 0) for row in all_data)
            leads_summary[col_name] = total
        for row in all_data:
            lead_form_count = int(row.get('Lead Form', 0) or 0)
            whatsapp_count = int(row.get('WhatsApp', 0) or 0)
            row_leads = lead_form_count + whatsapp_count
            total_smart_leads += row_leads
        return jsonify({
            "success": True,
            "total_rows": len(all_data),
            "available_columns": available_columns,
            "found_leads_columns": found_leads_columns,
            "leads_summary": leads_summary,
            "smart_total_leads": total_smart_leads,
            "sample_data": sample_rows,
            "logic_explanation": {
                "default": "Lead Form + WhatsApp (gabungan)",
                "description": "Messaging Conversations tidak dihitung terpisah karena sudah termasuk dalam Lead Form",
                "user_commands": [
                    "'hanya lead form' → Lead Form saja",
                    "'hanya whatsapp' → WhatsApp saja",
                    "'tanpa whatsapp' → Lead Form tanpa WhatsApp",
                    "'tanpa lead form' → WhatsApp tanpa Lead Form"
                ]
            },
            "debug_info": {
                "worksheet_title": ws.title,
                "sheet_title": sh.title
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
