## 🔀 Contoh Query Kombinasi & Edge Case

| Jenis Kombinasi/Edge Case      | Contoh Pertanyaan                                                                 | Insight yang Diberikan                                                                                   |
|---------------------------------|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Multi Filter (Gender+Usia+Bulan)| Berapa cost tertinggi dari wanita usia 45-54 di bulan September?                  | Cost terbesar segmented gender, usia, dan bulan.                                                         |
| Adset+Tanggal                   | WhatsApp leads adset X di tanggal 2025-09-01?                                    | Total WhatsApp leads untuk adset dan tanggal tertentu.                                                   |
| Minggu+Adset+Usia               | Klik tertinggi minggu ke-38 dari adset Y usia 35-44?                             | Klik tertinggi segmented minggu, adset, dan usia.                                                        |
| Performa Mingguan+Segmented     | Bagaimana performa minggu ke-40 untuk laki-laki usia 55-64?                      | Insight mingguan segmented gender dan usia.                                                              |
| Query Ambigu/Umum               | "Bagus nggak performa iklan bulan ini?"                                         | Jawaban analitik, konfirmasi jika pertanyaan kurang spesifik.                                            |
| Query Tidak Relevan             | "Siapa presiden Indonesia?"                                                      | Jawaban: hanya bisa membantu pertanyaan terkait data kampanye/iklan.                                     |
| Data Tidak Ada                  | "Leads adset Z di bulan Januari 2024?"                                          | Jawaban jujur: data tidak tersedia, insight dari data terdekat.                                          |

---

## 🧩 Penjelasan Logic Additive & Troubleshooting

- Semua logic dan fitur baru bersifat additive, tidak menghapus logic lama.
- Jawaban selalu diambil dari data yang tersedia, tidak mengarang.
- Jika filter segmented (gender/usia/bulan/adset/ad/tanggal/minggu) tidak ditemukan di data, chatbot akan memberi insight dari data terdekat atau summary.
- Debug/logging aktif untuk setiap filter segmented, sehingga troubleshooting mudah dilakukan.
- Jika ada pertanyaan yang tidak dijawab sesuai harapan, cek log server untuk detail filter dan data yang diproses.

---

Partial selesai. Apakah ingin lanjut menambah tips penggunaan lanjutan, best practice, atau FAQ?
Partial: Ini baru bagian pertama. Apakah ingin lanjut ke bagian berikutnya (contoh query kombinasi, edge case, dan penjelasan logic additive)?

---

## 🔀 Contoh Query Kombinasi & Edge Case

| Contoh Query Kombinasi                                                                 | Insight yang Diberikan                                                                                   |
|----------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Berapa cost dan WhatsApp leads wanita usia 35-44 di adset X pada bulan September 2025?  | Menampilkan cost dan WhatsApp leads tersegmentasi gender, usia, adset, dan bulan sekaligus.              |
| Siapa adset dengan CTR tertinggi di minggu ke-40 tahun 2025?                            | Adset dengan rasio klik-tayang (CTR) tertinggi pada minggu dan tahun yang diminta.                      |
| Tanggal berapa cost terbesar untuk adset Y di bulan Oktober?                            | Tanggal dengan cost terbesar untuk adset tertentu pada bulan yang diminta.                               |
| Berapa total leads Facebook dan Lead Form dari laki-laki usia 45-54 di minggu ke-38?    | Menampilkan total Facebook leads dan Lead Form tersegmentasi gender, usia, dan minggu.                  |
| Ad mana yang paling efisien menghasilkan WhatsApp leads di bulan Juni?                  | Ad dengan CPWA (Cost Per WhatsApp Lead) terendah pada bulan yang diminta.                                |
| Performa adset Z di tanggal 2025-09-01?                                                | Insight harian untuk adset tertentu: cost, leads, klik, dsb.                                            |

---

## ⚡ Penjelasan Logic Additive & Troubleshooting

- Semua logic di chatbot bersifat additive: penambahan fitur tidak menghapus logic lama, hanya memperluas kemampuan.
- Semua filter segmented (gender, usia, adset, ad, tanggal, minggu, bulan, metrik) bisa digabung sesuai kebutuhan.
- Jika pertanyaan ambigu atau data tidak tersedia, chatbot akan memberikan insight yang relevan dan jujur.
- Debug/logging aktif untuk setiap filter segmented dan query edge case, sehingga troubleshooting mudah dilakukan.
- Jawaban selalu berupa narasi analitik, bukan data mentah, agar mudah dipahami dan actionable.

---

Tips: Jika insight tidak muncul sesuai harapan, cek data Google Sheets dan pastikan kolom serta format sudah benar. Gunakan log server untuk audit filter dan troubleshooting.

# 🚀 Bot Meta Ads API – Flask Agentic AI

Optimized REST API untuk analisis Facebook Ads, terintegrasi Google Sheets & Gemini AI.  
Deploy-ready di Render, dengan caching, monitoring, dan endpoint yang developer-friendly.

---

## 🏗️ Arsitektur Sistem

