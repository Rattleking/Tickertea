-- 0010_watchlists_alerts.sql
-- User watchlists and alert subscriptions. TENANT-SCOPED.

CREATE TABLE watchlist (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid NOT NULL REFERENCES tenant(id),
  user_id     uuid NOT NULL REFERENCES app_user(id),
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
SELECT attach_updated_at('watchlist');
CREATE INDEX idx_watchlist_user ON watchlist(tenant_id, user_id);

CREATE TABLE watchlist_item (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    uuid NOT NULL REFERENCES tenant(id),
  watchlist_id uuid NOT NULL REFERENCES watchlist(id) ON DELETE CASCADE,
  company_id   uuid NOT NULL REFERENCES company(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (watchlist_id, company_id)
);
CREATE INDEX idx_watchlist_item_company ON watchlist_item(company_id);

-- A user's subscription to signal conditions. Skeleton in v1.
CREATE TABLE alert (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL REFERENCES tenant(id),
  user_id       uuid NOT NULL REFERENCES app_user(id),
  category_id   uuid REFERENCES signal_category(id),   -- NULL = any category
  watchlist_id  uuid REFERENCES watchlist(id),         -- scope to a watchlist, or
  company_id    uuid REFERENCES company(id),           -- a single company
  min_composite numeric(4,3) NOT NULL DEFAULT 0.500,
  channel       text NOT NULL DEFAULT 'in_app'
                CHECK (channel IN ('in_app','email','webhook')),
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
SELECT attach_updated_at('alert');
CREATE INDEX idx_alert_user ON alert(tenant_id, user_id) WHERE is_active;
