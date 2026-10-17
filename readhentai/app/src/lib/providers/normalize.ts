// Bridge: NormalizedTitle -> the UI-facing `Manga` type.
//
// Keeps every existing component (MangaCard, TrendingSection, detail page, …)
// working unchanged while the underlying data now comes from real providers.
// Fields a provider can't supply are left undefined rather than fabricated —
// call sites render an explicit "—" / hide the stat instead of a fake number.

import type { Manga } from "@/lib/manga";
import type { NormalizedChapter, NormalizedTitle, PublicationStatus } from "./types";

const CATEGORY_TO_CONTENT: Record<NormalizedTitle["category"], Manga["contentType"]> = {
  manga: "Manga",
  manhwa: "Manhwa",
  manhua: "Manhua",
};

function mapStatus(status: PublicationStatus | null): Manga["status"] {
  return (status as Manga["status"]) ?? undefined;
}

/** Format a real popularity count compactly ("1.2M"), or undefined if unknown. */
export function formatCount(n: number | null | undefined): string | undefined {
  if (n == null || !isFinite(n)) return undefined;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}k`;
  return String(n);
}

/** Whole days between an ISO timestamp and now — for "updated Xd ago" sorts. */
function daysSince(iso: string | null | undefined): number | undefined {
  if (!iso) return undefined;
  const t = Date.parse(iso);
  if (isNaN(t)) return undefined;
  return Math.max(0, Math.floor((Date.now() - t) / 86_400_000));
}

/** Map a provider title to the existing `Manga` shape used across the UI. */
export function toManga(title: NormalizedTitle): Manga {
  const popularity = formatCount(title.popularity);
  const year = title.publishedAt ? Number(title.publishedAt.slice(0, 4)) : undefined;

  return {
    slug: title.slug,
    title: title.title,
    // AniList rating is 0..100; convert to the 0..5 scale the UI renders.
    rating: title.rating != null ? Math.round((title.rating / 20) * 10) / 10 : 0,
    // Chapter count is resolved separately; 0 hides the Collection section.
    chapters: 0,
    // Real popularity only — never a fabricated view count.
    views: popularity ?? "",
    cover: title.coverImage ?? "",
    colored: false,
    pages: undefined,
    genres: title.genres.length ? title.genres : title.tags.slice(0, 6),
    status: mapStatus(title.status),
    contentType: CATEGORY_TO_CONTENT[title.category],
    artist: title.artists[0] ?? undefined,
    // "Circle"/"parody" aren't provided by these providers — surfaced as unknown.
    circle: undefined,
    subtitle: title.alternativeTitles[0] ?? undefined,
    language: title.language ?? undefined,
    parody: undefined,
    releaseYear: year && year > 1900 ? year : undefined,
    updatedDays: daysSince(title.updatedAt),
  };
}

/** Map a chapter to a UI collection entry built on the Manga shape. */
export function chapterToManga(title: NormalizedTitle, chapter: NormalizedChapter): Manga {
  const base = toManga(title);
  const num = chapter.chapterNumber ? Number(chapter.chapterNumber) : null;
  return {
    ...base,
    slug: `${title.slug}#ch-${chapter.providerChapterId}`,
    title: chapter.chapterTitle
      ? `Ch. ${chapter.chapterNumber ?? "?"} — ${chapter.chapterTitle}`
      : `Chapter ${chapter.chapterNumber ?? "?"}`,
    chapters: 0,
    pages: chapter.pageCount ?? undefined,
    rating: 0,
    views: "",
    updatedDays: daysSince(chapter.publishedAt),
    // Carry the chapter id so the collection can link to the reader.
    releaseYear: num && num > 0 ? num : undefined,
  };
}
