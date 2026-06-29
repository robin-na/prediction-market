# Market For Explanations Working Notes

Date: 2026-06-17

This is a running research notebook for the prediction-market explanation
project. It is intentionally less polished than a report. The goal is to keep
track of ideas, motivating posts, references, and runnable next analyses.

## Current Thesis

Prediction markets reveal prices, but they do not directly reveal the evidence
and update rules that produced those prices. A market for explanations would
make the belief-update process itself observable:

```text
prior market state + selected evidence + update rule -> posterior belief shift
```

The core empirical question is:

> Which evidence-to-belief update rules are popular, which are correct, and can
> agents learn from the difference?

This is closely related to Social World Models (SWM), but the unit of analysis
is different. SWM estimates which news event moved a market and how much the
market should move. The explanation project asks which reusable reasoning
operator links the event to the move.

Examples of reusable explanation classes:

- direct-result update: official result or announcement directly resolves part
  of the uncertainty;
- source-credibility update: one source should be weighted more than another;
- resolution-criteria update: the market resolves according to a formal rule
  that differs from the intuitive event;
- base-rate correction: salient evidence should move probability less than
  traders think because the base rate is low;
- causal-chain update: evidence affects an intermediate variable, which affects
  the market outcome;
- overreaction correction: the market moved too far relative to the information
  content of the evidence;
- source-disagreement update: conflicting evidence should widen uncertainty or
  dampen the update;
- endogenous/noise update: movement reflects liquidity, hedging, or coordination
  rather than external evidence.

## Running Artifacts

- Proposal PDF: `reports/explanation_market_proposal/market_for_explanations_proposal.pdf`
- Proposal TeX: `reports/explanation_market_proposal/market_for_explanations_proposal.tex`
- Research design note: `docs/explanation_market_research_design.md`
- Pilot design note: `docs/explanation_pilot_design.md`
- Pilot run log: `docs/explanation_pilot_run_log.md`
- Earlier SWM source-level memo: `reports/no_training/attention_is_not_information_no_training.pdf`
- Mechanism-design related-work note: `docs/evidence_explanations_related_work.md`
- Prior no-training analysis log: `docs/no_training_analysis_log.md`

## 2026-06-29 Research Design Distillation

The current project should be framed as an empirical extension of SWM from
event attribution to explanation attribution. SWM asks which news moved a
market and how much the market should move. This project asks which reusable
belief-update rules connect evidence to posterior changes.

The most important clarification is that an explanation should not be reduced
to "move posterior from X to Y." That fully specified posterior can overfit a
single market transition. We should instead keep separate levels:

```text
explanation class -> update rule -> calibration policy -> posterior instance
```

This makes "same explanation, different posterior" an empirical question rather
than a modeling bug. A class such as source credibility weighting may be useful
only when paired with context-specific calibration features. The pilot should
therefore measure posterior variance within each explanation class.

The clean contribution is not LLM hypothesis generation by itself. LLMs are
cheap generators of candidate explanations. The contribution is market-based
scoring of explanation candidates on two separate targets:

```text
market-update accuracy: does this update predict how other agents update?
outcome/payoff accuracy: does this update predict what eventually happens?
```

Detailed design is now split into:

- `docs/explanation_market_research_design.md`
- `docs/explanation_pilot_design.md`

## Motivating Posts And Screenshots

The LinkedIn screenshots are copied into `docs/assets/` so they are not lost
when clipboard temp files disappear.

### LLM-SoccerArena Post

Screenshot:

```text
docs/assets/linkedin_llm_soccer_arena.png
```

Takeaway: real-world LLM forecasting benchmarks test more than final answer
accuracy. They raise questions about agentic search, internet priors, and
training-data or corpus-specific bias.

Connection to this project:

- A forecast alone hides which information the model retrieved.
- Explanations can expose whether the model checked injuries, odds, source
  consensus, recent form, or other relevant evidence.
- Holding evidence fixed across models lets us study heterogeneous belief
  updates: different agents may update differently from the same evidence.
- The right benchmark is not just "which model predicted the winner?" but "which
  model selected useful evidence and applied a calibrated update rule?"

### Prediction Markets: Information Versus Revenue

Screenshots:

