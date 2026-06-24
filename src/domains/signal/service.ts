import { withTenant } from "@/lib/db/tenant-context.js";
import { DISCLAIMER, type Signal, type SignalListQuery } from "@tickertea/contracts";
import { listSignals, type SignalRow } from "./repository.js";

/** Map a DB row to the API Signal shape. Numeric columns arrive as strings from pg. */
function toSignal(row: SignalRow): Signal {
  const hasScore = row.composite !== null;
  return {
    id: row.id,
    company: { id: row.company_id, name: row.company_name, nse_symbol: row.nse_symbol },
    category: { slug: row.category_slug as Signal["category"]["slug"], name: row.category_name },
    title: row.title,
    summary: row.summary,
    direction: row.direction,
    status: row.status as Signal["status"],
    observed_at: row.observed_at,
    score: hasScore
      ? {
          magnitude: Number(row.magnitude),
          confidence: Number(row.confidence),
          novelty: Number(row.novelty),
          composite: Number(row.composite),
          model_version: row.model_version!,
        }
      : null,
    evidence_count: row.evidence_count,
    disclaimer: DISCLAIMER,
  };
}

export async function getSignalFeed(
  tenantId: string,
  query: SignalListQuery,
): Promise<{ data: Signal[]; next_cursor: string | null }> {
  return withTenant(tenantId, async (tx) => {
    const { rows, nextCursor } = await listSignals(tx, query);
    return { data: rows.map(toSignal), next_cursor: nextCursor };
  });
}
