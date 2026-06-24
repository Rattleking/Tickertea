-- local_setup.sql
-- Bootstrap for LOCAL development against a native PostgreSQL instance (no Docker).
-- Run this ONCE, connected to the `postgres` database as a SUPERUSER. It creates the
-- login roles and the tickertea database; migrations (db/migrations/*) then build the schema.
--
--   psql -U postgres -h localhost -d postgres -f db/local_setup.sql
--
-- Passwords here match .env.example ('tickertea'). Change them for anything but local dev.

-- Application role: RLS is ENFORCED for this role (not BYPASSRLS).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tickertea_app') THEN
    CREATE ROLE tickertea_app LOGIN PASSWORD 'tickertea';
  ELSE
    ALTER ROLE tickertea_app LOGIN PASSWORD 'tickertea';
  END IF;
END$$;

-- Admin role: used by migrations and trusted workers. BYPASSRLS + CREATEDB for local convenience.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tickertea_admin') THEN
    CREATE ROLE tickertea_admin LOGIN PASSWORD 'tickertea' BYPASSRLS CREATEDB;
  ELSE
    ALTER ROLE tickertea_admin LOGIN PASSWORD 'tickertea' BYPASSRLS CREATEDB;
  END IF;
END$$;

-- Create the database owned by the admin role (CREATE DATABASE cannot run in a txn/DO block).
-- \gexec runs the generated CREATE DATABASE only when it does not already exist.
SELECT 'CREATE DATABASE tickertea OWNER tickertea_admin'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'tickertea')\gexec

-- Let the app role connect.
GRANT CONNECT ON DATABASE tickertea TO tickertea_app;
