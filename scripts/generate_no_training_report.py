#!/usr/bin/env python3
"""Generate no-training analyses, figures, TeX source, and a rendered PDF report."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_source_attribute_panel import (
    category_of,
    pair_records,
    posterior_mass,
    score_map,
)


RAW_DIR = Path("data/swm-bench/raw/kalshi/splitted_v2_0102")
SOURCE_PANEL_DIR = Path("data/source_attribute_panel")
RANDOM_PROXY_DIR = Path("data/random_news_hurt_proxy")
OUT_DIR = Path("reports/no_training")
FIG_DIR = OUT_DIR / "figures"
TABLE_DIR = OUT_DIR / "tables"
SUMMARY_PATH = OUT_DIR / "analysis_summary.json"
TEX_PATH = OUT_DIR / "attention_is_not_information_no_training.tex"
PDF_PATH = OUT_DIR / "attention_is_not_information_no_training.pdf"
TEX_COMPILE_LOG_PATH = OUT_DIR / "attention_is_not_information_no_training__tectonic.log"
MD_PATH = OUT_DIR / "attention_is_not_information_no_training__report.md"
PROVENANCE_PATH = OUT_DIR / "attention_is_not_information_no_training__provenance.json"
NUMBERS_TEX_PATH = OUT_DIR / "numbers.tex"

EPS = 1e-6
RHO0 = 1.0
REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_path(path: Path | str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.name


def split_specs() -> list[tuple[str, Path, Path]]:
    return [
        (
            "train",
            RAW_DIR / "kalshi_prior_attributed_train_2025-11-01.jsonl",
            RAW_DIR / "kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl",
        ),
        (
            "test",
            RAW_DIR / "kalshi_prior_attributed_test_2025-11-01.jsonl",
            RAW_DIR / "kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl",
        ),
    ]


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def load_record_level() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, prior_path, posterior_path in split_specs():
        for row_idx, (prior, posterior) in enumerate(pair_records(prior_path, posterior_path, split)):
            news = posterior.get("news") or []
            prior_scores = score_map(prior)
            post_scores = score_map(posterior)
            positive = {idx for idx, score in post_scores.items() if score > 0}
            has_positive = bool(positive)
            prior_sum = sum(prior_scores.values())
            prior_on_positive = sum(prior_scores.get(idx, 0.0) for idx in positive)
            wasted_prior = sum(
                prior_scores.get(idx, 0.0)
                for idx in range(len(news))
                if idx not in positive
            )
            post_top_idx = max(post_scores, key=lambda idx: post_scores[idx]) if post_scores else None
            prior_top_idx = max(prior_scores, key=lambda idx: prior_scores[idx]) if prior_scores else None
            post_top_score = post_scores.get(post_top_idx, 0.0) if post_top_idx is not None else 0.0
            prior_top_score = prior_scores.get(prior_top_idx, 0.0) if prior_top_idx is not None else 0.0
            rows.append(
                {
                    "split": split,
                    "record_idx": row_idx,
                    "market_id": posterior.get("market_id", ""),
                    "event_id": posterior.get("event_id", ""),
                    "category": category_of(posterior),
                    "news_count": len(news),
                    "has_positive_posterior": has_positive,
                    "positive_news_count": len(positive),
                    "posterior_mass_total": sum(posterior_mass(post_scores, len(news), EPS, RHO0).values()),
                    "posterior_top_score": post_top_score,
                    "prior_sum": prior_sum,
                    "prior_on_positive": prior_on_positive,
                    "prior_wasted": wasted_prior,
                    "prior_alignment_rate": prior_on_positive / prior_sum if prior_sum > 0 else math.nan,
                    "prior_waste_rate": wasted_prior / prior_sum if prior_sum > 0 else math.nan,
                    "prior_top_score": prior_top_score,
                    "prior_top_positive": int(prior_top_idx in positive) if prior_top_idx is not None else 0,
                    "prior_top_matches_post_top": int(prior_top_idx == post_top_idx)
                    if prior_top_idx is not None and post_top_idx is not None
                    else 0,
                    "z_score": safe_float(posterior.get("z_score")),
                }
            )
    return pd.DataFrame(rows)


def load_item_scores() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, prior_path, posterior_path in split_specs():
        for record_idx, (prior, posterior) in enumerate(pair_records(prior_path, posterior_path, split)):
            news = posterior.get("news") or []
            prior_scores = score_map(prior)
            post_scores = score_map(posterior)
            for news_idx in range(len(news)):
                rows.append(
                    {
                        "split": split,
                        "record_idx": record_idx,
                        "news_idx": news_idx,
                        "prior_score": prior_scores.get(news_idx, 0.0),
                        "posterior_score": post_scores.get(news_idx, 0.0),
                    }
                )
    return pd.DataFrame(rows)


def prepare_outputs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def figure_domain_prior_vs_posterior() -> Path:
    domain = pd.read_csv(SOURCE_PANEL_DIR / "domain_panel.csv")
    domain = domain[domain["candidate_articles"] >= 20].copy()
    spearman = domain["prior_weight_mean"].corr(domain["posterior_score_mean"], method="spearman")
    pearson = domain["prior_weight_mean"].corr(domain["posterior_score_mean"], method="pearson")

    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    ax.scatter(
        domain["prior_weight_mean"],
        domain["posterior_score_mean"],
        s=28,
        color="#4c78a8",
        alpha=0.68,
        edgecolor="white",
        linewidth=0.35,
    )
    x = domain["prior_weight_mean"].to_numpy()
    y = domain["posterior_score_mean"].to_numpy()
    if len(domain) > 1:
        slope, intercept = np.polyfit(x, y, deg=1)
        xs = np.linspace(x.min(), x.max(), 100)
        ax.plot(xs, intercept + slope * xs, color="#e45756", linewidth=2, label="Linear trend")
    ax.text(
        0.03,
        0.96,
        f"Spearman rho = {spearman:.3f}\nPearson r = {pearson:.3f}\nDomains with >=20 articles",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    ax.set_xlabel("Mean prior-attributor weight by domain")
    ax.set_ylabel("Mean posterior helpfulness by domain")
    ax.set_title("Prior attention tracks helpfulness mainly after aggregating to sources")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    path = FIG_DIR / "fig1_domain_prior_vs_posterior.png"
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return path


def figure_source_attribute_correlations() -> Path:
    corr = pd.read_csv(SOURCE_PANEL_DIR / "domain_correlations.csv")
    labels = {
        "tranco_attention": "Tranco popularity",
        "mbfc_traffic_num": "MBFC traffic",
        "mbfc_credibility_num": "MBFC credibility",
        "mbfc_reporting_num": "MBFC factual reporting",
        "iffy_flag_num": "Iffy flagged",
    }
    predictors = list(labels)
    outcomes = {
        "posterior_score_mean": "Posterior helpfulness",
        "prior_weight_mean": "Prior attention",
    }
    rows: list[dict[str, Any]] = []
    for predictor in predictors:
        for outcome, outcome_label in outcomes.items():
            hit = corr[(corr["predictor"] == predictor) & (corr["outcome"] == outcome)]
            if not hit.empty:
                rows.append(
                    {
                        "predictor": labels[predictor],
                        "outcome": outcome_label,
                        "spearman": float(hit.iloc[0]["spearman"]),
                    }
                )
    plot_df = pd.DataFrame(rows)
    plot_df.to_csv(TABLE_DIR / "compact_source_attribute_correlations.csv", index=False)

    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    y = np.arange(len(predictors))
    width = 0.34
    for offset, (outcome, color) in zip(
        [-width / 2, width / 2],
        [("Posterior helpfulness", "#4c78a8"), ("Prior attention", "#f58518")],
        strict=True,
    ):
        values = [
            plot_df[(plot_df["predictor"] == labels[p]) & (plot_df["outcome"] == outcome)]["spearman"].iloc[0]
            for p in predictors
        ]
        ax.barh(y + offset, values, height=width, label=outcome, color=color)
        for yi, value in zip(y + offset, values, strict=True):
            x_text = value + 0.018 if value >= 0 else value - 0.018
            ha = "left" if value >= 0 else "right"
            ax.text(x_text, yi, f"{value:.2f}", va="center", ha=ha, fontsize=8)
    ax.axvline(0, color="#333333", linewidth=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[p] for p in predictors])
    ax.set_xlim(-0.45, 0.5)
    ax.set_xlabel("Spearman correlation across source domains")
    ax.set_title("Popularity, not credibility, is the clearest external correlate")
    ax.grid(axis="x", alpha=0.22)
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=2)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    path = FIG_DIR / "fig2_source_attribute_correlations.png"
    fig.savefig(path, dpi=240)
    plt.close(fig)
    return path


def build_summary(records: pd.DataFrame) -> dict[str, Any]:
    source_summary = json.loads((SOURCE_PANEL_DIR / "summary.json").read_text(encoding="utf-8"))
    random_summary = json.loads((RANDOM_PROXY_DIR / "summary.json").read_text(encoding="utf-8"))
    positive = records[records["has_positive_posterior"]].copy()
    test_positive = positive[positive["split"] == "test"].copy()
    domain_corr = pd.read_csv(SOURCE_PANEL_DIR / "domain_correlations.csv")
    domain_panel = pd.read_csv(SOURCE_PANEL_DIR / "domain_panel.csv")
    eligible_domains = domain_panel[domain_panel["candidate_articles"] >= 20].copy()
    tranco_corr = domain_corr[
        (domain_corr["predictor"] == "tranco_attention")
        & (domain_corr["outcome"] == "posterior_score_mean")
    ].iloc[0]
    prior_corr = domain_corr[
        (domain_corr["predictor"] == "tranco_attention")
        & (domain_corr["outcome"] == "prior_weight_mean")
    ].iloc[0]
    traffic_corr = domain_corr[
        (domain_corr["predictor"] == "mbfc_traffic_num")
        & (domain_corr["outcome"] == "posterior_score_mean")
    ].iloc[0]
    credibility_corr = domain_corr[
        (domain_corr["predictor"] == "mbfc_credibility_num")
        & (domain_corr["outcome"] == "posterior_score_mean")
    ].iloc[0]
    credibility_prior_corr = domain_corr[
        (domain_corr["predictor"] == "mbfc_credibility_num")
        & (domain_corr["outcome"] == "prior_weight_mean")
    ].iloc[0]

    item_scores = load_item_scores()
    item_scores["record_has_positive"] = item_scores.groupby(["split", "record_idx"])["posterior_score"].transform(
        lambda values: bool((values > 0).any())
    )
    item_positive_records = item_scores[item_scores["record_has_positive"]].copy()
    item_test_positive_records = item_positive_records[item_positive_records["split"] == "test"].copy()
    within_record_spearman: list[float] = []
    within_record_test_spearman: list[float] = []
    for (split, _record_idx), group in item_positive_records.groupby(["split", "record_idx"]):
        if group["prior_score"].nunique() <= 1 or group["posterior_score"].nunique() <= 1:
            continue
        rho = group["prior_score"].corr(group["posterior_score"], method="spearman")
        if pd.notna(rho):
            within_record_spearman.append(float(rho))
            if split == "test":
                within_record_test_spearman.append(float(rho))

    by_split = (
        records.groupby("split")
        .agg(
            records=("split", "size"),
            positive_records=("has_positive_posterior", "sum"),
            mean_news_count=("news_count", "mean"),
            mean_prior_alignment=("prior_alignment_rate", "mean"),
        )
        .reset_index()
        .to_dict("records")
    )

    return {
        "records": int(len(records)),
        "candidate_articles": int(source_summary["candidate_articles"]),
        "positive_records": int(records["has_positive_posterior"].sum()),
        "positive_record_rate": float(records["has_positive_posterior"].mean()),
        "mean_news_count": float(records["news_count"].mean()),
        "mean_prior_alignment_positive_records": float(positive["prior_alignment_rate"].mean()),
        "mean_prior_waste_positive_records": float(positive["prior_waste_rate"].mean()),
        "prior_top_positive_rate": float(positive["prior_top_positive"].mean()),
        "prior_exact_top_overlap_rate": float(positive["prior_top_matches_post_top"].mean()),
        "test_positive_records": int(len(test_positive)),
        "test_mean_prior_alignment_positive_records": float(test_positive["prior_alignment_rate"].mean()),
        "test_prior_top_positive_rate": float(test_positive["prior_top_positive"].mean()),
        "test_prior_exact_top_overlap_rate": float(test_positive["prior_top_matches_post_top"].mean()),
        "source_panel": source_summary,
        "random_proxy": random_summary,
        "by_split": by_split,
        "tranco_attention_posterior_spearman": float(tranco_corr["spearman"]),
        "tranco_attention_prior_spearman": float(prior_corr["spearman"]),
        "mbfc_traffic_posterior_spearman": float(traffic_corr["spearman"]),
        "mbfc_credibility_posterior_spearman": float(credibility_corr["spearman"]),
        "mbfc_credibility_prior_spearman": float(credibility_prior_corr["spearman"]),
        "item_positive_record_spearman": float(
            item_positive_records["prior_score"].corr(item_positive_records["posterior_score"], method="spearman")
        ),
        "test_item_positive_record_spearman": float(
            item_test_positive_records["prior_score"].corr(
                item_test_positive_records["posterior_score"], method="spearman"
            )
        ),
        "within_record_spearman_mean": float(pd.Series(within_record_spearman).mean()),
        "within_record_spearman_median": float(pd.Series(within_record_spearman).median()),
        "test_within_record_spearman_mean": float(pd.Series(within_record_test_spearman).mean()),
        "test_within_record_spearman_median": float(pd.Series(within_record_test_spearman).median()),
        "domain_prior_posterior_spearman": float(
            eligible_domains["prior_weight_mean"].corr(eligible_domains["posterior_score_mean"], method="spearman")
        ),
        "domain_prior_posterior_pearson": float(
            eligible_domains["prior_weight_mean"].corr(eligible_domains["posterior_score_mean"], method="pearson")
        ),
    }


def latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def format_num(value: float, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "--"
    return f"{value:.{digits}f}"


def write_numbers_tex(summary: dict[str, Any]) -> None:
    def pct(value: float) -> str:
        return f"{value:.1%}".replace("%", r"\%")

    lines = [
        "% Auto-generated by generate_no_training_report.py; do not edit by hand.",
        rf"\newcommand{{\MatchedKalshiRecords}}{{{summary['records']:,}}}",
        rf"\newcommand{{\CandidateNewsItems}}{{{summary['candidate_articles']:,}}}",
        rf"\newcommand{{\PositivePosteriorRecords}}{{{summary['positive_records']:,}}}",
        rf"\newcommand{{\PositivePosteriorRate}}{{{pct(summary['positive_record_rate'])}}}",
        rf"\newcommand{{\JoinedDomains}}{{{summary['source_panel']['domains']}}}",
        rf"\newcommand{{\MBFCMatchedDomains}}{{{summary['source_panel']['mbfc_matched_domains']}}}",
        rf"\newcommand{{\TrancoMatchedDomains}}{{{summary['source_panel']['tranco_matched_domains']}}}",
        rf"\newcommand{{\IffyFlaggedDomains}}{{{summary['source_panel']['iffy_flagged_domains']}}}",
        rf"\newcommand{{\PriorAlignmentPositive}}{{{summary['mean_prior_alignment_positive_records']:.3f}}}",
        rf"\newcommand{{\PriorWastePositive}}{{{summary['mean_prior_waste_positive_records']:.3f}}}",
        rf"\newcommand{{\PriorTopPositiveRate}}{{{pct(summary['prior_top_positive_rate'])}}}",
        rf"\newcommand{{\PriorExactTopRate}}{{{pct(summary['prior_exact_top_overlap_rate'])}}}",
        rf"\newcommand{{\TestPriorAlignmentPositive}}{{{summary['test_mean_prior_alignment_positive_records']:.3f}}}",
        rf"\newcommand{{\TestPriorTopPositiveRate}}{{{pct(summary['test_prior_top_positive_rate'])}}}",
        rf"\newcommand{{\TestPriorExactTopRate}}{{{pct(summary['test_prior_exact_top_overlap_rate'])}}}",
        rf"\newcommand{{\TrancoPosteriorSpearman}}{{{summary['tranco_attention_posterior_spearman']:.3f}}}",
        rf"\newcommand{{\TrancoPriorSpearman}}{{{summary['tranco_attention_prior_spearman']:.3f}}}",
        rf"\newcommand{{\MBFCTrafficPosteriorSpearman}}{{{summary['mbfc_traffic_posterior_spearman']:.3f}}}",
        rf"\newcommand{{\MBFCCredibilityPosteriorSpearman}}{{{summary['mbfc_credibility_posterior_spearman']:.3f}}}",
        rf"\newcommand{{\MBFCCredibilityPriorSpearman}}{{{summary['mbfc_credibility_prior_spearman']:.3f}}}",
        rf"\newcommand{{\ItemPositiveRecordSpearman}}{{{summary['item_positive_record_spearman']:.3f}}}",
        rf"\newcommand{{\TestItemPositiveRecordSpearman}}{{{summary['test_item_positive_record_spearman']:.3f}}}",
        rf"\newcommand{{\WithinRecordSpearmanMean}}{{{summary['within_record_spearman_mean']:.3f}}}",
        rf"\newcommand{{\TestWithinRecordSpearmanMean}}{{{summary['test_within_record_spearman_mean']:.3f}}}",
        rf"\newcommand{{\DomainPriorPosteriorSpearman}}{{{summary['domain_prior_posterior_spearman']:.3f}}}",
        rf"\newcommand{{\DomainPriorPosteriorPearson}}{{{summary['domain_prior_posterior_pearson']:.3f}}}",
        rf"\newcommand{{\RandomTopOneZeroMissRate}}{{{pct(summary['random_proxy']['random_top1_zero_miss_given_high_rate'])}}}",
        "",
    ]
    NUMBERS_TEX_PATH.write_text("\n".join(lines), encoding="utf-8")


def latex_table(
    path: Path,
    frame: pd.DataFrame,
    align: str,
    caption: str,
    label: str,
    notes: str | None = None,
) -> None:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        rf"\caption{{{latex_escape(caption)}}}",
        r"\small",
        r"\resizebox{\linewidth}{!}{%",
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(latex_escape(c) for c in frame.columns) + r" \\",
        r"\midrule",
    ]
    for _, row in frame.iterrows():
        lines.append(" & ".join(latex_escape(row[c]) for c in frame.columns) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"}"])
    if notes:
        lines.append(rf"\caption*{{\footnotesize {latex_escape(notes)}}}")
    lines.extend([rf"\label{{{label}}}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report_tables(summary: dict[str, Any]) -> None:
    signal_table = pd.DataFrame(
        [
            {
                "Check": "Item ranking",
                "Estimate": f"test rho {summary['test_item_positive_record_spearman']:.3f}",
                "Read": "weak item faithfulness",
            },
            {
                "Check": "Within-record ranking",
                "Estimate": f"test mean rho {summary['test_within_record_spearman_mean']:.3f}",
                "Read": "weak but positive",
            },
            {
                "Check": "Mass on positive news",
                "Estimate": f"test mean {summary['test_mean_prior_alignment_positive_records']:.3f}",
                "Read": "useful, not oracle",
            },
            {
                "Check": "Top item nonzero",
                "Estimate": f"test {summary['test_prior_top_positive_rate']:.1%}",
                "Read": "often relevant",
            },
            {
                "Check": "Exact top match",
                "Estimate": f"test {summary['test_prior_exact_top_overlap_rate']:.1%}",
                "Read": "low recovery",
            },
            {
                "Check": "Domain averages",
                "Estimate": f"domain Spearman {summary['domain_prior_posterior_spearman']:.3f}",
                "Read": "stronger aggregated",
            },
        ]
    )
    latex_table(
        TABLE_DIR / "table1_prior_signal.tex",
        signal_table,
        "lll",
        "How closely does the learned prior attributor match posterior helpfulness?",
        "tab:prior-signal",
        "q is the released prior-attributor score; posterior-positive means the hindsight/posterior score s is greater than zero. Test estimates use held-out Kalshi records.",
    )

    corr = pd.read_csv(SOURCE_PANEL_DIR / "domain_correlations.csv")
    keep = corr[
        corr["predictor"].isin(
            ["tranco_attention", "mbfc_traffic_num", "mbfc_credibility_num", "mbfc_reporting_num", "iffy_flag_num"]
        )
        & corr["outcome"].isin(["posterior_score_mean", "prior_weight_mean"])
    ].copy()
    labels = {
        "tranco_attention": "Tranco attention",
        "mbfc_traffic_num": "MBFC traffic",
        "mbfc_credibility_num": "MBFC credibility",
        "mbfc_reporting_num": "MBFC reporting",
        "iffy_flag_num": "Iffy flag",
        "posterior_score_mean": "Posterior helpfulness",
        "prior_weight_mean": "Prior attention",
    }
    keep = keep.assign(
        Predictor=keep["predictor"].map(labels),
        Outcome=keep["outcome"].map(labels),
        Domains=keep["n_domains"].astype(int),
        Spearman=keep["spearman"].map(lambda x: format_num(x, 3)),
    )[["Predictor", "Outcome", "Domains", "Spearman"]]
    latex_table(
        TABLE_DIR / "table2_source_correlations.tex",
        keep,
        "p{0.3\\linewidth}p{0.28\\linewidth}rr",
        "Unadjusted source-attribute correlations.",
        "tab:source-correlations",
        "Spearman correlations are computed across source domains with at least 20 candidate articles. These are descriptive correlations, not causal effects.",
    )


def write_markdown_report(summary: dict[str, Any]) -> None:
    text = f"""# Attention Proxies in SWM Kalshi News Attributions

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
  `{summary['tranco_attention_posterior_spearman']:.3f}`.
