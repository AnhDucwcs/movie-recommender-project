"""
RecommenderService
──────────────────
Singleton service chịu trách nhiệm:
  1. Tải model (movie_dict.pkl, similarity.pkl) và enriched CSV vào memory khi khởi động.
  2. Cung cấp các hàm: search, get_movie, get_recommendations.

Dữ liệu được chuẩn bị bởi ai_engine/export_model.py:
  - data/models/movie_dict.pkl  → list[dict] {movieId, tmdbId, title, poster_path}
  - data/models/similarity.pkl  → numpy ndarray (N×N) cosine similarity
  - data/processed/movies_enriched.csv → thông tin đầy đủ (overview, genres, cast, keywords)
"""

import ast
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from core.config import settings


# ─── Helper ──────────────────────────────────────────────────────────────────

def _parse_list_field(value) -> list[str]:
    """Parse chuỗi dạng "['a', 'b', 'c']" thành list Python thực sự."""
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    try:
        result = ast.literal_eval(str(value))
        return result if isinstance(result, list) else []
    except (ValueError, SyntaxError):
        return []


def _safe_int(value) -> Optional[int]:
    """Chuyển về int an toàn, trả None nếu không hợp lệ."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ─── Service ─────────────────────────────────────────────────────────────────

class RecommenderService:
    """
    Tải model AI và cung cấp các hàm nghiệp vụ cho backend API.
    Sử dụng dạng Singleton – chỉ khởi tạo một lần khi FastAPI startup.
    """

    def __init__(self):
        # Danh sách phim theo thứ tự index của ma trận similarity
        self._movie_dict: list[dict] = []
        # Ma trận cosine similarity (N×N)
        self._similarity: Optional[np.ndarray] = None
        # DataFrame đầy đủ từ movies_enriched.csv
        self._enriched_df: Optional[pd.DataFrame] = None
        # Reverse index: movieId (int) → vị trí trong _movie_dict
        self._id_to_index: dict[int, int] = {}
        self._loaded: bool = False

    # ─── Startup ─────────────────────────────────────────────────────────────

    def load(self) -> None:
        """
        Đọc toàn bộ dữ liệu model vào RAM.
        Gọi một lần duy nhất trong lifespan của FastAPI.
        """
        data_dir = Path(settings.DATA_DIR)
        model_dir = data_dir / "models"
        processed_dir = data_dir / "processed"

        dict_path = model_dir / "movie_dict.pkl"
        sim_path = model_dir / "similarity.pkl"
        enriched_path = processed_dir / "movies_enriched.csv"

        # Kiểm tra file model tồn tại
        if not dict_path.exists() or not sim_path.exists():
            print(
                f"⚠️  Không tìm thấy model tại: {model_dir}\n"
                "   Hãy chạy AI engine trước:\n"
                "   → Docker  : docker compose run --rm ai_engine\n"
                "   → Local   : cd ai_engine && python export_model.py"
            )
            return

        # Tải movie_dict
        with open(dict_path, "rb") as f:
            self._movie_dict = pickle.load(f)

        # Tải similarity matrix
        with open(sim_path, "rb") as f:
            self._similarity = pickle.load(f)

        # Xây dựng reverse index: movieId → list_index
        self._id_to_index = {
            int(m["movieId"]): idx
            for idx, m in enumerate(self._movie_dict)
        }

        # Tải enriched data để trả chi tiết đầy đủ
        if enriched_path.exists():
            self._enriched_df = pd.read_csv(enriched_path)
            self._enriched_df["movieId"] = self._enriched_df["movieId"].astype(int)
        else:
            print(f"⚠️  Không tìm thấy {enriched_path}. Chi tiết phim sẽ bị giới hạn.")

        self._loaded = True
        print(f"✅ Model sẵn sàng: {len(self._movie_dict):,} phim đã được tải vào bộ nhớ.")

    # ─── Properties ──────────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def movie_count(self) -> int:
        return len(self._movie_dict)

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _poster_url(self, poster_path) -> Optional[str]:
        """Tạo URL ảnh đầy đủ từ poster_path TMDB (vd: /abc.jpg)."""
        if not poster_path:
            return None
        if isinstance(poster_path, float) and np.isnan(poster_path):
            return None
        return f"{settings.TMDB_IMAGE_BASE_URL}{poster_path}"

    def _to_summary(self, record: dict) -> dict:
        """
        Chuyển một record từ movie_dict thành MovieSummary.
        Dùng cho kết quả search và danh sách recommendations.
        """
        return {
            "movieId": int(record["movieId"]),
            "tmdbId": _safe_int(record.get("tmdbId")),
            "title": record["title"],
            "poster_url": self._poster_url(record.get("poster_path")),
        }

    def _to_detail(self, row: pd.Series) -> dict:
        """
        Chuyển một row từ enriched DataFrame thành MovieDetail đầy đủ.
        Dùng cho endpoint chi tiết phim.
        """
        # Genres theo chuẩn MovieLens: "Adventure|Animation|Comedy"
        genres_ml: str = row.get("genres", "") or ""
        genres_list = [g.strip() for g in genres_ml.split("|") if g.strip()]

        overview = row.get("overview")
        return {
            "movieId": int(row["movieId"]),
            "tmdbId": _safe_int(row.get("tmdbId")),
            "title": row["title"],
            "overview": overview if pd.notna(overview) else None,
            "genres": genres_list,
            "tmdb_genres": _parse_list_field(row.get("tmdb_genres")),
            "keywords": _parse_list_field(row.get("keywords")),
            "cast": _parse_list_field(row.get("cast")),
            "poster_url": self._poster_url(row.get("poster_path")),
        }

    # ─── Public API ──────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Tìm kiếm phim theo tên (case-insensitive, substring match).
        Trả về danh sách MovieSummary.
        """
        q = query.strip().lower()
        results = [
            self._to_summary(m)
            for m in self._movie_dict
            if q in m["title"].lower()
        ]
        return results[:limit]

    def get_movie(self, movie_id: int) -> Optional[dict]:
        """
        Lấy thông tin chi tiết đầy đủ của một phim theo movieId.
        Ưu tiên dùng enriched CSV; fallback về movie_dict nếu chưa có.
        """
        # Fallback nếu chưa có enriched data
        if self._enriched_df is None:
            idx = self._id_to_index.get(movie_id)
            return self._to_summary(self._movie_dict[idx]) if idx is not None else None

        rows = self._enriched_df[self._enriched_df["movieId"] == movie_id]
        if rows.empty:
            return None
        return self._to_detail(rows.iloc[0])

    def get_recommendations(self, movie_id: int, n: int = 10) -> list[dict]:
        """
        Gợi ý Top-N phim tương tự dựa trên Cosine Similarity.
        Mỗi item trả về MovieSummary + trường similarity_score [0, 1].
        """
        if self._similarity is None:
            return []

        idx = self._id_to_index.get(movie_id)
        if idx is None:
            return []

        # Lấy điểm tương đồng với tất cả phim khác
        sim_scores: list[tuple[int, float]] = list(enumerate(self._similarity[idx]))
        # Sắp xếp giảm dần, loại bỏ chính bộ phim đó (score = 1.0)
        sim_scores.sort(key=lambda x: x[1], reverse=True)
        top = sim_scores[1 : n + 1]

        results = []
        for list_idx, score in top:
            item = self._to_summary(self._movie_dict[list_idx])
            item["similarity_score"] = round(float(score), 4)
            results.append(item)
        return results


# ─── Singleton instance (import ở mọi nơi) ───────────────────────────────────
recommender_service = RecommenderService()
