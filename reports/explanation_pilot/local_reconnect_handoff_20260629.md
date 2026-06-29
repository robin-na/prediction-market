# Local Reconnect Handoff: Grounded Non-Null Explanation Run

Date: 2026-06-29

## Current ORCD State

The active ORCD job to check after reconnect is:

```text
job_id: 16780895
run_id: gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629
requests: 50
status before SSH outage: running; first 2 rows parsed cleanly
```

No new ORCD jobs were submitted during the reconnect outage.

## Local Work Completed

The train-derived request files were regenerated with globally distinct row IDs.
The candidate builder now supports:

```text
scripts/build_explanation_pilot_candidates.py --row-id-prefix
```

Existing submitted test requests still use `kalshi_test_####`. Train requests
now use `kalshi_train_####`, avoiding pilot-row-id collisions when test and
train outputs are merged.

## Prepared Request Files

| File | Requests | Notes |
| --- | ---: | --- |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 50 | Already submitted as job `16780895`; do not resubmit until job status is known. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_remaining22_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 22 | Remaining grounded non-null test rows; ready to submit after `16780895` is checked. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 340 | All train grounded non-null requests in one file; useful for inspection, not preferred for first submission. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch001_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 100 | Train batch 1. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch002_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 100 | Train batch 2. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch003_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 100 | Train batch 3. |
| `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch004_fullnews_bounded_ensemble5_20260629_requests.jsonl` | 40 | Train batch 4. |

## Audit

Across the submitted 50-row test chunk, pending 22-row test remainder, and four
train batches:

```text
total_requests: 412
unique_pilot_row_ids: 412
cross_file_duplicate_pilot_row_ids: 0
largest_prompt_chars: 52726
```

The prompt size remains within the intended `MAX_MODEL_LEN=49152` token budget
based on character-level inspection, but final vLLM behavior should still be
checked through the first grounded run before launching train batches.

## Recommended Reconnect Order

1. Check `squeue`/`sacct` for job `16780895`.
2. If it completed, copy back outputs, parse, and inspect parse errors plus
   explanation diversity.
3. If outputs look healthy, submit the 22-row test remainder.
4. Only then submit train batches, preferably one batch first rather than all
   four at once.
