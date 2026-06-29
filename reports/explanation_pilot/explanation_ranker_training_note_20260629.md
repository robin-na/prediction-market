# Explanation Ranker Training Note

Date: 2026-06-29

## What Is Being Trained

We are not fine-tuning Gemma. Gemma is used as a generator of candidate
explanation/update models.

The trained object is a lightweight ranker that chooses one explanation from
the set Gemma generated for the same market-time prompt.

## Unit Of Observation

For each market-time prompt `i`, Gemma generates up to 5 candidate explanations:

```text
E_i1, E_i2, ..., E_iK
```

Each candidate includes:

- a posterior probability;
- selected evidence IDs;
- an update magnitude;
- explanation class labels;
- model confidence;
- structured explanation text and update rule.

## Current Supervision Signal

The current target is market-price matching, not final event resolution.

For candidate `k` in prompt `i`:

```text
posterior_error_ik = abs(gemma_posterior_ik - market_after_price_i)
```

The rank label is:

```text
is_best_candidate_ik = 1
```

for the candidate with the smallest posterior error within the same prompt.

We also track:

```text
is_positive_improvement_ik =
  abs(market_after_price_i - prior_price_i)
  - abs(gemma_posterior_ik - market_after_price_i) > 0
```

Interpretation: this learns which explanation best matches the market's belief
update, i.e. the popularity/equilibrium proxy. It does not yet learn final
outcome correctness.

## Schema Filtering

Before training, malformed candidates are dropped using parser-level validation:

- posterior is in `[0, 1]`;
- reported delta matches `posterior - prior`;
- reported direction matches the computed delta direction;
- selected evidence IDs are visible in the prompt;
- selected evidence IDs and evidence weights respect the 5-item bound;
- evidence weights only reference selected evidence;
- the response has the expected number of candidates;
- the recommended explanation ID exists.

## Current Feature Set

The deployable ranker uses only candidate-time features:

- generated posterior and delta from prior;
- selected evidence count;
- evidence weight count;
- Gemma confidence;
- whether the candidate uses evidence irrelevance;
- whether it selected evidence while claiming irrelevance;
- explanation class one-hot features;
- update magnitude one-hot features.

It does not use:

- market after price;
- market delta;
- direction match;
- posterior error;
- final event resolution;
- SWM posterior-attribution oracle features.

There is a separate diagnostic feature mode that can include SWM attribution
flags, but this is not treated as deployable.

## Current Model

The current baseline model is deliberately simple:

```text
SimpleImputer(median)
StandardScaler
LogisticRegression(class_weight="balanced")
```

The model predicts `P(is_best_candidate)`. For each held-out prompt, we select
the candidate with the highest predicted probability.

## Current Evaluation

Scripts:

- `scripts/build_explanation_ranking_dataset.py`
- `scripts/evaluate_explanation_ranker.py`

Train source:

```text
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_train_batch001_valid_ranking_candidates.csv
```

Held-out test source:

```text
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv
```

Held-out result using only train batch 001:

```text
train_valid_candidate_rows: 386
train_prompt_count: 85
test_valid_candidate_rows: 275
test_prompt_count: 62

ranker_top1_rate: 0.452
gemma_recommended_top1_rate: 0.396
confidence_top1_rate: 0.435
random_top1_rate: 0.248
```

Interpretation: the ranker is only a small improvement so far, but the direction
is consistent with the main hypothesis: Gemma can generate useful candidates
better than it can select among them.

## Full Train-Batch Evaluation

After all four train batches completed, the valid-only training pool became:

```text
train_valid_candidate_rows: 1361
train_prompt_count: 300
heldout_test_valid_candidate_rows: 275
heldout_test_prompt_count: 62
```

The first all-train logistic model using only absolute candidate features was
not stable:

```text
ranker_top1_rate: 0.387
gemma_recommended_top1_rate: 0.396
confidence_top1_rate: 0.435
random_top1_rate: 0.248
```

Adding prompt-relative features changed the result materially. These features
compare candidates only to the other candidates generated for the same prompt,
which is available at selection time and does not use the future market move:

- candidate confidence rank within the prompt;
- candidate posterior rank within the prompt;
- candidate update-magnitude rank within the prompt;
- selected-evidence-count rank within the prompt;
- z-scored and mean-relative versions of those quantities.

Held-out test results with prompt-relative deployable features:

```text
logistic_regression_top1_rate: 0.548
hist_gradient_boosting_top1_rate: 0.532
extra_trees_top1_rate: 0.516
gemma_recommended_top1_rate: 0.396
confidence_top1_rate: 0.435
random_top1_rate: 0.248
```

Interpretation: the first meaningful supervisor signal appears to be
comparative rather than absolute. It is not just "this explanation has class X";
it is closer to "among the five candidates Gemma generated, this one has the
right relative confidence/update/evidence profile." This is aligned with the
project's market-for-explanations framing because explanation value is defined
inside a choice set of competing belief-update models.

## Next Steps

The remaining train batches have now been added, and the first selector audit
changed the immediate priority.

Selector audit summary:

```text
heldout_test72_prompt_count: 62
random_expected_top1: 0.248
gemma_recommended_top1: 0.396
max_selected_evidence_count_top1_safe: 0.435
max_abs_update_top1: 0.613
core_relative_logit_top1: 0.532
core_relative_logit_mean_error: 0.163
oracle_best_candidate_mean_error: 0.140
```

Important correction: the earlier 0.710 top-1 result for max selected evidence
count was caused by row-order tie leakage. The ranking CSV is sorted by
market-error rank, so tied heuristics can accidentally select the best row
unless ties are broken by candidate index or another pre-label field.

Updated next steps:

1. Patch parser validation to enforce `confidence in [0, 1]`.
2. Keep both top-1 and mean market-price error in every selector result.
3. Treat the next supervised task as direction-and-size selection within a
   prompt, not global explanation-class classification.
4. Add text/evidence embeddings only after the numeric baselines are frozen.
5. Evaluate separate targets for market-price matching and final outcome
   correctness once resolution labels are available.
