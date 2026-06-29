# Gemma 4 26B Generation Gap Audit

Date: 2026-06-29

## Purpose

The selector audit showed that Gemma's generated candidate pool is better than
Gemma's own recommended candidate. This audit asks the next question:

```text
Even if we choose the best candidate post hoc, how close does the generated
candidate pool get to the market's next price?
```

This is the generation gap. It is the remaining error after giving the system
an oracle selector.

## Inputs

Training candidates:

```text
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_train_all_batches_valid_ranking_candidates.csv
candidate rows: 1361
prompt groups: 300
```

Held-out test candidates:

```text
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv
candidate rows: 275
prompt groups: 62
```

Audit script:

```text
scripts/audit_explanation_generation_gap.py
```

Outputs:

```text
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_prompt_level.csv
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_aggregate.csv
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_examples.csv
```

## Core Result

Held-out test72:

```text
prompt_count: 62
mean persistence error: 0.181
mean oracle-best candidate error: 0.140
mean oracle improvement over persistence: 0.041
helpful candidate available: 64.5%
best candidate within 5 percentage points: 21.0%
best candidate more than 20 percentage points away: 17.7%
target bracketed by candidate posterior range: 0.0%
```

Interpretation: the generated pool helps, but it does not cover the market's
posterior well. The best candidate is still about 14 percentage points away on
average, and the market-after price is never inside the candidate posterior
range on this held-out set.

## Main Failure Mode: Underreaction

Among held-out prompts, the generation gap decomposes as:

| Gap type | Prompts | Mean best error | Within 5pp |
| --- | ---: | ---: | ---: |
| Right direction, under-updated | 38 | 0.152 | 0.263 |
| No right-direction candidate | 22 | 0.129 | 0.045 |
| Near hit | 2 | 0.016 | 1.000 |

So the dominant failure is not only wrong direction. In most prompts, Gemma can
generate a candidate that moves in the same direction as the market, but it does
not move far enough.

For held-out prompts where the best candidate has the correct direction:

```text
median best-candidate update / market update: 0.250
mean candidate posterior range / market update: 0.457
```

In plain terms: even when Gemma moves the right way, the best generated update
usually covers only about one quarter of the actual market movement.

## Direction Split

Held-out test72:

| Market direction | Prompts | Helpful candidate available | Mean best error | Within 5pp |
| --- | ---: | ---: | ---: | ---: |
| Up | 35 | 77.1% | 0.139 | 25.7% |
| Down | 27 | 48.1% | 0.141 | 14.8% |

Gemma is much more likely to generate a helpful candidate for upward market
moves than downward moves. This matches the selector audit, where Gemma's own
recommendation was especially weak on downward moves.

## Example Pattern

Large generation gaps often look like this:

```text
kalshi_test_0354
market move: 0.754 -> 0.043
best Gemma candidate: 0.600
gap: 0.557
type: right direction, under-updated
```

Gemma recognized the downward direction in one candidate, but the market moved
far more sharply than Gemma was willing to represent.

Another upward example:

```text
kalshi_test_1104
market move: 0.102 -> 0.641
best Gemma candidate: 0.140
gap: 0.501
type: right direction, under-updated
```

Here Gemma generated only very small upward or flat updates despite a large
market move.

## Interpretation

The current prompt asks Gemma for plausible explanation/update candidates. It
does create diversity, but the diversity is too narrow in posterior space.

This means the project has two distinct empirical problems:

1. **Selection gap**: Gemma often generates a useful candidate but does not
   select it.
2. **Generation gap**: even the best generated candidate often does not move
   far enough to match the market.

The generation gap could come from several sources:

- The visible public evidence may genuinely not justify the market move.
- The retrieved evidence may omit the market-moving information.
- Gemma may be over-conservative when translating evidence into posterior
  updates.
- The prompt may discourage large market-style updates by emphasizing
  groundedness.
- Some market moves may reflect liquidity, timing, or private information
  rather than public news.

## Next Experiment

The next generator should deliberately create a wider posterior-support set,
not just five natural-language explanations.

Suggested prompt design:

```text
Generate five competing update models:
1. evidence-strict/no-update model;
2. conservative Bayesian update;
3. moderate evidence-weighted update;
4. aggressive market-reaction update;
5. contrarian/noise-or-overreaction update.
```

Each candidate should still cite visible evidence, but the prompt should
explicitly require posterior diversity and calibration diversity. The evaluation
should first ask whether the candidate pool's oracle-best error improves before
we train a better selector.

Success criterion for the next generation run:

```text
increase target-bracketed rate above 0%
increase within-5pp oracle-best rate above 21%
reduce oracle-best mean error below 0.140 on held-out-style prompts
```

Only after the generation upper bound improves does it make sense to invest
heavily in a more complex selector.
