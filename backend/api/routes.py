"""
API Routes – Movie Recommender
──────────────────────────────
Endpoint                                          Method  Mô tả
─────────────────────────────────────────────     ──────  ─────────────────────────────────────────────
GET  /api/health                                  GET     Kiểm tra trạng thái hệ thống
GET  /api/movies/trending                         GET     Lấy phim thịnh hành (cold-start)
GET  /api/movies/search?q=&limit=                 GET     Tìm kiếm phim theo tên
GET  /api/movies/{movie_id}                       GET     Thông tin chi tiết một bộ phim
POST /api/interactions                            POST    Lưu lịch sử tương tác người dùng
GET  /api/recommendations/movie/{movie_id}        GET     Gợi ý phim tương tự theo movie_id (item-to-item)
GET  /api/recommendations/user/{user_id}          GET     Gợi ý cá nhân hóa theo lịch sử tích cực (user-to-item)
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from core.config import settings
from db.models import Interaction, User
from db.session import get_db
from services.recommender import recommender_service

router = APIRouter()


class InteractionCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    movie_id: int = Field(..., ge=1)
    interaction_type: Literal["LIKE", "RATING"]
    rating_value: float | None = Field(default=None, ge=1.0, le=5.0)


def _get_trending_payload(limit: int) -> list[dict]:
    """
    Xếp hạng trending theo ratings.csv (MovieLens).
    """
    return recommender_service.get_trending_movies(limit=limit)


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
    "/movies/trending",
    tags=["Movies"],
    summary="Lấy Top phim thịnh hành (cold-start)",
)
async def get_trending_movies(
    limit: int = Query(
        default=settings.TRENDING_DEFAULT_LIMIT,
        ge=1,
        le=settings.TRENDING_MAX_LIMIT,
        description="Số phim trending cần lấy",
    ),
):
    """
    Trả về danh sách phim thịnh hành cho trang chủ người dùng mới.
    """
    _require_model()
    movies = _get_trending_payload(limit=limit)
    return {
        "strategy": "ratings_csv_vote_count_then_avg_score",
        "total": len(movies),
        "results": movies,
    }

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

@router.post(
    "/interactions",
    tags=["Interactions"],
    summary="Lưu lịch sử tương tác người dùng",
)
async def create_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
):
    """
    Lưu một tương tác của user với movie vào bảng interactions.
    """
    interaction_type = payload.interaction_type.upper()
    rating_value = payload.rating_value

    if interaction_type == "RATING" and rating_value is None:
        raise HTTPException(status_code=400, detail="interaction_type=RATING yêu cầu rating_value.")

    if interaction_type == "LIKE" and rating_value is None:
        rating_value = 5.0

    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user_id = {payload.user_id}")

    movie = recommender_service.get_movie(payload.movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy movie_id = {payload.movie_id}")

    interaction = Interaction(
        user_id=payload.user_id,
        movie_id=payload.movie_id,
        interaction_type=interaction_type,
        rating_value=rating_value,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return {
        "message": "Đã lưu interaction thành công",
        "interaction": {
            "interaction_id": interaction.interaction_id,
            "user_id": interaction.user_id,
            "movie_id": interaction.movie_id,
            "interaction_type": interaction.interaction_type,
            "rating_value": interaction.rating_value,
            "created_at": interaction.created_at,
        },
    }


@router.get(
    "/recommendations/movie/{movie_id}",
    tags=["Recommendations"],
    summary="Gợi ý phim tương tự theo movie_id (item-to-item)",
)
async def get_movie_recommendations(
    movie_id: int,
    n: int = Query(
        default=5,
        ge=1,
        le=settings.TOP_N_MAX,
        description="Số lượng phim gợi ý",
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
        "strategy": "item_to_item_cosine_similarity",
        "movie": movie,
        "n": n,
        "recommendations": recommendations,
    }


@router.get(
    "/recommendations/user/{user_id}",
    tags=["Recommendations"],
    summary="Gợi ý cá nhân hóa theo lịch sử tích cực của user",
)
async def get_user_recommendations(
    user_id: int,
    n: int = Query(default=20, ge=1, le=50, description="Số lượng phim đề cử"),
    history_limit: int = Query(
        default=10,
        ge=5,
        le=20,
        description="Số phim tích cực gần nhất dùng để dựng user profile",
    ),
    db: Session = Depends(get_db),
):
    """
    Luồng personalized:
    1) Lọc interaction tích cực: LIKE hoặc rating >= 4.
    2) Lấy lịch sử gần nhất theo created_at desc, giới hạn bởi history_limit.
    3) Ghép soup của các seed movies thành user_profile_soup.
    4) tfidf.transform(user_profile_soup) -> cosine_similarity với toàn catalog.
    5) Loại seed movies và trả Top-N.
    """
    _require_model()

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user_id = {user_id}")

    stmt = (
        select(Interaction.movie_id)
        .where(
            Interaction.user_id == user_id,
            or_(
                Interaction.interaction_type == "LIKE",
                Interaction.rating_value >= 4,
            ),
        )
        .order_by(desc(Interaction.created_at))
        .limit(history_limit)
    )
    rows = db.execute(stmt).all()

    seed_movie_ids: list[int] = []
    seen = set()
    for row in rows:
        movie_id = int(row.movie_id)
        if movie_id in seen:
            continue
        seen.add(movie_id)
        seed_movie_ids.append(movie_id)

    if not seed_movie_ids:
        trending = _get_trending_payload(limit=n)
        return {
            "user_id": user_id,
            "strategy": "cold_start_trending_fallback",
            "seed_movie_ids": [],
            "recommendations": trending,
        }

    recommendations = recommender_service.get_personalized_recommendations(
        seed_movie_ids=seed_movie_ids,
        n=n,
    )

    if not recommendations:
        trending = _get_trending_payload(limit=n)
        return {
            "user_id": user_id,
            "strategy": "personalized_unavailable_then_trending",
            "seed_movie_ids": seed_movie_ids,
            "recommendations": trending,
        }

    return {
        "user_id": user_id,
        "strategy": "user_profile_soup_tfidf_cosine",
        "seed_movie_ids": seed_movie_ids,
        "recommendations": recommendations,
    }


# Tương thích API cũ để frontend hiện tại không bị vỡ.
@router.get(
    "/movies/{movie_id}/recommendations",
    tags=["Recommendations"],
    summary="(Legacy) Gợi ý phim tương tự theo movie_id",
)
async def get_movie_recommendations_legacy(
    movie_id: int,
    n: int = Query(default=10, ge=1, le=settings.TOP_N_MAX),
):
    return await get_movie_recommendations(movie_id=movie_id, n=n)


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
