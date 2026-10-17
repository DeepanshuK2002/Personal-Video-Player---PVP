// MangaDex adapter.
//
// Classification: VERIFIED_AND_AVAILABLE (metadata + chapters + readable pages).
// Public, documented API (https://api.mangadex.org). MangaDex permits API use
// with attribution and rate limiting; we respect a shared rate budget and always
// link back to the source page. We request English translations by default and
// never bypass any access control.

import { cached, providerFetch } from "./http";
import { classifyMangaDex, inferOrigin } from "./adult";
import {
  CATEGORY_LABEL,
  ProviderError,
  type Category,
  type ChapterOptions,
  type ContentProvider,
  type NormalizedChapter,
  type NormalizedPage,
  type NormalizedTitle,
  type NormalizedUpdate,
  type ProviderCapabilities,
  type ProviderInfo,
  type PublicationStatus,
  type SearchOptions,
  type TrendingOptions,
  type UpdateOptions,
} from "./types";

const BASE = "https://api.mangadex.org";
const MANGADEX_URL = "https://mangadex.org";

const CACHE_TTL = 5 * 60 * 1000;
const PAGES_TTL = 60 * 60 * 1000; // at-home page servers are stable for a while

// READHENTAI is an adult-only catalogue: request MangaDex's adult + mature
// content ratings so every returned title passes the central catalogue
// eligibility filter (general-audience "safe" content is NEVER part of this
// catalogue and would otherwise be filtered out, emptying results).
//   pornographic -> confirmed_adult ; erotica/suggestive -> mature_non_explicit.
// Applied to search, the chapter feed (adult titles expose NO chapters under a
// safe-only feed query), latest, and trending.
const ADULT_CONTENT_RATINGS = ["pornographic", "erotica", "suggestive"];
function setAdultContentRating(p: { set(key: string, value: string): void }): void {
  for (const r of ADULT_CONTENT_RATINGS) p.set("contentRating[]", r);
}

const CAPABILITIES: ProviderCapabilities = {
  search: true,
  getTitle: true,
  getChapters: true,
  getChapterPages: true,
  trending: true,
  latestUpdates: true,
  ratings: false, // MangaDex exposes no aggregate score in the public API
};

const INFO: ProviderInfo = {
  id: "mangadex",
  name: "MangaDex",
  baseUrl: BASE,
  status: "VERIFIED_AND_AVAILABLE",
  attribution: "Content sourced from MangaDex (mangadex.org).",
  capabilities: CAPABILITIES,
  adult: false,
};

/* --------------------------- raw payload types --------------------------- */

interface MdLocalised {
  en?: string;
  [lang: string]: string | undefined;
}

interface MdRelationship {
  id: string;
  type: string;
  attributes?: Record<string, unknown>;
}

interface MdManga {
  id: string;
  attributes: {
    title?: MdLocalised;
    altTitles?: MdLocalised[];
    description?: MdLocalised;
    publicationDemographic?: "shounen" | "shoujo" | "josei" | "seinen" | "none" | null;
    status?: string;
    year?: number | null;
    contentRating?: string;
    tags?: Array<{ attributes?: { name?: MdLocalised; group?: string } }>;
    lastChapter?: string | null;
    latestUploadedChapter?: string | null;
  };
  relationships?: MdRelationship[];
}

interface MdChapter {
  id: string;
  attributes: {
    title?: string | null;
    chapter?: string | null;
    pages?: number;
    translatedLanguage?: string | null;
    publishAt?: string;
    readableAt?: string;
  };
  relationships?: MdRelationship[];
}

interface MdListResponse<T> {
  result: string;
  data: T[];
  limit?: number;
  offset?: number;
  total?: number;
}

/* ------------------------------- helpers ------------------------------- */

function pickLocalised(obj: MdLocalised | undefined | null): string | null {
  if (!obj) return null;
  return obj.en ?? Object.values(obj).find(Boolean) ?? null;
}

function relationAttr(rel: MdRelationship[] | undefined, type: string): Record<string, unknown> | undefined {
  return rel?.find((r) => r.type === type)?.attributes;
}

/** Map MangaDex demographic + tags to the app's coarse Category. */
function mapCategory(manga: MdManga): Category {
  const demo = manga.attributes?.publicationDemographic;
  if (demo === "shoujo" || demo === "josei") return "manhwa";
  // Fall back to scanlation-group region tags when demographic is absent.
  const tagNames = (manga.attributes?.tags ?? [])
    .map((t) => pickLocalised(t.attributes?.name)?.toLowerCase())
    .filter(Boolean) as string[];
  if (tagNames.includes("manhwa")) return "manhwa";
  if (tagNames.includes("manhua")) return "manhua";
  return "manga";
}

function mapStatus(status?: string | null): PublicationStatus | null {
  switch (status) {
    case "completed":
      return "Completed";
    case "ongoing":
      return "In Process";
    case "cancelled":
    case "hiatus":
      return "Paused";
    default:
      return null;
  }
}

