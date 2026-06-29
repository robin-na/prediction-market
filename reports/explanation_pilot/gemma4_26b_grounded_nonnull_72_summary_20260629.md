# Gemma 4 26B Grounded Non-Null 72-Row Summary

Date: 2026-06-29

This combines the initial 50-row grounded non-null run with the 22-row test
remainder.

## Runs

```text
first_chunk_job_id: 16780895
first_chunk_state: COMPLETED
first_chunk_exit_code: 0:0
first_chunk_requests: 50

remainder_job_id: 16781601
remainder_state: COMPLETED
remainder_exit_code: 0:0
remainder_elapsed: 00:10:38
remainder_requests: 22
```

Combined local outputs:

- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_72_fullnews_bounded_ensemble5_20260629_parsed.jsonl`
- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_72_fullnews_bounded_ensemble5_20260629_scores.csv`
- `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_72_fullnews_bounded_ensemble5_20260629_parsed.errors.jsonl`

## Parse Health

```text
requests: 72
parsed_responses: 68
parse_errors: 4
candidate_explanation_rows: 320
responses_with_5_candidates: 63
mean_candidates_per_parsed_prompt: 4.71
selected_evidence_bound_violations: 8 candidate explanations
```

The 22-row remainder parsed cleanly (`22 / 22`). All parse errors came from
the first 50-row chunk.

## Comparison To Broad 100-Row Full-News Run

| Metric | Broad 100 | Grounded non-null 72 | Interpretation |
| --- | ---: | ---: | --- |
| Candidate flat rate | 0.311 | 0.284 | Slightly less null/flat. |
| Multi-direction prompt rate | 0.674 | 0.721 | More diverse update directions. |
| Median within-prompt posterior std. | 0.010 | 0.017 | More posterior spread across explanations. |
| Mean candidate improvement vs persistence | 0.0034 | 0.0095 | Better average market matching, but still small. |
| Best-candidate mean improvement | 0.0356 | 0.0396 | Slightly better oracle candidate quality. |
| Best-candidate positive rate | 0.535 | 0.691 | Much more often contains at least one useful explanation. |
| Candidate direction match | 0.431 | 0.388 | Worse raw direction match. |

## Interpretation

The grounded non-null filter improves the kind of variation we need for a
market-for-explanations dataset. The generated ensembles are less dominated by
flat/no-update explanations, and more prompts contain competing update
directions. Most importantly, the ensemble often contains at least one candidate
that beats the persistence baseline, even when the average or recommended
candidate is weak.

This is not yet evidence that Gemma can reliably predict market direction from
these explanations. Direction matching is worse than in the broad run, and the
recommended explanation is not much better than the average candidate. The
promising signal is the contrastive one: useful and unhelpful explanations
coexist within the same prompt, giving us something to rank or learn from.

## Recommendation

Before launching all train batches, add or enforce post-hoc validation:

- drop parse failures;
- drop or trim candidates with more than 5 selected evidence IDs;
- score both the LLM-recommended candidate and the best candidate in the
  generated set;
- treat the generated set as a candidate pool for a learned ranker, not as a
  direct forecast.

The next compute step should be one train batch, not all four, unless we decide
that the current schema noise is acceptable for scale-up.
