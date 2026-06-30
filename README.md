# Prediction-Market Explanation Research

This repository tracks the market-for-explanations project: an empirical study
of explanations as belief-update models in prediction markets.

## Current Research Direction

The working definition is:

```text
explanation = prior belief + selected evidence + update rule -> posterior belief
```

The core question is whether we can identify explanation classes that predict
market belief updates, distinguish them from explanation classes that predict
final outcomes, and use that distinction to improve forecasting agents.

## Main Entry Points

- `docs/README.md`: index of working notes, research design docs, saved
  references, and the current feedback deck.
- `reports/explanation_pilot/README.md`: index of pilot results, audit outputs,
  and reproduction commands.
- `docs/explanation_market_research_design.md`: collaborator-facing research
  framing and literature positioning.
- `docs/explanation_pilot_run_log.md`: chronological run log for data prep,
  ORCD jobs, model choices, and interpretation decisions.
- `skills/market_explanation_feedback_deck/SKILL.md`: reusable deck-framing
  playbook for future project presentations.

## Current Empirical Checkpoint

The latest Gemma 4 26B pilot suggests two separate bottlenecks:

- **Selection gap**: generated candidate explanations sometimes contain a
  useful posterior update, but the model does not reliably select it.
- **Generation gap**: even the oracle-best generated candidate often underreacts
  relative to the next market price.

The calibration-diverse stress test showed that simply forcing named update
styles (`no-update`, `conservative`, `moderate`, `aggressive`, `contrarian`) did
not solve the generation gap. The next prompt should force distinct hypotheses
about why the market might move, including visible evidence, no-update,
attention or microstructure, missing public evidence, and overreaction or
reversal.

## Data Policy

Large generated data, requests, model outputs, and downloaded source datasets
live under `data/`, which is intentionally ignored by git. Human-readable
summaries and lightweight audit tables live under `reports/`.
