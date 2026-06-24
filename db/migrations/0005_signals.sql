-- 0005_signals.sql
-- Signal categories (shared lookup) + signals (tenant-scoped core unit).

-- Pluggable category list. Adding a category = inserting a row + shipping a detector.
CREATE TABLE signal_category (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug           text NOT NULL UNIQUE,    -- mean_reversion, hiring_spike, ...
  name           text NOT NULL,
  description    text,
  detector_key   text NOT NULL,           -- which Python detector produces it
  default_weight numeric(4,3) NOT NULL DEFAULT 1.000,
  is_active      boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
SELECT attach_updated_at('signal_category');

-- The product's core unit: an evidence-backed observation about a company.
-- TENANT-SCOPED: same evidence can yield different signals per tenant config.
-- NOTE: deliberately NO target_price / rating / action / expected_return columns.
--       Advice cannot be persisted by design (see compliance guardrails doc).
CREATE TABLE signal (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenant(id),
  company_id       uuid NOT NULL REFERENCES company(id),
  category_id      uuid NOT NULL REFERENCES signal_category(id),
  title            text NOT NULL,
  summary          text,
  direction        text NOT NULL DEFAULT 'neutral'
                   CHECK (direction IN ('up','down','neutral')),  -- describes observation, NOT advice
  status           text NOT NULL DEFAULT 'candidate'
                   CHECK (status IN ('candidate','scored','published','suppressed','expired')),
  dedupe_key       text NOT NULL,         -- idempotent detection (per tenant)
  detector_version text NOT NULL,
  metadata         jsonb NOT NULL DEFAULT '{}'::jsonb,
  observed_at      timestamptz NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  deleted_at       timestamptz,
  UNIQUE (tenant_id, dedupe_key)
);
SELECT attach_updated_at('signal');

-- Primary feed query: tenant's latest published signals.
CREATE INDEX idx_signal_feed ON signal(tenant_id, status, observed_at DESC);
-- Company timeline.
CREATE INDEX idx_signal_company ON signal(tenant_id, company_id, observed_at DESC);
-- Category feed.
CREATE INDEX idx_signal_category ON signal(tenant_id, category_id, observed_at DESC);
CREATE INDEX idx_signal_metadata ON signal USING gin (metadata);
