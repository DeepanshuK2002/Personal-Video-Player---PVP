// Canonical series matching tests — mocked, NO network.
// Covers: confident merges, false-positive prevention (approximate title alone
// must NOT merge), author-conflict disqualification, adult-signal combination,
// and adult eligibility filtering before grouping.

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  normalizeTitleForMatch,
  tokenSimilarity,
  seriesMatchConfidence,
  areSameSeries,
  combineAdultSignals,
  groupIntoCanonicalSeries,
  MATCH_THRESHOLD,
} from "../series-matching";
import type { AdultClassification, AdultContentMetadata, ContentOrigin } from "../adult";
import type { NormalizedTitle } from "../types";

function adult(
  classification: AdultClassification,
  origin: ContentOrigin = "manga",
): AdultContentMetadata {
  return {
    classification,
    isAdult: classification === "confirmed_adult",
    isExplicit: classification === "confirmed_adult",
    origin,
    sourceProvider: "test",
    reason: `test:${classification}`,
  };
}

function title(overrides: Partial<NormalizedTitle> & { title: string }): NormalizedTitle {
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

describe("normalizeTitleForMatch / tokenSimilarity", () => {
  it("normalizes case, punctuation and whitespace", () => {
    assert.equal(normalizeTitleForMatch("  The, GHOST!  "), "the ghost");
  });
  it("scores identical titles as 1 and unrelated as low", () => {
    assert.equal(tokenSimilarity("Chainsaw Man", "Chainsaw Man"), 1);
    assert.ok(tokenSimilarity("Chainsaw Man", "Cooking Papa") < 0.3);
  });
});

describe("seriesMatchConfidence / areSameSeries", () => {
  it("merges exact same title across providers with light corroboration", () => {
    const a = title({ title: "Blue Period", provider: "mangadex", publishedAt: "2017" });
    const b = title({ title: "Blue Period", provider: "anilist", publishedAt: "2017" });
    const r = seriesMatchConfidence(a, b);
    assert.ok(r.score >= MATCH_THRESHOLD, `score ${r.score} below threshold`);
    assert.equal(areSameSeries(a, b), true);
  });

  it("merges when an alternative title matches exactly", () => {
    const a = title({ title: "Fireworks", provider: "mangadex" });
    const b = title({ title: "Hana no Chiri Bito", provider: "anilist", alternativeTitles: ["Fireworks"] });
    assert.equal(areSameSeries(a, b), true);
  });

  it("does NOT merge on approximate title similarity ALONE (needs corroboration)", () => {
    // High token overlap but no author/year/category corroboration.
    const a = title({ title: "The Legend of Heroes", provider: "x" });
    const b = title({ title: "Legend of Heroes Saga", provider: "y" });
    const r = seriesMatchConfidence(a, b);
    assert.ok(r.score < MATCH_THRESHOLD, `should NOT merge, score ${r.score}`);
    assert.equal(areSameSeries(a, b), false);
  });

  it("does NOT merge clearly different titles", () => {
    const a = title({ title: "Chainsaw Man", provider: "x" });
    const b = title({ title: "Cooking Mama Recipes", provider: "y" });
    assert.equal(areSameSeries(a, b), false);
  });

  it("disqualifies a merge when known authors conflict", () => {
    const a = title({ title: "Same Title", provider: "x", authors: ["Alice"] });
    const b = title({ title: "Same Title", provider: "y", authors: ["Bob"] });
    const r = seriesMatchConfidence(a, b);
    assert.ok(r.reasons.includes("conflicting authors"));
    assert.ok(r.score < MATCH_THRESHOLD, `conflicting authors must block merge, got ${r.score}`);
    assert.equal(areSameSeries(a, b), false);
  });

  it("strengthens a merge with a shared author", () => {
    const a = title({ title: "Same Title", provider: "x", authors: ["Alice"] });
    const b = title({ title: "Same Title", provider: "y", authors: ["Alice"] });
    const r = seriesMatchConfidence(a, b);
    assert.ok(r.reasons.includes("shared author/artist"));
    assert.equal(areSameSeries(a, b), true);
  });
});

describe("combineAdultSignals", () => {
  const sig = (c: AdultClassification, sp = "p"): AdultContentMetadata => ({
    ...adult(c),
    sourceProvider: sp,
  });

  it("honors explicit adult evidence from any provider", () => {
    const out = combineAdultSignals([sig("general_audience", "a"), sig("confirmed_adult", "b")]);
    assert.equal(out.classification, "confirmed_adult");
    assert.equal(out.isAdult, true);
  });

  it("classifies general only when no adult/mature evidence exists", () => {
    const out = combineAdultSignals([sig("general_audience"), sig("unknown")]);
    assert.equal(out.classification, "general_audience");
    assert.equal(out.isAdult, false);
  });

  it("prefers mature over unknown/general when no explicit adult", () => {
    const out = combineAdultSignals([sig("unknown"), sig("mature_non_explicit")]);
    assert.equal(out.classification, "mature_non_explicit");
  });

  it("returns unknown when nothing is known", () => {
    const out = combineAdultSignals([sig("unknown")]);
    assert.equal(out.classification, "unknown");
    assert.equal(out.isAdult, false);
  });

  it("records the contributing providers for diagnostics", () => {
    const out = combineAdultSignals([sig("confirmed_adult", "mangadex"), sig("unknown", "dynasty")]);
    assert.ok(out.sourceProvider.includes("mangadex"));
    assert.ok(out.sourceProvider.includes("dynasty"));
  });
});

describe("groupIntoCanonicalSeries", () => {
  it("groups two providers' identical titles into ONE canonical series", () => {
    const series = groupIntoCanonicalSeries([
      title({ title: "Shared Work", provider: "mangadex", providerId: "md1", publishedAt: "2020" }),
      title({ title: "Shared Work", provider: "anilist", providerId: "al1", publishedAt: "2020" }),
    ]);
    assert.equal(series.length, 1);
    assert.equal(series[0].providerMappings.length, 2);
    assert.deepEqual(
      series[0].providerMappings.map((m) => m.providerId).sort(),
      ["anilist", "mangadex"],
    );
  });

  it("keeps unmatched titles as separate series (no false merge)", () => {
    const series = groupIntoCanonicalSeries([
      title({ title: "Alpha Story", provider: "mangadex", providerId: "md1", authors: ["A"] }),
      title({ title: "Beta Chronicle", provider: "anilist", providerId: "al1", authors: ["B"] }),
    ]);
    assert.equal(series.length, 2);
  });

  it("excludes general_audience records before they seed a series", () => {
    const series = groupIntoCanonicalSeries([
      title({ title: "Kid Comic", provider: "mangadex", adult: adult("general_audience") }),
    ]);
    assert.equal(series.length, 0);
  });

  it("excludes unknown-classification records (conservative)", () => {
    const series = groupIntoCanonicalSeries([
      title({ title: "Unclassified", provider: "dynasty", adult: adult("unknown") }),
    ]);
    assert.equal(series.length, 0);
  });

  it("includes confirmed_adult and preserves the manga origin", () => {
    const series = groupIntoCanonicalSeries([
      title({
        title: "Adult Manga Work",
        provider: "mangadex",
        category: "manga",
        adult: adult("confirmed_adult", "manga"),
      }),
    ]);
    assert.equal(series.length, 1);
    assert.equal(series[0].isAdult, true);
    assert.equal(series[0].origin, "manga"); // origin separate from age
    assert.equal(series[0].category, "manga");
  });

  it("produces a stable canonical id for the same input", () => {
    const input = () => [
      title({ title: "Stable Id Work", provider: "mangadex", providerId: "md1", publishedAt: "2021" }),
      title({ title: "Stable Id Work", provider: "anilist", providerId: "al1", publishedAt: "2021" }),
    ];
    const a = groupIntoCanonicalSeries(input())[0];
    const b = groupIntoCanonicalSeries(input())[0];
    assert.equal(a.id, b.id);
    assert.equal(a.slug, b.slug);
  });
});
