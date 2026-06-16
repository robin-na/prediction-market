# No-Training Prediction-Market Rationale Analysis

This folder contains the rendered report and analysis artifacts for the
no-training/no-new-LLM-inference version of the "Attention Is Not Information"
project.

## Deliverables

- `attention_is_not_information_no_training.pdf`: rendered report with figures.
- `attention_is_not_information_no_training.tex`: LaTeX source for the report,
  organized in the same compact memo style as the Behavioral Portability reports.
- `attention_is_not_information_no_training__tectonic.log`: TeX compile log.
- `attention_is_not_information_no_training__report.md`: concise Markdown report note.
- `attention_is_not_information_no_training__provenance.json`: provenance and input/output manifest.
- `numbers.tex`: numeric macros used by the TeX report.
- `analysis_summary.json`: machine-readable summary of the main counts and metrics.
- `figures/fig1_domain_prior_vs_posterior.png`: source-level prior/helpfulness scatter.
- `figures/fig2_source_attribute_correlations.png`: source-attribute correlation chart.
- `tables/table1_prior_signal.tex`: compact prior-versus-posterior signal table.
- `tables/table2_source_correlations.tex`: compact source-attribute correlation table.

## Scope

The goal was to run all analyses available from released data and external
source tables without:

- training a new model,
- running new LLM inference,
- using unreleased checkpoints,
- using unreleased per-record random-ablation predictions.

The resulting analysis is a source-level analogue to the rationale-level
question in the Robin tab of the brainstorming document. The released SWM Kalshi
data contain candidate news and attribution scores, not community rationales or
comment engagement.

## Data Used

- SWM-Bench Kalshi raw split files from `ulab-ai/swm-bench`.
- Released prior-attributed Kalshi train/test splits.
- Released posterior-attributed Kalshi train/test splits.
- Tranco top-domain ranks as an attention/popularity proxy.
- MBFC-derived `mbfcext` source fields as credibility/reporting/traffic proxies.
- Iffy index as an explicit low-credibility/unreliable-source flag.

## Main Estimands

For a source domain \(d\):

\[
H_d=\frac{1}{N_d}\sum_{(r,i):d_{ri}=d}s_{ri}
\]

is posterior helpfulness,

\[
A_d=\frac{1}{N_d}\sum_{(r,i):d_{ri}=d}q_{ri}
\]

is learned prior attention.

Here \(s_{ri}\) is the released posterior/hindsight attribution score and
\(q_{ri}\) is the released prior-attributor score.

## Reproduction Commands

From the repository root:

```bash
/opt/anaconda3/bin/python scripts/build_source_attribute_panel.py
MPLCONFIGDIR=tmp/mplconfig /opt/anaconda3/bin/python scripts/generate_no_training_report.py
```

The second command writes this folder.

## Visual QA

The PDF is compiled from `attention_is_not_information_no_training.tex` with the
bundled Codex Tectonic binary. The generator sets a repo-local Tectonic cache
under `tmp/tectonic-cache` so the build does not depend on the user's home cache.
The compile log is clean as of the current report build.

Because Poppler is not installed locally, visual QA used AppKit's PDF image
representation through the conda Python environment. Pages 1, 2, 3, 4, and 6
were rendered to PNG under `tmp/pdfs/` and checked for equation rendering,
figure/table flow, readable legends, and appendix URL/path breaks.

## Interpretation Boundary

These results should not be read as causal proof that a source caused a market
move. They compare released hindsight attributions, learned prior weights, and
external source attributes. A direct rationale-level project needs a dataset
with comments/rationales, attention metrics, price or probability movement, and
resolved outcomes, such as a Manifold-first or Metaculus-first dataset.
