// GET /api/providers — provider registry status + capability detection.
import { NextResponse } from "next/server";
import { listProviders, healthyProviders } from "@/lib/providers/registry";

export async function GET() {
  const all = listProviders();
  const healthy = new Set(healthyProviders().map((p) => p.getProviderInfo().id));
  return NextResponse.json({
    providers: all.map((p) => ({ ...p, healthy: healthy.has(p.id) })),
  });
}
