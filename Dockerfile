# ============================================================
# Dockerfile — IoT Smart Room Dashboard (Streamlit)
# Target: Google Cloud Run
# ============================================================

# --- Stage 1: Base image ---
FROM python:3.11-slim

# Metadata
LABEL maintainer="iot-unj"
LABEL description="Smart Room IoT Dashboard — Streamlit + InfluxDB Cloud"

# Env dasar
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# --- Stage 2: Install dependencies ---
# Copy requirements dulu (layer caching — jika requirements tidak berubah, layer ini di-cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- Stage 3: Copy source code ---
# Copy file-file yang dibutuhkan dashboard
COPY email_helper.py     .
COPY settings.json       .
COPY .streamlit/         .streamlit/
COPY dashboard/dashboard.py          dashboard/dashboard.py
COPY dashboard/data_sensor_1_minggu_lineprotocol.txt \
     dashboard/data_sensor_1_minggu_lineprotocol.txt

# Pastikan folder log bisa ditulis (Cloud Run: ephemeral, tapi supaya tidak crash)
RUN mkdir -p /app/logs && touch /app/security_activity.log

# --- Stage 4: Entrypoint ---
# Credentials (INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET)
# di-inject via Cloud Run --set-env-vars atau Secret Manager saat deploy.
# JANGAN hardcode di sini.
EXPOSE 8080

CMD ["streamlit", "run", "dashboard/dashboard.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
