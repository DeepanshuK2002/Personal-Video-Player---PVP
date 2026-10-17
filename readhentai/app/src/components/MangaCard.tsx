"use client";

import { useEffect, useRef, useState } from "react";
import { Bookmark, Copy, EllipsisVertical, Eye, Star } from "lucide-react";
import { CoverImage } from "./CoverImage";
import type { Manga } from "@/lib/manga";
import { isSaved, toggleSaved } from "@/lib/saved";
import { addHistory } from "@/lib/history";

/** Chapter slugs (`<title>#ch-<id>`) open the reader; title slugs open detail. */
function hrefFor(slug: string): string {
  const hashAt = slug.indexOf("#ch-");
  if (hashAt === -1) return `/manga/${slug}`;
  return `/read/${slug.slice(0, hashAt)}/${slug.slice(hashAt + 4)}`;
}

export function MangaCard({
  manga,
  twoLineTitle = false,
  titlePrefix,
}: {
  manga: Manga;
  twoLineTitle?: boolean;
  titlePrefix?: string;
}) {
  const [saved, setSaved] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSaved(isSaved(manga.slug));
    const handler = () => setSaved(isSaved(manga.slug));
    window.addEventListener("saved-change", handler);
    return () => window.removeEventListener("saved-change", handler);
  }, [manga.slug]);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const handleSave = () => {
    toggleSaved(manga.slug, manga.title);
    setSaved(isSaved(manga.slug));
    setMenuOpen(false);
  };

  return (
    <article className="group relative">
      <a href={hrefFor(manga.slug)} className="block" onClick={() => addHistory(manga.slug.split("#")[0])}>
        <div className="relative">
          <CoverImage
            src={manga.cover}
            alt={manga.title}
            className="aspect-[2/3] w-full rounded-xl"
            imgClassName="transition-transform duration-300 group-hover:scale-[1.04]"
          >
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/80 via-black/25 to-transparent"
              aria-hidden
            />

            {manga.views && (
              <div className="absolute left-2 top-2 flex items-center gap-1 rounded-full bg-black/10 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm drop-shadow-md">
                <Eye className="h-3 w-3 drop-shadow-md" aria-hidden />
                {manga.views}
              </div>
            )}

          <p className="absolute inset-x-0 bottom-2 flex items-center justify-center gap-1.5 px-2 text-[11px] font-semibold text-brand-soft">
              {manga.unavailable ? "Unavailable" : "Manga"}
              <span className="font-normal text-ink-soft/70" aria-hidden>
                |
              </span>
              <Star className="h-3 w-3 fill-brand-soft text-brand-soft" aria-hidden />
              {manga.rating != null && manga.rating > 0 ? manga.rating.toFixed(1) : "—"}
            </p>
          </CoverImage>

          <div
            className="pointer-events-none absolute inset-0 rounded-xl"
            aria-hidden
            style={{
              background: manga.colored
                ? "linear-gradient(90deg, rgba(255,0,0,0) 0%, #ff0000 18%, #ffe600 50%, #007adf 82%, rgba(139,92,246,0) 100%)"
                : "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.45) 50%, rgba(255,255,255,0) 100%)",
              padding: "1.5px",
              WebkitMask:
                "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
              WebkitMaskComposite: "xor",
              mask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
              maskComposite: "exclude",
              clipPath: "inset(calc(100% - 15px) 0 0 0)",
              opacity: 0.65,
            }}
          />
        </div>
      </a>

      <div ref={menuRef} className="absolute right-2 top-2 z-20">
        <button
          type="button"
          aria-label="More options"
          onClick={() => setMenuOpen((v) => !v)}
          className="flex h-7 w-7 items-center justify-center rounded-full bg-black/10 text-ink drop-shadow-md backdrop-blur-sm transition hover:bg-white/10 hover:text-brand-soft"
        >
          <EllipsisVertical className="h-4 w-4" />
        </button>
        {menuOpen && (
          <div className="absolute right-0 mt-1 w-28 overflow-hidden rounded-md border border-white/10 bg-[#1c1c1c]/95 py-1 shadow-xl shadow-black/50 backdrop-blur">
            <button
              type="button"
              onClick={handleSave}
              className="flex w-full items-center gap-2 whitespace-nowrap px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
            >
              <Bookmark
                className="h-4 w-4"
                fill={saved ? "currentColor" : "none"}
                aria-hidden
              />
              {saved ? "Unsave" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard?.writeText(manga.title);
                setMenuOpen(false);
              }}
              className="flex w-full items-center gap-2 whitespace-nowrap px-3 py-2 text-left text-sm text-ink-soft transition hover:bg-white/5 hover:text-ink"
            >
              <Copy className="h-4 w-4" aria-hidden />
              Copy title
            </button>
            <div className="border-t border-white/10 px-3 py-2 text-xs text-ink-faint">
              <div>Images: {manga.pages}</div>
              <div>Views: {manga.views}</div>
            </div>
          </div>
        )}
      </div>

      <h3
        className={`mt-2 text-center text-sm font-medium leading-snug text-ink ${
          twoLineTitle ? "line-clamp-2" : "truncate"
        }`}
      >
        {titlePrefix && (
          <span className="mr-1 font-bold text-brand-soft">{titlePrefix}</span>
        )}
        {manga.title}
      </h3>
    </article>
  );
}