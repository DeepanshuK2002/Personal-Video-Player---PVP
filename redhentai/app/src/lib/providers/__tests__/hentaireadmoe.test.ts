import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { hentaireadmoe } from "../hentaireadmoe";
import { getProvider, listProviders } from "../registry";

describe("hentaireadmoe provider capabilities", () => {
  it("declares correct capabilities and info", () => {
    const info = hentaireadmoe.getProviderInfo();
    assert.equal(info.id, "hentaireadmoe");
    assert.equal(info.name, "HentaiRead.moe");
    assert.equal(info.adult, true);
    assert.equal(info.capabilities.search, true);
    assert.equal(info.capabilities.getTitle, true);
    assert.equal(info.capabilities.getChapters, true);
    assert.equal(info.capabilities.getChapterPages, true);
    assert.equal(info.capabilities.trending, true);
    assert.equal(info.capabilities.latestUpdates, true);
  });

  it("is registered in the global registry", () => {
    const provider = getProvider("hentaireadmoe");
    assert.ok(provider);
    assert.equal(provider.getProviderInfo().id, "hentaireadmoe");
    const listed = listProviders().find((p) => p.id === "hentaireadmoe");
    assert.ok(listed);
  });
});
