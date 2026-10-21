"use strict";
// Shared HTTP + resilience layer for provider adapters.
//
// Provides: request timeouts, bounded retries with exponential backoff + jitter,
// in-flight request deduplication, a TTL cache, a per-provider circuit breaker,
// and bounded concurrency. All provider traffic in the app routes through here
// so cross-cutting concerns live in exactly one place.
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rawJson = rawJson;
exports.rawText = rawText;
exports.rawBuffer = rawBuffer;
exports.cacheGet = cacheGet;
exports.cacheSet = cacheSet;
exports.cached = cached;
exports.cacheInvalidate = cacheInvalidate;
exports.dedupe = dedupe;
exports.providerHealthy = providerHealthy;
exports.providerFetch = providerFetch;
const node_https_1 = __importDefault(require("node:https"));
const node_http_1 = __importDefault(require("node:http"));
const types_1 = require("./types");
// A descriptive User-Agent is required by some providers (e.g. MangaDex returns
// HTTP 400 without one) and is good practice for identifying our client.
const DEFAULT_UA = "readhentai-aggregator/1.0 (+https://github.com/readhentai)";
/** Perform an HTTP(S) request and parse JSON, with a hard socket timeout. */
function rawJson(url, opts = {}) {
    const { method = "GET", headers = {}, body, timeoutMs = DEFAULT_TIMEOUT_MS } = opts;
    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (fn) => {
            if (settled)
                return;
            settled = true;
            fn();
        };
        const lib = url.startsWith("http:") ? node_http_1.default : node_https_1.default;
        const req = lib.request(url, {
            method,
            headers: {
                Accept: "application/json",
                "User-Agent": DEFAULT_UA,
                ...headers,
            },
        }, (res) => {
            const chunks = [];
            res.on("data", (c) => chunks.push(c));
            res.on("end", () => {
                const text = Buffer.concat(chunks).toString("utf8");
                const status = res.statusCode ?? 0;
                if (status === 429) {
                    finish(() => reject(new types_1.ProviderError("raw", "rate limited", "rate_limited", true)));
                    return;
                }
                if (status < 200 || status >= 300) {
                    finish(() => reject(new types_1.ProviderError("raw", `HTTP ${status}`, "http", status >= 500)));
                    return;
                }
                try {
                    finish(() => resolve(JSON.parse(text)));
                }
                catch {
                    finish(() => reject(new types_1.ProviderError("raw", "invalid JSON", "parse", false)));
                }
            });
            res.on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
        });
        req.setTimeout(timeoutMs, () => {
            req.destroy();
            finish(() => reject(new types_1.ProviderError("raw", "timeout", "timeout", true)));
        });
        req.on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
        if (body)
            req.write(body);
        req.end();
    });
}
/* ------------------------------------------------------------------ */
/* Raw HTML (for providers that expose no JSON API, only server HTML)  */
/* ------------------------------------------------------------------ */
// Some verified sources (e.g. hentairead.io) publish content only as server-
// rendered HTML with no public JSON API. `rawText` performs the same resilient
// node:https request as `rawJson` but resolves the raw text so the adapter can
// parse markup. It never bypasses any access control — it issues a normal GET
// with a descriptive browser-like User-Agent against a directly-reachable page.
function rawText(url, opts = {}) {
    const { headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS } = opts;
    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (fn) => {
            if (settled)
                return;
            settled = true;
            fn();
        };
        node_https_1.default
            .get(url, {
            headers: {
                Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                ...headers,
            },
        }, (res) => {
            // Follow a single redirect (some listing URLs 301 to a canonical path).
            const status = res.statusCode ?? 0;
            if (status >= 300 && status < 400 && res.headers.location) {
                res.resume();
                const next = new URL(res.headers.location, url).toString();
                finish(() => resolve(rawText(next, opts)));
                return;
            }
            const chunks = [];
            res.on("data", (c) => chunks.push(c));
            res.on("end", () => {
                const text = Buffer.concat(chunks).toString("utf8");
                if (status < 200 || status >= 300) {
                    finish(() => reject(new types_1.ProviderError("raw", `HTTP ${status}`, "http", status >= 500)));
                    return;
                }
                finish(() => resolve(text));
            });
            res.on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
        })
            .on("timeout", function () {
            this.destroy();
            finish(() => reject(new types_1.ProviderError("raw", "timeout", "timeout", true)));
        })
            .on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
    });
}
function rawBuffer(url, opts = {}) {
    const { headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS } = opts;
    return new Promise((resolve, reject) => {
        let settled = false;
        const finish = (fn) => {
            if (settled)
                return;
            settled = true;
            fn();
        };
        node_https_1.default
            .get(url, {
            headers: {
                Accept: "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ...headers,
            },
        }, (res) => {
            const status = res.statusCode ?? 0;
            if (status >= 300 && status < 400 && res.headers.location) {
                res.resume();
                const next = new URL(res.headers.location, url).toString();
                finish(() => resolve(rawBuffer(next, opts)));
                return;
            }
            if (status < 200 || status >= 300) {
                res.resume();
                finish(() => reject(new types_1.ProviderError("raw", `HTTP ${status}`, "http", false)));
                return;
            }
            const chunks = [];
            res.on("data", (c) => chunks.push(c));
            res.on("end", () => finish(() => resolve({
                buffer: Buffer.concat(chunks),
                contentType: res.headers["content-type"] ?? "image/jpeg",
            })));
            res.on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
        })
            .on("timeout", function () {
            this.destroy();
            finish(() => reject(new types_1.ProviderError("raw", "timeout", "timeout", true)));
        })
            .on("error", (e) => finish(() => reject(new types_1.ProviderError("raw", e.message, "network", true))));
    });
}
/* ------------------------------------------------------------------ */
/* Config                                                              */
/* ------------------------------------------------------------------ */
const DEFAULT_TIMEOUT_MS = 10000;
const DEFAULT_RETRIES = 2;
const CIRCUIT_FAILURE_THRESHOLD = 4;
const CIRCUIT_COOLDOWN_MS = 30000;
const MAX_CONCURRENT_PER_PROVIDER = 4;
const cache = new Map();
function cacheGet(key) {
    const entry = cache.get(key);
    if (!entry)
        return undefined;
    if (Date.now() > entry.expiresAt) {
        cache.delete(key);
        return undefined;
    }
    return entry.value;
}
function cacheSet(key, value, ttlMs) {
    // Bound total cache size to avoid unbounded memory growth.
    if (cache.size > 500) {
        const oldest = cache.keys().next().value;
        if (oldest !== undefined)
            cache.delete(oldest);
    }
    cache.set(key, { value, expiresAt: Date.now() + ttlMs });
}
/** Read-through cache: returns cached value or runs fn and caches the result. */
async function cached(key, ttlMs, fn) {
    const hit = cacheGet(key);
    if (hit !== undefined)
        return hit;
    const value = await fn();
    cacheSet(key, value, ttlMs);
    return value;
}
/** Drop every cached entry whose key starts with `prefix`. Returns count. */
function cacheInvalidate(prefix) {
    let n = 0;
    for (const key of [...cache.keys()]) {
        if (key.startsWith(prefix)) {
            cache.delete(key);
            n++;
        }
    }
    return n;
}
/* ------------------------------------------------------------------ */
/* In-flight dedup                                                     */
/* ------------------------------------------------------------------ */
const inflight = new Map();
/** Collapse identical concurrent requests into one shared promise. */
function dedupe(key, fn) {
    const existing = inflight.get(key);
    if (existing)
        return existing;
    const promise = fn().finally(() => inflight.delete(key));
    inflight.set(key, promise);
    return promise;
}
/* ------------------------------------------------------------------ */
/* Bounded concurrency (per provider semaphore)                        */
/* ------------------------------------------------------------------ */
const semaphores = new Map();
async function acquire(providerId) {
    let sem = semaphores.get(providerId);
    if (!sem) {
        sem = { active: 0, queue: [] };
        semaphores.set(providerId, sem);
    }
    if (sem.active < MAX_CONCURRENT_PER_PROVIDER) {
        sem.active++;
        return;
    }
    await new Promise((resolve) => sem.queue.push(resolve));
    sem.active++;
}
function release(providerId) {
    const sem = semaphores.get(providerId);
    if (!sem)
        return;
    sem.active--;
    const next = sem.queue.shift();
    if (next)
        next();
}
const breakers = new Map();
function breakerOpen(providerId) {
    const state = breakers.get(providerId);
    if (!state)
        return false;
    if (state.openUntil && Date.now() < state.openUntil)
        return true;
    if (state.openUntil && Date.now() >= state.openUntil) {
        // Half-open: allow a trial request through.
        state.openUntil = 0;
        state.failures = Math.floor(CIRCUIT_FAILURE_THRESHOLD / 2);
    }
    return false;
}
function breakerRecordFailure(providerId) {
    const state = breakers.get(providerId) ?? { failures: 0, openUntil: 0 };
    state.failures++;
    if (state.failures >= CIRCUIT_FAILURE_THRESHOLD) {
        state.openUntil = Date.now() + CIRCUIT_COOLDOWN_MS;
    }
    breakers.set(providerId, state);
}
function breakerRecordSuccess(providerId) {
    breakers.set(providerId, { failures: 0, openUntil: 0 });
}
/** Exposed for health checks / diagnostics. */
function providerHealthy(providerId) {
    return !breakerOpen(providerId);
}
/* ------------------------------------------------------------------ */
/* Backoff helper                                                      */
/* ------------------------------------------------------------------ */
function backoffDelay(attempt) {
    const base = Math.min(2 ** attempt * 250, 4000);
    return base + Math.random() * 250; // jitter
}
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
/**
 * Resilient JSON GET against a provider. Throws ProviderError with a kind so the
 * aggregator can decide whether to fail over. Uses raw node:https so provider
 * I/O never blocks Next's response stream.
 */
