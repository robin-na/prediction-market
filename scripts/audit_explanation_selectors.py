#!/usr/bin/env python3
"""Audit candidate-selection baselines for the explanation pilot.

The goal is to compare learned selection against simple deployable rules before
we treat a supervisor as meaningful. The input is the candidate-level ranking
dataset produced by build_explanation_ranking_dataset.py.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_TEST_INPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv"
)
DEFAULT_TRAIN_INPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_train_all_batches_valid_ranking_candidates.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/explanation_pilot")
DEFAULT_PREFIX = "gemma4_26b_selector_audit_20260629"

EPSILON = 1e-9
CLASS_COLUMNS = [
    "class_source_credibility",
    "class_base_rate_calibration",
    "class_resolution_rule",
    "class_causal_chain",
    "class_direct_resolution",
    "class_trend_continuation",
    "class_overreaction_correction",
    "class_underreaction_correction",
    "class_evidence_irrelevance",
    "class_market_microstructure",
    "class_other",
]
CORE_RELATIVE_COLUMNS = [
    "confidence_z",
    "posterior_z",
    "abs_explanation_delta_z",
    "selected_evidence_count_z",
    "evidence_weights_count_z",
]


@dataclass(frozen=True)
class Selector:
    name: str
    chooser: Callable[[pd.DataFrame], pd.Series | None]


def parse_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["1", "true", "yes", "y"])


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def prep_frame(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = frame.copy()
    out["dataset"] = dataset
    for column in [
        "candidate_index",
        "num_candidates_for_prompt",
        "market_delta",
        "explanation_delta",
        "posterior",
        "posterior_error_to_market",
        "improvement_vs_persistence",
        "delta_error",
        "selected_evidence_count",
        "evidence_weights_count",
        "confidence",
    ]:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    out["confidence_raw"] = out["confidence"]
    out["confidence_out_of_bounds"] = out["confidence"].lt(0) | out["confidence"].gt(1)
    out.loc[out["confidence_out_of_bounds"], "confidence"] = np.nan
    for column in [
        "is_best_candidate",
        "is_recommended_candidate",
        "is_positive_improvement",
        "direction_match",
    ] + [column for column in CLASS_COLUMNS if column in out.columns]:
        if column in out.columns:
            out[column] = parse_bool_series(out[column])
    out["prior"] = out["posterior"] - out["explanation_delta"]
    out["market_after"] = out["prior"] + out["market_delta"]
    out["abs_market_delta"] = out["market_delta"].abs()
    out["abs_explanation_delta"] = out["explanation_delta"].abs()
    out["market_direction"] = np.select(
        [out["market_delta"] > EPSILON, out["market_delta"] < -EPSILON],
        ["up", "down"],
        default="flat",
    )
    out["candidate_direction"] = np.select(
        [out["explanation_delta"] > EPSILON, out["explanation_delta"] < -EPSILON],
        ["up", "down"],
        default="flat",
    )
    out["market_move_bin"] = pd.cut(
        out["abs_market_delta"],
        bins=[-0.001, 0.0, 0.02, 0.05, 0.15, math.inf],
        labels=["zero", "tiny", "small", "medium", "large"],
        include_lowest=True,
    ).astype(str)
    out["valid_candidate_count_bin"] = out["num_candidates_for_prompt"].astype("Int64").astype(str)
    return out


def add_prompt_relative_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    relative_columns = [
        "confidence",
        "posterior",
        "abs_explanation_delta",
        "selected_evidence_count",
        "evidence_weights_count",
    ]
    for column in relative_columns:
        group = out.groupby("custom_id")[column]
        mean = group.transform("mean")
        std = group.transform("std").replace(0, np.nan)
        out[f"{column}_z"] = ((out[column] - mean) / std).replace([np.inf, -np.inf], np.nan)
        out[f"{column}_z"] = out[f"{column}_z"].fillna(0)
    return out


def choose_by_sort(
    group: pd.DataFrame,
    column: str,
    *,
    ascending: bool,
    require_mask: pd.Series | None = None,
) -> pd.Series | None:
    subset = group if require_mask is None else group[require_mask]
    if subset.empty:
        return None
    return subset.sort_values(
        [column, "candidate_index"],
        ascending=[ascending, True],
        na_position="last",
    ).iloc[0]


def choose_recommended(group: pd.DataFrame) -> pd.Series | None:
    return choose_by_sort(
        group,
        "candidate_index",
        ascending=True,
        require_mask=group["is_recommended_candidate"],
    )


def choose_first(group: pd.DataFrame) -> pd.Series | None:
    return choose_by_sort(group, "candidate_index", ascending=True)


def selector_set() -> list[Selector]:
    return [
        Selector("gemma_recommended", choose_recommended),
        Selector("first_candidate", choose_first),
        Selector("max_confidence", lambda group: choose_by_sort(group, "confidence", ascending=False)),
        Selector("max_posterior", lambda group: choose_by_sort(group, "posterior", ascending=False)),
        Selector("min_posterior", lambda group: choose_by_sort(group, "posterior", ascending=True)),
        Selector(
            "max_abs_update",
            lambda group: choose_by_sort(group.assign(_metric=group["explanation_delta"].abs()), "_metric", ascending=False),
        ),
        Selector(
            "min_abs_update",
            lambda group: choose_by_sort(group.assign(_metric=group["explanation_delta"].abs()), "_metric", ascending=True),
        ),
        Selector("max_positive_update", lambda group: choose_by_sort(group, "explanation_delta", ascending=False)),
        Selector("max_negative_update", lambda group: choose_by_sort(group, "explanation_delta", ascending=True)),
        Selector(
            "max_selected_evidence_count",
            lambda group: choose_by_sort(group, "selected_evidence_count", ascending=False),
        ),
        Selector(
            "max_evidence_weights_count",
            lambda group: choose_by_sort(group, "evidence_weights_count", ascending=False),
        ),
        Selector(
            "oracle_best_candidate",
            lambda group: choose_by_sort(group, "posterior_error_to_market", ascending=True),
        ),
    ]


def prompt_summaries(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for custom_id, group in frame.groupby("custom_id", sort=False):
        best = group[group["is_best_candidate"]].sort_values("candidate_index").iloc[0]
        signs = set(group["candidate_direction"].astype(str))
        rows.append(
            {
                "dataset": group["dataset"].iloc[0],
                "custom_id": custom_id,
                "pilot_row_id": group["pilot_row_id"].iloc[0],
                "category": group["category"].iloc[0],
                "market_delta": float(group["market_delta"].iloc[0]),
                "abs_market_delta": float(group["abs_market_delta"].iloc[0]),
                "market_direction": group["market_direction"].iloc[0],
                "market_move_bin": group["market_move_bin"].iloc[0],
                "valid_candidate_count": int(len(group)),
                "valid_candidate_count_bin": str(len(group)),
                "posterior_range": float(group["posterior"].max() - group["posterior"].min()),
                "posterior_std": float(group["posterior"].std(ddof=0)),
                "abs_update_range": float(group["abs_explanation_delta"].max() - group["abs_explanation_delta"].min()),
                "multi_direction_candidates": len(signs - {"flat"}) > 1
                or ("flat" in signs and len(signs) > 1),
                "helpful_candidate_available": bool(group["is_positive_improvement"].any()),
                "best_candidate_id": best["explanation_id"],
                "best_candidate_index": int(best["candidate_index"]),
                "best_selected_evidence_count": float(best["selected_evidence_count"]),
                "best_evidence_weights_count": float(best["evidence_weights_count"]),
                "best_confidence": float(best["confidence"]),
                "best_abs_update": float(abs(best["explanation_delta"])),
                "best_positive_improvement": bool(best["is_positive_improvement"]),
            }
        )
    return pd.DataFrame(rows)


def summarize_selected(selected: pd.DataFrame, selector_name: str) -> dict[str, float | int | str]:
    if selected.empty:
        return {
            "selector": selector_name,
            "coverage_prompt_count": 0,
            "top1_rate": math.nan,
            "mean_selected_error": math.nan,
            "median_selected_error": math.nan,
            "mean_improvement_vs_persistence": math.nan,
            "positive_improvement_rate": math.nan,
            "direction_match_rate": math.nan,
        }
    return {
        "selector": selector_name,
        "coverage_prompt_count": int(len(selected)),
        "top1_rate": float(selected["is_best_candidate"].mean()),
        "mean_selected_error": float(selected["posterior_error_to_market"].mean()),
        "median_selected_error": float(selected["posterior_error_to_market"].median()),
        "mean_improvement_vs_persistence": float(selected["improvement_vs_persistence"].mean()),
        "positive_improvement_rate": float(selected["is_positive_improvement"].mean()),
        "direction_match_rate": float(selected["direction_match"].mean()),
    }


def random_expected_row(frame: pd.DataFrame) -> dict[str, float | int | str]:
    prompt_rows = []
    for _, group in frame.groupby("custom_id", sort=False):
        prompt_rows.append(
            {
                "top1": 1.0 / len(group),
                "error": float(group["posterior_error_to_market"].mean()),
                "improvement": float(group["improvement_vs_persistence"].mean()),
                "positive": float(group["is_positive_improvement"].mean()),
                "direction": float(group["direction_match"].mean()),
            }
        )
    prompt_frame = pd.DataFrame(prompt_rows)
    return {
        "selector": "random_expected",
        "coverage_prompt_count": int(len(prompt_frame)),
        "top1_rate": float(prompt_frame["top1"].mean()),
        "mean_selected_error": float(prompt_frame["error"].mean()),
        "median_selected_error": math.nan,
        "mean_improvement_vs_persistence": float(prompt_frame["improvement"].mean()),
        "positive_improvement_rate": float(prompt_frame["positive"].mean()),
        "direction_match_rate": float(prompt_frame["direction"].mean()),
    }


def apply_selectors(frame: pd.DataFrame, selectors: list[Selector]) -> pd.DataFrame:
    rows = []
    for custom_id, group in frame.groupby("custom_id", sort=False):
        for selector in selectors:
            chosen = selector.chooser(group)
            if chosen is None:
                continue
            row = chosen.to_dict()
            row["selector"] = selector.name
            rows.append(row)
    return pd.DataFrame(rows)


def fit_core_relative_logit(train_frame: pd.DataFrame, test_frame: pd.DataFrame) -> pd.DataFrame:
    train = add_prompt_relative_features(train_frame)
    test = add_prompt_relative_features(test_frame)
    features = [column for column in CORE_RELATIVE_COLUMNS if column in train.columns and column in test.columns]
    if not features:
        raise ValueError("no core relative features are available")
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=3000, class_weight="balanced"),
    )
    model.fit(train[features], train["is_best_candidate"].astype(int))
    scored = test.copy()
    scored["selector_score"] = model.predict_proba(test[features])[:, 1]
    rows = []
    for _, group in scored.groupby("custom_id", sort=False):
        chosen = group.sort_values(["selector_score", "candidate_index"], ascending=[False, True]).iloc[0]
        row = chosen.to_dict()
        row["selector"] = "core_relative_logit"
        rows.append(row)
    return pd.DataFrame(rows)


def selector_performance(frame: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    rows = [random_expected_row(frame)]
    for selector_name, group in selected.groupby("selector", sort=False):
        rows.append(summarize_selected(group, selector_name))
    out = pd.DataFrame(rows)
    out.insert(0, "dataset", frame["dataset"].iloc[0])
    out.insert(2, "total_prompt_count", int(frame["custom_id"].nunique()))
    out["coverage_rate"] = out["coverage_prompt_count"] / out["total_prompt_count"]
    return out


def stratum_performance(selected: pd.DataFrame) -> pd.DataFrame:
    strata = [
        ("category", "category"),
        ("market_direction", "market_direction"),
        ("market_move_bin", "market_move_bin"),
        ("valid_candidate_count", "valid_candidate_count_bin"),
    ]
    rows = []
    for selector_name, selector_group in selected.groupby("selector", sort=False):
        for stratum_type, column in strata:
            for value, group in selector_group.groupby(column, sort=False):
                summary = summarize_selected(group, selector_name)
                rows.append(
                    {
                        "dataset": group["dataset"].iloc[0],
                        "stratum_type": stratum_type,
                        "stratum": str(value),
                        **summary,
                    }
                )
        for class_column in [column for column in CLASS_COLUMNS if column in selector_group.columns]:
            class_group = selector_group[selector_group[class_column]]
            if class_group.empty:
                continue
            summary = summarize_selected(class_group, selector_name)
            rows.append(
                {
                    "dataset": class_group["dataset"].iloc[0],
                    "stratum_type": "selected_explanation_class",
                    "stratum": class_column.removeprefix("class_"),
                    **summary,
                }
            )
    return pd.DataFrame(rows)


def evidence_count_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for custom_id, group in frame.groupby("custom_id", sort=False):
        best = group[group["is_best_candidate"]].sort_values("candidate_index").iloc[0]
        max_selected = group["selected_evidence_count"].max()
        max_weighted = group["evidence_weights_count"].max()
        max_abs_update = group["abs_explanation_delta"].max()
        max_selected_tie_size = int(group["selected_evidence_count"].eq(max_selected).sum())
        max_weighted_tie_size = int(group["evidence_weights_count"].eq(max_weighted).sum())
        max_abs_update_tie_size = int(group["abs_explanation_delta"].eq(max_abs_update).sum())
        rows.append(
            {
                "dataset": group["dataset"].iloc[0],
                "custom_id": custom_id,
                "category": group["category"].iloc[0],
                "market_direction": group["market_direction"].iloc[0],
                "market_move_bin": group["market_move_bin"].iloc[0],
                "valid_candidate_count": int(len(group)),
                "best_has_max_selected_evidence_count": bool(
                    best["selected_evidence_count"] == max_selected
                ),
                "best_has_max_evidence_weights_count": bool(
                    best["evidence_weights_count"] == max_weighted
                ),
                "best_has_max_abs_update": bool(best["abs_explanation_delta"] == max_abs_update),
                "best_selected_evidence_count": float(best["selected_evidence_count"]),
                "prompt_max_selected_evidence_count": float(max_selected),
                "max_selected_evidence_count_tie_size": max_selected_tie_size,
                "best_evidence_weights_count": float(best["evidence_weights_count"]),
                "prompt_max_evidence_weights_count": float(max_weighted),
                "max_evidence_weights_count_tie_size": max_weighted_tie_size,
                "best_abs_update": float(best["abs_explanation_delta"]),
                "prompt_max_abs_update": float(max_abs_update),
                "max_abs_update_tie_size": max_abs_update_tie_size,
                "candidate_count": int(len(group)),
                "helpful_candidate_available": bool(group["is_positive_improvement"].any()),
                "posterior_range": float(group["posterior"].max() - group["posterior"].min()),
            }
        )
    return pd.DataFrame(rows)


def tie_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature, ascending in [
        ("selected_evidence_count", False),
        ("evidence_weights_count", False),
        ("abs_explanation_delta", False),
        ("confidence", False),
        ("posterior", False),
        ("posterior", True),
    ]:
        row_order_hits = []
        safe_hits = []
        tied_prompts = []
        tie_sizes = []
        best_among_extreme = []
        for _, group in frame.groupby("custom_id", sort=False):
            metric = group[feature]
            extreme = metric.min() if ascending else metric.max()
            tied = group[metric.eq(extreme)]
            if tied.empty:
                continue
            # The input ranking file is sorted by market-error rank, so this
            # reproduces the leaky result one gets from idxmax/idxmin tie
            # behavior on the ranking CSV.
            row_order_choice = tied.iloc[0]
            safe_choice = tied.sort_values("candidate_index", ascending=True).iloc[0]
            best_among_extreme.append(bool(tied["is_best_candidate"].any()))
            row_order_hits.append(bool(row_order_choice["is_best_candidate"]))
            safe_hits.append(bool(safe_choice["is_best_candidate"]))
            tied_prompts.append(len(tied) > 1)
            tie_sizes.append(len(tied))
        rows.append(
            {
                "dataset": frame["dataset"].iloc[0],
                "feature": feature,
                "extreme": "min" if ascending else "max",
                "prompt_count": len(safe_hits),
                "prompts_with_tie_rate": float(np.mean(tied_prompts)),
                "mean_tie_size": float(np.mean(tie_sizes)),
                "best_among_extreme_rate": float(np.mean(best_among_extreme)),
                "leaky_row_order_top1_rate": float(np.mean(row_order_hits)),
                "safe_candidate_index_top1_rate": float(np.mean(safe_hits)),
            }
        )
    return pd.DataFrame(rows)


def candidate_feature_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for feature in [
        "confidence",
        "posterior",
        "abs_explanation_delta",
        "selected_evidence_count",
        "evidence_weights_count",
    ]:
        by_best = frame.groupby("is_best_candidate")[feature].agg(["mean", "median", "std"]).reset_index()
        for _, row in by_best.iterrows():
            rows.append(
                {
                    "dataset": frame["dataset"].iloc[0],
                    "feature": feature,
                    "is_best_candidate": bool(row["is_best_candidate"]),
                    "mean": float(row["mean"]),
                    "median": float(row["median"]),
                    "std": float(row["std"]) if not pd.isna(row["std"]) else math.nan,
                }
            )
    return pd.DataFrame(rows)


def write_outputs(
    output_dir: Path,
    prefix: str,
    frames: dict[str, pd.DataFrame],
    summary: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(output_dir / f"{prefix}_{name}.csv", index=False)
    (output_dir / f"{prefix}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-input", type=Path, default=DEFAULT_TEST_INPUT)
    parser.add_argument("--train-input", type=Path, default=DEFAULT_TRAIN_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument(
        "--no-logit",
        action="store_true",
        help="Skip the train-to-test core relative logistic selector.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    test = prep_frame(pd.read_csv(args.test_input), "heldout_test72")
    train = prep_frame(pd.read_csv(args.train_input), "train_all_batches")
    selectors = selector_set()

    test_selected = apply_selectors(test, selectors)
    train_selected = apply_selectors(train, selectors)
    if not args.no_logit:
        test_selected = pd.concat(
            [test_selected, fit_core_relative_logit(train, test)],
            ignore_index=True,
        )

    performance = pd.concat(
        [
            selector_performance(train, train_selected),
            selector_performance(test, test_selected),
        ],
        ignore_index=True,
    )
    stratified = pd.concat(
        [stratum_performance(train_selected), stratum_performance(test_selected)],
        ignore_index=True,
    )
    evidence_diag = pd.concat(
        [evidence_count_diagnostics(train), evidence_count_diagnostics(test)],
        ignore_index=True,
    )
    tie_diag = pd.concat([tie_diagnostics(train), tie_diagnostics(test)], ignore_index=True)
    feature_diag = pd.concat(
        [candidate_feature_diagnostics(train), candidate_feature_diagnostics(test)],
        ignore_index=True,
    )
    prompts = pd.concat([prompt_summaries(train), prompt_summaries(test)], ignore_index=True)
    selected = pd.concat([train_selected, test_selected], ignore_index=True)

    summary = {
        "train_input": str(args.train_input),
        "test_input": str(args.test_input),
        "train_candidate_rows": int(len(train)),
        "train_prompt_count": int(train["custom_id"].nunique()),
        "test_candidate_rows": int(len(test)),
        "test_prompt_count": int(test["custom_id"].nunique()),
        "outputs": {
            name: str(args.output_dir / f"{args.prefix}_{name}.csv")
            for name in [
                "selector_performance",
                "stratified_performance",
                "evidence_count_diagnostics",
                "tie_diagnostics",
                "candidate_feature_diagnostics",
                "prompt_diagnostics",
                "selected_candidates",
            ]
        },
    }
    write_outputs(
        args.output_dir,
        args.prefix,
        {
            "selector_performance": performance,
            "stratified_performance": stratified,
            "evidence_count_diagnostics": evidence_diag,
            "tie_diagnostics": tie_diag,
            "candidate_feature_diagnostics": feature_diag,
            "prompt_diagnostics": prompts,
            "selected_candidates": selected,
        },
        summary,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(
        performance[
            performance["dataset"].eq("heldout_test72")
        ][
            [
                "selector",
                "coverage_prompt_count",
                "top1_rate",
                "mean_selected_error",
                "positive_improvement_rate",
                "direction_match_rate",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
