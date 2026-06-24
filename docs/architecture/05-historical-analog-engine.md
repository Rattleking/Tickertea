# 05 — Historical Analog Engine (Skeleton)

**Goal:** given a current situation (a signal or a company's current observable state), find
*comparable past situations* and show what was observable then — letting the user reason by
analogy. It answers "when has something like this happened before?", **not** "what will happen
next?" No outcome prediction, no return estimation.

Status in v1: **skeleton** — schema, interfaces, and a baseline similarity implementation are in
place; richer embeddings and cohort logic are future work.

## Inputs & outputs

```
AnalogQuery {                          AnalogMatch[] {
  seed: signal_id | company_state        snapshot_id        // a historical_snapshot
  feature_vector: number[]               similarity: 0..1
  filters: { sector?, index?,            explanation: jsonb // which features matched & how
             category?, date_range? }    // (NO outcome / return field by design)
}                                      }
```

- `analog_query` and `analog_match` are tenant-scoped tables (see data model).
- A match references a `historical_snapshot` (and optionally the `signal` active then). The user
  can open that snapshot's evidence chain exactly like a live signal.

## Feature vector

Built from the same `features` the scoring engine uses plus snapshot metrics, normalized:

```
[ magnitude_z, valuation_percentile, hiring_z, holding_delta,
  narrative_tone, sector_onehot..., category_onehot... ]
```

The builder lives in `workers/tickertea/analog/features.py` and is shared with scoring so analogs
are computed over the *same* feature space that produced the signal.

## Similarity (v1 baseline → future)

| Stage | v1 (skeleton) | Future |
| --- | --- | --- |
| Candidate set | filter snapshots by sector/index/category/date | ANN over embedding index |
| Distance | cosine on normalized feature vector | learned metric / pgvector embeddings |
| Ranking | top-K by similarity | re-rank with cohort & regime awareness |
| Explanation | per-feature contribution to distance | natural-language rationale (LLM, evidence-linked) |

The interface is stable across stages:

```python
class AnalogEngine(Protocol):
    def build_query(self, seed: Seed, filters: Filters) -> AnalogQuery: ...
    def search(self, query: AnalogQuery, k: int) -> list[AnalogMatch]: ...
    def explain(self, match: AnalogMatch) -> dict: ...   # feature-level, auditable
```

`pgvector` is anticipated: a future migration adds an `embedding vector` column to
`historical_snapshot` and an ANN index. The skeleton deliberately keeps `feature_vector` in
`jsonb` so we can swap the storage/search backend without changing the API contract.

## Honesty constraints

- Every analog must trace to a real `historical_snapshot` with its own evidence — no synthetic
  examples.
- The engine **must not** attach, compute, or display the subsequent return/outcome of an analog
  as a headline metric. (If users later request "what happened next" it is shown only as raw,
  user-requested historical price context with explicit "not a prediction" framing — gated by
  the compliance review in [`08-compliance-guardrails.md`](08-compliance-guardrails.md).)
- Point-in-time correctness: analogs only use data that was knowable `as_of` the snapshot date
  (`index_membership` and `historical_snapshot` are point-in-time for exactly this reason).
