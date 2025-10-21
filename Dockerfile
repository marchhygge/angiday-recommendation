# syntax=docker/dockerfile:1
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_COLOR=1

# In lệnh khi chạy (để log build rõ ràng) và fail-fast
SHELL ["/bin/sh", "-euxo", "pipefail", "-c"]

WORKDIR /app

# Cài các gói hệ thống tối thiểu (nếu cần compile nhẹ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
# In version và bật verbose cho pip
RUN python -V && pip -V \
 && pip install --no-cache-dir -U pip setuptools wheel \
 && pip install --no-cache-dir -v -r requirements.txt

# Sao chép code
COPY . .

# Xử lý CRLF nếu repo push từ Windows (tránh lỗi /bin/sh^M khi run)
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

CMD ./start.sh