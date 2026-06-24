import { headers } from "next/headers";
import type { Signal } from "@tickertea/contracts";

/**
 * Server-side fetch of the LIVE signal feed from GET /api/v1/signals.
 * Calls the real route handler (reads from Neon under RLS). Never throws — returns a
 * typed result so the page can render live data, an auth notice, or a graceful fallback.
 *
 * Auth: the API derives the tenant from a session. Until real auth is wired, we forward
 * the dev session headers the stub expects (see src/lib/auth/session.ts), sourced from env
 * with the seeded demo workspace as default. That is an auth shim, not data — live signals
 * are always real.
 */
const DEV_TENANT_ID = process.env.TICKERTEA_DEV_TENANT_ID ?? "11111111-1111-1111-1111-111111111111";
const DEV_USER_ID = process.env.TICKERTEA_DEV_USER_ID ?? "22222222-2222-2222-2222-222222222222";

export interface SignalFeedFilters {
  category?: string;
  min_composite?: number;
  direction?: "up" | "down" | "neutral";
  limit?: number;
}

export type SignalFeedResult =
  | { ok: true; data: Signal[]; next_cursor: string | null }
  | { ok: false; status: number; message: string };

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

/** Coerce an unknown API body into a safe Signal[] — tolerant of partial/missing fields. */
function coerceSignals(body: unknown): Signal[] {
  const rows = (body as { data?: unknown })?.data;
  if (!Array.isArray(rows)) return [];
  return rows.filter((r): r is Signal => !!r && typeof r === "object" && "id" in r);
}

export async function fetchSignalFeed(filters: SignalFeedFilters): Promise<SignalFeedResult> {
  let res: Response;
  try {
    res = await fetch(`${await baseUrl()}/api/v1/signals?${buildQuery(filters)}`, {
      headers: { "x-dev-tenant-id": DEV_TENANT_ID, "x-dev-user-id": DEV_USER_ID },
      cache: "no-store",
    });
  } catch (e) {
    return { ok: false, status: 0, message: e instanceof Error ? e.message : "Network error" };
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    return { ok: false, status: res.status, message: text.slice(0, 200) || res.statusText };
  }

  const json = await res.json().catch(() => null);
  const next = (json as { next_cursor?: string | null })?.next_cursor ?? null;
  return { ok: true, data: coerceSignals(json), next_cursor: next };
}
