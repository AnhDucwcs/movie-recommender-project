"""
Movie Recommender – FastAPI Backend
────────────────────────────────────
Khởi động server:
  uvicorn main:app --reload                    (local dev)
  docker compose up backend                    (Docker)

Tài liệu API tự động:
  http://localhost:8000/docs    (Swagger UI)
  http://localhost:8000/redoc   (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from services.recommender import recommender_service


# ─── Lifespan (startup / shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    print("🚀 Khởi động Movie Recommender API...")
    recommender_service.load()
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    print("🛑 Server đang tắt.")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Movie Recommender API",
    description=(
        "Hệ thống gợi ý phim dựa trên **Content-Based Filtering** "
        "(TF-IDF + Cosine Similarity).\n\n"
        "Dữ liệu: **MovieLens** + **TMDB API**.\n\n"
        "Đồ án chuyên ngành – Trường Đại học Sài Gòn."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Cho phép frontend (Next.js) gọi API từ origin khác.
# Cần cấu hình lại khi deploy production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api")


# ─── Root ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    return {
        "message": "Movie Recommender API đang chạy.",
        "docs": "/docs",
        "health": "/api/health",
    }
