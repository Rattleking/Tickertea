import { withSharedRead } from "@/lib/db/tenant-context.js";
import { ok, fail } from "@/lib/http/respond.js";

/**
 * GET /api/v1/health — liveness + DB connectivity (no auth).
 * Reads shared reference data (no tenant context needed) to prove the app can reach Neon.
 */
export async function GET() {
  try {
    const row = await withSharedRead(async (tx) => {
      const r = await tx.query<{ companies: number; categories: number }>(
        `SELECT (SELECT count(*) FROM company)::int        AS companies,
                (SELECT count(*) FROM signal_category)::int AS categories`,
      );
      return r.rows[0];
    });
    return ok({ status: "ok", db: "up", ...row });
  } catch (e) {
    return fail(503, "db_unreachable", (e as Error).message);
  }
}
