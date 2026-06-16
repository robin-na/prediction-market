# No-Training Analysis Log

Date: 2026-06-16

Workspace root: repository root (`.`)

## Origin of the Question

The Robin tab of the shared brainstorming document proposes a project around
forecast rationales in prediction markets. The motivating distinction is between:

- attention: what receives engagement or visibility,
- influence: what moves aggregate beliefs or market prices,
- marginal predictive usefulness: what adds non-redundant information and moves
  forecasts closer to the truth.

The key empirical question is whether high-attention rationales are also
high-information rationales.

## Important Dataset Constraint

The SWM/Kalshi data we have are not community rationales. They contain:

- market/question metadata,
- historical prices,
- candidate news items,
- posterior attribution scores over candidate news,
- prior-attributor scores in the raw Kalshi split.

Therefore, the analyses in this repository answer a source/news analogue of the
Robin-tab question:

> Are higher-attention or higher-credibility news sources the ones that receive
> posterior attribution and learned prior weight?

They do not directly answer:

> Which user-written comments or rationales received attention and improved
> forecast accuracy?

That direct rationale-level question requires a platform dataset with comments,
likes/replies, author information, market-price or forecast changes, and final
resolutions.

## Decisions Made

1. Use only released data and static external source tables.
2. Do not train a new LLM or attributor.
3. Do not run LLM inference to classify rationales/news.
4. Treat SWM posterior attribution as a hindsight information proxy, not causal
   proof.
5. Treat SWM prior attribution as learned deployable attention, but only as far
   as the released prior-attributed files expose it.
6. Join external attributes by URL domain instead of display source name.
7. Interpret Iffy absence as "not flagged by Iffy", not "credible".
8. Use Tranco and candidate frequency as attention/popularity proxies.
9. Document GDELT as feasible but not included in the final run because broad
   domain-volume queries were slow in this session.
10. Render the final PDF from the generated TeX source using the bundled Codex
    Tectonic binary, with a repo-local cache.

## Data Files Used

Released SWM-Bench files:

- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_prior_attributed_train_2025-11-01.jsonl`
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_prior_attributed_test_2025-11-01.jsonl`
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl`
- `data/swm-bench/raw/kalshi/splitted_v2_0102/kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl`
- `data/swm-bench/Qwen3.5-397B-attributed-data/test_kalshi.jsonl`
- `data/swm-bench/Qwen3.5-397B-attributed-data/train.jsonl`

External source attributes:

- `data/external/tranco_top_1m.csv.zip`
- `data/external/mbfcext_combined.json`
- `data/external/iffy_index.json`

Code/release checks:

- `data/external/social_world_model_tree.json`

## Scripts

- `scripts/fetch_kalshi.py`: small public Kalshi API probe.
- `scripts/random_news_hurt_proxy.py`: random-news selection proxy using released posterior attribution mass.
- `scripts/score_random_ablation_predictions.py`: scorer for unreleased/random-ablation prediction JSONL if those files become available later.
- `scripts/build_source_attribute_panel.py`: builds article, source, domain, and category-domain panels and joins external source attributes.
- `scripts/generate_no_training_report.py`: generates record-level summaries,
  tables, figures, `.tex`, and the Tectonic-rendered PDF report.

## Commands Run for the Final Report

```bash
/opt/anaconda3/bin/python scripts/build_source_attribute_panel.py
MPLCONFIGDIR=tmp/mplconfig /opt/anaconda3/bin/python scripts/generate_no_training_report.py
```

## Main Counts

From the refreshed source panel:

- 3,899 matched Kalshi train/test records.
- 232,647 candidate news articles.
- 1,513 records with at least one positive posterior attribution.
- 388 joined source domains.
- 274 MBFC-matched domains.
- 379 Tranco-matched domains.
- 10 Iffy-flagged domains.

## Main Findings

- Posterior attribution is sparse: 38.8% of matched Kalshi records have at least
  one posterior-positive candidate.
- Among positive-posterior records, the learned prior places 0.585 of its mass
  on posterior-positive candidates on average.
- The learned prior top candidate is posterior-positive in 70.2% of positive
  records, but exactly matches the posterior top candidate in only 20.8%.
- On held-out positive records, item-level prior attention and posterior
  helpfulness have Spearman correlation 0.067; exact top-item recovery is 16.2%.
- Across domains with at least 20 candidate articles, mean prior attention and
  mean posterior helpfulness have Spearman correlation 0.532.
- Tranco attention has Spearman correlation 0.353 with posterior helpfulness and
  0.360 with learned prior attention at the domain level.
- MBFC traffic has a clearer relationship with helpfulness/attention than MBFC
  credibility or reporting labels.
- Random top-1 news selection is a poor proxy for optimized selection: in the
  Qwen3.5 Kalshi test proxy, random top-1 selection has a 72.9% zero-miss rate
  among high-attribution records.

## Compact Report Figures and Tables

- Figure 1: domain-level prior attention versus posterior helpfulness.
- Figure 2: source-attribute correlations with posterior helpfulness and prior
  attention.
- Table 1: compact prior-versus-posterior signal checks.
- Table 2: compact source-attribute correlations.

## Report Style Revision

After comparing against the latest report in `../Behavioral_Portability`, the
report bundle was revised to match that clearer pattern:

- compact memo-style sections instead of one slide-like page per figure,
- generated `numbers.tex` numeric macros,
- generated TeX table inputs in `reports/no_training/tables/`,
- a companion Markdown report note,
- provenance JSON,
- figures and tables floated into the surrounding argument,
- an appendix with reproducibility and limitations.

After later review, the main report was compressed further around the clearest
objectives: defining the SWM prior/posterior attribution scores for readers who
have not read the paper, showing that the prior attributor learns coarse but not
faithful item-level signal, and comparing popularity/credibility source
attributes. The old six-figure diagnostic version was replaced by a two-figure,
two-table memo.

The main PDF is compiled directly from the generated TeX source with the bundled
Codex Tectonic binary. The compile log is saved in
`reports/no_training/attention_is_not_information_no_training__tectonic.log`,
and representative pages were rendered to PNG for visual QA.

## Things We Could Not Do Without New Data or Inference

- Direct comment/rationale attention analysis.
- Author reputation or social engagement modeling.
- LLM extraction of evidence atoms from rationales.
- LLM-based redundancy or rhetorical-feature annotation.
- Model-checkpoint evaluation of actual forecast errors.
- Random-news ablation scoring against optimized SWM predictions, because the
  released repository/data do not include those prediction outputs.

## Recommended Next Step

Build a Manifold-first rationale dataset:

1. Pull resolved binary markets.
2. Pull comments/rationales and timestamps.
3. Pull likes/replies/visibility proxies and author-level information when
   available.
4. Pull bets or probability histories around each comment.
5. Compute local belief movement and accuracy improvement against final
   resolution.
6. Only then add LLM evidence-atom extraction and redundancy scoring.

This would directly test the Robin-tab hypothesis rather than the source-level
news analogue in the current report.
