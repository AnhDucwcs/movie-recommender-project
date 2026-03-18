"""
API Routes – Movie Recommender
──────────────────────────────
Endpoint                                          Method  Mô tả
─────────────────────────────────────────────     ──────  ─────────────────────────────────────────────
GET  /api/health                                  GET     Kiểm tra trạng thái hệ thống
GET  /api/movies/search?q=&limit=                 GET     Tìm kiếm phim theo tên
GET  /api/movies/{movie_id}                       GET     Thông tin chi tiết một bộ phim
GET  /api/movies/{movie_id}/recommendations?n=    GET     Gợi ý Top-N phim tương tự (Content-Based)
"""

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from services.recommender import recommender_service

router = APIRouter()


# ─── Utility ─────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    tags=["Utility"],
    summary="Kiểm tra trạng thái server",
)
async def health_check():
    """
    Trả về trạng thái hoạt động của server và thông tin model.
    - `model_loaded`: model AI đã sẵn sàng chưa
    - `movies_count`: tổng số phim đang được quản lý
    """
    return {
        "status": "ok",
        "model_loaded": recommender_service.is_loaded,
        "movies_count": recommender_service.movie_count,
    }


# ─── Movies ──────────────────────────────────────────────────────────────────

@router.get(
    "/movies/search",
    tags=["Movies"],
    summary="Tìm kiếm phim theo tên",
)
async def search_movies(
    q: str = Query(..., min_length=1, description="Từ khóa tìm kiếm (tên phim)"),
    limit: int = Query(default=10, ge=1, le=50, description="Số lượng kết quả tối đa"),
):
    """
    Tìm kiếm phim theo tên – **không phân biệt hoa thường**, dùng substring match.

    Ví dụ: `?q=toy story` → trả về tất cả phim có "toy story" trong tên.

    Mỗi kết quả gồm: `movieId`, `tmdbId`, `title`, `poster_url`.
    """
    _require_model()
    results = recommender_service.search(q, limit=limit)
    return {
        "query": q,
        "total": len(results),
        "results": results,
    }


@router.get(
    "/movies/{movie_id}",
    tags=["Movies"],
    summary="Xem chi tiết một bộ phim",
)
async def get_movie_detail(movie_id: int):
    """
    Trả về thông tin **chi tiết đầy đủ** của bộ phim theo `movieId` (MovieLens ID).

    Bao gồm: `title`, `overview`, `genres`, `tmdb_genres`, `keywords`, `cast`, `poster_url`.
    """
    _require_model()
    movie = recommender_service.get_movie(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy phim với movieId = {movie_id}",
        )
    return movie


# ─── Recommendations ─────────────────────────────────────────────────────────

@router.get(
    "/movies/{movie_id}/recommendations",
    tags=["Recommendations"],
    summary="Gợi ý phim tương tự (Content-Based Filtering)",
)
async def get_recommendations(
    movie_id: int,
    n: int = Query(
        default=settings.TOP_N_DEFAULT,
        ge=1,
        le=settings.TOP_N_MAX,
        description="Số lượng phim gợi ý (Top-N)",
    ),
):
    """
    Trả về danh sách **Top-N phim tương tự** dựa trên thuật toán
    **Content-Based Filtering** (TF-IDF + Cosine Similarity).

    Mỗi kết quả gợi ý gồm: `movieId`, `title`, `poster_url`,
    và `similarity_score` ∈ [0, 1] – càng gần 1 càng tương đồng.

    Response schema:
    ```json
    {
      "movie": { ...chi tiết phim đầu vào... },
      "n": 10,
      "recommendations": [
        { "movieId": ..., "title": "...", "poster_url": "...", "similarity_score": 0.87 },
        ...
      ]
    }
    ```
    """
    _require_model()

    # Xác nhận phim tồn tại
    movie = recommender_service.get_movie(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy phim với movieId = {movie_id}",
        )

    recommendations = recommender_service.get_recommendations(movie_id, n=n)
    return {
        "movie": movie,
        "n": n,
        "recommendations": recommendations,
    }


# ─── Internal helper ─────────────────────────────────────────────────────────

def _require_model():
    """Trả 503 nếu model AI chưa được load."""
    if not recommender_service.is_loaded:
        raise HTTPException(
            status_code=503,
            detail=(
                "Model AI chưa sẵn sàng. "
                "Hãy chạy AI Engine trước: "
                "docker compose run --rm ai_engine"
            ),
        )
