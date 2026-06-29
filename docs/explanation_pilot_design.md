# Explanation Ensemble Pilot Design

Date: 2026-06-29

This document defines the first concrete empirical pilot for the
market-for-explanations project.

## Goal

Generate many plausible explanations for the same market transition, score each
explanation against market movement and eventual correctness, and test whether
explanation-level features add predictive signal beyond prices, news, and SWM
attribution scores.

The pilot should answer three practical questions:

1. Can LLMs produce structured, inspectable belief-update explanations for
   prediction-market news?
2. Do explanation classes differ in their ability to predict market updates or
   outcomes?
3. Are explanation features useful enough to justify scaling beyond the pilot?

## Existing Data

The current pilot data were prepared without LLM calls.

Rows:

```text
data/derived/explanation_pilot/kalshi_100row_rows.jsonl
```

Candidate news:

```text
data/derived/explanation_pilot/kalshi_100row_candidates.jsonl
```

Summary:

```text
reports/explanation_pilot/initial_data_prep_summary.md
```

The dataset contains:

```text
100 market-transition rows
334 selected candidate-news records
```

Row buckets:

```text
50 posterior-attributed movement rows
25 unattributed but moved rows
25 stable/no-attribution rows
```

Candidate selection reasons:

```text
top_posterior
top_prior
lexical_hard_negative
random_candidate
```

The generator prompt must not reveal these selection-reason labels unless a
specific diagnostic condition intentionally requires them.

## Unit Of Observation

The generated dataset should have one row per explanation candidate:

```text
market transition r
evidence regime g
generator model m
prompt variant v
sample index s
-> explanation candidate e
```

An explanation candidate is not just text. It is a structured belief-update
proposal with an implied posterior.

## Evidence Regimes

The pilot should keep oracle and deployable settings separate.

### Regime A: Mixed Blind Candidate Packet

Input: the selected candidates currently in
`kalshi_100row_candidates.jsonl`, stripped of selection reason and attribution
scores.

Purpose: test whether the LLM can select among plausible evidence, distractors,
and hard negatives when the packet is small.

Deployability: partially deployable, because the packet may include an oracle
top-posterior candidate selected using hindsight. Use for explanation landscape
analysis, not deployable forecasting claims.

### Regime B: Prior-Selected Deployable Packet

Input: top prior-attributed candidate news and optionally hard negatives,
without posterior scores.

Purpose: test the deployable setting closest to real forecasting. The model only
sees evidence that could have been selected before observing the future move.

Deployability: yes.

### Regime C: Posterior-Selected Oracle Packet

Input: top posterior-attributed candidate news, but hide the after price,
delta, and posterior score.

Purpose: build a taxonomy of explanations when SWM hindsight suggests which
news likely mattered.

Deployability: no. This is an oracle scaffold for analysis and codebook
construction.

### Regime D: History-Only Baseline

Input: market question, description, category, and prior price/history, but no
news.

Purpose: estimate how much of the update comes from price trend or base-rate
reasoning rather than evidence content.

Deployability: yes.

## Explanation Generators

Use LLMs as cheap proposal generators. The paper should not claim novelty from
LLM generation itself.

Recommended first pass:

```text
models: 1 frontier model first, then 2-3 models after schema validation
temperature: moderate, enough to diversify explanations
samples per prompt: 2 or 3
```

Prompt variants:

```text
neutral_forecaster:
  produce the most plausible evidence-to-belief update

source_skeptic:
  focus on source reliability and whether evidence is direct or indirect

base_rate_calibrator:
  focus on whether the evidence should move the prior less or more than a
  naive reader expects

resolution_rule_analyst:
  focus on exact market wording and resolution criteria

contrarian_market_analyst:
  look for reasons the market may underreact or overreact
```

The variants are not final labels. They are a way to induce disagreement so the
pilot can study the distribution of plausible explanations.

## Prompt Inputs

Each prompt should include:

```text
market_id
question
description, if available
category
prior price before the target transition
recent price history up to the prior time, if available
candidate evidence packet
candidate evidence IDs, titles, descriptions, sources, publication times
```

Each prompt should hide:

```text
after price
price delta
price direction
z-score
SWM posterior attribution score
SWM prior attribution score, unless the regime explicitly uses it for retrieval
candidate selection reason
final outcome
```

The prompt should ask the model to reason about what should happen after the
evidence, not why the known move happened.

## Required Output Schema

Each explanation should be valid JSON with these fields:

```json
{
  "pilot_row_id": "kalshi_test_0000",
  "evidence_regime": "mixed_blind",
  "generator_model": "model_name",
  "prompt_variant": "neutral_forecaster",
  "sample_index": 0,
  "selected_evidence_ids": ["candidate_1"],
  "ignored_evidence_ids": ["candidate_2"],
  "posterior_probability": 0.42,
  "delta_from_prior": 0.07,
  "direction": "up",
  "magnitude": "small",
  "explanation_text": "short natural language explanation",
  "update_rule": "generalized reusable update rule",
  "explanation_classes": [
    "source_credibility",
    "base_rate_calibration"
  ],
  "evidence_weights": [
    {
      "candidate_id": "candidate_1",
      "weight": 0.8,
      "role": "supports_upward_update"
    }
  ],
  "calibration_rule": "why the posterior moves this much rather than more",
  "confidence": 0.62
}
```

The numeric posterior is required because we need a scoreable belief update.
The natural-language fields are required because we want reusable explanation
features, not only another forecast.

## Scoring Metrics

Let:

```text
p_t = prior market price before the transition
q_e = explanation-implied posterior
p_{t+h} = observed market price after the transition
y = final outcome, when available
```

Market-update metrics:

