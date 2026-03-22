from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── TMDB ──────────────────────────────────────────────────────────────────
    TMDB_API_KEY: str = ""
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/w500"

    # ── Đường dẫn data ────────────────────────────────────────────────────────
    # Mặc định: "../data" → hoạt động khi chạy `uvicorn main:app` từ thư mục backend/
    # Docker  : được override thành "/app/data" qua biến môi trường trong docker-compose.yml
    DATA_DIR: str = "../data"

    # ── Cấu hình gợi ý ────────────────────────────────────────────────────────
    TOP_N_DEFAULT: int = 10
    TOP_N_MAX: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Cho phép đọc biến môi trường hệ thống (ưu tiên hơn .env)
        case_sensitive=False,
    )


settings = Settings()