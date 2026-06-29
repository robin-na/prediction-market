# Gemma 4 26B Balanced Diagnostic Summary

Date: 2026-06-29

This diagnostic uses the same 20 rows as the balanced Stage 1 run, but swaps
the evidence regimes to separate baseline update behavior from evidence
selection failure.

## Setup

| Field | Value |
| --- | --- |
| Model | `google/gemma-4-26B-A4B` |
| ORCD job | `16774267` |
| Rows | 20 market-transition rows |
| Requests | 240 |
| Evidence regimes | `history_only`, `posterior_oracle` |
| Prompt variants | `neutral_forecaster`, `source_skeptic`, `base_rate_calibrator` |
| Samples per cell | 2 |
| Relevance policy | `balanced` |
| Temperature | 0.6 |

## Operational Result

| Metric | Value |
| --- | ---: |
| Successful generations | 240 / 240 |
| Generation errors | 0 |
| Parse errors | 1 |
| Mean completion tokens/sec | 120.91 |
| Mean seconds/request | 1.60 |

The single parse failure was an incomplete JSON object in a `history_only`
request. It is preserved as a parse error rather than repaired silently.

## Score Summary

| Metric | Value |
| --- | ---: |
| Scored rows | 239 |
| Direction match to market delta | 4 / 239 |
| Mean delta error | 0.3814 |
| Median delta error | 0.3300 |
| Any evidence selected | 17 / 239 |
| Selected top-posterior candidate | 4 / 239 |
| Selected hard-negative candidate | 15 / 239 |
| Mean absolute posterior delta | 0.0012 |
| Median absolute posterior delta | 0.0000 |

## By Evidence Regime

| Regime | Scored rows | Direction match | Any evidence selected | Mean abs posterior delta | Magnitude distribution |
| --- | ---: | ---: | ---: | ---: | --- |
| `history_only` | 119 | 0 / 119 | 0 / 119 | 0.0000 | `none`: 119 |
| `posterior_oracle` | 120 | 4 / 120 | 17 / 120 | 0.0024 | `none`: 114, `small`: 5, `moderate`: 1 |

## Interpretation

`history_only` is a clean null-update baseline for Gemma: without visible
evidence, it keeps the posterior at the prior.

The important result is that `posterior_oracle` barely changes this behavior.
Even when the evidence packet contains candidate evidence selected for its
association with the posterior/moved state, Gemma still usually refuses to
move. This suggests that the current bottleneck is not only evidence retrieval
or evidence selection. It is also the update model: the prompt/model combination
does not translate candidate evidence into posterior shifts of meaningful size.

The next comparison is Qwen3 14B on the same Stage 1 request design. If Qwen
moves more under the same schema, the null-update behavior is at least partly
Gemma-specific. If Qwen also stays near the prior, the bottleneck is likely in
the prompt/schema/evidence representation rather than in one model.
