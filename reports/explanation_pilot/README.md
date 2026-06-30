# Explanation Pilot Reports

This directory collects human-readable summaries and lightweight audit outputs
for the market-for-explanations pilot. Large generated request/output data live
under `data/derived/explanation_pilot/`, which is intentionally ignored by git.

## Current Checkpoint

The current empirical picture has two separate bottlenecks:

1. **Selection gap**: Gemma often generates a useful explanation/update
   candidate but does not reliably recommend the best one.
2. **Generation gap**: even the post-hoc oracle-best Gemma candidate is often
   too conservative relative to the next market price.

Freeform held-out `test72` headline numbers:

```text
random_expected_top1: 0.248
gemma_recommended_top1: 0.396
core_relative_logit_top1: 0.532
oracle_best_candidate_mean_error: 0.140
target_bracketed_by_candidate_range: 0.000
```

The calibration-diverse stress test did **not** close the generation gap. On
the 14 overlapping valid rows, the freeform prompt had a helpful oracle
candidate on 13/14 rows, while the named calibration-profile prompt had a
helpful candidate on only 3/14 rows and collapsed to all-flat on 10/14 rows.

The next generation run should force distinct market-movement hypotheses, not
just named update magnitudes:

```text
visible evidence update
no-informative-evidence/no-update
attention or market-microstructure shock
missing public evidence
overreaction or reversal
```

## Main Summaries

- `gemma4_26b_selector_audit_summary_20260629.md`: leakage-safe selector
  baseline audit; corrects the earlier inflated evidence-count heuristic.
- `gemma4_26b_generation_gap_audit_summary_20260629.md`: oracle-best
  candidate-pool audit showing underreaction and narrow posterior support.
- `gemma4_26b_calibration_diverse_test20_summary_20260629.md`: stress test
  showing that named calibration profiles did not create useful posterior
  diversity.
- `explanation_ranker_training_note_20260629.md`: supervised selector setup,
  target labels, features, and held-out ranker results.
- `gemma4_26b_grounded_nonnull_72_summary_20260629.md`: grounded non-null
  held-out test generation summary.
- `gemma4_26b_grounded_nonnull_50_summary_20260629.md`: first 50 grounded
  non-null held-out requests.
- `gemma4_26b_balanced_stage1_summary_20260629.md`: balanced Stage 1 Gemma
  run.
- `gemma4_26b_balanced_diagnostic_summary_20260629.md`: Gemma diagnostic run
  comparing history-only and oracle evidence conditions.
- `gemma_qwen_comparison_summary_20260629.md`: early Gemma/Qwen comparison.
- `local_reconnect_handoff_20260629.md`: ORCD reconnect and handoff notes.

## Audit Outputs

Selector audit:

```text
gemma4_26b_selector_audit_20260629_selector_performance.csv
gemma4_26b_selector_audit_20260629_stratified_performance.csv
gemma4_26b_selector_audit_20260629_tie_diagnostics.csv
gemma4_26b_selector_audit_20260629_prompt_diagnostics.csv
```

Generation-gap audit:

```text
gemma4_26b_generation_gap_audit_20260629_prompt_level.csv
gemma4_26b_generation_gap_audit_20260629_aggregate.csv
gemma4_26b_generation_gap_audit_20260629_examples.csv
gemma4_26b_generation_gap_parser_fixed_freeform_20260629_prompt_level.csv
gemma4_26b_generation_gap_parser_fixed_freeform_20260629_aggregate.csv
gemma4_26b_generation_gap_caldiv_test20_completions_parser_fixed_20260629_prompt_level.csv
gemma4_26b_generation_gap_caldiv_test20_completions_parser_fixed_20260629_aggregate.csv
```

## Reproduce Local Audits

```bash
/opt/anaconda3/bin/python scripts/audit_explanation_selectors.py
/opt/anaconda3/bin/python scripts/audit_explanation_generation_gap.py
```

Both scripts consume ranking CSVs under `data/derived/explanation_pilot/ranking/`.
