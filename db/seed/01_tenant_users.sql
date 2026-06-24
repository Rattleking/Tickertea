-- 01_tenant_users.sql
-- A demo tenant, a user, a membership, and default scoring config.
-- Stable UUIDs so later seed files can reference them.

INSERT INTO tenant (id, slug, name, plan, status) VALUES
  ('11111111-1111-1111-1111-111111111111', 'demo', 'Tickertea Demo', 'standard', 'active')
ON CONFLICT (id) DO NOTHING;

INSERT INTO app_user (id, email, display_name, auth_provider) VALUES
  ('22222222-2222-2222-2222-222222222222', 'analyst@tickertea.tech', 'Demo Analyst', 'password')
ON CONFLICT (id) DO NOTHING;

INSERT INTO membership (id, tenant_id, user_id, role) VALUES
  ('33333333-3333-3333-3333-333333333333',
   '11111111-1111-1111-1111-111111111111',
   '22222222-2222-2222-2222-222222222222', 'owner')
ON CONFLICT (id) DO NOTHING;

INSERT INTO scoring_config (tenant_id) VALUES
  ('11111111-1111-1111-1111-111111111111')
ON CONFLICT (tenant_id) DO NOTHING;
