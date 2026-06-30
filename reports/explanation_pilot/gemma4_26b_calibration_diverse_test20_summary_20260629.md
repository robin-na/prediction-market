# Gemma 4 26B Calibration-Diverse Test20 Summary

Date: 2026-06-29

## Purpose

This run tested whether the generation gap in the explanation pilot is caused by
generic explanation generation being too conservative. The new prompt forced
five fixed update profiles:

- E1: evidence-strict/no-update
- E2: conservative Bayesian
- E3: moderate evidence-weighted
- E4: aggressive market-reaction
- E5: contrarian/noise-or-overreaction

The test used 20 high-movement grounded non-null heldout rows and the same
market-price evaluation used in the previous pilot.

## Run Artifacts

- Requests:
  `data/derived/explanation_pilot/requests/gemma4_26b_grounded_nonnull_caldiv_test20_20260629_requests.jsonl`
- ORCD job:
  `16790730`
- Raw outputs:
  `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_caldiv_test20_completions_20260629_outputs.jsonl`
- Scores:
  `data/derived/explanation_pilot/outputs/gemma4_26b_grounded_nonnull_caldiv_test20_completions_20260629_scores.csv`
- Ranking dataset:
  `data/derived/explanation_pilot/ranking/gemma4_26b_grounded_nonnull_caldiv_test20_completions_valid_ranking_candidates.csv`
- Generation-gap audit:
  `reports/explanation_pilot/gemma4_26b_generation_gap_caldiv_test20_completions_parser_fixed_20260629_aggregate.csv`

## Infrastructure Notes

The first chat-endpoint submission failed because Gemma's tokenizer did not
provide a vLLM chat template. A first retry also failed because the runner
expects `--endpoint completions`, not `completion`. The corrected completions
job finished successfully with 20/20 raw outputs in 11m57s.

Completion-mode outputs sometimes contained a valid JSON object followed by an
echo of the prompt. The parser was updated to recover the first balanced JSON
object instead of slicing from the first `{` to the last `}`. This increased
usable calibration-diverse rows from 13 to 17; after schema filtering, 16
prompts remained. The same parser fix was applied to the prior freeform outputs
before comparison.

## Main Result

The calibration-diverse prompt did not reduce the generation gap on this stress
test. It produced more explicit profile labels, but often not meaningfully more
posterior diversity.

Prompt-level metrics:

| Dataset | Prompts | Mean persistence error | Mean oracle-best error | Mean oracle improvement | Helpful-candidate rate | Any direction-match rate | Within 5pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Freeform heldout 72, parser-fixed | 62 | 0.1807 | 0.1398 | 0.0410 | 0.6452 | 0.6452 | 0.2097 |
| Calibration-diverse test20 valid subset | 16 | 0.3393 | 0.3185 | 0.0208 | 0.1875 | 0.1875 | 0.0625 |

The calibration-diverse sample was deliberately harder than the full heldout
set, so the cleaner comparison is the overlapping valid rows:

| Dataset | Common prompts | Mean persistence error | Mean oracle-best error | Mean oracle improvement | Helpful-candidate rate | Any direction-match rate | Mean posterior range | All-flat rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Freeform common rows | 14 | 0.3526 | 0.2950 | 0.0576 | 0.9286 | 0.9286 | 0.1017 | 0.0000 |
| Calibration-diverse common rows | 14 | 0.3526 | 0.3289 | 0.0237 | 0.2143 | 0.2143 | 0.0311 | 0.7143 |

## Interpretation

The failure mode is not just lack of named update styles. The model often
collapses all five candidates to the prior after deciding that the visible news
does not directly resolve the market. On the common rows, 10/14 calibration-
diverse prompts were all-flat, while 0/14 freeform prompts were all-flat.

This suggests that a calibration-profile prompt can make explanations look more
structured without actually producing useful posterior support coverage. The
bottleneck is likely one of:

- evidence relevance judgments are too strict or too brittle;
- the prompt gives the model permission to collapse all profiles when evidence
  is judged irrelevant;
- the model does not separate "evidence is weak" from "generate plausible
  market-reaction hypotheses anyway";
- market moves may be driven by information not visible in the retrieved packet,
  but the explanation generator needs to represent that as a hypothesis rather
  than only as no-update.

## Concrete Examples

- `kalshi_test_0354`: Gary Peters CR vote. Market moved from 0.7543 to 0.0432.
  Calibration-diverse generated five identical flat posteriors at 0.7543, all
  labeled `evidence_irrelevance`.
- `kalshi_test_0305`: Walmart earnings-call topic. Market moved down from
  0.5579 to 0.2352. Calibration-diverse generated a narrow upward range
  0.5600-0.5800, so diversity existed but in the wrong direction.
- `kalshi_test_0874`: EU sanctions Israel. Market moved down from 0.4012 to
  0.1110. Calibration-diverse generated a broad downward range 0.0000-0.3000
  and achieved a near hit. This is the desired behavior.
- `kalshi_test_1106`: Pelosi Epstein files vote. Market moved up from 0.7263 to
  0.9489. Calibration-diverse generated only a small upward range
  0.7263-0.7512, correctly signed but still under-updated.

## Next Experimental Implication

The next prompt should not merely assign calibration profiles. It should force
separate hypotheses about why the market might move:

1. visible-evidence update;
2. no-informative-evidence/no-update;
3. market-microstructure or attention shock;
4. missing-public-evidence hypothesis;
5. overreaction or reversal hypothesis.

That would align better with the research question: explanations are not just
different phrasings of evidence, but different belief-update models that can
include evidence selection, source weighting, missing-information assumptions,
and calibration policies.
