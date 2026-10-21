"use strict";
// Cross-provider chapter fallback tests — mocked, NO network.
// Covers: exact-title/alt-title match supplies chapters (metadata-only
// profiles like AniList get a readable collection), no-match safety (a wrong
// series never leaks in), own-provider exclusion, failover past a candidate
// whose search or chapter list fails, and the `readable` flag reflecting the
// SERVING provider's capability.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const registry_1 = require("../registry");
function adult(classification, origin = "manga") {
    return {
        classification,
        isAdult: classification === "confirmed_adult",
        isExplicit: classification === "confirmed_adult",
        origin,
        sourceProvider: "test",
        reason: `test:${classification}`,
    };
}
function title(overrides) {
    const a = overrides.adult ?? adult("confirmed_adult");
    return {
        id: overrides.id ?? `${overrides.provider ?? "p"}:${overrides.title}`,
        provider: overrides.provider ?? "mangadex",
        providerId: overrides.providerId ?? "id-1",
        slug: overrides.slug ?? "slug-1",
        title: overrides.title,
        alternativeTitles: overrides.alternativeTitles ?? [],
        description: overrides.description ?? null,
        category: overrides.category ?? "manga",
        isAdult: overrides.isAdult ?? a.isAdult,
        coverImage: overrides.coverImage ?? null,
        rating: overrides.rating ?? null,
        popularity: overrides.popularity ?? null,
        genres: overrides.genres ?? [],
        tags: overrides.tags ?? [],
        artists: overrides.artists ?? [],
        authors: overrides.authors ?? [],
        language: overrides.language ?? "en",
        status: overrides.status ?? null,
        updatedAt: overrides.updatedAt ?? null,
        publishedAt: overrides.publishedAt ?? null,
        providerUrl: overrides.providerUrl ?? null,
        readable: overrides.readable ?? false,
        adult: a,
        originalLanguage: overrides.originalLanguage ?? null,
    };
}
function chapter(provider, titleId, n) {
    return {
        id: `${provider}:${titleId}#${n}`,
        titleId,
        provider,
        providerChapterId: `ch-${n}`,
        chapterNumber: String(n),
        chapterTitle: null,
        language: "en",
        publishedAt: null,
        pageCount: 10,
        imageUrl: "",
    };
}
function fakeProvider(opts) {
    return {
        getProviderInfo: () => ({
            id: opts.id,
            name: opts.id,
            baseUrl: "https://example.test",
            status: "VERIFIED_AND_AVAILABLE",
            capabilities: {
                search: Boolean(opts.search),
                getTitle: false,
                getChapters: Boolean(opts.chapters),
                getChapterPages: opts.pages ?? false,
                trending: false,
                latestUpdates: false,
                ratings: false,
            },
            adult: true,
        }),
        searchTitles: opts.search ?? (async () => []),
        getTitle: async () => null,
        getChapters: opts.chapters ?? (async () => []),
        getChapterPages: async () => [],
    };
}
// The user-visible case: an AniList metadata record (no chapters capability)
// must find its series on an adult source that does serve chapters.
const target = title({ title: "Secret Class", provider: "anilist", providerId: "119913" });
const sourceHit = title({
    title: "Secret Class",
    provider: "hentai18",
    providerId: "secret-class",
    slug: "hentai18-secret-class",
});
(0, node_test_1.describe)("findChaptersByTitleMatch", () => {
    (0, node_test_1.it)("supplies chapters from a source whose title matches exactly", async () => {
        const source = fakeProvider({
            id: "hentai18",
            search: async (q) => (q === "Secret Class" ? [sourceHit] : []),
            chapters: async (providerId) => {
                strict_1.default.equal(providerId, "secret-class");
                return [
                    chapter("hentai18", "hentai18:secret-class", 1),
                    chapter("hentai18", "hentai18:secret-class", 2),
                ];
            },
            pages: true,
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [source]);
        strict_1.default.equal(out.length, 2);
        strict_1.default.ok(out.every((c) => c.provider === "hentai18"));
        strict_1.default.ok(out.every((c) => c.readable === true), "pages-capable source → readable");
        strict_1.default.ok(out.every((c) => c.titleId === "hentai18:secret-class"));
    });
    (0, node_test_1.it)("matches when the identity only appears as an alternative title", async () => {
        const altHit = title({
            title: "비밀수업",
            provider: "hentaireadmoe",
            providerId: "bimil-soweop",
            alternativeTitles: ["Secret Class"],
        });
        const source = fakeProvider({
            id: "hentaireadmoe",
            search: async () => [altHit],
            chapters: async () => [chapter("hentaireadmoe", "hentaireadmoe:bimil-soweop", 1)],
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [source]);
        strict_1.default.equal(out.length, 1);
        strict_1.default.equal(out[0].provider, "hentaireadmoe");
        strict_1.default.equal(out[0].readable, false, "source without page capability → not readable");
    });
    (0, node_test_1.it)("never returns chapters of a different series", async () => {
        const wrong = title({ title: "Cooking Mama Recipes", provider: "hentai18" });
        const source = fakeProvider({
            id: "hentai18",
            search: async () => [wrong],
            chapters: async () => [chapter("hentai18", "hentai18:cooking-mama", 1)],
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [source]);
        strict_1.default.deepEqual(out, []);
    });
    (0, node_test_1.it)("does not merge on approximate title similarity alone", async () => {
        // High token overlap, no corroborating metadata → below threshold.
        const near = title({ title: "The Secret Classes", provider: "hentai18" });
        const source = fakeProvider({
            id: "hentai18",
            search: async () => [near],
            chapters: async () => [chapter("hentai18", "hentai18:the-secret-classes", 1)],
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [source]);
        strict_1.default.deepEqual(out, []);
    });
    (0, node_test_1.it)("excludes the title's own provider even when it would match", async () => {
        const own = fakeProvider({
            id: "anilist",
            search: async () => [sourceHit],
            chapters: async () => [chapter("anilist", "anilist:119913", 1)],
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [own]);
        strict_1.default.deepEqual(out, [], "own provider already failed by id — must not be retried by search");
    });
    (0, node_test_1.it)("falls through to the next source when the matched one cannot list chapters", async () => {
        const broken = fakeProvider({
            id: "hentai18",
            search: async () => [sourceHit],
            chapters: async () => {
                throw new Error("chapter list unavailable");
            },
        });
        const working = fakeProvider({
            id: "hentaireadmoe",
            search: async () => [sourceHit],
            chapters: async () => [chapter("hentaireadmoe", "hentaireadmoe:secret-class", 1)],
            pages: true,
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [broken, working]);
        strict_1.default.equal(out.length, 1);
        strict_1.default.equal(out[0].provider, "hentaireadmoe");
    });
    (0, node_test_1.it)("falls through when a candidate's search endpoint is dead", async () => {
        const dead = fakeProvider({
            id: "omegascans",
            search: async () => {
                throw new Error("HTTP 404");
            },
            chapters: async () => [chapter("omegascans", "omegascans:secret-class", 1)],
        });
        const working = fakeProvider({
            id: "hentai18",
            search: async () => [sourceHit],
            chapters: async () => [chapter("hentai18", "hentai18:secret-class", 1)],
        });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [dead, working]);
        strict_1.default.equal(out.length, 1);
        strict_1.default.equal(out[0].provider, "hentai18");
    });
    (0, node_test_1.it)("returns [] when no candidate supports search or chapters", async () => {
        const metadataOnly = fakeProvider({ id: "anilist" });
        const out = await (0, registry_1.findChaptersByTitleMatch)(target, "en", [metadataOnly]);
        strict_1.default.deepEqual(out, []);
    });
});
