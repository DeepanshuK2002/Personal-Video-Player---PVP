"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const adult_1 = require("../adult");
const enma_1 = require("../enma");
const registry_1 = require("../registry");
(0, node_test_1.describe)("classifyEnma", () => {
    (0, node_test_1.it)("classifies the nhentai source as confirmed adult, doujinshi origin", () => {
        const c = (0, adult_1.classifyEnma)("nhentai", "doujinshi");
        strict_1.default.equal(c.classification, "confirmed_adult");
        strict_1.default.equal(c.isAdult, true);
        strict_1.default.equal(c.isExplicit, true);
        strict_1.default.equal(c.origin, "doujinshi");
        strict_1.default.equal(c.sourceProvider, "enma");
        strict_1.default.equal((0, adult_1.isEligible)(c.classification, adult_1.DEFAULT_ADULT_POLICY), true);
    });
    (0, node_test_1.it)("keeps other Enma sources at unknown (never promoted to adult)", () => {
        const c = (0, adult_1.classifyEnma)("mangadex");
        strict_1.default.equal(c.classification, "unknown");
        strict_1.default.equal(c.isAdult, false);
        strict_1.default.equal((0, adult_1.isEligible)(c.classification, adult_1.DEFAULT_ADULT_POLICY), false);
    });
    (0, node_test_1.it)("treats a missing sidecar source as unknown", () => {
        for (const raw of [null, undefined, ""]) {
            const c = (0, adult_1.classifyEnma)(raw);
            strict_1.default.equal(c.classification, "unknown");
            strict_1.default.equal((0, adult_1.isEligible)(c.classification, adult_1.DEFAULT_ADULT_POLICY), false);
        }
    });
});
(0, node_test_1.describe)("enma provider capabilities", () => {
    (0, node_test_1.it)("declares correct capabilities and info", () => {
        const info = enma_1.enma.getProviderInfo();
        strict_1.default.equal(info.id, "enma");
        strict_1.default.equal(info.name, "Enma (nhentai)");
        strict_1.default.equal(info.adult, true);
        strict_1.default.equal(info.status, "SELF_HOST_REQUIRED");
        strict_1.default.equal(info.capabilities.search, true);
        strict_1.default.equal(info.capabilities.getTitle, true);
        strict_1.default.equal(info.capabilities.getChapters, true);
        strict_1.default.equal(info.capabilities.getChapterPages, true);
        strict_1.default.equal(info.capabilities.trending, true);
        // No dates at listing level / no rating signal — surfaced, not faked.
        strict_1.default.equal(info.capabilities.latestUpdates, false);
        strict_1.default.equal(info.capabilities.ratings, false);
        strict_1.default.equal(enma_1.enma.getLatestUpdates, undefined);
    });
    (0, node_test_1.it)("uses a hyphen-free provider id (slug contract)", () => {
        const info = enma_1.enma.getProviderInfo();
        strict_1.default.equal(info.id.includes("-"), false);
        // And the reserved prefix stripping used by getTitle/getChapters works.
        strict_1.default.equal(info.id.replace(/^enma-/, ""), "enma");
    });
    (0, node_test_1.it)("is registered in the global registry", () => {
        const provider = (0, registry_1.getProvider)("enma");
        strict_1.default.ok(provider);
        strict_1.default.equal(provider.getProviderInfo().id, "enma");
        const listed = (0, registry_1.listProviders)().find((p) => p.id === "enma");
        strict_1.default.ok(listed);
    });
});
(0, node_test_1.describe)("chapter id encoding", () => {
    (0, node_test_1.it)("round-trips title id + index (registry passes chapter id for both args)", () => {
        const ref = (0, enma_1.chapterRef)("688749", 0);
        strict_1.default.equal(ref, "688749__0");
        strict_1.default.deepEqual((0, enma_1.parseChapterRef)(ref), { titleId: "688749", index: 0 });
        const multi = (0, enma_1.chapterRef)("688749", 12);
        strict_1.default.deepEqual((0, enma_1.parseChapterRef)(multi), { titleId: "688749", index: 12 });
    });
    (0, node_test_1.it)("keeps embedded separators in the title id (split on last marker only)", () => {
        strict_1.default.deepEqual((0, enma_1.parseChapterRef)("abc__def__3"), { titleId: "abc__def", index: 3 });
    });
    (0, node_test_1.it)("accepts the namespaced NormalizedChapter.id form (`enma:<ref>`)", () => {
        // getChapters returns id: `enma:688749__0`; callers that pass chapter.id
        // (instead of providerChapterId) must still resolve — the sidecar rejects
        // a title id carrying the `enma:` prefix with HTTP 400.
        strict_1.default.deepEqual((0, enma_1.parseChapterRef)("enma:688749__0"), { titleId: "688749", index: 0 });
        strict_1.default.deepEqual((0, enma_1.parseChapterRef)("enma:688749__12"), { titleId: "688749", index: 12 });
        strict_1.default.equal((0, enma_1.parseChapterRef)("enma:"), null);
        strict_1.default.equal((0, enma_1.parseChapterRef)("enma:688749__"), null);
    });
    (0, node_test_1.it)("rejects malformed references", () => {
        for (const bad of ["", "__", "__1", "688749__", "688749__x", "688749__-1", "688749__1.5"]) {
            strict_1.default.equal((0, enma_1.parseChapterRef)(bad), null, `expected null for ${JSON.stringify(bad)}`);
        }
    });
});
(0, node_test_1.describe)("search sort mapping", () => {
    (0, node_test_1.it)("maps app orders onto the API v2 sort enum, never inventing ranks", () => {
        strict_1.default.equal((0, enma_1.sortForOrder)("popular"), "popular");
        strict_1.default.equal((0, enma_1.sortForOrder)("latest"), "date");
        strict_1.default.equal((0, enma_1.sortForOrder)("relevance"), undefined); // v2 has no relevance rank
        strict_1.default.equal((0, enma_1.sortForOrder)("rating"), undefined); // v2 exposes no ratings
        strict_1.default.equal((0, enma_1.sortForOrder)(undefined), undefined);
    });
});
(0, node_test_1.describe)("language + origin helpers", () => {
    (0, node_test_1.it)("maps language tags to codes and display labels", () => {
        strict_1.default.equal((0, enma_1.languageCode)("japanese"), "ja");
        strict_1.default.equal((0, enma_1.languageCode)("english"), "en");
        strict_1.default.equal((0, enma_1.languageCode)(null), null);
        strict_1.default.equal((0, enma_1.languageCode)("klingon"), null);
        strict_1.default.equal((0, enma_1.languageLabel)("japanese"), "Japanese");
        strict_1.default.equal((0, enma_1.languageLabel)(null), null);
    });
    (0, node_test_1.it)("derives the origin axis from nhentai category tags", () => {
        strict_1.default.equal((0, enma_1.originFromCategories)(["doujinshi"]), "doujinshi");
        strict_1.default.equal((0, enma_1.originFromCategories)(["manga"]), "manga");
        strict_1.default.equal((0, enma_1.originFromCategories)(["manhwa"]), "manhwa");
        strict_1.default.equal((0, enma_1.originFromCategories)(["Manga"]), "manga");
        strict_1.default.equal((0, enma_1.originFromCategories)([]), "doujinshi");
        // A doujinshi category wins over a generic manga one.
        strict_1.default.equal((0, enma_1.originFromCategories)(["manga", "doujinshi"]), "doujinshi");
    });
});
