-- 0002_tenancy_and_users.sql
-- Tenancy spine: tenant, app_user, membership. Multi-tenant from day one.

CREATE TABLE tenant (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        text NOT NULL UNIQUE,
  name        text NOT NULL,
  plan        text NOT NULL DEFAULT 'standard',
  status      text NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','suspended','closed')),
  settings    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
SELECT attach_updated_at('tenant');

-- A person. Not tenant-scoped directly; linked to tenants via membership so a
-- single identity can later belong to multiple tenants.
CREATE TABLE app_user (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         citext NOT NULL UNIQUE,
  display_name  text,
  auth_provider text NOT NULL DEFAULT 'password',
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  deleted_at    timestamptz
);
SELECT attach_updated_at('app_user');

CREATE TABLE membership (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenant(id),
  user_id     uuid NOT NULL REFERENCES app_user(id),
  role        text NOT NULL DEFAULT 'viewer'
              CHECK (role IN ('owner','admin','analyst','viewer')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz,
  UNIQUE (tenant_id, user_id)
);
SELECT attach_updated_at('membership');

CREATE INDEX idx_membership_user ON membership(user_id);
CREATE INDEX idx_membership_tenant ON membership(tenant_id);
