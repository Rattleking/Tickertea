# 00 — Overview & Principles

## What Tickertea is

Tickertea is an **alternative intelligence platform for public equities**. It continuously
ingests corporate, market, hiring, management, sentiment, and valuation data for a curated
universe of Indian listed companies and surfaces **signals** — interesting, evidence-backed
observations — that a human analyst can act on.

## What Tickertea is NOT

Tickertea **does not**:

- generate buy / sell / hold recommendations
- produce target prices, fair values, or expected returns
- give investment advice or portfolio guidance
- rank companies by "attractiveness as an investment"

It **only** surfaces signals and the evidence behind them. The user interprets and decides.
This is a hard product and engineering constraint, enforced in the scoring engine, the API
layer, and the content pipeline. See [`08-compliance-guardrails.md`](08-compliance-guardrails.md).

## Target universe

- Nifty 50
- Nifty Next 50
- F&O (futures & options) stocks
- ~250 Indian listed companies total

The universe is data-driven (a `companies.in_universe` flag + index membership), not hardcoded,
so it can expand later without schema changes.

## Signal categories (v1)

| Category | Slug | Example observation |
| --- | --- | --- |
| Mean Reversion | `mean_reversion` | Price/valuation N std-devs from its own trailing mean |
| Hiring Spike | `hiring_spike` | Open roles up sharply vs trailing baseline |
| Management Change | `management_change` | CXO / board / KMP appointment or exit |
| Capex Expansion | `capex_expansion` | New plant, capacity, or capex guidance |
| Subsidiary Creation | `subsidiary_creation` | New subsidiary / JV registered (MCA) |
| Narrative Shift | `narrative_shift` | Tone / theme of coverage changes materially |
| News Event | `news_event` | Material disclosed event (filing, order, ruling) |
| Insider Activity | `insider_activity` | Promoter / insider buy-sell disclosures |
| Institutional Flow | `institutional_flow` | FII/DII/MF holding changes, bulk/block deals |

Categories are data rows (`signal_category`), not enums in code, so new categories ship
without a deploy. Each category has a pluggable **detector** (Python) and a **scorer**.

## Core architecture goals

1. **Monolith first** — one deployable Next.js app + a pool of Python workers.
2. **Modular domain design** — clear domain boundaries (`company`, `signal`, `evidence`,
   `scoring`, `ingestion`, `analog`, `watchlist`, `tenant`) with no cross-domain reach-around.
3. **Event-driven ingestion** — sources emit raw events → normalized → detectors → signals.
4. **Horizontal scalability later** — domains are seams along which services can split.
5. **Multi-tenant from day one** — every tenant-scoped row carries `tenant_id`; RLS-ready.
6. **Every signal traceable to source evidence** — a signal with no evidence cannot exist.
7. **Historical retention forever** — raw events, snapshots, and signals are append-only.

## The seven goals as enforced invariants

| Goal | Enforced by |
| --- | --- |
| Monolith first | Single Next.js deploy; workers are stateless consumers |
| Modular domains | `src/domains/*` boundaries; lint rule forbids cross-domain imports except via public `index.ts` |
| Event-driven | `ingest_event` table + queue; detectors are pure functions of events |
| Scale later | Domain seams + stateless workers + Redis/queue between stages |
| Multi-tenant | `tenant_id` NOT NULL on tenant data; Postgres RLS policies |
| Traceability | `signal_evidence` FK required; `signal` has ≥1 evidence (checked) |
| Retention | Append-only `ingest_event`, `historical_snapshot`, soft-delete only |

## Document map

- [`01-system-architecture.md`](01-system-architecture.md) — components, data flow, deployment
- [`02-data-model.md`](02-data-model.md) — entities, relationships, lifecycle
- [`03-ingestion-framework.md`](03-ingestion-framework.md) — sources → events → signals
- [`04-signal-scoring-engine.md`](04-signal-scoring-engine.md) — scoring model & invariants
- [`05-historical-analog-engine.md`](05-historical-analog-engine.md) — analog search skeleton
- [`06-api-contracts.md`](06-api-contracts.md) — REST contracts & types
- [`07-multi-tenancy.md`](07-multi-tenancy.md) — tenancy model & isolation
- [`08-compliance-guardrails.md`](08-compliance-guardrails.md) — the "no advice" boundary
- [`09-local-development.md`](09-local-development.md) — running it locally
