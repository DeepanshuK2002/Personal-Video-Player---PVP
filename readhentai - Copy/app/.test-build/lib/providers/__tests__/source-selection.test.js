"use strict";
// Source selection + chapter-level fallback tests — mocked, NO network.
// Covers: eligibility-before-scoring, bounded fallback, same-chapter-only
// attempts, honest failure (never substituting a different chapter).
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const source_selection_1 = require("../source-selection");
function ver(partial = {}) {
    return {
        providerId: "prov-a",
        providerSeriesId: "series-1",
        providerChapterId: "ch-1",
        chapterNumber: "1",
        volumeNumber: null,
        title: null,
        language: "en",
        releaseGroup: null,
        sourceUrl: null,
        pageAccessCapability: "available",
        pageCount: 20,
        publishedAt: new Date().toISOString(),
        ...partial,
    };
}
function chapter(versions) {
    return {
        id: "series-1:ch:en::num::1",
        seriesId: "series-1",
        chapterNumber: 1,
        label: "Chapter 1",
        volumeNumber: null,
        title: null,
        language: "en",
        chapterType: "main",
        sourceVersions: versions,
        sortKey: 1,
    };
}
(0, node_test_1.beforeEach)(() => (0, source_selection_1.resetObservations)());
(0, node_test_1.describe)("eligibleVersions", () => {
    (0, node_test_1.it)("excludes unavailable sources", () => {
        const out = (0, source_selection_1.eligibleVersions)([
            ver({ providerId: "a", pageAccessCapability: "unavailable" }),
            ver({ providerId: "b", pageAccessCapability: "available" }),
        ]);
        strict_1.default.deepEqual(out.map((v) => v.providerId), ["b"]);
    });
    (0, node_test_1.it)("when pages are needed, only 'available' versions qualify", () => {
        const out = (0, source_selection_1.eligibleVersions)([
            ver({ providerId: "a", pageAccessCapability: "link_out_only" }),
            ver({ providerId: "b", pageAccessCapability: "metadata_only" }),
            ver({ providerId: "c", pageAccessCapability: "available" }),
        ], { needsPages: true });
        strict_1.default.deepEqual(out.map((v) => v.providerId), ["c"]);
    });
    (0, node_test_1.it)("filters by preferred language but keeps unknown ('und') language", () => {
        const out = (0, source_selection_1.eligibleVersions)([
            ver({ providerId: "en", language: "en" }),
            ver({ providerId: "ja", language: "ja" }),
            ver({ providerId: "unk", language: "und" }),
        ], { preferredLanguage: "en" });
        strict_1.default.deepEqual(out.map((v) => v.providerId).sort(), ["en", "unk"]);
    });
});
(0, node_test_1.describe)("selectBestVersion", () => {
    (0, node_test_1.it)("prefers a readable source over a metadata-only one", () => {
        const best = (0, source_selection_1.selectBestVersion)(chapter([
            ver({ providerId: "meta", pageAccessCapability: "metadata_only" }),
            ver({ providerId: "read", pageAccessCapability: "available" }),
        ]), { needsPages: true });
        strict_1.default.equal(best?.providerId, "read");
    });
    (0, node_test_1.it)("returns null when nothing is eligible (honest, no substitution)", () => {
        const best = (0, source_selection_1.selectBestVersion)(chapter([ver({ providerId: "x", pageAccessCapability: "unavailable" })]), { needsPages: true });
        strict_1.default.equal(best, null);
    });
    (0, node_test_1.it)("favors the preferred language among equal-capability sources", () => {
        const best = (0, source_selection_1.selectBestVersion)(chapter([
            ver({ providerId: "ja", language: "ja" }),
            ver({ providerId: "en", language: "en" }),
        ]), { preferredLanguage: "en", needsPages: true });
        strict_1.default.equal(best?.providerId, "en");
    });
    (0, node_test_1.it)("uses measured reliability only after the minimum sample size", () => {
        // One provider has a poor recent record; with enough samples it should lose.
        for (let i = 0; i < 5; i++)
            (0, source_selection_1.recordFailure)("flaky");
        for (let i = 0; i < 5; i++)
            (0, source_selection_1.recordSuccess)("solid", 50);
        const ranked = (0, source_selection_1.rankVersions)(chapter([
            ver({ providerId: "flaky", providerChapterId: "f-1" }),
            ver({ providerId: "solid", providerChapterId: "s-1" }),
        ]), { needsPages: true }).filter((r) => r.eligible);
        ranked.sort((a, b) => b.score - a.score);
        strict_1.default.equal(ranked[0].version.providerId, "solid");
        strict_1.default.ok((0, source_selection_1.getObservation)("flaky").failure >= 5);
    });
});
(0, node_test_1.describe)("resolveWithFallback", () => {
    (0, node_test_1.it)("falls back to another eligible version of the SAME chapter on failure", async () => {
        const chap = chapter([
            ver({ providerId: "primary", providerChapterId: "p-1" }),
            ver({ providerId: "secondary", providerChapterId: "s-1" }),
        ]);
        const result = await (0, source_selection_1.resolveWithFallback)(chap, async (v) => {
            if (v.providerId === "primary")
                throw new Error("primary down");
            return `pages-from-${v.providerId}`;
        });
        strict_1.default.equal(result.value, "pages-from-secondary");
        strict_1.default.equal(result.servedBy, "secondary");
        strict_1.default.equal(result.attempts.length, 2);
        strict_1.default.equal(result.attempts[0].ok, false);
        strict_1.default.equal(result.attempts[1].ok, true);
    });
    (0, node_test_1.it)("never substitutes a different chapter — attempts stay on the same chapter id", async () => {
        const chap = chapter([
            ver({ providerId: "a", providerChapterId: "ch-13" }),
            ver({ providerId: "b", providerChapterId: "ch-13-alt" }),
        ]);
        const seen = [];
        await (0, source_selection_1.resolveWithFallback)(chap, async (v) => {
            seen.push(v.providerChapterId);
            throw new Error("always fails");
        });
        for (const id of seen) {
            strict_1.default.ok(id.startsWith("ch-13"), `attempted unrelated chapter: ${id}`);
        }
    });
    (0, node_test_1.it)("bounds the number of attempts (no infinite retry)", async () => {
        const chap = chapter([
            ver({ providerId: "a" }),
            ver({ providerId: "b" }),
            ver({ providerId: "c" }),
            ver({ providerId: "d" }),
        ]);
        let calls = 0;
        const result = await (0, source_selection_1.resolveWithFallback)(chap, async () => {
            calls++;
            throw new Error("fail");
        }, { maxAttempts: 2 });
        strict_1.default.equal(calls, 2);
        strict_1.default.equal(result.value, null);
        strict_1.default.equal(result.servedBy, null);
    });
    (0, node_test_1.it)("returns null with recorded attempts when all eligible versions fail", async () => {
        const chap = chapter([ver({ providerId: "only" })]);
        const result = await (0, source_selection_1.resolveWithFallback)(chap, async () => {
            throw new Error("nope");
        });
        strict_1.default.equal(result.value, null);
        strict_1.default.equal(result.servedBy, null);
        strict_1.default.equal(result.attempts.length, 1);
        strict_1.default.equal(result.attempts[0].ok, false);
        // Failure was recorded against provider health.
        strict_1.default.ok((0, source_selection_1.getObservation)("only").failure >= 1);
    });
    (0, node_test_1.it)("does not attempt ineligible versions at all", async () => {
        const chap = chapter([
            ver({ providerId: "unavailable", pageAccessCapability: "unavailable" }),
            ver({ providerId: "ok", pageAccessCapability: "available" }),
        ]);
        const attempted = [];
        const result = await (0, source_selection_1.resolveWithFallback)(chap, async (v) => {
            attempted.push(v.providerId);
            return "ok";
        });
        strict_1.default.deepEqual(attempted, ["ok"]);
        strict_1.default.equal(result.value, "ok");
    });
});
