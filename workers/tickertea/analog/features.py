"""Feature-vector builder shared by the scoring engine and the analog engine, so analogs
are computed over the SAME feature space that produced the signal.
See docs/architecture/05-historical-analog-engine.md.
"""
from __future__ import annotations

from typing import Any

# Stable, ordered feature keys. Append-only to keep historical vectors comparable.
FEATURE_KEYS: list[str] = [
    "magnitude_z",
    "valuation_percentile",
    "hiring_z",
    "holding_delta",
    "narrative_tone",
]


def build_vector(metrics: dict[str, Any]) -> list[float]:
    """Project a snapshot's metrics onto the normalized feature vector."""
    return [_norm(key, metrics.get(key)) for key in FEATURE_KEYS]


def _norm(key: str, value: Any) -> float:
    if value is None:
        return 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    # Percentile-style features are already in [0,1]; z-scores are squashed to [-1,1].
    if key.endswith("_percentile") or key == "narrative_tone":
        return max(0.0, min(1.0, v))
    return max(-1.0, min(1.0, v / 5.0))
