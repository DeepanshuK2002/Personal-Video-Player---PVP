// AniList adapter.
//
// Classification: METADATA_ONLY (VERIFIED_AND_AVAILABLE for metadata).
// Public GraphQL API (https://graphql.anilist.co), no credentials required for
// read-only queries. Supplies rich metadata + a genuine aggregate rating
// (averageScore) that MangaDex does not expose. It provides NO chapter images,
// so getChapters / getChapterPages throw "unsupported" and the aggregator never
// invents chapters for it.

import { cached, rawJson } from "./http";
import { classifyAniList, inferOrigin } from "./adult";
import {
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
  type SearchOptions,
  type TrendingOptions,
  type UpdateOptions,
} from "./types";

const ENDPOINT = "https://graphql.anilist.co";
const ANILIST_URL = "https://anilist.co";
const CACHE_TTL = 10 * 60 * 1000;

const CAPABILITIES: ProviderCapabilities = {
  search: true,
  getTitle: true,
  getChapters: false,
  getChapterPages: false,
  trending: true,
  latestUpdates: false,
  ratings: true,
};

const INFO: ProviderInfo = {
  id: "anilist",
  name: "AniList",
  baseUrl: ENDPOINT,
  status: "METADATA_ONLY",
  attribution: "Metadata & ratings from AniList (anilist.co).",
  capabilities: CAPABILITIES,
  adult: false,
};

const MEDIA_FIELDS = `
  id
  idMal
  type
  format
  status
  countryOfOrigin
  isAdult
  description(asHtml: false)
  startDate { year }
  updatedAt
  popularity
  meanScore
  averageScore
  genres
  tags { name }
  coverImage { large extraLarge }
  bannerImage
  title { romaji english native }
  synonyms
  staff(perPage: 1, sort: RELEVANCE) { edges { node { name { full } } role } }
  staffRoles: staff(perPage: 5, sort: RELEVANCE) { edges { role } }
  staffNodes: staff(perPage: 5, sort: RELEVANCE) { edges { node { name { full } } } }
`;

interface AlMedia {
  id: number;
  idMal?: number;
  type?: string;
  format?: string;
  status?: string;
  countryOfOrigin?: string;
  isAdult?: boolean;
  description?: string | null;
  startDate?: { year?: number | null };
  updatedAt?: number | null;
  popularity?: number | null;
  meanScore?: number | null;
  averageScore?: number | null;
  genres?: string[] | null;
  tags?: Array<{ name?: string }> | null;
  coverImage?: { large?: string; extraLarge?: string } | null;
  title?: { romaji?: string; english?: string; native?: string } | null;
  synonyms?: string[] | null;
  staffNodes?: { edges: Array<{ node: { name?: { full?: string } } }> } | null;
}

// postGql returns the already-unwrapped `data` object, so this is the shape of
// `{ data: { Page: { media } } }.data`.
interface AlPage<T> {
  Page: { media: T[] };
}

/** Map AniList format + tags to the app's coarse Category. */
function mapCategory(media: AlMedia): Category {
  const tagNames = (media.tags ?? []).map((t) => t.name?.toLowerCase()).filter(Boolean) as string[];
  const origin = (media.countryOfOrigin ?? "").toUpperCase();
  if (tagNames.includes("manhwa") || origin === "KR") return "manhwa";
  if (tagNames.includes("manhua") || origin === "CN" || origin === "TW") return "manhua";
  return "manga";
}

function mapStatus(status?: string): NormalizedTitle["status"] {
  switch (status) {
    case "FINISHED":
      return "Completed";
    case "RELEASING":
      return "In Process";
    case "CANCELLED":
    case "HIATUS":
      return "Paused";
    default:
      return null;
  }
}

function normalize(media: AlMedia): NormalizedTitle {
  const title =
    media.title?.english ?? media.title?.romaji ?? media.title?.native ?? "Untitled";
  const alt = [media.title?.romaji, media.title?.native, ...(media.synonyms ?? [])].filter(
    (t): t is string => Boolean(t && t !== title),
  );
  const artists = (media.staffNodes?.edges ?? [])
    .map((e) => e.node?.name?.full)
    .filter((n): n is string => Boolean(n));
  const tags = (media.tags ?? []).map((t) => t.name).filter((n): n is string => Boolean(n));

  // AniList exposes a single isAdult flag; map it through the shared classifier
  // so age classification stays centralized and separate from origin category.
  const adult = classifyAniList(
    Boolean(media.isAdult),
    inferOrigin({ demographic: media.format ?? null, tags }),
  );

  return {
    id: `anilist:${media.id}`,
    provider: INFO.id,
    providerId: String(media.id),
    slug: `anilist-${media.id}`,
    title,
    alternativeTitles: alt,
    description: media.description?.replace(/<[^>]+>/g, "") ?? null,
    category: mapCategory(media),
    isAdult: adult.isAdult,
    coverImage: media.coverImage?.large ?? media.coverImage?.extraLarge ?? null,
    // AniList averageScore is 0..100 with null meaning "no score" — never guessed.
    rating: media.averageScore ?? media.meanScore ?? null,
    popularity: media.popularity ?? null,
    genres: media.genres ?? [],
    tags,
    artists,
    authors: artists,
    language: null,
    status: mapStatus(media.status),
    updatedAt: media.updatedAt ? new Date(media.updatedAt * 1000).toISOString() : null,
    publishedAt: media.startDate?.year ? `${media.startDate.year}` : null,
    providerUrl: `${ANILIST_URL}/manga/${media.id}`,
    // Metadata-only: never claim readable chapters.
    readable: false,
    adult,
  };
}

