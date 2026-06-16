# Attention Proxies in SWM Kalshi News Attributions

Created: 2026-06-16

## Objective

Use the released Social World Model (SWM) Kalshi data to ask a narrower version of
the Robin-tab question: do source-level attention proxies identify the news that is
helpful for belief updates?

The released data contain candidate news and attribution scores, not community
rationales or comment engagement. This is therefore a source/news-level analysis,
not the final rationale-level study.

## Main Answer

Popularity and traffic are the clearest external correlates of posterior
helpfulness. Credibility is not positively associated with helpfulness in the raw
domain panel.

- Tranco attention vs. posterior helpfulness: Spearman
  `0.353`.
- MBFC traffic vs. posterior helpfulness: Spearman
  `0.356`.
- MBFC credibility vs. posterior helpfulness: Spearman
  `-0.208`.

These are descriptive source-domain correlations, not causal estimates.

The SWM prior attributor helps interpret why source-level regularities appear,
but it is not a faithful item-level explanation of hindsight attribution.

On held-out Kalshi records with posterior-positive news:

- Item-level `q` versus `s` Spearman is only `0.067`.
- The prior puts `0.505` of its mass on
  posterior-positive news.
- The prior top item is posterior-positive in `61.9%`
  of positive records, but exactly matches the posterior top item in only
  `16.2%`.

At the source-domain level, prior/posterior relation is much stronger: mean prior attention and
mean posterior helpfulness correlate at Spearman
`0.532` among domains with at least 20
candidate articles.

## Scope

No new LLM training or inference was run. We did not use unreleased checkpoints,
unreleased random-ablation predictions, or platform comments/rationales.

## Main Report Artifacts

- `attention_is_not_information_no_training.pdf`
- `attention_is_not_information_no_training.tex`
- `tables/table1_prior_signal.tex`
- `tables/table2_source_correlations.tex`
- `figures/fig1_domain_prior_vs_posterior.png`
- `figures/fig2_source_attribute_correlations.png`

## Next Step

The direct test should use a Manifold-first or Metaculus-first dataset with
comments/rationales, likes/replies, author information, price movement, and final
resolution. That would test attention versus information at the actual rationale
level rather than at the released SWM news-source level.
