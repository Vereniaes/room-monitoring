# ============================================================
# Dockerfile — IoT Smart Room (All-in-One)
# -> Streamlit Dashboard  (port 8080, exposed ke Cloud Run)
# -> API Gateway Flask    (port 5000, internal container)
# Target: Google Cloud Run
# ============================================================

FROM python:3.11-slim

LABEL maintainer="iot-unj"
LABEL description="Smart Room IoT — Streamlit Dashboard + Flask API Gateway"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    GATEWAY_URL=http://localhost:5000

WORKDIR /app

# --- Install dependencies (semua: streamlit + flask + gunicorn + nginx) ---
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# --- Copy semua source code ---
COPY email_helper.py        .
COPY api_gateway.py         .
COPY settings.json          .
COPY start.sh               .
COPY nginx.conf             .
COPY .streamlit/            .streamlit/
COPY dashboard/dashboard.py                          dashboard/dashboard.py
COPY dashboard/data_sensor_1_minggu_lineprotocol.txt dashboard/data_sensor_1_minggu_lineprotocol.txt

# Buat log file & set permission start.sh
RUN touch /app/security_activity.log \
 && chmod +x /app/start.sh

# Cloud Run expose 8080 ke publik
# Gateway berjalan di :5000 (internal container, tidak di-expose)
EXPOSE 8080

# Credentials di-inject via env var saat deploy:
# INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
CMD ["/bin/bash", "/app/start.sh"]