```text
docs/assets/linkedin_prediction_markets_information_vs_revenue_1.png
docs/assets/linkedin_prediction_markets_information_vs_revenue_2.png
```

Takeaway: prediction markets differ in whether they are designed to produce
information or to generate revenue/volume. Sports markets may create high
volume but relatively little new information because outcomes are frequent,
data are clean, and strong models are easy to build. Less regular domains with
dispersed, idiosyncratic information may be where prediction markets add more
public value.

Connection to this project:

- Market volume is not the same as information production.
- Price accuracy is not the same as explanation quality.
- A market may be valuable when it surfaces non-obvious evidence and maps that
  evidence into better beliefs.
- Sports can be a useful control domain: high-volume, clean-data, low-marginal
  explanation value.
- Non-sports political, legal, economic, science, and corporate-event markets
  may have higher explanation value because they require source selection,
  resolution-rule reasoning, causal-chain reasoning, and base-rate correction.

## Key References

- Yu et al. (2026), "Building Social World Models with Large Language Models":
  <https://arxiv.org/pdf/2606.11482>
- SWM-Bench dataset:
  <https://huggingface.co/datasets/ulab-ai/swm-bench>
- SWM code:
  <https://github.com/ulab-uiuc/social-world-model>
- Srinivasan et al. (2025), "Tell Me Why: Incentivizing Explanations":
  <https://arxiv.org/pdf/2502.13410>
- Hossain et al. (2026), "Evidence Markets":
  <https://arxiv.org/pdf/2606.07434>
- Srinivasan et al. (2025), "Self-Resolving Prediction Markets for
  Unverifiable Outcomes":
  <https://arxiv.org/pdf/2306.04305>
- Zhou et al. (2024), "Hypothesis Generation with Large Language Models":
  <https://arxiv.org/abs/2404.04326>
- Liu et al. (2025), "HypoBench: Towards Systematic and Principled
  Benchmarking for Hypothesis Generation":
  <https://arxiv.org/abs/2504.11524>
- Halawi et al. (2024), "Approaching Human-Level Forecasting with Language
  Models":
  <https://arxiv.org/pdf/2402.18563>
- Karger et al. (2025), "ForecastBench":
  <https://arxiv.org/pdf/2409.19839>
- Yang et al. (2025), "LLM-as-a-Prophet: Understanding Predictive Intelligence
  with Prophet Arena":
  <https://arxiv.org/abs/2510.17638>
- Zhang et al. (2026), "Prediction Arena: Benchmarking AI Models on Real-World
  Prediction Markets":
  <https://arxiv.org/abs/2604.07355>

## What We Have Locally

Released or derived data currently present in this workspace:

- `data/swm-bench/Qwen3.5-397B-attributed-data/train.jsonl`
  - 8,546 train rows.
  - Each row has market metadata, 16-step price history, candidate news,
    posterior attribution scores, target next price, future path, and z-score.
- `data/swm-bench/Qwen3.5-397B-attributed-data/test_kalshi.jsonl`
  - 760 Kalshi test rows.
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl`
  - 2,779 raw Kalshi train rows with posterior attributions.
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl`
  - 1,120 raw Kalshi test rows with posterior attributions.
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_prior_attributed_train_2025-11-01.jsonl`
  - Raw Kalshi train rows with prior attribution scores.
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_prior_attributed_test_2025-11-01.jsonl`
  - Raw Kalshi test rows with prior attribution scores.

Not currently local:

- Polymarket splits.
- Qwen3-32B attribution labels.
- SWM trained checkpoints.
- Final market resolution labels joined to every row.
- Platform comments/rationales, likes, replies, or trader histories.

## Things We Can Try To Run

### 1. Explanation-generation pilot

Feasibility: immediate, needs LLM inference but no training.

Build a 100-row pilot from Kalshi test rows:

- 50 rows with at least one positive posterior attribution;
- 50 rows with zero posterior attribution or weak attribution;
- for each row, select top posterior news, top prior news when available, one
  hard negative, and one random candidate.

Generate structured explanations while hiding the realized target price:

```json
{
  "direction": "up/down/none",
  "magnitude": "small/moderate/large",
  "mechanism_class": "...",
  "selected_evidence": "...",
  "update_logic": "...",
  "expected_posterior": 0.0,
  "uncertainty": 0.0
}
```

