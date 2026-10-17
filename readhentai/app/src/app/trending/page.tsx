"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  Columns3,
  Eye,
  Filter,
  Images,
  List,
  MessageSquare,
  X,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CoverImage } from "@/components/CoverImage";
import { MangaCard } from "@/components/MangaCard";
import { Pagination } from "@/components/Pagination";
import { GENRE_LIST, parseViews, type Manga } from "@/lib/manga";
import { useTitles } from "@/lib/content";
import { useContentType } from "@/lib/contentType";

const TABS = ["Daily", "Weekly", "Monthly", "All Time"] as const;
type Tab = (typeof TABS)[number];

const WINDOWS: Record<Tab, number> = {
  Daily: 1,
  Weekly: 7,
  Monthly: 30,
  "All Time": Infinity,
};

function recencyScore(views: string, updatedDays: number, window: number): number {
  return parseViews(views) / (1 + updatedDays / window);
}

/** Deterministic comment count so the stat is stable between loads. */
function commentCount(slug: string): number {
  let h = 2166136261;
  for (let i = 0; i < slug.length; i++) {
    h ^= slug.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) % 900;
}

export default function TrendingPage() {
  const contentType = useContentType();
  const [tab, setTab] = useState<Tab>("Daily");
  const [view, setView] = useState<"list" | "column">("list");
  const [genreOpen, setGenreOpen] = useState(false);
  const [pendingGenres, setPendingGenres] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const modalRef = useRef<HTMLDivElement>(null);

  // Popularity-ordered working set from providers; genre + window sorting stays
  // client-side so tab/filter changes are instant over the fetched data.
  const genreQuery = selected.map((g) => `genre=${encodeURIComponent(g)}`).join("&");
  const { items: workingSet, loading } = useTitles(
    `/api/titles?limit=50&order=popular&contentType=${encodeURIComponent(contentType)}${genreQuery ? `&${genreQuery}` : ""}`,
  );

  useEffect(() => {
    if (!genreOpen) return;
    const onPointerDown = (event: PointerEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setGenreOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setGenreOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [genreOpen]);

  const results = useMemo(() => {
    // Content type + genre were applied server-side in the fetched working set.
    let list: Manga[] = workingSet.slice();

    const window = WINDOWS[tab];
    if (window === Infinity) {
      list.sort((a, b) => parseViews(b.views) - parseViews(a.views));
    } else {
      list.sort(
        (a, b) =>
          recencyScore(b.views, b.updatedDays ?? 0, window) -
          recencyScore(a.views, a.updatedDays ?? 0, window)
      );
    }

    return list;
  }, [workingSet, tab]);

  const openGenrePopup = () => {
    setPendingGenres(selected);
    setGenreOpen(true);
  };
  const togglePending = (genre: string) =>
    setPendingGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  const applyGenres = () => {
    setSelected(pendingGenres);
    setGenreOpen(false);
  };
  const clearGenres = () => setPendingGenres([]);

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] px-4 pb-10 pt-4 sm:px-6 md:pt-6 lg:px-8">
        {/* Header: title (on mobile, filter + view toggle inline) */}
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Trending</h1>

          {/* Mobile-only: filter + view toggle inline with title */}
          <div className="flex shrink-0 items-center gap-2 sm:hidden">
            <button
              type="button"
              onClick={openGenrePopup}
              aria-label="Select a genre to filter"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:border-brand-soft hover:text-ink"
            >
              <Filter className="h-4 w-4" aria-hidden />
            </button>
            <div
              role="tablist"
              aria-label="View mode"
              className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1"
            >
              <button
                type="button"
                role="tab"
                aria-selected={view === "list"}
                aria-label="List view"
                onClick={() => setView("list")}
                className={`flex h-8 w-8 items-center justify-center rounded-full transition ${
                  view === "list" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                <List className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={view === "column"}
                aria-label="Column view"
                onClick={() => setView("column")}
                className={`flex h-8 w-8 items-center justify-center rounded-full transition ${
                  view === "column" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                <Columns3 className="h-4 w-4" aria-hidden />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs + (desktop) genre filter + view toggle */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-2 sm:gap-3">
          <div
            role="tablist"
            aria-label="Trending range"
            className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1"
          >
            {TABS.map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={`rounded-full px-2.5 py-1.5 text-xs font-medium transition sm:px-3.5 sm:text-sm ${
                  tab === t ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="hidden shrink-0 items-center gap-2 sm:flex">
            <button
              type="button"
              onClick={openGenrePopup}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-ink-soft transition hover:border-brand-soft hover:text-ink sm:px-3.5 sm:py-2 sm:text-sm"
            >
              <Filter className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden />
              <span className="hidden sm:inline">Select a genre to filter</span>
            </button>

            <div
              role="tablist"
              aria-label="View mode"
              className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1"
            >
              <button
                type="button"
                role="tab"
                aria-selected={view === "list"}
                aria-label="List view"
                onClick={() => setView("list")}
                className={`flex h-7 w-7 items-center justify-center rounded-full transition sm:h-8 sm:w-8 ${
                  view === "list" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                <List className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden />
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={view === "column"}
                aria-label="Column view"
                onClick={() => setView("column")}
                className={`flex h-7 w-7 items-center justify-center rounded-full transition sm:h-8 sm:w-8 ${
                  view === "column" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
                }`}
              >
                <Columns3 className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden />
              </button>
            </div>
          </div>
        </div>

        {/* Results: list or column view */}
        {loading && results.length === 0 ? (
          <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : results.length === 0 ? (
          <p className="mt-16 text-center text-sm text-ink-faint">No titles match these genres.</p>
        ) : view === "column" ? (
          <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
            {results.map((manga) => (
              <MangaCard key={manga.slug} manga={manga} />
            ))}
          </div>
        ) : (
          <ol className="mt-6 space-y-3">
            {results.map((manga, index) => (
              <li key={manga.slug}>
                <a
                  href={`/manga/${manga.slug}`}
                  className="group flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 p-2.5 transition hover:border-brand-soft/50 hover:bg-white/10 sm:gap-4 sm:p-3"
                >
                  <span className="w-6 shrink-0 text-center text-lg font-bold text-ink-faint sm:w-8 sm:text-xl">
                    {index + 1}
                  </span>

                  <CoverImage
                    src={manga.cover}
                    alt={manga.title}
                    className="h-20 w-14 shrink-0 rounded-lg sm:h-24 sm:w-[68px]"
                    imgClassName="transition-transform duration-300 group-hover:scale-[1.05]"
                  />

                  <div className="min-w-0 flex-1">
                    <h2 className="truncate text-sm font-semibold text-ink sm:text-base">
                      {manga.title}
                    </h2>
                    {manga.genres && manga.genres.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {manga.genres.map((g) => (
                          <span
                            key={g}
                            className="rounded-full border border-white/15 px-2 py-0.5 text-[11px] text-ink-soft"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="mt-2 flex items-center gap-3 text-xs text-ink-faint sm:gap-4">
                      <span className="inline-flex items-center gap-1">
                        <Eye className="h-3.5 w-3.5" aria-hidden />
                        {manga.views} Views
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <MessageSquare className="h-3.5 w-3.5" aria-hidden />
                        {commentCount(manga.slug)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Images className="h-3.5 w-3.5" aria-hidden />
                        {manga.pages ?? 0}
                      </span>
                    </div>
                  </div>
                </a>
              </li>
            ))}
          </ol>
        )}

        {/* Genre filter modal */}
        {genreOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div
              ref={modalRef}
              className="relative max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-white/10 bg-[#1c1c1c] p-5 shadow-2xl"
            >
              <button
                type="button"
                aria-label="Close"
                onClick={() => setGenreOpen(false)}
                className="absolute right-3 top-3 rounded-full p-1.5 text-ink-soft transition hover:bg-white/10 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
              <h2 className="mb-4 text-lg font-medium text-ink">Select genres</h2>
              <div className="flex flex-wrap gap-2">
                {GENRE_LIST.map((genre) => {
                  const checked = pendingGenres.includes(genre);
                  return (
                    <button
                      key={genre}
                      type="button"
                      onClick={() => togglePending(genre)}
                      className={`rounded-full border px-3 py-1.5 text-sm transition ${
                        checked
                          ? "border-brand-soft bg-brand-deep/40 text-ink"
                          : "border-white/10 bg-surface text-ink-soft hover:border-brand-soft hover:text-ink"
                      }`}
                    >
                      {genre}
                      {checked && <Check className="ml-1 inline h-3.5 w-3.5" aria-hidden />}
                    </button>
                  );
                })}
              </div>
              <div className="mt-4 flex justify-between gap-2">
                <button
                  type="button"
                  onClick={clearGenres}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-ink-soft transition hover:bg-white/5 hover:text-ink"
                >
                  Clear
                </button>
                <button
                  type="button"
                  onClick={applyGenres}
                  className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-ink transition hover:bg-brand-soft"
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        )}

        <Pagination />
      </section>
    </AppShell>
  );
}
