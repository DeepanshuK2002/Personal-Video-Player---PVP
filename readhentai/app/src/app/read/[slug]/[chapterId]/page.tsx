"use client";

// Chapter reader. Fetches the ordered page list for a chapter from the app's
// /api route and renders pages top-to-bottom in the provider's exact order.
// Unavailable chapters and failed images degrade gracefully. All data fetching
// happens client-side in effects, so this route prerenders as a static shell.

import { useEffect, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useChapterPages } from "@/lib/content";
import { addHistory } from "@/lib/history";

export default function ReaderPage({
  params,
}: {
  params: Promise<{ slug: string; chapterId: string }>;
}) {
  // Next 16 passes params as a Promise; unwrap synchronously via a small shim
  // by reading the resolved values in state.
  const [resolved, setResolved] = useState<{ slug: string; chapterId: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    params.then((p) => {
      if (!cancelled) setResolved(p);
    });
    return () => {
      cancelled = true;
    };
  }, [params]);

  const slug = resolved?.slug ?? null;
  const chapterId = resolved?.chapterId ?? null;

  // Track reading history (bounded to 12, keyed by the title slug).
  useEffect(() => {
    if (slug) addHistory(slug.split("#")[0]);
  }, [slug]);

  const { pages, loading, error } = useChapterPages(slug, chapterId);
  const [failed, setFailed] = useState<Set<number>>(new Set());

  const baseSlug = slug?.split("#")[0] ?? "";
  const backHref = baseSlug ? `/manga/${baseSlug}` : "/";

  return (
    <AppShell>
      <div className="mx-auto max-w-[820px] px-3 pb-16 pt-4 sm:px-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <a
            href={backHref}
            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-ink-soft transition hover:border-brand-soft hover:text-ink"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back to title
          </a>
          <span className="text-xs text-ink-faint">
            Chapter{resolved ? "" : "…"}
          </span>
        </div>

        {loading && (
          <div className="space-y-3" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-lg bg-white/5" />
            ))}
          </div>
        )}

        {error && (
          <div className="flex min-h-40 flex-col items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 p-6 text-center">
            <p className="text-sm text-ink-soft">This chapter is unavailable right now.</p>
            <p className="text-xs text-ink-faint">{error}</p>
            <a href={backHref} className="mt-2 text-sm text-brand-soft hover:underline">
              Go back
            </a>
          </div>
        )}

        {!loading && !error && pages.length === 0 && (
          <p className="mt-16 text-center text-sm text-ink-faint">
            No readable pages available for this chapter.
          </p>
        )}

        {pages.length > 0 && (
          <div className="space-y-2">
            {pages.map((src, i) =>
              failed.has(i) ? (
                <div
                  key={i}
                  className="flex aspect-[2/3] w-full items-center justify-center rounded-lg border border-white/10 bg-white/5 text-xs text-ink-faint"
                >
                  Page {i + 1} unavailable
                </div>
              ) : (
                <img
                  key={i}
                  src={src}
                  alt={`Page ${i + 1}`}
                  loading={i < 2 ? "eager" : "lazy"}
                  onError={() =>
                    setFailed((prev) => {
                      const next = new Set(prev);
                      next.add(i);
                      return next;
                    })
                  }
                  className="w-full rounded-lg"
                />
              ),
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
