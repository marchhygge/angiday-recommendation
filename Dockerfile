# Bước 1: Chọn một image Python cơ sở
FROM python:3.10-slim

# Bước 2: Đặt thư mục làm việc bên trong container
WORKDIR /app

# Bước 3: Sao chép file requirements.txt vào trước
COPY requirements.txt .

# Bước 4: Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Bước 5: Sao chép toàn bộ code của bạn vào container
# (bao gồm api_server.py, train_model.py, ...)
COPY . .

# Bước 6: (QUAN TRỌNG) Chạy script train_model.py
# Bước này sẽ chạy KHI BUILD, tạo ra các file .pkl
RUN python train_model.py

# Bước 7: Cung cấp lệnh để khởi động server Gunicorn
# Lệnh này sẽ chạy KHI START, Railway sẽ tự động cung cấp $PORT
CMD gunicorn --bind 0.0.0.0:$PORT "api_server:app"