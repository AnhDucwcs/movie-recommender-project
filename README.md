# Movie Recommender Project

Hệ thống gợi ý phim dựa trên **Content-Based Filtering** (TF-IDF + Cosine Similarity), kết hợp dữ liệu từ **MovieLens** và **TMDB API**.

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
│   ├── services/
│   │   └── recommender.py          # Load model, logic gợi ý
│   └── api/
│       └── routes.py               # Các endpoint REST
├── frontend/                       # Giao diện web (Next.js) — chưa tạo
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
| Backend | Python, FastAPI, Uvicorn |
| Frontend | Next.js, React, TypeScript *(chưa tạo)* |
| Hạ tầng | Docker, Docker Compose |

## API Endpoints

| Method | URL | Mô tả |
|--------|-----|-------|
| `GET` | `/api/health` | Trạng thái server và model |
| `GET` | `/api/movies/search?q=&limit=` | Tìm kiếm phim theo tên |
| `GET` | `/api/movies/{movie_id}` | Chi tiết một bộ phim |
| `GET` | `/api/movies/{movie_id}/recommendations?n=` | Gợi ý Top-N phim tương tự |

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
```

### Bước 4 — Tạo model AI *(chạy 1 lần duy nhất)*

```bash
docker compose run --rm ai_engine
```

Lệnh này sẽ tự động build model và lưu vào `data/models/`. Kiểm tra:

```bash
ls data/models/
# movie_dict.pkl  similarity.pkl
```

### Bước 5 — Chạy Backend

```bash
# Chạy nền (khuyến nghị)
docker compose up -d backend

# Hoặc xem log trực tiếp
docker compose up backend
```

### Bước 6 — Kiểm tra

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

# Dừng server
docker compose down

# Rebuild image sau khi sửa code
docker compose up -d --build backend

# Tạo lại model từ đầu
docker compose run --rm ai_engine
```

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
- [ ] Khởi tạo project Next.js (App Router)
- [ ] `app/page.tsx` — Trang chủ hiển thị phim phổ biến
- [ ] `app/movies/[id]/page.tsx` — Trang chi tiết phim & danh sách gợi ý
- [ ] `components/MovieCard.tsx` — Component hiển thị poster phim
- [ ] `components/SearchBar.tsx` — Thanh tìm kiếm phim
- [ ] `components/Navbar.tsx` — Thanh điều hướng
- [ ] `lib/api.ts` — Hàm gọi API tới backend

### DevOps / Hạ tầng
- [x] `docker-compose.yml` — Chạy local / Ubuntu
- [x] `Dockerfile` (gốc) — Multi-stage build cho cloud deploy
- [x] `render.yaml` — Cấu hình deploy lên Render.com
