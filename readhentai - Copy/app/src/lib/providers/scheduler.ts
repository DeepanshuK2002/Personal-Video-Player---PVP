// Background trending refresher.
//
// Keeps the hentairead trending cache warm and current. The listing/detail caches
// carry a 6-hour TTL (see hentairead.ts); this refresher force-invalidates them
// and re-fetches on the same 6-hour cadence so the page reflects upstream updates
// even when nobody is actively browsing. The loop is started once from
// instrumentation.ts when the server boots.

import { cacheInvalidate } from "./http";
import { hentairead } from "./hentairead";

const REFRESH_INTERVAL_MS = 6 * 60 * 60 * 1000; // 6 hours
const CACHE_PREFIX = "hentairead:";

let timer: ReturnType<typeof setInterval> | null = null;

/** Force-refresh the hentairead caches (all categories) right now. */
export async function refreshTrendingNow(): Promise<void> {
  cacheInvalidate(CACHE_PREFIX);
  try {
    // Warm the global + per-category feeds so every content filter is served fresh.
    await hentairead.getTrending?.({ limit: 40 });
    await hentairead.getTrending?.({ limit: 40, categories: ["manhwa"] });
    await hentairead.getTrending?.({ limit: 40, categories: ["manhua"] });
    console.log(`[scheduler] hentairead trending refreshed at ${new Date().toISOString()}`);
  } catch (err) {
    // Never crash the server over a refresh — the next tick retries.
    console.warn(`[scheduler] hentairead refresh failed: ${(err as Error).message}`);
  }
}

/** Start the 6-hour refresh loop. Idempotent — safe to call repeatedly. */
export function startTrendingRefresher(): void {
  if (timer) return;
  // Immediate (non-blocking) warm so the first page view is served from cache.
  void refreshTrendingNow();
  timer = setInterval(() => void refreshTrendingNow(), REFRESH_INTERVAL_MS);
  // Don't hold the process open purely for the timer (clean dev/prod shutdown).
  (timer as unknown as { unref?: () => void })?.unref?.();
}

/** Stop the loop (used by tests / graceful shutdown). */
export function stopTrendingRefresher(): void {
  if (timer) clearInterval(timer);
  timer = null;
}
