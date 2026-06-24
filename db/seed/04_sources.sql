-- 04_sources.sql
-- External data source registry.

INSERT INTO source (id, key, name, kind) VALUES
  ('50000000-0000-0000-0000-000000000001', 'nse_announcements', 'NSE Corporate Announcements', 'exchange'),
  ('50000000-0000-0000-0000-000000000002', 'bse_announcements', 'BSE Corporate Announcements', 'exchange'),
  ('50000000-0000-0000-0000-000000000003', 'mca_filings',       'MCA Filings',                 'registry'),
  ('50000000-0000-0000-0000-000000000004', 'diffbot_news',      'Diffbot News',                'news'),
  ('50000000-0000-0000-0000-000000000005', 'diffbot_org',       'Diffbot Organization',        'enrichment'),
  ('50000000-0000-0000-0000-000000000006', 'linkedin_jobs',     'LinkedIn Jobs',               'jobs'),
  ('50000000-0000-0000-0000-000000000007', 'nse_market_data',   'NSE Market Data',             'market_data')
ON CONFLICT (key) DO NOTHING;
