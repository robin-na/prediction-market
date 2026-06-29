# Gemma 4 26B Balanced Stage 1 Summary

Date: 2026-06-29

This run tests whether a balanced relevance policy can make Gemma 4 26B A4B
generate useful explanation candidates for market belief updates, without
either over-selecting distractors or refusing to update at all.

## Setup

| Field | Value |
| --- | --- |
| Model | `google/gemma-4-26B-A4B` |
| ORCD job | `16773996` |
| Rows | 20 market-transition rows |
| Requests | 240 |
| Evidence regimes | `mixed_blind`, `prior_selected` |
| Prompt variants | `neutral_forecaster`, `source_skeptic`, `base_rate_calibrator` |
| Samples per cell | 2 |
| Relevance policy | `balanced` |
| Temperature | 0.6 |

## Operational Result

| Metric | Value |
| --- | ---: |
| Successful generations | 240 / 240 |
| Generation errors | 0 |
| Parse errors | 0 |
| Mean completion tokens/sec | 117.76 |
| Mean seconds/request | 2.24 |
| Median seconds/request | 2.20 |

The model-serving and request-generation pipeline is working reliably.

## First Score Summary

Market movement is used here as the proxy for popularity or agreement with the
market's belief update. It is not the same as final-event correctness.

| Metric | Value |
| --- | ---: |
| Direction match to market delta | 19 / 240 |
| Mean delta error | 0.3823 |
| Median delta error | 0.3300 |
| Any evidence selected | 47 / 240 |
| Selected top-posterior candidate | 5 / 240 |
| Selected top-prior candidate | 25 / 240 |
| Selected hard-negative candidate | 26 / 240 |
| Had `evidence_irrelevance` label | 209 / 240 |
| Selected evidence while labeling irrelevance | 16 / 240 |
| Mean absolute posterior delta | 0.0046 |
| Median absolute posterior delta | 0.0000 |

## Magnitude Distribution

| Magnitude | Count |
| --- | ---: |
| `none` | 207 |
| `small` | 26 |
| `moderate` | 6 |
| `large` | 1 |

## Explanation Labels

| Label | Count |
| --- | ---: |
| `evidence_irrelevance` | 209 |
| `base_rate_calibration` | 52 |
| `source_credibility` | 44 |
| `causal_chain` | 12 |
| `direct_resolution` | 7 |
| `trend_continuation` | 4 |

Labels are not mutually exclusive, so counts exceed the number of generations.

## Interpretation

The pipeline is ready for real experiments, but this particular Gemma prompting
setup is mostly a null-update generator. It often rejects evidence and keeps the
posterior at the prior. That is useful as a baseline, but it is not yet the
explanation ensemble we want.

The balanced prompt was an improvement over the strict prompt only in a limited
sense. It allowed more evidence selection than strict, but it did not produce
substantial belief updates. The median absolute posterior move remained zero.

For stable rows where the market barely moved, this behavior is reasonable. For
large market moves, it suggests a bottleneck. The model may not be seeing the
true market-moving evidence, may be too conservative about how evidence should
move probabilities, or both.

The `selected_with_irrelevance` cases are also important. In those outputs, the
model sometimes selected candidate evidence while simultaneously classifying
the explanation as evidence irrelevance. That is not just a formatting issue:
it suggests the schema needs consistency checks and that evidence selection
should be scored separately from explanation labeling.

## Next Diagnostic

Run the same 20 rows with two additional regimes:

| Regime | Purpose |
| --- | --- |
| `history_only` | Measures the model's baseline tendency to update from the market wording and prior alone. |
| `posterior_oracle` | Tests whether the model updates when given the candidate evidence most associated with the posterior/moved state. |

If `posterior_oracle` improves sharply, the bottleneck is evidence selection.
If it still produces mostly null updates, the bottleneck is the update model or
prompting itself.
