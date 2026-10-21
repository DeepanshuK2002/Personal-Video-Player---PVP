// GET /api/hentairead-image?url=<encoded> — display-only image proxy.
//
// hentairead.io and hentai18.net (and hentairead's chapter CDN on mgread.io)
// hotlink-protect their images: they return HTTP 403 for any request whose
// Referer is not their own origin. A browser <img> pointing at the real URL from
// our origin therefore never loads. This route fetches the bytes server-side
// with the correct Referer and streams them straight back — a display proxy,
// never a re-host (nothing is stored; bytes are piped through). No access
// control, CAPTCHA, or paywall is bypassed: these images are publicly served to
// any client that simply carries the site's own Referer.
//
// It is deliberately host-allowlisted so it can never be used as an open proxy.
import { rawBuffer } from "@/lib/providers/http";
import { ProviderError } from "@/lib/providers/types";

// Each image host family expects a specific Referer (verified: foreign Referer
// or missing origin -> 403; these -> 200).
const REFERER_BY_SUFFIX: ReadonlyArray<readonly [suffix: string, referer: string]> = [
  ["hentai18.net", "https://hentai18.net/"],
  ["mgread.io", "https://hentairead.io/"],
  ["hentairead.io", "https://hentairead.io/"],
];

function allowedHost(hostname: string): boolean {
  return REFERER_BY_SUFFIX.some(([suffix]) => hostname === suffix || hostname.endsWith(`.${suffix}`));
}

function refererFor(hostname: string): string {
  for (const [suffix, referer] of REFERER_BY_SUFFIX) {
    if (hostname === suffix || hostname.endsWith(`.${suffix}`)) return referer;
  }
  return "https://hentairead.io/";
}

/* ------------------------------------------------------------------ */
/* Burst control                                                       */
/*                                                                     */
/* A results page fires ~20 cover requests at once — every <img> is      */
/* lazy, so they all enter the viewport together on a fast scroll or a  */
/* full-page render. These CDNs throttle concurrent connections from a  */
/* single IP: a 19-way burst measured 2 failures (HTTP 502) while the   */
/* exact same URLs fetched 1.5 s apart all returned 200.                */
/*                                                                     */
/* So cap in-flight upstream fetches and retry the failures with        */
/* backoff + jitter, mirroring the bounded-concurrency/retry policy     */
/* every provider call already goes through.                            */
/* ------------------------------------------------------------------ */

const MAX_IN_FLIGHT = 4;
const MAX_ATTEMPTS = 3;
const BACKOFF_MS = [300, 900] as const;

let inFlight = 0;
const waiting: Array<() => void> = [];

async function acquire(): Promise<void> {
  if (inFlight >= MAX_IN_FLIGHT) {
    await new Promise<void>((resolve) => waiting.push(resolve));
  }
  inFlight += 1;
}

function release(): void {
  inFlight = Math.max(0, inFlight - 1);
  waiting.shift()?.();
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Transient upstream throttling (5xx / 429 / resets) is worth retrying;
 *  a definitive 4xx will never change, so fail straight through. */
function retryableImageError(err: unknown): boolean {
  if (!(err instanceof ProviderError)) return true;
  const status = /HTTP (\d{3})/.exec(err.message);
  if (status) {
    const code = Number(status[1]);
    return code >= 500 || code === 429;
  }
  return err.retryable;
}

async function fetchImage(url: string, referer: string) {
  let lastError: unknown = undefined;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (attempt > 0) {
      // Back off before the next try so the CDN stops seeing a hot burst.
      await sleep(BACKOFF_MS[attempt - 1] + Math.floor(Math.random() * 200));
    }
    await acquire();
    try {
      return await rawBuffer(url, { headers: { Referer: referer }, timeoutMs: 15_000 });
    } catch (err) {
      lastError = err;
      if (!retryableImageError(err)) throw err;
    } finally {
      release(); // release while backing off so other covers can proceed
    }
  }
  throw lastError;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const raw = searchParams.get("url");
  if (!raw) return new Response("Missing url", { status: 400 });

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    return new Response("Invalid url", { status: 400 });
  }
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return new Response("Invalid protocol", { status: 400 });
  }
  if (!allowedHost(parsed.hostname)) {
    return new Response("Host not allowed", { status: 403 });
  }

  try {
    const { buffer, contentType } = await fetchImage(parsed.toString(), refererFor(parsed.hostname));
    return new Response(new Uint8Array(buffer), {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400, s-maxage=86400",
      },
    });
  } catch {
    return new Response("Image unavailable", { status: 502 });
  }
}