async function providerFetch(url, opts) {
    const { providerId, timeoutMs = DEFAULT_TIMEOUT_MS, retries = DEFAULT_RETRIES } = opts;
    if (!opts.ignoreBreaker && breakerOpen(providerId)) {
        throw new types_1.ProviderError(providerId, "circuit open", "network", false);
    }
    await acquire(providerId);
    try {
        let lastError = new types_1.ProviderError(providerId, "unknown", "network", true);
        for (let attempt = 0; attempt <= retries; attempt++) {
            if (attempt > 0)
                await sleep(backoffDelay(attempt - 1));
            try {
                const data = await rawJson(url, {
                    method: "GET",
                    timeoutMs,
                    headers: { Accept: "application/json", ...(opts.headers ?? {}) },
                });
                breakerRecordSuccess(providerId);
                return data;
            }
            catch (err) {
                // rawJson tags errors with providerId "raw"; rewrap for this provider.
                const kind = err instanceof types_1.ProviderError ? err.kind : "network";
                const retryable = err instanceof types_1.ProviderError ? err.retryable : true;
                lastError = new types_1.ProviderError(providerId, err.message.replace(/^\[raw\]\s*/, ""), kind, retryable);
                if (!retryable)
                    throw lastError;
            }
        }
        breakerRecordFailure(providerId);
        throw lastError;
    }
    finally {
        release(providerId);
    }
}
