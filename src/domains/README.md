# Domain modules

Each subdirectory is a bounded domain. **A domain may only be imported through its
`index.ts` barrel** — deep imports into another domain's internals are forbidden and
enforced by `.dependency-cruiser.cjs`. This keeps the seams clean so a domain can later
be extracted into its own service (architecture goal #4).

| Domain | Responsibility | Write path |
| --- | --- | --- |
| `tenant` | tenancy, users, membership, RLS context helpers | app |
| `company` | company master, identifiers, index membership, universe | ingestion (workers) |
| `ingestion` | event read models, source registry | **workers** |
| `signal` | signal lifecycle, query/read models | workers (detect) |
| `evidence` | evidence records + S3 artifact references | workers (detect) |
| `scoring` | score read models + scoring config | **workers** |
| `analog` | historical analog search read models | workers |
| `watchlist` | user watchlists & alerts | app |

Cross-cutting infrastructure (db client, tenant context, auth, http, redis, s3) lives in
`src/lib/*`, not in any domain.

The `signal` domain is the fully worked reference implementation (`repository.ts` →
`service.ts` → `index.ts`, consumed by `src/app/api/v1/signals/route.ts`). Other domains
follow the same shape.
