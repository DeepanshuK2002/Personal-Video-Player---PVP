"use client";

import { useVotes } from "@/lib/votes";

export function CategoryRating({ slug, category }: { slug: string; category: string }) {
  const { rating } = useVotes(slug);

  return (
    <p className="text-center text-sm font-semibold text-brand-soft lg:hidden">
      {category}
      <span className="mx-1.5 inline-flex items-center gap-1 text-ink">
        ★ {rating.toFixed(1)}
      </span>
    </p>
  );
}
