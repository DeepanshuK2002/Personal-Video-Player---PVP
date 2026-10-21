"use strict";
// AniList adapter.
//
// Classification: METADATA_ONLY (VERIFIED_AND_AVAILABLE for metadata).
// Public GraphQL API (https://graphql.anilist.co), no credentials required for
// read-only queries. Supplies rich metadata + a genuine aggregate rating
// (averageScore) that MangaDex does not expose. It provides NO chapter images,
// so getChapters / getChapterPages throw "unsupported" and the aggregator never
// invents chapters for it.
Object.defineProperty(exports, "__esModule", { value: true });
exports.anilist = void 0;
const http_1 = require("./http");
const adult_1 = require("./adult");
const types_1 = require("./types");
const ENDPOINT = "https://graphql.anilist.co";
const ANILIST_URL = "https://anilist.co";
const CACHE_TTL = 10 * 60 * 1000;
const CAPABILITIES = {
    search: true,
    getTitle: true,
    getChapters: false,
    getChapterPages: false,
    trending: true,
    latestUpdates: false,
    ratings: true,
};
const INFO = {
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
  chapters
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
/** Map AniList format + tags to the app's coarse Category. */
function mapCategory(media) {
    const tagNames = (media.tags ?? []).map((t) => t.name?.toLowerCase()).filter(Boolean);
    const origin = (media.countryOfOrigin ?? "").toUpperCase();
    if (tagNames.includes("manhwa") || origin === "KR")
        return "manhwa";
    if (tagNames.includes("manhua") || origin === "CN" || origin === "TW")
        return "manhua";
    return "manga";
}
function mapStatus(status) {
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
function normalize(media) {
    const title = media.title?.english ?? media.title?.romaji ?? media.title?.native ?? "Untitled";
    const alt = [media.title?.romaji, media.title?.native, ...(media.synonyms ?? [])].filter((t) => Boolean(t && t !== title));
    const artists = (media.staffNodes?.edges ?? [])
        .map((e) => e.node?.name?.full)
        .filter((n) => Boolean(n));
    const tags = (media.tags ?? []).map((t) => t.name).filter((n) => Boolean(n));
    // AniList exposes a single isAdult flag; map it through the shared classifier
    // so age classification stays centralized and separate from origin category.
    const adult = (0, adult_1.classifyAniList)(Boolean(media.isAdult), (0, adult_1.inferOrigin)({ demographic: media.format ?? null, tags }));
    return {
        id: `anilist:${media.id}`,
        provider: INFO.id,
        providerId: String(media.id),
        slug: `anilist-${media.id}`,
        title,
        alternativeTitles: alt,
        description: media.description?.replace(/<[^>]+>/g, "") ?? null,
        category: mapCategory(media),
        // Real series length; only present when AniList actually reports it.
        chapterCount: media.chapters ?? null,
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
async function postGql(query, variables) {
    const key = `anilist:gql:${query.slice(0, 40)}:${JSON.stringify(variables)}`;
    return (0, http_1.cached)(key, CACHE_TTL, async () => {
        try {
            // rawJson uses node:https so the POST never blocks Next's response stream.
            const json = await (0, http_1.rawJson)(ENDPOINT, {
                method: "POST",
                timeoutMs: 10000,
                headers: { "Content-Type": "application/json", Accept: "application/json" },
                body: JSON.stringify({ query, variables }),
            });
            if (json.errors?.length)
                throw new types_1.ProviderError(INFO.id, json.errors[0].message, "parse", false);
            if (!json.data)
                throw new types_1.ProviderError(INFO.id, "no data", "parse", false);
            return json.data;
        }
        catch (err) {
            if (err instanceof types_1.ProviderError)
                throw err;
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    });
}
/** Reject unsupported operations explicitly instead of inventing chapter data. */
function unsupported(op) {
    throw new types_1.ProviderError(INFO.id, `${op} is not supported (metadata-only provider)`, "unsupported", false);
}
exports.anilist = {
    getProviderInfo() {
        return INFO;
    },
    async searchTitles(query, options = {}) {
        const limit = Math.min(options.limit ?? 20, 50);
        const page = Math.floor(Math.max(options.offset ?? 0, 0) / limit) + 1;
        const sort = options.order === "popular" ? "POPULARITY_DESC"
            : options.order === "rating" ? "SCORE_DESC"
                : options.order === "latest" ? "UPDATED_AT_DESC"
                    : "SEARCH_MATCH";
        const search = query?.trim();
        // AniList's MediaType enum only contains MANGA/ANIME/… — there is NO
        // "MANHWA"/"MANHUA" member, and passing one makes the whole query fail with
        // HTTP 400 (dropping this provider on every category-filtered search).
        // Manhwa/manhua are still `type: MANGA` media; they are only distinguishable
        // by `countryOfOrigin` (KR → manhwa, CN/TW → manhua — the same signal
        // `mapCategory` uses below). Omitting the variable means "no filter", which
        // is exactly what we want for Manga / unfiltered queries.
        const category = options.categories?.length === 1 ? options.categories[0] : undefined;
        const countryOfOrigin = category === "manhwa" ? "KR" : category === "manhua" ? "CN" : undefined;
        const variables = { page, perPage: limit, sort: [sort], type: "MANGA" };
        if (countryOfOrigin)
            variables.countryOfOrigin = countryOfOrigin;
        if (search) {
            variables.search = search;
        }
        variables.isAdult = options.isAdult === false ? false : true;
        if (options.genres?.length) {
            variables.genre_in = options.genres;
        }
        const queryStr = `
      query ($page: Int, $perPage: Int, $sort: [MediaSort], $search: String, $type: MediaType, $isAdult: Boolean, $genre_in: [String], $countryOfOrigin: CountryCode) {
        Page(page: $page, perPage: $perPage) {
          media(sort: $sort, search: $search, type: $type, isAdult: $isAdult, genre_in: $genre_in, countryOfOrigin: $countryOfOrigin) { ${MEDIA_FIELDS} }
        }
      }`;
        const data = await postGql(queryStr, variables);
        return (data.Page?.media ?? []).map(normalize);
    },
    async getTitle(providerId) {
        const queryStr = `query ($id: Int) { Media(id: $id, type: MANGA) { ${MEDIA_FIELDS} } }`;
        const data = await postGql(queryStr, { id: Number(providerId) });
        return data.Media ? normalize(data.Media) : null;
    },
    getChapters(_providerId, _options) {
        return Promise.resolve(unsupported("getChapters"));
    },
    getChapterPages(_providerId, _chapterId) {
        return Promise.resolve(unsupported("getChapterPages"));
    },
    async getTrending(options = {}) {
        const limit = Math.min(options.limit ?? 20, 50);
        const queryStr = `query ($page: Int, $perPage: Int, $isAdult: Boolean) {
      Page(page: $page, perPage: $perPage) {
        media(sort: [TRENDING_DESC, POPULARITY_DESC], type: MANGA, isAdult: $isAdult) { ${MEDIA_FIELDS} }
      }
    }`;
        const data = await postGql(queryStr, {
            page: 1,
            perPage: limit,
            isAdult: options.isAdult === false ? false : true,
        });
        return (data.Page?.media ?? []).map(normalize);
    },
    getLatestUpdates(_options) {
        return Promise.resolve(unsupported("getLatestUpdates"));
    },
};
