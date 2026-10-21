// Dynasty Reader adapter.
//
// Classification: AUTHORIZED_WITH_RESTRICTIONS (verified operational for the
// capabilities below, with attribution). Source: https://dynasty-scans.com —
// a long-standing scanlation site exposing stable public JSON endpoints.
// We request only those endpoints, add an identifying User-Agent, and always
// link back to the source page. Chapter images are served from Dynasty's own
// hosts (hot-linked, never stored or redistributed by this app).
//
// IMPORTANT — operator note: Dynasty hosts scanlated translations. The registry
// (docs/PROVIDER_REGISTRY.md) records the licensing/redistribution consideration
// so the operator can confirm this display use is acceptable for their context.
//
// Verified capability map (real requests, see registry for evidence):
//   search ............ UNAVAILABLE  (/search and /search.json return HTTP 500)
//   getTitle .......... available    /series/{permalink}.json
//   getChapters ....... UNAVAILABLE  no per-series endpoint — /chapters.json?series=
//                                    is ignored (returns the global recent list)
//                                    and derived permalinks (_ch1) 404
//   getChapterPages ... available    /chapters/{permalink}.json -> pages[].url
//   latestUpdates ..... available    /chapters/added.json
//   trending .......... UNAVAILABLE  /hot.json, /recent.json return 404
//
// Because search and full chapter enumeration are unavailable, Dynasty can only
// surface through "Latest updates" (where each entry carries a directly readable
// chapter permalink). It is registered for exactly those genuine capabilities and
// never fakes the rest.

import { cached, providerFetch } from "./http";
import { classifyDynasty, inferOrigin } from "./adult";
import { parseChapterLabel } from "./reconcile";
import {
  ProviderError,
  type ChapterOptions,
  type ContentProvider,
  type NormalizedChapter,
  type NormalizedPage,
  type NormalizedTitle,
  type NormalizedUpdate,
  type ProviderInfo,
  type SearchOptions,
  type UpdateOptions,
} from "./types";

const BASE = "https://dynasty-scans.com";
const TTL_METADATA = 5 * 60_000; // 5 min
const TTL_CHAPTER_PAGES = 60 * 60_000; // 60 min
const TTL_LATEST = 60_000; // 1 min

/* ------------------------------------------------------------------ */
/* Raw response shapes                                                 */
/* ------------------------------------------------------------------ */

interface DsTag {
  type?: string;
  name?: string;
  permalink?: string;
}

interface DsSeries {
  name?: string;
  type?: string;
  permalink?: string;
  tags?: DsTag[];
  cover?: string | null;
  description?: string | null;
  aliases?: string[] | null;
}

interface DsChapter {
  title?: string;
  long_title?: string;
  series?: string | null;
  permalink?: string;
  tags?: DsTag[];
  pages?: { name?: string; url?: string }[];
  released_on?: string | null;
  added_on?: string | null;
}

