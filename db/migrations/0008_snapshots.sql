-- 0008_snapshots.sql
-- Append-only point-in-time snapshots of a company's observable metrics.
-- SHARED. Powers mean-reversion baselines and the historical analog engine.

CREATE TABLE historical_snapshot (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id     uuid NOT NULL REFERENCES company(id),
  source_run_id  uuid REFERENCES ingest_run(id),
  as_of          timestamptz NOT NULL,
  metrics        jsonb NOT NULL DEFAULT '{}'::jsonb,
  -- metrics example:
  -- { "price_close": 1234.5, "pe": 28.1, "pb": 5.2, "mcap": 1.2e12,
  --   "open_roles": 142, "fii_pct": 21.3, "dii_pct": 18.9, "narrative_tone": 0.31 }
  created_at     timestamptz NOT NULL DEFAULT now()
);

-- One snapshot per company per as_of timestamp.
CREATE UNIQUE INDEX uq_snapshot_company_asof ON historical_snapshot(company_id, as_of);
CREATE INDEX idx_snapshot_company ON historical_snapshot(company_id, as_of DESC);
CREATE INDEX idx_snapshot_metrics ON historical_snapshot USING gin (metrics);

-- NOTE: a future migration adds `embedding vector(N)` + an ANN index here for the
-- analog engine (pgvector). The skeleton keeps the feature vector in analog_query.jsonb
-- so search backends can be swapped without changing the API contract.
