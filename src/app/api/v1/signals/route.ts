import { SignalListQuerySchema } from "@tickertea/contracts";
import { getSignalFeed } from "@/domains/signal";
import { requireSession, UnauthorizedError } from "@/lib/auth/session.js";
import { ok, fail, parseOr400, searchParamsToObject } from "@/lib/http/respond.js";

/**
 * GET /api/v1/signals — the core signal feed.
 *
 * Demonstrates the standard handler pattern:
 *   1. resolve session (tenant derived server-side)
 *   2. validate input against the shared contract
 *   3. delegate to the domain service (RLS-scoped query)
 *   4. serialize via the contract shape
 */
export async function GET(req: Request) {
  let session;
  try {
    session = await requireSession();
  } catch (err) {
    if (err instanceof UnauthorizedError) return fail(401, "unauthorized", err.message);
    throw err;
  }

  const parsed = parseOr400(SignalListQuerySchema, searchParamsToObject(req.url));
  if (!parsed.ok) return parsed.response;

  const result = await getSignalFeed(session.tenantId, parsed.value);
  return ok(result);
}
