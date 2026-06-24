import { pool, type PoolClient } from "./client.js";

/**
 * The ONLY sanctioned way to run tenant-scoped queries.
 *
 * Opens a transaction, sets the transaction-scoped GUC `app.tenant_id`, and runs the
 * callback. Postgres RLS policies (migration 0011) then filter every tenant-scoped
 * table to this tenant. The tenant_id MUST come from the authenticated session /
 * membership — never from client input. See docs/architecture/07-multi-tenancy.md.
 */
export async function withTenant<T>(
  tenantId: string,
  fn: (tx: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    // set_config(..., true) => transaction-local; cleared on COMMIT/ROLLBACK.
    await client.query("SELECT set_config('app.tenant_id', $1, true)", [tenantId]);
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

/** For reads over SHARED reference data only (no tenant scoping needed). */
export async function withSharedRead<T>(
  fn: (tx: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await pool.connect();
  try {
    return await fn(client);
  } finally {
    client.release();
  }
}
