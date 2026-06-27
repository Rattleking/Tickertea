"""Signal scoring engine.

Turns candidate signals into scored, publishable signals. The score is a DESCRIPTIVE
notability measure (magnitude / confidence / novelty), never an expected return or price
target. See docs/architecture/04-signal-scoring-engine.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from tickertea.common.types import CandidateSignal, Score
from tickertea.scoring.guardrail import check_text

MODEL_VERSION = "score-1.0.0"


@dataclass
class ScoringConfig:
    """Per-tenant config (mirrors the scoring_config table)."""

    weight_magnitude: float = 0.40
    weight_confidence: float = 0.35
    weight_novelty: float = 0.25
    publish_threshold: float = 0.50
    category_weight: float = 1.0  # from signal_category.default_weight (+ overrides)


@dataclass
class ScoreResult:
    score: Score
    publish: bool
    suppressed_reason: str | None = None


class ScoringEngine:
    def score(self, candidate: CandidateSignal, cfg: ScoringConfig) -> ScoreResult:
        # Invariant: a candidate with no evidence can never be scored/published.
        if not candidate.evidence:
            raise ValueError("candidate signal has no evidence (traceability invariant)")

        # 1. Guardrail FIRST: advice-language => suppress, never publish.
        guard = check_text(candidate.title, candidate.summary)
        if not guard.ok:
            score = self._blank_score()
            return ScoreResult(score, publish=False,
                               suppressed_reason=f"advice_language:{','.join(guard.violations)}")

        # 2. Descriptive sub-scores in [0,1].
        magnitude = self._magnitude(candidate)
        confidence = self._confidence(candidate)
        novelty = self._novelty(candidate)

        composite = _clip01(
            (cfg.weight_magnitude * magnitude
             + cfg.weight_confidence * confidence
             + cfg.weight_novelty * novelty)
            * cfg.category_weight
        )

        score = Score(
            magnitude=round(magnitude, 3),
            confidence=round(confidence, 3),
            novelty=round(novelty, 3),
            composite=round(composite, 3),
            model_version=MODEL_VERSION,
            features={**candidate.features, "category_weight": cfg.category_weight},
        )
        return ScoreResult(score, publish=composite >= cfg.publish_threshold)

    # --- component scorers (replaceable per category) -------------------------------
    def _magnitude(self, c: CandidateSignal) -> float:
        """How large the change is. Statistical detectors supply a z-score (squashed:
        5σ -> ~1.0); event-driven detectors (e.g. a disclosed CXO change, which has no
        baseline) supply an explicit `magnitude` in [0,1] reflecting materiality."""
        if "magnitude" in c.features:
            return _clip01(float(c.features["magnitude"]))
        z = abs(float(c.features.get("zscore", 0.0)))
        return _clip01(z / 5.0)

    def _confidence(self, c: CandidateSignal) -> float:
        """Evidence strength & corroboration. More independent evidence -> higher."""
        n = len(c.evidence)
        avg_weight = sum(e.weight for e in c.evidence) / n
        corroboration = _clip01(0.5 + 0.25 * (n - 1))  # 1 src -> 0.5, 3 src -> 1.0
        return _clip01(0.6 * corroboration + 0.4 * _clip01(avg_weight))

    def _novelty(self, c: CandidateSignal) -> float:
        """How unusual vs history. Placeholder until snapshot-based novelty lands."""
        return float(c.features.get("novelty", 0.6))

    @staticmethod
    def _blank_score() -> Score:
        return Score(0.0, 0.0, 0.0, 0.0, MODEL_VERSION, {})


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))
