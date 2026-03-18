# ═══════════════════════════════════════════════════════════════════════════
# Movie Recommender – Production Dockerfile (Multi-stage Build)
# ═══════════════════════════════════════════════════════════════════════════
#
# Mục đích: Dùng để DEPLOY lên cloud (Render, Railway, Fly.io…).
#           File này khác với ai_engine/Dockerfile và backend/Dockerfile
#           (hai file kia dùng cho docker compose local dev).
#
# Cơ chế:
#   Stage 1 (model-builder): Chạy export_model.py → tạo similarity.pkl & movie_dict.pkl
#   Stage 2 (backend)      : Copy model đã build vào image FastAPI → sẵn sàng chạy
#
# Vì data/processed/ đã được commit lên git, nên Stage 1 có thể tạo model
# ngay trong quá trình docker build mà không cần mount volume.
# ═══════════════════════════════════════════════════════════════════════════


# ───────────────────────────────────────────────────────────────────────────
# Stage 1 – AI Engine: tạo model từ data đã có sẵn trong repo
# ───────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS model-builder

WORKDIR /app/ai_engine

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Cài dependencies của AI Engine
COPY ai_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tải dữ liệu NLTK cần thiết
RUN python -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('punkt', quiet=True)"

# Copy source AI Engine
COPY ai_engine/ .

# Copy dữ liệu đã xử lý (movies_cleaned_soup.csv, movies_enriched.csv)
# Đây là input cho export_model.py
COPY data/processed/ /app/data/processed/

# Chạy pipeline tạo model → output vào /app/data/models/
RUN python export_model.py


# ───────────────────────────────────────────────────────────────────────────
# Stage 2 – Backend: FastAPI production server
# ───────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Cài dependencies của Backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source Backend
COPY backend/ .

# ── Lấy dữ liệu từ Stage 1 ──────────────────────────────────────────────
# Model đã được tạo sẵn (similarity.pkl, movie_dict.pkl)
COPY --from=model-builder /app/data/models/ /app/data/models/

# Enriched CSV cho endpoint /api/movies/{id} (overview, cast, keywords…)
COPY data/processed/ /app/data/processed/

# ── Environment ─────────────────────────────────────────────────────────
# DATA_DIR trỏ vào /app/data (nơi vừa copy models + processed vào)
ENV DATA_DIR=/app/data
# Render/Railway inject PORT qua biến môi trường; mặc định 8000
ENV PORT=8000

EXPOSE ${PORT}

# Dùng sh -c để đọc $PORT lúc runtime (không phải lúc build)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
