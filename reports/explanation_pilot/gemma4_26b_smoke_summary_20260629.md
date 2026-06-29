# Gemma 4 26B Explanation Smoke Summary

Date: 2026-06-29

This note summarizes the first two ORCD/vLLM smoke runs for the
market-for-explanations pilot. These runs validate the generation pipeline and
expose an important prompt-design tradeoff before scaling to larger batches.

## Runs

| Run | Requests | Rows | Evidence regimes | Prompt variants | Samples | Parse errors |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| `gemma4_26b_explanation_smoke5_20260629` | 30 | 5 | `mixed_blind`, `prior_selected` | `neutral_forecaster`, `source_skeptic`, `base_rate_calibrator` | 1 | 0 |
| `gemma4_26b_explanation_strict_smoke5_20260629` | 30 | 5 | `mixed_blind`, `prior_selected` | `neutral_forecaster`, `source_skeptic`, `base_rate_calibrator` | 1 | 0 |

## Operational Results

| Run | ORCD job | Successes | Errors | Mean completion tok/s | Mean seconds/request |
| --- | --- | ---: | ---: | ---: | ---: |
| Initial smoke | `16773317` | 30 | 0 | 116.21 | 2.43 |
| Strict smoke | `16773837` | 30 | 0 | 118.65 | 1.93 |

## Score Summary

These are lightweight diagnostics, not final evaluation metrics. Market
movement is treated as the proxy for popularity or belief-shift agreement; it
is not the same as ground-truth correctness.

| Run | Direction match | Mean delta error | Median delta error | Selected top-prior evidence | Selected hard negatives |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial smoke | 8 / 30 | 0.5253 | 0.4527 | 12 / 30 | 10 / 30 |
| Strict smoke | 2 / 30 | 0.5214 | 0.4527 | 1 / 30 | 1 / 30 |

## Interpretation

The initial prompt showed excellent JSON compliance but sometimes stretched
weak topical evidence into a causal story. The strict prompt fixed much of that
over-selection: hard-negative evidence selection dropped from 10/30 to 1/30.

The strict prompt also pushed the model toward excessive immobility. It
increased `evidence_irrelevance` labels from 19 to 28 and reduced market
direction matches from 8/30 to 2/30. This is substantively useful: it suggests
that explanation generation is sensitive to the policy used for deciding when
evidence is relevant enough to justify a belief update.

## Design Decision

Do not scale the strict prompt directly. The next Stage 1 run uses a `balanced`
relevance policy:

- reject broad topical matches and hard negatives;
- select directly relevant evidence when it changes the exact market outcome's
  likelihood;
- make small updates for weak/indirect evidence, larger updates only for direct
  or diagnostic evidence;
- keep the posterior near the prior when no visible evidence is relevant.

The balanced Stage 1 run is submitted as ORCD job `16773996` with 240 requests.
