const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type MovieSummary = {
  movieId: number;
  tmdbId: number | null;
  title: string;
  poster_url: string | null;
};

export type MovieDetail = {
  movieId: number;
  tmdbId: number | null;
  title: string;
  overview: string | null;
  genres: string[];
  tmdb_genres: string[];
  keywords: string[];
  cast: string[];
  poster_url: string | null;
};

export type Recommendation = MovieSummary & {
  similarity_score: number;
};

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function searchMovies(q: string, limit = 10) {
  return getJson<{ query: string; total: number; results: MovieSummary[] }>(
    `${API_BASE}/api/movies/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getMovie(movieId: number) {
  return getJson<MovieDetail>(`${API_BASE}/api/movies/${movieId}`);
}

export function getRecommendations(movieId: number, n = 10) {
  return getJson<{ movie: MovieDetail; n: number; recommendations: Recommendation[] }>(
    `${API_BASE}/api/movies/${movieId}/recommendations?n=${n}`
  );
}