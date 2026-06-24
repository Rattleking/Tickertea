-- 0011_rls_policies.sql
-- Roles + Row-Level Security. Tenant isolation is enforced at the database for the
-- application role. See docs/architecture/07-multi-tenancy.md.
--
-- Portability: this migration runs on both self-managed Postgres (superuser) and managed
-- Postgres without superuser (e.g. Neon). It therefore avoids superuser-only attributes:
--   * No BYPASSRLS (cannot be granted without a real superuser).
--   * No FORCE ROW LEVEL SECURITY: the table-OWNER role (the migration / trusted-worker
--     role) bypasses RLS by the standard Postgres rule, which is exactly the trusted path
--     we want. The application connects as the NON-owner `tickertea_app` role, to which
--     RLS policies DO apply. Same isolation guarantee, no superuser required.

-- ---------------------------------------------------------------------------
-- Roles (idempotent). Created NOLOGIN; provisioning layer attaches LOGIN + password.
-- tickertea_app  = application role  -> RLS ENFORCED (non-owner).
-- tickertea_admin = migrations/workers -> trusted (owns tables / table-owner bypass).
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tickertea_app') THEN
    CREATE ROLE tickertea_app NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tickertea_admin') THEN
    CREATE ROLE tickertea_admin NOLOGIN;
  END IF;
END$$;

GRANT USAGE ON SCHEMA public TO tickertea_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tickertea_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO tickertea_app;

-- ---------------------------------------------------------------------------
-- Helper: current tenant from the transaction-scoped GUC app.tenant_id.
-- Set via `SELECT set_config('app.tenant_id', '<uuid>', true)` (see tenant-context.ts).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS uuid AS $$
  SELECT nullif(current_setting('app.tenant_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

-- ---------------------------------------------------------------------------
-- Enable RLS + isolation policy on every tenant-scoped table (idempotent).
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  t text;
  tenant_tables text[] := ARRAY[
    'signal','signal_evidence','signal_score','scoring_config',
    'watchlist','watchlist_item','alert',
    'analog_query','analog_match','membership'
  ];
BEGIN
  FOREACH t IN ARRAY tenant_tables LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I_tenant_isolation ON %I', t, t);
    EXECUTE format(
      'CREATE POLICY %I_tenant_isolation ON %I
         USING (tenant_id = current_tenant_id())
         WITH CHECK (tenant_id = current_tenant_id())', t, t);
  END LOOP;
END$$;

-- app_user is reachable only through the current tenant's memberships.
ALTER TABLE app_user ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS app_user_via_membership ON app_user;
CREATE POLICY app_user_via_membership ON app_user
  USING (EXISTS (
    SELECT 1 FROM membership m
    WHERE m.user_id = app_user.id
      AND m.tenant_id = current_tenant_id()
  ));

-- tenant: a session may read only its own tenant row.
ALTER TABLE tenant ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_self ON tenant;
CREATE POLICY tenant_self ON tenant
  USING (id = current_tenant_id());

-- NOTE: shared reference tables (company, company_identifier, index_ref,
-- index_membership, source, ingest_run, ingest_event, signal_category,
-- historical_snapshot) have NO RLS: they are global market data readable by all tenants.