interface DsChapterList {
  chapters?: DsChapter[];
  current_page?: number;
  total_pages?: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const abs = (u: string | null | undefined): string | null =>
  u ? (u.startsWith("http") ? u : `${BASE}${u}`) : null;

const stripHtml = (h: string | null | undefined): string | null =>
  h ? h.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim() || null : null;

function tagsOfType(tags: DsTag[] | undefined, type: string): string[] {
  return (tags ?? [])
    .filter((t) => t.type === type && t.name)
    .map((t) => t.name as string);
}

function allTagNames(tags: DsTag[] | undefined): string[] {
  return (tags ?? []).map((t) => t.name).filter((n): n is string => Boolean(n));
}

function statusFromTags(tags: DsTag[] | undefined): NormalizedTitle["status"] {
  const s = tagsOfType(tags, "Status")[0]?.toLowerCase() ?? "";
  if (s.includes("complete")) return "Completed";
  if (s.includes("ongoing") || s.includes("process")) return "In Process";
  if (s.includes("pause") || s.includes("hiatus")) return "Paused";
  return null;
}

/** Find the series permalink referenced by a chapter's tags. */
function seriesPermalinkOf(ch: DsChapter): string | null {
  const seriesTag = (ch.tags ?? []).find((t) => t.type === "Series" && t.permalink);
  if (seriesTag?.permalink) return seriesTag.permalink;
  // Fall back to deriving from the chapter permalink ("..._chN" -> "...").
  if (ch.permalink) {
    const m = ch.permalink.match(/^(.*)_ch\d+(?:\.\d+)?$/);
    if (m) return m[1];
  }
  return null;
}

/** Build a NormalizedTitle from a chapter record's series context (cheap, for Latest). */
function titleFromChapter(ch: DsChapter): NormalizedTitle | null {
  const sp = seriesPermalinkOf(ch);
  const seriesName = ch.series ?? (ch.tags ?? []).find((t) => t.type === "Series")?.name;
  if (!sp || !seriesName) return null;

  const tags = allTagNames(ch.tags);
  const authors = tagsOfType(ch.tags, "Author");
  const genres = tagsOfType(ch.tags, "General");
  const adult = classifyDynasty(tags, inferOrigin({ tags }));

  return {
    id: `dynasty:${sp}`,
    provider: INFO.id,
    providerId: sp,
    slug: `dynasty-${sp}`,
    title: seriesName,
    alternativeTitles: [],
    description: null,
    category: "manga",
    isAdult: adult.isAdult,
    coverImage: null, // not present on chapter records; populated by getTitle()
    rating: null, // Dynasty exposes no aggregate rating
    popularity: null,
    genres,
    tags,
    artists: [],
    authors,
    language: null,
    status: statusFromTags(ch.tags),
    updatedAt: null,
    publishedAt: null,
    providerUrl: `${BASE}/series/${sp}`,
    // No enumerable chapter list, so a Dynasty title's detail page cannot show
    // a reliable Collection / Read Now — kept false to avoid dead reading UI.
    readable: false,
    adult,
  };
}

function chapterFromRecord(ch: DsChapter, title: NormalizedTitle): NormalizedChapter | null {
  if (!ch.permalink) return null;
  const label = ch.long_title ?? ch.title ?? ch.permalink;
  const parsed = parseChapterLabel(label);
  return {
    id: `dynasty:${ch.permalink}`,
    titleId: title.id,
    provider: INFO.id,
    providerChapterId: ch.permalink,
    chapterNumber: parsed.number !== null ? String(parsed.number) : null,
    chapterTitle: ch.title ?? null,
    // Dynasty scanlations are English; the API does not expose a language field,
    // so we record the observed language explicitly rather than guessing.
    language: "en",
    publishedAt: ch.released_on ?? ch.added_on ?? null,
    pageCount: ch.pages?.length ?? null,
    imageUrl: "",
    // This specific chapter permalink IS readable via getChapterPages().
    readable: true,
  };
}

/* ------------------------------------------------------------------ */
/* Adapter                                                             */
/* ------------------------------------------------------------------ */

const INFO: ProviderInfo = {
  id: "dynasty",
  name: "Dynasty Reader",
  baseUrl: BASE,
  status: "AUTHORIZED_WITH_RESTRICTIONS",
  attribution:
    "Content © Dynasty Reader scanlation group. Metadata & images hot-linked from " +
    "dynasty-scans.com with attribution; not stored or redistributed by this app.",
  capabilities: {
    search: false, // /search returns 500
    getTitle: true,
    getChapters: false, // no per-series chapter endpoint
    getChapterPages: true,
    trending: false, // /hot.json, /recent.json 404
    latestUpdates: true,
    ratings: false,
  },
  adult: false, // catalogue is predominantly Yuri/GL; adult flag not exposed
};

export const dynasty: ContentProvider = {
  getProviderInfo: () => INFO,

  async searchTitles(_query: string, _opts?: SearchOptions): Promise<NormalizedTitle[]> {
    // Search endpoint is server-side broken (HTTP 500 on every variant tried).
    throw new ProviderError(INFO.id, "search endpoint unavailable (HTTP 500)", "unsupported", false);
  },

  async getTitle(providerId: string): Promise<NormalizedTitle | null> {
    const permalink = providerId.startsWith("dynasty-")
      ? providerId.slice("dynasty-".length)
      : providerId;
    if (!permalink) return null;

    const data = await cached(`dynasty:series:${permalink}`, TTL_METADATA, () =>
      providerFetch<DsSeries>(`${BASE}/series/${encodeURIComponent(permalink)}.json`, {
        providerId: INFO.id,
      }),
    );

    if (!data?.permalink || !data.name) return null;

    const tags = data.tags ?? [];
    const adult = classifyDynasty(allTagNames(tags), inferOrigin({ tags: allTagNames(tags) }));

    return {
      id: `dynasty:${data.permalink}`,
      provider: INFO.id,
      providerId: data.permalink,
      slug: `dynasty-${data.permalink}`,
      title: data.name,
      alternativeTitles: (data.aliases ?? []).filter((a): a is string => Boolean(a)),
      description: stripHtml(data.description),
      category: "manga",
      isAdult: adult.isAdult,
      coverImage: abs(data.cover),
      rating: null,
      popularity: null,
      genres: tagsOfType(tags, "General"),
      tags: allTagNames(tags),
      artists: [],
      authors: tagsOfType(tags, "Author"),
      language: null,
      status: statusFromTags(tags),
      updatedAt: null,
      publishedAt: null,
      providerUrl: `${BASE}/series/${data.permalink}`,
      readable: false, // see note in INFO — no enumerable chapter list
      adult,
    };
  },

  async getChapters(_providerId: string, _opts?: ChapterOptions): Promise<NormalizedChapter[]> {
    // No per-series chapter endpoint exists (verified). Never fabricate one.
    throw new ProviderError(
      INFO.id,
      "chapter enumeration unavailable for this source",
      "unsupported",
      false,
    );
  },

  async getChapterPages(_providerId: string, chapterId: string): Promise<NormalizedPage[]> {
    const permalink = chapterId.startsWith("dynasty-") ? chapterId.slice("dynasty-".length) : chapterId;
    if (!permalink) {
      throw new ProviderError(INFO.id, "missing chapter id", "unsupported", false);
    }

    const data = await cached(`dynasty:chapter:${permalink}`, TTL_CHAPTER_PAGES, () =>
      providerFetch<DsChapter>(`${BASE}/chapters/${encodeURIComponent(permalink)}.json`, {
        providerId: INFO.id,
      }),
    );

    const pages = data?.pages ?? [];
    if (pages.length === 0) {
      throw new ProviderError(INFO.id, "chapter has no pages", "parse", false);
    }

    return pages
      .filter((p) => p.url)
      .map((p, i) => ({
        index: i,
        imageUrl: abs(p.url) as string,
      }));
  },

  async getLatestUpdates(opts?: UpdateOptions): Promise<NormalizedUpdate[]> {
    const limit = opts?.limit ?? 24;
    const list = await cached("dynasty:latest", TTL_LATEST, () =>
      providerFetch<DsChapterList>(`${BASE}/chapters/added.json`, { providerId: INFO.id }),
    );

    const out: NormalizedUpdate[] = [];
    for (const ch of list?.chapters ?? []) {
      if (out.length >= limit) break;
      const title = titleFromChapter(ch);
      const chapter = title ? chapterFromRecord(ch, title) : null;
      if (title && chapter) out.push({ title, chapter });
    }
    return out;
  },
};
