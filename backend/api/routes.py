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
from sqlalchemy import desc, func, or_, select
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


class InteractionTarget(BaseModel):
    user_id: int = Field(..., ge=1)
    movie_id: int = Field(..., ge=1)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


def _get_db_movie_stats(db: Session, movie_ids: list[int]) -> dict[int, dict]:
    """
    Lấy thống kê interaction từ DB cho danh sách movie_ids.
    """
    if not movie_ids:
        return {}

    vote_count = func.count(Interaction.interaction_id).label("interaction_count")
    avg_score = func.avg(Interaction.rating_value).label("avg_score")

    stmt = (
        select(Interaction.movie_id, vote_count, avg_score)
        .where(Interaction.movie_id.in_(movie_ids))
        .group_by(Interaction.movie_id)
    )
    rows = db.execute(stmt).all()

    return {
        int(row.movie_id): {
            "interaction_count": int(row.interaction_count or 0),
            "avg_score": round(float(row.avg_score), 2) if row.avg_score is not None else None,
        }
        for row in rows
    }


def _get_trending_payload(limit: int) -> tuple[list[dict], str]:
    """
    Xếp hạng trending theo ratings.csv (MovieLens).
    """
    movies = recommender_service.get_trending_movies(limit=limit)
    if movies:
        return movies, "ratings_csv_vote_count_then_avg_score"
    return [], "ratings_data_unavailable"


# ─── Utility ─────────────────────────────────────────────────────────────────

@router.post(
    "/auth/login",
    tags=["Auth"],
    summary="Đăng nhập người dùng",
)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập theo username + mật khẩu demo cấu hình trong env.
    """
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username không hợp lệ.")

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu.")

    if payload.password != settings.DEMO_LOGIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu.")

    return {
        "message": "Đăng nhập thành công",
        "token": f"demo-token-{user.user_id}",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
        },
    }

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
    movies, strategy = _get_trending_payload(limit=limit)
    if not movies:
        raise HTTPException(
            status_code=503,
            detail=(
                "Trending chỉ dùng dữ liệu rating nhưng hiện chưa có ratings.csv. "
                "Hãy cung cấp RATINGS_CSV_PATH hoặc mount data/raw/ml-latest-small/ratings.csv"
            ),
        )
    return {
        "strategy": strategy,
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

    if interaction_type == "RATING":
        latest_rating = db.execute(
            select(Interaction)
            .where(
                Interaction.user_id == payload.user_id,
                Interaction.movie_id == payload.movie_id,
                Interaction.interaction_type == "RATING",
            )
            .order_by(desc(Interaction.created_at), desc(Interaction.interaction_id))
            .limit(1)
        ).scalar_one_or_none()

        if latest_rating is not None:
            latest_rating.rating_value = rating_value
            db.commit()
            db.refresh(latest_rating)
            return {
                "message": "Đã cập nhật rating thành công",
                "interaction": {
                    "interaction_id": latest_rating.interaction_id,
                    "user_id": latest_rating.user_id,
                    "movie_id": latest_rating.movie_id,
                    "interaction_type": latest_rating.interaction_type,
                    "rating_value": latest_rating.rating_value,
                    "created_at": latest_rating.created_at,
                },
            }

    if interaction_type == "LIKE":
        existing_like = db.execute(
            select(Interaction)
            .where(
                Interaction.user_id == payload.user_id,
                Interaction.movie_id == payload.movie_id,
                Interaction.interaction_type == "LIKE",
            )
            .order_by(desc(Interaction.created_at), desc(Interaction.interaction_id))
            .limit(1)
        ).scalar_one_or_none()
        if existing_like is not None:
            return {
                "message": "Phim đã được Like trước đó",
                "interaction": {
                    "interaction_id": existing_like.interaction_id,
                    "user_id": existing_like.user_id,
                    "movie_id": existing_like.movie_id,
                    "interaction_type": existing_like.interaction_type,
                    "rating_value": existing_like.rating_value,
                    "created_at": existing_like.created_at,
                },
            }

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
    "/interactions/status",
    tags=["Interactions"],
    summary="Lấy trạng thái tương tác user với movie",
)
async def get_interaction_status(
    user_id: int = Query(..., ge=1),
    movie_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user_id = {user_id}")

    liked = db.execute(
        select(Interaction.interaction_id)
        .where(
            Interaction.user_id == user_id,
            Interaction.movie_id == movie_id,
            Interaction.interaction_type == "LIKE",
        )
        .order_by(desc(Interaction.created_at), desc(Interaction.interaction_id))
        .limit(1)
    ).scalar_one_or_none()

    latest_rating = db.execute(
        select(Interaction.rating_value)
        .where(
            Interaction.user_id == user_id,
            Interaction.movie_id == movie_id,
            Interaction.interaction_type == "RATING",
        )
        .order_by(desc(Interaction.created_at), desc(Interaction.interaction_id))
        .limit(1)
    ).scalar_one_or_none()

    return {
        "user_id": user_id,
        "movie_id": movie_id,
        "liked": liked is not None,
        "latest_rating": float(latest_rating) if latest_rating is not None else None,
    }


@router.delete(
    "/interactions/like",
    tags=["Interactions"],
    summary="Hủy Like phim",
)
async def unlike_movie(
    payload: InteractionTarget,
    db: Session = Depends(get_db),
):
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy user_id = {payload.user_id}")

    like_rows = db.execute(
        select(Interaction)
        .where(
            Interaction.user_id == payload.user_id,
            Interaction.movie_id == payload.movie_id,
            Interaction.interaction_type == "LIKE",
        )
    ).scalars().all()

    if not like_rows:
        return {"message": "Phim chưa được Like", "deleted": 0}

    deleted_count = len(like_rows)
    for row in like_rows:
        db.delete(row)
    db.commit()

    return {"message": "Đã hủy Like thành công", "deleted": deleted_count}


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
    db: Session = Depends(get_db),
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
    missing_rating_movie_ids = [
        int(item["movieId"])
        for item in recommendations
        if item.get("avg_score") is None
    ]
    if missing_rating_movie_ids:
        db_stats = _get_db_movie_stats(db=db, movie_ids=missing_rating_movie_ids)
        for item in recommendations:
            if item.get("avg_score") is not None:
                continue
            stats = db_stats.get(int(item["movieId"]))
            if stats is not None:
                item["avg_score"] = stats["avg_score"]

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
        trending, strategy = _get_trending_payload(limit=n)
        if not trending:
            raise HTTPException(
                status_code=503,
                detail="Không thể fallback trending vì thiếu dữ liệu rating (ratings.csv).",
            )
        return {
            "user_id": user_id,
            "strategy": f"cold_start_trending_fallback::{strategy}",
            "seed_movie_ids": [],
            "recommendations": trending,
        }

    recommendations = recommender_service.get_personalized_recommendations(
        seed_movie_ids=seed_movie_ids,
        n=n,
    )

    if not recommendations:
        trending, strategy = _get_trending_payload(limit=n)
        if not trending:
            raise HTTPException(
                status_code=503,
                detail="Không thể fallback trending vì thiếu dữ liệu rating (ratings.csv).",
            )
        return {
            "user_id": user_id,
            "strategy": f"personalized_unavailable_then_trending::{strategy}",
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
    db: Session = Depends(get_db),
):
    return await get_movie_recommendations(movie_id=movie_id, n=n, db=db)


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
