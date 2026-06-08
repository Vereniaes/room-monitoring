#!/bin/bash
# start.sh
# -> jalankan 3 proses dalam 1 container:
#    1. gunicorn  (api_gateway) - internal :5000
#    2. streamlit (dashboard)   - internal :8501
#    3. nginx     (reverse proxy) - exposed :8080
#
# -> nginx route berdasarkan path:
#    /write, /get_command, /set_light, ... → Gateway :5000
#    /                                     → Streamlit :8501
# -> Cloud Run expose :8080 ke publik

set -e

echo "=============================================="
echo "  IoT Smart Room — Container Starting Up"
echo "=============================================="

# Buat temp dirs nginx (perlu writable)
mkdir -p /tmp/nginx_client_body /tmp/nginx_proxy /tmp/nginx_fastcgi \
         /tmp/nginx_uwsgi /tmp/nginx_scgi

# --- 1. API Gateway (background) ---
echo "[1/3] Starting API Gateway (gunicorn) on :5000..."
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 1 \
  --threads 4 \
  --timeout 60 \
  --log-level warning \
  api_gateway:app &
echo "      PID: $!"

# --- 2. Streamlit Dashboard (background, port 8501) ---
echo "[2/3] Starting Streamlit Dashboard on :8501..."
streamlit run dashboard/dashboard.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false &
STREAMLIT_PID=$!
echo "      PID: $STREAMLIT_PID"

# Tunggu Streamlit siap
sleep 4

# --- 3. nginx reverse proxy (foreground, port 8080) ---
echo "[3/3] Starting nginx reverse proxy on :8080..."
exec nginx -g "daemon off;" -c /app/nginx.conf

