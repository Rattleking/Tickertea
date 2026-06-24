# 04 — Signal Scoring Engine

The scoring engine turns candidate signals into scored, publishable signals. It lives in
`workers/tickertea/scoring/` and `workers/tickertea/detect/`. It is **descriptive**: it scores how
*notable* an observation is, never how *profitable* a trade might be.

## Detectors → candidate signals

Each `signal_category` has a `detector_key` mapping to a detector class:

```python
class Detector(Protocol):
    category_slug: str
    version: str
    def evaluate(self, ctx: DetectorContext, event: IngestEvent) -> list[CandidateSignal]: ...
```

A `CandidateSignal` always carries its evidence:

```python
@dataclass
class CandidateSignal:
    company_id: UUID
    category_slug: str
    title: str
    summary: str
    direction: Literal["up", "down", "neutral"]   # describes the observation, not advice
    observed_at: datetime
    evidence: list[EvidenceRef]      # >= 1 required; engine rejects empties
    features: dict                   # raw inputs for scoring & audit
    dedupe_key: str
```

The engine **rejects any candidate with zero evidence** — enforcing the traceability invariant
before a signal row is ever written.

## The score: three descriptive components

Every score is a blend of three sub-scores in `[0, 1]`:

| Component | Question it answers | Example (hiring spike) |
| --- | --- | --- |
| `magnitude` | How large is the observation vs the company's own baseline? | open roles 3.2σ above trailing-90d mean |
| `confidence` | How well-corroborated and reliable is the evidence? | 2 independent sources, official filing |
| `novelty` | How unusual is this vs the company's history & peers? | first hiring spike in 18 months |

```
composite = w_m · magnitude + w_c · confidence + w_n · novelty
```

Weights come from `signal_category.default_weight` and per-tenant overrides in
`scoring_config` (jsonb), so tenants can tune emphasis without code changes. All components and
the composite are persisted in `signal_score` with the `features` that produced them.

### What the score is NOT
- Not an expected return, probability of profit, or price target.
- Not comparable to "rating." It is an **attention/notability** measure.
- The API and UI must label it as such (see [`08-compliance-guardrails.md`](08-compliance-guardrails.md)).

## Baselines & statistics

- Per-company baselines (trailing means, std-devs, percentiles) are computed from
  `historical_snapshot` so `magnitude`/`novelty` are always *self-relative* and explainable.
- Where peer comparison is used, peers are index/sector cohorts from `index_membership`.
- All statistics are recomputed from immutable history → reproducible and auditable.

## Lifecycle & publication

```
candidate ─▶ score() ─▶ signal_score(is_current=true)
                         │
            composite >= publish_threshold ? ─yes─▶ signal.status = published
                         │
                         └─no─▶ signal.status = suppressed   (retained, never served)
```

- `publish_threshold` is a per-tenant config value.
- Re-scoring (new model version or new corroborating evidence) inserts a new `signal_score`,
  flips the previous to `is_current=false`, and may move a suppressed signal to published.
- Scores never silently change a published signal's text; the audit trail is append-only.

## Confidence & LLM use

- Claude / OpenAI are used for **summarization, entity extraction, and tone/narrative
  classification** that feed `features` — never to emit a recommendation.
- LLM outputs are themselves evidence-linked (the source text is in `signal_evidence.excerpt`)
  and the model + prompt version are recorded in `signal_score.features` for auditability.
- A deterministic **guardrail filter** scans generated `title`/`summary` for advice-like
  language (target price, "buy", "should sell", expected return) and blocks publication if found.

## Pluggability

Adding a category = (1) `signal_category` row with `detector_key`, (2) a `Detector` subclass,
(3) optional category-specific scorer; default scorer uses the three-component blend. No schema
migration. The engine discovers detectors via `workers/tickertea/detect/registry.py`.
