"use client";

import { useEffect, useState } from "react";

import { createInteraction, getInteractionStatus, unlikeMovie } from "@/lib/api";

const AUTH_STORAGE_KEY = "movie_recommender_auth_user";

type AuthUser = {
  user_id: number;
  username: string;
};

type MovieInteractionPanelProps = {
  movieId: number;
};

export default function MovieInteractionPanel({ movieId }: MovieInteractionPanelProps) {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [liked, setLiked] = useState(false);
  const [selectedRating, setSelectedRating] = useState<number | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw) as AuthUser;
      if (parsed?.user_id && parsed?.username) {
        setCurrentUser(parsed);
      }
    } catch {
      // Ignore invalid local storage data.
    }
  }, []);

  useEffect(() => {
    if (!currentUser) {
      setLiked(false);
      setSelectedRating(null);
      return;
    }

    let active = true;
    const loadStatus = async () => {
      try {
        const status = await getInteractionStatus(currentUser.user_id, movieId);
        if (!active) {
          return;
        }
        setLiked(status.liked);
        setSelectedRating(typeof status.latest_rating === "number" ? Math.round(status.latest_rating) : null);
      } catch {
        if (!active) {
          return;
        }
        setLiked(false);
        setSelectedRating(null);
      }
    };

    loadStatus();
    return () => {
      active = false;
    };
  }, [currentUser, movieId]);

  const toggleLike = async () => {
    if (!currentUser) {
      setError("Bạn cần đăng nhập ở trang chủ trước khi Like/Rate.");
      setMessage("");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      if (liked) {
        await unlikeMovie(currentUser.user_id, movieId);
        setLiked(false);
        setMessage("Đã hủy Like cho phim này.");
        return;
      }

      await createInteraction({
        user_id: currentUser.user_id,
        movie_id: movieId,
        interaction_type: "LIKE",
      });
      setLiked(true);
      setMessage("Đã lưu Like cho phim này.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể lưu tương tác.");
    } finally {
      setLoading(false);
    }
  };

  const submitInteraction = async (interactionType: "LIKE" | "RATING", ratingValue?: number) => {
    if (!currentUser) {
      setError("Bạn cần đăng nhập ở trang chủ trước khi Like/Rate.");
      setMessage("");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      await createInteraction({
        user_id: currentUser.user_id,
        movie_id: movieId,
        interaction_type: interactionType,
        rating_value: ratingValue,
      });

      if (interactionType === "RATING" && typeof ratingValue === "number") {
        setSelectedRating(ratingValue);
        setMessage(`Đã lưu đánh giá ${ratingValue}/5 cho phim này.`);
      } else {
        setLiked(true);
        setMessage("Đã lưu Like cho phim này.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể lưu tương tác.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mt-6 rounded-xl border border-slate-400/25 bg-white/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-200">Tương tác cá nhân</p>
        <p className="text-xs text-slate-300">
          {currentUser ? `Đăng nhập: ${currentUser.username}` : "Chưa đăng nhập"}
        </p>
      </div>

      <div className="mt-3 space-y-3">
        <div className="flex items-center justify-start">
          <button
            type="button"
            disabled={loading}
            onClick={toggleLike}
            className={`inline-flex min-w-28 items-center justify-center rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] transition disabled:cursor-not-allowed disabled:opacity-70 ${
              liked
                ? "border-transparent bg-(--accent) text-slate-950 shadow-[0_6px_18px_rgba(0,0,0,0.2)]"
                : "border-slate-300/35 bg-white/15 text-slate-100 hover:bg-white/20"
            }`}
          >
            {loading ? "Đang lưu..." : liked ? "Bỏ Like" : "Like"}
          </button>
        </div>

        <div className="rounded-lg border border-slate-300/20 bg-black/10 p-2">
          <p className="mb-2 text-[10px] uppercase tracking-widest text-slate-300">Đánh giá 1-5</p>
          <div className="grid grid-cols-5 gap-2">
            {[1, 2, 3, 4, 5].map((score) => (
              <button
                key={score}
                type="button"
                disabled={loading}
                onClick={() => submitInteraction("RATING", score)}
                className={`rounded-full border px-1 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-70 ${
                  selectedRating === score
                    ? "border-transparent bg-(--accent) text-slate-950 shadow-[0_8px_20px_rgba(0,0,0,0.24)]"
                    : "border-slate-300/35 bg-white/15 text-slate-100 hover:scale-105 hover:bg-white/25"
                }`}
              >
                {score}
              </button>
            ))}
          </div>
        </div>
      </div>

      {message ? <p className="mt-3 text-sm text-emerald-300">{message}</p> : null}
      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
    </section>
  );
}