# 07 — Multi-Tenancy

Tickertea is **multi-tenant capable from day one**. The schema, the API, and the data-access layer
all assume a tenant context, even while the product launches with a single tenant.

## Model: shared-schema, row-level isolation

- **One database, one schema.** Tenant-scoped tables carry `tenant_id uuid NOT NULL`.
- **Isolation via Postgres Row-Level Security (RLS).** Policies restrict every tenant-scoped
  table to rows where `tenant_id = current_setting('app.tenant_id')::uuid`.
- **Shared reference data** (companies, identifiers, indices, sources, ingest events, snapshots,
  signal categories) has **no** `tenant_id` and is readable by all tenants. It represents market
  reality, which is identical for everyone.

This balances isolation with the cost of re-ingesting identical market data per tenant (which we
explicitly avoid — see data model design note).

## Request → tenant context

```
session → membership lookup → tenant_id
  ↓
db.withTenant(tenant_id, async (tx) => {
    SET LOCAL app.tenant_id = $tenant_id;   -- transaction-scoped GUC
    -- all queries now RLS-filtered to this tenant
})
```

The `tenant_id` is **always** derived from the authenticated session/membership, never from
client input. `src/lib/db/tenant-context.ts` provides `withTenant()` and is the only sanctioned
way to open a tenant-scoped transaction. Workers set the GUC explicitly per job.

> **Auth bootstrap (chicken-and-egg):** `membership` is itself RLS-protected, so the *initial*
> lookup of "which tenants does this authenticated user belong to?" cannot run under a tenant
> context that doesn't exist yet. That single lookup runs through a narrow, audited system path
> (the `tickertea_admin` / BYPASSRLS connection) keyed strictly by the verified `user_id` from the
> session token. Once a `tenant_id` is chosen, every subsequent query uses `withTenant()` and is
> fully RLS-scoped. This is the only place the app reads across tenants, and it reads only the
> caller's own memberships.

## RLS policy shape (see migration `0011`)

```sql
ALTER TABLE signal ENABLE ROW LEVEL SECURITY;
CREATE POLICY signal_tenant_isolation ON signal
  USING (tenant_id = current_tenant_id())
  WITH CHECK (tenant_id = current_tenant_id());
-- repeated for: signal_evidence, signal_score, scoring_config, watchlist, watchlist_item,
--               alert, analog_query, analog_match, membership; plus app_user (via membership)
--               and tenant (self). current_tenant_id() reads the app.tenant_id GUC.
```

**Role model (portable — works on self-managed Postgres *and* managed providers like Neon
without superuser):**

- The application connects as the **non-owner `tickertea_app` role**, to which RLS policies
  **always apply**. This is the enforcement boundary.
- Migrations and trusted workers run as the **table-owner role** (`tickertea_admin` locally,
  the Neon project owner on Neon). By the standard Postgres rule, the table owner is **not**
  subject to RLS — which is exactly the trusted cross-tenant path we want for migrations and
  shared-data writes.
- We deliberately do **not** use `BYPASSRLS` or `FORCE ROW LEVEL SECURITY`: both require a real
  superuser, which managed providers don't grant. The owner-bypass + non-owner-enforced model
  gives the same isolation guarantee without it. (Verified on Neon: as `tickertea_app`, the demo
  tenant sees its rows, any other tenant sees zero, and an unset context fails closed.)

## Tenant-scoped vs shared — quick reference

| Shared (no RLS) | Tenant-scoped (RLS) |
| --- | --- |
| company, company_identifier | signal, signal_evidence, signal_score |
| index, index_membership | watchlist, watchlist_item, alert |
| source, ingest_run, ingest_event | analog_query, analog_match |
| signal_category, historical_snapshot | app_user, membership |

## Per-tenant configuration

Tenant-specific behavior (scoring weights, publish thresholds, enabled categories, feature flags)
lives in `tenant.settings jsonb` and a `scoring_config` table keyed by `tenant_id`. The same raw
events therefore yield tenant-specific signal sets — the multi-tenant product surface.

## Scaling path

1. v1: single tenant, RLS active (proves isolation under real load).
2. Onboard more tenants: pure data operation, no schema change.
3. If a large tenant needs isolation guarantees: move it to a dedicated database using the same
   schema; the data-access layer's connection routing is the only change.
