"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Eye,
  EllipsisVertical,
  Minimize2,
} from "lucide-react";
import { CoverImage } from "./CoverImage";
import { useFollowUpdates } from "@/lib/content";

/** Compact relative time: "4h ago", "2d ago", "3mo ago". */
function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (isNaN(t)) return "";
  const mins = Math.floor((Date.now() - t) / 60_000);
  if (mins < 60) return `${Math.max(1, mins)}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

/**
 * Home rail listing followed titles that dropped a new chapter since the user
 * last caught up. Renders nothing when there is nothing new.
 */
export function NewChaptersSection() {
  const router = useRouter();
  const { follows, updates, loading } = useFollowUpdates();
  const [minimized, setMinimized] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const items = useMemo(() => {
    return follows
      .map((follow) => ({ follow, entry: updates[follow.slug] }))
      .filter((row) => row.entry?.latestChapter)
      .filter(
        (row) =>
          row.follow.seenChapterId != null &&
          row.entry!.latestChapter!.id !== row.follow.seenChapterId,
      )
      .map((row) => ({
        slug: row.follow.slug,
        title: row.follow.title || row.entry!.manga.title,
        manga: row.entry!.manga,
        latest: row.entry!.latestChapter!,
        resumeNumber: row.follow.seenChapterNumber,
      }))
      .sort((a, b) =>
        (b.latest.publishedAt ?? "").localeCompare(a.latest.publishedAt ?? ""),
      );
  }, [follows, updates]);

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
  }, [items.length, minimized]);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  if (loading || items.length === 0) return null;

  return (
    <section
      aria-labelledby="new-chapters-title"
      className="mx-auto max-w-[1440px] px-4 pb-2 pt-6 sm:px-6 md:pt-8 lg:px-8"
    >
      <div className="relative flex items-center justify-between gap-3">
        <h2 id="new-chapters-title" className="text-left text-lg font-medium tracking-tight text-ink sm:text-2xl">
          New Chapters from Followed Comics
        </h2>
        <div ref={menuRef} className="relative flex shrink-0 items-center gap-1">
          {!minimized && (
            <>
              <button
                type="button"
                aria-label="Scroll left"
                disabled={!canScrollLeft}
                onClick={() => scroll(-1)}
                className="hidden h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40 sm:flex"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <button
                type="button"
                aria-label="Scroll right"
                disabled={!canScrollRight}
                onClick={() => scroll(1)}
                className="hidden h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40 sm:flex"
              >
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </>
          )}
          <button
            type="button"
            aria-label="Section options"
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
                  setMenuOpen(false);
                  router.push("/my-list");
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

      {minimized ? (
        <button
          type="button"
          onClick={() => setMinimized(false)}
          className="mt-4 block w-full text-center text-sm text-ink-soft transition hover:text-ink"
        >
          Show new chapters
        </button>
      ) : (
        <div
          className="no-scrollbar mt-5 flex gap-4 overflow-x-auto pb-6 md:mt-7 md:gap-5"
          ref={scrollRef}
        >
          {items.map(({ slug, title, manga, latest, resumeNumber }) => (
            <article
              key={slug}
              className="group relative w-[calc((100%-2rem)/3)] shrink-0 md:w-[calc((100%-3.75rem)/4)] lg:w-[calc((100%-6.25rem)/6)]"
            >
              <a href={`/manga/${slug}`} className="block">
                <CoverImage
                  src={manga.cover}
                  alt={title}
                  className="aspect-[3/4] w-full rounded-xl"
                  imgClassName="transition-transform duration-300 group-hover:scale-[1.04]"
                >
                  <span className="absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[11px] font-semibold text-white backdrop-blur-sm">
                    <Bookmark className="h-3 w-3 fill-current" aria-hidden />
                    Ch.{resumeNumber ?? latest.number ?? "?"}
                  </span>
                </CoverImage>
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="font-medium text-ink-soft">
                    {latest.number ? `Ch.${latest.number}` : "New"}
                  </span>
                  <span className="text-ink-faint">{timeAgo(latest.publishedAt)}</span>
                </div>
                <h3 className="mt-1 line-clamp-2 text-center text-sm font-medium leading-snug text-ink">
                  {title}
                </h3>
              </a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
