# 08 — Compliance Guardrails

> **Tickertea surfaces signals, not advice.** This document defines the hard boundary and how it
> is enforced in code, schema, and content. Treat every item here as a non-negotiable invariant.

## The boundary

Tickertea **must never**:

- generate buy / sell / hold recommendations
- output target prices, fair value, or price objectives
- output expected returns, probability of profit, or risk-adjusted return estimates
- give investment advice, portfolio allocation, or position-sizing guidance
- rank companies as "good/bad investments"

Tickertea **may**:

- surface factual, evidence-backed observations (signals) and their source evidence
- score how *notable* a signal is (magnitude / confidence / novelty) — an attention measure
- show historical analogs as *observable past states*, not as outcome predictions

## Enforcement layers (defense in depth)

### 1. Schema-level
The `signal`, `signal_score`, and analog tables have **no fields** for recommendation, action,
target price, or expected return. Advice literally cannot be persisted. `direction`
(`up`/`down`/`neutral`) describes the *observation* and is documented as non-advisory.

### 2. Scoring-engine-level
- Scores are descriptive intensities in `[0,1]`, never return estimates.
- A deterministic **advice-language filter** runs on every generated `title`/`summary` before a
  signal can reach `status='published'`. It blocks phrases like *buy, sell, target price,
  upside, should accumulate, expected return, undervalued/overvalued (as a verdict)*. Blocked
  candidates go to `status='suppressed'` with a reason and are flagged for review.

### 3. LLM-prompt-level
- System prompts for Claude/OpenAI explicitly forbid recommendations and require neutral,
  descriptive language. Prompt + model versions are recorded in `signal_score.features`.
- LLMs are used only for extraction, summarization, and tone/narrative classification — never
  as a decision oracle.

### 4. API-level
- No request or response schema contains advice fields (`packages/contracts/` is the gate).
- Every signal payload includes a `disclaimer` field; the API rejects attempts to add advisory
  query params.

### 5. UI/content-level
- Persistent, visible disclaimer: *"Tickertea surfaces signals, not investment advice. You decide."*
- Scores are labeled "notability," never "rating" or "expected return."
- No "top picks", "best buys", or ranked-by-attractiveness surfaces.

## Auditability

Because every signal traces signal → evidence → ingest_event → raw S3 payload, and every score
records its model/prompt versions and features, any output can be fully reconstructed and
defended. This is both a compliance and a trust feature.

## Review process

- The advice-language filter's blocklist lives in `workers/tickertea/scoring/guardrail.py` and is
  unit-tested with adversarial phrasings.
- Any new signal category, LLM prompt, or user-facing copy that touches signal text requires a
  compliance review checklist sign-off (tracked in PR template).
- Regulatory note: this is a **research/information** product, not a SEBI-registered investment
  advisory. The guardrails keep it on the correct side of that line; legal review precedes any
  feature that could be construed as advice.
