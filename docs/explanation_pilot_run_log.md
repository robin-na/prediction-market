# Explanation Pilot Run Log

This log records concrete runs, design choices, and operational decisions for
the market-for-explanations pilot.

## 2026-06-29: Gemma 4 26B A4B Smoke Setup

Objective: validate the full local-to-ORCD pipeline before running the 100-row
or 240-request explanation pilot.

Model:

```text
google/gemma-4-26B-A4B
```

Serving plan:

- Use the existing ORCD vLLM setup from `../Behavioral_Portability`.
- Use environment `vllm_gemma4_py312`.
- Use `VLLM_USE_FLASHINFER_SAMPLER=0`, matching the existing Gemma 4 run notes.
- Serve and run the client inside one Slurm GPU job, following
  `orcd_pgg_forecast_gemma.sbatch`, so no model client runs on the login node.
- Use the scratch Hugging Face cache at
  `/orcd/scratch/orcd/003/robinna/hf_home`; the Gemma 4 26B A4B checkpoint is
  already present there.

First smoke scale:

```text
5 market-transition rows
2 evidence regimes: mixed_blind, prior_selected
3 prompt variants: neutral_forecaster, source_skeptic, base_rate_calibrator
1 sample per cell
expected requests: 30
```

Reason for starting smaller than the documented Stage 1 pilot:

- validate request schema;
- validate Gemma JSON compliance;
- validate ORCD job plumbing;
- avoid spending GPU time on a malformed prompt or output parser.

Generation constraints:

- Hide `after_p`, `price_delta`, `price_direction`, `z_score`, attribution
  scores, candidate selection reason, and final outcome from the model prompt.
- Keep those fields in request metadata only for later scoring.
- Ask for a numeric posterior plus reusable explanation fields.
- Treat this as infrastructure/schema validation, not as a substantive
  estimate of explanation-class performance.

Local scripts added:

```text
scripts/build_explanation_generation_requests.py
scripts/parse_explanation_generation_outputs.py
```

Local request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_smoke5_20260629_requests.jsonl
```

Selected pilot rows:

```text
kalshi_test_0800
kalshi_test_0271
kalshi_test_0070
kalshi_test_0801
kalshi_test_0150
```

ORCD execution directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_smoke5_20260629
```

Submitted ORCD job:

```text
job_id: 16773303
script: /home/robinna/Behavioral_Portability/repo/scripts/orcd_pgg_forecast_gemma.sbatch
time_limit: 02:00:00
max_model_len: 49152
max_tokens: 2048
temperature: 0.6
concurrency: 1
```

Queue adjustment:

```text
job_id: 16773303
status: canceled while pending on sched_mit_sloan_gpu_r8 due to Resources

job_id: 16773317
partition: mit_preemptable
gres: gpu:a100:1
status: submitted with the same request/output paths
```

Completed smoke outcome:

```text
job_id: 16773317
success_count: 30
error_count: 0
parse_errors: 0
mean_completion_tokens_per_second: 116.21
mean_elapsed_seconds_per_request: 2.43
```

Initial quality observation:

- JSON compliance was excellent.
- Many outputs correctly used `evidence_irrelevance` and kept the posterior at
  the prior when the evidence packet was unrelated.
- Some mixed-packet outputs still stretched weak topical evidence into a causal
  story. Before scaling, the prompt was tightened to make no-selection behavior
  explicit and to require direct relevance to the exact market question.

Strict prompt follow-up:

```text
run_id: gemma4_26b_explanation_strict_smoke5_20260629
local_request_file: data/derived/explanation_pilot/requests/gemma4_26b_strict_smoke5_20260629_requests.jsonl
remote_dir: /home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_strict_smoke5_20260629
job_id: 16773837
partition: mit_preemptable
gres: gpu:a100:1
status: completed
success_count: 30
error_count: 0
parse_errors: 0
mean_completion_tokens_per_second: 118.65
mean_elapsed_seconds_per_request: 1.93
```

Strict-vs-initial smoke comparison:

```text
initial prompt:
  direction_match: 8 / 30
  mean_delta_error: 0.5253
  top_prior_selected: 12 / 30
  hard_negative_selected: 10 / 30
  dominant class: evidence_irrelevance, 19 labels

strict prompt:
  direction_match: 2 / 30
  mean_delta_error: 0.5214
  top_prior_selected: 1 / 30
  hard_negative_selected: 1 / 30
  dominant class: evidence_irrelevance, 28 labels
```

Interpretation:

- The strict prompt improved rejection of weak topical matches.
- It also made the model too reluctant to move its posterior. This is an
  important pilot finding: prompt policy changes can move the generated
  explanations between "over-eager causal storytelling" and "excessive
  evidence skepticism."
- The next run should not simply scale the strict prompt. It should preserve
  strict rejection of distractors while making clear that directly relevant
  evidence should produce a non-zero posterior update.

Builder update:

```text
script: scripts/build_explanation_generation_requests.py
new option: --relevance-policy strict|balanced
default: balanced
metadata field: relevance_policy
```

Balanced policy decision:

- Keep the instruction that most candidate evidence may be distractors.
- Explicitly state that a good answer is selective, not immobile.
- Tell the model to make a non-zero update when evidence directly changes the
  exact market outcome's likelihood.
- Use small updates for weak/indirect evidence, larger updates only for direct
  or highly diagnostic evidence, and no update when no visible item is relevant.

## 2026-06-29: Gemma 4 26B A4B Balanced Stage 1

Objective: test the calibrated relevance policy at a scale large enough to see
whether the explanation ensemble produces useful variation.

Scale:

```text
20 market-transition rows
2 evidence regimes: mixed_blind, prior_selected
3 prompt variants: neutral_forecaster, source_skeptic, base_rate_calibrator
2 samples per cell
expected requests: 240
```

Local request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_balanced_stage1_20260629_requests.jsonl
```

Leakage check:

```text
metadata contains after_p, price_delta, z_score, price_direction, positive_posterior
model-visible prompt contains none of those hidden terms
```

Selected pilot rows:

```text
kalshi_test_0800
kalshi_test_0271
kalshi_test_0070
kalshi_test_0801
kalshi_test_0150
kalshi_test_0020
kalshi_test_0575
kalshi_test_0003
kalshi_test_0091
kalshi_test_1003
kalshi_test_0921
kalshi_test_0011
kalshi_test_0444
kalshi_test_1011
kalshi_test_0058
kalshi_test_0327
kalshi_test_0237
kalshi_test_0056
kalshi_test_0354
kalshi_test_1015
```

Remote execution directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_balanced_stage1_20260629
```

Submitted ORCD job:

```text
job_id: 16773996
partition: mit_preemptable
gres: gpu:a100:1
time_limit: 02:00:00
max_model_len: 49152
max_tokens: 2048
temperature: 0.6
concurrency: 1
status: completed
success_count: 240
error_count: 0
parse_errors: 0
mean_completion_tokens_per_second: 117.76
mean_elapsed_seconds_per_request: 2.24
```

Stage 1 score summary:

```text
rows: 240
direction_match_to_market_delta: 19 / 240
mean_delta_error: 0.3823
median_delta_error: 0.3300
selected_any_evidence: 47 / 240
selected_with_evidence_irrelevance_label: 16 / 240
has_evidence_irrelevance_label: 209 / 240
selected_top_posterior_candidate: 5 / 240
selected_top_prior_candidate: 25 / 240
selected_hard_negative_candidate: 26 / 240
mean_abs_posterior_delta: 0.0046
median_abs_posterior_delta: 0.0000
magnitude_distribution:
  none: 207
  small: 26
  moderate: 6
  large: 1
```

First empirical read:

- The local-to-ORCD-vLLM pipeline is reliable for this task: all three Gemma
  runs produced valid JSON with no parse failures.
- The balanced policy reduced the extreme immobility of the strict prompt only
  slightly. Most outputs still keep the posterior at the prior.
- The model is appropriately skeptical for stable/no-attribution rows, where
  market movement is close to zero.
- For large market moves, the current setup rarely reproduces the market
  direction or magnitude. This means either the visible evidence packet is
  missing the true market-moving information, the model is too conservative, or
  both.
- Some outputs select evidence while also labeling the explanation as
  `evidence_irrelevance`; the parser now tracks this as
  `selected_with_irrelevance`.
- The main conclusion is not yet about which explanation class wins. The first
  conclusion is that evidence selection and update magnitude are themselves
  hard and should be studied explicitly.

Recommended next diagnostic:

