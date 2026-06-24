-- 02_signal_categories.sql
-- The v1 signal categories. detector_key maps to a Python detector class.

INSERT INTO signal_category (slug, name, description, detector_key, default_weight) VALUES
  ('mean_reversion',      'Mean Reversion',      'Price/valuation N std-devs from its own trailing mean.',           'mean_reversion.v1',      1.000),
  ('hiring_spike',        'Hiring Spike',        'Open roles up sharply vs the company''s trailing baseline.',        'hiring_spike.v1',        1.000),
  ('management_change',   'Management Change',   'CXO / board / KMP appointment or exit.',                            'management_change.v1',   1.200),
  ('capex_expansion',     'Capex Expansion',     'New plant, capacity addition, or capex guidance.',                  'capex_expansion.v1',     1.100),
  ('subsidiary_creation', 'Subsidiary Creation', 'New subsidiary or JV registered (MCA).',                            'subsidiary_creation.v1', 1.000),
  ('narrative_shift',     'Narrative Shift',     'Tone or theme of coverage changes materially.',                     'narrative_shift.v1',     0.900),
  ('news_event',          'News Event',          'Material disclosed event (filing, order, ruling).',                 'news_event.v1',          0.800),
  ('insider_activity',    'Insider Activity',    'Promoter / insider buy-sell disclosures.',                          'insider_activity.v1',    1.150),
  ('institutional_flow',  'Institutional Flow',  'FII/DII/MF holding changes, bulk/block deals.',                     'institutional_flow.v1',  1.050)
ON CONFLICT (slug) DO NOTHING;
