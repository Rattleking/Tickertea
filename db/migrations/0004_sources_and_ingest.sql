-- 0004_sources_and_ingest.sql
-- Source registry + ingestion runs + append-only event log.
-- SHARED data: market reality is identical across tenants.

CREATE TABLE source (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key         text NOT NULL UNIQUE,    -- nse_announcements, mca_filings, diffbot_news, ...
  name        text NOT NULL,
  kind        text NOT NULL
              CHECK (kind IN ('exchange','registry','news','jobs','enrichment','market_data')),
  config      jsonb NOT NULL DEFAULT '{}'::jsonb,
  enabled     boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
SELECT attach_updated_at('source');

-- One execution of a connector. Operational visibility + incremental cursor.
CREATE TABLE ingest_run (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       uuid NOT NULL REFERENCES source(id),
  status          text NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running','succeeded','failed')),
  cursor          jsonb NOT NULL DEFAULT '{}'::jsonb,   -- watermark for incremental pulls
  events_emitted  integer NOT NULL DEFAULT 0,
  error           text,
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz
);
CREATE INDEX idx_ingest_run_source ON ingest_run(source_id, started_at DESC);

-- The atomic unit of the event-driven pipeline. APPEND-ONLY (status transitions only).
CREATE TABLE ingest_event (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id    uuid NOT NULL REFERENCES source(id),
  run_id       uuid REFERENCES ingest_run(id),
  company_id   uuid REFERENCES company(id),         -- NULL until resolved; never dropped
  external_id  text,                                -- provider's id
  dedupe_key   text NOT NULL UNIQUE,                -- deterministic; exactly-once ingestion
  event_type   text NOT NULL,                       -- board_meeting, job_posting, bulk_deal, ...
  raw_uri      text NOT NULL,                        -- S3 pointer to immutable raw payload
  payload      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- normalized, source-agnostic
  status       text NOT NULL DEFAULT 'received'
               CHECK (status IN ('received','normalized','processed','failed')),
  error        text,
  occurred_at  timestamptz,                          -- when the event happened in the world
  received_at  timestamptz NOT NULL DEFAULT now(),   -- when we ingested it
  processed_at timestamptz
);
CREATE INDEX idx_ingest_event_company ON ingest_event(company_id, occurred_at DESC);
CREATE INDEX idx_ingest_event_status ON ingest_event(source_id, status);
CREATE INDEX idx_ingest_event_type ON ingest_event(event_type, occurred_at DESC);
CREATE INDEX idx_ingest_event_payload ON ingest_event USING gin (payload);
