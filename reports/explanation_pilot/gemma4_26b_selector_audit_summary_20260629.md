# Gemma 4 26B Selector Baseline Audit

Date: 2026-06-29

## Purpose

This audit checks whether the explanation supervisor is learning something
beyond simple candidate-selection rules. The evaluation target remains
market-price matching: for each prompt, the best candidate explanation is the
one whose posterior is closest to the next observed market price.

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
scripts/audit_explanation_selectors.py
```

Main outputs:

```text
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_selector_performance.csv
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_stratified_performance.csv
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_tie_diagnostics.csv
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_prompt_diagnostics.csv
```

## Important Correction

The earlier heuristic result that "max selected evidence count" reached about
71% top-1 on the held-out set was a tie-breaking artifact.

The ranking CSV is sorted by market-error rank within prompt. Therefore, if a
heuristic has many ties and uses the first row returned by `idxmax`, it
accidentally chooses the already-ranked best candidate.

For held-out test prompts:

```text
selected_evidence_count ties for max: 64.5% of prompts
mean max-tie size: 2.82 candidates
best candidate is among max selected-evidence candidates: 71.0%
leaky row-order top-1: 71.0%
safe candidate-index tie-break top-1: 43.5%
```

Conclusion: evidence count is associated with the best candidate being in the
max-evidence set, but it is not by itself a strong selector once ties are broken
without label leakage.

## Held-Out Selector Results

Top-1 means the selected candidate is the closest candidate to the next market
price. Mean error is the selected candidate's absolute posterior error against
that next market price.

| Selector | Coverage | Top-1 | Mean error | Positive improvement | Direction match |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random expected | 62 | 0.248 | 0.172 | 0.349 | 0.349 |
| Gemma recommended | 53 | 0.396 | 0.182 | 0.377 | 0.377 |
| Max confidence | 62 | 0.371 | 0.177 | 0.242 | 0.242 |
| Max selected evidence count | 62 | 0.435 | 0.176 | 0.371 | 0.371 |
| Max posterior | 62 | 0.629 | 0.175 | 0.435 | 0.435 |
| Min posterior | 62 | 0.548 | 0.169 | 0.258 | 0.258 |
| Max absolute update | 62 | 0.613 | 0.166 | 0.452 | 0.452 |
| Core relative logit | 62 | 0.532 | 0.163 | 0.452 | 0.452 |
| Oracle best candidate | 62 | 1.000 | 0.140 | 0.645 | 0.645 |

The core relative logit does not have the highest top-1 rate, but it has the
lowest mean market-price error among non-oracle selectors. This matters because
top-1 ignores how close the runner-up candidates are; mean error is closer to
the actual market-price-matching objective.

## Directional Pattern

The candidate pool often contains both upward and downward updates. On the
held-out set:

```text
multi-direction candidate prompts: 69.4%
helpful candidate available: 64.5%
median posterior range within prompt: 0.049
```

The one-sided extreme rules reveal that direction is the central unresolved
selection problem:

| Market direction | Selector | Top-1 | Direction match |
| --- | --- | ---: | ---: |
| Up | Max posterior | 1.000 | 0.771 |
| Up | Max absolute update | 0.800 | 0.629 |
| Up | Gemma recommended | 0.655 | 0.690 |
| Up | Core relative logit | 0.543 | 0.514 |
| Down | Min posterior | 1.000 | 0.481 |
| Down | Core relative logit | 0.519 | 0.370 |
| Down | Max absolute update | 0.370 | 0.222 |
| Down | Gemma recommended | 0.083 | 0.000 |

Interpretation: Gemma can generate useful alternatives, but its recommended
choice is heavily asymmetric. It is much better when the market moves upward
than when the market moves downward. A selector that can infer the likely
direction of market belief update would be valuable.

## Schema Note

One training candidate had `confidence = 95.0`, outside the intended 0-1 range.
The audit treats out-of-range confidence values as missing before computing
confidence selectors or training the core relative logit. The parser should add
an explicit confidence-range validation check in the next cleanup pass.

## Research Implications

The current data supports the hypothesis that explanation generation and
explanation selection are separable. Gemma often generates a useful candidate,
but its own recommendation is not reliable enough.

The strongest simple baseline is not "use more evidence"; it is "choose the
candidate that moves most." That rule is plausible but blunt: it performs well
on top-1, while the learned relative selector gives a slightly better mean
market-price error.

The next empirical question should be:

```text
Can a selector infer the direction and size of the market's belief update from
candidate explanations and visible evidence, without using the realized market
move?
```

This is a cleaner formulation than globally classifying explanation classes as
good or bad. Explanation value appears to be prompt-relative: a candidate is
useful because it is the best update model among a local set of competing update
models.

## Recommended Next Experiment

1. Patch parser validation to enforce `confidence in [0, 1]`.
2. Keep reporting both top-1 and mean market-price error.
3. Add a direction-focused selection task:
   - target: sign of the market delta;
   - inputs: candidate explanation text, selected evidence, posterior/delta,
     confidence, explanation classes;
   - evaluation: whether the selector chooses an upward, downward, or flat
     candidate before scoring posterior closeness.
4. Add text/evidence embeddings only after the simple numeric baselines are
   locked, so we know whether embeddings add value beyond "move more."
