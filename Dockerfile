FROM python:3.10-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mọi thứ (bao gồm cả start.sh)
COPY . .

# 1. XÓA 'RUN python train_model.py' (không train ở build-time nữa)
#
# 2. THÊM QUYỀN THỰC THI CHO start.sh
RUN chmod +x ./start.sh

# 3. CHẠY start.sh LÀM LỆNH KHỞI ĐỘNG
CMD ./start.sh