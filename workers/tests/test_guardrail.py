"""Adversarial tests for the compliance advice-language guardrail."""
from tickertea.scoring.guardrail import check_text

CLEAN = [
    "Open roles up 3.2 sigma vs trailing 90-day mean",
    "New Chief Technology Officer appointed (KMP)",
    "Promoter holding rose 2.1 percentage points this quarter",
    "Coverage tone shifted toward capacity expansion",
]

ADVICE = [
    "Strong buy on this stock",
    "We recommend you sell before earnings",
    "Target price of 4200 implies meaningful upside",
    "This looks undervalued; accumulate on dips",
    "Expected return of 18% over 12 months",
    "A potential multibagger",
]


def test_clean_text_passes():
    for text in CLEAN:
        result = check_text(text)
        assert result.ok, f"clean text flagged: {text!r} -> {result.violations}"


def test_advice_text_blocked():
    for text in ADVICE:
        result = check_text(text)
        assert not result.ok, f"advice text passed: {text!r}"
        assert result.violations


def test_checks_multiple_fields():
    result = check_text("Neutral title", "but the summary says buy now")
    assert not result.ok
    assert "buy" in result.violations
