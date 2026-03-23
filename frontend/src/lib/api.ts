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
  avg_score: number | null;
};

export type TrendingMovie = MovieSummary & {
  interaction_count: number;
  avg_score: number | null;
};

export type LoginResponse = {
  message: string;
  token: string;
  user: {
    user_id: number;
    username: string;
  };
};

export type UserRecommendationItem = MovieSummary & {
  similarity_score?: number;
  avg_score?: number | null;
  interaction_count?: number;
};

export type UserRecommendationsResponse = {
  user_id: number;
  strategy: string;
  seed_movie_ids: number[];
  recommendations: UserRecommendationItem[];
};

export type InteractionType = "LIKE" | "RATING";

export type CreateInteractionPayload = {
  user_id: number;
  movie_id: number;
  interaction_type: InteractionType;
  rating_value?: number;
};

export type InteractionStatusResponse = {
  user_id: number;
  movie_id: number;
  liked: boolean;
  latest_rating: number | null;
};

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = "Đăng nhập thất bại.";
    try {
      const data = (await res.json()) as { detail?: string };
      if (data?.detail) {
        detail = data.detail;
      }
    } catch {
      // Keep default error detail when response is not JSON.
    }
    throw new Error(detail);
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

export function getTrendingMovies(limit = 12) {
  return getJson<{
    strategy: string;
    total: number;
    results: TrendingMovie[];
  }>(`${API_BASE}/api/movies/trending?limit=${limit}`);
}

export function loginUser(username: string, password: string) {
  return postJson<LoginResponse>(`${API_BASE}/api/auth/login`, { username, password });
}

export function getUserRecommendations(userId: number, n = 12, historyLimit = 10) {
  return getJson<UserRecommendationsResponse>(
    `${API_BASE}/api/recommendations/user/${userId}?n=${n}&history_limit=${historyLimit}`
  );
}

export function createInteraction(payload: CreateInteractionPayload) {
  return postJson<{ message: string }>(`${API_BASE}/api/interactions`, payload);
}

async function deleteJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = "Yêu cầu thất bại.";
    try {
      const data = (await res.json()) as { detail?: string };
      if (data?.detail) {
        detail = data.detail;
      }
    } catch {
      // Keep fallback error message.
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function getInteractionStatus(userId: number, movieId: number) {
  return getJson<InteractionStatusResponse>(
    `${API_BASE}/api/interactions/status?user_id=${userId}&movie_id=${movieId}`
  );
}

export function unlikeMovie(userId: number, movieId: number) {
  return deleteJson<{ message: string; deleted: number }>(`${API_BASE}/api/interactions/like`, {
    user_id: userId,
    movie_id: movieId,
  });
}