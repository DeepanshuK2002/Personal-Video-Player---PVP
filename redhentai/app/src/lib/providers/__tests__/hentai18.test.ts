import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { classifyHentai18, isEligible, DEFAULT_ADULT_POLICY } from "../adult";
import { hentai18 } from "../hentai18";
import { getProvider, listProviders } from "../registry";

describe("classifyHentai18", () => {
  it("always classifies as confirmed_adult and explicit", () => {
    const c = classifyHentai18("manhwa");
    assert.equal(c.classification, "confirmed_adult");
    assert.equal(c.isAdult, true);
    assert.equal(c.isExplicit, true);
    assert.equal(c.origin, "manhwa");
  });

  it("passes default adult eligibility filter", () => {
    const c = classifyHentai18("manga");
    assert.equal(isEligible(c.classification, DEFAULT_ADULT_POLICY), true);
  });
});

describe("hentai18 provider capabilities", () => {
  it("declares correct capabilities and info", () => {
    const info = hentai18.getProviderInfo();
    assert.equal(info.id, "hentai18");
    assert.equal(info.name, "Hentai18");
    assert.equal(info.adult, true);
    assert.equal(info.capabilities.search, true);
    assert.equal(info.capabilities.getTitle, true);
    assert.equal(info.capabilities.getChapters, true);
    assert.equal(info.capabilities.getChapterPages, true);
    assert.equal(info.capabilities.trending, true);
    assert.equal(info.capabilities.latestUpdates, true);
  });

  it("is registered in the global registry", () => {
    const provider = getProvider("hentai18");
    assert.ok(provider);
    assert.equal(provider.getProviderInfo().id, "hentai18");
    const listed = listProviders().find((p) => p.id === "hentai18");
    assert.ok(listed);
  });
});
