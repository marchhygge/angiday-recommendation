# Bước 1: Chọn một image Python cơ sở
FROM python:3.10-slim

# Bước 2: Đặt thư mục làm việc bên trong container
WORKDIR /app

# Bước 3: Sao chép file requirements.txt vào trước
COPY requirements.txt .

# Bước 4: Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Bước 5: Sao chép toàn bộ code của bạn vào container
# (Bao gồm cả 'start.sh' mới)
COPY . .

# --- THAY ĐỔI LỚN ---
# 1. XÓA LỆNH 'RUN python train_model.py'
#    Chúng ta không train ở build-time nữa.
#
# 2. THÊM QUYỀN THỰC THI CHO start.sh
RUN chmod +x ./start.sh

# 3. CHẠY 'start.sh' LÀM LỆNH KHỞI ĐỘNG
#    Nó sẽ chạy train_model.py TRƯỚC, sau đó chạy gunicorn.
CMD ./start.sh