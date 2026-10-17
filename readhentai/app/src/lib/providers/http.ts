// Shared HTTP + resilience layer for provider adapters.
//
// Provides: request timeouts, bounded retries with exponential backoff + jitter,
// in-flight request deduplication, a TTL cache, a per-provider circuit breaker,
// and bounded concurrency. All provider traffic in the app routes through here
// so cross-cutting concerns live in exactly one place.

import https from "node:https";
import http from "node:http";
import { ProviderError } from "./types";

/* ------------------------------------------------------------------ */
/* Raw HTTP (bypasses Next's patched fetch)                            */
/* ------------------------------------------------------------------ */
// Provider calls deliberately avoid the global `fetch` that Next.js patches in
// route handlers: the patch registers every request as "pending dynamic data",
// so a slow/hung upstream (e.g. AniList POST) would block the whole response
// stream from flushing. Raw node:https keeps provider I/O fully decoupled from
// Next's caching/PPR machinery and gives us precise timeouts.

export interface RawJsonOptions {
  method?: "GET" | "POST";
  headers?: Record<string, string>;
  body?: string;
  timeoutMs?: number;
}

// A descriptive User-Agent is required by some providers (e.g. MangaDex returns
// HTTP 400 without one) and is good practice for identifying our client.
const DEFAULT_UA = "readhentai-aggregator/1.0 (+https://github.com/readhentai)";

/** Perform an HTTP(S) request and parse JSON, with a hard socket timeout. */
export function rawJson<T>(url: string, opts: RawJsonOptions = {}): Promise<T> {
  const { method = "GET", headers = {}, body, timeoutMs = DEFAULT_TIMEOUT_MS } = opts;

  return new Promise<T>((resolve, reject) => {
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      fn();
    };

    const lib = url.startsWith("http:") ? http : https;
    const req = lib.request(
      url,
      {
        method,
        headers: {
          Accept: "application/json",
          "User-Agent": DEFAULT_UA,
          ...headers,
        },
      },
      (res: import("node:http").IncomingMessage) => {
        const chunks: Buffer[] = [];
        res.on("data", (c: Buffer) => chunks.push(c));
        res.on("end", () => {
          const text = Buffer.concat(chunks).toString("utf8");
          const status = res.statusCode ?? 0;
          if (status === 429) {
            finish(() => reject(new ProviderError("raw", "rate limited", "rate_limited", true)));
            return;
          }
          if (status < 200 || status >= 300) {
            finish(() => reject(new ProviderError("raw", `HTTP ${status}`, "http", status >= 500)));
            return;
          }
          try {
            finish(() => resolve(JSON.parse(text) as T));
          } catch {
            finish(() => reject(new ProviderError("raw", "invalid JSON", "parse", false)));
          }
        });
        res.on("error", (e) => finish(() => reject(new ProviderError("raw", e.message, "network", true))));
      },
    );

    req.setTimeout(timeoutMs, () => {
      req.destroy();
      finish(() => reject(new ProviderError("raw", "timeout", "timeout", true)));
    });
    req.on("error", (e) => finish(() => reject(new ProviderError("raw", e.message, "network", true))));

    if (body) req.write(body);
    req.end();
  });
}

/* ------------------------------------------------------------------ */
/* Config                                                              */
/* ------------------------------------------------------------------ */

const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_RETRIES = 2;
const CIRCUIT_FAILURE_THRESHOLD = 4;
const CIRCUIT_COOLDOWN_MS = 30_000;
const MAX_CONCURRENT_PER_PROVIDER = 4;

/* ------------------------------------------------------------------ */
/* TTL cache                                                           */
/* ------------------------------------------------------------------ */

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const cache = new Map<string, CacheEntry<unknown>>();

export function cacheGet<T>(key: string): T | undefined {
  const entry = cache.get(key);
  if (!entry) return undefined;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return undefined;
  }
  return entry.value as T;
}

export function cacheSet<T>(key: string, value: T, ttlMs: number): void {
  // Bound total cache size to avoid unbounded memory growth.
  if (cache.size > 500) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(key, { value, expiresAt: Date.now() + ttlMs });
}

/** Read-through cache: returns cached value or runs fn and caches the result. */
export async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = cacheGet<T>(key);
  if (hit !== undefined) return hit;
  const value = await fn();
  cacheSet(key, value, ttlMs);
  return value;
}

/* ------------------------------------------------------------------ */
/* In-flight dedup                                                     */
/* ------------------------------------------------------------------ */

const inflight = new Map<string, Promise<unknown>>();

