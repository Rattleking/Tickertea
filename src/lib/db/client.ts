import { Pool, type PoolClient } from "pg";

/**
 * The application connection pool. Connects as the non-BYPASSRLS `tickertea_app`
 * role so Postgres RLS always enforces tenant isolation (see migration 0011).
 */
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: Number(process.env.DB_POOL_MAX ?? 10),
});

export { pool };
export type { PoolClient };
