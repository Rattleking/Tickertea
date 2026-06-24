-- 0007_scoring.sql
-- Scoring engine output (append-only history, one current row per signal) + per-tenant config.
-- Scores are DESCRIPTIVE intensities in [0,1] — NOT expected returns or price targets.

CREATE TABLE signal_score (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid NOT NULL REFERENCES tenant(id),
  signal_id     uuid NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  magnitude     numeric(4,3) NOT NULL CHECK (magnitude  BETWEEN 0 AND 1),
  confidence    numeric(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  novelty       numeric(4,3) NOT NULL CHECK (novelty    BETWEEN 0 AND 1),
  composite     numeric(4,3) NOT NULL CHECK (composite  BETWEEN 0 AND 1),
  model_version text NOT NULL,
  features      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- inputs + LLM prompt/model versions (audit)
  is_current    boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Fast lookup of the current score; at most one current score per signal.
CREATE UNIQUE INDEX uq_score_current ON signal_score(signal_id) WHERE is_current;
CREATE INDEX idx_score_signal ON signal_score(signal_id, created_at DESC);
CREATE INDEX idx_score_composite ON signal_score(tenant_id, composite DESC) WHERE is_current;

-- Per-tenant scoring configuration: weights, thresholds, category enable flags.
CREATE TABLE scoring_config (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         uuid NOT NULL REFERENCES tenant(id),
  weight_magnitude  numeric(4,3) NOT NULL DEFAULT 0.400,
  weight_confidence numeric(4,3) NOT NULL DEFAULT 0.350,
  weight_novelty    numeric(4,3) NOT NULL DEFAULT 0.250,
  publish_threshold numeric(4,3) NOT NULL DEFAULT 0.500,
  category_overrides jsonb NOT NULL DEFAULT '{}'::jsonb,  -- per-category weight/threshold overrides
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id)
);
SELECT attach_updated_at('scoring_config');
