// Chapter reconciliation tests — mocked fixtures, NO network.
// Covers: decimal parsing, cross-provider merging, language separation,
// stable ordering, special-chapter placement, and version preservation.

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  parseChapterLabel,
  assignSortKeys,
  reconcileChapters,
  type ChapterInput,
} from "../reconcile";

function ch(partial: Partial<ChapterInput> & { label: string }): ChapterInput {
  return {
    providerId: "p1",
    providerSeriesId: "series-1",
    providerChapterId: partial.label.toLowerCase().replace(/\W+/g, "-"),
    language: "en",
    pageAccessCapability: "available",
    ...partial,
  };
}

describe("parseChapterLabel", () => {
  it("parses a plain chapter number", () => {
    assert.deepEqual(parseChapterLabel("Chapter 12"), { number: 12, type: "main", volume: null });
  });

  it("parses decimals without collapsing 10.5 to 105", () => {
    const r = parseChapterLabel("Ch. 10.5");
    assert.equal(r.number, 10.5);
    assert.notEqual(r.number, 105);
  });

  it("extracts a volume when present", () => {
    const r = parseChapterLabel("Vol. 3 Chapter 7");
    assert.equal(r.number, 7);
    assert.equal(r.volume, "3");
  });

  it("classifies specials", () => {
    assert.equal(parseChapterLabel("Prologue").type, "prologue");
    assert.equal(parseChapterLabel("Epilogue").type, "epilogue");
    assert.equal(parseChapterLabel("Oneshot").type, "oneshot");
    assert.equal(parseChapterLabel("Side Story: Beach").type, "side_story");
    assert.equal(parseChapterLabel("Extra #2").type, "extra");
  });

  it("returns null number for numberless labels", () => {
    assert.equal(parseChapterLabel("Untitled").number, null);
  });
});

describe("assignSortKeys", () => {
  it("orders numberless prologue first and epilogue last", () => {
    const keys = assignSortKeys([
      { number: null, type: "prologue", inputIndex: 0 },
      { number: 1, type: "main", inputIndex: 1 },
      { number: 2, type: "main", inputIndex: 2 },
      { number: null, type: "epilogue", inputIndex: 3 },
    ]);
    // Sorted ascending must be: prologue, 1, 2, epilogue
    const order = keys.map((_, i) => i).sort((a, b) => keys[a] - keys[b]);
    assert.deepEqual(order, [0, 1, 2, 3]);
  });
});

describe("reconcileChapters", () => {
  it("merges the same chapter across two providers into one canonical chapter", () => {
    const out = reconcileChapters("series-1", [
      ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5" }),
      ch({ providerId: "dynasty", providerChapterId: "ds-ch5", label: "Ch. 5" }),
    ]);

    assert.equal(out.length, 1);
    assert.equal(out[0].sourceVersions.length, 2);
    assert.deepEqual(
      out[0].sourceVersions.map((v) => v.providerId).sort(),
      ["dynasty", "mangadex"],
    );
  });

  it("keeps original provider chapter IDs and labels", () => {
    const out = reconcileChapters("series-1", [
      ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5: The Fight" }),
    ]);
    assert.equal(out[0].label, "Chapter 5: The Fight");
    assert.equal(out[0].sourceVersions[0].providerChapterId, "md-5");
  });

  it("does NOT merge different languages", () => {
    const out = reconcileChapters("series-1", [
      ch({ providerId: "a", providerChapterId: "en-5", label: "Chapter 5", language: "en" }),
      ch({ providerId: "b", providerChapterId: "ja-5", label: "Chapter 5", language: "ja" }),
    ]);
    assert.equal(out.length, 2);
    assert.deepEqual(out.map((c) => c.language).sort(), ["en", "ja"]);
  });

  it("orders numerically, placing 10.5 between 10 and 11 (not at 105)", () => {
    const out = reconcileChapters("series-1", [
      ch({ label: "Chapter 10" }),
      ch({ label: "Chapter 2" }),
      ch({ label: "Chapter 10.5" }),
      ch({ label: "Chapter 1" }),
    ]);
    assert.deepEqual(
      out.map((c) => c.chapterNumber),
      [1, 2, 10, 10.5],
    );
  });

  it("is stable regardless of input order", () => {
    const a = reconcileChapters("series-1", [
      ch({ label: "Chapter 3" }),
      ch({ label: "Chapter 1" }),
      ch({ label: "Chapter 2" }),
    ]);
    const b = reconcileChapters("series-1", [
      ch({ label: "Chapter 2" }),
      ch({ label: "Chapter 3" }),
      ch({ label: "Chapter 1" }),
    ]);
    assert.deepEqual(
      a.map((c) => c.chapterNumber),
      b.map((c) => c.chapterNumber),
    );
  });

  it("supplies a chapter from a secondary provider that the preferred one lacks", () => {
    // Preferred (mangadex) has 1,2,3,5; secondary (dynasty) has 4.
    const out = reconcileChapters("series-1", [
      ch({ providerId: "mangadex", providerChapterId: "md-1", label: "Chapter 1" }),
      ch({ providerId: "mangadex", providerChapterId: "md-2", label: "Chapter 2" }),
      ch({ providerId: "mangadex", providerChapterId: "md-3", label: "Chapter 3" }),
      ch({ providerId: "mangadex", providerChapterId: "md-5", label: "Chapter 5" }),
      ch({ providerId: "dynasty", providerChapterId: "ds-4", label: "Chapter 4" }),
    ]);
    assert.deepEqual(
      out.map((c) => c.chapterNumber),
      [1, 2, 3, 4, 5],
    );
    // Chapter 4 came only from the secondary provider.
    const ch4 = out.find((c) => c.chapterNumber === 4)!;
    assert.equal(ch4.sourceVersions.length, 1);
    assert.equal(ch4.sourceVersions[0].providerId, "dynasty");
  });

  it("keeps numberless chapters with different labels separate", () => {
    const out = reconcileChapters("series-1", [
      ch({ label: "Prologue" }),
      ch({ label: "Epilogue" }),
      ch({ providerId: "z", label: "Side Story: Summer" }),
    ]);
    assert.equal(out.length, 3);
  });

  it("does not force-merge ambiguous numberless chapters (empty labels)", () => {
    const out = reconcileChapters("series-1", [
      ch({ providerId: "a", providerChapterId: "x", label: "" }),
      ch({ providerId: "b", providerChapterId: "y", label: "" }),
    ]);
    // Two distinct empty-label chapters must not collapse into one.
    assert.equal(out.length, 2);
  });

  it("preserves multiple release-group versions of the same chapter", () => {
    const out = reconcileChapters("series-1", [
      ch({ providerId: "a", providerChapterId: "a-7", label: "Chapter 7", releaseGroup: "GroupA" }),
      ch({ providerId: "b", providerChapterId: "b-7", label: "Chapter 7", releaseGroup: "GroupB" }),
    ]);
    assert.equal(out.length, 1);
    const groups = out[0].sourceVersions.map((v) => v.releaseGroup).sort();
    assert.deepEqual(groups, ["GroupA", "GroupB"]);
  });

  it("stamps a stable canonical id derived from the series id", () => {
    const out = reconcileChapters("series-9", [ch({ label: "Chapter 1" })]);
    assert.ok(out[0].id.startsWith("series-9:ch:"));
    assert.equal(out[0].seriesId, "series-9");
  });
});
