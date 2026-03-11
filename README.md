# Movie Recommender Project

Hệ thống gợi ý phim dựa trên **Content-Based Filtering** (TF-IDF + Cosine Similarity), kết hợp dữ liệu từ **MovieLens** và **TMDB API**.

## Cấu trúc dự án

```
movie-recommender-project/
├── data/
│   ├── raw/            # Dữ liệu gốc MovieLens (movies.csv, links.csv, ratings.csv)
│   ├── processed/      # CSV đã crawl từ TMDB và làm sạch
│   └── models/         # Model AI xuất ra (similarity.pkl, movie_dict.pkl)
├── ai_engine/          # Pipeline xử lý dữ liệu & huấn luyện model
├── backend/            # REST API server (FastAPI)
├── frontend/           # Giao diện web (Next.js) — chưa tạo
├── .gitignore
└── README.md
```

## Tech Stack

| Tầng | Công nghệ |
|------|-----------|
| AI Engine | Python, Pandas, Scikit-learn, TMDB API |
| Backend | Python, FastAPI, Uvicorn |
| Frontend | Next.js, React, TypeScript |

## Cài đặt

**Yêu cầu:** Tạo file `.env` ở thư mục gốc:
```
TMDB_API_KEY=your_api_key_here
```

```bash
# AI Engine
cd ai_engine && pip install -r requirements.txt

# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

---

## TODO

### AI Engine
- [x] `01_crawl_tmdb_data.ipynb` — Crawl metadata từ TMDB (genres, cast, keywords, poster)
- [x] `02_data_cleaning.ipynb` — Làm sạch dữ liệu, tạo cột `soup`
- [x] `03_build_model.ipynb` — Xây dựng TF-IDF matrix & Cosine Similarity
- [x] `export_model.py` — Xuất model ra file `.pkl`

### Backend
- [ ] `main.py` — Khởi tạo FastAPI app, cấu hình CORS
- [ ] `services/recommender.py` — Load `.pkl`, logic gợi ý phim theo `movie_id`
- [ ] `api/routes.py` — Endpoint `GET /movies` và `GET /recommendations/{id}`
- [ ] `requirements.txt` — Khai báo fastapi, uvicorn, scikit-learn, pandas

### Frontend
- [ ] Khởi tạo project Next.js (App Router)
- [ ] `app/page.tsx` — Trang chủ hiển thị phim phổ biến (xử lý Cold-Start)
- [ ] `app/movies/[id]/page.tsx` — Trang chi tiết phim & danh sách gợi ý
- [ ] `components/MovieCard.tsx` — Component hiển thị poster phim
- [ ] `components/SearchBar.tsx` — Thanh tìm kiếm phim
- [ ] `components/Navbar.tsx` — Thanh điều hướng
- [ ] `lib/api.ts` — Hàm gọi API tới backend (`localhost:8000`)

### Khác
- [ ] `.gitignore` — Chặn `data/raw/`, `data/models/`, `__pycache__/`, `.env`, `node_modules/`