/** Collapse identical concurrent requests into one shared promise. */
export function dedupe<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inflight.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  const promise = fn().finally(() => inflight.delete(key));
  inflight.set(key, promise as Promise<unknown>);
  return promise;
}

/* ------------------------------------------------------------------ */
/* Bounded concurrency (per provider semaphore)                        */
/* ------------------------------------------------------------------ */

const semaphores = new Map<string, { active: number; queue: Array<() => void> }>();

async function acquire(providerId: string): Promise<void> {
  let sem = semaphores.get(providerId);
  if (!sem) {
    sem = { active: 0, queue: [] };
    semaphores.set(providerId, sem);
  }
  if (sem.active < MAX_CONCURRENT_PER_PROVIDER) {
    sem.active++;
    return;
  }
  await new Promise<void>((resolve) => sem!.queue.push(resolve));
  sem.active++;
}

function release(providerId: string): void {
  const sem = semaphores.get(providerId);
  if (!sem) return;
  sem.active--;
  const next = sem.queue.shift();
  if (next) next();
}

/* ------------------------------------------------------------------ */
/* Circuit breaker                                                     */
/* ------------------------------------------------------------------ */

interface BreakerState {
  failures: number;
  openUntil: number;
}

const breakers = new Map<string, BreakerState>();

function breakerOpen(providerId: string): boolean {
  const state = breakers.get(providerId);
  if (!state) return false;
  if (state.openUntil && Date.now() < state.openUntil) return true;
  if (state.openUntil && Date.now() >= state.openUntil) {
    // Half-open: allow a trial request through.
    state.openUntil = 0;
    state.failures = Math.floor(CIRCUIT_FAILURE_THRESHOLD / 2);
  }
  return false;
}

function breakerRecordFailure(providerId: string): void {
  const state = breakers.get(providerId) ?? { failures: 0, openUntil: 0 };
  state.failures++;
  if (state.failures >= CIRCUIT_FAILURE_THRESHOLD) {
    state.openUntil = Date.now() + CIRCUIT_COOLDOWN_MS;
  }
  breakers.set(providerId, state);
}

function breakerRecordSuccess(providerId: string): void {
  breakers.set(providerId, { failures: 0, openUntil: 0 });
}

/** Exposed for health checks / diagnostics. */
export function providerHealthy(providerId: string): boolean {
  return !breakerOpen(providerId);
}

/* ------------------------------------------------------------------ */
/* Backoff helper                                                      */
/* ------------------------------------------------------------------ */

function backoffDelay(attempt: number): number {
  const base = Math.min(2 ** attempt * 250, 4000);
  return base + Math.random() * 250; // jitter
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/* ------------------------------------------------------------------ */
/* Main fetch                                                          */
/* ------------------------------------------------------------------ */

export interface ProviderFetchOptions {
  providerId: string;
  timeoutMs?: number;
  retries?: number;
  headers?: Record<string, string>;
  /** Force bypass of the circuit breaker (used for explicit health probes). */
  ignoreBreaker?: boolean;
}

/**
 * Resilient JSON GET against a provider. Throws ProviderError with a kind so the
 * aggregator can decide whether to fail over. Uses raw node:https so provider
 * I/O never blocks Next's response stream.
 */
export async function providerFetch<T>(
  url: string,
  opts: ProviderFetchOptions,
): Promise<T> {
  const { providerId, timeoutMs = DEFAULT_TIMEOUT_MS, retries = DEFAULT_RETRIES } = opts;

  if (!opts.ignoreBreaker && breakerOpen(providerId)) {
    throw new ProviderError(providerId, "circuit open", "network", false);
  }

  await acquire(providerId);
  try {
    let lastError: ProviderError = new ProviderError(providerId, "unknown", "network", true);

    for (let attempt = 0; attempt <= retries; attempt++) {
      if (attempt > 0) await sleep(backoffDelay(attempt - 1));
      try {
        const data = await rawJson<T>(url, {
          method: "GET",
          timeoutMs,
          headers: { Accept: "application/json", ...(opts.headers ?? {}) },
        });
        breakerRecordSuccess(providerId);
        return data;
      } catch (err) {
        // rawJson tags errors with providerId "raw"; rewrap for this provider.
        const kind = err instanceof ProviderError ? err.kind : "network";
        const retryable = err instanceof ProviderError ? err.retryable : true;
        lastError = new ProviderError(
          providerId,
          (err as Error).message.replace(/^\[raw\]\s*/, ""),
          kind,
          retryable,
        );
        if (!retryable) throw lastError;
      }
    }

    breakerRecordFailure(providerId);
    throw lastError;
  } finally {
    release(providerId);
  }
}
