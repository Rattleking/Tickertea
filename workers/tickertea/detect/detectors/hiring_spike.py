"""Hiring Spike detector: open roles up sharply vs the company's trailing baseline.

Reference detector showing the full contract: read a normalized job-posting event,
compare to the company's own trailing baseline, and emit an evidence-backed candidate
signal describing the OBSERVATION (no advice).
"""
from __future__ import annotations

from tickertea.common.types import CandidateSignal, EvidenceRef, IngestEvent
from tickertea.detect.base import DetectorContext

# Minimum z-score for the observation to be worth surfacing as a candidate.
Z_THRESHOLD = 2.0


class HiringSpikeDetector:
    category_slug = "hiring_spike"
    version = "hiring_spike.v1"

    def evaluate(self, ctx: DetectorContext, event: IngestEvent) -> list[CandidateSignal]:
        if event.event_type != "job_posting_batch" or event.company_id is None:
            return []

        open_roles = event.payload.get("open_roles")
        if open_roles is None:
            return []

        mean = event.payload.get("trailing_90d_mean")
        std = event.payload.get("trailing_90d_std")
        if mean is None or std is None:
            mean, std = ctx.trailing_stats(event.company_id, "open_roles", days=90)
        if not std:
            return []

        z = (open_roles - mean) / std
        if z < Z_THRESHOLD:
            return []

        return [
            CandidateSignal(
                company_id=event.company_id,
                category_slug=self.category_slug,
                title=f"Open roles up {z:.1f}σ vs trailing 90-day mean",
                summary=(
                    f"Open roles rose to {open_roles}, about {z:.1f} standard deviations "
                    f"above the trailing 90-day average of {mean:.0f}. Observation only."
                ),
                direction="up",
                observed_at=event.occurred_at or event.payload.get("as_of"),
                dedupe_key=f"{self.category_slug}:{event.company_id}:{event.id}",
                evidence=[
                    EvidenceRef(
                        ingest_event_id=event.id,
                        evidence_type="job_posting",
                        excerpt=f"{open_roles} open roles vs mean {mean:.0f} (std {std:.0f}).",
                        weight=1.0,
                    )
                ],
                features={"open_roles": open_roles, "mean": mean, "std": std, "zscore": z},
            )
        ]
