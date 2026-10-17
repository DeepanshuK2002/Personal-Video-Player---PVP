"use client";

import { useEffect, useRef, useState } from "react";
import { Bookmark, Calendar, Copy, EllipsisVertical, Eye, Heart, ListChevronsDownUp, ListChevronsUpDown, Star } from "lucide-react";
import { useTitles } from "@/lib/content";
import { CoverImage } from "./CoverImage";
import { isSaved, toggleSaved } from "@/lib/saved";
import { useContentType } from "@/lib/contentType";
import { useRouter } from "next/navigation";

const RANGES = ["Popular", "Today", "This Week", "This Month", "This Year", "All Time"] as const;

/** Map the section's range picker onto a real provider order + window. */
function rangeToOrder(range: string): "popular" | "latest" {
  return range === "Today" || range === "This Week" || range === "This Month" ? "latest" : "popular";
}

export function TrendingSection() {
  const router = useRouter();
  const contentType = useContentType();
  const [range, setRange] = useState<string>("Today");
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [menuSlug, setMenuSlug] = useState<string | null>(null);
  const [savedSet, setSavedSet] = useState<Set<string>>(new Set());
  const menuRef = useRef<HTMLDivElement>(null);

  // Real popularity/latest feed. `useTitles` dedupes + caches by path so
  // flipping the range is instant and never shows a superseded response.
  const order = rangeToOrder(range);
  const { items: trending, loading } = useTitles(
    `/api/trending?limit=18&contentType=${encodeURIComponent(contentType)}&order=${order}`,
  );

  useEffect(() => {
    const sync = () => setSavedSet(new Set(trending.map((m) => m.slug).filter((s) => isSaved(s))));
    sync();
    const handler = () => sync();
    window.addEventListener("saved-change", handler);
    return () => window.removeEventListener("saved-change", handler);
  }, [trending]);

  useEffect(() => {
    if (!menuSlug) return;
    const onClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest(".trending-menu")) setMenuSlug(null);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuSlug]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // contentType is applied server-side; the API result is already filtered.
  const visibleTrending = trending;

  return (
    <section
      aria-labelledby="trending-title"
      className="bg-[linear-gradient(180deg,#6f0000_0%,#430000_38%,#180000_72%,#000000_100%)]"
    >
      <div className="mx-auto max-w-[1440px] px-4 pb-8 pt-4 sm:px-6 md:pb-12 md:pt-8 lg:px-8">
        <div className="relative flex items-center gap-2 flex-nowrap">
          <div ref={menuRef} className="relative">
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-haspopup="listbox"
              aria-expanded={open}
              className="flex h-8 w-8 items-center justify-center rounded-full border-0 bg-black/25 text-ink transition sm:h-auto sm:w-auto sm:gap-2 sm:border sm:border-brand-soft/70 sm:py-2 sm:pl-3.5 sm:pr-4 sm:text-sm hover:border-brand-soft"
            >
              <Calendar className="h-4 w-4 text-brand-soft" aria-hidden />
              <span className="hidden sm:inline">{range}</span>
            </button>

            {open && (
              <ul
                role="listbox"
                aria-label="Trending range"
                className="absolute left-0 top-full z-30 mt-2 w-44 overflow-hidden rounded-xl border border-white/10 bg-[#1c1c1c]/95 py-1 shadow-xl shadow-black/50 backdrop-blur"
              >
                {RANGES.map((option) => {
                  if (option === "Popular") {
                    return (
                      <li key={option} className="px-4 py-2 text-xs font-semibold uppercase tracking-wide text-brand-soft">
                        {option}
                      </li>
                    );
                  }
                  const selected = option === range;
                  return (
                    <li key={option}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={selected}
                        onClick={() => {
                          setRange(option);
                          setOpen(false);
                        }}
                        className={`flex mx-1 w-[calc(100%-0.5rem)] items-center rounded-md px-4 py-2.5 text-left text-sm transition ${
                          selected
                            ? "bg-white/5 font-semibold text-brand-soft"
                            : "text-ink-soft hover:bg-white/5 hover:text-ink"
                        }`}
                      >
                        {option}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <div className="absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 sm:gap-2">
            <Heart className="h-5 w-5 fill-brand text-brand sm:h-6 sm:w-6" aria-hidden />
            <button
              type="button"
              onClick={() => router.push("/trending")}
              className="text-lg font-medium tracking-tight text-ink transition hover:text-brand-soft sm:text-2xl"
            >
              trending
            </button>
          </div>

          <button
            type="button"
            aria-label={expanded ? "Collapse trending" : "Expand trending"}
            onClick={() => setExpanded((v) => !v)}
            className={`ml-auto rounded-full p-2 transition ${
              expanded ? "bg-white/10 text-brand" : "text-ink hover:bg-white/10"
            }`}
          >
            {expanded ? (
              <ListChevronsDownUp className="h-5 w-5" />
            ) : (
              <ListChevronsUpDown className="h-5 w-5" />
            )}
          </button>
        </div>

        {loading && visibleTrending.length === 0 ? (
          <div
            className={
              expanded
                ? "mt-5 grid grid-cols-2 gap-x-5 gap-y-8 md:mt-7 md:grid-cols-4 xl:grid-cols-6"
                : "no-scrollbar mt-5 flex gap-4 overflow-x-auto md:mt-7 md:gap-5"
            }
            aria-busy="true"
          >
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className={
                  expanded
                    ? "aspect-[3/4] w-full animate-pulse rounded-xl bg-white/5"
                    : "aspect-[3/4] w-[calc((100%-2rem)/3)] shrink-0 animate-pulse rounded-xl bg-white/5 md:w-[calc((100%-3.75rem)/4)] lg:w-[calc((100%-6.25rem)/6)]"
                }
              />
            ))}
          </div>
        ) : visibleTrending.length === 0 ? (
          <p className="mt-10 text-center text-sm text-ink-faint">No trending titles right now.</p>
        ) : (
        <div
          className={
            expanded
              ? "mt-5 grid grid-cols-2 gap-x-5 gap-y-8 md:mt-7 md:grid-cols-4 xl:grid-cols-6"
              : "no-scrollbar mt-5 flex gap-4 overflow-x-auto md:mt-7 md:gap-5"
          }
        >
          {visibleTrending.map((manga, index) => (
            <article
              key={manga.slug}
              className={
                expanded
                  ? "group relative"
                  : "group relative w-[calc((100%-2rem)/3)] shrink-0 md:w-[calc((100%-3.75rem)/4)] lg:w-[calc((100%-6.25rem)/6)]"
              }
            >
              <a href={`/manga/${manga.slug}`} className="block">
                <CoverImage
                  src={manga.cover}
                  alt={manga.title}
                  className="aspect-[3/4] w-full rounded-xl"
                  imgClassName="transition-transform duration-300 group-hover:scale-[1.04]"
                >
                  <span className="absolute left-0 top-0 flex h-8 w-8 items-center justify-center rounded-br-2xl rounded-tl-xl border border-brand-soft/45 bg-brand-soft/30 text-sm font-bold text-ink backdrop-blur-md sm:h-10 sm:w-10 sm:text-lg">
                    {index + 1}
                  </span>
                </CoverImage>
                <p className="mt-2.5 flex items-center justify-center gap-1.5 text-xs font-semibold text-brand-soft">
                  Manga
                  <span className="font-normal text-ink-faint" aria-hidden>
                    |
                  </span>
                  <Star className="h-3.5 w-3.5 fill-brand-soft text-brand-soft" aria-hidden />
                  {manga.rating != null && manga.rating > 0 ? manga.rating.toFixed(1) : "—"}
                </p>
                <h3 className="mt-1 truncate text-center text-sm font-medium leading-snug text-ink">
                  {manga.title}
                </h3>
              </a>

              <div className="trending-menu absolute right-2 top-2 z-20">
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
                        setSavedSet((prev) => {
                          const next = new Set(prev);
                          if (isSaved(manga.slug)) next.add(manga.slug);
                          else next.delete(manga.slug);
                          return next;
                        });
                        setMenuSlug(null);
                      }}
                      className="flex w-full items-center gap-2 whitespace-nowrap px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
                    >
                      <Bookmark
                        className="h-4 w-4"
                        fill={savedSet.has(manga.slug) ? "currentColor" : "none"}
                        aria-hidden
                      />
                      {savedSet.has(manga.slug) ? "Unsave" : "Save"}
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
      </div>
    </section>
  );
}
