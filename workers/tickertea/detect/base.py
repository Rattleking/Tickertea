"""Detector contract. A detector consumes a normalized event and may emit candidate
signals — each of which MUST carry >= 1 evidence ref. The scoring engine rejects any
candidate with no evidence, enforcing the traceability invariant before a signal row
is written. See docs/architecture/04-signal-scoring-engine.md.
"""
from __future__ import annotations

from typing import Protocol

from tickertea.common.types import CandidateSignal, IngestEvent


class DetectorContext(Protocol):
    """Read access a detector needs (baselines, snapshots, peers). Backed by Postgres."""

    def trailing_stats(self, company_id, metric: str, days: int) -> tuple[float, float]:
        """Return (mean, std) of a metric over the trailing window, from historical_snapshot."""
        ...


class Detector(Protocol):
    category_slug: str
    version: str

    def evaluate(self, ctx: DetectorContext, event: IngestEvent) -> list[CandidateSignal]:
        """Return zero or more candidate signals for this event. Pure function of the
        event + context: same inputs -> same dedupe_key -> idempotent detection."""
        ...