Why this is useful: it tests whether LLMs can express the missing mechanism
between news and belief update, rather than only assigning an attribution score.

### 2. Explanation taxonomy audit

Feasibility: immediate after pilot.

Hand-audit 30 to 50 generated explanations and refine the mechanism-class
codebook. The key issue is granularity: classes should be reusable across
markets, not one-off rationales.

Outputs:

- a mechanism-class codebook;
- examples of each class;
- failure modes such as post-hoc rationalization, source salience, wrong
  direction, and topical-but-not-causal reasoning.

### 3. Popularity versus correctness quadrants

Feasibility: immediate with SWM-Bench transition labels.

Classify explanations by two axes:

```text
popular: explanation-implied move matches observed next market move
correct: explanation-implied move improves one-step accuracy or later outcome accuracy
```

Initial quadrant:

```text
popular and correct      consensus learning
popular and wrong        persuasive error
unpopular and correct    trader edge / ignored signal
unpopular and wrong      noise
```

Why this is useful: it directly operationalizes the idea that markets may reward
some explanations that are not actually right, and may ignore some explanations
that are later valuable.

### 4. Explanation value beyond SWM attribution

Feasibility: immediate after generating explanations.

Test whether mechanism classes predict one-step moves after controlling for:

- posterior attribution score;
- prior attribution score;
- prior market price;
- recent volatility;
- market category;
- source domain;
- news recency.

Question: do explanation classes add predictive signal beyond "this article was
attributed"?

### 5. Persistence and reversion analysis

Feasibility: likely immediate for main SWM-Bench rows because they include a
future path.

Some market moves revert. Use the `future` field to distinguish:

- evidence that predicts the next move and persists;
- evidence that predicts the next move but later reverts;
- evidence that the market initially ignored but later incorporated.

Why this matters: transition correctness and outcome correctness can diverge.
An explanation can be popular in the short run but wrong by the later path.

### 6. Sports versus non-sports information value

Feasibility: requires additional data, but conceptually high value.

Inspired by the prediction-market information-versus-revenue post. Compare
sports markets against politics/economics/legal/science/company-event markets.

Predictions:

- sports explanations are more redundant and closer to public statistical
  baselines;
- simple models explain more of sports movements;
- non-sports markets have more unexplained belief updates and more valuable
  "unpopular but correct" explanation cases;
- explanation classes like resolution-criteria reasoning and causal-chain
  updates matter more outside sports.

Data needed:

- sports market price histories and outcomes;
- candidate evidence pool such as odds, injury reports, team ratings, news;
- comparable non-sports markets.

### 7. Information-production index for markets

Feasibility: medium; can start with SWM-Bench, stronger with more data.

Create a market-level index of informational value:

```text
information production =
  improvement over public baseline
  + non-redundant evidence surfaced
  + persistence of belief updates
  + difficulty for simple models
  - volume explained by obvious/public baselines
```

This would make the Rothschild-style distinction measurable: markets built for
information versus markets built for engagement/revenue.

### 8. LLM update-bias experiment

Feasibility: medium; needs repeated LLM calls across models/prompts.

Hold the evidence packet fixed and ask different models to produce posterior
updates and explanations.

Questions:

- Do models update differently from identical evidence?
- Do language/source changes shift updates?
- Do some models over-weight national, linguistic, or corpus-specific priors?
- Does adding betting-market information make models converge?

This connects to the LLM-SoccerArena post: model forecasts may reveal retrieval
choices, internet priors, and training-data bias.

### 9. Explanation-memory forecasting agent

Feasibility: later-stage; needs the explanation landscape first.

Give an agent memory of successful explanation classes and compare:

- price history only;
- price history plus raw news;
- price history plus generated explanations;
- price history plus retrieved successful explanation classes;
- price history plus explanations and prior/posterior attribution scores.

Outcome: one-step MASE/MAE/directional accuracy, future-path persistence, and
eventual resolution accuracy.

### 10. Explanation-aware prior attributor

Feasibility: heavier; may require training.

Train a lightweight model to predict posterior attribution using:

- market state;
- candidate news;
- source metadata;
- generated mechanism class;
- explanation-implied direction and magnitude.

Question: does adding explanation structure improve top-event identification
relative to scalar news text and market state alone?

