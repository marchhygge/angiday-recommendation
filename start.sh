#!/bin/sh
set -e

# 1. Chạy training (Ở run-time, nên sẽ thấy các biến HOST, PORT...)
echo "--- [Railway] Starting model training (train_model.py) ---"
python train_model.py

# 2. Khởi động Gunicorn
echo "--- [Railway] Model training complete. Starting API server (gunicorn) ---"
exec gunicorn --bind 0.0.0.0:$PORT "api_server:app"