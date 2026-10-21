"use client";

import { useVotes } from "@/lib/votes";

export function RatingDisplay({ slug }: { slug: string }) {
  const { rating } = useVotes(slug);

  return (
    <div className="flex items-center justify-center gap-2">
      <div className="flex items-center gap-0.5" aria-label={`Rating ${rating.toFixed(1)} out of 5`}>
        {Array.from({ length: 5 }, (_, i) => {
          const filled = i < Math.round(rating);
          return (
            <svg
              key={i}
              viewBox="0 0 24 24"
              className={`h-5 w-5 ${filled ? "fill-brand-soft text-brand-soft" : "fill-white/10 text-white/10"}`}
              aria-hidden
            >
              <path d="M12 2l2.9 6.6 7.1.7-5.4 4.8 1.6 7-6.2-3.8-6.2 3.8 1.6-7L2 9.3l7.1-.7z" />
            </svg>
          );
        })}
      </div>
      <span className="text-sm font-medium text-ink">{rating.toFixed(1)}</span>
      <span className="text-sm text-ink-faint">/ 5</span>
    </div>
  );
}
