# Tickertea Workers

Python workers for the write path: ingestion, detection, scoring, and historical analogs.
They share the **database schema as the contract** with the Next.js app and never import
TypeScript. See `docs/architecture/03`, `04`, and `05`.

```
tickertea/
  common/        shared types, db, redis, s3, settings
  ingestion/     connectors + normalizers -> ingest_event   (architecture goal #3)
    connectors/  one module per source (NSE, BSE, MCA, Diffbot, LinkedIn, news)
    normalizers/ one module per source -> canonical NormalizedEvent
    registry.py  source_key -> (connector, normalizer)
  detect/        per-category detectors -> candidate signals (+ evidence)
    detectors/   one module per signal_category
    registry.py  category_slug -> Detector
  scoring/       three-component descriptive scorer + advice-language guardrail
  analog/        historical analog engine skeleton (features + search)
  cli.py         `tickertea ingest|detect|score|analog` entrypoints
```

## Pipeline

```
ingest  -> connector pulls -> raw to S3 -> normalize -> ingest_event (received)
detect  -> consume events -> detectors emit candidate signals + evidence
score   -> build features -> magnitude/confidence/novelty/composite -> guardrail -> publish|suppress
analog  -> build feature vector -> similarity search over historical_snapshot
```

## Run

```bash
uv sync
tickertea ingest --source nse_announcements
tickertea detect --once
tickertea score --once
pytest
```