function coverUrl(manga: MdManga): string | null {
  const cover = relationAttr(manga.relationships, "cover_art") as { fileName?: string } | undefined;
  if (!cover?.fileName) return null;
  return `${BASE}/uploads/covers/${manga.id}/${cover.fileName}.256.jpg`;
}

function normalize(manga: MdManga): NormalizedTitle {
  const title = pickLocalised(manga.attributes?.title) ?? "Untitled";
  const altTitles = (manga.attributes?.altTitles ?? [])
    .map((t) => pickLocalised(t))
    .filter((t): t is string => Boolean(t));
  const tags = (manga.attributes?.tags ?? [])
    .map((t) => pickLocalised(t.attributes?.name))
    .filter((t): t is string => Boolean(t));
  const authors = [(relationAttr(manga.relationships, "author") as { name?: string } | undefined)?.name]
    .filter((n): n is string => Boolean(n));
  const artists = [(relationAttr(manga.relationships, "artist") as { name?: string } | undefined)?.name]
    .filter((n): n is string => Boolean(n));

  // Content rating is MangaDex's reliable maturity signal; feed it through the
  // centralized classifier so the data pipeline filters consistently.
  const adult = classifyMangaDex(
    (manga.attributes?.contentRating as string | undefined) ?? null,
    inferOrigin({ demographic: manga.attributes?.publicationDemographic ?? null, tags }),
  );

  return {
    id: `mangadex:${manga.id}`,
    provider: INFO.id,
    providerId: manga.id,
    slug: `mangadex-${manga.id}`,
    title,
    alternativeTitles: altTitles,
    description: pickLocalised(manga.attributes?.description),
    category: mapCategory(manga),
    isAdult: adult.isAdult,
    coverImage: coverUrl(manga),
    rating: null, // not provided by the public API — surfaced as "unavailable"
    popularity: null,
    genres: [], // MangaDex tags are surfaced via `tags`
    tags,
    artists,
    authors,
    language: null,
    status: mapStatus(manga.attributes?.status),
    updatedAt: manga.attributes?.latestUploadedChapter ? null : null,
    publishedAt: manga.attributes?.year ? `${manga.attributes.year}` : null,
    providerUrl: `${MANGADEX_URL}/title/${manga.id}`,
    readable: true,
    adult,
  };
}

function normalizeChapter(chapter: MdChapter, titleId: string): NormalizedChapter {
  const pageCount = chapter.attributes?.pages ?? null;
  return {
    id: `mangadex:${chapter.id}`,
    titleId,
    provider: INFO.id,
    providerChapterId: chapter.id,
    chapterNumber: chapter.attributes?.chapter ?? null,
    chapterTitle: chapter.attributes?.title ?? null,
    language: chapter.attributes?.translatedLanguage ?? null,
    publishedAt: chapter.attributes?.readableAt ?? chapter.attributes?.publishAt ?? null,
    pageCount,
    // A chapter is only "readable" if we can actually resolve its pages.
    readable: (pageCount ?? 0) > 0,
  };
}

/* ------------------------------- adapter -------------------------------- */

