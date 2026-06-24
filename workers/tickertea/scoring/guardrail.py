"""Compliance guardrail: advice-language filter.

Runs on every generated signal title/summary BEFORE it can be published. If advice-like
language is detected, the signal is suppressed (retained, never served) and flagged for
review. This is one of several defense-in-depth layers — see
docs/architecture/08-compliance-guardrails.md.

Tested with adversarial phrasings in tests/test_guardrail.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Phrases that imply a recommendation, target, or expected return. Word-boundary matched.
_FORBIDDEN_PATTERNS = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\bhold\b",
    r"\baccumulate\b",
    r"\bbook profits?\b",
    r"\btarget price\b",
    r"\bprice target\b",
    r"\bupside\b",
    r"\bdownside\b",
    r"\bexpected returns?\b",
    r"\bshould (buy|sell|invest|accumulate|exit)\b",
    r"\b(under|over)valued\b",      # as a verdict
    r"\bfair value\b",
    r"\bstrong (buy|sell)\b",
    r"\boutperform\b",
    r"\bunderperform\b",
    r"\bmultibagger\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _FORBIDDEN_PATTERNS]


@dataclass
class GuardrailResult:
    ok: bool
    violations: list[str]


def check_text(*texts: str | None) -> GuardrailResult:
    """Return ok=False with the matched phrases if any advice-language is present."""
    violations: list[str] = []
    for text in texts:
        if not text:
            continue
        for pattern in _COMPILED:
            m = pattern.search(text)
            if m:
                violations.append(m.group(0).lower())
    return GuardrailResult(ok=not violations, violations=sorted(set(violations)))
