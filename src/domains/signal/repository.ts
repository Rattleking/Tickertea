import type { PoolClient } from "@/lib/db/client";
import type { SignalListQuery } from "@tickertea/contracts";

/**
 * Data access for signals. Internal to the signal domain — callers must go through
 * the public barrel (index.ts), not import this file directly (enforced by
 * dependency-cruiser). All queries assume an RLS-scoped transaction from withTenant().
 */

export interface SignalRow {
  id: string;
  company_id: string;
  company_name: string;
  nse_symbol: string | null;
  category_slug: string;
  category_name: string;
  title: string;
  summary: string | null;
  direction: "up" | "down" | "neutral";
  status: string;
  observed_at: string;
  magnitude: string | null;
  confidence: string | null;
  novelty: string | null;
  composite: string | null;
  model_version: string | null;
  evidence_count: number;
}

export async function listSignals(
  tx: PoolClient,
  q: SignalListQuery,
): Promise<{ rows: SignalRow[]; nextCursor: string | null }> {
  // Cursor is the observed_at of the last row (keyset pagination on the feed index).
  const params: unknown[] = [q.status];
  const where: string[] = ["s.status = $1", "s.deleted_at IS NULL"];

  if (q.company_id) { params.push(q.company_id); where.push(`s.company_id = $${params.length}`); }
  if (q.category) { params.push(q.category); where.push(`cat.slug = $${params.length}`); }
  if (q.direction) { params.push(q.direction); where.push(`s.direction = $${params.length}`); }
  if (q.observed_from) { params.push(q.observed_from); where.push(`s.observed_at >= $${params.length}`); }
  if (q.observed_to) { params.push(q.observed_to); where.push(`s.observed_at <= $${params.length}`); }
  if (q.min_composite !== undefined) { params.push(q.min_composite); where.push(`sc.composite >= $${params.length}`); }
  if (q.cursor) { params.push(q.cursor); where.push(`s.observed_at < $${params.length}`); }

  params.push(q.limit + 1); // fetch one extra to compute next_cursor
  const limitParam = `$${params.length}`;

  const sql = `
    SELECT s.id, s.company_id, c.name AS company_name,
           ci.value AS nse_symbol,
           cat.slug AS category_slug, cat.name AS category_name,
           s.title, s.summary, s.direction, s.status, s.observed_at,
           sc.magnitude, sc.confidence, sc.novelty, sc.composite, sc.model_version,
           (SELECT count(*) FROM signal_evidence e WHERE e.signal_id = s.id)::int AS evidence_count
    FROM signal s
    JOIN company c ON c.id = s.company_id
    JOIN signal_category cat ON cat.id = s.category_id
    LEFT JOIN company_identifier ci
           ON ci.company_id = c.id AND ci.scheme = 'nse_symbol'
    LEFT JOIN signal_score sc
           ON sc.signal_id = s.id AND sc.is_current
    WHERE ${where.join(" AND ")}
    ORDER BY s.observed_at DESC
    LIMIT ${limitParam}
  `;

  const res = await tx.query<SignalRow>(sql, params);
  const hasMore = res.rows.length > q.limit;
  const rows = hasMore ? res.rows.slice(0, q.limit) : res.rows;
  const nextCursor = hasMore ? rows[rows.length - 1]!.observed_at : null;
  return { rows, nextCursor };
}