- **Flask REST API**: Backend utama, modular dan scalable.
- **Google Sheets**: Sumber data utama, real-time dan mudah update.
- **Gemini AI (LangChain)**: LLM untuk analisis naratif dan insight otomatis.
- **ChromaDB**: Vector store untuk retrieval augmented generation (RAG).
- **Prompt Logic**: Prioritas jawaban (adset efisien, demografi, summary) additive dan non-destructive.
- **Debug Logging**: Setiap filter dan query segmented terekam di log untuk troubleshooting.
- **Frontend (optional)**: Bisa diintegrasi dengan web, chatbot, atau platform lain.

Diagram arsitektur tersedia di file `architecture_diagram.html`.

---

## ✨ Fitur Utama

- ⚡ **Fast Response**: 1-2 detik, berkat smart caching
- 🧠 **Agentic AI**: Analisis otomatis, prompt teroptimasi
- 📊 **Google Sheets Integration**: Data real-time, mudah update
- 🔒 **Memory Safe**: Thread-safe, auto cache cleanup
- 🛠️ **Monitoring**: Endpoint status & cache management

- 🏆 **Adset Efficiency Insight**: Jawab pertanyaan "adset paling efisien per bulan" (CPWA, cost/WhatsApp lead) langsung dari data.
- 👥 **Segmented/Demografi Query**: Bisa filter dan analisis berdasarkan gender, usia, bulan, dan metrik lain.
- 🧩 **Additive Logic**: Semua fitur baru tidak menghapus logic lama, hanya menambah dan memperbaiki.
- 🐞 **Debug Logging**: Setiap filter segmented dan demografi terekam di log server untuk audit dan troubleshooting.

---

## 🔥 Optimisasi Performa

| Aspek                | Sebelum      | Sesudah      | Improvement         |
|----------------------|--------------|--------------|---------------------|
| Response Time        | 3-5 detik    | 1-2 detik    | ~60% lebih cepat    |
| Google Sheets Calls  | Setiap req   | 1x/5 menit   | 95% pengurangan     |
| Memory Usage         | Tinggi       | Optimized    | 40% lebih efisien   |
| AI Token Usage       | 500-800      | 150-250      | 70% pengurangan     |

---


## 📚 API Endpoints

- `POST /chat` – Chatbot analytics (input: message, output: insight)
- `GET /cache/status` – Status cache Google Sheets
- `POST /cache/clear` – Bersihkan cache manual
- `POST /chart` – Generate grafik tren (cost, impressions, dsb) dari Google Sheets, response gambar (PNG/base64), filter natural (gender, usia, tanggal, dsb)

---

## 🖼️ Fitur Visualisasi Data (Plotly Chart Endpoint)

- Endpoint additive `/chart` untuk generate grafik tren (cost, impressions, dsb) langsung dari data Google Sheets.
- Mendukung filter natural: gender, usia, adset, tanggal, bulan, dsb.
- Output bisa berupa file gambar (PNG) atau base64 (untuk integrasi frontend/Laravel).
- Visualisasi menggunakan plotly (modern, interaktif, dan mudah di-custom).
- Logic additive: tidak mengganggu pipeline lama, hanya menambah kapabilitas visualisasi.

### Contoh Request

```json
POST /chart
{
  "metric": "cost",
  "filter": {"gender": "Wanita"},
  "start_date": "2023-09-01",
  "end_date": "2023-09-30",
  "output": "base64"
}
```

### Contoh Response

