# Gemma 4 26B Grounded Non-Null 50-Row Summary

Date: 2026-06-29

## Run

```text
run_id: gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629
job_id: 16780895
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:16:53
requests: 50
api_successes: 50
```

Local outputs:

- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_outputs.jsonl`
- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_parsed.jsonl`
- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_scores.csv`

## Parse And Schema Health

```text
parsed_responses: 46 / 50
parse_errors: 4
candidate_explanation_rows: 210
responses_with_5_candidates: 41
responses_with_1_candidate: 5
```

Parse failures:

- 3 responses had no JSON object.
- 1 response returned an empty `candidate_explanations` array.

Constraint issues among parsed candidates:

- 5 candidates selected more than 5 evidence IDs despite the prompt bound.
- These should be treated as post-hoc validation failures or trimmed before
  downstream supervised modeling.

## Market-Matching Scores

All scores compare generated posterior updates against the next market price.
The persistence baseline is the prior probability.

```text
candidate_direction_match_rate: 0.410
candidate_flat_rate: 0.286
mean_delta_error: 0.2115
median_delta_error: 0.1815
mean_baseline_error: 0.2283
mean_candidate_improvement_vs_persistence: 0.0167
candidate_positive_improvement_rate: 0.410
recommended_candidate_mean_improvement: 0.0176
recommended_candidate_positive_improvement_rate: 0.413
```

## Multiple-Explanation Spread

Prompt-level summaries over 46 parsed market rows:

```text
mean_candidates_per_prompt: 4.57
mean_posterior_std_within_prompt: 0.0250
median_posterior_std_within_prompt: 0.0171
prompts_with_more_than_one_update_direction: 34 / 46
mean_best_candidate_improvement_vs_persistence: 0.0500
best_candidate_positive_improvement_rate: 0.717
mean_worst_candidate_improvement_vs_persistence: -0.0205
```

Interpretation: the average generated explanation is only modestly better than
persistence, but the ensemble often contains at least one candidate explanation
that is materially closer to the market update. This supports continuing the
pilot as a dataset of explanation variants rather than a single-posterior
forecasting exercise.

## Explanation Classes

Top class counts across candidate explanations:

```text
source_credibility: 110
evidence_irrelevance: 70
base_rate_calibration: 55
causal_chain: 51
direct_resolution: 35
trend_continuation: 17
resolution_rule: 17
overreaction_correction: 6
market_microstructure: 3
```

## Operational Decision

The run is healthy enough to submit the 22-row grounded non-null test remainder,
but not clean enough to submit all train batches blindly. Train batches should
wait until the 72-row test set is parsed and we decide whether to enforce
post-hoc schema validation, prompt tightening, or candidate trimming.
