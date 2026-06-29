# Prediction-Market Research Notes

This folder collects working notes, references, and logs for the prediction
market explanation project.

## Main Working Notes

- `market_for_explanations_working_notes.md`: running notebook for the current
  "market for explanations" direction, including motivating posts, references,
  local data inventory, and runnable next analyses.
- `explanation_market_research_design.md`: collaborator-facing summary of the
  research question, contribution, related work, definitions, and open concerns.
- `explanation_pilot_design.md`: concrete pilot protocol for generating and
  scoring explanation ensembles on the 100-row Kalshi/SWM pilot.
- `explanation_pilot_run_log.md`: operational log of explanation-generation
  runs, model choices, ORCD decisions, and run outcomes.
- `explanation_experiment_map.md`: Mermaid diagram of the current Gemma/Qwen
  experiment matrix and scoring flow.
- `evidence_explanations_related_work.md`: short note on mechanism-design papers
  about explanations, evidence, and self-resolving prediction markets.
- `no_training_analysis_log.md`: log for the earlier no-training SWM/Kalshi
  source-level analysis.

## Reports

- `../reports/explanation_market_proposal/market_for_explanations_proposal.pdf`:
  concrete proposal for studying explanation classes as belief-update rules.
- `../reports/explanation_pilot/gemma4_26b_smoke_summary_20260629.md`: summary
  of the initial and strict Gemma smoke runs.
- `../reports/explanation_pilot/gemma4_26b_balanced_stage1_summary_20260629.md`:
  summary of the 20-row Gemma balanced Stage 1 run.
- `../reports/explanation_pilot/gemma4_26b_balanced_diagnostic_summary_20260629.md`:
  diagnostic comparing Gemma `history_only` against `posterior_oracle`.
- `../reports/explanation_pilot/gemma_qwen_comparison_summary_20260629.md`:
  comparison of Gemma 4 26B A4B and Qwen3 14B on Stage 1 and diagnostic runs.
- `../reports/explanation_pilot/README.md`: index of explanation-pilot reports,
  audit outputs, and reproduction commands.
- `../reports/explanation_pilot/explanation_ranker_training_note_20260629.md`:
  supervised selector setup and current ranker results.
- `../reports/explanation_pilot/gemma4_26b_selector_audit_summary_20260629.md`:
  selector baseline audit separating model self-selection from post-hoc
  candidate quality.
- `../reports/explanation_pilot/gemma4_26b_generation_gap_audit_summary_20260629.md`:
  oracle-best candidate-pool audit showing the current generation gap.
- `../reports/no_training/attention_is_not_information_no_training.pdf`: earlier
  source-level SWM/Kalshi memo.

## Saved Post Screenshots

- `assets/linkedin_llm_soccer_arena.png`: post motivating real-world LLM
  forecasting challenges, including agentic search, internet priors, and
  corpus-specific bias.
- `assets/linkedin_prediction_markets_information_vs_revenue_1.png` and
  `assets/linkedin_prediction_markets_information_vs_revenue_2.png`: post
  motivating the distinction between prediction markets built for information
  and markets built for revenue or volume.
