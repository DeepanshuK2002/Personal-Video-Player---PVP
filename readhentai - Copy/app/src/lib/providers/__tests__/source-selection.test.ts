// Source selection + chapter-level fallback tests — mocked, NO network.
// Covers: eligibility-before-scoring, bounded fallback, same-chapter-only
// attempts, honest failure (never substituting a different chapter).

import { describe, it, beforeEach } from "node:test";
import assert from "node:assert/strict";

import {
  eligibleVersions,
  rankVersions,
  selectBestVersion,
  resolveWithFallback,
  resetObservations,
  recordSuccess,
  recordFailure,
  getObservation,
} from "../source-selection";
import type { CanonicalChapter, ChapterSourceVersion } from "../types";

function ver(partial: Partial<ChapterSourceVersion> = {}): ChapterSourceVersion {
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

function chapter(versions: ChapterSourceVersion[]): CanonicalChapter {
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

beforeEach(() => resetObservations());

describe("eligibleVersions", () => {
  it("excludes unavailable sources", () => {
    const out = eligibleVersions([
      ver({ providerId: "a", pageAccessCapability: "unavailable" }),
      ver({ providerId: "b", pageAccessCapability: "available" }),
    ]);
    assert.deepEqual(out.map((v) => v.providerId), ["b"]);
  });

  it("when pages are needed, only 'available' versions qualify", () => {
    const out = eligibleVersions(
      [
        ver({ providerId: "a", pageAccessCapability: "link_out_only" }),
        ver({ providerId: "b", pageAccessCapability: "metadata_only" }),
        ver({ providerId: "c", pageAccessCapability: "available" }),
      ],
      { needsPages: true },
    );
    assert.deepEqual(out.map((v) => v.providerId), ["c"]);
  });

  it("filters by preferred language but keeps unknown ('und') language", () => {
    const out = eligibleVersions(
      [
        ver({ providerId: "en", language: "en" }),
        ver({ providerId: "ja", language: "ja" }),
        ver({ providerId: "unk", language: "und" }),
      ],
      { preferredLanguage: "en" },
    );
    assert.deepEqual(out.map((v) => v.providerId).sort(), ["en", "unk"]);
  });
});

describe("selectBestVersion", () => {
  it("prefers a readable source over a metadata-only one", () => {
    const best = selectBestVersion(
      chapter([
        ver({ providerId: "meta", pageAccessCapability: "metadata_only" }),
        ver({ providerId: "read", pageAccessCapability: "available" }),
      ]),
      { needsPages: true },
    );
    assert.equal(best?.providerId, "read");
  });

  it("returns null when nothing is eligible (honest, no substitution)", () => {
    const best = selectBestVersion(
      chapter([ver({ providerId: "x", pageAccessCapability: "unavailable" })]),
      { needsPages: true },
    );
    assert.equal(best, null);
  });

  it("favors the preferred language among equal-capability sources", () => {
    const best = selectBestVersion(
      chapter([
        ver({ providerId: "ja", language: "ja" }),
        ver({ providerId: "en", language: "en" }),
      ]),
      { preferredLanguage: "en", needsPages: true },
    );
    assert.equal(best?.providerId, "en");
  });

  it("uses measured reliability only after the minimum sample size", () => {
    // One provider has a poor recent record; with enough samples it should lose.
    for (let i = 0; i < 5; i++) recordFailure("flaky");
    for (let i = 0; i < 5; i++) recordSuccess("solid", 50);

    const ranked = rankVersions(
      chapter([
        ver({ providerId: "flaky", providerChapterId: "f-1" }),
        ver({ providerId: "solid", providerChapterId: "s-1" }),
      ]),
      { needsPages: true },
    ).filter((r) => r.eligible);

    ranked.sort((a, b) => b.score - a.score);
    assert.equal(ranked[0].version.providerId, "solid");
    assert.ok(getObservation("flaky")!.failure >= 5);
  });
});

describe("resolveWithFallback", () => {
  it("falls back to another eligible version of the SAME chapter on failure", async () => {
    const chap = chapter([
      ver({ providerId: "primary", providerChapterId: "p-1" }),
      ver({ providerId: "secondary", providerChapterId: "s-1" }),
    ]);

    const result = await resolveWithFallback(chap, async (v) => {
      if (v.providerId === "primary") throw new Error("primary down");
      return `pages-from-${v.providerId}`;
    });

    assert.equal(result.value, "pages-from-secondary");
    assert.equal(result.servedBy, "secondary");
    assert.equal(result.attempts.length, 2);
    assert.equal(result.attempts[0].ok, false);
    assert.equal(result.attempts[1].ok, true);
  });

  it("never substitutes a different chapter — attempts stay on the same chapter id", async () => {
    const chap = chapter([
      ver({ providerId: "a", providerChapterId: "ch-13" }),
      ver({ providerId: "b", providerChapterId: "ch-13-alt" }),
    ]);
    const seen: string[] = [];
    await resolveWithFallback(chap, async (v) => {
      seen.push(v.providerChapterId);
      throw new Error("always fails");
    });
    for (const id of seen) {
      assert.ok(id.startsWith("ch-13"), `attempted unrelated chapter: ${id}`);
    }
  });

  it("bounds the number of attempts (no infinite retry)", async () => {
    const chap = chapter([
      ver({ providerId: "a" }),
      ver({ providerId: "b" }),
      ver({ providerId: "c" }),
      ver({ providerId: "d" }),
    ]);
    let calls = 0;
    const result = await resolveWithFallback(
      chap,
      async () => {
        calls++;
        throw new Error("fail");
      },
      { maxAttempts: 2 },
    );
    assert.equal(calls, 2);
    assert.equal(result.value, null);
    assert.equal(result.servedBy, null);
  });

  it("returns null with recorded attempts when all eligible versions fail", async () => {
    const chap = chapter([ver({ providerId: "only" })]);
    const result = await resolveWithFallback(chap, async () => {
      throw new Error("nope");
    });
    assert.equal(result.value, null);
    assert.equal(result.servedBy, null);
    assert.equal(result.attempts.length, 1);
    assert.equal(result.attempts[0].ok, false);
    // Failure was recorded against provider health.
    assert.ok(getObservation("only")!.failure >= 1);
  });

  it("does not attempt ineligible versions at all", async () => {
    const chap = chapter([
      ver({ providerId: "unavailable", pageAccessCapability: "unavailable" }),
      ver({ providerId: "ok", pageAccessCapability: "available" }),
    ]);
    const attempted: string[] = [];
    const result = await resolveWithFallback(chap, async (v) => {
      attempted.push(v.providerId);
      return "ok";
    });
    assert.deepEqual(attempted, ["ok"]);
    assert.equal(result.value, "ok");
  });
});
