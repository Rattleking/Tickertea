"""Maps signal_category.slug -> Detector. Adding a category = add a row in
signal_category (db/seed/02) + a Detector here. No schema migration required.
"""
from __future__ import annotations

from tickertea.detect.base import Detector
from tickertea.detect.detectors.hiring_spike import HiringSpikeDetector

_DETECTORS: dict[str, Detector] = {}


def register(detector: Detector) -> None:
    _DETECTORS[detector.category_slug] = detector


def all_detectors() -> list[Detector]:
    return list(_DETECTORS.values())


def get_detector(category_slug: str) -> Detector:
    return _DETECTORS[category_slug]


# --- Built-in registrations ---------------------------------------------------------
register(HiringSpikeDetector())
# TODO: mean_reversion, management_change, capex_expansion, subsidiary_creation,
#       narrative_shift, news_event, insider_activity, institutional_flow