```text
Run the same 20 rows with posterior_oracle and history_only regimes.
```

Rationale:

- `history_only` measures the model's baseline tendency to move from the market
  wording and prior alone.
- `posterior_oracle` tests whether the model can update when given the
  candidate evidence that SWM-style attribution says is closest to the
  posterior/moved state.
- If `posterior_oracle` still mostly returns null updates, the bottleneck is
  the explanation/update model. If it improves sharply, the bottleneck is
  evidence retrieval/selection.

## 2026-06-29: Gemma 4 26B A4B Balanced Diagnostic

Objective: distinguish baseline update behavior from evidence-selection
failure.

Scale:

```text
20 market-transition rows
2 evidence regimes: history_only, posterior_oracle
3 prompt variants: neutral_forecaster, source_skeptic, base_rate_calibrator
2 samples per cell
expected requests: 240
```

Local request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_balanced_diagnostic_20260629_requests.jsonl
```

Leakage check:

```text
metadata contains hidden future/attribution fields
model-visible prompt contains none of: after_p, price_delta, price_direction,
z_score, top_posterior, top_prior, posterior_score, prior_score,
selection_reasons, positive_posterior
history_only visible evidence count: 0
posterior_oracle visible evidence count: 1-2
```

Remote execution directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_balanced_diagnostic_20260629
```

Submitted ORCD job:

```text
job_id: 16774267
partition: mit_preemptable
gres: gpu:a100:1
time_limit: 02:00:00
max_model_len: 49152
max_tokens: 2048
temperature: 0.6
concurrency: 1
status: completed
success_count: 240
error_count: 0
parse_errors: 1
mean_completion_tokens_per_second: 120.91
mean_elapsed_seconds_per_request: 1.60
```

Diagnostic score summary:

```text
scored_rows: 239
direction_match_to_market_delta: 4 / 239
mean_delta_error: 0.3814
median_delta_error: 0.3300
selected_any_evidence: 17 / 239
selected_top_posterior_candidate: 4 / 239
selected_hard_negative_candidate: 15 / 239
mean_abs_posterior_delta: 0.0012
median_abs_posterior_delta: 0.0000
magnitude_distribution:
  none: 233
  small: 5
  moderate: 1
```

By evidence regime:

```text
history_only:
  scored_rows: 119
  direction_match_to_market_delta: 0 / 119
  selected_any_evidence: 0 / 119
  mean_abs_posterior_delta: 0.0000
  magnitude: none for all scored rows

posterior_oracle:
  scored_rows: 120
  direction_match_to_market_delta: 4 / 120
  selected_any_evidence: 17 / 120
  selected_top_posterior_candidate: 4 / 120
  mean_abs_posterior_delta: 0.0024
  magnitude: none 114, small 5, moderate 1
```

Interpretation:

- `history_only` is a clean null-update baseline for Gemma.
- `posterior_oracle` does not materially increase posterior movement. Even when
  the evidence packet is restricted to posterior-associated candidate evidence,
  Gemma mostly declines to update.
- This points to an update-model/prompt bottleneck, not only an evidence
  retrieval bottleneck.
- One `history_only` row produced incomplete JSON and is preserved as a parse
  error rather than repaired silently.
```

## 2026-06-29: Qwen3 14B Balanced Stage 1

Objective: test whether the mostly-null-update behavior observed with Gemma is
model-specific.

Model:

```text
Qwen/Qwen3-14B
```

Execution notes:

- The checkpoint is already cached in the ORCD Hugging Face cache as
  `models--Qwen--Qwen3-14B`.
- Use the chat endpoint, not Gemma completion formatting.
- Disable Qwen thinking through
  `{"chat_template_kwargs":{"enable_thinking":false}}`.
- Use the same rows, prompts, relevance policy, temperature, and max output
  tokens as Gemma Balanced Stage 1.

Local request file:

```text
data/derived/explanation_pilot/requests/qwen3_14b_balanced_stage1_20260629_requests.jsonl
```

Remote execution directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/qwen3_14b_balanced_stage1_20260629
```

Submitted ORCD job:

```text
job_id: 16774417
partition: mit_preemptable
gres: gpu:a100:1
exclude: node4309
time_limit: 02:00:00
max_model_len: 32768
max_tokens: 2048
temperature: 0.6
concurrency: 1
status: completed
node: node4501
success_count: 240
error_count: 0
parse_errors: 0
mean_completion_tokens_per_second: 51.65
mean_elapsed_seconds_per_request: 4.69
```

Qwen Stage 1 score summary:

```text
rows: 240
direction_match_to_market_delta: 2 / 240
mean_delta_error: 0.3811
median_delta_error: 0.2986
selected_any_evidence: 52 / 240
selected_with_evidence_irrelevance_label: 18 / 240
has_evidence_irrelevance_label: 206 / 240
selected_top_posterior_candidate: 12 / 240
selected_top_prior_candidate: 46 / 240
selected_hard_negative_candidate: 24 / 240
mean_abs_posterior_delta: 0.0012
median_abs_posterior_delta: 0.0000
magnitude_distribution:
  none: 206
  small: 34
```

## 2026-06-29: Qwen3 14B Balanced Diagnostic

Objective: run the same `history_only`/`posterior_oracle` diagnostic as Gemma
to test whether the posterior-oracle null-update behavior is Gemma-specific.

Local request file:

```text
data/derived/explanation_pilot/requests/qwen3_14b_balanced_diagnostic_20260629_requests.jsonl
```

Remote execution directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/qwen3_14b_balanced_diagnostic_20260629
```

Submitted ORCD job:

```text
job_id: 16774520
partition: mit_preemptable
gres: gpu:a100:1
exclude: node4309,node4501
time_limit: 02:00:00
max_model_len: 32768
max_tokens: 2048
temperature: 0.6
concurrency: 1
status: completed
node: node4417
success_count: 240
error_count: 0
parse_errors: 0
mean_completion_tokens_per_second: 51.78
mean_elapsed_seconds_per_request: 3.74
```

Qwen diagnostic score summary:

```text
rows: 240
direction_match_to_market_delta: 0 / 240
mean_delta_error: 0.3801
median_delta_error: 0.2986
selected_any_evidence: 35 / 240
selected_with_evidence_irrelevance_label: 29 / 240
has_evidence_irrelevance_label: 234 / 240
selected_top_posterior_candidate: 6 / 240
selected_top_prior_candidate: 6 / 240
selected_hard_negative_candidate: 34 / 240
mean_abs_posterior_delta: 0.0002
median_abs_posterior_delta: 0.0000
magnitude_distribution:
  none: 234
  small: 6
```

By diagnostic regime:

```text
history_only:
  scored_rows: 120
  direction_match_to_market_delta: 0 / 120
  selected_any_evidence: 0 / 120
  mean_abs_posterior_delta: 0.0000
  magnitude: none for all rows

posterior_oracle:
  scored_rows: 120
  direction_match_to_market_delta: 0 / 120
  selected_any_evidence: 35 / 120
  selected_top_posterior_candidate: 6 / 120
  mean_abs_posterior_delta: 0.0003
  magnitude: none 114, small 6
```

Model-comparison read:

- Qwen3 14B does not fix the null-update issue. It produces even smaller
  posterior movement than Gemma under the same prompt schema.
- Qwen selects evidence somewhat more often than Gemma in Stage 1 and
  posterior-oracle regimes, but this does not translate into meaningful
  posterior movement.
- The pattern is therefore not only Gemma-specific. The immediate bottleneck is
  likely the prompt/schema/evidence representation for eliciting update
  functions, not just a single model's conservatism.
```

## 2026-06-29: SWM Resolution Label Audit

Question checked: do the local SWM benchmark files already include final
resolution or settlement labels? This was checked with a full-pass top-level
key scan over each file, plus sample nested-key inspection.

Files inspected:

```text
data/swm-bench/Qwen3.5-397B-attributed-data/test_kalshi.jsonl
data/swm-bench/Qwen3.5-397B-attributed-data/train.jsonl
data/derived/explanation_pilot/kalshi_100row_rows.jsonl
data/derived/explanation_pilot/kalshi_100row_candidates.jsonl
```

Result:

- No explicit resolution, settlement, final outcome, winner, answer, or status
  field appears in the inspected local files.
- The raw SWM records contain `target`, `future`, `history`, `z_score`,
  `news`, and `attributions`. Here `target` is a later market price/time point,
  not a settled outcome.
