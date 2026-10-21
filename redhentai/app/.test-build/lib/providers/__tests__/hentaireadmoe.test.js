"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const hentaireadmoe_1 = require("../hentaireadmoe");
const registry_1 = require("../registry");
(0, node_test_1.describe)("hentaireadmoe provider capabilities", () => {
    (0, node_test_1.it)("declares correct capabilities and info", () => {
        const info = hentaireadmoe_1.hentaireadmoe.getProviderInfo();
        strict_1.default.equal(info.id, "hentaireadmoe");
        strict_1.default.equal(info.name, "HentaiRead.moe");
        strict_1.default.equal(info.adult, true);
        strict_1.default.equal(info.capabilities.search, true);
        strict_1.default.equal(info.capabilities.getTitle, true);
        strict_1.default.equal(info.capabilities.getChapters, true);
        strict_1.default.equal(info.capabilities.getChapterPages, true);
        strict_1.default.equal(info.capabilities.trending, true);
        strict_1.default.equal(info.capabilities.latestUpdates, true);
    });
    (0, node_test_1.it)("is registered in the global registry", () => {
        const provider = (0, registry_1.getProvider)("hentaireadmoe");
        strict_1.default.ok(provider);
        strict_1.default.equal(provider.getProviderInfo().id, "hentaireadmoe");
        const listed = (0, registry_1.listProviders)().find((p) => p.id === "hentaireadmoe");
        strict_1.default.ok(listed);
    });
});
