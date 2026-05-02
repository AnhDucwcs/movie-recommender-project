# Movie Recommender Project

Hệ thống gợi ý phim dựa trên **Content-Based Filtering** (TF-IDF + Cosine Similarity), kết hợp dữ liệu từ **MovieLens** và **TMDB API**.

Phiên bản hiện tại hỗ trợ đầy đủ:
- Item-to-Item recommendation theo `movie_id`
- User-to-Item personalized recommendation theo lịch sử tương tác tích cực
- Cold-start fallback cho user mới bằng danh sách Trending
- Lưu tương tác người dùng vào PostgreSQL

## Cấu trúc dự án

```
movie-recommender-project/
├── data/
│   ├── raw/                        # Dữ liệu gốc MovieLens (movies.csv, links.csv, ratings.csv)
│   ├── processed/                  # CSV đã crawl từ TMDB và làm sạch
│   └── models/                     # Model AI xuất ra (similarity.pkl, movie_dict.pkl) — tự tạo khi chạy
├── ai_engine/                      # Pipeline xử lý dữ liệu & huấn luyện model
│   ├── 01_crawl_tmdb_data.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_build_model.ipynb
│   ├── export_model.py             # Script xuất model ra .pkl
│   ├── requirements.txt
│   └── Dockerfile
├── backend/                        # REST API server (FastAPI)
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── core/
│   │   └── config.py               # Cấu hình app (đọc .env)
│   ├── db/
│   │   ├── models.py               # ORM: users, interactions
│   │   ├── session.py              # SQLAlchemy session
│   │   └── init_db.py              # Tạo bảng khi startup
│   ├── services/
│   │   └── recommender.py          # Load model + logic trending/recommendation
│   └── api/
│       └── routes.py               # Các endpoint REST
├── frontend/                       # Giao diện web (Next.js)
├── docker/
│   └── postgres/
│       └── init/
│           ├── 01_schema.sql       # Schema khởi tạo DB
│           └── 02_seed_sample_data.sql  # Dữ liệu mẫu cho demo/test
├── Dockerfile                      # Multi-stage build dùng để deploy cloud
├── docker-compose.yml              # Dùng để chạy local / Ubuntu
├── render.yaml                     # Cấu hình deploy lên Render.com
├── .env.example                    # Mẫu biến môi trường
└── README.md
```

## Tech Stack

| Tầng | Công nghệ |
|------|-----------|
| AI Engine | Python, Pandas, Scikit-learn, NLTK, TMDB API |
| Backend | Python, FastAPI, Uvicorn, SQLAlchemy |
| Frontend | Next.js, React, TypeScript |
| Database | PostgreSQL (Docker), SQLite fallback |
| Hạ tầng | Docker, Docker Compose |

## API Endpoints

| Method | URL | Mô tả |
|--------|-----|-------|
| `GET` | `/api/health` | Trạng thái server và model |
| `GET` | `/api/movies/trending?limit=` | Top phim thịnh hành từ `ratings.csv` |
| `GET` | `/api/movies/search?q=&limit=` | Tìm kiếm phim theo tên |
| `GET` | `/api/movies/{movie_id}` | Chi tiết một bộ phim |
| `POST` | `/api/interactions` | Lưu tương tác người dùng (`LIKE`/`RATING`) |
| `GET` | `/api/recommendations/movie/{movie_id}?n=` | Gợi ý phim tương tự (item-to-item) |
| `GET` | `/api/recommendations/user/{user_id}?n=&history_limit=` | Gợi ý cá nhân hóa (user-to-item) |
| `GET` | `/api/movies/{movie_id}/recommendations?n=` | Legacy endpoint tương thích frontend cũ |

Xem tài liệu đầy đủ tại: `http://localhost:8000/docs`

---

## Chạy trên Ubuntu với Docker

### Yêu cầu

- Ubuntu 20.04 / 22.04 / 24.04
- Docker Engine & Docker Compose Plugin

### Bước 1 — Cài Docker (nếu chưa có)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Bước 2 — Clone repo

```bash
git clone https://github.com/<your-username>/movie-recommender-project.git
cd movie-recommender-project
```

### Bước 3 — Tạo file `.env`

```bash
cp .env.example .env
nano .env
```

Điền thông tin vào `.env`:

```
TMDB_API_KEY=your_api_key_here
DATA_DIR=../data
RATINGS_CSV_PATH=
TRENDING_DEFAULT_LIMIT=20
TRENDING_MAX_LIMIT=50
TRENDING_MIN_VOTES=0
DATABASE_URL=sqlite:///./movie_recommender.db
DB_ECHO=false
```

