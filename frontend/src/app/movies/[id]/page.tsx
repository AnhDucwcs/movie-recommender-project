import Link from "next/link";
import { notFound } from "next/navigation";

import MovieInteractionPanel from "@/components/movie-interaction-panel";
import { getMovie, getRecommendations } from "@/lib/api";

type MovieDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function MovieDetailPage({ params }: MovieDetailPageProps) {
  const { id } = await params;
  const movieId = Number(id);

  if (!Number.isInteger(movieId) || movieId <= 0) {
    notFound();
  }

  let movie;
  let rec;

  try {
    [movie, rec] = await Promise.all([getMovie(movieId), getRecommendations(movieId, 12)]);
  } catch {
    notFound();
  }

  return (
    <main className="page-wrap">
      <div className="content-layer mx-auto max-w-6xl px-4 py-8 md:px-6 md:py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-300 transition hover:text-white"
        >
          ← Quay lại tìm kiếm
        </Link>

        <section className="glass-panel fade-up mt-5 rounded-2xl p-4 md:mt-6 md:grid md:grid-cols-[230px_1fr] md:gap-8 md:p-6">
          <div className="mx-auto aspect-2/3 w-full max-w-64 overflow-hidden rounded-xl">
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

          <div className="mt-5 md:mt-0">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-300">Now Analyzing</p>
            <h1 className="title-display mt-2 text-4xl leading-none md:text-6xl">{movie.title}</h1>
            <p className="mt-4 text-sm leading-relaxed text-slate-200 md:text-base">
              {movie.overview || "Chưa có mô tả cho bộ phim này."}
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              {movie.genres.length > 0 ? (
                movie.genres.map((genre) => (
                  <span
                    key={genre}
                    className="rounded-full border border-slate-400/35 bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.08em] text-slate-100 md:text-sm"
                  >
                    {genre}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-300">Chưa có nhãn thể loại.</span>
              )}
            </div>

            <MovieInteractionPanel movieId={movie.movieId} />
          </div>
        </section>

        <section className="mt-8 md:mt-10">
          <div className="mb-4 flex items-end justify-between gap-3">
            <h2 className="title-display text-3xl md:text-4xl">Top Recommendations</h2>
            <p className="text-xs uppercase tracking-[0.14em] text-slate-300 md:text-sm">
              {rec.recommendations.length} phim tương tự
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 md:gap-5">
            {rec.recommendations.map((item, index) => (
              <Link
                key={item.movieId}
                href={`/movies/${item.movieId}`}
                className="movie-card fade-up rounded-2xl p-3 md:p-4"
                style={{ animationDelay: `${Math.min(index, 11) * 50}ms` }}
              >
                <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.14em] text-slate-600">
                  <span>#{String(index + 1).padStart(2, "0")}</span>
                  <span>{item.avg_score !== null ? `${item.avg_score}/5` : "Chưa có"}</span>
                </div>

                <div className="mb-3 aspect-2/3 overflow-hidden rounded-xl">
                  {item.poster_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.poster_url}
                      alt={item.title}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="poster-fallback h-full w-full">No Poster</div>
                  )}
                </div>

                <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 md:min-h-12 md:text-base md:leading-6">{item.title}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.12em] text-slate-600">
                  Rating trung bình: {item.avg_score !== null ? `${item.avg_score}/5` : "Chưa có dữ liệu"}
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
