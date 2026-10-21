"use strict";
// Chapter reconciliation tests — mocked fixtures, NO network.
// Covers: decimal parsing, cross-provider merging, language separation,
// stable ordering, special-chapter placement, and version preservation.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const reconcile_1 = require("../reconcile");
function ch(partial) {
    return {
        providerId: "p1",
        providerSeriesId: "series-1",
        providerChapterId: partial.label.toLowerCase().replace(/\W+/g, "-"),
        language: "en",
        pageAccessCapability: "available",
        ...partial,
    };
}
(0, node_test_1.describe)("parseChapterLabel", () => {
    (0, node_test_1.it)("parses a plain chapter number", () => {
        strict_1.default.deepEqual((0, reconcile_1.parseChapterLabel)("Chapter 12"), { number: 12, type: "main", volume: null });
    });
    (0, node_test_1.it)("parses decimals without collapsing 10.5 to 105", () => {
        const r = (0, reconcile_1.parseChapterLabel)("Ch. 10.5");
        strict_1.default.equal(r.number, 10.5);
        strict_1.default.notEqual(r.number, 105);
    });
    (0, node_test_1.it)("extracts a volume when present", () => {
        const r = (0, reconcile_1.parseChapterLabel)("Vol. 3 Chapter 7");
        strict_1.default.equal(r.number, 7);
        strict_1.default.equal(r.volume, "3");
    });
    (0, node_test_1.it)("classifies specials", () => {
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Prologue").type, "prologue");
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Epilogue").type, "epilogue");
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Oneshot").type, "oneshot");
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Side Story: Beach").type, "side_story");
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Extra #2").type, "extra");
    });
    (0, node_test_1.it)("returns null number for numberless labels", () => {
        strict_1.default.equal((0, reconcile_1.parseChapterLabel)("Untitled").number, null);
    });
});
(0, node_test_1.describe)("assignSortKeys", () => {
    (0, node_test_1.it)("orders numberless prologue first and epilogue last", () => {
        const keys = (0, reconcile_1.assignSortKeys)([
            { number: null, type: "prologue", inputIndex: 0 },
            { number: 1, type: "main", inputIndex: 1 },
            { number: 2, type: "main", inputIndex: 2 },
            { number: null, type: "epilogue", inputIndex: 3 },
        ]);
        // Sorted ascending must be: prologue, 1, 2, epilogue
        const order = keys.map((_, i) => i).sort((a, b) => keys[a] - keys[b]);
        strict_1.default.deepEqual(order, [0, 1, 2, 3]);
    });
});
(0, node_test_1.describe)("reconcileChapters", () => {
    (0, node_test_1.it)("merges the same chapter across two providers into one canonical chapter", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5" }),
            ch({ providerId: "dynasty", providerChapterId: "ds-ch5", label: "Ch. 5" }),
        ]);
        strict_1.default.equal(out.length, 1);
        strict_1.default.equal(out[0].sourceVersions.length, 2);
        strict_1.default.deepEqual(out[0].sourceVersions.map((v) => v.providerId).sort(), ["dynasty", "mangadex"]);
    });
    (0, node_test_1.it)("keeps original provider chapter IDs and labels", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5: The Fight" }),
        ]);
        strict_1.default.equal(out[0].label, "Chapter 5: The Fight");
        strict_1.default.equal(out[0].sourceVersions[0].providerChapterId, "md-5");
    });
    (0, node_test_1.it)("does NOT merge different languages", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "a", providerChapterId: "en-5", label: "Chapter 5", language: "en" }),
            ch({ providerId: "b", providerChapterId: "ja-5", label: "Chapter 5", language: "ja" }),
        ]);
        strict_1.default.equal(out.length, 2);
        strict_1.default.deepEqual(out.map((c) => c.language).sort(), ["en", "ja"]);
    });
    (0, node_test_1.it)("orders numerically, placing 10.5 between 10 and 11 (not at 105)", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ label: "Chapter 10" }),
            ch({ label: "Chapter 2" }),
            ch({ label: "Chapter 10.5" }),
            ch({ label: "Chapter 1" }),
        ]);
        strict_1.default.deepEqual(out.map((c) => c.chapterNumber), [1, 2, 10, 10.5]);
    });
    (0, node_test_1.it)("is stable regardless of input order", () => {
        const a = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ label: "Chapter 3" }),
            ch({ label: "Chapter 1" }),
            ch({ label: "Chapter 2" }),
        ]);
        const b = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ label: "Chapter 2" }),
            ch({ label: "Chapter 3" }),
            ch({ label: "Chapter 1" }),
        ]);
        strict_1.default.deepEqual(a.map((c) => c.chapterNumber), b.map((c) => c.chapterNumber));
    });
    (0, node_test_1.it)("supplies a chapter from a secondary provider that the preferred one lacks", () => {
        // Preferred (mangadex) has 1,2,3,5; secondary (dynasty) has 4.
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "mangadex", providerChapterId: "md-1", label: "Chapter 1" }),
            ch({ providerId: "mangadex", providerChapterId: "md-2", label: "Chapter 2" }),
            ch({ providerId: "mangadex", providerChapterId: "md-3", label: "Chapter 3" }),
            ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5" }),
            ch({ providerId: "dynasty", providerChapterId: "ds-4", label: "Chapter 4" }),
        ]);
        strict_1.default.deepEqual(out.map((c) => c.chapterNumber), [1, 2, 3, 4, 5]);
        // Chapter 4 came only from the secondary provider.
        const ch4 = out.find((c) => c.chapterNumber === 4);
        strict_1.default.equal(ch4.sourceVersions.length, 1);
        strict_1.default.equal(ch4.sourceVersions[0].providerId, "dynasty");
    });
    (0, node_test_1.it)("keeps numberless chapters with different labels separate", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ label: "Prologue" }),
            ch({ label: "Epilogue" }),
            ch({ providerId: "z", label: "Side Story: Summer" }),
        ]);
        strict_1.default.equal(out.length, 3);
    });
    (0, node_test_1.it)("does not force-merge ambiguous numberless chapters (empty labels)", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "a", providerChapterId: "x", label: "" }),
            ch({ providerId: "b", providerChapterId: "y", label: "" }),
        ]);
        // Two distinct empty-label chapters must not collapse into one.
        strict_1.default.equal(out.length, 2);
    });
    (0, node_test_1.it)("preserves multiple release-group versions of the same chapter", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-1", [
            ch({ providerId: "a", providerChapterId: "a-7", label: "Chapter 7", releaseGroup: "GroupA" }),
            ch({ providerId: "b", providerChapterId: "b-7", label: "Chapter 7", releaseGroup: "GroupB" }),
        ]);
        strict_1.default.equal(out.length, 1);
        const groups = out[0].sourceVersions.map((v) => v.releaseGroup).sort();
        strict_1.default.deepEqual(groups, ["GroupA", "GroupB"]);
    });
    (0, node_test_1.it)("stamps a stable canonical id derived from the series id", () => {
        const out = (0, reconcile_1.reconcileChapters)("series-9", [ch({ label: "Chapter 1" })]);
        strict_1.default.ok(out[0].id.startsWith("series-9:ch:"));
        strict_1.default.equal(out[0].seriesId, "series-9");
    });
});