export const mangadex: ContentProvider = {
  getProviderInfo(): ProviderInfo {
    return INFO;
  },

  async searchTitles(query: string, options: SearchOptions = {}): Promise<NormalizedTitle[]> {
    const limit = Math.min(options.limit ?? 20, 50);
    const offset = Math.max(options.offset ?? 0, 0);
    const order =
      options.order === "popular" ? "followedCount"
      : options.order === "rating" ? "rating"
      : "latestUploadedChapter";

    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    params.set("includes[]", "cover_art", );
    params.set(`order[${order}]`, "desc");
    if (query) params.set("title", query);
    if (options.isAdult === false) {
      // Adult content explicitly disabled for this request: SFW only.
      params.set("contentRating[]", "safe");
      params.set("contentRating[]", "suggestive");
    } else {
      // Adult-only platform default (isAdult true OR undefined): request the
      // eligible adult/mature ratings so results reach the catalogue.
      setAdultContentRating(params);
    }
    if (options.status) {
      params.set("status[]", options.status === "Completed" ? "completed" : options.status === "In Process" ? "ongoing" : "hiatus");
    }
    const lang = options.language ?? "en";
    if (lang) params.set("availableTranslatedLanguage[]", lang);

    const key = `mangadex:search:${params.toString()}`;
    return cached(key, CACHE_TTL, async () => {
      const res = await providerFetch<MdListResponse<MdManga>>(`${BASE}/manga?${params}`, {
        providerId: INFO.id,
      });
      return (res.data ?? []).map(normalize);
    });
  },

  async getTitle(providerId: string): Promise<NormalizedTitle | null> {
    const key = `mangadex:title:${providerId}`;
    return cached(key, CACHE_TTL, async () => {
      // The single-manga endpoint returns `data` as an object (entity), while
      // list endpoints return an array (collection). Handle both shapes.
      const res = await providerFetch<
        MdListResponse<MdManga> | { result: string; data: MdManga }
      >(`${BASE}/manga/${providerId}?includes[]=cover_art`, {
        providerId: INFO.id,
      });
      const data = Array.isArray(res.data) ? res.data[0] : (res.data as MdManga | undefined);
      return data ? normalize(data) : null;
    });
  },

  async getChapters(providerId: string, options: ChapterOptions = {}): Promise<NormalizedChapter[]> {
    const limit = Math.min(options.limit ?? 500, 500);
    const lang = options.language ?? "en";
    const order = options.order ?? "desc";

    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set(`order[chapter]`, order);
    if (lang) params.set("translatedLanguage[]", lang);
    // Adult titles expose their chapters only under matching adult ratings.
    setAdultContentRating(params);

    const key = `mangadex:chapters:${providerId}:${lang}:${order}`;
    return cached(key, CACHE_TTL, async () => {
      const res = await providerFetch<MdListResponse<MdChapter>>(
        `${BASE}/manga/${providerId}/feed?${params}`,
        { providerId: INFO.id },
      );
      return (res.data ?? []).map((c) => normalizeChapter(c, `mangadex:${providerId}`));
    });
  },

  async getChapterPages(providerId: string, chapterId: string): Promise<NormalizedPage[]> {
    const key = `mangadex:pages:${chapterId}`;
    return cached(key, PAGES_TTL, async () => {
      const atHome = await providerFetch<{
        baseUrl?: string;
        chapter?: { hash?: string; data?: string[]; dataSaver?: string[] };
      }>(`${BASE}/at-home/server/${chapterId}`, { providerId: INFO.id });

      const baseUrl = atHome.baseUrl;
      const hash = atHome.chapter?.hash;
      const files = atHome.chapter?.data ?? [];
      if (!baseUrl || !hash || files.length === 0) {
        throw new ProviderError(INFO.id, "no pages available", "http", false);
      }
      // Preserve the provider's page order exactly.
      return files.map((file, index) => ({
        index,
        imageUrl: `${baseUrl}/data/${hash}/${file}`,
      }));
    });
  },

  async getTrending(options: TrendingOptions = {}): Promise<NormalizedTitle[]> {
    // MangaDex has no public "trending" endpoint; use the most-followed titles
    // as a genuine popularity proxy rather than fabricating a ranking.
    return this.searchTitles("", {
      limit: options.limit ?? 20,
      order: "popular",
      categories: options.categories,
      isAdult: options.isAdult,
    });
  },

  async getLatestUpdates(options: UpdateOptions = {}): Promise<NormalizedUpdate[]> {
    const limit = Math.min(options.limit ?? 20, 50);
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("order[readableAt]", "desc");
    params.set("includes[]", "manga");
    params.set("includes[]", "cover_art");
    setAdultContentRating(params);
    const lang = options.language ?? "en";
    if (lang) params.set("translatedLanguage[]", lang);

    const key = `mangadex:latest:${limit}:${lang}`;
    const chapters = await cached(key, CACHE_TTL, async () => {
      const res = await providerFetch<MdListResponse<MdChapter>>(`${BASE}/chapter?${params}`, {
        providerId: INFO.id,
      });
      return res.data ?? [];
    });

    // The chapter feed's embedded manga lacks cover_art. Collect the distinct
    // manga ids, then batch-fetch them (with covers) in a single /manga call.
    const ids: string[] = [];
    const seenIds = new Set<string>();
    for (const chapter of chapters) {
      const mangaRel = chapter.relationships?.find((r) => r.type === "manga") as
        | { id: string }
        | undefined;
      if (mangaRel?.id && !seenIds.has(mangaRel.id)) {
        seenIds.add(mangaRel.id);
        ids.push(mangaRel.id);
      }
      if (ids.length >= limit) break;
    }
    if (ids.length === 0) return [];

    const mangaParams = new URLSearchParams();
    ids.forEach((id) => mangaParams.append("ids[]", id));
    mangaParams.set("includes[]", "cover_art");
    setAdultContentRating(mangaParams);

    const mangaByKey = new Map<string, NormalizedTitle>();
    const mangaList = await cached(`mangadex:latest-manga:${ids.join(",")}`, CACHE_TTL, async () => {
      const res = await providerFetch<MdListResponse<MdManga>>(`${BASE}/manga?${mangaParams}`, {
        providerId: INFO.id,
      });
      return res.data ?? [];
    });
    for (const m of mangaList) mangaByKey.set(m.id, normalize(m));

    const seen = new Set<string>();
    const updates: NormalizedUpdate[] = [];
    for (const chapter of chapters) {
      const mangaRel = chapter.relationships?.find((r) => r.type === "manga") as
        | { id: string }
        | undefined;
      if (!mangaRel?.id || seen.has(mangaRel.id)) continue;
      const title = mangaByKey.get(mangaRel.id);
      if (!title) continue;
      seen.add(mangaRel.id);
      updates.push({ title, chapter: normalizeChapter(chapter, title.id) });
      if (updates.length >= limit) break;
    }
    return updates;
  },
};
