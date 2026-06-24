import { headers } from "next/headers";
import type { Signal } from "@tickertea/contracts";

/**
 * Server-side fetch of the LIVE signal feed from GET /api/v1/signals.
 * No mock data — this calls the real route handler, which reads from Neon under RLS.
 *
 * Auth: the API derives the tenant from a session. Until real auth is wired, we forward
 * the dev session headers the stub expects (see src/lib/auth/session.ts). The tenant/user
 * identity comes from env with the seeded demo workspace as the default — this is an auth
 * shim, not data; every signal returned is real.
 */
const DEV_TENANT_ID = process.env.TICKERTEA_DEV_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";
const DEV_USER_ID = process.env.TICKERTEA_DEV_USER_ID ?? "22222222-2222-2222-2222-222222222222";

export interface SignalFeedFilters {
  category?: string;
  min_composite?: number;
  direction?: "up" | "down" | "neutral";
  limit?: number;
}

export interface SignalFeed {
  data: Signal[];
  next_cursor: string | null;
}

function buildQuery(filters: SignalFeedFilters): string {
  const p = new URLSearchParams();
  if (filters.category) p.set("category", filters.category);
  if (typeof filters.min_composite === "number") p.set("min_composite", String(filters.min_composite));
  if (filters.direction) p.set("direction", filters.direction);
  p.set("limit", String(filters.limit ?? 50));
  return p.toString();
}

async function baseUrl(): Promise<string> {
  const h = await headers();
  const host = h.get("x-forwarded-host") ?? h.get("host") ?? "localhost:3000";
  const proto = h.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${proto}://${host}`;
}

export async function fetchSignalFeed(filters: SignalFeedFilters): Promise<SignalFeed> {
  const url = `${await baseUrl()}/api/v1/signals?${buildQuery(filters)}`;
  const res = await fetch(url, {
    headers: { "x-dev-tenant-id": DEV_TENANT_ID, "x-dev-user-id": DEV_USER_ID },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`signals API ${res.status}: ${body.slice(0, 200)}`);
  }
  return (await res.json()) as SignalFeed;
}
