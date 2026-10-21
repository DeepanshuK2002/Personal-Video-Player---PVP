"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const adult_1 = require("../adult");
const hentai18_1 = require("../hentai18");
const registry_1 = require("../registry");
(0, node_test_1.describe)("classifyHentai18", () => {
    (0, node_test_1.it)("always classifies as confirmed_adult and explicit", () => {
        const c = (0, adult_1.classifyHentai18)("manhwa");
        strict_1.default.equal(c.classification, "confirmed_adult");
        strict_1.default.equal(c.isAdult, true);
        strict_1.default.equal(c.isExplicit, true);
        strict_1.default.equal(c.origin, "manhwa");
    });
    (0, node_test_1.it)("passes default adult eligibility filter", () => {
        const c = (0, adult_1.classifyHentai18)("manga");
        strict_1.default.equal((0, adult_1.isEligible)(c.classification, adult_1.DEFAULT_ADULT_POLICY), true);
    });
});
(0, node_test_1.describe)("hentai18 provider capabilities", () => {
    (0, node_test_1.it)("declares correct capabilities and info", () => {
        const info = hentai18_1.hentai18.getProviderInfo();
        strict_1.default.equal(info.id, "hentai18");
        strict_1.default.equal(info.name, "Hentai18");
        strict_1.default.equal(info.adult, true);
        strict_1.default.equal(info.capabilities.search, true);
        strict_1.default.equal(info.capabilities.getTitle, true);
        strict_1.default.equal(info.capabilities.getChapters, true);
        strict_1.default.equal(info.capabilities.getChapterPages, true);
        strict_1.default.equal(info.capabilities.trending, true);
        strict_1.default.equal(info.capabilities.latestUpdates, true);
    });
    (0, node_test_1.it)("is registered in the global registry", () => {
        const provider = (0, registry_1.getProvider)("hentai18");
        strict_1.default.ok(provider);
        strict_1.default.equal(provider.getProviderInfo().id, "hentai18");
        const listed = (0, registry_1.listProviders)().find((p) => p.id === "hentai18");
        strict_1.default.ok(listed);
    });
});
