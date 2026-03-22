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
from sklearn.metrics.pairwise import cosine_similarity

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
        # movieId -> soup string để tạo hồ sơ người dùng
        self._soup_by_movie_id: dict[int, str] = {}
        # TF-IDF artifacts cho gợi ý cá nhân hóa
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        # Reverse index: movieId (int) → vị trí trong _movie_dict
        self._id_to_index: dict[int, int] = {}
        # Dữ liệu xếp hạng trending từ ratings.csv
        self._trending_ids: list[int] = []
        self._trending_stats: dict[int, dict] = {}
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
        vectorizer_path = model_dir / "tfidf_vectorizer.pkl"
        matrix_path = model_dir / "tfidf_matrix.pkl"
        enriched_path = processed_dir / "movies_enriched.csv"
        cleaned_soup_path = processed_dir / "movies_cleaned_soup.csv"
        default_ratings_path = data_dir / "raw" / "ml-latest-small" / "ratings.csv"
        ratings_path = Path(settings.RATINGS_CSV_PATH) if settings.RATINGS_CSV_PATH else default_ratings_path

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

        # Tải TF-IDF artifacts (nếu có) để hỗ trợ personalized recommendation
        if vectorizer_path.exists() and matrix_path.exists():
            with open(vectorizer_path, "rb") as f:
                self._tfidf_vectorizer = pickle.load(f)
            with open(matrix_path, "rb") as f:
                self._tfidf_matrix = pickle.load(f)
        else:
            print(
                "⚠️  Không tìm thấy tfidf_vectorizer.pkl hoặc tfidf_matrix.pkl. "
                "API gợi ý cá nhân hóa sẽ bị giới hạn."
            )

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

        if cleaned_soup_path.exists():
            cleaned_df = pd.read_csv(cleaned_soup_path, usecols=["movieId", "soup"])
            cleaned_df["movieId"] = cleaned_df["movieId"].astype(int)
            cleaned_df["soup"] = cleaned_df["soup"].fillna("")
            self._soup_by_movie_id = {
                int(row["movieId"]): str(row["soup"]) for _, row in cleaned_df.iterrows()
            }
        else:
            print(f"⚠️  Không tìm thấy {cleaned_soup_path}. API user recommendations sẽ bị giới hạn.")

        if ratings_path.exists():
            ratings_df = pd.read_csv(ratings_path, usecols=["movieId", "rating"])
            grouped = (
                ratings_df.groupby("movieId", as_index=False)
                .agg(vote_count=("rating", "count"), avg_score=("rating", "mean"))
            )
            grouped["movieId"] = grouped["movieId"].astype(int)

            if settings.TRENDING_MIN_VOTES > 0:
                grouped = grouped[grouped["vote_count"] >= settings.TRENDING_MIN_VOTES]

            grouped = grouped.sort_values(["vote_count", "avg_score"], ascending=[False, False])

            self._trending_ids = [int(mid) for mid in grouped["movieId"].tolist()]
            self._trending_stats = {
                int(row["movieId"]): {
                    "interaction_count": int(row["vote_count"]),
                    "avg_score": round(float(row["avg_score"]), 2),
                }
                for _, row in grouped.iterrows()
            }
        else:
            print(f"⚠️  Không tìm thấy {ratings_path}. API trending sẽ fallback sang catalog mặc định.")

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

    def _summary_by_movie_id(self, movie_id: int) -> Optional[dict]:
        idx = self._id_to_index.get(int(movie_id))
        if idx is None:
            return None
        return self._to_summary(self._movie_dict[idx])

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
            item = self._summary_by_movie_id(int(self._movie_dict[list_idx]["movieId"]))
            if item is None:
                continue
            item["similarity_score"] = round(float(score), 4)
            results.append(item)
        return results

    def get_movie_summaries(self, movie_ids: list[int]) -> list[dict]:
        """Trả về danh sách MovieSummary theo đúng thứ tự movie_ids truyền vào."""
        results: list[dict] = []
        for movie_id in movie_ids:
            item = self._summary_by_movie_id(int(movie_id))
            if item is None:
                continue
            results.append(item)
        return results

    def get_trending_movies(self, limit: int) -> list[dict]:
        """
        Trả về danh sách phim trending dựa trên ratings.csv.
        Xếp hạng theo vote_count giảm dần, rồi avg_score giảm dần.
        """
        if not self._trending_ids:
            fallback = self.search(query="", limit=limit)
            for item in fallback:
                item["interaction_count"] = 0
                item["avg_score"] = None
            return fallback

        top_ids = self._trending_ids[:limit]
        movies = self.get_movie_summaries(top_ids)
        for item in movies:
            movie_id = int(item["movieId"])
            stats = self._trending_stats.get(movie_id, {"interaction_count": 0, "avg_score": None})
            item["interaction_count"] = stats["interaction_count"]
            item["avg_score"] = stats["avg_score"]
        return movies

    def get_personalized_recommendations(
        self,
        seed_movie_ids: list[int],
        n: int = 20,
    ) -> list[dict]:
        """
        Gợi ý cá nhân hóa từ tập seed movies tích cực của user.
        Cách làm: gộp soup -> tfidf.transform -> cosine_similarity với toàn bộ phim.
        """
        if self._tfidf_vectorizer is None or self._tfidf_matrix is None:
            return []

        valid_seed_ids = [mid for mid in seed_movie_ids if mid in self._soup_by_movie_id]
        if not valid_seed_ids:
            return []

        user_profile_soup = " ".join(self._soup_by_movie_id[mid] for mid in valid_seed_ids).strip()
        if not user_profile_soup:
            return []

        user_vector = self._tfidf_vectorizer.transform([user_profile_soup])
        scores = cosine_similarity(user_vector, self._tfidf_matrix).flatten()

        excluded = set(valid_seed_ids)
        ranked_indices = np.argsort(scores)[::-1]

        results: list[dict] = []
        for idx in ranked_indices:
            movie_record = self._movie_dict[int(idx)]
            movie_id = int(movie_record["movieId"])
            if movie_id in excluded:
                continue
            item = self._to_summary(movie_record)
            item["similarity_score"] = round(float(scores[int(idx)]), 4)
            results.append(item)
            if len(results) >= n:
                break

        return results


# ─── Singleton instance (import ở mọi nơi) ───────────────────────────────────
recommender_service = RecommenderService()