- The 100-row pilot derived files contain price-transition fields such as
  `before_p`, `after_p`, `price_delta`, `price_direction`, and SWM attribution
  summaries such as `max_posterior_score` and `positive_posterior`, but no final
  outcome label.

Implication:

- We can score market-update alignment immediately: whether an explanation's
  implied posterior matches the observed next market move.
- We cannot yet score final payoff/resolution correctness from SWM alone.
- Until settlement labels are joined from Kalshi/Polymarket or another source,
  use future-path persistence/reversion as a clearly labeled interim correctness
  proxy.

Current evaluation scope:

- Focus the pilot evaluation on market-price prediction: compare the
  explanation-implied posterior to the observed next market price.
- Treat final resolution/payoff correctness as a later join task, not part of
  the current SWM-only pilot.

## 2026-06-29: Market-Price Evaluation Snapshot

Main score files:

```text
data/derived/explanation_pilot/outputs/gemma4_26b_balanced_stage1_20260629_scores.csv
data/derived/explanation_pilot/outputs/qwen3_14b_balanced_stage1_20260629_scores.csv
data/derived/explanation_pilot/outputs/gemma4_26b_balanced_diagnostic_20260629_scores.csv
data/derived/explanation_pilot/outputs/qwen3_14b_balanced_diagnostic_20260629_scores.csv
```

Metric definitions:

```text
p_t = prior market price
p_{t+h} = observed next market price
q_e = explanation-implied posterior

posterior_error_to_market = |q_e - p_{t+h}|
market-price baseline / persistence error = |p_t - p_{t+h}|
improvement_vs_persistence = |p_t - p_{t+h}| - |q_e - p_{t+h}|
direction_match = sign(q_e - p_t) == sign(p_{t+h} - p_t)
persistence baseline = q_e = p_t
```

Evaluation framing:

- The primary market-price question is whether `q_e` predicts the next
  market-implied probability better than the persistence baseline `q_e = p_t`.
- Directional accuracy is secondary. A flat forecast is not inherently a bug:
  it is correct when the market should not move, and wrong when the observed
  next price moves outside the chosen dead band.
- For SWM comparability, report MAE/MASE-like error and improvement over
  persistence before interpreting direction-match rates.

Current main run: balanced Stage 1 on the deterministic 20-row pilot subset.
Each model has 240 generated explanation records: 20 rows x 2 evidence regimes
x 3 prompt variants x 2 samples.

Gemma 4 26B Stage 1:

```text
direction_match_to_market_delta: 19 / 240 = 7.9%
mean_market_abs_delta / persistence error: 0.3800
mean_posterior_error_to_market: 0.3823
MASE-like error vs persistence: 1.006
mean_improvement_vs_persistence: -0.0023
mean_abs_explanation_delta: 0.0046
flat_explanation_direction: 206 / 240
selected_any_evidence: 47 / 240
selected_top_posterior_candidate: 5 / 240
selected_hard_negative_candidate: 26 / 240
```

Qwen3 14B Stage 1:

```text
direction_match_to_market_delta: 2 / 240 = 0.8%
mean_market_abs_delta / persistence error: 0.3800
mean_posterior_error_to_market: 0.3811
MASE-like error vs persistence: 1.003
mean_improvement_vs_persistence: -0.0012
mean_abs_explanation_delta: 0.0012
flat_explanation_direction: 203 / 240
selected_any_evidence: 52 / 240
selected_top_posterior_candidate: 12 / 240
selected_hard_negative_candidate: 24 / 240
```

Row-level upper-bound check:

- Gemma Stage 1 contains at least one direction-matching candidate for 10 / 20
  pilot rows, but the best-candidate mean improvement over persistence is only
  0.0112. The direction can sometimes be right, but the magnitude is usually
  much too small.
- Qwen Stage 1 contains at least one direction-matching candidate for only
  1 / 20 rows, with essentially zero best-candidate improvement.

Diagnostic run:

- `history_only` is a sanity check and correctly stays flat.
- `posterior_oracle` shows that even when the evidence packet includes
  hindsight-selected candidates, the current prompt/schema still yields mostly
  flat posteriors.
- Gemma posterior-oracle direction matches only 4 / 120 records; Qwen
  posterior-oracle direction matches 0 / 120 records.

Interpretation:

- The current explanation generator is not yet useful as a market-price
  forecaster: it does not beat the persistence/no-change baseline on average.
- The failure mode is not just evidence absence. It is mostly posterior
  conservatism: generated explanations often reject or weakly select evidence
  and then keep the posterior near the prior.
- The next design iteration should elicit larger, explicitly market-calibrated
  posterior moves and separate evidence relevance from update magnitude.

## 2026-06-29: Gemma Flat-Case Audit

Question checked: when Gemma stays flat, are the explanations reasonable?

Input inspected:

```text
data/derived/explanation_pilot/outputs/gemma4_26b_balanced_stage1_20260629_parsed.jsonl
data/derived/explanation_pilot/outputs/gemma4_26b_balanced_stage1_20260629_scores.csv
data/derived/explanation_pilot/kalshi_100row_candidates.jsonl
```

Aggregate flat counts:

```text
Gemma Stage 1 flat outputs: 206 / 240

By row bucket:
posterior_attributed_move: 68 / 84 flat
stable_no_attribution:     65 / 72 flat
unattributed_moved:        73 / 84 flat

Flat outputs with no visible positive posterior-attributed candidate:
stable_no_attribution + unattributed_moved = 138 / 206

Flat outputs with a visible positive posterior-attributed candidate:
posterior_attributed_move = 68 / 206
```

Interpretation:

- Many flat explanations are reasonable as local evidence-relevance judgments.
  The visible candidate packets are often unrelated keyword artifacts.
- This does not make them good market-price forecasts. If the relevant market
  mover is absent from the packet, a locally reasonable flat forecast will still
  miss the next market price.
- The hard cases are posterior-attributed rows where SWM's hindsight score says
  a candidate mattered, but the candidate appears only weakly or indirectly
  connected to the market resolution. These cases are useful for auditing SWM
  posterior labels and for designing a less brittle evidence packet.

Reasonable flat examples:

- `kalshi_test_0020`: West Virginia Senate race, prior 0.0464 to next price
  0.0500. Visible evidence was about Arizona State football, Staten Island voter
  registration, and Pennsylvania's governor race. Gemma kept the posterior at
  0.0464 and said the evidence did not affect the West Virginia Senate race.
- `kalshi_test_0271`: Bucharest mayoral election, prior 0.4110 to next price
  0.8637. Visible evidence was about Arsenal, Powerball, and the stock market.
  Gemma's flat explanation is locally reasonable, but the market moved sharply,
  so this is a retrieval or evidence-packet failure.
- `kalshi_test_0800`: countries creating crypto reserves, prior 0.0300 to next
  price 0.8900. Visible evidence included an India film festival, COP30 fossil
  fuels, a G20 summit, and a Ukraine peace plan. Gemma judged no item directly
  relevant. The top SWM posterior candidate was the G20 article, which looks
  weakly connected at best.
- `kalshi_test_0444`: Trump saying "Crooked Hillary", prior 0.1100 to next
  price 0.8869. Visible evidence concerned a federal holiday, housing reform,
  and rare earth restrictions after a Trump-China deal. Gemma's flat explanation
  looks reasonable; the market move is not explained by the visible packet.

Borderline or possibly too-strict flat examples:

- `kalshi_test_0354`: Gary Peters voting on the next omnibus, minibus, or CR,
  prior 0.7543 to next price 0.0432. Visible evidence included a Senate vote on
  a continuing resolution and whether Democrats would support it. Gemma argued
  this was not Peters-specific enough. That is defensible, but possibly too
  strict because broader Senate-vote context may affect the market.
- `kalshi_test_0575`: Death by Lightning Golden Globe limited-series
  nomination, prior 0.8998 to next price 0.0786. Visible evidence included a
  topical article about shows like Death by Lightning, but not nomination or
  awards evidence. Gemma's flat call is plausible, though it shows the current
  prompt may discount indirect popularity/critical-reception evidence.

Design implication:

- The next experiment should separate two failures:
  1. evidence retrieval did not surface resolution-relevant information;
  2. relevant or semi-relevant information was surfaced, but the model refused
     to translate it into a calibrated price move.
- For evaluation, keep flat as a valid action. Score it against the
  persistence/no-change baseline rather than treating it as a categorical bug.

Clarification on "optimized retrieval" in this pilot:

