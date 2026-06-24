"""Pipeline orchestration: the real bodies behind the `tickertea` CLI stages.

    ingest  : connector.discover -> raw to S3 -> normalize -> resolve company -> ingest_event
    detect  : unprocessed ingest_events -> detectors -> scoring engine -> signal (+evidence+score)
    rescore : recompute the current score for signals missing one (maintenance/repair)

Detection and scoring run in one pass: a signal is only valid with a score and >=1 piece
of evidence (the scoring engine enforces the evidence invariant), so producing a scored,
persisted signal is the natural unit of work. Signals are tenant-scoped, so each candidate
fans out across active tenants using that tenant's scoring_config.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import UUID

from tickertea.common import repository as repo
from tickertea.common.db import connect
from tickertea.common.rawstore import get_rawstore
from tickertea.common.types import CandidateSignal, EvidenceRef
from tickertea.detect.base import Detector
from tickertea.detect.context import PgDetectorContext
from tickertea.detect.registry import all_detectors
from tickertea.ingestion.base import Cursor
from tickertea.ingestion.registry import get_connector, get_normalizer
from tickertea.scoring.engine import ScoringEngine

logger = logging.getLogger(__name__)


@dataclass
class IngestSummary:
    source_key: str
    fetched: int
    inserted: int
    run_id: UUID


@dataclass
class DetectSummary:
    events_processed: int
    signals_published: int
    signals_total: int
    events_failed: int = 0


def run_ingest(source_key: str) -> IngestSummary:
    """Pull from one source, persist raw + normalized events, advance the cursor."""
    connector = get_connector(source_key)
    normalizer = get_normalizer(source_key)
    rawstore = get_rawstore()
    conn = connect()
    try:
        source_id = repo.get_source_id(conn, source_key)
        cursor = Cursor(repo.latest_cursor(conn, source_id))
        run_id = repo.start_run(conn, source_id, cursor.state)
        conn.commit()

        fetched = inserted = 0
        try:
            for item in connector.discover(cursor):
                fetched += 1
                raw_uri = rawstore.put(source_key, item.external_id, item.body, item.content_type)
                event = normalizer.normalize(item, raw_uri)
                company_id = (
                    repo.resolve_company_id(conn, event.company_ref.scheme, event.company_ref.value)
                    if event.company_ref
                    else None
                )
                _, was_new = repo.insert_ingest_event(
                    conn,
                    source_id=source_id,
                    run_id=run_id,
                    company_id=company_id,
                    event=event,
                    raw_uri=raw_uri,
                )
                inserted += int(was_new)
                cursor.state["last_external_id"] = item.external_id
                conn.commit()
            cursor.state["last_run_at"] = datetime.now(timezone.utc).isoformat()
            repo.finish_run(
                conn, run_id, status="succeeded", events_emitted=inserted, cursor=cursor.state
            )
            conn.commit()
        except Exception as exc:  # noqa: BLE001 - persist failure for operability, then re-raise
            conn.rollback()
            repo.finish_run(
                conn, run_id, status="failed", events_emitted=inserted,
                cursor=cursor.state, error=str(exc)[:2000],
            )
            conn.commit()
            raise
        return IngestSummary(source_key, fetched, inserted, run_id)
    finally:
        conn.close()


def run_detect(limit: int = 500) -> DetectSummary:
    """Detect + score + persist over unprocessed ingest events."""
    engine = ScoringEngine()
    conn = connect()
    try:
        events = repo.fetch_unprocessed_events(conn, limit=limit)
        if not events:
            return DetectSummary(0, 0, 0)

        ctx = PgDetectorContext(conn)
        detectors = all_detectors()
        tenants = repo.active_tenants(conn)
        configs = {t: repo.load_scoring_config(conn, t) for t in tenants}
        category_cache: dict[str, dict | None] = {}

        processed = failed = published = total = 0
        for event in events:
            # Per-event isolation: a single malformed event (bad data, a detector raising,
            # a constraint violation) must not abort the batch or permanently stall the
            # pipeline. On failure we mark the event 'failed' with the error and move on.
            try:
                # Carry each candidate's producing detector so we use its version
                # directly — no fragile re-lookup by slug.
                candidates: list[tuple[CandidateSignal, Detector]] = []
                for det in detectors:
                    candidates.extend((cand, det) for cand in det.evaluate(ctx, event))

                for tenant_id in tenants:
                    for cand, det in candidates:
                        if cand.company_id is None:
                            logger.warning(
                                "skipping candidate with null company_id "
                                "(category=%s, event=%s)",
                                cand.category_slug, event.id,
                            )
                            continue
                        cat = _resolve_category(conn, category_cache, cand.category_slug)
                        if cat is None:
                            logger.warning(
                                "skipping candidate with unknown/inactive category "
                                "'%s' (event=%s)",
                                cand.category_slug, event.id,
                            )
                            continue
                        cfg = replace(configs[tenant_id], category_weight=cat["default_weight"])
                        result = engine.score(cand, cfg)
                        sid = repo.persist_scored_signal(
                            conn,
                            tenant_id=tenant_id,
                            category_id=cat["id"],
                            candidate=cand,
                            result=result,
                            detector_version=det.version,
                        )
                        if sid is not None:
                            total += 1
                            published += int(result.publish)

                repo.mark_event(conn, event.id, "processed")
                conn.commit()
                processed += 1
            except Exception as exc:  # noqa: BLE001 - isolate the bad event, keep going
                conn.rollback()
                logger.exception("detect failed for event %s", event.id)
                failed += 1
                try:
                    repo.mark_event(conn, event.id, "failed", str(exc)[:2000])
                    conn.commit()
                except Exception:  # noqa: BLE001 - even marking failed failed; log and continue
                    conn.rollback()
                    logger.exception("could not mark event %s as failed", event.id)
        return DetectSummary(processed, published, total, events_failed=failed)
    finally:
        conn.close()


def _resolve_category(conn, cache: dict[str, dict | None], slug: str) -> dict | None:
    """Look up a signal category by slug, caching misses. Returns None (not raises) for an
    unknown/inactive category so the caller can skip the candidate instead of aborting."""
    if slug not in cache:
        try:
            cache[slug] = repo.category_by_slug(conn, slug)
        except repo.UnknownCategoryError:
            cache[slug] = None
    return cache[slug]


def run_rescore(limit: int = 500) -> int:
    """Repair pass: recompute the current score for signals that have none.

    Normal `detect` writes the score inline, so this is a maintenance command (e.g. after a
    config change or a partial failure). Returns the number of signals rescored.
    """
    engine = ScoringEngine()
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT s.id, s.tenant_id, s.company_id, s.title, s.summary, s.direction,
                      s.dedupe_key, s.observed_at, s.metadata, cat.slug AS category_slug,
                      cat.default_weight
                 FROM signal s
                 JOIN signal_category cat ON cat.id = s.category_id
                 LEFT JOIN signal_score sc ON sc.signal_id = s.id AND sc.is_current
                WHERE s.deleted_at IS NULL AND sc.id IS NULL
                LIMIT %s""",
            (limit,),
        ).fetchall()

        rescored = 0
        for r in rows:
            ev_rows = conn.execute(
                """SELECT ingest_event_id, evidence_type, excerpt, artifact_uri, weight
                     FROM signal_evidence WHERE signal_id = %s""",
                (r["id"],),
            ).fetchall()
            if not ev_rows:
                continue  # cannot score without evidence (invariant)
            features = dict((r["metadata"] or {}).get("features", {}))
            cand = CandidateSignal(
                company_id=r["company_id"],
                category_slug=r["category_slug"],
                title=r["title"],
                summary=r["summary"] or "",
                direction=r["direction"],
                observed_at=r["observed_at"],
                dedupe_key=r["dedupe_key"],
                evidence=[
                    EvidenceRef(
                        ingest_event_id=e["ingest_event_id"],
                        evidence_type=e["evidence_type"],
                        excerpt=e["excerpt"],
                        artifact_uri=e["artifact_uri"],
                        weight=float(e["weight"]),
                    )
                    for e in ev_rows
                ],
                features=features,
            )
            cfg = replace(repo.load_scoring_config(conn, r["tenant_id"]),
                          category_weight=float(r["default_weight"]))
            result = engine.score(cand, cfg)
            conn.execute(
                "UPDATE signal_score SET is_current = false WHERE signal_id = %s AND is_current",
                (r["id"],),
            )
            conn.execute(
                """INSERT INTO signal_score
                     (tenant_id, signal_id, magnitude, confidence, novelty, composite,
                      model_version, features, is_current)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)""",
                (
                    r["tenant_id"], r["id"], result.score.magnitude, result.score.confidence,
                    result.score.novelty, result.score.composite, result.score.model_version,
                    json.dumps(result.score.features, default=str),
                ),
            )
            conn.commit()
            rescored += 1
        return rescored
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
