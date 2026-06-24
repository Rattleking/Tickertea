-- 0003_companies.sql
-- Company master + external identifiers + index membership (point-in-time).
-- All SHARED (global) reference data: no tenant_id.

CREATE TABLE company (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  legal_name  text,
  cin         text UNIQUE,                       -- MCA Corporate Identity Number
  sector      text,
  industry    text,
  status      text NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','suspended','delisted')),
  in_universe boolean NOT NULL DEFAULT false,    -- part of the ~250 tracked universe
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  deleted_at  timestamptz
);
SELECT attach_updated_at('company');

CREATE INDEX idx_company_universe ON company(in_universe) WHERE in_universe;
CREATE INDEX idx_company_sector ON company(sector);
CREATE INDEX idx_company_name_trgm ON company USING gin (name gin_trgm_ops);

-- One company maps to many external keys (NSE symbol, BSE code, ISIN, MCA CIN, etc.)
CREATE TABLE company_identifier (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id  uuid NOT NULL REFERENCES company(id),
  scheme      text NOT NULL
              CHECK (scheme IN ('nse_symbol','bse_code','isin','mca_cin','diffbot_id','lei')),
  value       text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scheme, value)            -- the join key for external feeds
);
CREATE INDEX idx_company_identifier_company ON company_identifier(company_id);

CREATE TABLE index_ref (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code        text NOT NULL UNIQUE,   -- NIFTY50, NIFTYNEXT50, FNO
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Point-in-time membership so we can answer "was X in Nifty 50 on date D?"
CREATE TABLE index_membership (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  index_id       uuid NOT NULL REFERENCES index_ref(id),
  company_id     uuid NOT NULL REFERENCES company(id),
  effective_from date NOT NULL,
  effective_to   date,                 -- NULL = currently a member
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_index_membership_company ON index_membership(company_id);
CREATE INDEX idx_index_membership_index ON index_membership(index_id);
-- Only one open membership row per (index, company).
CREATE UNIQUE INDEX uq_index_membership_open
  ON index_membership(index_id, company_id) WHERE effective_to IS NULL;
