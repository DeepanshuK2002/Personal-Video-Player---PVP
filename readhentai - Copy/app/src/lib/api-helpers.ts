// Shared helpers for API route handlers.

import { NextResponse } from "next/server";
import { ProviderError } from "@/lib/providers/types";

/** Wrap a handler so provider failures never 500 the whole app. */
export async function guard<T>(fn: () => Promise<T>): Promise<NextResponse> {
  try {
    const data = await fn();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "public, s-maxage=120, stale-while-revalidate=600" },
    });
  } catch (err) {
    if (err instanceof ProviderError) {
      return NextResponse.json(
        { error: err.message, provider: err.providerId, kind: err.kind },
        { status: err.kind === "unsupported" ? 404 : 502 },
      );
    }
    return NextResponse.json({ error: (err as Error).message }, { status: 500 });
  }
}

export function intParam(url: URL, key: string, fallback: number, max?: number): number {
  const raw = url.searchParams.get(key);
  const n = raw != null ? Number(raw) : NaN;
  if (!isFinite(n) || n <= 0) return fallback;
  return max ? Math.min(Math.floor(n), max) : Math.floor(n);
}

export function strParam(url: URL, key: string): string | undefined {
  return url.searchParams.get(key) ?? undefined;
}

export function listParam(url: URL, key: string): string[] | undefined {
  const all = url.searchParams.getAll(key).flatMap((v) => v.split(",")).map((s) => s.trim()).filter(Boolean);
  return all.length ? all : undefined;
}
