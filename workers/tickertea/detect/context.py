"""Postgres-backed DetectorContext.

Gives detectors the read access they need (currently trailing baselines from
historical_snapshot). Kept separate from the detectors so they stay pure functions of
(event, context) and can be unit-tested with an in-memory fake context.
"""
from __future__ import annotations

import statistics
from uuid import UUID

import psycopg


class PgDetectorContext:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def trailing_stats(self, company_id: UUID, metric: str, days: int) -> tuple[float, float]:
        """(mean, std) of a numeric metric over the trailing `days` from historical_snapshot.

        Returns (0.0, 0.0) when there isn't enough history; detectors treat std==0 as
        "no baseline yet" and emit nothing, so a cold start never produces false signals.
        """
        # Only consider snapshots where this metric is a JSON *number*; this excludes
        # missing keys and guards the ::float8 cast against non-numeric values (e.g. a
        # stray "N/A" string or a nested object), which would otherwise raise and abort
        # the whole detect transaction.
        rows = self._conn.execute(
            """SELECT (metrics ->> %s)::float8 AS v
                 FROM historical_snapshot
                WHERE company_id = %s
                  AND as_of >= now() - make_interval(days => %s)
                  AND jsonb_typeof(metrics -> %s) = 'number'""",
            (metric, company_id, days, metric),
        ).fetchall()
        values = [r["v"] for r in rows if r["v"] is not None]
        if len(values) < 2:
            return (values[0] if values else 0.0, 0.0)
        return (statistics.fmean(values), statistics.pstdev(values))
