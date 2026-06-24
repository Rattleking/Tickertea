# Tickertea — Entity Relationship Diagram

Rendered with Mermaid. View in any Mermaid-capable viewer (GitHub, VS Code Mermaid preview).
Legend: shared/global entities are not tenant-scoped; everything referencing `tenant` is
tenant-scoped.

```mermaid
erDiagram
    tenant ||--o{ membership : has
    app_user ||--o{ membership : "joins via"
    tenant ||--o{ watchlist : owns
    app_user ||--o{ watchlist : creates
    watchlist ||--o{ watchlist_item : contains
    company ||--o{ watchlist_item : "referenced by"
    tenant ||--o{ alert : owns
    app_user ||--o{ alert : creates

    company ||--o{ company_identifier : "identified by"
    index ||--o{ index_membership : "lists"
    company ||--o{ index_membership : "member of"

    source ||--o{ ingest_run : runs
    source ||--o{ ingest_event : emits
    company ||--o{ ingest_event : "subject of"

    signal_category ||--o{ signal : classifies
    tenant ||--o{ signal : owns
    company ||--o{ signal : about
    signal ||--o{ signal_evidence : "supported by"
    ingest_event ||--o{ signal_evidence : "cited as"
    signal ||--o{ signal_score : "scored by"

    company ||--o{ historical_snapshot : "snapshotted"
    ingest_run ||--o{ historical_snapshot : produces

    tenant ||--o{ analog_query : owns
    signal ||--o{ analog_query : "seeds"
    analog_query ||--o{ analog_match : returns
    historical_snapshot ||--o{ analog_match : "matched as"

    tenant {
        uuid id PK
        text slug UK
        text name
        text plan
        text status
        jsonb settings
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }
    app_user {
        uuid id PK
        citext email
        text display_name
        text auth_provider
        timestamptz created_at
    }
    membership {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        text role
        timestamptz created_at
    }
    company {
        uuid id PK
        text name
        text legal_name
        text cin UK
        text sector
        text industry
        text status
        boolean in_universe
        timestamptz created_at
    }
    company_identifier {
        uuid id PK
        uuid company_id FK
        text scheme
        text value
    }
    index {
        uuid id PK
        text code UK
        text name
    }
    index_membership {
        uuid id PK
        uuid index_id FK
        uuid company_id FK
        date effective_from
        date effective_to
    }
    source {
        uuid id PK
        text key UK
        text kind
        jsonb config
        boolean enabled
    }
    ingest_run {
        uuid id PK
        uuid source_id FK
        text status
        jsonb cursor
        int events_emitted
        timestamptz started_at
        timestamptz finished_at
    }
    ingest_event {
        uuid id PK
        uuid source_id FK
        uuid company_id FK
        text external_id
        text dedupe_key UK
        text event_type
        text raw_uri
        jsonb payload
        text status
        timestamptz occurred_at
        timestamptz received_at
    }
    signal_category {
        uuid id PK
        text slug UK
        text name
        text detector_key
        numeric default_weight
        boolean is_active
    }
    signal {
        uuid id PK
        uuid tenant_id FK
        uuid company_id FK
        uuid category_id FK
        text title
        text summary
        text direction
        text status
        text dedupe_key
        text detector_version
        jsonb metadata
        timestamptz observed_at
        timestamptz created_at
    }
    signal_evidence {
        uuid id PK
        uuid tenant_id FK
        uuid signal_id FK
        uuid ingest_event_id FK
        text evidence_type
        text artifact_uri
        text excerpt
        numeric weight
    }
    signal_score {
        uuid id PK
        uuid tenant_id FK
        uuid signal_id FK
        numeric magnitude
        numeric confidence
        numeric novelty
        numeric composite
        text model_version
        jsonb features
        boolean is_current
        timestamptz created_at
    }
    historical_snapshot {
        uuid id PK
        uuid company_id FK
        uuid source_run_id FK
        timestamptz as_of
        jsonb metrics
    }
    analog_query {
        uuid id PK
        uuid tenant_id FK
        uuid signal_id FK
        jsonb feature_vector
        jsonb filters
        timestamptz created_at
    }
    analog_match {
        uuid id PK
        uuid tenant_id FK
        uuid analog_query_id FK
        uuid snapshot_id FK
        numeric similarity
        jsonb explanation
    }
    watchlist {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        text name
    }
    watchlist_item {
        uuid id PK
        uuid watchlist_id FK
        uuid company_id FK
    }
    alert {
        uuid id PK
        uuid tenant_id FK
        uuid user_id FK
        uuid category_id FK
        numeric min_composite
        text channel
        boolean is_active
    }
```

## Reading the diagram

- **Shared spine:** `company` ← `company_identifier` / `index_membership` / `ingest_event` /
  `historical_snapshot`. This is the market reality, identical for all tenants.
- **Tenant interpretation:** `signal` → `signal_evidence` → `signal_score`. Same evidence,
  per-tenant signals and scores.
- **Traceability path:** `signal_score` → `signal` → `signal_evidence` → `ingest_event` →
  `raw_uri` (S3). Any score traces all the way back to an immutable raw payload.
