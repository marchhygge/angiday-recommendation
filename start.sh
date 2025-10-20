#!/bin/sh

# Đặt -e để script tự động dừng nếu có lỗi
set -e

# Bước 1: Chạy script huấn luyện
# Ở run-time, các biến HOST, DATABASE... SẼ CÓ SẴN
echo "--- [Railway] Starting model training (train_model.py) ---"
python train_model.py

# Bước 2: Nếu training thành công, khởi động Gunicorn
# Dùng 'exec' để Gunicorn thay thế tiến trình 'sh',
# giúp Railway quản lý server tốt hơn.
echo "--- [Railway] Model training complete. Starting API server (gunicorn) ---"
exec gunicorn --bind 0.0.0.0:$PORT "api_server:app"