- MBFC traffic vs. posterior helpfulness: Spearman
  `{summary['mbfc_traffic_posterior_spearman']:.3f}`.
- MBFC credibility vs. posterior helpfulness: Spearman
  `{summary['mbfc_credibility_posterior_spearman']:.3f}`.

These are descriptive source-domain correlations, not causal estimates.

The SWM prior attributor helps interpret why source-level regularities appear,
but it is not a faithful item-level explanation of hindsight attribution.

On held-out Kalshi records with posterior-positive news:

- Item-level `q` versus `s` Spearman is only `{summary['test_item_positive_record_spearman']:.3f}`.
- The prior puts `{summary['test_mean_prior_alignment_positive_records']:.3f}` of its mass on
  posterior-positive news.
- The prior top item is posterior-positive in `{summary['test_prior_top_positive_rate']:.1%}`
  of positive records, but exactly matches the posterior top item in only
  `{summary['test_prior_exact_top_overlap_rate']:.1%}`.

At the source-domain level, prior/posterior relation is much stronger: mean prior attention and
mean posterior helpfulness correlate at Spearman
`{summary['domain_prior_posterior_spearman']:.3f}` among domains with at least 20
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
"""
    MD_PATH.write_text(text, encoding="utf-8")


def write_provenance(summary: dict[str, Any], fig_paths: list[Path]) -> None:
    tectonic = find_tectonic()
    payload = {
        "created": "2026-06-16",
        "scope": "No new LLM training or inference; released SWM-Bench Kalshi data and static external source tables only.",
        "commands": [
            "python scripts/build_source_attribute_panel.py",
            "MPLCONFIGDIR=tmp/mplconfig python scripts/generate_no_training_report.py",
            f"{Path(tectonic).name} {TEX_PATH.name}  # cwd={repo_path(OUT_DIR)}"
            if tectonic
            else "tectonic unavailable",
        ],
        "inputs": {
            "swm_raw_kalshi": [
                str(path)
                for path in [
                    RAW_DIR / "kalshi_prior_attributed_train_2025-11-01.jsonl",
                    RAW_DIR / "kalshi_prior_attributed_test_2025-11-01.jsonl",
                    RAW_DIR / "kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl",
                    RAW_DIR / "kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl",
                ]
            ],
            "source_panel": str(SOURCE_PANEL_DIR),
            "random_proxy": str(RANDOM_PROXY_DIR),
            "external": [
                "data/external/tranco_top_1m.csv.zip",
                "data/external/mbfcext_combined.json",
                "data/external/iffy_index.json",
            ],
        },
        "outputs": {
            "pdf": str(PDF_PATH),
            "tex": str(TEX_PATH),
            "tectonic_log": str(TEX_COMPILE_LOG_PATH),
            "markdown_report": str(MD_PATH),
            "numbers_tex": str(NUMBERS_TEX_PATH),
            "figures": [str(path) for path in fig_paths],
            "tables_dir": str(TABLE_DIR),
        },
        "summary": summary,
    }
    PROVENANCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_tex(summary: dict[str, Any], fig_paths: list[Path]) -> None:
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=0.92in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{array}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs}",
        r"\usepackage{amsmath}",
        r"\usepackage{caption}",
        r"\usepackage{float}",
        r"\usepackage{hyperref}",
        r"\usepackage{xurl}",
        r"\usepackage{xcolor}",
        r"\graphicspath{{figures/}}",
        r"\hypersetup{colorlinks=true, linkcolor=blue!45!black, urlcolor=blue!45!black, citecolor=blue!45!black}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0.55em}",
        r"\setlength{\emergencystretch}{3em}",
        r"\captionsetup{font=small, labelfont=bf}",
        r"\input{numbers.tex}",
        r"\title{Attention Proxies in SWM Kalshi News Attributions}",
        r"\author{Prediction-market exploratory analysis}",
        r"\date{June 16, 2026}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{abstract}",
        (
            "This memo asks whether external source attributes help identify news that is useful for "
            "prediction-market belief updates in the released Social World Model (SWM) Kalshi data. The "
            "main result is source-level: popularity and traffic are positive correlates of posterior "
            "helpfulness, while raw credibility labels are not. Tranco attention correlates with posterior "
            "helpfulness at Spearman \\TrancoPosteriorSpearman, and MBFC traffic is similar "
            "(\\MBFCTrafficPosteriorSpearman). MBFC credibility is negative in the unadjusted domain "
            "panel (\\MBFCCredibilityPosteriorSpearman), a descriptive pattern that is likely confounded "
            "by source and category mix. A second diagnostic explains why source-level patterns should "
            "not be read as item-level explanations: on held-out Kalshi records, item-level prior "
            "attention and posterior helpfulness have Spearman correlation only "
            "\\TestItemPositiveRecordSpearman\\ among records with any posterior-positive news."
        ),
        r"\end{abstract}",
        r"\section{Objective and Short Answer}",
        (
            "The broader project asks whether prediction-market rationales that attract attention are also "
            "the rationales that add predictive information. The SWM release does not contain community "
            "rationales or comment engagement. It does contain candidate news, learned prior-attributor "
            "scores, and hindsight/posterior attribution scores. This report therefore tests the closest "
            "available source-level analogue."
        ),
        r"\begin{itemize}",
        (
            "\\item Popularity is the clearest external correlate. Tranco attention and MBFC traffic are "
            "positively associated with posterior helpfulness and prior attention."
        ),
        (
            "\\item Credibility is not positively associated with helpfulness in the raw panel. MBFC "
            "credibility is negative for both posterior helpfulness and prior attention, but this is "
            "descriptive and likely confounded."
        ),
        (
            "\\item The SWM prior attributor helps interpret these source patterns but is not a faithful "
            "item-level explanation. In held-out positive records, exact top-item recovery is only "
            "\\TestPriorExactTopRate."
        ),
        r"\end{itemize}",
        r"\section{What the SWM Scores Mean}",
        (
            "The SWM paper models prediction-market prices as social beliefs and news articles as possible "
            "events that move those beliefs. For each market transition, the paper uses two attribution "
            "models. A posterior attributor $Q_\\phi$ sees the realized next state and assigns hindsight "
            "responsibility to candidate news. A prior attributor $P_\\eta$ sees only the current market "
            "context and candidate news, and is trained to approximate the posterior weights. In the "
            "released files used here, $s_{ri}$ is the posterior/hindsight score for news item $i$ in "
            "record $r$, and $q_{ri}$ is the prior-attributor score for that same item."
        ),
        r"\begin{align}",
        r"q_{ri} &= P_\eta(Z_r=i \mid s_r,E_r),\\",
        r"H_d &= \frac{1}{N_d}\sum_{(r,i):d_{ri}=d}s_{ri},\qquad",
        r"A_d = \frac{1}{N_d}\sum_{(r,i):d_{ri}=d}q_{ri}.",
        r"\end{align}",
        (
            "$H_d$ is a domain's average hindsight helpfulness, and $A_d$ is the average learned prior "
            "attention assigned to that domain. The analysis uses \\MatchedKalshiRecords\\ matched Kalshi "
            "records and \\CandidateNewsItems\\ candidate news items. \\PositivePosteriorRecords\\ records "
            "(\\PositivePosteriorRate) have at least one positive posterior attribution. We join article "
            "domains to Tranco popularity ranks, MBFC-derived traffic and credibility fields, and Iffy "
            "flags."
        ),
        r"\section{Finding 1: Popularity Is Clearer Than Credibility}",
        (
            "External source attributes add a second distinction. Popularity measures are positive "
            "correlates of both posterior helpfulness and prior attention: Tranco attention has Spearman "
            "\\TrancoPosteriorSpearman\\ with posterior helpfulness and \\TrancoPriorSpearman\\ with prior "
            "attention. MBFC traffic is similar for posterior helpfulness (\\MBFCTrafficPosteriorSpearman). "
            "By contrast, MBFC credibility is negative in the raw domain panel "
            "(\\MBFCCredibilityPosteriorSpearman\\ with posterior helpfulness and "
            "\\MBFCCredibilityPriorSpearman\\ with prior attention). This does not mean credibility causes "
            "lower usefulness. The domain panel is confounded by category mix, source mix, and what kinds "
            "of events happened to move Kalshi prices in the release."
        ),
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=0.92\linewidth]{fig2_source_attribute_correlations.png}",
        (
            "\\caption{Bars are unadjusted Spearman correlations across source domains. Positive values "
            "mean domains higher on the attribute also have higher average posterior helpfulness or prior "
            "attention. Popularity and traffic are positive; MBFC credibility and factual-reporting labels "
            "are negative in this raw panel. These are descriptive correlations, not causal estimates.}"
        ),
        r"\label{fig:source-correlations}",
        r"\end{figure}",
        r"\input{tables/table2_source_correlations.tex}",
        r"\section{Finding 2: Source-Level Attention and Helpfulness Move Together}",
        (
            "The external-source result is consistent with the model's own source-level behavior. Among "
            "source domains with at least 20 candidate articles, mean prior attention $A_d$ and mean "
            "posterior helpfulness $H_d$ have Spearman correlation \\DomainPriorPosteriorSpearman\\ "
            "(Pearson \\DomainPriorPosteriorPearson). In other words, domains that receive more learned "
            "attention also tend to be domains whose articles receive more hindsight attribution. This is "
            "a source-level association, not proof that popularity or credibility caused the market move."
        ),
        r"\begin{figure}[H]",
        r"\centering",
        r"\includegraphics[width=0.92\linewidth]{fig1_domain_prior_vs_posterior.png}",
        (
            "\\caption{Each dot is a source domain with at least 20 candidate news articles. The horizontal "
            "axis is the domain's mean prior-attributor weight $A_d$; the vertical axis is its mean "
            "posterior helpfulness $H_d$. The positive trend shows that source-level averages line up, but "
            "it does not show causal influence or faithful item-level explanation.}"
        ),
        r"\label{fig:domain-prior-posterior}",
        r"\end{figure}",
        r"\section{Finding 3: Source Patterns Are Not Item-Level Explanations}",
        (
            "The source-level correlations are easier to interpret after checking the item-level "
            "attribution behavior. Because $P_\\eta$ is trained to approximate posterior attributions, "
            "some relationship between $q_{ri}$ and $s_{ri}$ is expected. At the candidate-news level it "
            "is weak: among held-out records with any posterior-positive news, the item-level Spearman "
            "correlation between $q_{ri}$ and $s_{ri}$ is \\TestItemPositiveRecordSpearman. The prior "
            "selects useful candidates more often than chance, but exact recovery of the hindsight top "
            "item remains low at \\TestPriorExactTopRate."
        ),
        r"\input{tables/table1_prior_signal.tex}",
        r"\section{Interpretation}",
        (
            "The results support a careful version of the attention-is-not-information claim. Source "
            "popularity is a useful predictor of both learned attention and hindsight helpfulness in this "
            "release; credibility labels are not. But these are source-level regularities, not causal "
            "estimates and not faithful explanations of which exact article mattered. A system can learn "
            "where useful information often comes from without reliably explaining which particular item "
            "drove a belief update."
        ),
        r"\section{What This Does Not Answer}",
        (
            "This report does not establish that a source caused a market move. It also does not test "
            "forecast-community rationales, likes, comments, author reputation, or market microstructure. "
            "Those require a Manifold- or Metaculus-style dataset with written rationales, engagement "
            "metrics, timestamps, price movement around each rationale, and final resolution. The SWM "
            "news analysis is best read as a reproducible baseline for that later rationale-level design."
        ),
        r"\clearpage",
        r"\appendix",
        r"\section{Provenance and Reproducibility}",
        "The report was generated without new LLM calls. The two analysis scripts were:",
        r"\begin{quote}",
        r"\small\texttt{scripts/build\_source\_attribute\_panel.py}\\",
        r"\small\texttt{scripts/generate\_no\_training\_report.py}",
        r"\end{quote}",
        (
            "The latter compiles this TeX source with the bundled Tectonic engine. The bundle includes "
            "this TeX file, a rendered PDF, figures, CSV tables, generated TeX tables, numeric macros, "
            "a Markdown report, and provenance JSON."
        ),
        r"\section{Known Limits}",
        (
            "No new LLM training or inference was run. The released Kalshi data contain candidate news, "
            "not forecast-community rationales. The posterior attribution scores are hindsight labels and "
            "should not be interpreted as formal causal proof. Actual random-news forecast harm cannot be "
            "scored without unreleased prediction outputs or a rerun of the trained world model; the "
            "available no-training proxy found a \\RandomTopOneZeroMissRate\\ random top-one zero-miss "
            "rate among high-attribution records."
        ),
        r"\section{References}",
        r"\begin{itemize}",
        r"\item Yu et al. (2026), \textit{Building Social World Models with Large Language Models}: \url{https://arxiv.org/pdf/2606.11482}",
        r"\item SWM-Bench dataset: \url{https://huggingface.co/datasets/ulab-ai/swm-bench}",
        r"\item Social World Model code: \url{https://github.com/ulab-uiuc/social-world-model}",
        r"\item Tranco: \url{https://tranco-list.eu/}",
        r"\item Iffy Index: \url{https://iffy.news/index/}",
        r"\item MBFC extension data: \url{https://github.com/drmikecrowe/mbfcext/}",
        r"\end{itemize}",
        r"\end{document}",
        "",
    ]
    TEX_PATH.write_text("\n".join(lines), encoding="utf-8")


def find_tectonic() -> str | None:
    home = Path.home()
    candidates = [
        os.environ.get("TECTONIC_BIN"),
        shutil.which("tectonic"),
        str(
            home
            / ".codex/.tmp/bundled-marketplaces/openai-bundled/plugins/latex/bin/tectonic"
        ),
    ]
    candidates.extend(
        str(path)
        for path in home.glob(
            "Library/Caches/com.openai.codex/**/plugins/latex/bin/tectonic"
        )
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def compile_tex_pdf() -> None:
    tectonic = find_tectonic()
    if tectonic is None:
        raise RuntimeError(
            "No TeX engine found. Expected tectonic on PATH or the bundled Codex Tectonic binary."
        )

    cache_dir = REPO_ROOT / "tmp/tectonic-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TECTONIC_CACHE_DIR"] = str(cache_dir)
    env["XDG_CACHE_HOME"] = str(cache_dir)

    result = subprocess.run(
        [tectonic, TEX_PATH.name],
        cwd=OUT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    TEX_COMPILE_LOG_PATH.write_text(
        "\n".join(
            [
                f"command: {Path(tectonic).name} {TEX_PATH.name}",
                f"cwd: {repo_path(OUT_DIR)}",
                f"cache_dir: {repo_path(cache_dir)}",
                f"returncode: {result.returncode}",
                "",
                "stdout:",
                result.stdout,
                "",
                "stderr:",
                result.stderr,
            ]
        ),
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Tectonic failed with exit code {result.returncode}. See {TEX_COMPILE_LOG_PATH}."
        )
    if not PDF_PATH.exists():
        raise RuntimeError(f"Tectonic completed but did not create {PDF_PATH}.")


def main() -> int:
    prepare_outputs()
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    records = load_record_level()
    records.to_csv(TABLE_DIR / "record_level_prior_posterior.csv", index=False)
    summary = build_summary(records)
    fig_paths = [
        figure_domain_prior_vs_posterior(),
        figure_source_attribute_correlations(),
    ]
    summary["figures"] = [str(path) for path in fig_paths]
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_numbers_tex(summary)
    write_report_tables(summary)
    write_markdown_report(summary)
    write_tex(summary, fig_paths)
    compile_tex_pdf()
    write_provenance(summary, fig_paths)
    print(
        json.dumps(
            {
                "summary": str(SUMMARY_PATH),
                "tex": str(TEX_PATH),
                "pdf": str(PDF_PATH),
                "tectonic_log": str(TEX_COMPILE_LOG_PATH),
                "markdown_report": str(MD_PATH),
                "provenance": str(PROVENANCE_PATH),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