- The 100-row pilot is not random news retrieval. It is a controlled candidate
  panel built from SWM raw Kalshi posterior-attributed and prior-attributed
  files.
- Candidate selection per row attempts to include:
  - top posterior-attributed news, if the row has positive posterior
    attribution;
  - top prior-attributed news;
  - lexical hard negative;
  - random candidate.
- This is optimized for contrastive evaluation and manual diagnosis, not for
  giving the LLM the full best possible evidence set.
- In the Stage 1 run, the selected 20-row subset contains 7
  posterior-attributed-move rows, 7 unattributed-moved rows, and 6 stable
  no-attribution rows.
- For posterior-attributed rows under `mixed_blind`, the top posterior item is
  visible in all 42 requests. Gemma still stayed flat in 35 / 42 of those.
  Therefore those failures are not simply missing retrieval; they are cases
  where Gemma rejects, discounts, or under-calibrates an SWM-attributed item.
- Under `prior_selected`, the top posterior item is usually hidden unless it is
  also the top prior item. In Stage 1, only 6 / 42 posterior-attributed
  `prior_selected` requests had the top posterior item visible.
- Across the full 100-row pilot, top-prior candidates are posterior-positive in
  only 26 / 98 cases, and the exact top-prior/top-posterior candidate coincides
  in only 8 cases. Prior retrieval is therefore a weak proxy for hindsight
  posterior relevance.

## 2026-06-29: SWM Evidence-Gap Audit

Question checked: do the same flat/retrieval-gap patterns appear in SWM's own
attributed data?

Files inspected:

```text
data/swm-bench/Qwen3.5-397B-attributed-data/test_kalshi.jsonl
data/swm-bench/Qwen3.5-397B-attributed-data/train.jsonl
data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl
data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl
```

Compact Qwen3.5-attributed release:

```text
test_kalshi rows: 760
rows with any positive posterior-attributed news: 142 / 760 = 18.7%
rows with no positive posterior-attributed news: 618 / 760 = 81.3%

large moves with no positive posterior-attributed news:
abs_delta >= 0.05: 204 / 297 = 68.7%
abs_delta >= 0.10:  74 / 115 = 64.3%
abs_delta >= 0.20:  21 / 39  = 53.8%
abs_delta >= 0.50:   6 / 10  = 60.0%
```

Raw Kalshi posterior-attributed split:

```text
test rows: 1120
rows with any positive posterior-attributed news: 339 / 1120 = 30.3%

large moves with no positive posterior-attributed news:
abs_delta >= 0.05: 14 / 325 = 4.3%
abs_delta >= 0.10: 11 / 171 = 6.4%
abs_delta >= 0.20:  5 / 77  = 6.5%
abs_delta >= 0.50:  0 / 21  = 0.0%

train rows: 2779
rows with any positive posterior-attributed news: 1174 / 2779 = 42.2%

large moves with no positive posterior-attributed news:
abs_delta >= 0.05: 30 / 1147 = 2.6%
abs_delta >= 0.10: 12 / 538  = 2.2%
abs_delta >= 0.20:  5 / 197  = 2.5%
abs_delta >= 0.50:  0 / 29   = 0.0%
```

Interpretation:

- Yes, SWM data contain many cases where no candidate news is assigned positive
  posterior responsibility. This is especially true in the compact
  Qwen3.5-attributed release, where evidence lists are much shorter.
- In the raw Kalshi posterior-attributed files, large market moves usually do
  receive at least one positive posterior attribution. That means SWM's full
  candidate pool often contains something the posterior attributor can use.
- However, "posterior-attributed" does not always mean "human-obviously
  resolution-relevant." Some high-scored articles are broad, indirect, or look
  weakly connected to the market wording.

Rough lexical-overlap diagnostic for raw Kalshi test:

```text
posterior-positive rows: 339
top posterior article lexical overlap with market question:
mean: 0.250
median: 0.200
overlap <= 0.20: 173 / 339 = 51.0%
overlap <= 0.30: 232 / 339 = 68.4%

Among abs_delta >= 0.20 posterior-positive rows:
overlap <= 0.30: 48 / 72 = 66.7%
```

This lexical diagnostic is not a direct irrelevance measure. Many true links
are semantically relevant despite low lexical overlap. But it shows why a
strict LLM relevance judge may reject SWM-attributed evidence unless prompted to
reason through indirect market mechanisms.

Examples:

- Compact release, large move with no positive attribution: `KXGGGNOMLSERIES-25-DEA`
  moved from 0.8998 to 0.0786. The short compact evidence packet contained a
  Nick Offerman podcast item and a "12 TV Shows Like Netflix's Death By
  Lightning" article, both scored 0.0 in the compact file.
- Raw release, same market transition: the "12 TV Shows Like Netflix's Death By
  Lightning" article receives posterior score 0.7. This is topical but not a
  direct nomination/awards announcement, so Gemma's flat response is
  understandable under a strict direct-evidence standard.
- Raw release, `KXTRUMPSAYNICKNAME-26JAN01-CROO`: the market moved from 0.1100
  to 0.8869. Top posterior items included rare-earth restrictions after a
  Trump-China deal, a federal-holiday/open-closed article, bank-stock gains, and
  a Trump Christmas message. These are Trump-related, but the link to saying
  "Crooked Hillary" is weak without additional context.
- Raw release, `KXGGGNOMDRAMATV-25-SLO`: a large Slow Horses Golden Globe
  nomination move has top posterior items such as a weekly style-moments article
  and a Landman renewal article. These look indirect or noisy relative to the
  exact resolution criterion.

Design implication:

- Our pilot should not treat SWM posterior attribution as causal truth.
- We should explicitly distinguish:
  1. SWM-attributed evidence that is direct and human-plausible;
  2. SWM-attributed evidence that is indirect but plausibly market-relevant;
  3. SWM-attributed evidence that looks spurious or proxy-like.
- The next experiment should include a retrieval/evidence-quality label in
  addition to the market-price error, otherwise we conflate bad explanation
  generation with weak evidence packets or noisy posterior labels.

## 2026-06-29: Expanded Evidence Packet Setup

Question checked: does SWM also see only 2-4 compact news items, and can we
increase the number of visible items for our LLM prompt?

SWM news-count audit:

```text
Compact Qwen3.5-attributed Kalshi test:
rows: 760
mean news count: 11.67
median news count: 5
p75: 16
p90: 34
max: 82

Raw Kalshi posterior-attributed test:
rows: 1120
mean news count: 69.10
median news count: 100
p75: 100
p90: 100
max: 100

Raw Kalshi posterior-attributed train:
rows: 2779
mean news count: 55.87
median news count: 53
p75: 100
p90: 100
max: 100
```

Answer:

- No, the raw SWM Kalshi files often contain far more than 2-4 news items. Many
  rows have the full 100 candidate news records.
- The compact Qwen3.5 release is smaller, with median 5 news records.
- Our first explanation prompt deliberately shrank the visible packet to 2-4
  items for controlled contrastive diagnosis, not because SWM only had 2-4
  items.
- The released/news fields are still compact news records: title, description,
  source, URL, and timestamp. They are not full article bodies.

Code change:

- `scripts/build_explanation_pilot_candidates.py` now supports:
  - `--top-posterior-k`
  - `--top-prior-k`
  - `--hard-negative-k`
  - `--random-k`
  - `--output-prefix`
- `scripts/build_explanation_generation_requests.py` now recognizes expanded
  `posterior_top_k`, `prior_top_k`, and `lexical_hard_negative_k` reason labels
  when building `posterior_oracle` and `prior_selected` packets.

Expanded candidate panel generated:

```text
command:
python scripts/build_explanation_pilot_candidates.py \
  --output-prefix kalshi_100row_expanded_k5 \
  --top-posterior-k 5 \
  --top-prior-k 5 \
  --hard-negative-k 3 \
  --random-k 2

outputs:
data/derived/explanation_pilot/kalshi_100row_expanded_k5_rows.jsonl
data/derived/explanation_pilot/kalshi_100row_expanded_k5_candidates.jsonl
data/derived/explanation_pilot/kalshi_100row_expanded_k5_summary.json
data/derived/explanation_pilot/kalshi_100row_expanded_k5_candidate_selection_summary.csv
reports/explanation_pilot/kalshi_100row_expanded_k5_data_prep_summary.md

rows: 100
candidates: 1100
candidate config:
  top_posterior_k: 5
  top_prior_k: 5
  hard_negative_k: 3
  random_k: 2
```

Expanded 20-row request file generated:

