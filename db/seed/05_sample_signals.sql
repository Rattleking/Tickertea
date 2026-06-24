-- 05_sample_signals.sql
-- Two end-to-end examples demonstrating the full traceability chain:
--   ingest_event (shared) -> signal (tenant) -> signal_evidence (tenant) -> signal_score (tenant)
-- Note the absence of any target price / recommendation: signals are observations only.

-- ---- Shared ingest events (the evidence) -------------------------------------------------
INSERT INTO ingest_event
  (id, source_id, company_id, external_id, dedupe_key, event_type, raw_uri, payload, status, occurred_at)
VALUES
  ('e0000000-0000-0000-0000-000000000001',
   '50000000-0000-0000-0000-000000000006',                 -- linkedin_jobs
   'c0000000-0000-0000-0000-000000000004',                 -- Infosys
   'li-job-batch-2026-06-20',
   'linkedin_jobs:infy:2026-06-20',
   'job_posting_batch',
   's3://tickertea-raw/raw/linkedin_jobs/2026/06/20/li-job-batch.json',
   '{"open_roles": 412, "trailing_90d_mean": 180, "trailing_90d_std": 72, "function": "engineering"}'::jsonb,
   'processed', '2026-06-20T06:30:00Z'),

  ('e0000000-0000-0000-0000-000000000002',
   '50000000-0000-0000-0000-000000000001',                 -- nse_announcements
   'c0000000-0000-0000-0000-000000000001',                 -- Reliance
   'nse-ann-2026-06-21-0098',
   'nse_announcements:reliance:0098',
   'board_meeting',
   's3://tickertea-raw/raw/nse_announcements/2026/06/21/ann-0098.pdf',
   '{"subject": "Appointment of Chief Technology Officer", "kmp": true}'::jsonb,
   'processed', '2026-06-21T11:05:00Z')
ON CONFLICT (dedupe_key) DO NOTHING;

-- ---- Tenant signals ----------------------------------------------------------------------
INSERT INTO signal
  (id, tenant_id, company_id, category_id, title, summary, direction, status,
   dedupe_key, detector_version, observed_at)
VALUES
  ('51900000-0000-0000-0000-000000000001',
   '11111111-1111-1111-1111-111111111111',
   'c0000000-0000-0000-0000-000000000004',                 -- Infosys
   (SELECT id FROM signal_category WHERE slug = 'hiring_spike'),
   'Open engineering roles up 3.2σ vs trailing 90-day mean',
   'Infosys engineering job postings rose to 412, about 3.2 standard deviations above its trailing 90-day average of 180. Observation only.',
   'up', 'published',
   'hiring_spike:infy:2026-06-20', 'hiring_spike.v1', '2026-06-20T06:30:00Z'),

  ('51900000-0000-0000-0000-000000000002',
   '11111111-1111-1111-1111-111111111111',
   'c0000000-0000-0000-0000-000000000001',                 -- Reliance
   (SELECT id FROM signal_category WHERE slug = 'management_change'),
   'New Chief Technology Officer appointed (KMP)',
   'Reliance disclosed the appointment of a new CTO via an NSE board-meeting announcement. Key managerial personnel change.',
   'neutral', 'published',
   'management_change:reliance:0098', 'management_change.v1', '2026-06-21T11:05:00Z')
ON CONFLICT (tenant_id, dedupe_key) DO NOTHING;

-- ---- Evidence (links each signal back to its source event) -------------------------------
INSERT INTO signal_evidence
  (tenant_id, signal_id, ingest_event_id, evidence_type, artifact_uri, excerpt, weight)
VALUES
  ('11111111-1111-1111-1111-111111111111',
   '51900000-0000-0000-0000-000000000001',
   'e0000000-0000-0000-0000-000000000001',
   'job_posting', NULL,
   '412 open engineering roles vs trailing-90d mean of 180 (std 72).', 1.000),

  ('11111111-1111-1111-1111-111111111111',
   '51900000-0000-0000-0000-000000000002',
   'e0000000-0000-0000-0000-000000000002',
   'filing', 's3://tickertea-raw/raw/nse_announcements/2026/06/21/ann-0098.pdf',
   'Appointment of Chief Technology Officer (KMP) per board meeting outcome.', 1.000)
ON CONFLICT (signal_id, ingest_event_id) DO NOTHING;

-- ---- Scores (descriptive intensities in [0,1]; NOT expected returns) ----------------------
INSERT INTO signal_score
  (tenant_id, signal_id, magnitude, confidence, novelty, composite, model_version, features, is_current)
VALUES
  ('11111111-1111-1111-1111-111111111111',
   '51900000-0000-0000-0000-000000000001',
   0.880, 0.700, 0.640, 0.760, 'score-1.0.0',
   '{"zscore": 3.2, "sources": 1, "category_weight": 1.0}'::jsonb, true),

  ('11111111-1111-1111-1111-111111111111',
   '51900000-0000-0000-0000-000000000002',
   0.600, 0.900, 0.700, 0.720, 'score-1.0.0',
   '{"is_kmp": true, "sources": 1, "category_weight": 1.2}'::jsonb, true)
ON CONFLICT DO NOTHING;
