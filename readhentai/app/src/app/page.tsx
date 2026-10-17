"use client";

import { useEffect, useRef, useState } from "react";
import { Bookmark, ChevronLeft, ChevronRight, Copy, EllipsisVertical, Eye, Minimize2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MangaCard } from "@/components/MangaCard";
import { TrendingSection } from "@/components/TrendingSection";
import { Pagination } from "@/components/Pagination";
import { useTitles, resolveSlug } from "@/lib/content";
import { CoverImage } from "@/components/CoverImage";
import { getHistory } from "@/lib/history";
import { isSaved, toggleSaved } from "@/lib/saved";
import { useContentType } from "@/lib/contentType";
import type { Manga } from "@/lib/manga";

export default function Home() {
  const contentType = useContentType();
  const [historySlugs, setHistorySlugs] = useState<string[]>([]);
  const [historyItems, setHistoryItems] = useState<Manga[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [menuSlug, setMenuSlug] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  // Latest release feed (server-aggregated from providers).
  const { items: latest, loading: latestLoading } = useTitles("/api/latest?limit=24");

  const updateScrollState = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  };

  const scroll = (dir: -1 | 1) => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollBy({ left: dir * 260, behavior: "smooth" });
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    updateScrollState();
    const onScroll = () => updateScrollState();
    el.addEventListener("scroll", onScroll);
    const ro = new ResizeObserver(updateScrollState);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [historySlugs, showAll, minimized]);

  useEffect(() => {
    const sync = () => setHistorySlugs(getHistory());
    sync();
    window.addEventListener("history-change", sync);
    return () => window.removeEventListener("history-change", sync);
  }, []);

  // Resolve persisted history slugs to live titles (gracefully skipping any
  // that the provider no longer serves).
  useEffect(() => {
    let cancelled = false;
    if (historySlugs.length === 0) {
      setHistoryItems([]);
      return;
    }
    Promise.all(historySlugs.map((s) => resolveSlug(s)))
      .then((resolved) => {
        if (cancelled) return;
        setHistoryItems(resolved.filter((m): m is Manga => Boolean(m && !m.unavailable)));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [historySlugs]);

  useEffect(() => {
    if (!menuSlug) return;
    const onClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest(".history-menu")) setMenuSlug(null);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuSlug]);

  const visibleHistory = showAll ? historyItems : historyItems.slice(0, 6);

  const visibleLatest =
    contentType === "All"
      ? latest
      : latest.filter((m) => m.contentType === contentType);

  return (
    <AppShell>
      <TrendingSection />

      {historyItems.length > 0 && (
        <>
          <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-8" style={{ marginBottom: 8 }}>
            <hr className="border-t border-white/10" />
          </div>
          <section
            aria-labelledby="history-title"
            className="mx-auto max-w-[1440px] px-4 pb-2 pt-2 sm:px-6 md:pt-3 lg:px-8"
          >
        <div className="relative flex items-center justify-start">
          <h2 id="history-title" className="text-left text-2xl font-medium tracking-tight text-ink">
            History
          </h2>
          <div className="absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1">
            {!minimized && historyItems.length > 0 && (
              <>
                <button
                  type="button"
                  aria-label="Scroll left"
                  disabled={!canScrollLeft}
                  onClick={() => scroll(-1)}
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" aria-hidden />
                </button>
                <button
                  type="button"
                  aria-label="Scroll right"
                  disabled={!canScrollRight}
                  onClick={() => scroll(1)}
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" aria-hidden />
                </button>
              </>
            )}
            <button
              type="button"
              aria-label="History options"
              onClick={() => setMenuOpen((v) => !v)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-ink-soft transition hover:bg-white/10 hover:text-ink"
            >
              <EllipsisVertical className="h-5 w-5" aria-hidden />
            </button>
            {menuOpen && (
              <div className="absolute right-0 top-full z-30 mt-2 w-36 overflow-hidden rounded-xl border border-white/10 bg-[#1c1c1c]/95 py-1 shadow-xl shadow-black/50 backdrop-blur">
                <button
                  type="button"
                  onClick={() => {
                    setShowAll(true);
                    setMenuOpen(false);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
                >
                  <Eye className="h-4 w-4" aria-hidden />
                  View all
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMinimized(true);
                    setMenuOpen(false);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
                >
                  <Minimize2 className="h-4 w-4" aria-hidden />
                  Minimise
                </button>
              </div>
            )}
          </div>
        </div>

        {!minimized && (
          <div className="no-scrollbar mt-5 flex gap-4 overflow-x-auto md:mt-7 md:gap-5" ref={scrollRef}>
            {visibleHistory.map((manga) => (
              <article
                key={manga.slug}
                className="group relative w-[calc((100%-2rem)/3)] shrink-0 md:w-[calc((100%-3.75rem)/4)] lg:w-[calc((100%-6.25rem)/6)]"
              >
                <a href={`/manga/${manga.slug}`} className="block" onClick={() => { /* tracked via MangaCard */ }}>
                  <CoverImage
                    src={manga.cover}
                    alt={manga.title}
                    className="aspect-[3/4] w-full rounded-xl"
                    imgClassName="transition-transform duration-300 group-hover:scale-[1.04]"
                  />
                  <h3 className="mt-2 truncate text-center text-sm font-medium text-ink">{manga.title}</h3>
                </a>
                <div className="history-menu absolute right-2 top-2 z-20">
                  <button
                    type="button"
                    aria-label="More options"
                    onClick={() => setMenuSlug((v) => (v === manga.slug ? null : manga.slug))}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-black/10 text-ink drop-shadow-md backdrop-blur-sm transition hover:bg-white/10 hover:text-brand-soft"
                  >
                    <EllipsisVertical className="h-4 w-4" />
                  </button>
                  {menuSlug === manga.slug && (
                    <div className="absolute right-0 mt-1 w-28 overflow-hidden rounded-md border border-white/10 bg-[#1c1c1c]/95 py-1 shadow-xl shadow-black/50 backdrop-blur">
                      <button
                        type="button"
                        onClick={() => {
                          toggleSaved(manga.slug, manga.title);
                          setMenuSlug(null);
                        }}
                        className="flex w-full items-center gap-2 whitespace-nowrap px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
                      >
                        <Bookmark
                          className="h-4 w-4"
                          fill={isSaved(manga.slug) ? "currentColor" : "none"}
                          aria-hidden
                        />
                        {isSaved(manga.slug) ? "Unsave" : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard?.writeText(manga.title);
                          setMenuSlug(null);
                        }}
                        className="flex w-full items-center gap-2 whitespace-nowrap px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
                      >
                        <Copy className="h-4 w-4" aria-hidden />
                        Copy title
                      </button>
                      <div className="border-t border-white/10 px-3 py-2 text-xs text-ink-faint">
                        <div>Images: {manga.pages ?? 0}</div>
                        <div>Views: {manga.views}</div>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}

        {minimized && (
          <button
            type="button"
            onClick={() => setMinimized(false)}
            className="mt-4 block w-full text-center text-sm text-ink-soft transition hover:text-ink"
          >
            Show history
          </button>
        )}
      </section>
      </>
      )}

      <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-8" style={{ marginTop: 16, marginBottom: 8 }}>
        <hr className="border-t border-white/10" />
      </div>

      <section
        aria-labelledby="latest-title"
        className="mx-auto max-w-[1440px] px-4 pb-10 pt-2 sm:px-6 md:pt-3 lg:px-8"
      >
        <h2 id="latest-title" className="text-left text-2xl font-medium tracking-tight text-ink">
          Latest Release
        </h2>
        {latestLoading && visibleLatest.length === 0 ? (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6" aria-busy="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : visibleLatest.length === 0 ? (
          <p className="mt-10 text-center text-sm text-ink-faint">
            No titles available right now.
          </p>
        ) : (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
            {visibleLatest.map((manga) => (
              <MangaCard key={manga.slug} manga={manga} />
            ))}
          </div>
        )}
      </section>
      <Pagination />
    </AppShell>
  );
}
