"use strict";
// Canonical series matching tests — mocked, NO network.
// Covers: confident merges, false-positive prevention (approximate title alone
// must NOT merge), author-conflict disqualification, adult-signal combination,
// and adult eligibility filtering before grouping.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const series_matching_1 = require("../series-matching");
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
        id: overrides.id ?? `p:${overrides.title}`,
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
(0, node_test_1.describe)("normalizeTitleForMatch / tokenSimilarity", () => {
    (0, node_test_1.it)("normalizes case, punctuation and whitespace", () => {
        strict_1.default.equal((0, series_matching_1.normalizeTitleForMatch)("  The, GHOST!  "), "the ghost");
    });
    (0, node_test_1.it)("scores identical titles as 1 and unrelated as low", () => {
        strict_1.default.equal((0, series_matching_1.tokenSimilarity)("Chainsaw Man", "Chainsaw Man"), 1);
        strict_1.default.ok((0, series_matching_1.tokenSimilarity)("Chainsaw Man", "Cooking Papa") < 0.3);
    });
});
(0, node_test_1.describe)("seriesMatchConfidence / areSameSeries", () => {
    (0, node_test_1.it)("merges exact same title across providers with light corroboration", () => {
        const a = title({ title: "Blue Period", provider: "mangadex", publishedAt: "2017" });
        const b = title({ title: "Blue Period", provider: "anilist", publishedAt: "2017" });
        const r = (0, series_matching_1.seriesMatchConfidence)(a, b);
        strict_1.default.ok(r.score >= series_matching_1.MATCH_THRESHOLD, `score ${r.score} below threshold`);
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), true);
    });
    (0, node_test_1.it)("merges when an alternative title matches exactly", () => {
        const a = title({ title: "Fireworks", provider: "mangadex" });
        const b = title({ title: "Hana no Chiri Bito", provider: "anilist", alternativeTitles: ["Fireworks"] });
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), true);
    });
    (0, node_test_1.it)("does NOT merge on approximate title similarity ALONE (needs corroboration)", () => {
        // High token overlap but no author/year/category corroboration.
        const a = title({ title: "The Legend of Heroes", provider: "x" });
        const b = title({ title: "Legend of Heroes Saga", provider: "y" });
        const r = (0, series_matching_1.seriesMatchConfidence)(a, b);
        strict_1.default.ok(r.score < series_matching_1.MATCH_THRESHOLD, `should NOT merge, score ${r.score}`);
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), false);
    });
    (0, node_test_1.it)("does NOT merge clearly different titles", () => {
        const a = title({ title: "Chainsaw Man", provider: "x" });
        const b = title({ title: "Cooking Mama Recipes", provider: "y" });
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), false);
    });
    (0, node_test_1.it)("disqualifies a merge when known authors conflict", () => {
        const a = title({ title: "Same Title", provider: "x", authors: ["Alice"] });
        const b = title({ title: "Same Title", provider: "y", authors: ["Bob"] });
        const r = (0, series_matching_1.seriesMatchConfidence)(a, b);
        strict_1.default.ok(r.reasons.includes("conflicting authors"));
        strict_1.default.ok(r.score < series_matching_1.MATCH_THRESHOLD, `conflicting authors must block merge, got ${r.score}`);
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), false);
    });
    (0, node_test_1.it)("strengthens a merge with a shared author", () => {
        const a = title({ title: "Same Title", provider: "x", authors: ["Alice"] });
        const b = title({ title: "Same Title", provider: "y", authors: ["Alice"] });
        const r = (0, series_matching_1.seriesMatchConfidence)(a, b);
        strict_1.default.ok(r.reasons.includes("shared author/artist"));
        strict_1.default.equal((0, series_matching_1.areSameSeries)(a, b), true);
    });
});
(0, node_test_1.describe)("combineAdultSignals", () => {
    const sig = (c, sp = "p") => ({
        ...adult(c),
        sourceProvider: sp,
    });
    (0, node_test_1.it)("honors explicit adult evidence from any provider", () => {
        const out = (0, series_matching_1.combineAdultSignals)([sig("general_audience", "a"), sig("confirmed_adult", "b")]);
        strict_1.default.equal(out.classification, "confirmed_adult");
        strict_1.default.equal(out.isAdult, true);
    });
    (0, node_test_1.it)("classifies general only when no adult/mature evidence exists", () => {
        const out = (0, series_matching_1.combineAdultSignals)([sig("general_audience"), sig("unknown")]);
        strict_1.default.equal(out.classification, "general_audience");
        strict_1.default.equal(out.isAdult, false);
    });
    (0, node_test_1.it)("prefers mature over unknown/general when no explicit adult", () => {
        const out = (0, series_matching_1.combineAdultSignals)([sig("unknown"), sig("mature_non_explicit")]);
        strict_1.default.equal(out.classification, "mature_non_explicit");
    });
    (0, node_test_1.it)("returns unknown when nothing is known", () => {
        const out = (0, series_matching_1.combineAdultSignals)([sig("unknown")]);
        strict_1.default.equal(out.classification, "unknown");
        strict_1.default.equal(out.isAdult, false);
    });
    (0, node_test_1.it)("records the contributing providers for diagnostics", () => {
        const out = (0, series_matching_1.combineAdultSignals)([sig("confirmed_adult", "mangadex"), sig("unknown", "dynasty")]);
        strict_1.default.ok(out.sourceProvider.includes("mangadex"));
        strict_1.default.ok(out.sourceProvider.includes("dynasty"));
    });
});
(0, node_test_1.describe)("groupIntoCanonicalSeries", () => {
    (0, node_test_1.it)("groups two providers' identical titles into ONE canonical series", () => {
        const series = (0, series_matching_1.groupIntoCanonicalSeries)([
            title({ title: "Shared Work", provider: "mangadex", providerId: "md1", publishedAt: "2020" }),
            title({ title: "Shared Work", provider: "anilist", providerId: "al1", publishedAt: "2020" }),
        ]);
        strict_1.default.equal(series.length, 1);
        strict_1.default.equal(series[0].providerMappings.length, 2);
        strict_1.default.deepEqual(series[0].providerMappings.map((m) => m.providerId).sort(), ["anilist", "mangadex"]);
    });
    (0, node_test_1.it)("keeps unmatched titles as separate series (no false merge)", () => {
        const series = (0, series_matching_1.groupIntoCanonicalSeries)([
            title({ title: "Alpha Story", provider: "mangadex", providerId: "md1", authors: ["A"] }),
            title({ title: "Beta Chronicle", provider: "anilist", providerId: "al1", authors: ["B"] }),
        ]);
        strict_1.default.equal(series.length, 2);
    });
    (0, node_test_1.it)("excludes general_audience records before they seed a series", () => {
        const series = (0, series_matching_1.groupIntoCanonicalSeries)([
            title({ title: "Kid Comic", provider: "mangadex", adult: adult("general_audience") }),
        ]);
        strict_1.default.equal(series.length, 0);
    });
    (0, node_test_1.it)("excludes unknown-classification records (conservative)", () => {
        const series = (0, series_matching_1.groupIntoCanonicalSeries)([
            title({ title: "Unclassified", provider: "dynasty", adult: adult("unknown") }),
        ]);
        strict_1.default.equal(series.length, 0);
    });
    (0, node_test_1.it)("includes confirmed_adult and preserves the manga origin", () => {
        const series = (0, series_matching_1.groupIntoCanonicalSeries)([
            title({
                title: "Adult Manga Work",
                provider: "mangadex",
                category: "manga",
                adult: adult("confirmed_adult", "manga"),
            }),
        ]);
        strict_1.default.equal(series.length, 1);
        strict_1.default.equal(series[0].isAdult, true);
        strict_1.default.equal(series[0].origin, "manga"); // origin separate from age
        strict_1.default.equal(series[0].category, "manga");
    });
    (0, node_test_1.it)("produces a stable canonical id for the same input", () => {
        const input = () => [
            title({ title: "Stable Id Work", provider: "mangadex", providerId: "md1", publishedAt: "2021" }),
            title({ title: "Stable Id Work", provider: "anilist", providerId: "al1", publishedAt: "2021" }),
        ];
        const a = (0, series_matching_1.groupIntoCanonicalSeries)(input())[0];
        const b = (0, series_matching_1.groupIntoCanonicalSeries)(input())[0];
        strict_1.default.equal(a.id, b.id);
        strict_1.default.equal(a.slug, b.slug);
    });
});
