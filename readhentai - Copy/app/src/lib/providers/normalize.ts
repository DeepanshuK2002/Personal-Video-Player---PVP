// Bridge: NormalizedTitle -> the UI-facing `Manga` type.
//
// Keeps every existing component (MangaCard, TrendingSection, detail page, …)
// working unchanged while the underlying data now comes from real providers.
// Fields a provider can't supply are left undefined rather than fabricated —
// call sites render an explicit "—" / hide the stat instead of a fake number.

import type { Manga } from "@/lib/manga";
import type { Category, NormalizedChapter, NormalizedTitle, PublicationStatus } from "./types";

const CATEGORY_TO_CONTENT: Partial<Record<Category, Manga["contentType"]>> = {
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
    // Real series length when the provider reports one (AniList `chapters`);
    // 0 means "unknown" — readable chapter count lives on the detail endpoint,
    // and Collection is gated by `readableChapters.length`, not by this field.
    chapters: title.chapterCount && title.chapterCount > 0 ? title.chapterCount : 0,
    // Real popularity only — never a fabricated view count.
    views: popularity ?? "",
    cover: title.coverImage ?? "",
    // Provider-supplied color flag; falls back to manhwa=true for backwards compat.
    colored: title.colored ?? title.category === "manhwa",
    pages: undefined,
    genres: title.genres.length ? title.genres : title.tags.slice(0, 6),
    status: mapStatus(title.status),
    contentType: title.category ? CATEGORY_TO_CONTENT[title.category] : undefined,
    artist: title.artists[0] ?? undefined,
    // "Circle"/"parody" aren't provided by these providers — surfaced as unknown.
    circle: undefined,
    subtitle: title.alternativeTitles[0] ?? undefined,
    language: title.language ?? undefined,
    parody: undefined,
    releaseYear: year && year > 1900 ? year : undefined,
    updatedDays: daysSince(title.updatedAt),
    // Real synopsis when the source supplies one (many listings omit it).
    description: title.description || undefined,
    // Centralized adult classification (only eligible titles reach this point).
    adult: title.adult.classification,
  };
}

/** Base slug of the reader route that owns a chapter.
 *
 * Reader and pages routes derive the provider from the slug's FIRST segment
 * (`anilist-119913` → provider `anilist`), so when chapters are served
 * cross-provider (AniList/Dynasty metadata + another source's chapters), every
 * reader link must use the chapter's own provider — not the profile's slug.
 * Convention: `NormalizedChapter.titleId` is `"<provider>:<providerId>"`.
 */
export function readerBaseSlug(chapter: NormalizedChapter): string {
  const namespaced = `${chapter.provider}:`;
  if (chapter.titleId.startsWith(namespaced)) {
    return `${chapter.provider}-${chapter.titleId.slice(namespaced.length)}`;
  }
  return chapter.titleId.includes(":")
    ? chapter.titleId.replace(":", "-")
    : `${chapter.provider}-${chapter.titleId}`;
}

/** Map a chapter to a UI collection entry built on the Manga shape. */
export function chapterToManga(title: NormalizedTitle, chapter: NormalizedChapter): Manga {
  const base = toManga(title);
  const num = chapter.chapterNumber ? Number(chapter.chapterNumber) : null;
  return {
    ...base,
    slug: `${readerBaseSlug(chapter)}#ch-${chapter.providerChapterId}`,
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
