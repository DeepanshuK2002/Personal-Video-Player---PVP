// Regression tests for the trending interleave — the previous implementation
// infinite-looped for any list of length >= 2 (blocking Node's event loop and
// freezing the whole dev server), and dropped ~2/3 of results. These tests
// would have caught it: a hang fails by timeout, a drop fails by count.
// NO network.

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { interleave } from "../registry";

describe("interleave (trending spread)", () => {
  it("terminates and preserves every item for all sizes (old version hung)", () => {
    for (let n = 0; n <= 20; n++) {
      const input = Array.from({ length: n }, (_, i) => i);
      const out = interleave(input);
      assert.equal(out.length, n, `length changed for n=${n}`);
      // Same multiset — nothing dropped or duplicated.
      assert.deepEqual([...out].sort((a, b) => a - b), input, `items altered for n=${n}`);
    }
  });

  it("returns empty and singletons unchanged", () => {
    assert.deepEqual(interleave([]), []);
    assert.deepEqual(interleave(["only"]), ["only"]);
  });

  it("lifts items from different provider blocks toward the front", () => {
    // Two provider blocks of 3 (as fanOut concatenates them).
    const grouped = ["md0", "md1", "md2", "al0", "al1", "al2"];
    const out = interleave(grouped);
    // Both provider heads should appear near the front, not md block first.
    assert.equal(out[0], "md0");
    assert.ok(out.slice(0, 3).includes("al0"), "second provider head not lifted to front");
    assert.equal(out.length, grouped.length);
  });

  it("is deterministic for the same input", () => {
    const input = Array.from({ length: 12 }, (_, i) => `item${i}`);
    assert.deepEqual(interleave(input), interleave(input));
  });
});
