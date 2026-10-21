"use strict";
// Adult-content classification + eligibility tests — mocked, NO network.
// Covers: confirmed_adult enters, general_audience excluded, unknown handled
// conservatively, mature vs explicit distinct, origin kept separate from age.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const adult_1 = require("../adult");
(0, node_test_1.describe)("classifyMangaDex (provider-native contentRating)", () => {
    (0, node_test_1.it)("maps pornographic -> confirmed_adult", () => {
        const c = (0, adult_1.classifyMangaDex)("pornographic");
        strict_1.default.equal(c.classification, "confirmed_adult");
        strict_1.default.equal(c.isAdult, true);
        strict_1.default.equal(c.isExplicit, true);
    });
    (0, node_test_1.it)("maps erotica/suggestive -> mature_non_explicit (distinct from explicit)", () => {
        strict_1.default.equal((0, adult_1.classifyMangaDex)("erotica").classification, "mature_non_explicit");
        strict_1.default.equal((0, adult_1.classifyMangaDex)("suggestive").classification, "mature_non_explicit");
        strict_1.default.equal((0, adult_1.classifyMangaDex)("erotica").isExplicit, false);
    });
    (0, node_test_1.it)("maps safe -> general_audience", () => {
        const c = (0, adult_1.classifyMangaDex)("safe");
        strict_1.default.equal(c.classification, "general_audience");
        strict_1.default.equal(c.isAdult, false);
    });
    (0, node_test_1.it)("treats a missing rating as unknown (never adult)", () => {
        const c = (0, adult_1.classifyMangaDex)(null);
        strict_1.default.equal(c.classification, "unknown");
        strict_1.default.equal(c.isAdult, false);
    });
});
(0, node_test_1.describe)("classifyAniList", () => {
    (0, node_test_1.it)("isAdult=true -> confirmed_adult", () => {
        strict_1.default.equal((0, adult_1.classifyAniList)(true).classification, "confirmed_adult");
    });
    (0, node_test_1.it)("isAdult=false -> general_audience", () => {
        strict_1.default.equal((0, adult_1.classifyAniList)(false).classification, "general_audience");
    });
    (0, node_test_1.it)("isAdult=undefined -> general_audience (AniList default is SFW)", () => {
        strict_1.default.equal((0, adult_1.classifyAniList)(undefined).classification, "general_audience");
    });
});
(0, node_test_1.describe)("classifyDynasty (conservative)", () => {
    (0, node_test_1.it)("is unknown without a reliable adult tag", () => {
        const c = (0, adult_1.classifyDynasty)(["Yuri", "School life"]);
        strict_1.default.equal(c.classification, "unknown");
        strict_1.default.equal(c.isAdult, false);
    });
    (0, node_test_1.it)("is confirmed_adult when an adult tag is present", () => {
        const c = (0, adult_1.classifyDynasty)(["Yuri", "Hentai"]);
        strict_1.default.equal(c.classification, "confirmed_adult");
    });
});
(0, node_test_1.describe)("inferOrigin (separate from age)", () => {
    (0, node_test_1.it)("infers doujinshi from tags regardless of explicitness", () => {
        strict_1.default.equal((0, adult_1.inferOrigin)({ tags: ["doujinshi"] }), "doujinshi");
    });
    (0, node_test_1.it)("infers manhwa/manhua from country", () => {
        strict_1.default.equal((0, adult_1.inferOrigin)({ countryOfOrigin: "KR" }), "manhwa");
        strict_1.default.equal((0, adult_1.inferOrigin)({ countryOfOrigin: "CN" }), "manhua");
    });
    (0, node_test_1.it)("defaults to manga", () => {
        strict_1.default.equal((0, adult_1.inferOrigin)({}), "manga");
    });
});
(0, node_test_1.describe)("eligibility policy (adult-only catalogue)", () => {
    (0, node_test_1.it)("includes confirmed_adult", () => {
        strict_1.default.equal((0, adult_1.isEligible)("confirmed_adult", adult_1.DEFAULT_ADULT_POLICY), true);
    });
    (0, node_test_1.it)("includes mature_non_explicit under the default mature-allowed policy", () => {
        strict_1.default.equal((0, adult_1.isEligible)("mature_non_explicit", adult_1.DEFAULT_ADULT_POLICY), true);
    });
    (0, node_test_1.it)("EXCLUDES general_audience (never eligible for the adult catalogue)", () => {
        strict_1.default.equal((0, adult_1.isEligible)("general_audience", adult_1.DEFAULT_ADULT_POLICY), false);
    });
    (0, node_test_1.it)("EXCLUDES unknown (conservative until classification verified)", () => {
        strict_1.default.equal((0, adult_1.isEligible)("unknown", adult_1.DEFAULT_ADULT_POLICY), false);
    });
    (0, node_test_1.it)("respects a stricter policy that disallows mature", () => {
        const strict = { ...adult_1.DEFAULT_ADULT_POLICY, allowMature: false };
        strict_1.default.equal((0, adult_1.isEligible)("mature_non_explicit", strict), false);
        strict_1.default.equal((0, adult_1.isEligible)("confirmed_adult", strict), true);
    });
    (0, node_test_1.it)("can allow unknown when explicitly configured", () => {
        const lenient = { ...adult_1.DEFAULT_ADULT_POLICY, allowUnknown: true };
        strict_1.default.equal((0, adult_1.isEligible)("unknown", lenient), true);
    });
});
(0, node_test_1.describe)("mature vs explicit remain distinct", () => {
    const classes = [
        "confirmed_adult",
        "mature_non_explicit",
        "general_audience",
        "unknown",
    ];
    (0, node_test_1.it)("all four classifications are distinct values", () => {
        strict_1.default.equal(new Set(classes).size, 4);
    });
    (0, node_test_1.it)("only confirmed_adult is explicit", () => {
        const md = classes.map((c) => c === "confirmed_adult"
            ? (0, adult_1.classifyMangaDex)("pornographic")
            : c === "mature_non_explicit"
                ? (0, adult_1.classifyMangaDex)("erotica")
                : c === "general_audience"
                    ? (0, adult_1.classifyMangaDex)("safe")
                    : (0, adult_1.classifyMangaDex)(null));
        strict_1.default.deepEqual(md.map((m) => m.isExplicit), [true, false, false, false]);
    });
});