```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### Dependensi Tambahan

- plotly
- kaleido (untuk ekspor gambar PNG)

Install dengan:
```
pip install plotly kaleido
```

---

### Prinsip Additive untuk Visualisasi
- Endpoint /chart tidak menghapus atau mengubah logic lama.
- Semua filter segmented (gender, usia, tanggal, adset, dsb) tetap berlaku di pipeline visualisasi.
- Jika data tidak ditemukan, response tetap robust dan privacy-safe.

---

---

## ❓ List Pertanyaan yang Bisa Dijawab & Insight

Berikut contoh pertanyaan yang dapat diajukan ke chatbot beserta penjelasan insight yang akan diberikan:


| Jenis Pertanyaan                | Contoh Pertanyaan                                                                 | Insight yang Diberikan                                                                                   |
|---------------------------------|----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Cost (Total/Segmented)          | Berapa total cost bulan Oktober 2025? <br> Cost tertinggi dari adset X di minggu ke-40? | Menampilkan total cost, cost segmented per adset/ad/usia/gender/bulan/tanggal/minggu sesuai permintaan.  |
| Leads (Total/Segmented)         | Berapa total WhatsApp leads di bulan Mei? <br> Leads wanita usia 35-44 di adset Y? | Menampilkan total leads (WhatsApp, Facebook, Lead Form) segmented per filter apapun.                    |
| Klik (All/Link/Segmented)       | Berapa total klik semua iklan di bulan Juni? <br> Klik tertinggi dari laki-laki usia 45-54? | Menampilkan total klik (all clicks, link clicks) segmented per adset/ad/usia/gender/bulan/tanggal.      |
| Impression/Reach                | Berapa total impression di bulan September? <br> Reach adset Z di minggu ke-38?    | Menampilkan total impression/reach segmented per filter apapun.                                          |
| CTR/LCTR                        | Berapa CTR tertinggi di bulan Agustus? <br> LCTR adset X di tanggal 2025-08-15?    | Menampilkan rasio klik-tayang (CTR/LCTR) segmented per adset/ad/bulan/tanggal/usia/gender.              |
| Lead Form/Facebook Leads        | Berapa total Facebook leads di bulan Juli? <br> Lead Form adset Y di minggu ke-30? | Menampilkan total Facebook leads dan Lead Form segmented per filter apapun.                              |
| Messaging Conversation Started  | Berapa total messaging conversation bulan September? <br> Dari adset Z di minggu ke-39? | Menampilkan total messaging conversation started segmented per adset/ad/bulan/tanggal/usia/gender.       |
| Efisiensi Adset (CPWA)          | Adset mana yang paling efisien menghasilkan WhatsApp leads di bulan September 2025? | Adset dengan CPWA (Cost Per WhatsApp Lead) terendah, total cost, dan jumlah WhatsApp leads per bulan.    |
| Performa Harian/Mingguan        | Bagaimana performa iklan di tanggal 2025-09-01? <br> Performa minggu ke-41?       | Menampilkan insight harian/mingguan: cost, leads, klik, adset/ad/segment paling efisien, dsb.           |
| Tanggal/Bulan/Minggu Tersedia   | Data yang ada ada tanggal dan bulan apa saja? <br> Minggu ke berapa saja yang tersedia? | Daftar tanggal, bulan, dan minggu yang tersedia di data Google Sheets.                                   |
| Cost/Leads/Clicks Terbesar      | Tanggal berapa cost terbesar di bulan September? <br> Leads terbanyak di adset X?  | Tanggal/adset/ad/segment dengan cost/leads/klik terbesar pada periode yang diminta.                      |
| Pertanyaan Umum/Salam           | Halo! <br> Terima kasih!                                                           | Jawaban natural, sapaan, atau konfirmasi tanpa insight data.                                             |

---

Partial: Ini baru bagian pertama. Apakah ingin lanjut ke bagian berikutnya (contoh query kombinasi, edge case, dan penjelasan logic additive)?

---

Setiap insight diberikan dalam bentuk narasi analitik yang jelas, actionable, dan mudah dipahami. Jawaban tidak berupa tabel mentah, melainkan ringkasan dan rekomendasi sesuai data yang tersedia.

### Contoh Query & Jawaban

- **Efisiensi Adset per Bulan**
  - Query: `Adset mana yang paling efisien dalam menghasilkan WhatsApp leads di bulan September 2025?`
  - Jawaban: `Adset paling efisien (CPWA terendah) untuk WhatsApp leads pada bulan September 2025: <strong>helene_leads_26</strong> dengan CPWA <strong>12.345 IDR</strong> (Total Cost: 123.456 IDR, Total WhatsApp Leads: 10)`

- **Segmented/Demografi**
  - Query: `Berapa total leads wanita usia 35-44 di bulan Mei?`
  - Jawaban: `Total WhatsApp leads untuk wanita usia 35-44 di bulan Mei: <strong>15</strong>`

- **Summary/Insight**
  - Query: `Bagaimana performa iklan bulan Juni?`
  - Jawaban: `Ringkasan performa bulan Juni: Total Cost 1.234.567 IDR, Total Leads WhatsApp 123, Adset paling efisien: ...`

Contoh `/cache/status` response:
```json
{
  "cache_status": {
    "sheet_id_work1": {
      "age_seconds": 45.2,
      "data_rows": 150,
      "expires_in": 254.8
    }
  },
  "cache_duration": 300
}
```

Contoh `/cache/clear` response:
```json
{
  "status": "Cache cleared successfully"
}
```

---

## ⚙️ Konfigurasi

- **Durasi Cache**: Edit `CACHE_DURATION` di `app.py` (default: 300 detik)
- **History Limit**: Edit `get_history(n=3)`
- **AI Response Length**: Edit `max_tokens=200`

---

## 🚀 Instalasi & Menjalankan

```bash
pip install -r requirements.txt
python app.py
```
Server: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📝 Tips Penggunaan

1. Request pertama mungkin lambat (cache kosong)
2. Request berikutnya jauh lebih cepat
3. Update data manual? POST ke `/cache/clear`
4. Monitoring cache via `/cache/status`

---

## 🌐 Deploy ke Render

1. Pastikan file: `requirements.txt`, `Procfile`, `.env`
2. Push ke GitHub, connect ke Render, isi environment variables
3. Render akan auto-deploy & expose public API

---

## 👨‍💻 Developer Notes

- Kode modular & mudah di-extend
- Semua secrets via `.env` (jangan commit ke repo!)
- Siap diintegrasi dengan Laravel,Django, Streamlit, chatbot, atau platform lain

- Semua logic additive, tidak ada fitur yang dihapus, hanya penambahan dan perbaikan.
- Debug/logging tersedia untuk audit filter segmented/demografi.
- Arsitektur modular: Flask, Google Sheets, Gemini AI, ChromaDB, dan prompt logic.

---
