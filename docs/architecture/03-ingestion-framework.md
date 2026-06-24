# 03 — Ingestion Framework

The ingestion framework turns heterogeneous external data into a uniform, append-only stream of
`ingest_event` rows that detectors can consume. It lives in `workers/tickertea/ingestion/`.

## Pipeline stages

```
 Connector ──▶ RawStore(S3) ──▶ Normalizer ──▶ ingest_event ──▶ Queue ──▶ Detectors
   pull/recv     immutable        typed map      (received)      (redis)    (per category)
```

### 1. Connector (`connectors/`)
A connector knows how to talk to one source. It implements:

```python
class Connector(Protocol):
    source_key: str
    def discover(self, cursor: Cursor) -> Iterable[RawItem]: ...
    # yields raw items since the cursor watermark; pure I/O, no business logic
```

Each connector run creates an `ingest_run` row and advances a `cursor` (jsonb watermark) for
incremental, idempotent pulls. Connectors are scheduled (cron-like) or webhook-triggered.

Planned connectors: `nse_announcements`, `bse_announcements`, `mca_filings`,
`diffbot_news`, `diffbot_org`, `linkedin_jobs`, `news_rss`.

### 2. RawStore
Every raw item is written verbatim to S3 at `raw/{source_key}/{yyyy}/{mm}/{dd}/{uuid}` BEFORE
anything else. The S3 URI becomes `ingest_event.raw_uri`. This guarantees we can always re-derive
everything (retention + traceability) and re-run normalizers/detectors against history.

### 3. Normalizer (`normalizers/`)
Maps a source-specific raw item into the canonical envelope and resolves the company:

```python
@dataclass
class NormalizedEvent:
    source_key: str
    external_id: str          # provider id, for dedupe
    event_type: str           # e.g. "board_meeting", "job_posting", "bulk_deal"
    occurred_at: datetime
    company_ref: CompanyRef   # (scheme, value) → resolved to company_id
    payload: dict             # normalized, source-agnostic
    dedupe_key: str           # deterministic hash(source_key, external_id, ...)
```

Company resolution uses `company_identifier (scheme, value)`. Unresolved events are stored with
`company_id = NULL` and `status='received'` for later backfill — never dropped.

### 4. Persist → `ingest_event`
Insert with `ON CONFLICT (dedupe_key) DO NOTHING` for idempotency. Status `received` →
`normalized`. Then enqueue `event_id` to the Redis stream `ingest.events`.

### 5. Queue & detectors
Detector workers (`workers/tickertea/detect/`) consume `ingest.events`. See
[`04-signal-scoring-engine.md`](04-signal-scoring-engine.md) for the detector → signal → score path.

## Idempotency, replay, backfill

- **dedupe_key** makes ingestion exactly-once at the event level.
- **Replay:** re-running a detector against historical `ingest_event` rows is a first-class
  operation (`detector_version` bump). Old signals are not deleted; new ones are written and
  superseded scores marked `is_current=false`.
- **Backfill:** late company resolution re-emits affected events to the queue.

## Failure handling

| Failure | Behavior |
| --- | --- |
| Connector error | `ingest_run.status='failed'`, error captured, cursor not advanced |
| Normalizer error | `ingest_event.status='failed'`, raw payload retained, alert raised |
| Detector error | retried N times, then event flagged; never silently dropped |

## Adding a new source — checklist

1. Insert a `source` row (`db/seed/` or admin).
2. Implement `connectors/<source>.py` and `normalizers/<source>.py`.
3. Register in `workers/tickertea/ingestion/registry.py`.
4. (If it should produce a new signal type) add a `signal_category` + detector — see scoring doc.

The framework's contract is: **connectors and normalizers never decide what is interesting.**
That is the detectors' and scoring engine's job. This separation keeps ingestion dumb, replayable,
and reusable across many signal categories.
