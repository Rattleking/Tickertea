# 09 — Local Development

## Prerequisites

- Node.js 20+ and pnpm
- Python 3.12+ and uv (or venv + pip)
- Docker (for Postgres, Redis, MinIO) or local installs
- PostgreSQL 16 with the `pgcrypto` and `citext` extensions available

## Services

```bash
# from repo root
docker compose up -d postgres redis minio   # see infra/docker-compose.yml (to be added)
```

Defaults (override via `.env`):

```
DATABASE_URL=postgres://tickertea_app:tickertea@localhost:5432/tickertea
DATABASE_ADMIN_URL=postgres://tickertea_admin:tickertea@localhost:5432/tickertea
REDIS_URL=redis://localhost:6379
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=tickertea-raw
CLAUDE_API_KEY=...
OPENAI_API_KEY=...
```

> The app connects as `tickertea_app` (RLS enforced). Migrations and trusted workers use
> `tickertea_admin` (BYPASSRLS). See [`07-multi-tenancy.md`](07-multi-tenancy.md).

## Database setup

```bash
# Apply migrations in numeric order (use your runner of choice; raw psql shown)
for f in db/migrations/*.sql; do psql "$DATABASE_ADMIN_URL" -f "$f"; done

# Load seed data
for f in db/seed/*.sql; do psql "$DATABASE_ADMIN_URL" -f "$f"; done
```

A migration runner (`node-pg-migrate` or `dbmate`) can be wired later; the SQL files are written
to be runner-agnostic and ordered by filename.

## App

```bash
pnpm install
pnpm dev            # Next.js 15 on http://localhost:3000
```

## Workers

```bash
cd workers
uv sync                       # or: python -m venv .venv && pip install -e .
python -m tickertea.cli ingest --source nse_announcements
python -m tickertea.cli detect --once
python -m tickertea.cli score --once
```

## Tests

```bash
pnpm test           # contracts + domain unit tests
cd workers && pytest # ingestion, detectors, scoring, guardrail tests
```

## Make targets (planned)

```
make db.reset       # drop, migrate, seed
make dev            # services + app + workers
make check          # lint + typecheck + tests + domain-boundary lint
```
