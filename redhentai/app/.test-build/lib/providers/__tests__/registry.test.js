"use strict";
// Regression tests for the trending interleave — the previous implementation
// infinite-looped for any list of length >= 2 (blocking Node's event loop and
// freezing the whole dev server), and dropped ~2/3 of results. These tests
// would have caught it: a hang fails by timeout, a drop fails by count.
// NO network.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const node_test_1 = require("node:test");
const strict_1 = __importDefault(require("node:assert/strict"));
const registry_1 = require("../registry");
(0, node_test_1.describe)("interleave (trending spread)", () => {
    (0, node_test_1.it)("terminates and preserves every item for all sizes (old version hung)", () => {
        for (let n = 0; n <= 20; n++) {
            const input = Array.from({ length: n }, (_, i) => i);
            const out = (0, registry_1.interleave)(input);
            strict_1.default.equal(out.length, n, `length changed for n=${n}`);
            // Same multiset — nothing dropped or duplicated.
            strict_1.default.deepEqual([...out].sort((a, b) => a - b), input, `items altered for n=${n}`);
        }
    });
    (0, node_test_1.it)("returns empty and singletons unchanged", () => {
        strict_1.default.deepEqual((0, registry_1.interleave)([]), []);
        strict_1.default.deepEqual((0, registry_1.interleave)(["only"]), ["only"]);
    });
    (0, node_test_1.it)("lifts items from different provider blocks toward the front", () => {
        // Two provider blocks of 3 (as fanOut concatenates them).
        const grouped = ["md0", "md1", "md2", "al0", "al1", "al2"];
        const out = (0, registry_1.interleave)(grouped);
        // Both provider heads should appear near the front, not md block first.
        strict_1.default.equal(out[0], "md0");
        strict_1.default.ok(out.slice(0, 3).includes("al0"), "second provider head not lifted to front");
        strict_1.default.equal(out.length, grouped.length);
    });
    (0, node_test_1.it)("is deterministic for the same input", () => {
        const input = Array.from({ length: 12 }, (_, i) => `item${i}`);
        strict_1.default.deepEqual((0, registry_1.interleave)(input), (0, registry_1.interleave)(input));
    });
});