/** POST a GraphQL query (AniList does not accept GET for these). */
async function postGql<T>(query: string, variables: Record<string, unknown>): Promise<T> {
  const key = `anilist:gql:${query.slice(0, 40)}:${JSON.stringify(variables)}`;
  return cached(key, CACHE_TTL, async () => {
    try {
      // rawJson uses node:https so the POST never blocks Next's response stream.
      const json = await rawJson<{ data?: T; errors?: Array<{ message: string }> }>(ENDPOINT, {
        method: "POST",
        timeoutMs: 10_000,
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ query, variables }),
      });
      if (json.errors?.length) throw new ProviderError(INFO.id, json.errors[0].message, "parse", false);
      if (!json.data) throw new ProviderError(INFO.id, "no data", "parse", false);
      return json.data;
    } catch (err) {
      if (err instanceof ProviderError) throw err;
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  });
}

/** Reject unsupported operations explicitly instead of inventing chapter data. */
function unsupported(op: string): never {
  throw new ProviderError(INFO.id, `${op} is not supported (metadata-only provider)`, "unsupported", false);
}

export const anilist: ContentProvider = {
  getProviderInfo(): ProviderInfo {
    return INFO;
  },

  async searchTitles(query: string, options: SearchOptions = {}): Promise<NormalizedTitle[]> {
    const limit = Math.min(options.limit ?? 20, 50);
    const page = Math.floor(Math.max(options.offset ?? 0, 0) / limit) + 1;
    const sort =
      options.order === "popular" ? "POPULARITY_DESC"
      : options.order === "rating" ? "SCORE_DESC"
      : options.order === "latest" ? "UPDATED_AT_DESC"
      : "SEARCH_MATCH";

    const search = query?.trim();
    const type = options.categories?.length === 1
      ? options.categories[0] === "manhwa" ? "MANHWA" : options.categories[0] === "manhua" ? "MANHUA" : "MANGA"
      : "MANGA";

    const variables: Record<string, unknown> = { page, perPage: limit, sort: [sort], type };
    let where = "";
    if (search) { variables.search = search; }
    if (options.isAdult !== true) variables.isAdult = false;
    if (options.genres?.length) { variables.genre_in = options.genres; }

    const queryStr = `
      query ($page: Int, $perPage: Int, $sort: [MediaSort], $search: String, $type: MediaType, $isAdult: Boolean, $genre_in: [String]) {
        Page(page: $page, perPage: $perPage) {
          media(sort: $sort, search: $search, type: $type, isAdult: $isAdult, genre_in: $genre_in) { ${MEDIA_FIELDS} }
        }
      }`;
    const data = await postGql<AlPage<AlMedia>>(queryStr, variables);
    return (data.Page?.media ?? []).map(normalize);
  },

  async getTitle(providerId: string): Promise<NormalizedTitle | null> {
    const queryStr = `query ($id: Int) { Media(id: $id, type: MANGA) { ${MEDIA_FIELDS} } }`;
    const data = await postGql<{ Media: AlMedia | null }>(queryStr, { id: Number(providerId) });
    return data.Media ? normalize(data.Media) : null;
  },

  getChapters(_providerId: string, _options?: ChapterOptions): Promise<NormalizedChapter[]> {
    return Promise.resolve(unsupported("getChapters"));
  },

  getChapterPages(_providerId: string, _chapterId: string): Promise<NormalizedPage[]> {
    return Promise.resolve(unsupported("getChapterPages"));
  },

  async getTrending(options: TrendingOptions = {}): Promise<NormalizedTitle[]> {
    const limit = Math.min(options.limit ?? 20, 50);
    const queryStr = `query ($page: Int, $perPage: Int, $isAdult: Boolean) {
      Page(page: $page, perPage: $perPage) {
        media(sort: [TRENDING_DESC, POPULARITY_DESC], type: MANGA, isAdult: $isAdult) { ${MEDIA_FIELDS} }
      }
    }`;
    const data = await postGql<AlPage<AlMedia>>(queryStr, { page: 1, perPage: limit, isAdult: options.isAdult ?? false });
    return (data.Page?.media ?? []).map(normalize);
  },

  getLatestUpdates(_options?: UpdateOptions): Promise<NormalizedUpdate[]> {
    return Promise.resolve(unsupported("getLatestUpdates"));
  },
};