```text
data/derived/explanation_pilot/requests/gemma4_26b_expanded_k5_stage1_20260629_requests.jsonl

row_limit: 20
regimes: history_only, mixed_blind, prior_selected, posterior_oracle
prompt variants: neutral_forecaster, source_skeptic, base_rate_calibrator
samples_per_cell: 1
requests: 237
unique rows: 20
```

Visible evidence counts in expanded request file:

```text
history_only:
  mean visible evidence: 0
  max prompt length: ~900 rough tokens

mixed_blind:
  mean visible evidence: 10.15
  median visible evidence: 10
  max visible evidence: 15
  max prompt length: ~2449 rough tokens

prior_selected:
  mean visible evidence: 7.45
  median visible evidence: 8
  max visible evidence: 8
  max prompt length: ~1810 rough tokens

posterior_oracle:
  mean visible evidence: 4.21
  median visible evidence: 3
  max visible evidence: 8
  max prompt length: ~1796 rough tokens
```

Next inference option:

- Run Gemma on this expanded request file before changing the prompt further.
  This isolates whether the earlier flat behavior was caused by tiny packets or
  by the model/prompt discounting indirect evidence.
- If expanded evidence still stays flat, the next change should be forecast
  first: ask for next market price before explanation and force a movement
  bucket before the numeric posterior.

## 2026-06-29: Full-News Gemma Ensemble Run

User decision:

- Expand the retrieval environment to be as close as possible to the SWM
  baseline.
- Run Gemma only.
- Keep the input environment close to SWM and change the explanation output:
  ask the LLM to generate multiple explanation/posterior candidates in a single
  prompt.

Implementation choices:

- Use the raw Kalshi SWM candidate-news pool for the same 100-row pilot.
- Expose up to 100 compact news records per row in the model-visible prompt.
- Include pre-target market price history, filtered so no `after_t` or later
  prices are visible.
- Hide all target/scoring fields from the prompt: `after_p`, `after_t`,
  `price_delta`, `price_direction`, `z_score`, attribution scores, and selection
  reasons remain metadata only.
- Ask for exactly 5 candidate explanations/posteriors per request in one JSON
  object.

Code updates:

```text
scripts/build_explanation_pilot_candidates.py
  added full-news/top-K candidate controls:
    --top-posterior-k
    --top-prior-k
    --hard-negative-k
    --random-k
    --output-prefix
  added pre-target price_history to row files

scripts/build_explanation_generation_requests.py
  added price history rendering
  added --num-explanations
  added ensemble JSON schema

scripts/parse_explanation_ensemble_outputs.py
  added parser/scorer that flattens one model response into one row per
  candidate explanation
```

Full-news candidate panel:

```text
command:
python scripts/build_explanation_pilot_candidates.py \
  --output-prefix kalshi_100row_fullnews \
  --top-posterior-k 100 \
  --top-prior-k 100 \
  --hard-negative-k 0 \
  --random-k 100

outputs:
data/derived/explanation_pilot/kalshi_100row_fullnews_rows.jsonl
data/derived/explanation_pilot/kalshi_100row_fullnews_candidates.jsonl
data/derived/explanation_pilot/kalshi_100row_fullnews_summary.json
data/derived/explanation_pilot/kalshi_100row_fullnews_candidate_selection_summary.csv
reports/explanation_pilot/kalshi_100row_fullnews_data_prep_summary.md

rows: 100
candidates: 7732
mean visible news in final request file: 77.32
median visible news: 100
max visible news: 100
```

Gemma request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_fullnews_ensemble5_20260629_requests.jsonl

requests: 100
regime: mixed_blind
prompt variant: neutral_forecaster
samples_per_cell: 1
num_explanations_per_request: 5
largest prompt: 52,521 characters, roughly 13.1k tokens
leakage check: no hidden target/attribution terms found in prompt text
```

Remote execution:

```text
remote_dir:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_20260629

remote_request_file:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_20260629/requests.jsonl

request_size: 6.1M
local_request_sha256:
2d55a7045ebf596e8d9fd0cbe5453fcf660ad035122471fba42ebd44843dc2e9
```

Submitted ORCD job:

```text
job_id: 16776414
partition: mit_preemptable
node: node4417
model: google/gemma-4-26B-A4B
max_model_len: 49152
max_tokens: 6144
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
excluded_nodes: node4309,node4501
status_at_submission_check: running; vLLM loading checkpoint
```

Expected output paths on ORCD:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_20260629/gemma4_26b_fullnews_ensemble5_20260629_outputs.jsonl
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_20260629/gemma4_26b_fullnews_ensemble5_20260629_timing_summary.json
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_20260629/gemma4_26b_fullnews_ensemble5_20260629_per_request_timing.csv
```

### 2026-06-29 status audit and corrected Gemma rerun

The first full-news Gemma ensemble job finished at the Slurm level but did not
produce usable inference outputs.

```text
job_id: 16776414
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:23:01
node: node4417
model_outputs_success_count: 0
model_outputs_error_count: 100
```

Observed failure mode:

```text
RuntimeError('chat completion failed after 4 attempts: HTTP Error 400: Bad Request')
```

The vLLM server log identifies the root cause as a chat-template mismatch:

```text
ChatTemplateResolutionError: As of transformers v4.44, default chat template is no longer allowed,
so you must provide a chat template if the tokenizer does not define one.
```

Interpretation: this was a runner configuration issue, not a prompt/data issue.
The submitted job used the chat-completions endpoint. Earlier successful Gemma
runs used the completions endpoint with the repository's Gemma turn-format
prompting path.

Corrected rerun:

```text
job_id: 16778683
status_at_submission_check: RUNNING
partition: mit_preemptable
node: node4417
remote_dir:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_completion_20260629

request_file:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_ensemble5_completion_20260629/requests.jsonl

request_size: 6.1M
model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
extra_body_json: {"stop":["<end_of_turn>"]}
max_model_len: 49152
max_tokens: 6144
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
excluded_nodes: node4309,node4501
```

The corrected rerun uses the same 100 full-news requests and writes to a fresh
output directory so it will not resume from the all-error output file produced
by the failed chat-endpoint run.

### 2026-06-29 compact-schema full-news rerun

Monitoring of the corrected completions-endpoint rerun showed that the endpoint
fix worked, but the output schema was too verbose for full-news packets.

```text
job_id: 16778683
state_after_audit: CANCELLED
elapsed_before_cancel: 00:06:19
rows_written_before_cancel: 5
parse_audit_on_first_rows: 1 of first 4 rows parsed as complete JSON candidate lists
primary_failure_mode: outputs truncated while enumerating long ignored_evidence_ids or evidence_weights arrays
```

Interpretation: this was a prompt/schema issue. The request asked the model to
list every ignored evidence ID for each of five explanation candidates. With
77-100 visible news items, that made many otherwise useful responses too long
and caused invalid JSON truncation.

Schema adjustment:

```text
removed from model-visible required schema:
ignored_evidence_ids

added:
nonselected_evidence_summary

bounded:
selected_evidence_ids: at most 5 IDs
evidence_weights: at most 5 objects
```

Local compact request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_fullnews_compact_ensemble5_20260629_requests.jsonl

requests: 100
regime: mixed_blind
prompt_variant: neutral_forecaster
samples_per_cell: 1
num_explanations_per_request: 5
visible evidence mean: 77.32
visible evidence median: 100
visible evidence max: 100
largest prompt: 52,885 characters
```

Submitted compact ORCD rerun:

```text
job_id: 16778846
status_at_submission_check: PENDING (Priority)
partition: mit_preemptable
remote_dir:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_compact_ensemble5_20260629

request_file:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_compact_ensemble5_20260629/requests.jsonl

model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
extra_body_json: {"stop":["<end_of_turn>"]}
max_model_len: 49152
max_tokens: 4096
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
excluded_nodes: node4309,node4501
```

Initial output audit:

```text
status: running on node4417
rows_written_at_audit: 2
parse_rows: 2 / 2
candidate_counts: [5, 5]
array_bound_violations: 0
```

Non-null row availability audit:

```text
Kalshi test split:
  all rows: 1120
  non-null positive-posterior rows: 339
  grounded rows: 236
  grounded non-null positive-posterior rows: 72

Kalshi train split:
  all rows: 2779
  non-null positive-posterior rows: 1174
  grounded rows: 836
  grounded non-null positive-posterior rows: 340
