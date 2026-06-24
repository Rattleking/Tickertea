# 01 — System Architecture

## High-level component view

```
                         ┌──────────────────────────────────────────────┐
                         │              External Data Sources             │
                         │  NSE · BSE · MCA · Diffbot · LinkedIn · News    │
                         └───────────────┬──────────────────────────────┘
                                         │ (poll / webhook / scrape)
                                         ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                          Python Ingestion Workers                          │
   │  Connector → RawPayload(S3) → Normalizer → ingest_event (Postgres)         │
   └───────────────┬───────────────────────────────────────────────────────────┘
                   │  enqueue event_id
                   ▼
            ┌───────────────┐        ┌───────────────────────────────────────────┐
            │  Redis Queue  │ ─────▶ │            Python Detector Workers          │
            │ (streams)     │        │  per-category detectors → candidate signals │
            └───────────────┘        └───────────────┬───────────────────────────┘
                                                      │ writes signal + evidence
                                                      ▼
                            ┌───────────────────────────────────────────┐
                            │      Signal Scoring Engine (Python)         │
                            │  feature build → score → confidence → store │
                            └───────────────┬───────────────────────────┘
                                            ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                              PostgreSQL (RLS)                               │
   │  tenants · companies · signals · evidence · scores · snapshots · watchlists│
   └───────────────┬───────────────────────────────────────────────────────────┘
                   │ read (cached via Redis)
                   ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │                      Next.js 15 App (monolith)                             │
   │  App Router UI (Tailwind + shadcn/ui)  +  /api/* route handlers            │
   │  domain modules in src/domains/*  ·  S3 for evidence artifacts             │
   └───────────────────────────────────────────────────────────────────────────┘
```

## Deployable units

| Unit | Runtime | Scales | Responsibility |
| --- | --- | --- | --- |
| `web` | Next.js 15 (Node) | horizontally (stateless) | UI + API + read models |
| `worker-ingest` | Python | by source throughput | connectors, normalization |
| `worker-detect` | Python | by event volume | category detectors |
| `worker-score` | Python | by signal volume | scoring engine |
| `postgres` | PostgreSQL 16 | read replicas later | system of record |
| `redis` | Redis 7 | cluster later | queue + cache |
| `objectstore` | S3-compatible | managed | raw payloads + evidence artifacts |

"Monolith first" = **one** application deploy (`web`). The workers are a small, stateless
fleet sharing the same database and the same domain libraries. They are not microservices;
they are background processors of the same modular monolith.

## Data flow (event-driven ingestion)

1. **Connect** — an ingestion connector pulls/receives data from a source on a schedule or webhook.
2. **Persist raw** — the exact raw payload is stored in S3 (`raw/{source}/{yyyy}/{mm}/{dd}/{uuid}`)
   and referenced by a row in `ingest_event` with `status='received'`. Nothing is discarded.
3. **Normalize** — a normalizer maps the raw payload to a typed, source-agnostic shape and
   resolves the subject `company_id`. Sets `status='normalized'`.
4. **Detect** — the event is enqueued; category detectors subscribe. A detector may emit a
   **candidate signal** with one or more `signal_evidence` rows pointing back at the event(s).
5. **Score** — the scoring engine builds features, computes a `magnitude`/`confidence`/`novelty`
   composite, writes a `signal_score`, and transitions the signal to `published` (or `suppressed`).
6. **Serve** — the Next.js API reads published signals (Redis-cached) for the UI and external API.

Each arrow is idempotent and keyed by a deterministic `dedupe_key` so replays are safe — a
requirement for "retention forever" + "every signal traceable".

## Modular domain design

```
src/domains/
  tenant/      tenancy, users, membership, RLS context helpers
  company/     company master, identifiers, index membership, universe
  ingestion/   event read models, source registry (write path is in workers/)
  signal/      signal lifecycle, categories, query/read models
  evidence/    evidence records + artifact (S3) references
  scoring/     score read models + scoring config (engine lives in workers/)
  analog/      historical analog search read models
  watchlist/   user watchlists & alerts
```

**Rule:** a domain may only import another domain through its public `index.ts` barrel.
A lint boundary (`eslint-plugin-boundaries` or `dependency-cruiser`) enforces this so the
seams stay clean for a later service split. Cross-cutting concerns (db client, logging,
auth, redis, s3) live in `src/lib/*`.

Python workers mirror the same domain vocabulary under `workers/tickertea/<domain>/` and
**share the database schema as the contract** — they do not import TypeScript.

## Why these boundaries

- The **write path** (ingestion → detection → scoring) is CPU/NLP heavy and bursty → Python workers.
- The **read path** (signals, evidence, watchlists) is latency sensitive → Next.js + Redis cache.
- The database is the single contract between them, which keeps the monolith honest and makes
  the eventual extraction of, say, `scoring` into its own service a mechanical change.

## Observability & ops (v1 minimum)

- Structured JSON logs with `tenant_id`, `event_id`, `signal_id`, `trace_id` on every line.
- `ingest_event.status` + `ingest_run` table give an at-a-glance pipeline health view.
- Dead-letter: events that fail detection/scoring N times move to `status='failed'` with the error,
  never silently dropped (retention requirement).
