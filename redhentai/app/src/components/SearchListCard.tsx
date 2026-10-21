"use client";

import { useEffect, useState } from "react";
import { Bookmark, ListPlus } from "lucide-react";
import { CoverImage } from "./CoverImage";
import type { Manga, Status } from "@/lib/manga";
import { isSaved, toggleSaved } from "@/lib/saved";
import { isFollowed, toggleFollow } from "@/lib/follow";
import { addHistory } from "@/lib/history";

/** Chapter slugs (`<title>#ch-<id>`) open the reader; title slugs open detail. */
function hrefFor(slug: string): string {
  const hashAt = slug.indexOf("#");
  if (hashAt === -1) return `/manga/${slug}`;
  const base = slug.slice(0, hashAt);
  const chapterPart = slug.slice(hashAt + 1);
  const chapterId = chapterPart.startsWith("ch-") ? chapterPart.slice(3) : chapterPart;
  return `/read/${base}/${chapterId}`;
}

/** Real publication status -> accent colour. Unknown status renders muted. */
const STATUS_TONE: Record<Status, string> = {
  All: "text-ink-muted",
  Completed: "text-emerald-400",
  "In Process": "text-sky-400",
  Paused: "text-amber-400",
};

/**
 * Horizontal result row used by the regular search list: cover on the left,
 * title + meta + synopsis + actions on the right. Chapter count is only shown
 * when the provider actually reports one (never fabricated).
 */
export function SearchListCard({ manga }: { manga: Manga }) {
  const [saved, setSaved] = useState(false);
  const [followed, setFollowed] = useState(false);

  useEffect(() => {
    setSaved(isSaved(manga.slug));
    const handler = () => setSaved(isSaved(manga.slug));
    window.addEventListener("saved-change", handler);
    return () => window.removeEventListener("saved-change", handler);
  }, [manga.slug]);

  // "My List" (follow) is a separate store from Watch Later: it tracks chapter
  // updates rather than bookmarking, so it gets its own state + change event.
  useEffect(() => {
    setFollowed(isFollowed(manga.slug));
    const handler = () => setFollowed(isFollowed(manga.slug));
    window.addEventListener("follow-change", handler);
    return () => window.removeEventListener("follow-change", handler);
  }, [manga.slug]);

  const handleSave = () => {
    toggleSaved(manga.slug, manga.title);
    setSaved(isSaved(manga.slug));
  };

  const handleFollow = () => {
    toggleFollow(manga.slug, manga.title);
    setFollowed(isFollowed(manga.slug));
  };

  const recordOpen = () => addHistory(manga.slug.split("#")[0], manga.title);
  const href = hrefFor(manga.slug);
  const showChapter = manga.chapters > 0;
  const showStatus = Boolean(manga.status);
  const statusTone = manga.status ? STATUS_TONE[manga.status] : undefined;

  return (
    <article className="group rounded-2xl border border-white/10 bg-[#141414] p-3 transition hover:border-white/20 sm:p-3.5">
      <div className="flex gap-3 sm:gap-4">
        <a
          href={href}
          onClick={recordOpen}
          aria-label={manga.title}
          className="shrink-0"
        >
          <CoverImage
            src={manga.cover}
            alt={manga.title}
            className="aspect-[3/4] w-[104px] rounded-xl sm:w-[126px]"
            imgClassName="transition-transform duration-300 group-hover:scale-[1.04]"
          />
        </a>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-start justify-between gap-3">
            <a href={href} onClick={recordOpen} className="min-w-0">
              <h3 className="line-clamp-2 text-base font-semibold leading-snug text-ink sm:text-xl">
                {manga.title}
              </h3>
            </a>
            <span className="shrink-0 pt-1 text-xs text-ink-muted sm:text-[13px]">
              {manga.contentType ?? "—"}
            </span>
          </div>

          {(showChapter || showStatus) && (
            <p className="mt-1 flex flex-wrap items-center gap-x-2.5 text-sm text-ink-soft">
              {showChapter && <span>chapter {manga.chapters}</span>}
              {showStatus && (
                <span className={`font-medium ${statusTone ?? "text-ink-muted"}`}>
                  {manga.status}
                </span>
              )}
            </p>
          )}

          {manga.description && (
            <p className="mt-2.5 line-clamp-2 text-[13px] leading-relaxed text-ink-muted">
              {manga.description}
            </p>
          )}

          <div className="mt-auto flex items-center gap-3 pt-3.5">
            <button
              type="button"
              onClick={handleSave}
              aria-pressed={saved}
              aria-label={saved ? "Remove from Watch Later" : "Save to Watch Later"}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-ink-soft transition hover:border-white/30 hover:text-ink"
            >
              <Bookmark
                className="h-4 w-4"
                fill={saved ? "currentColor" : "none"}
                aria-hidden
              />
            </button>
            <button
              type="button"
              onClick={handleFollow}
              aria-pressed={followed}
              aria-label={followed ? "Remove from My List" : "Add to My List"}
              title={followed ? "In My List" : "Add to My List"}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-ink-soft transition hover:border-white/30 hover:text-ink"
            >
              <ListPlus
                className="h-4 w-4"
                fill={followed ? "currentColor" : "none"}
                aria-hidden
              />
            </button>
            <a
              href={href}
              onClick={recordOpen}
              className="rounded-lg bg-brand-deep/70 px-6 py-2 text-sm font-semibold text-brand-soft ring-1 ring-inset ring-brand/40 transition hover:bg-brand-deep hover:text-ink"
            >
              Read
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}
