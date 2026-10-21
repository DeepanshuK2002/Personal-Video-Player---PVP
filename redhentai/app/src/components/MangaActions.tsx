"use client";

import { Bookmark, ThumbsDown, ThumbsUp } from "lucide-react";
import { isSaved, toggleSaved } from "@/lib/saved";
import { useVotes } from "@/lib/votes";

export function MangaActions({ slug, title, showCounts = true }: { slug: string; title: string; showCounts?: boolean }) {
  const { votes, vote } = useVotes(slug);
  const saved = isSaved(slug);

  return (
    <div className="flex items-center justify-center gap-2">
      {/* Like count + dislike combined pill */}
      <div className="flex items-center rounded-full border border-white/10 bg-white/5">
        <button
          type="button"
          onClick={() => vote("like")}
          aria-pressed={votes.mine === "like"}
          className={`flex items-center gap-1.5 rounded-l-full px-3.5 py-2 text-sm font-medium transition ${
            votes.mine === "like"
              ? "text-brand-soft"
              : "text-ink-soft hover:text-ink"
          }`}
        >
          <ThumbsUp
            className="h-4 w-4"
            fill={votes.mine === "like" ? "currentColor" : "none"}
            aria-hidden
          />
          {showCounts &&
            (votes.likes >= 1000
              ? `${(votes.likes / 1000).toFixed(1)}k`
              : votes.likes)}
        </button>
        <span className="h-5 w-px bg-white/10" aria-hidden />
        <button
          type="button"
          onClick={() => vote("dislike")}
          aria-pressed={votes.mine === "dislike"}
          className={`flex items-center rounded-r-full px-3.5 py-2 text-sm font-medium transition ${
            votes.mine === "dislike"
              ? "text-brand-soft"
              : "text-ink-soft hover:text-ink"
          }`}
        >
          <ThumbsDown
            className="h-4 w-4"
            fill={votes.mine === "dislike" ? "currentColor" : "none"}
            aria-hidden
          />
        </button>
      </div>

      {/* Save bookmark */}
      <button
        type="button"
        onClick={() => toggleSaved(slug, title)}
        aria-pressed={saved}
        aria-label={saved ? "Unsave" : "Save"}
        className="flex h-10 w-10 items-center justify-center text-ink-soft transition hover:text-brand-soft"
      >
        <Bookmark className="h-5 w-5" fill={saved ? "currentColor" : "none"} aria-hidden />
      </button>
    </div>
  );
}