```

The submitted job uses 50 grounded non-null rows because it was built from the
fixed 100-row grounded pilot panel. There are 22 additional grounded non-null
rows in the Kalshi test split, plus 340 grounded non-null rows in train if we
want a larger training-style explanation dataset.

Initial compact-output audit:

```text
status: running on node4417
rows_written_at_audit: 4
json_candidate_list_rows: 4 / 4
candidate_counts: [5, 5, 5, 5]
max_selected_evidence_ids_per_candidate: 5
max_evidence_weights_per_candidate: 4
bad_parse_count: 0
```

Interpretation: the compact schema appears to fix the JSON truncation problem
seen in job `16778683`, while preserving the intended five-explanation ensemble
per market transition.

Follow-up audit over the first seven compact rows showed one remaining
truncation failure:

```text
job_id: 16778846
state_after_followup_audit: CANCELLED
elapsed_before_cancel: 00:05:27
rows_written_before_cancel: 7
json_candidate_list_rows: 6 / 7
bad_parse_count: 1
failure_mode: one candidate violated the at-most-5 selected_evidence_ids constraint and began enumerating many IDs
```

Tighter bounded-schema change:

```text
selected_evidence_ids: must contain at most 5 IDs
evidence_weights: must contain at most 5 objects
evidence_weights: must refer only to selected_evidence_ids
evidence_weights: cannot use the role "irrelevant"
prompt-level guard: no output array other than candidate_explanations and explanation_classes may exceed 5 items
```

Local bounded request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_fullnews_bounded_ensemble5_20260629_requests.jsonl

requests: 100
regime: mixed_blind
prompt_variant: neutral_forecaster
samples_per_cell: 1
num_explanations_per_request: 5
visible evidence mean: 77.32
visible evidence median: 100
visible evidence max: 100
largest prompt: 53,407 characters
```

Submitted bounded ORCD rerun:

```text
job_id: 16779182
status_at_submission_check: PENDING (Priority)
partition: mit_preemptable
remote_dir:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_bounded_ensemble5_20260629

request_file:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_bounded_ensemble5_20260629/requests.jsonl

model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
extra_body_json: {"stop":["<end_of_turn>"]}
max_model_len: 49152
max_tokens: 3072
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
excluded_nodes: node4309,node4501
```

Initial bounded-output audit:

```text
status: running on node4417
rows_written_at_audit: 7
json_candidate_list_rows: 7 / 7
candidate_counts: [5, 5, 5, 5, 5, 1, 5]
max_selected_evidence_ids_per_candidate: 5
max_evidence_weights_per_candidate: 5
array_bound_violations: 0
bad_parse_count: 0
```

Interpretation: the stricter bounded prompt is producing valid, compact
JSON on the first completed rows. One row returned only one candidate because
the model treated all visible evidence as irrelevant; this is not a truncation
failure, and the parser records `num_candidates_in_response` so underfilled
ensembles can be filtered or analyzed. Continue monitoring until the 100-row
run finishes, then copy outputs locally and parse with
`scripts/parse_explanation_ensemble_outputs.py`.

Latest bounded-output audit:

```text
rows_written_at_audit: 29
lenient_json_candidate_list_rows: 26 / 29
candidate_count_hist_at_29_rows: {1: 1, 5: 25}
array_bound_violations: 0
underfilled_count: 1
bad_rows_identified_at_29_rows: 3
bad_direct_parse_modes: two length-truncated long responses at max_tokens=3072; one empty-content stop response
```

Parser update:

```text
scripts/parse_explanation_ensemble_outputs.py now has a conservative fallback
for invalid JSON backslash escapes, while still preserving truly truncated rows
as parse errors for audit.
```

### 2026-06-29 grounded-market filter

Motivation: the broad 100-row pilot includes markets whose price movement may
be driven by attention, thin liquidity, platform dynamics, or private/dispersed
signals rather than public news. Examples include mention markets such as
whether Trump will say a phrase, popularity markets, entertainment awards, and
some crypto/attention markets. These are real markets, but they are less ideal
for testing whether public evidence supports explanation diversity.

Design decision: add a conservative `--market-filter grounded` option to
`scripts/build_explanation_pilot_candidates.py`.

Included market mechanisms:

```text
election_result
official_political_process
economic_release
company_scheduled_disclosure
legal_regulatory
```

Excluded mechanisms/categories:

```text
attention_mentions
popularity_attention
awards_entertainment
sports_or_game
Crypto
Entertainment
Mentions
Social
```

Note: company earnings-call markets may contain the word "say", but are kept
when they match `company_scheduled_disclosure`, because they are tied to a
scheduled official disclosure rather than open-ended public attention.

Grounded eligible pool:

```text
eligible_rows: 236 / 1120
eligible_categories:
  Politics: 120
  Elections: 42
  Companies: 45
  Economics: 27
  Financials: 2
positive_posterior_rows: 72
zero_posterior_abs_delta_ge_0.02_rows: 49
zero_posterior_stable_rows: enough for the 25-row stable bucket
```

Grounded 100-row full-news panel:

```text
command:
python scripts/build_explanation_pilot_candidates.py \
  --market-filter grounded \
  --output-prefix kalshi_100row_grounded_fullnews \
  --top-posterior-k 100 \
  --top-prior-k 100 \
  --hard-negative-k 0 \
  --random-k 100

rows: 100
row_buckets:
  posterior_attributed_move: 50
  unattributed_moved: 25
  stable_no_attribution: 25
categories:
  Politics: 46
  Elections: 24
  Companies: 18
  Economics: 10
  Financials: 2
candidate_news_records: 6464
```

Grounded bounded request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_grounded_fullnews_bounded_ensemble5_20260629_requests.jsonl

requests: 100
regime: mixed_blind
prompt_variant: neutral_forecaster
samples_per_cell: 1
num_explanations_per_request: 5
visible evidence mean: 64.64
visible evidence median: 100
visible evidence max: 100
largest prompt: 52,607 characters
```

This request file is prepared locally but has not been submitted to ORCD yet.
The current broad full-news bounded job `16779182` should be allowed to finish
or be explicitly stopped before launching the grounded follow-up.

### 2026-06-29 broad bounded run completion and sparsity scan

Broad full-news bounded Gemma run:

```text
job_id: 16779182
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:33:20
rows_written: 100
remote_output:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_fullnews_bounded_ensemble5_20260629/gemma4_26b_fullnews_bounded_ensemble5_20260629_outputs.jsonl
```

Local parse:

```text
outputs:
data/derived/explanation_pilot/outputs/gemma4_26b_fullnews_bounded_ensemble5_20260629_outputs.jsonl

parsed_model_responses: 86 / 100
parse_errors: 14
candidate_explanation_rows: 418
candidate_count_per_response:
  5 candidates: 83 responses
  1 candidate: 3 responses
```

Rough prompt-level interpretation among parsed responses:

```text
other_or_mixed: 34
model_too_conservative_candidate: 23
retrieval_missing_or_no_visible_signal: 17
correct_null_update: 8
weak_proxy_or_missing_signal: 4
```

The broad sample therefore supports the concern that many large market moves
are not explainable from the public evidence packets available to the model.
This is especially visible in attention, entertainment, crypto, and other
high-volatility markets. The grounded-market panel is intended as the next
diagnostic to test whether this is mainly a market-selection problem.

SWM/Kalshi sparsity scan:

```text
raw_test_rows: 1120
sample_type_counts:
  normal_point: 767
  breakpoint: 353

positive_posterior_attribution_rate:
  all rows: 0.303
  normal_point: 0.000
  breakpoint: 0.960

median_abs_delta:
  normal_point: 0.0073
  breakpoint: 0.0956

abs_delta <= 0.005:
  normal_point: 0.424
  breakpoint: 0.000

zero_attribution_item_rate:
  all candidate news items: 0.835
  normal_point candidate news items: 1.000
  breakpoint candidate news items: 0.544
```

Interpretation: SWM explicitly represents the sparse regime. Most normal
points are no-news/no-attribution transitions, while breakpoint rows concentrate
large moves and non-null attributed events. This supports separating
`correct_null_update` from `retrieval_missing_or_no_visible_signal` in our
explanation pipeline.

### 2026-06-29 grounded non-null submission

Decision: run the grounded follow-up only on SWM non-null rows. Operationally,
this means filtering the grounded full-news panel to `row_bucket ==
posterior_attributed_move`, which corresponds to rows with positive posterior
attribution.

Builder update:

```text
script: scripts/build_explanation_generation_requests.py
new option: --row-buckets
usage here: --row-buckets posterior_attributed_move --row-limit 0
```

Local request file:

```text
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_requests.jsonl

