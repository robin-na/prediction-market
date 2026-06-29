# Gemma vs Qwen Explanation Pilot Comparison

Date: 2026-06-29

This note compares Gemma 4 26B A4B and Qwen3 14B on the same 20-row
market-for-explanations pilot. Both models used the same request schema,
prompt variants, evidence regimes, relevance policy, temperature, and scoring
pipeline. Qwen used the chat endpoint with thinking disabled.

## Operational Summary

| Model | Run | Requests | Generation errors | Parse errors | Mean completion tok/s | Mean seconds/request |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gemma 4 26B A4B | Stage 1 | 240 | 0 | 0 | 117.76 | 2.24 |
| Gemma 4 26B A4B | Diagnostic | 240 | 0 | 1 | 120.91 | 1.60 |
| Qwen3 14B | Stage 1 | 240 | 0 | 0 | 51.65 | 4.69 |
| Qwen3 14B | Diagnostic | 240 | 0 | 0 | 51.78 | 3.74 |

## Score Summary

| Model | Run | Scored rows | Direction match | Mean delta error | Any evidence selected | Top-posterior selected | Hard negatives selected | Mean abs posterior delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemma | Stage 1 | 240 | 19 | 0.3823 | 47 | 5 | 26 | 0.0046 |
| Gemma | Diagnostic | 239 | 4 | 0.3814 | 17 | 4 | 15 | 0.0012 |
| Qwen | Stage 1 | 240 | 2 | 0.3811 | 52 | 12 | 24 | 0.0012 |
| Qwen | Diagnostic | 240 | 0 | 0.3801 | 35 | 6 | 34 | 0.0002 |

Market-direction match is a popularity proxy: it measures whether the generated
posterior moved in the same direction as the market price, not whether the
prediction was ultimately correct.

## Diagnostic Regimes

| Model | Regime | Rows | Direction match | Any evidence selected | Top-posterior selected | Mean abs posterior delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Gemma | `history_only` | 119 | 0 | 0 | 0 | 0.0000 |
| Gemma | `posterior_oracle` | 120 | 4 | 17 | 4 | 0.0024 |
| Qwen | `history_only` | 120 | 0 | 0 | 0 | 0.0000 |
| Qwen | `posterior_oracle` | 120 | 0 | 35 | 6 | 0.0003 |

## Interpretation

The main finding is that the null-update behavior is not Gemma-specific. Qwen
selects evidence somewhat more often than Gemma, especially in the
posterior-oracle diagnostic, but this does not translate into meaningful
posterior movement.

Both models treat `history_only` as a pure null-update baseline, which is good.
The surprising result is that `posterior_oracle` also remains close to a null
update. This suggests that merely showing posterior-associated evidence is not
enough. The current prompt/schema asks for a disciplined update, and both
models interpret that discipline as extreme conservatism.

For the next pilot iteration, the likely bottleneck is the elicitation of update
functions rather than raw model capability or evidence availability alone. We
should test prompts that explicitly generate multiple update hypotheses, force
non-null alternatives when evidence is plausibly relevant, and score them after
generation, rather than asking one model response to be both selective and
calibrated.
