-- 0009_analog.sql
-- Historical analog engine (skeleton). TENANT-SCOPED.
-- Finds comparable PAST situations. Deliberately NO outcome/return field by design.

CREATE TABLE analog_query (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL REFERENCES tenant(id),
  signal_id      uuid REFERENCES signal(id),          -- optional seed signal
  company_id     uuid REFERENCES company(id),         -- or seed company state
  as_of          timestamptz,                          -- the "now" being matched
  feature_vector jsonb NOT NULL DEFAULT '[]'::jsonb,   -- normalized features (jsonb for backend-agnosticism)
  filters        jsonb NOT NULL DEFAULT '{}'::jsonb,   -- sector/index/category/date_range
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_analog_query_tenant ON analog_query(tenant_id, created_at DESC);

CREATE TABLE analog_match (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL REFERENCES tenant(id),
  analog_query_id uuid NOT NULL REFERENCES analog_query(id) ON DELETE CASCADE,
  snapshot_id     uuid NOT NULL REFERENCES historical_snapshot(id),
  signal_ref_id   uuid REFERENCES signal(id),          -- signal active at that snapshot, if any
  similarity      numeric(5,4) NOT NULL CHECK (similarity BETWEEN 0 AND 1),
  explanation     jsonb NOT NULL DEFAULT '{}'::jsonb,   -- per-feature contribution (auditable)
  rank            integer NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_analog_match_query ON analog_match(analog_query_id, rank);
