import { headers } from "next/headers";

export interface SessionContext {
  userId: string;
  tenantId: string;
  role: "owner" | "admin" | "analyst" | "viewer";
}

/**
 * Resolves the authenticated session and its tenant context.
 *
 * STUB: wire this to your auth provider. The critical invariant is that `tenantId`
 * is derived from the user's membership server-side — NEVER read from request input.
 * Until auth is wired, this reads a dev header so the API is runnable locally.
 */
export async function getSession(): Promise<SessionContext | null> {
  const h = await headers();
  const tenantId = h.get("x-dev-tenant-id");
  const userId = h.get("x-dev-user-id");
  if (!tenantId || !userId) return null;
  return { userId, tenantId, role: "analyst" };
}

export async function requireSession(): Promise<SessionContext> {
  const session = await getSession();
  if (!session) throw new UnauthorizedError();
  return session;
}

export class UnauthorizedError extends Error {
  constructor() {
    super("Authentication required");
    this.name = "UnauthorizedError";
  }
}
