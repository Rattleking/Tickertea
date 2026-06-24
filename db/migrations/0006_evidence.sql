-- 0006_evidence.sql
-- Traceability: why a signal exists. Every signal must have >= 1 evidence row.
-- TENANT-SCOPED (mirrors its signal's tenant).

CREATE TABLE signal_evidence (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenant(id),
  signal_id        uuid NOT NULL REFERENCES signal(id) ON DELETE CASCADE,
  ingest_event_id  uuid NOT NULL REFERENCES ingest_event(id),  -- the source datum (shared)
  evidence_type    text NOT NULL
                   CHECK (evidence_type IN
                     ('filing','news','job_posting','price_series',
                      'mca_record','holding_disclosure','llm_extraction')),
  artifact_uri     text,            -- optional S3 snapshot/screenshot
  excerpt          text,            -- the exact supporting text
  weight           numeric(4,3) NOT NULL DEFAULT 1.000,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- M:N in practice: a signal cites many events; an event supports many signals.
CREATE INDEX idx_evidence_signal ON signal_evidence(signal_id);
CREATE INDEX idx_evidence_event ON signal_evidence(ingest_event_id);
-- Don't cite the same event twice for one signal.
CREATE UNIQUE INDEX uq_evidence_signal_event
  ON signal_evidence(signal_id, ingest_event_id);

-- Integrity helper: signals with zero evidence (should always be empty for published).
-- Used by a periodic integrity check; the detector contract also enforces >=1 at write time.
CREATE VIEW signal_without_evidence AS
  SELECT s.id, s.tenant_id, s.status, s.created_at
  FROM signal s
  LEFT JOIN signal_evidence e ON e.signal_id = s.id
  WHERE e.id IS NULL;
