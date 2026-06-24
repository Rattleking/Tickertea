# 02 — Data Model

This is the canonical description of the schema. The SQL in `db/migrations/` is the source of
truth; this document explains intent, relationships, and lifecycle. The ERD is in
[`../erd/erd.md`](../erd/erd.md).

## Conventions

- **IDs:** `uuid` primary keys, generated `gen_random_uuid()` (pgcrypto).
- **Time:** `timestamptz`, UTC. `created_at` / `updated_at` on every table (trigger-maintained).
- **Tenancy:** every tenant-scoped table has `tenant_id uuid NOT NULL REFERENCES tenant(id)`.
  Global reference data (companies, categories, indices, sources) is **shared** (no `tenant_id`).
- **Soft delete:** `deleted_at timestamptz NULL`. Rows are never hard-deleted (retention goal).
- **Money/ratios:** `numeric` (never float) for prices, amounts, scores.
- **Enums:** modeled as lookup tables or Postgres enums where the set is truly closed.

## Shared vs tenant-scoped

| Shared (global) | Tenant-scoped |
| --- | --- |
| `company`, `company_identifier`, `index`, `index_membership` | `app_user`, `membership` |
| `signal_category` | `watchlist`, `watchlist_item`, `alert` |
| `source`, `ingest_event`, `ingest_run` | `signal`, `signal_evidence`, `signal_score` |
| `historical_snapshot` | `analog_query`, `analog_match` |

> **Design note:** signals are tenant-scoped even though the underlying company and events are
> shared. This lets different tenants run different detector configs / thresholds and see
> different signal sets over identical market data — the multi-tenant core of the product.
> The *evidence events* are shared and immutable; the *interpretation* (signal + score) is per tenant.

## Entities

### tenant
A customer workspace. `slug`, `name`, `plan`, `status`, `settings jsonb`.

### app_user
A person. Belongs to a tenant via `membership` (many-to-many to support future cross-tenant users).
`email` (citext, unique per tenant), `display_name`, `auth_provider`, `role` default at membership level.

### membership
`(tenant_id, user_id)` with `role` enum (`owner`,`admin`,`analyst`,`viewer`). The unit of
authorization. RLS uses the current user's memberships to scope reads/writes.

### company
The master record for a listed entity. Global.
- `name`, `legal_name`, `cin` (MCA Corporate Identity Number, unique), `sector`, `industry`,
  `status` (`active`,`suspended`,`delisted`), `in_universe boolean`.
- Multiple market identifiers live in `company_identifier` (NSE symbol, BSE code, ISIN, etc.)
  because one company maps to several external keys.

### company_identifier
`(company_id, scheme, value)` where `scheme ∈ {nse_symbol, bse_code, isin, mca_cin, diffbot_id, lei}`.
Unique on `(scheme, value)`. This is the join key for every external feed.

### index / index_membership
`index` = Nifty 50, Nifty Next 50, F&O, etc. `index_membership` is point-in-time
(`effective_from`, `effective_to`) so we can answer "was X in Nifty 50 on date D?" — required
for honest historical analogs and for defining `in_universe`.

### source
Registry of external data providers and feeds. `key` (`nse_announcements`, `mca_filings`,
`diffbot_news`, `linkedin_jobs`, …), `kind` (`exchange`,`registry`,`news`,`jobs`,`enrichment`),
`config jsonb`, `enabled`. Detectors and connectors reference sources by `key`.

