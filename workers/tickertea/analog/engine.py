"""Historical analog engine (SKELETON).

Finds comparable PAST situations so a user can reason by analogy. It answers "when has
something like this happened before?" — NOT "what will happen next?". By design there is
no outcome/return field on a match. See docs/architecture/05-historical-analog-engine.md.

v1 baseline: filter candidate snapshots, cosine-similarity over a normalized feature
vector, top-K with per-feature explanation. The interface is stable across future
backends (pgvector ANN, learned metrics).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from tickertea.analog.features import FEATURE_KEYS


@dataclass
class Seed:
    company_id: UUID
    as_of: datetime
    vector: list[float]


@dataclass
class Filters:
    sector: str | None = None
    index: str | None = None
    category: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass
class SnapshotCandidate:
    snapshot_id: UUID
    company_id: UUID
    as_of: datetime
    vector: list[float]


@dataclass
class AnalogMatch:
    snapshot_id: UUID
    company_id: UUID
    as_of: datetime
    similarity: float
    explanation: dict[str, Any] = field(default_factory=dict)
    # NOTE: no `outcome` / `forward_return` field — compliance invariant.


class AnalogEngine:
    def search(self, seed: Seed, candidates: list[SnapshotCandidate], k: int) -> list[AnalogMatch]:
        """Rank candidates by cosine similarity to the seed vector; return top-K.

        Point-in-time correctness is the caller's responsibility: only pass candidates
        whose as_of < seed.as_of and that were knowable then (index_membership etc.).
        """
        scored = [
            AnalogMatch(
                snapshot_id=c.snapshot_id,
                company_id=c.company_id,
                as_of=c.as_of,
                similarity=_cosine(seed.vector, c.vector),
                explanation=self.explain(seed.vector, c.vector),
            )
            for c in candidates
            if c.as_of < seed.as_of
        ]
        scored.sort(key=lambda m: m.similarity, reverse=True)
        return scored[:k]

    def explain(self, a: list[float], b: list[float]) -> dict[str, Any]:
        """Per-feature contribution to similarity (auditable, not predictive)."""
        return {
            key: round(1.0 - abs(av - bv), 4)
            for key, av, bv in zip(FEATURE_KEYS, a, b)
        }


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    # Map cosine [-1,1] to [0,1] similarity.
    return max(0.0, min(1.0, (dot / (na * nb) + 1.0) / 2.0))