This directly attacks SWM's bottleneck: prior attribution.

## Recommended Immediate Next Run

The best next run is the 100-row explanation-generation pilot.

Why:

- it uses data we already have;
- it does not require training or new platform scraping;
- it tests the central object of the project;
- it gives examples we can inspect qualitatively;
- it creates the labels needed for every later analysis.

Minimum output:

```text
data/derived/explanation_pilot/kalshi_100row_candidates.jsonl
data/derived/explanation_pilot/kalshi_100row_explanations.jsonl
docs/explanation_taxonomy_codebook.md
```

First analysis:

```text
reports/explanation_pilot/
  explanation_class_counts.csv
  quadrant_counts.csv
  examples_popular_wrong.md
  examples_unpopular_correct.md
```

The first pilot should optimize for inspectability rather than scale. If the
explanations are not meaningful on 100 rows, scaling up will not fix the core
problem.

## Initial No-LLM Data Prep Run

Run date: 2026-06-17

Script:

```text
scripts/build_explanation_pilot_candidates.py
```

Generated files:

```text
data/derived/explanation_pilot/kalshi_100row_rows.jsonl
data/derived/explanation_pilot/kalshi_100row_candidates.jsonl
data/derived/explanation_pilot/summary.json
data/derived/explanation_pilot/candidate_selection_summary.csv
reports/explanation_pilot/initial_data_prep_summary.md
```

No LLM calls were used. The script pairs the raw Kalshi posterior-attributed
and prior-attributed SWM test files, then samples:

- 50 posterior-attributed movement rows;
- 25 zero-posterior rows with abs(delta) >= 0.02;
- 25 stable zero-posterior rows.

For each row it selects up to four candidate news items:

- top posterior-attributed news;
- top prior-attributed news;
- lexical hard negative: topically overlapping but posterior-zero;
- deterministic random candidate.

Key counts from the full raw Kalshi test context:

- 1,120 input rows.
- 339 posterior-positive rows (30.3%).
- 781 zero-posterior rows.
- 180 zero-posterior rows still moved by at least two percentage points.
- Top-prior candidate is posterior-positive in 19.3% of all rows with prior
  scores.
- On posterior-positive rows, the top-prior candidate exactly matches the
  top-posterior candidate in 16.6% of rows.

Key counts from the 100-row pilot:

- 100 rows.
- 334 selected candidate-news records.
- top-prior candidate is posterior-positive in 26.5% of pilot rows with prior
  scores.
- lexical hard negatives have mean lexical overlap 0.395 with the market
  question.

Initial observation:

The largest market moves contain several cases where the posterior-attributed
or prior-attributed news appears semantically thin, topically broad, or plainly
off-topic on first inspection. That is not a problem for the project. It is a
reason to run the explanation audit: scalar attribution alone does not tell us
whether the evidence-to-belief link is coherent.

## 2026-06-29 Empirical Checkpoint

The Gemma 4 26B grounded non-null pilot now separates two bottlenecks.

First, there is a selector gap. Gemma can generate multiple plausible
explanation/update candidates, but its recommended candidate is not reliably
the candidate closest to the next market price. A leakage-safe selector audit
found:

```text
random_expected_top1: 0.248
gemma_recommended_top1: 0.396
core_relative_logit_top1: 0.532
max_abs_update_top1: 0.613
```

The earlier high score for "max selected evidence count" was a tie-breaking
artifact caused by using row order from a ranking CSV sorted by market-error
rank. With safe tie-breaking, that heuristic is only 0.435 top-1.

Second, there is a generation gap. Even with a post-hoc oracle selector, the
generated candidate pool is too narrow:

```text
mean_persistence_error: 0.181
mean_oracle_best_candidate_error: 0.140
best_candidate_within_5pp_rate: 0.210
target_bracketed_by_candidate_range_rate: 0.000
```

The dominant generation failure is underreaction. In 38 of 62 held-out prompts,
Gemma generated a candidate in the right direction but not far enough. When the
best candidate has the correct direction, its median update is only about 25%
of the actual market move.

Current implication: before making the selector much more complex, the next
generation prompt should explicitly produce calibration-diverse update models:
strict/no-update, conservative, moderate, aggressive market-reaction, and
contrarian/noise-or-overreaction.
