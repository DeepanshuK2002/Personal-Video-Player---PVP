import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { classifyEnma, isEligible, DEFAULT_ADULT_POLICY } from "../adult";
import {
  chapterRef,
  enma,
  languageCode,
  languageLabel,
  originFromCategories,
  parseChapterRef,
  sortForOrder,
} from "../enma";
import { getProvider, listProviders } from "../registry";

describe("classifyEnma", () => {
  it("classifies the nhentai source as confirmed adult, doujinshi origin", () => {
    const c = classifyEnma("nhentai", "doujinshi");
    assert.equal(c.classification, "confirmed_adult");
    assert.equal(c.isAdult, true);
    assert.equal(c.isExplicit, true);
    assert.equal(c.origin, "doujinshi");
    assert.equal(c.sourceProvider, "enma");
    assert.equal(isEligible(c.classification, DEFAULT_ADULT_POLICY), true);
  });

  it("keeps other Enma sources at unknown (never promoted to adult)", () => {
    const c = classifyEnma("mangadex");
    assert.equal(c.classification, "unknown");
    assert.equal(c.isAdult, false);
    assert.equal(isEligible(c.classification, DEFAULT_ADULT_POLICY), false);
  });

  it("treats a missing sidecar source as unknown", () => {
    for (const raw of [null, undefined, ""]) {
      const c = classifyEnma(raw);
      assert.equal(c.classification, "unknown");
      assert.equal(isEligible(c.classification, DEFAULT_ADULT_POLICY), false);
    }
  });
});

describe("enma provider capabilities", () => {
  it("declares correct capabilities and info", () => {
    const info = enma.getProviderInfo();
    assert.equal(info.id, "enma");
    assert.equal(info.name, "Enma (nhentai)");
    assert.equal(info.adult, true);
    assert.equal(info.status, "SELF_HOST_REQUIRED");
    assert.equal(info.capabilities.search, true);
    assert.equal(info.capabilities.getTitle, true);
    assert.equal(info.capabilities.getChapters, true);
    assert.equal(info.capabilities.getChapterPages, true);
    assert.equal(info.capabilities.trending, true);
    // No dates at listing level / no rating signal — surfaced, not faked.
    assert.equal(info.capabilities.latestUpdates, false);
    assert.equal(info.capabilities.ratings, false);
    assert.equal(enma.getLatestUpdates, undefined);
  });

  it("uses a hyphen-free provider id (slug contract)", () => {
    const info = enma.getProviderInfo();
    assert.equal(info.id.includes("-"), false);
    // And the reserved prefix stripping used by getTitle/getChapters works.
    assert.equal(info.id.replace(/^enma-/, ""), "enma");
  });

  it("is registered in the global registry", () => {
    const provider = getProvider("enma");
    assert.ok(provider);
    assert.equal(provider.getProviderInfo().id, "enma");
    const listed = listProviders().find((p) => p.id === "enma");
    assert.ok(listed);
  });
});

describe("chapter id encoding", () => {
  it("round-trips title id + index (registry passes chapter id for both args)", () => {
    const ref = chapterRef("688749", 0);
    assert.equal(ref, "688749__0");
    assert.deepEqual(parseChapterRef(ref), { titleId: "688749", index: 0 });

    const multi = chapterRef("688749", 12);
    assert.deepEqual(parseChapterRef(multi), { titleId: "688749", index: 12 });
  });

  it("keeps embedded separators in the title id (split on last marker only)", () => {
    assert.deepEqual(parseChapterRef("abc__def__3"), { titleId: "abc__def", index: 3 });
  });

  it("accepts the namespaced NormalizedChapter.id form (`enma:<ref>`)", () => {
    // getChapters returns id: `enma:688749__0`; callers that pass chapter.id
    // (instead of providerChapterId) must still resolve — the sidecar rejects
    // a title id carrying the `enma:` prefix with HTTP 400.
    assert.deepEqual(parseChapterRef("enma:688749__0"), { titleId: "688749", index: 0 });
    assert.deepEqual(parseChapterRef("enma:688749__12"), { titleId: "688749", index: 12 });
    assert.equal(parseChapterRef("enma:"), null);
    assert.equal(parseChapterRef("enma:688749__"), null);
  });

  it("rejects malformed references", () => {
    for (const bad of ["", "__", "__1", "688749__", "688749__x", "688749__-1", "688749__1.5"]) {
      assert.equal(parseChapterRef(bad), null, `expected null for ${JSON.stringify(bad)}`);
    }
  });
});

describe("search sort mapping", () => {
  it("maps app orders onto the API v2 sort enum, never inventing ranks", () => {
    assert.equal(sortForOrder("popular"), "popular");
    assert.equal(sortForOrder("latest"), "date");
    assert.equal(sortForOrder("relevance"), undefined); // v2 has no relevance rank
    assert.equal(sortForOrder("rating"), undefined); // v2 exposes no ratings
    assert.equal(sortForOrder(undefined), undefined);
  });
});

describe("language + origin helpers", () => {
  it("maps language tags to codes and display labels", () => {
    assert.equal(languageCode("japanese"), "ja");
    assert.equal(languageCode("english"), "en");
    assert.equal(languageCode(null), null);
    assert.equal(languageCode("klingon"), null);
    assert.equal(languageLabel("japanese"), "Japanese");
    assert.equal(languageLabel(null), null);
  });

  it("derives the origin axis from nhentai category tags", () => {
    assert.equal(originFromCategories(["doujinshi"]), "doujinshi");
    assert.equal(originFromCategories(["manga"]), "manga");
    assert.equal(originFromCategories(["manhwa"]), "manhwa");
    assert.equal(originFromCategories(["Manga"]), "manga");
    assert.equal(originFromCategories([]), "doujinshi");
    // A doujinshi category wins over a generic manga one.
    assert.equal(originFromCategories(["manga", "doujinshi"]), "doujinshi");
  });
});
