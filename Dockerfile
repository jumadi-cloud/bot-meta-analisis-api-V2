# Gunakan Python 3.10 (sesuai dengan kebutuhan umum Flask)
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements dulu (untuk efisiensi build cache)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode
COPY . .

# Buka port 8080 (sesuai dengan app.py)
EXPOSE 8080

# Jalankan aplikasi
CMD ["python", "app.py"]
