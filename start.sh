#!/bin/sh
set -e

echo "--- [API] Starting API server (gunicorn) ---"

# Train nếu thiếu model
MODEL_PATH=${MODEL_PATH:-/models}
mkdir -p "$MODEL_PATH"
if [ ! -f "$MODEL_PATH/vectorizer.pkl" ] || \
   [ ! -f "$MODEL_PATH/restaurant_vectors.pkl" ] || \
   [ ! -f "$MODEL_PATH/restaurant_metrics.pkl" ]; then
  echo "[INIT] Model files not found in $MODEL_PATH. Training..."
  python train_model.py
else
  echo "[INIT] Model files found in $MODEL_PATH. Skipping training."
fi

# Chỉ chạy Gunicorn
exec gunicorn --bind 0.0.0.0:"${PORT}" "api_server:app"