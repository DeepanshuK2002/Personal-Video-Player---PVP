// Adult-content classification + eligibility tests — mocked, NO network.
// Covers: confirmed_adult enters, general_audience excluded, unknown handled
// conservatively, mature vs explicit distinct, origin kept separate from age.

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  classifyMangaDex,
  classifyAniList,
  classifyDynasty,
  inferOrigin,
  isEligible,
  DEFAULT_ADULT_POLICY,
  type AdultClassification,
} from "../adult";

describe("classifyMangaDex (provider-native contentRating)", () => {
  it("maps pornographic -> confirmed_adult", () => {
    const c = classifyMangaDex("pornographic");
    assert.equal(c.classification, "confirmed_adult");
    assert.equal(c.isAdult, true);
    assert.equal(c.isExplicit, true);
  });

  it("maps erotica/suggestive -> mature_non_explicit (distinct from explicit)", () => {
    assert.equal(classifyMangaDex("erotica").classification, "mature_non_explicit");
    assert.equal(classifyMangaDex("suggestive").classification, "mature_non_explicit");
    assert.equal(classifyMangaDex("erotica").isExplicit, false);
  });

  it("maps safe -> general_audience", () => {
    const c = classifyMangaDex("safe");
    assert.equal(c.classification, "general_audience");
    assert.equal(c.isAdult, false);
  });

  it("treats a missing rating as unknown (never adult)", () => {
    const c = classifyMangaDex(null);
    assert.equal(c.classification, "unknown");
    assert.equal(c.isAdult, false);
  });
});

describe("classifyAniList", () => {
  it("isAdult=true -> confirmed_adult", () => {
    assert.equal(classifyAniList(true).classification, "confirmed_adult");
  });
  it("isAdult=false -> general_audience", () => {
    assert.equal(classifyAniList(false).classification, "general_audience");
  });
  it("isAdult=undefined -> general_audience (AniList default is SFW)", () => {
    assert.equal(classifyAniList(undefined).classification, "general_audience");
  });
});

describe("classifyDynasty (conservative)", () => {
  it("is unknown without a reliable adult tag", () => {
    const c = classifyDynasty(["Yuri", "School life"]);
    assert.equal(c.classification, "unknown");
    assert.equal(c.isAdult, false);
  });
  it("is confirmed_adult when an adult tag is present", () => {
    const c = classifyDynasty(["Yuri", "Hentai"]);
    assert.equal(c.classification, "confirmed_adult");
  });
});

describe("inferOrigin (separate from age)", () => {
  it("infers doujinshi from tags regardless of explicitness", () => {
    assert.equal(inferOrigin({ tags: ["doujinshi"] }), "doujinshi");
  });
  it("infers manhwa/manhua from country", () => {
    assert.equal(inferOrigin({ countryOfOrigin: "KR" }), "manhwa");
    assert.equal(inferOrigin({ countryOfOrigin: "CN" }), "manhua");
  });
  it("defaults to manga", () => {
    assert.equal(inferOrigin({}), "manga");
  });
});

describe("eligibility policy (adult-only catalogue)", () => {
  it("includes confirmed_adult", () => {
    assert.equal(isEligible("confirmed_adult", DEFAULT_ADULT_POLICY), true);
  });

  it("includes mature_non_explicit under the default mature-allowed policy", () => {
    assert.equal(isEligible("mature_non_explicit", DEFAULT_ADULT_POLICY), true);
  });

  it("EXCLUDES general_audience (never eligible for the adult catalogue)", () => {
    assert.equal(isEligible("general_audience", DEFAULT_ADULT_POLICY), false);
  });

  it("EXCLUDES unknown (conservative until classification verified)", () => {
    assert.equal(isEligible("unknown", DEFAULT_ADULT_POLICY), false);
  });

  it("respects a stricter policy that disallows mature", () => {
    const strict = { ...DEFAULT_ADULT_POLICY, allowMature: false };
    assert.equal(isEligible("mature_non_explicit", strict), false);
    assert.equal(isEligible("confirmed_adult", strict), true);
  });

  it("can allow unknown when explicitly configured", () => {
    const lenient = { ...DEFAULT_ADULT_POLICY, allowUnknown: true };
    assert.equal(isEligible("unknown", lenient), true);
  });
});

describe("mature vs explicit remain distinct", () => {
  const classes: AdultClassification[] = [
    "confirmed_adult",
    "mature_non_explicit",
    "general_audience",
    "unknown",
  ];
  it("all four classifications are distinct values", () => {
    assert.equal(new Set(classes).size, 4);
  });
  it("only confirmed_adult is explicit", () => {
    const md = classes.map((c) =>
      c === "confirmed_adult"
        ? classifyMangaDex("pornographic")
        : c === "mature_non_explicit"
          ? classifyMangaDex("erotica")
          : c === "general_audience"
            ? classifyMangaDex("safe")
            : classifyMangaDex(null),
    );
    assert.deepEqual(
      md.map((m) => m.isExplicit),
      [true, false, false, false],
    );
  });
});
