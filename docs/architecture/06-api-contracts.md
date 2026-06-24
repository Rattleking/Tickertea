# 06 — API Contracts

REST over the Next.js App Router (`src/app/api/*`). Contracts are defined once as **Zod schemas**
in `packages/contracts/` and shared by the API handlers (validation) and the frontend (types).
An OpenAPI document is generated from the Zod schemas (`packages/contracts/openapi.ts`).

## Conventions

- Base path: `/api/v1`.
- Auth: bearer session token; tenant resolved from the session (never from the request body).
- All list endpoints: cursor pagination `?cursor=&limit=` → `{ data, next_cursor }`.
- All times ISO-8601 UTC. All money/score values are numbers in documented ranges.
- Errors: `{ error: { code, message, details? } }` with appropriate HTTP status.
- **Guardrail:** no endpoint accepts or returns recommendation/target-price/return fields.

## Resources

### Companies
```
GET  /api/v1/companies?index=&sector=&in_universe=&q=&cursor=&limit=
GET  /api/v1/companies/{id}
GET  /api/v1/companies/{id}/signals?category=&status=published&cursor=
GET  /api/v1/companies/{id}/snapshots?as_of_from=&as_of_to=
```

### Signals  (the core read model)
```
GET  /api/v1/signals
       ?company_id=&category=&direction=&min_composite=
       &observed_from=&observed_to=&status=published&cursor=&limit=
GET  /api/v1/signals/{id}            // signal + current score + categories
GET  /api/v1/signals/{id}/evidence   // full evidence chain → ingest_event → raw_uri
GET  /api/v1/signals/{id}/scores     // score history (audit)
```

`Signal` response shape (abridged):
```jsonc
{
  "id": "uuid",
  "company": { "id": "uuid", "name": "…", "nse_symbol": "…" },
  "category": { "slug": "hiring_spike", "name": "Hiring Spike" },
  "title": "Open engineering roles up 3.2σ vs trailing 90d",
  "summary": "…",
  "direction": "up",            // describes the observation; NOT advice
  "observed_at": "2026-06-20T…",
  "status": "published",
  "score": {                    // descriptive intensities in [0,1], NOT expected return
    "magnitude": 0.82, "confidence": 0.71, "novelty": 0.64, "composite": 0.74,
    "model_version": "score-1.0.0"
  },
  "evidence_count": 3,
  "disclaimer": "Tickertea surfaces signals, not investment advice."
}
```

### Signal categories
```
GET  /api/v1/categories            // active signal categories + descriptions
```

### Watchlists
```
GET    /api/v1/watchlists
POST   /api/v1/watchlists                 { name }
GET    /api/v1/watchlists/{id}
POST   /api/v1/watchlists/{id}/items      { company_id }
DELETE /api/v1/watchlists/{id}/items/{itemId}
GET    /api/v1/watchlists/{id}/feed       // signals for the watchlist's companies
```

### Alerts (skeleton)
```
GET    /api/v1/alerts
POST   /api/v1/alerts        { category?, watchlist_id?, company_id?, min_composite, channel }
PATCH  /api/v1/alerts/{id}   { is_active, min_composite }
DELETE /api/v1/alerts/{id}
```

### Historical analogs (skeleton)
```
POST /api/v1/analogs/search
   { seed: { signal_id } | { company_id, as_of }, filters?, k? }
   → { query_id, matches: [{ snapshot_id, company, as_of, similarity, explanation }] }
```

### Admin / internal (service-token only, not public)
```
GET  /api/v1/admin/ingest/runs           // pipeline health
GET  /api/v1/admin/ingest/events?status= // event inspection
POST /api/v1/admin/detectors/replay      { category, from, to }   // re-run detection
```

## Contract location & generation

```
packages/contracts/
  src/
    common.ts        // pagination, error, id, timestamp primitives
    company.ts       // CompanySchema, CompanyListQuery
    signal.ts        // SignalSchema, SignalScoreSchema, SignalListQuery
    category.ts
    watchlist.ts
    alert.ts
    analog.ts
    index.ts         // re-exports + ContractRegistry
  openapi.ts         // builds OpenAPI 3.1 doc from the Zod registry
```

The API route handlers import these schemas to validate input and serialize output; the frontend
imports the inferred TypeScript types. One definition, no drift.