requests: 50
row_buckets_filter: posterior_attributed_move
regime: mixed_blind
prompt_variant: neutral_forecaster
samples_per_cell: 1
num_explanations_per_request: 5
categories:
  Politics: 26
  Elections: 12
  Companies: 10
  Financials: 2
visible evidence mean: 74.18
visible evidence median: 100
visible evidence max: 100
largest prompt: 52,607 characters
```

Submitted ORCD job:

```text
job_id: 16780895
status_at_submission_check: PENDING (Priority)
partition: mit_preemptable
remote_dir:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629

request_file:
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629/requests.jsonl

model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
extra_body_json: {"stop":["<end_of_turn>"]}
max_model_len: 49152
max_tokens: 6144
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
excluded_nodes: node4309,node4501
```

### 2026-06-29 local work during ORCD reconnect outage

ORCD SSH became unavailable while monitoring job `16780895`. Local work
continued without submitting new jobs.

Script update:

```text
script: scripts/build_explanation_pilot_candidates.py
new option: --row-id-prefix
default: kalshi_test
reason: pilot_row_id was unique within a generated panel but could collide
        across train/test-derived panels because it used only row_idx.
```

Existing submitted test requests were left untouched. Train-derived local
artifacts had not been submitted, so they were regenerated with
`--row-id-prefix kalshi_train`.

Regenerated train panel:

```text
rows:
data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_rows.jsonl

candidates:
data/derived/explanation_pilot/kalshi_grounded_nonnull_train_fullnews_candidates.jsonl

rows: 340
candidate_news_records: 22571
row_bucket: posterior_attributed_move only
row_id_prefix: kalshi_train
```

Prepared request files:

```text
submitted/running test chunk:
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_requests.jsonl
requests: 50
row_id_prefix: kalshi_test

pending test remainder:
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_remaining22_fullnews_bounded_ensemble5_20260629_requests.jsonl
requests: 22
row_id_prefix: kalshi_test

train all-in-one:
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_fullnews_bounded_ensemble5_20260629_requests.jsonl
requests: 340
row_id_prefix: kalshi_train

train batches:
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch001_fullnews_bounded_ensemble5_20260629_requests.jsonl
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch002_fullnews_bounded_ensemble5_20260629_requests.jsonl
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch003_fullnews_bounded_ensemble5_20260629_requests.jsonl
data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_train_batch004_fullnews_bounded_ensemble5_20260629_requests.jsonl
requests: 100, 100, 100, 40
```

Request audit across the submitted 50-row test chunk, pending 22-row test
remainder, and four train batches:

```text
total_requests: 412
unique_pilot_row_ids: 412
cross_file_duplicate_pilot_row_ids: 0
max_prompt_chars: 52726
```

Recommended reconnect order:

1. Check whether ORCD job `16780895` completed, failed, or is still running.
2. If complete, copy back outputs and parse before launching more jobs.
3. Submit the pending 22-row test remainder next.
4. Submit train batches only after the grounded test outputs still show valid
   JSON and non-degenerate explanation diversity.

### 2026-06-29 grounded 50-row completion after reconnect

ORCD job `16780895` completed successfully:

```text
job_id: 16780895
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:16:53
node: node4417
api_successes: 50 / 50
```

Copied local outputs:

```text
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_outputs.jsonl
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_per_request_timing.csv
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_timing_summary.json
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_outputs.jsonl.run.json
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_run_metadata.json
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_fullnews_bounded_ensemble5_20260629_vllm_server_16780895.log
```

Parse summary:

```text
parsed_responses: 46 / 50
parse_errors: 4
candidate_explanation_rows: 210
responses_with_5_candidates: 41
responses_with_1_candidate: 5
```

Score summary:

```text
candidate_direction_match_rate: 0.410
candidate_flat_rate: 0.286
mean_delta_error: 0.2115
mean_baseline_error: 0.2283
mean_candidate_improvement_vs_persistence: 0.0167
recommended_candidate_mean_improvement: 0.0176
mean_best_candidate_improvement_vs_persistence: 0.0500
best_candidate_positive_improvement_rate: 0.717
prompts_with_more_than_one_update_direction: 34 / 46
```

Interpretation: the run is usable for the explanation-variant study. Average
candidate performance is only modestly better than persistence, but the
candidate set often contains a substantially better explanation. This supports
the contrastive framing: learn what distinguishes useful explanations from
unhelpful ones, rather than relying on a single generated rationale.

Known issues:

- 3 responses had no JSON object.
- 1 response returned an empty `candidate_explanations` array.
- 5 parsed candidates violated the selected-evidence bound by selecting more
  than 5 IDs. These should be filtered or trimmed before supervised modeling.

Report:

```text
reports/explanation_pilot/gemma4_26b_grounded_nonnull_50_summary_20260629.md
```

### 2026-06-29 grounded 22-row remainder submission

Decision: submit the 22-row grounded non-null test remainder, but do not submit
train batches until the full 72-row test set is copied back and parsed.

Remote output directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_grounded_nonnull_remaining22_fullnews_bounded_ensemble5_20260629
```

Submitted ORCD job:

```text
job_id: 16781601
status_at_submission_check: PENDING (Priority)
partition: mit_preemptable
requests: 22
model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
max_model_len: 49152
max_tokens: 6144
temperature: 0.7
concurrency: 1
time_limit: 03:00:00
```

Completion:

```text
job_id: 16781601
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:10:38
node: node4417
api_successes: 22 / 22
parsed_responses: 22 / 22
parse_errors: 0
candidate_explanation_rows: 110
```

Combined grounded non-null test summary:

```text
requests: 72
parsed_responses: 68
parse_errors: 4
candidate_explanation_rows: 320
responses_with_5_candidates: 63
candidate_flat_rate: 0.284
candidate_direction_match_rate: 0.388
mean_candidate_improvement_vs_persistence: 0.0095
recommended_candidate_mean_improvement: 0.0064
mean_best_candidate_improvement_vs_persistence: 0.0396
best_candidate_positive_improvement_rate: 0.691
multi_direction_prompt_rate: 0.721
median_within_prompt_posterior_std: 0.0167
selected_evidence_bound_violations: 8 candidate explanations
```

Comparison to the broad 100-row full-news run:

```text
candidate_flat_rate: 0.311 -> 0.284
multi_direction_prompt_rate: 0.674 -> 0.721
median_within_prompt_posterior_std: 0.0102 -> 0.0167
mean_candidate_improvement_vs_persistence: 0.0034 -> 0.0095
best_candidate_positive_improvement_rate: 0.535 -> 0.691
candidate_direction_match_rate: 0.431 -> 0.388
```

Interpretation: grounded non-null markets produce less flat and more diverse
explanation ensembles, and they more often contain at least one explanation
that beats persistence. However, raw direction matching is worse, so the value
of the current setup is contrastive/ranking-oriented rather than direct
forecasting.

Report:

```text
reports/explanation_pilot/gemma4_26b_grounded_nonnull_72_summary_20260629.md
```

### 2026-06-29 validation and ranking dataset

Parser update:

```text
script: scripts/parse_explanation_ensemble_outputs.py
new fields:
  schema_selected_ids_bound_ok
  schema_weights_bound_ok
  schema_selected_ids_visible_ok
  schema_weights_subset_ok
  schema_posterior_valid
  schema_delta_consistent
  schema_direction_consistent
  schema_candidate_count_ok
  schema_recommended_id_valid
  schema_valid
```

Ranking dataset builder:

```text
script: scripts/build_explanation_ranking_dataset.py
input:
data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_72_fullnews_bounded_ensemble5_20260629_scores.csv

valid-only output:
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv
```

Validation summary:

```text
candidate_score_rows: 320
schema_valid_candidate_rows: 275
schema_invalid_candidate_rows: 45

schema failure counts:
  selected_ids_bound: 8
  evidence_weights_bound: 5
  selected_ids_visible: 1
  evidence_weights_subset: 7
  direction_consistency: 27
  candidate_count: 5
```

Valid-only ranking summary:

```text
ranking_rows: 275
prompt_count: 62
best_rows: 62
recommended_rows: 53
recommended_is_best_rate: 0.396
positive_improvement_rate: 0.353
best_positive_improvement_rate: 0.645
```

Interpretation: after strict schema validation, Gemma's own recommended
candidate is still rank-1 in only about 40% of prompts. This supports training
or evaluating a separate explanation ranker.