```text
mae_to_market = abs(q_e - p_{t+h})
persistence_error = abs(p_t - p_{t+h})
mase_like = mae_to_market / mean(persistence_error)
improvement_vs_persistence = persistence_error - mae_to_market
delta_error = abs((q_e - p_t) - (p_{t+h} - p_t))
posterior_error_to_market = abs(q_e - p_{t+h})
direction_match = sign(q_e - p_t) == sign(p_{t+h} - p_t)
magnitude_bucket_match = bucket(q_e - p_t) == bucket(p_{t+h} - p_t)
```

The primary market-price evaluation should follow the SWM framing: predict the
next market-implied probability and compare against the realized next price,
with persistence/no-change as the main baseline. Directional accuracy is a
secondary diagnostic. Flat is a valid forecast when no update is warranted, but
it is penalized when the realized next market price moves beyond the chosen
dead band.

Outcome metrics, when final resolution is available:

```text
brier_improvement = brier(p_t, y) - brier(q_e, y)
log_score_improvement = log_score(q_e, y) - log_score(p_t, y)
directional_payoff = payoff from trading from p_t toward q_e
```

Future-path metrics, when final outcome is unavailable:

```text
persistence = whether the market keeps moving toward q_e after t+h
reversion = whether the t+h move reverses later
future_path_error = distance between q_e and later price path summaries
```

Attribution metrics:

```text
top_posterior_selected = did the explanation select the SWM hindsight top news?
top_prior_selected = did it select the SWM prior top news?
hard_negative_rejected = did it ignore lexical but non-causal distractors?
```

Attribution metrics are diagnostic, not the main outcome.

## Main Analyses

### 1. Explanation Landscape

Count explanation classes by:

```text
market category
evidence regime
prompt variant
generator model
row bucket
```

Inspect whether classes are coherent and reusable across markets.

### 2. Popularity Versus Correctness Quadrants

Use market-update score for market adoption and outcome score for correctness.

```text
market-aligned and outcome-correct
market-aligned but outcome-wrong
market-contrarian but outcome-correct
market-contrarian and outcome-wrong
```

If final outcomes are missing, use future-path persistence as an interim
correctness proxy and label it clearly as a proxy.

### 3. Same-Class Posterior Variance

For each explanation class, measure the distribution of numeric updates:

```text
mean delta
delta variance
direction entropy
market-update score variance
outcome score variance
```

This directly addresses the concern that the same explanation can lead to
different posteriors. Stable classes are candidates for transferable forecasting
features. Unstable classes may need finer subtypes or explicit calibration
features.

### 4. Value Beyond Baselines

Fit simple supervised models, not a large agent first.

Baselines:

```text
prior price only
price history only
raw news/source/recency features
SWM prior attribution features
generic LLM posterior without structured explanation
```

Explanation-feature models:

```text
baseline + explanation class indicators
baseline + explanation ensemble posterior statistics
baseline + evidence-selection features
baseline + calibration-rule embeddings or labels
```

Targets:

```text
next market price
next market direction
future-path persistence
final outcome, where available
```

Use held-out markets or event IDs, not random explanation rows from the same
market, to avoid leakage.

### 5. Disagreement As Signal

For each market transition, measure disagreement across explanations:

```text
posterior variance
direction disagreement
class entropy
evidence-selection disagreement
model disagreement
prompt-variant disagreement
```

Hypothesis: high disagreement may predict market uncertainty, noisy movement,
reversion, or low outcome correctness.

## Recommended Pilot Scale

Use two stages.

### Stage 1: Smoke Test

```text
20 market rows
2 evidence regimes: mixed_blind, prior_selected
3 prompt variants: neutral, source_skeptic, base_rate_calibrator
1 model
2 samples per prompt
```

Expected explanations:

```text
20 * 2 * 3 * 2 = 240 explanations
```

Purpose: validate JSON schema, prompt clarity, and whether outputs are
inspectable.

### Stage 2: Full 100-Row Pilot

```text
100 market rows
4 evidence regimes: mixed_blind, prior_selected, posterior_oracle, history_only
5 prompt variants
2 samples per prompt
1-3 models
```

Expected explanations:

```text
1 model: 100 * 4 * 5 * 2 = 4,000 explanations
3 models: 12,000 explanations
```

This is large enough to estimate class distributions and score differences, but
small enough for manual audit and rapid iteration.

## Expected Output Files

Generated data:

```text
data/derived/explanation_pilot/kalshi_100row_explanations.jsonl
data/derived/explanation_pilot/kalshi_100row_explanation_scores.csv
data/derived/explanation_pilot/kalshi_100row_explanation_features.csv
```

Documentation:

```text
docs/explanation_taxonomy_codebook.md
docs/explanation_generation_prompt.md
```

Reports:

```text
reports/explanation_pilot/explanation_generation_summary.md
reports/explanation_pilot/explanation_class_counts.csv
reports/explanation_pilot/quadrant_counts.csv
reports/explanation_pilot/examples_market_aligned_outcome_wrong.md
reports/explanation_pilot/examples_market_contrarian_outcome_correct.md
```

Scripts:

```text
scripts/generate_explanation_pilot.py
scripts/score_explanation_pilot.py
scripts/analyze_explanation_pilot.py
```

## Decision Rule After The Pilot

Scale up only if the pilot shows at least one of the following:

- generated explanations are structurally valid and manually interpretable;
- explanation classes show non-trivial variation in market-update score;
- explanation features improve prediction beyond prior price and SWM prior
  attribution in held-out rows;
- disagreement among explanations predicts uncertainty, reversion, or error;
- oracle posterior-selected explanations reveal a coherent taxonomy that the
  prior-selected deployable regime can partially recover.

If none of these hold, the project should pivot away from explanation classes
and toward a narrower analysis of evidence selection or SWM attribution failure
modes.
