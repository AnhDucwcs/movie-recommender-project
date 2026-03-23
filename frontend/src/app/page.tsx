"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  createInteraction,
  getInteractionStatus,
  MovieSummary,
  TrendingMovie,
  UserRecommendationItem,
  getTrendingMovies,
  getUserRecommendations,
  loginUser,
  searchMovies,
  unlikeMovie,
} from "@/lib/api";

const AUTH_STORAGE_KEY = "movie_recommender_auth_user";

export default function HomePage() {
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const trendingScrollRef = useRef<HTMLDivElement>(null);
  const personalizedScrollRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<MovieSummary[]>([]);
  const [suggestions, setSuggestions] = useState<MovieSummary[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [trending, setTrending] = useState<TrendingMovie[]>([]);
  const [loadingTrending, setLoadingTrending] = useState(true);
  const [trendingError, setTrendingError] = useState("");
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState<{ user_id: number; username: string } | null>(null);
  const [personalizedItems, setPersonalizedItems] = useState<UserRecommendationItem[]>([]);
  const [loadingPersonalized, setLoadingPersonalized] = useState(false);
  const [personalizedError, setPersonalizedError] = useState("");
  const [personalizedStrategy, setPersonalizedStrategy] = useState("");
  const [hasPersonalizedSeed, setHasPersonalizedSeed] = useState(false);
  const [interactionLoadingByMovie, setInteractionLoadingByMovie] = useState<Record<number, boolean>>({});
  const [likedByMovie, setLikedByMovie] = useState<Record<number, boolean>>({});
  const [interactionMessage, setInteractionMessage] = useState("");
  const [personalizedRefreshKey, setPersonalizedRefreshKey] = useState(0);

  const clearSearch = () => {
    setQuery("");
    setSuggestions([]);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const keyword = query.trim();
    if (keyword.length < 2) {
      setSuggestions([]);
      setLoadingSuggestions(false);
      return;
    }

    let active = true;
    const timer = setTimeout(async () => {
      setLoadingSuggestions(true);
      try {
        const data = await searchMovies(keyword, 6);
        if (active) {
          setSuggestions(data.results);
        }
      } catch {
        if (active) {
          setSuggestions([]);
        }
      } finally {
        if (active) {
          setLoadingSuggestions(false);
        }
      }
    }, 220);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as { user_id: number; username: string };
      if (parsed?.user_id && parsed?.username) {
        setCurrentUser(parsed);
      }
    } catch {
      // Ignore malformed cache and keep logged-out state.
    }
  }, []);

  useEffect(() => {
    try {
      if (!currentUser) {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        return;
      }
      window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(currentUser));
    } catch {
      // Ignore storage errors in private mode or restricted environments.
    }
  }, [currentUser]);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!searchBoxRef.current) {
        return;
      }
      if (!searchBoxRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    let active = true;

    const loadTrending = async () => {
      setLoadingTrending(true);
      setTrendingError("");
      try {
        const data = await getTrendingMovies(50);
        if (active) {
          setTrending(data.results);
        }
      } catch (err) {
        if (active) {
          setTrending([]);
          setTrendingError(err instanceof Error ? err.message : "Không tải được danh sách trending.");
        }
      } finally {
        if (active) {
          setLoadingTrending(false);
        }
      }
    };

    loadTrending();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!currentUser) {
      setPersonalizedItems([]);
      setPersonalizedError("");
      setPersonalizedStrategy("");
      setHasPersonalizedSeed(false);
      return;
    }

    let active = true;

    const loadPersonalized = async () => {
      setLoadingPersonalized(true);
      setPersonalizedError("");
      try {
        const data = await getUserRecommendations(currentUser.user_id, 12, 10);
        if (active) {
          setPersonalizedItems(data.recommendations);
          setPersonalizedStrategy(data.strategy);
          setHasPersonalizedSeed(data.seed_movie_ids.length > 0);
        }
      } catch (err) {
        if (active) {
          setPersonalizedItems([]);
          setPersonalizedStrategy("");
          setHasPersonalizedSeed(false);
          setPersonalizedError(err instanceof Error ? err.message : "Không tải được đề cử cá nhân hóa.");
        }
      } finally {
        if (active) {
          setLoadingPersonalized(false);
        }
      }
    };

    loadPersonalized();

    return () => {
      active = false;
    };
  }, [currentUser, personalizedRefreshKey]);

  useEffect(() => {
    if (!currentUser || personalizedItems.length === 0) {
      setLikedByMovie({});
      return;
    }

    let active = true;
    const loadLikeStates = async () => {
      try {
        const pairs = await Promise.all(
          personalizedItems.map(async (movie) => {
            const status = await getInteractionStatus(currentUser.user_id, movie.movieId);
            return [movie.movieId, status.liked] as const;
          })
        );
        if (!active) {
          return;
        }
        const nextMap: Record<number, boolean> = {};
        for (const [movieId, liked] of pairs) {
          nextMap[movieId] = liked;
        }
        setLikedByMovie(nextMap);
      } catch {
        if (!active) {
          return;
        }
        setLikedByMovie({});
      }
    };

    loadLikeStates();
    return () => {
      active = false;
    };
  }, [currentUser, personalizedItems]);

  const submitInteraction = async (movieId: number, interactionType: "LIKE" | "RATING", ratingValue?: number) => {
    if (!currentUser) {
      return;
    }

    setInteractionMessage("");
    setInteractionLoadingByMovie((prev) => ({ ...prev, [movieId]: true }));
    try {
      if (interactionType === "LIKE") {
        if (likedByMovie[movieId]) {
          await unlikeMovie(currentUser.user_id, movieId);
          setLikedByMovie((prev) => ({ ...prev, [movieId]: false }));
          setInteractionMessage("Đã hủy Like. Đang cập nhật đề cử cá nhân hóa...");
          setPersonalizedRefreshKey((prev) => prev + 1);
          return;
        }

        await createInteraction({
          user_id: currentUser.user_id,
          movie_id: movieId,
          interaction_type: "LIKE",
        });
        setLikedByMovie((prev) => ({ ...prev, [movieId]: true }));
        setInteractionMessage("Đã ghi nhận tương tác Like. Đang cập nhật đề cử cá nhân hóa...");
        setPersonalizedRefreshKey((prev) => prev + 1);
        return;
      }

      await createInteraction({
        user_id: currentUser.user_id,
        movie_id: movieId,
        interaction_type: "RATING",
        rating_value: ratingValue,
      });
      if (interactionType === "RATING" && typeof ratingValue === "number") {
        setInteractionMessage(`Đã lưu đánh giá ${ratingValue}/5. Đang cập nhật đề cử cá nhân hóa...`);
      } else {
        setInteractionMessage("Đã ghi nhận tương tác Like. Đang cập nhật đề cử cá nhân hóa...");
      }
      setPersonalizedRefreshKey((prev) => prev + 1);
    } catch (err) {
      setInteractionMessage(err instanceof Error ? err.message : "Không lưu được tương tác.");
    } finally {
      setInteractionLoadingByMovie((prev) => ({ ...prev, [movieId]: false }));
    }
  };

  const topRatedTrending = [...trending].sort((a, b) => {
    const scoreDiff = (b.avg_score ?? 0) - (a.avg_score ?? 0);
    if (scoreDiff !== 0) {
      return scoreDiff;
    }
    return b.interaction_count - a.interaction_count;
  });
  const visibleTrending = topRatedTrending.slice(0, 50);

  const formatRating = (score: number | null) => {
    if (score === null) {
      return "Chưa có";
    }
    return `${score.toFixed(1)}/5`;
  };

  const pickSuggestion = async (movie: MovieSummary) => {
    setQuery(movie.title);
    setShowSuggestions(false);
    setLoading(true);
    setError("");

    try {
      const data = await searchMovies(movie.title, 20);
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tìm kiếm phim.");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const q = query.trim();
    if (!q) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await searchMovies(q, 20);
      setResults(data.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tìm kiếm phim.");
    } finally {
      setLoading(false);
    }
  };

  const onLoginSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const username = loginUsername.trim();
    const password = loginPassword.trim();

    if (!username || !password) {
      setLoginError("Vui lòng nhập đầy đủ tài khoản và mật khẩu.");
      return;
    }

    setLoginLoading(true);
    setLoginError("");

    try {
      const data = await loginUser(username, password);
      setCurrentUser(data.user);
      setShowLoginModal(false);
      setLoginUsername("");
      setLoginPassword("");
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setLoginLoading(false);
    }
  };

  const scrollHorizontal = (ref: React.RefObject<HTMLDivElement | null>, direction: "left" | "right") => {
    if (!ref.current) {
      return;
    }
    const delta = direction === "left" ? -760 : 760;
    ref.current.scrollBy({ left: delta, behavior: "smooth" });
  };

  const scrollHorizontalToEdge = (ref: React.RefObject<HTMLDivElement | null>, edge: "start" | "end") => {
    if (!ref.current) {
      return;
    }
    const left = edge === "start" ? 0 : ref.current.scrollWidth;
    ref.current.scrollTo({ left, behavior: "smooth" });
  };

  const shouldShowPersonalizedSection = !!currentUser && (loadingPersonalized || hasPersonalizedSeed);

  return (
    <main className="page-wrap">
      <div className="content-layer mx-auto max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <header className="fade-up">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="mb-2 text-xs uppercase tracking-[0.24em] text-[var(--text-dim)] md:text-sm">
                Content-Based Movie Explorer
              </p>
              <h1 className="title-display text-5xl leading-none md:text-7xl">
                Film Compass
              </h1>
              <p className="mt-3 max-w-2xl text-sm text-[var(--text-dim)] md:text-base">
                Nhập một bộ phim bạn thích để khám phá các lựa chọn tương tự bằng TF-IDF và Cosine Similarity.
              </p>
            </div>

            <button
              type="button"
              onClick={() => {
                if (currentUser) {
                  setCurrentUser(null);
                  setPersonalizedItems([]);
                  setInteractionMessage("");
                  return;
                }
                setShowLoginModal(true);
                setLoginError("");
              }}
              className="rounded-xl border border-white/30 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white transition hover:bg-white/20 md:text-sm"
            >
              {currentUser ? `Đăng xuất (${currentUser.username})` : "Đăng nhập"}
            </button>
          </div>
        </header>

        <section className="search-shell fade-up relative z-40 mt-7 rounded-2xl p-4 md:mt-8 md:p-5">
          <p className="mb-3 text-xs uppercase tracking-[0.2em] text-slate-300 md:text-sm">
            Smart Search
          </p>

          <form onSubmit={onSubmit} className="grid gap-3 md:grid-cols-[1fr_auto] md:items-start">
            <div className="relative w-full" ref={searchBoxRef}>
              <div className="search-command flex items-center gap-2 rounded-xl px-3 py-2">
                <svg
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  className="h-5 w-5 shrink-0 text-slate-300"
                >
                  <path
                    fill="currentColor"
                    d="M10 2a8 8 0 1 1 5.29 14l4.35 4.35a1 1 0 0 1-1.42 1.42l-4.35-4.35A8 8 0 0 1 10 2Zm0 2a6 6 0 1 0 0 12a6 6 0 0 0 0-12Z"
                  />
                </svg>

                <input
                  className="w-full bg-transparent py-2 text-sm text-white outline-none placeholder:text-slate-400 md:text-base"
                  placeholder="Tìm theo tên phim: Inception, Spider-Man, Interstellar..."
                  value={query}
                  onFocus={() => setShowSuggestions(true)}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setShowSuggestions(true);
                  }}
                />

                {query.trim().length > 0 ? (
                  <button
                    type="button"
                    onClick={clearSearch}
                    className="rounded-md px-2 py-1 text-xs uppercase tracking-[0.12em] text-slate-300 transition hover:bg-white/10 hover:text-white"
                  >
                    xoa
                  </button>
                ) : null}
              </div>

              {showSuggestions && query.trim().length >= 2 ? (
                <div className="suggestion-panel absolute left-0 right-0 top-[calc(100%+10px)] z-1000 overflow-hidden rounded-xl">
                  {loadingSuggestions ? (
                    <p className="px-4 py-3 text-sm text-slate-300">Đang gợi ý...</p>
                  ) : suggestions.length > 0 ? (
                    <ul className="max-h-72 overflow-y-auto">
                      {suggestions.map((movie) => (
                        <li key={movie.movieId}>
                          <button
                            type="button"
                            onClick={() => pickSuggestion(movie)}
                            className="suggestion-item flex w-full items-center gap-3 border-b border-white/10 px-4 py-3 text-left"
                          >
                            <div className="h-12 w-9 shrink-0 overflow-hidden rounded-md bg-[#1f2e58]">
                              {movie.poster_url ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img src={movie.poster_url} alt={movie.title} className="h-full w-full object-cover" />
                              ) : (
                                <div className="poster-fallback h-full w-full text-[10px]">No</div>
                              )}
                            </div>

                            <div className="min-w-0 flex-1">
                              <p className="line-clamp-1 text-sm text-white md:text-base">{movie.title}</p>
                              <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-slate-300">Mở danh sách gợi ý</p>
                            </div>

                            <span className="hint-key rounded px-2 py-1 text-[10px] uppercase tracking-[0.12em] text-slate-300">
                              Enter
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="px-4 py-3 text-sm text-slate-300">Không có gợi ý phù hợp.</p>
                  )}
                </div>
              ) : null}

              <p className="mt-2 text-xs text-slate-300">
                Mẹo: gõ ít nhất 2 ký tự để hiện gợi ý nhanh.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-70 md:min-h-[54px] md:text-base"
            >
              {loading ? "Đang phân tích..." : "Gợi ý ngay"}
            </button>
          </form>

          {error ? <p className="mt-3 text-sm text-amber-300">{error}</p> : null}
          {!error && results.length > 0 ? (
            <p className="mt-3 text-sm text-[var(--text-dim)]">Tìm thấy {results.length} kết quả phù hợp.</p>
          ) : null}
        </section>

        {results.length > 0 ? (
          <section className="mt-8 md:mt-10">
            <h2 className="title-display text-3xl md:text-4xl">Danh sách phù hợp</h2>
            <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
              {results.map((movie, index) => (
                <Link
                  key={movie.movieId}
                  href={`/movies/${movie.movieId}`}
                  className="movie-card fade-up rounded-2xl p-3 md:p-4"
                  style={{ animationDelay: `${Math.min(index, 11) * 40}ms` }}
                >
                  <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.14em] text-slate-600">
                    <span>#{String(index + 1).padStart(2, "0")}</span>
                    <span>MovieLens</span>
                  </div>

                  <div className="mb-3 aspect-[2/3] overflow-hidden rounded-xl">
                    {movie.poster_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={movie.poster_url}
                        alt={movie.title}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="poster-fallback h-full w-full">No Poster</div>
                    )}
                  </div>

                  <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 md:min-h-12 md:text-base md:leading-6">{movie.title}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.12em] text-slate-600">Xem gợi ý tương tự</p>
                </Link>
              ))}
            </div>
          </section>
        ) : (
          <section className="mt-8 rounded-2xl border border-dashed border-[var(--line)] p-5 text-sm text-[var(--text-dim)] md:mt-10 md:p-6 md:text-base">
            Bắt đầu bằng cách nhập tên một bộ phim để hệ thống đề xuất các phim có nội dung gần nhất.
          </section>
        )}

        <section className="mt-8 md:mt-10">
          <div className="mb-4 flex items-end justify-between gap-3">
            <h2 className="title-display text-3xl md:text-4xl">Top Rated Trending</h2>
            <div className="flex items-center gap-2">
              <p className="text-xs uppercase tracking-[0.14em] text-slate-300 md:text-sm">
                Hiển thị {visibleTrending.length} phim
              </p>
              <button
                type="button"
                onClick={() => scrollHorizontalToEdge(trendingScrollRef, "start")}
                className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-xs text-white transition hover:bg-white/20"
                aria-label="Về đầu danh sách trending"
              >
                &lt;&lt;
              </button>
              <button
                type="button"
                onClick={() => scrollHorizontal(trendingScrollRef, "left")}
                className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-sm text-white transition hover:bg-white/20"
                aria-label="Cuộn trái danh sách trending"
              >
                &lt;
              </button>
              <button
                type="button"
                onClick={() => scrollHorizontal(trendingScrollRef, "right")}
                className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-sm text-white transition hover:bg-white/20"
                aria-label="Cuộn phải danh sách trending"
              >
                &gt;
              </button>
              <button
                type="button"
                onClick={() => scrollHorizontalToEdge(trendingScrollRef, "end")}
                className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-xs text-white transition hover:bg-white/20"
                aria-label="Về cuối danh sách trending"
              >
                &gt;&gt;
              </button>
            </div>
          </div>

          {loadingTrending ? (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
              {Array.from({ length: 8 }).map((_, index) => (
                <div
                  key={index}
                  className="movie-card rounded-2xl p-3 opacity-70 md:p-4"
                >
                  <div className="mb-3 aspect-2/3 animate-pulse rounded-xl bg-slate-300/40" />
                  <div className="h-4 animate-pulse rounded bg-slate-300/40" />
                  <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-slate-300/30" />
                </div>
              ))}
            </div>
          ) : trendingError ? (
            <div className="rounded-2xl border border-amber-300/40 bg-amber-400/10 p-4 text-sm text-amber-200">
              Không thể tải trending: {trendingError}
            </div>
          ) : topRatedTrending.length > 0 ? (
            <div
              ref={trendingScrollRef}
              className="movie-carousel"
            >
              {visibleTrending.map((movie, index) => (
                <Link
                  key={movie.movieId}
                  href={`/movies/${movie.movieId}`}
                  className="movie-carousel-item movie-card fade-up rounded-2xl p-3 md:p-4"
                  style={{ animationDelay: `${Math.min(index, 11) * 40}ms` }}
                >
                  <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.14em] text-slate-600">
                    <span>#{String(index + 1).padStart(2, "0")}</span>
                    <span>{formatRating(movie.avg_score)}</span>
                  </div>

                  <div className="mb-3 aspect-2/3 overflow-hidden rounded-xl">
                    {movie.poster_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={movie.poster_url}
                        alt={movie.title}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="poster-fallback h-full w-full">No Poster</div>
                    )}
                  </div>

                  <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 md:min-h-12 md:text-base md:leading-6">{movie.title}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.12em] text-slate-600">Rating: {formatRating(movie.avg_score)}</p>
                </Link>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-(--line) p-5 text-sm text-(--text-dim) md:p-6 md:text-base">
              Chưa có dữ liệu trending.
            </div>
          )}

        </section>

        {shouldShowPersonalizedSection ? (
          <section className="mt-8 md:mt-10">
            <div className="mb-4 flex items-end justify-between gap-3">
              <h2 className="title-display text-3xl md:text-4xl">Đề Cử Cho Bạn</h2>
              <div className="flex items-center gap-2">
                <p className="text-xs uppercase tracking-[0.14em] text-slate-300 md:text-sm">
                  @{currentUser.username}
                </p>
                <button
                  type="button"
                  onClick={() => scrollHorizontalToEdge(personalizedScrollRef, "start")}
                  className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-xs text-white transition hover:bg-white/20"
                  aria-label="Về đầu danh sách đề cử cá nhân"
                >
                  &lt;&lt;
                </button>
                <button
                  type="button"
                  onClick={() => scrollHorizontal(personalizedScrollRef, "left")}
                  className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-sm text-white transition hover:bg-white/20"
                  aria-label="Cuộn trái danh sách đề cử cá nhân"
                >
                  &lt;
                </button>
                <button
                  type="button"
                  onClick={() => scrollHorizontal(personalizedScrollRef, "right")}
                  className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-sm text-white transition hover:bg-white/20"
                  aria-label="Cuộn phải danh sách đề cử cá nhân"
                >
                  &gt;
                </button>
                <button
                  type="button"
                  onClick={() => scrollHorizontalToEdge(personalizedScrollRef, "end")}
                  className="rounded-lg border border-white/30 bg-white/10 px-2 py-1 text-xs text-white transition hover:bg-white/20"
                  aria-label="Về cuối danh sách đề cử cá nhân"
                >
                  &gt;&gt;
                </button>
              </div>
            </div>

            {loadingPersonalized ? (
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} className="movie-card rounded-2xl p-3 opacity-70 md:p-4">
                    <div className="mb-3 aspect-2/3 animate-pulse rounded-xl bg-slate-300/40" />
                    <div className="h-4 animate-pulse rounded bg-slate-300/40" />
                    <div className="mt-2 h-3 w-2/3 animate-pulse rounded bg-slate-300/30" />
                  </div>
                ))}
              </div>
            ) : personalizedError ? (
              <div className="rounded-2xl border border-amber-300/40 bg-amber-400/10 p-4 text-sm text-amber-200">
                Không thể tải đề cử cá nhân hóa: {personalizedError}
              </div>
            ) : personalizedItems.length > 0 ? (
              <>
                <div
                  ref={personalizedScrollRef}
                  className="movie-carousel"
                >
                  {personalizedItems.map((movie, index) => (
                    <div
                      key={movie.movieId}
                      className="movie-carousel-item movie-card fade-up rounded-2xl p-3 md:p-4"
                      style={{ animationDelay: `${Math.min(index, 11) * 40}ms` }}
                    >
                      <Link href={`/movies/${movie.movieId}`}>
                        <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.14em] text-slate-600">
                          <span>#{String(index + 1).padStart(2, "0")}</span>
                          <span>
                            {typeof movie.similarity_score === "number"
                              ? `${Math.round(movie.similarity_score * 100)}% match`
                              : formatRating(movie.avg_score ?? null)}
                          </span>
                        </div>

                        <div className="mb-3 aspect-2/3 overflow-hidden rounded-xl">
                          {movie.poster_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={movie.poster_url} alt={movie.title} className="h-full w-full object-cover" />
                          ) : (
                            <div className="poster-fallback h-full w-full">No Poster</div>
                          )}
                        </div>

                        <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 md:min-h-12 md:text-base md:leading-6">{movie.title}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.12em] text-slate-600">
                          {typeof movie.similarity_score === "number"
                            ? `Độ phù hợp: ${movie.similarity_score.toFixed(3)}`
                            : `Rating: ${formatRating(movie.avg_score ?? null)}`}
                        </p>
                      </Link>

                      <div className="mt-3 space-y-2">
                        <button
                          type="button"
                          disabled={!!interactionLoadingByMovie[movie.movieId]}
                          onClick={() => submitInteraction(movie.movieId, "LIKE")}
                          className="w-full rounded-lg border border-slate-500/40 bg-white/20 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-900 transition hover:bg-white/30 disabled:opacity-60"
                        >
                          {interactionLoadingByMovie[movie.movieId]
                            ? "Đang lưu..."
                            : likedByMovie[movie.movieId]
                              ? "Bỏ Like"
                              : "Like"}
                        </button>
                        <div>
                          <p className="mb-1 text-[10px] uppercase tracking-[0.08em] text-slate-700">Rate 1-5</p>
                          <div className="grid grid-cols-5 gap-1">
                            {[1, 2, 3, 4, 5].map((score) => (
                              <button
                                key={score}
                                type="button"
                                disabled={!!interactionLoadingByMovie[movie.movieId]}
                                onClick={() => submitInteraction(movie.movieId, "RATING", score)}
                                className="rounded-md border border-slate-500/40 bg-(--accent) px-1 py-1 text-[10px] font-semibold text-slate-950 transition hover:brightness-105 disabled:opacity-60"
                              >
                                {score}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {interactionMessage ? (
                  <p className="mt-3 text-xs uppercase tracking-[0.12em] text-slate-300">{interactionMessage}</p>
                ) : null}
                <p className="mt-3 text-xs uppercase tracking-[0.12em] text-slate-300">
                  Strategy: {personalizedStrategy}
                </p>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-(--line) p-5 text-sm text-(--text-dim) md:p-6 md:text-base">
                Chưa có đề cử cá nhân hóa cho tài khoản này.
              </div>
            )}
          </section>
        ) : null}

      </div>

      {showLoginModal ? (
        <div
          className="fixed inset-0 z-1200 flex items-center justify-center bg-[#020617]/70 px-4 backdrop-blur-sm"
          onClick={() => {
            if (!loginLoading) {
              setShowLoginModal(false);
            }
          }}
        >
          <div
            className="glass-panel w-full max-w-md rounded-2xl p-5 md:p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-300">Member Access</p>
                <h2 className="title-display mt-2 text-3xl md:text-4xl">Đăng Nhập</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowLoginModal(false)}
                className="rounded-md border border-white/25 px-2 py-1 text-xs uppercase tracking-widest text-slate-200 hover:bg-white/10"
              >
                Đóng
              </button>
            </div>

            <form onSubmit={onLoginSubmit}>
              <div className="space-y-3">
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-slate-300">Tài khoản</span>
                  <input
                    type="text"
                    value={loginUsername}
                    onChange={(e) => setLoginUsername(e.target.value)}
                    placeholder="nguyen_van_a"
                    className="w-full rounded-xl border border-white/20 bg-[#111a33] px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-400 focus:border-white/45"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-[0.12em] text-slate-300">Mật khẩu</span>
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="movie123"
                    className="w-full rounded-xl border border-white/20 bg-[#111a33] px-3 py-2 text-sm text-white outline-none transition placeholder:text-slate-400 focus:border-white/45"
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={loginLoading}
                className="mt-4 w-full rounded-xl bg-(--accent) px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {loginLoading ? "Đang đăng nhập..." : "Đăng nhập"}
              </button>

              {loginError ? <p className="mt-3 text-xs text-amber-300">{loginError}</p> : null}
              <p className="mt-3 text-[11px] text-slate-300">Tài khoản demo: nguyen_van_a, tran_thi_b, le_van_c. Mật khẩu mặc định: movie123.</p>
            </form>
          </div>
        </div>
      ) : null}
    </main>
  );
}