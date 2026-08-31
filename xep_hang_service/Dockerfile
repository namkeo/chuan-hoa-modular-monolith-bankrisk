# Sử dụng Python 3.11 Slim làm base image
FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Thiết lập biến môi trường Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8088

# Cài đặt các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements.txt và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn ứng dụng
COPY . .

# Cấp quyền thực thi cho các script nếu có
RUN chmod +x *.sh 2>/dev/null || true

# Expose cổng 8088
EXPOSE 8088

# Lệnh khởi chạy ứng dụng FastAPI tại cổng 8088
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
