#!/bin/sh
set -e
echo "--- [API] Starting API server (gunicorn) ---"
# Chỉ chạy Gunicorn, không train
exec gunicorn --bind 0.0.0.0:$PORT "api_server:app"