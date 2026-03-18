FROM python:3.11-slim

# Đặt WORKDIR = /app/ai_engine để path tương đối "../data" trong script
# trỏ đúng đến /app/data (volume mount trong docker-compose.yml)
WORKDIR /app/ai_engine

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tải dữ liệu NLTK cần thiết
RUN python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"

COPY . .

# Lệnh mặc định: xuất model ra data/models/
CMD ["python", "export_model.py"]