### 2026-06-29 train batch 001 submission

Decision: submit exactly one train batch before scaling to all remaining train
batches.

Remote output directory:

```text
/home/robinna/Behavioral_Portability/repo/data/prediction_market/explanation_pilot/gemma4_26b_grounded_nonnull_train_batch001_fullnews_bounded_ensemble5_20260629
```

Submitted ORCD job:

```text
job_id: 16782046
status_at_submission_check: RUNNING
node: node4417
partition: mit_preemptable
requests: 100
model: google/gemma-4-26B-A4B
endpoint: completions
completion_prompt_style: gemma_turns
max_model_len: 49152
max_tokens: 6144
temperature: 0.7
concurrency: 1
time_limit: 06:00:00
```

Completion and parse:

```text
job_id: 16782046
slurm_state: COMPLETED
exit_code: 0:0
elapsed: 00:33:27
node: node4417
api_successes: 100 / 100
parsed_responses: 95 / 100
parse_errors: 5
candidate_explanation_rows: 450
schema_valid_candidate_rows: 386
valid_prompt_count: 85
recommended_is_best_rate: 0.444
best_positive_improvement_rate: 0.671
```

Ranker check:

```text
train_batch001_valid_rows: 386
train_batch001_prompt_count: 85
deployable_ranker_top1_rate_group_cv: 0.435
gemma_recommended_top1_rate: 0.444
confidence_top1_rate: 0.529
random_top1_rate: 0.238
```

Combined test72 + train batch001 valid-only ranking pool:

```text
ranking_rows: 661
prompt_count: 147
recommended_is_best_rate: 0.425
best_positive_improvement_rate: 0.660
deployable_ranker_top1_rate_group_cv: 0.469
gemma_recommended_top1_rate: 0.425
confidence_top1_rate: 0.490
random_top1_rate: 0.242
```

Interpretation: train batch 001 is healthy enough to scale. The simple ranker
is not yet clearly better than the confidence heuristic, but it beats Gemma's
recommended candidate in the combined prompt-level cross-validation.

### 2026-06-29 train batches 002-004 submission

Decision: submit the remaining train batches after batch 001 completed with
acceptable parse/schema health.

Submitted jobs:

```text
batch002_job_id: 16783833
batch002_requests: 100
batch002_status_at_submission_check: RUNNING on node4417

batch003_job_id: 16783834
batch003_requests: 100
batch003_status_at_submission_check: RUNNING on node2414

batch004_job_id: 16783883
batch004_requests: 40
batch004_status_at_submission_check: PENDING (Priority)
```

Completion and parse:

```text
batch002_job_id: 16783833
batch002_state: COMPLETED
batch002_exit_code: 0:0
batch002_elapsed: 00:33:23
batch002_api_successes: 100 / 100
batch002_parsed_responses: 98 / 100
batch002_parse_errors: 2
batch002_candidate_rows: 467
batch002_schema_valid_candidate_rows: 408
batch002_valid_prompt_count: 90

batch003_job_id: 16783834
batch003_state: COMPLETED
batch003_exit_code: 0:0
batch003_elapsed: 00:35:43
batch003_api_successes: 100 / 100
batch003_parsed_responses: 97 / 100
batch003_parse_errors: 3
batch003_candidate_rows: 472
batch003_schema_valid_candidate_rows: 409
batch003_valid_prompt_count: 90

batch004_job_id: 16783883
batch004_state: COMPLETED
batch004_exit_code: 0:0
batch004_elapsed: 00:16:30
batch004_api_successes: 40 / 40
batch004_parsed_responses: 36 / 40
batch004_parse_errors: 4
batch004_candidate_rows: 176
batch004_schema_valid_candidate_rows: 158
batch004_valid_prompt_count: 35
```

All train batches combined:

```text
train_score_rows: 1565
train_schema_valid_candidate_rows: 1361
train_valid_prompt_count: 300
train_recommended_is_best_rate: 0.493
train_best_positive_improvement_rate: 0.560
```

Held-out ranker evaluation on the 72-row grounded test set:

```text
absolute deployable logistic top1: 0.387
prompt-relative deployable logistic top1: 0.548
prompt-relative deployable hist_gradient_boosting top1: 0.532
prompt-relative deployable extra_trees top1: 0.516
gemma_recommended_top1: 0.396
confidence_top1: 0.435
random_top1: 0.248
```

Interpretation: absolute structured features are not enough. Prompt-relative
features produce the first clear held-out supervisor signal, suggesting that
the useful problem formulation is selecting the best explanation from the local
candidate set rather than classifying explanations globally.

### 2026-06-29 selector baseline audit

Objective: audit whether the supervisor result survives comparison against
simple deployable selectors and detect any leakage from the ranking-file order.

Script:

```text
scripts/audit_explanation_selectors.py
```

Inputs:

```text
train:
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_train_all_batches_valid_ranking_candidates.csv

held-out test:
data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv
```

Outputs:

```text
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_selector_performance.csv
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_stratified_performance.csv
reports/explanation_pilot/gemma4_26b_selector_audit_20260629_tie_diagnostics.csv
reports/explanation_pilot/gemma4_26b_selector_audit_summary_20260629.md
```

Important correction:

```text
previous naive max-selected-evidence top1: 0.710
safe candidate-index tie-break top1: 0.435
```

The naive result was inflated because the ranking CSV is sorted by
market-error rank. When many candidates tie on selected evidence count,
row-order tie-breaking selects the already-ranked best candidate. On held-out
test prompts, 64.5% of prompts tie for max selected evidence count, with mean
tie size 2.82.

Held-out selector audit:

```text
random_expected_top1: 0.248
gemma_recommended_top1: 0.396
max_confidence_top1: 0.371
max_selected_evidence_count_top1_safe: 0.435
max_posterior_top1: 0.629
min_posterior_top1: 0.548
max_abs_update_top1: 0.613
core_relative_logit_top1: 0.532
oracle_best_candidate_top1: 1.000

random_expected_mean_error: 0.172
max_abs_update_mean_error: 0.166
core_relative_logit_mean_error: 0.163
oracle_best_candidate_mean_error: 0.140
```

Interpretation:

- Evidence count is not the main baseline once ties are handled safely.
- The strongest simple deployable top-1 baseline is choosing the candidate
  with the largest absolute update.
- The core relative logit has lower mean market-price error than the simple
  non-oracle selectors, even though its top-1 rate is lower than the extreme
  posterior/update rules.
- Candidate pools are often diverse enough to contain useful alternatives:
  held-out prompts have multi-direction candidates in 69.4% of cases and at
  least one positive-improvement candidate in 64.5% of cases.
- Gemma's recommendation is asymmetric: it works better for upward market
  moves than downward moves.

Schema note: one training candidate had `confidence = 95.0`; the audit treats
out-of-range confidence as missing. The parser should add explicit
confidence-range validation.

### 2026-06-29 generation gap audit

Objective: measure the oracle upper bound of the generated candidate pool
before selector quality enters. This asks how close the best available Gemma
candidate gets to the next market price.

Script:

```text
scripts/audit_explanation_generation_gap.py
```

Outputs:

```text
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_prompt_level.csv
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_aggregate.csv
reports/explanation_pilot/gemma4_26b_generation_gap_audit_20260629_examples.csv
reports/explanation_pilot/gemma4_26b_generation_gap_audit_summary_20260629.md
```

Held-out test72 result:

```text
prompt_count: 62
mean_persistence_error: 0.181
mean_oracle_best_candidate_error: 0.140
mean_oracle_improvement_over_persistence: 0.041
helpful_candidate_available_rate: 0.645
best_candidate_within_5pp_rate: 0.210
best_candidate_over_20pp_error_rate: 0.177
target_bracketed_by_candidate_range_rate: 0.000
```

Gap decomposition:

```text
right_direction_under_update: 38 / 62 prompts
no_right_direction_candidate: 22 / 62 prompts
near_hit: 2 / 62 prompts
```

Magnitude diagnostic:

```text
median_best_candidate_update_fraction_of_market_update_when_direction_matches: 0.250
mean_candidate_posterior_range_fraction_of_market_update: 0.457
```

Interpretation: the generated pool is useful but too narrow in posterior
space. The main generation failure is underreaction: even when Gemma generates
a candidate in the correct market direction, the candidate usually covers only
about one quarter of the actual market move. The next generation experiment
should deliberately ask for calibration-diverse update models and evaluate
whether the oracle-best generation bound improves before adding a more complex
selector.
