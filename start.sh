#!/bin/bash
# start.sh
# -> script untuk jalanin 2 proses sekaligus dalam 1 container:
#    1. gunicorn (api_gateway) - background, port 5000
#    2. streamlit (dashboard)  - foreground, port 8080
#
# -> Cloud Run expose port 8080 ke luar
# -> gateway jalan di localhost:5000 (internal container saja)

set -e

echo "=============================================="
echo "  IoT Smart Room — Container Starting Up"
echo "=============================================="

# --- 1. Jalanin API Gateway (background) ---
echo "[1/2] Starting API Gateway (gunicorn) on :5000..."
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 1 \
  --threads 4 \
  --timeout 60 \
  --log-level info \
  api_gateway:app &

GATEWAY_PID=$!
echo "      API Gateway PID: $GATEWAY_PID"

# Tunggu sebentar pastiin gateway sudah ready sebelum Streamlit start
sleep 2

# --- 2. Jalanin Streamlit Dashboard (foreground) ---
echo "[2/2] Starting Streamlit Dashboard on :8080..."
exec streamlit run dashboard/dashboard.py \
  --server.port=8080 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false \
  --server.enableWebsocketCompression=false
