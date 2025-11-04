
from flask import Blueprint, request, send_file, jsonify
import io
import plotly.graph_objs as go
import pandas as pd
import os
import gspread
from datetime import datetime
from services.aggregation import safe_float
from routes.sheet_routes import get_gsheet, get_worksheet

chart_bp = Blueprint('chart_bp', __name__)


@chart_bp.route('/chart', methods=['POST'])
def generate_chart():
    """
    Endpoint additive untuk generate grafik tren sederhana (misal: cost, impressions)
    Parameter: {
        "metric": "cost" | "impressions" | ...,
        "filter": {...},
        "sheet": "File Sheet 1",  # opsional
        "worksheet": "Worksheet1",  # opsional
        "start_date": "2023-01-01",  # opsional
        "end_date": "2023-01-31",  # opsional
        "output": "image" | "base64" (default: image)
    }
    """
    params = request.json or {}
    metric = params.get('metric', 'cost')
    filter_dict = params.get('filter', {})
    sheet = params.get('sheet')
    worksheet = params.get('worksheet')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    output_mode = params.get('output', 'image')

    # Ambil data dari Google Sheets (additive, robust)
    try:
        sh = get_gsheet(sheet_id=sheet)
        ws = get_worksheet(sh, worksheet) if worksheet else sh.worksheets()[0]
        data = ws.get_all_records(head=1)
        if not data:
            return jsonify({"error": "Data tidak ditemukan di worksheet."}), 404
        df = pd.DataFrame(data)
        # Filter tanggal jika ada kolom date
        if start_date or end_date:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                if start_date:
                    df = df[df['date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['date'] <= pd.to_datetime(end_date)]
        # Filter by filter_dict
        for k, v in filter_dict.items():
            if k in df.columns:
                df = df[df[k] == v]
        # Pastikan kolom metrik ada
        if metric not in df.columns:
            # fallback: cari kolom yang mirip (case-insensitive)
            found = [c for c in df.columns if c.lower() == metric.lower()]
            if found:
                metric = found[0]
            else:
                return jsonify({"error": f"Kolom metrik '{metric}' tidak ditemukan."}), 400
        # Drop baris tanpa nilai metrik
        df = df[df[metric].notnull()]
        if df.empty:
            return jsonify({"error": "Tidak ada data yang bisa divisualisasikan."}), 404
    except Exception as e:
        return jsonify({"error": f"Gagal mengambil data: {str(e)}"}), 500

    # Plotly chart
    fig = go.Figure()
    if 'date' in df.columns:
        fig.add_trace(go.Scatter(x=df['date'], y=df[metric], mode='lines+markers', name=metric))
        fig.update_layout(title=f'Trend {metric}', xaxis_title='Tanggal', yaxis_title=metric)
    else:
        fig.add_trace(go.Bar(x=df.index, y=df[metric], name=metric))
        fig.update_layout(title=f'{metric} per kategori', xaxis_title='Kategori', yaxis_title=metric)

    # Output gambar
    img_bytes = fig.to_image(format='png')
    img_io = io.BytesIO(img_bytes)
    img_io.seek(0)

    if output_mode == 'base64':
        import base64
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        return jsonify({"image_base64": img_b64})
    else:
        return send_file(img_io, mimetype='image/png', as_attachment=False, download_name='chart.png')
