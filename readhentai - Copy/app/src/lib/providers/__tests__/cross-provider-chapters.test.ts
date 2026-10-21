// Cross-provider chapter fallback tests — mocked, NO network.
// Covers: exact-title/alt-title match supplies chapters (metadata-only
// profiles like AniList get a readable collection), no-match safety (a wrong
// series never leaks in), own-provider exclusion, failover past a candidate
// whose search or chapter list fails, and the `readable` flag reflecting the
// SERVING provider's capability.

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { findChaptersByTitleMatch } from "../registry";
import type { AdultClassification, AdultContentMetadata, ContentOrigin } from "../adult";
import type { ContentProvider, NormalizedChapter, NormalizedTitle } from "../types";

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

function chapter(provider: string, titleId: string, n: number): NormalizedChapter {
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

interface FakeOpts {
  id: string;
  search?: (query: string) => Promise<NormalizedTitle[]>;
  chapters?: (providerId: string) => Promise<NormalizedChapter[]>;
  /** Serves readable page images (getChapterPages capability). */
  pages?: boolean;
}

function fakeProvider(opts: FakeOpts): ContentProvider {
  return {
    getProviderInfo: () => ({
      id: opts.id,
      name: opts.id,
      baseUrl: "https://example.test",
      status: "VERIFIED_AND_AVAILABLE" as const,
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

describe("findChaptersByTitleMatch", () => {
  it("supplies chapters from a source whose title matches exactly", async () => {
    const source = fakeProvider({
      id: "hentai18",
      search: async (q) => (q === "Secret Class" ? [sourceHit] : []),
      chapters: async (providerId) => {
        assert.equal(providerId, "secret-class");
        return [
          chapter("hentai18", "hentai18:secret-class", 1),
          chapter("hentai18", "hentai18:secret-class", 2),
        ];
      },
      pages: true,
    });

    const out = await findChaptersByTitleMatch(target, "en", [source]);
    assert.equal(out.length, 2);
    assert.ok(out.every((c) => c.provider === "hentai18"));
    assert.ok(out.every((c) => c.readable === true), "pages-capable source → readable");
    assert.ok(out.every((c) => c.titleId === "hentai18:secret-class"));
  });

  it("matches when the identity only appears as an alternative title", async () => {
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

    const out = await findChaptersByTitleMatch(target, "en", [source]);
    assert.equal(out.length, 1);
    assert.equal(out[0].provider, "hentaireadmoe");
    assert.equal(out[0].readable, false, "source without page capability → not readable");
  });

  it("never returns chapters of a different series", async () => {
    const wrong = title({ title: "Cooking Mama Recipes", provider: "hentai18" });
    const source = fakeProvider({
      id: "hentai18",
      search: async () => [wrong],
      chapters: async () => [chapter("hentai18", "hentai18:cooking-mama", 1)],
    });

    const out = await findChaptersByTitleMatch(target, "en", [source]);
    assert.deepEqual(out, []);
  });

  it("does not merge on approximate title similarity alone", async () => {
    // High token overlap, no corroborating metadata → below threshold.
    const near = title({ title: "The Secret Classes", provider: "hentai18" });
    const source = fakeProvider({
      id: "hentai18",
      search: async () => [near],
      chapters: async () => [chapter("hentai18", "hentai18:the-secret-classes", 1)],
    });

    const out = await findChaptersByTitleMatch(target, "en", [source]);
    assert.deepEqual(out, []);
  });

  it("excludes the title's own provider even when it would match", async () => {
    const own = fakeProvider({
      id: "anilist",
      search: async () => [sourceHit],
      chapters: async () => [chapter("anilist", "anilist:119913", 1)],
    });

    const out = await findChaptersByTitleMatch(target, "en", [own]);
    assert.deepEqual(out, [], "own provider already failed by id — must not be retried by search");
  });

  it("falls through to the next source when the matched one cannot list chapters", async () => {
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

    const out = await findChaptersByTitleMatch(target, "en", [broken, working]);
    assert.equal(out.length, 1);
    assert.equal(out[0].provider, "hentaireadmoe");
  });

  it("falls through when a candidate's search endpoint is dead", async () => {
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

    const out = await findChaptersByTitleMatch(target, "en", [dead, working]);
    assert.equal(out.length, 1);
    assert.equal(out[0].provider, "hentai18");
  });

  it("returns [] when no candidate supports search or chapters", async () => {
    const metadataOnly = fakeProvider({ id: "anilist" });
    const out = await findChaptersByTitleMatch(target, "en", [metadataOnly]);
    assert.deepEqual(out, []);
  });
});
