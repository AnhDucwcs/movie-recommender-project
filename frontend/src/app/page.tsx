"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { MovieSummary, searchMovies } from "@/lib/api";

export default function HomePage() {
  const searchBoxRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<MovieSummary[]>([]);
  const [suggestions, setSuggestions] = useState<MovieSummary[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

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

  return (
    <main className="page-wrap">
      <div className="content-layer mx-auto max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <header className="fade-up">
          <p className="mb-2 text-xs uppercase tracking-[0.24em] text-[var(--text-dim)] md:text-sm">
            Content-Based Movie Explorer
          </p>
          <h1 className="title-display text-5xl leading-none md:text-7xl">
            Film Compass
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-[var(--text-dim)] md:text-base">
            Nhập một bộ phim bạn thích để khám phá các lựa chọn tương tự bằng TF-IDF và Cosine Similarity.
          </p>
        </header>

        <section className="search-shell fade-up mt-7 rounded-2xl p-4 md:mt-8 md:p-5">
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
                <div className="suggestion-panel absolute left-0 right-0 top-[calc(100%+10px)] z-20 overflow-hidden rounded-xl">
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

                  <p className="line-clamp-2 text-sm font-semibold md:text-base">{movie.title}</p>
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
      </div>
    </main>
  );
}