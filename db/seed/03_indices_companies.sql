-- 03_indices_companies.sql
-- Indices + a small representative slice of the universe with identifiers and membership.
-- (Full universe of ~250 is loaded by an ingestion backfill job; this is a dev sample.)

INSERT INTO index_ref (id, code, name) VALUES
  ('a0000000-0000-0000-0000-000000000001', 'NIFTY50',     'Nifty 50'),
  ('a0000000-0000-0000-0000-000000000002', 'NIFTYNEXT50', 'Nifty Next 50'),
  ('a0000000-0000-0000-0000-000000000003', 'FNO',         'F&O Stocks')
ON CONFLICT (code) DO NOTHING;

-- Sample companies (id, name, cin, sector, in_universe).
INSERT INTO company (id, name, legal_name, cin, sector, industry, in_universe) VALUES
  ('c0000000-0000-0000-0000-000000000001', 'Reliance Industries', 'Reliance Industries Limited', 'L17110MH1973PLC019786', 'Energy',      'Refineries',        true),
  ('c0000000-0000-0000-0000-000000000002', 'Tata Consultancy Services', 'Tata Consultancy Services Limited', 'L22210MH1995PLC084781', 'IT', 'IT Services', true),
  ('c0000000-0000-0000-0000-000000000003', 'HDFC Bank',            'HDFC Bank Limited',            'L65920MH1994PLC080618', 'Financials',  'Private Bank',      true),
  ('c0000000-0000-0000-0000-000000000004', 'Infosys',              'Infosys Limited',              'L85110KA1981PLC013115', 'IT',          'IT Services',       true),
  ('c0000000-0000-0000-0000-000000000005', 'Larsen & Toubro',      'Larsen & Toubro Limited',      'L99999MH1946PLC004768', 'Industrials', 'Construction',      true)
ON CONFLICT (id) DO NOTHING;

INSERT INTO company_identifier (company_id, scheme, value) VALUES
  ('c0000000-0000-0000-0000-000000000001', 'nse_symbol', 'RELIANCE'),
  ('c0000000-0000-0000-0000-000000000001', 'isin',       'INE002A01018'),
  ('c0000000-0000-0000-0000-000000000002', 'nse_symbol', 'TCS'),
  ('c0000000-0000-0000-0000-000000000002', 'isin',       'INE467B01029'),
  ('c0000000-0000-0000-0000-000000000003', 'nse_symbol', 'HDFCBANK'),
  ('c0000000-0000-0000-0000-000000000003', 'isin',       'INE040A01034'),
  ('c0000000-0000-0000-0000-000000000004', 'nse_symbol', 'INFY'),
  ('c0000000-0000-0000-0000-000000000004', 'isin',       'INE009A01021'),
  ('c0000000-0000-0000-0000-000000000005', 'nse_symbol', 'LT'),
  ('c0000000-0000-0000-0000-000000000005', 'isin',       'INE018A01030')
ON CONFLICT (scheme, value) DO NOTHING;

-- All five are current Nifty 50 + F&O members (effective_to NULL = current).
INSERT INTO index_membership (index_id, company_id, effective_from) VALUES
  ('a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', '2020-01-01'),
  ('a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000002', '2020-01-01'),
  ('a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000003', '2020-01-01'),
  ('a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000004', '2020-01-01'),
  ('a0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000005', '2020-01-01')
ON CONFLICT DO NOTHING;