### Bước 4 — Tạo model AI *(chạy 1 lần duy nhất)*

```bash
docker compose run --rm ai_engine
```

Lệnh này sẽ tự động build model và lưu vào `data/models/`. Kiểm tra:

```bash
ls data/models/
# movie_dict.pkl  similarity.pkl  tfidf_vectorizer.pkl  tfidf_matrix.pkl
```

### Bước 5 — Khởi động Database + Backend

```bash
# Chạy DB trước (lần đầu sẽ tự chạy schema + seed trong docker/postgres/init)
docker compose up -d db

# Chạy backend
docker compose up -d --build backend

# (Tuỳ chọn) chạy cả DB + backend cùng lúc
# docker compose up -d --build db backend
```

### Bước 6 — Chạy Frontend (tuỳ chọn)

```bash
cd frontend
npm install
npm run dev
```

Frontend chạy tại `http://localhost:3001`.

### Bước 7 — Kiểm tra

```bash
curl http://localhost:8000/api/health
# {"status":"ok","model_loaded":true,"movies_count":...}
```

Hoặc mở trình duyệt: **`http://localhost:8000/docs`**

---

## Các lệnh thường dùng

```bash
# Xem log backend
docker compose logs -f backend

# Xem log database
docker compose logs -f db

# Dừng server
docker compose down

# Dừng và xoá volume DB (để seed chạy lại từ đầu)
docker compose down -v

# Rebuild image sau khi sửa code
docker compose up -d --build backend

# Tạo lại model từ đầu
docker compose run --rm ai_engine
```

---

## Kịch bản AI Đã Xác Nhận

### User 1 (Sci-fi fan, có điểm thấp cho Forrest Gump)
- Lọc positive history bằng điều kiện: `interaction_type='LIKE' OR rating_value>=4`.
- Phim `Forrest Gump (movieId=356, rating=2.0)` bị loại khỏi seed set.
- Kết quả gợi ý trả về cụm Sci-fi/Space như các phần Star Wars khác, Alien, Interstellar, ...

### User 2 (Romance + Animation)
- Seed set chứa `Titanic`, `Toy Story`, `Toy Story 2`, `Beauty and the Beast`.
- Kết quả nghiêng về cụm hoạt hình/tình cảm như `Toy Story 3`, `Pinocchio`, ...

### User 3 (Cold-start)
- Không có lịch sử tương tác.
- API tự fallback sang strategy `cold_start_trending_fallback`.
- Dữ liệu trả về lấy từ Top Trending tính trên `ratings.csv`.

---

## TODO

### AI Engine
- [x] `01_crawl_tmdb_data.ipynb` — Crawl metadata từ TMDB (genres, cast, keywords, poster)
- [x] `02_data_cleaning.ipynb` — Làm sạch dữ liệu, tạo cột `soup`
- [x] `03_build_model.ipynb` — Xây dựng TF-IDF matrix & Cosine Similarity
- [x] `export_model.py` — Xuất model ra file `.pkl`

### Backend
- [x] `main.py` — Khởi tạo FastAPI app, cấu hình CORS
- [x] `services/recommender.py` — Load `.pkl`, logic gợi ý phim theo `movie_id`
- [x] `api/routes.py` — Các endpoint search, detail, recommendations
- [x] `core/config.py` — Quản lý cấu hình qua biến môi trường
- [x] `requirements.txt` — Khai báo fastapi, uvicorn, scikit-learn, pandas

### Frontend
- [x] Khởi tạo project Next.js (App Router)
- [x] `app/page.tsx` — Trang chủ hiển thị phim phổ biến, tìm kiếm và trending
- [x] `app/movies/[id]/page.tsx` — Trang chi tiết phim & danh sách gợi ý
- [x] `app/movies/[id]/movie-interaction-panel.tsx` — Khu vực tương tác người dùng với phim
- [x] `components/movie-interaction-panel.tsx` — Component dùng lại cho phần tương tác
- [x] `app/layout.tsx` — Layout gốc và metadata của ứng dụng
- [x] `lib/api.ts` — Hàm gọi API tới backend

### DevOps / Hạ tầng
- [x] `docker-compose.yml` — Chạy local / Ubuntu
- [x] `Dockerfile` (gốc) — Multi-stage build cho cloud deploy
- [x] `render.yaml` — Cấu hình deploy lên Render.com