### ingest_event  *(append-only, shared)*
One normalized inbound datum. The atomic unit of the event-driven pipeline.
- `source_id`, `external_id` (provider's id, for dedupe), `dedupe_key` (unique),
  `company_id` (nullable until resolved), `event_type`, `occurred_at`, `received_at`,
  `raw_uri` (S3 pointer to exact raw payload), `payload jsonb` (normalized),
  `status` (`received`→`normalized`→`processed`|`failed`), `error`.
- **Never updated destructively** except status transitions; the raw payload is immutable.

### ingest_run
One execution of a connector. `source_id`, `started_at`, `finished_at`, `status`,
`events_emitted`, `cursor` (jsonb watermark for incremental pulls), `error`. Operational visibility.

### signal_category  *(shared lookup)*
The pluggable category list (`mean_reversion`, `hiring_spike`, …). `slug`, `name`,
`description`, `detector_key` (which Python detector produces it), `default_weight`,
`is_active`. Adding a category = inserting a row + shipping a detector. No schema change.

### signal  *(tenant-scoped)*
The product's core unit. An evidence-backed observation about a company.
- `tenant_id`, `company_id`, `category_id`, `title`, `summary`, `direction`
  (`up`,`down`,`neutral` — descriptive of the *observation*, NOT a recommendation),
  `observed_at`, `dedupe_key` (unique per tenant — idempotent detection),
  `status` (`candidate`→`scored`→`published`|`suppressed`|`expired`),
  `detector_version`, `metadata jsonb`.
- **Invariant:** a `signal` must have ≥1 `signal_evidence`. Enforced by detector contract +
  a periodic integrity check + FK from evidence (see migration `0004`/`0005`).
- A signal carries **no** target price / rating / action fields. By schema, advice cannot be stored.

### signal_evidence  *(tenant-scoped)*
The traceability link: why this signal exists. `signal_id`, `ingest_event_id` (the source datum),
`artifact_uri` (optional S3 snapshot/screenshot), `excerpt`, `weight`, `evidence_type`
(`filing`,`news`,`job_posting`,`price_series`,`mca_record`,`holding_disclosure`). A signal can
cite many events; an event can support many signals (M:N via this table).

### signal_score  *(tenant-scoped)*
The output of the scoring engine. One **current** row per signal plus history (append).
- `signal_id`, `magnitude` (0–1, how big the move/observation is vs baseline),
  `confidence` (0–1, evidence strength & corroboration), `novelty` (0–1, how unusual vs history),
  `composite` (0–1, weighted blend), `model_version`, `features jsonb`, `is_current bool`.
- Scores are **descriptive intensities**, never expected returns. See guardrails doc.

### historical_snapshot  *(append-only, shared)*
Periodic frozen state of a company's observable metrics (price stats, valuation multiples,
hiring counts, holding patterns) at a point in time. `company_id`, `as_of`, `metrics jsonb`,
`source_run_id`. Powers mean-reversion baselines and the analog engine. Never overwritten.

### analog_query / analog_match  *(tenant-scoped)*
Skeleton for the historical analog engine. `analog_query` captures "find past situations like
signal X / company state Y" with a feature vector + filters. `analog_match` stores ranked past
`historical_snapshot` / `signal` references with a `similarity` score and the explanation. See
[`05-historical-analog-engine.md`](05-historical-analog-engine.md).

### watchlist / watchlist_item  *(tenant-scoped)*
`watchlist` belongs to a user; `watchlist_item` references a `company`. Drives personalized feeds.

### alert  *(tenant-scoped)*
A user's subscription to signal conditions (`category`, `min_composite`, company/watchlist scope,
channel). Generates notifications when matching signals publish. Skeleton in v1.

## Lifecycle summary

```
ingest_event(received) ─▶ (normalized) ─▶ detector ─▶ signal(candidate)
                                                         │  + signal_evidence(≥1)
                                                         ▼
                                              scoring ─▶ signal_score(is_current)
                                                         │
                                                         ▼
                                          signal(published | suppressed)
```

Suppression (not deletion) is how we drop low-signal noise while honoring retention: the row
stays, `status='suppressed'`, and never reaches the published API.

## Indexing strategy (highlights)

- `signal (tenant_id, status, observed_at desc)` — primary feed query.
- `signal (tenant_id, company_id, observed_at desc)` — company timeline.
- `signal (tenant_id, category_id, observed_at desc)` — category feed.
- `signal_score (signal_id) where is_current` — current score lookup.
- `ingest_event (source_id, status)` + unique `(dedupe_key)`.
- `company_identifier (scheme, value)` unique — feed resolution.
- GIN on `signal.metadata`, `ingest_event.payload`, `historical_snapshot.metrics`.
