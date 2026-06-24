"""Persistence for the write path: ingest_run / ingest_event / signal / evidence / score.

The DB schema (db/migrations) is the contract. These functions speak SQL directly and
keep field names aligned with the columns. All writes run as the trusted role; tenant
scoping is applied explicitly (tenant_id stamped on every tenant-scoped row).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import UUID

import psycopg

from tickertea.common.types import IngestEvent, NormalizedEvent
from tickertea.scoring.engine import ScoreResult, ScoringConfig


class UnknownSourceError(RuntimeError):
    pass


class UnknownCategoryError(RuntimeError):
    pass


# --- sources & runs -----------------------------------------------------------------
def get_source_id(conn: psycopg.Connection, source_key: str) -> UUID:
    row = conn.execute("SELECT id FROM source WHERE key = %s", (source_key,)).fetchone()
    if not row:
        raise UnknownSourceError(f"source '{source_key}' not registered (see db/seed/04)")
    return row["id"]


def latest_cursor(conn: psycopg.Connection, source_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        """SELECT cursor FROM ingest_run
           WHERE source_id = %s AND status = 'succeeded'
           ORDER BY started_at DESC LIMIT 1""",
        (source_id,),
    ).fetchone()
    return dict(row["cursor"]) if row and row["cursor"] else {}


def start_run(conn: psycopg.Connection, source_id: UUID, cursor: dict[str, Any]) -> UUID:
    row = conn.execute(
        """INSERT INTO ingest_run (source_id, status, cursor)
           VALUES (%s, 'running', %s) RETURNING id""",
        (source_id, json.dumps(cursor)),
    ).fetchone()
    return row["id"]


def finish_run(
    conn: psycopg.Connection,
    run_id: UUID,
    *,
    status: str,
    events_emitted: int,
    cursor: dict[str, Any],
    error: str | None = None,
) -> None:
    conn.execute(
        """UPDATE ingest_run
              SET status = %s, events_emitted = %s, cursor = %s,
                  error = %s, finished_at = now()
            WHERE id = %s""",
        (status, events_emitted, json.dumps(cursor), error, run_id),
    )


# --- company resolution -------------------------------------------------------------
def resolve_company_id(conn: psycopg.Connection, scheme: str, value: str) -> UUID | None:
    row = conn.execute(
        "SELECT company_id FROM company_identifier WHERE scheme = %s AND value = %s",
        (scheme, value),
    ).fetchone()
    return row["company_id"] if row else None


# --- ingest events ------------------------------------------------------------------
def insert_ingest_event(
    conn: psycopg.Connection,
    *,
    source_id: UUID,
    run_id: UUID,
    company_id: UUID | None,
    event: NormalizedEvent,
    raw_uri: str,
) -> tuple[UUID, bool]:
    """Insert one event idempotently. Returns (event_id, inserted)."""
    row = conn.execute(
        """INSERT INTO ingest_event
             (source_id, run_id, company_id, external_id, dedupe_key,
              event_type, raw_uri, payload, status, occurred_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'received', %s)
           ON CONFLICT (dedupe_key) DO NOTHING
           RETURNING id""",
        (
            source_id, run_id, company_id, event.external_id, event.dedupe_key,
            event.event_type, raw_uri, json.dumps(event.payload, default=str),
            event.occurred_at,
        ),
    ).fetchone()
    if row:
        return row["id"], True
    existing = conn.execute(
        "SELECT id FROM ingest_event WHERE dedupe_key = %s", (event.dedupe_key,)
    ).fetchone()
    return existing["id"], False


def fetch_unprocessed_events(
    conn: psycopg.Connection,
    *,
    limit: int = 500,
    event_types: Sequence[str] | None = None,
) -> list[IngestEvent]:
    sql = [
        """SELECT e.id, s.key AS source_key, e.company_id, e.event_type,
                  e.occurred_at, e.payload, e.raw_uri
             FROM ingest_event e JOIN source s ON s.id = e.source_id
            WHERE e.status = 'received'"""
    ]
    params: list[Any] = []
    if event_types:
        sql.append("AND e.event_type = ANY(%s)")
        params.append(list(event_types))
    sql.append("ORDER BY e.received_at ASC LIMIT %s")
    params.append(limit)
    rows = conn.execute(" ".join(sql), params).fetchall()
    return [
        IngestEvent(
            id=r["id"],
            source_key=r["source_key"],
            company_id=r["company_id"],
            event_type=r["event_type"],
            occurred_at=r["occurred_at"],
            payload=dict(r["payload"]),
            raw_uri=r["raw_uri"],
        )
        for r in rows
    ]


def mark_event(
    conn: psycopg.Connection, event_id: UUID, status: str, error: str | None = None
) -> None:
    conn.execute(
        "UPDATE ingest_event SET status = %s, error = %s, processed_at = now() WHERE id = %s",
        (status, error, event_id),
    )


# --- tenants, config, categories ----------------------------------------------------
def active_tenants(conn: psycopg.Connection) -> list[UUID]:
    rows = conn.execute(
        "SELECT id FROM tenant WHERE status = 'active' ORDER BY created_at"
    ).fetchall()
    return [r["id"] for r in rows]


def load_scoring_config(conn: psycopg.Connection, tenant_id: UUID) -> ScoringConfig:
    row = conn.execute(
        """SELECT weight_magnitude, weight_confidence, weight_novelty, publish_threshold
             FROM scoring_config WHERE tenant_id = %s""",
        (tenant_id,),
    ).fetchone()
    if not row:
        return ScoringConfig()
    return ScoringConfig(
        weight_magnitude=float(row["weight_magnitude"]),
        weight_confidence=float(row["weight_confidence"]),
        weight_novelty=float(row["weight_novelty"]),
        publish_threshold=float(row["publish_threshold"]),
    )


def category_by_slug(conn: psycopg.Connection, slug: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, default_weight FROM signal_category WHERE slug = %s AND is_active",
        (slug,),
    ).fetchone()
    if not row:
        raise UnknownCategoryError(f"signal_category '{slug}' not found / inactive")
    return {"id": row["id"], "default_weight": float(row["default_weight"])}


# --- signals (tenant-scoped) --------------------------------------------------------
def persist_scored_signal(
    conn: psycopg.Connection,
    *,
    tenant_id: UUID,
    category_id: UUID,
    candidate: Any,  # CandidateSignal
    result: ScoreResult,
    detector_version: str,
) -> UUID | None:
    """Insert a signal + its evidence + current score, idempotently per (tenant, dedupe).

    Returns the new signal id, or None if a signal with this dedupe_key already exists.
    Status reflects the scoring outcome; below-threshold and guardrail-suppressed signals
    are RETAINED (never served), preserving the audit trail.
    """
    if result.suppressed_reason:
        status = "suppressed"
    elif result.publish:
        status = "published"
    else:
        status = "scored"

    observed_at = candidate.observed_at or datetime.now(timezone.utc)
    metadata = {"detector_version": detector_version, "features": candidate.features}
    if result.suppressed_reason:
        metadata["suppressed_reason"] = result.suppressed_reason

    sig = conn.execute(
        """INSERT INTO signal
             (tenant_id, company_id, category_id, title, summary, direction,
              status, dedupe_key, detector_version, metadata, observed_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (tenant_id, dedupe_key) DO NOTHING
           RETURNING id""",
        (
            tenant_id, candidate.company_id, category_id, candidate.title,
            candidate.summary, candidate.direction, status, candidate.dedupe_key,
            detector_version, json.dumps(metadata, default=str), observed_at,
        ),
    ).fetchone()
    if not sig:
        return None  # already generated this signal for this tenant
    signal_id = sig["id"]

    for ev in candidate.evidence:
        conn.execute(
            """INSERT INTO signal_evidence
                 (tenant_id, signal_id, ingest_event_id, evidence_type,
                  artifact_uri, excerpt, weight)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (signal_id, ingest_event_id) DO NOTHING""",
            (
                tenant_id, signal_id, ev.ingest_event_id, ev.evidence_type,
                ev.artifact_uri, ev.excerpt, ev.weight,
            ),
        )

    score = result.score
    conn.execute(
        """INSERT INTO signal_score
             (tenant_id, signal_id, magnitude, confidence, novelty, composite,
              model_version, features, is_current)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)""",
        (
            tenant_id, signal_id, score.magnitude, score.confidence, score.novelty,
            score.composite, score.model_version, json.dumps(score.features, default=str),
        ),
    )
    return signal_id


# --- snapshots (shared; powers baselines + analogs) ---------------------------------
def upsert_snapshot(
    conn: psycopg.Connection,
    *,
    company_id: UUID,
    as_of: datetime,
    metrics: dict[str, Any],
    source_run_id: UUID | None = None,
) -> None:
    conn.execute(
        """INSERT INTO historical_snapshot (company_id, source_run_id, as_of, metrics)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (company_id, as_of)
           DO UPDATE SET metrics = historical_snapshot.metrics || EXCLUDED.metrics""",
        (company_id, source_run_id, as_of, json.dumps(metrics, default=str)),
    )
