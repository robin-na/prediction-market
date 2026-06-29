#!/usr/bin/env python3
"""Audit the generation gap in Gemma explanation candidates.

This script asks how good the generated candidate pool is before selector
quality enters the picture. For each prompt, it computes the oracle-best
candidate: the candidate whose posterior is closest to the next market price.
The remaining error is the generation gap.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_TEST_INPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv"
)
DEFAULT_TRAIN_INPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_train_all_batches_valid_ranking_candidates.csv"
)
DEFAULT_OUTPUT_DIR = Path("reports/explanation_pilot")
DEFAULT_PREFIX = "gemma4_26b_generation_gap_audit_20260629"

EPSILON = 1e-9


def parse_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["1", "true", "yes", "y"])


def sign_label(value: float) -> str:
    if not math.isfinite(value) or abs(value) <= EPSILON:
        return "flat"
    return "up" if value > 0 else "down"


def prep_frame(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = frame.copy()
    out["dataset"] = dataset
    numeric_columns = [
        "candidate_index",
        "num_candidates_for_prompt",
        "market_delta",
        "explanation_delta",
        "posterior",
        "posterior_error_to_market",
        "improvement_vs_persistence",
        "selected_evidence_count",
        "evidence_weights_count",
        "confidence",
    ]
    for column in numeric_columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce")
    for column in [
        "is_best_candidate",
        "is_recommended_candidate",
        "is_positive_improvement",
        "direction_match",
    ]:
        if column in out.columns:
            out[column] = parse_bool_series(out[column])
    out["prior"] = out["posterior"] - out["explanation_delta"]
    out["market_after"] = out["prior"] + out["market_delta"]
    out["abs_market_delta"] = out["market_delta"].abs()
    out["abs_explanation_delta"] = out["explanation_delta"].abs()
    out["candidate_direction"] = out["explanation_delta"].map(sign_label)
    out["market_direction"] = out["market_delta"].map(sign_label)
    out["market_move_bin"] = pd.cut(
        out["abs_market_delta"],
        bins=[-0.001, 0.0, 0.02, 0.05, 0.15, math.inf],
        labels=["zero", "tiny", "small", "medium", "large"],
        include_lowest=True,
    ).astype(str)
    return out


def bracket_status(candidate_min: float, candidate_max: float, target: float) -> str:
    if candidate_min - EPSILON <= target <= candidate_max + EPSILON:
        return "bracketed"
    if candidate_max < target:
        return "all_below_target"
    if candidate_min > target:
        return "all_above_target"
    return "unknown"


def magnitude_cover(group: pd.DataFrame, market_direction: str, market_after: float) -> bool:
    if market_direction == "up":
        return bool(group["posterior"].max() >= market_after - EPSILON)
    if market_direction == "down":
        return bool(group["posterior"].min() <= market_after + EPSILON)
    return bool(group["posterior"].min() <= market_after <= group["posterior"].max())


def classify_gap(row: dict[str, Any], near_threshold: float) -> str:
    if row["best_error"] <= near_threshold:
        return "near_hit"
    if row["market_direction"] == "flat":
        return "flat_target_missed"
    if not row["any_direction_match"]:
        return "no_right_direction_candidate"
    if row["bracket_status"] == "bracketed":
        return "bracketed_but_sparse"
    if row["market_direction"] == "up":
        if row["candidate_max_posterior"] < row["market_after"]:
            return "right_direction_under_update"
        if row["candidate_min_posterior"] > row["market_after"]:
            return "right_direction_over_update"
    if row["market_direction"] == "down":
        if row["candidate_min_posterior"] > row["market_after"]:
            return "right_direction_under_update"
        if row["candidate_max_posterior"] < row["market_after"]:
            return "right_direction_over_update"
    if not row["helpful_candidate_available"]:
        return "no_candidate_beats_persistence"
    return "other_outside_candidate_range"


def error_bin(error: float) -> str:
    if error <= 0.01:
        return "within_1pp"
    if error <= 0.02:
        return "within_2pp"
    if error <= 0.05:
        return "within_5pp"
    if error <= 0.10:
        return "within_10pp"
    if error <= 0.20:
        return "within_20pp"
    return "over_20pp"


def prompt_level(frame: pd.DataFrame, near_threshold: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for custom_id, group in frame.groupby("custom_id", sort=False):
        group = group.sort_values("candidate_index")
        best = group.sort_values(
            ["posterior_error_to_market", "candidate_index"],
            ascending=[True, True],
            na_position="last",
        ).iloc[0]
        prior = float(group["prior"].median())
        market_after = float(group["market_after"].median())
        market_delta = float(group["market_delta"].median())
        market_direction = sign_label(market_delta)
        persistence_error = abs(market_delta)
        best_error = float(best["posterior_error_to_market"])
        candidate_min = float(group["posterior"].min())
        candidate_max = float(group["posterior"].max())
        candidate_directions = sorted(set(group["candidate_direction"].astype(str)))
        any_direction_match = market_direction in set(candidate_directions)
        best_delta = float(best["explanation_delta"])
        best_direction_match = sign_label(best_delta) == market_direction
        best_delta_fraction = (
            abs(best_delta) / abs(market_delta)
            if best_direction_match and abs(market_delta) > EPSILON
            else math.nan
        )
        candidate_range_fraction = (
            (candidate_max - candidate_min) / abs(market_delta)
            if abs(market_delta) > EPSILON
            else math.nan
        )
        row = {
            "dataset": group["dataset"].iloc[0],
            "custom_id": custom_id,
            "pilot_row_id": group["pilot_row_id"].iloc[0],
            "category": group["category"].iloc[0],
            "candidate_count": int(len(group)),
            "prior": prior,
            "market_after": market_after,
            "market_delta": market_delta,
            "abs_market_delta": abs(market_delta),
            "market_direction": market_direction,
            "market_move_bin": group["market_move_bin"].iloc[0],
            "persistence_error": persistence_error,
            "best_candidate_id": best["explanation_id"],
            "best_candidate_index": int(best["candidate_index"]),
            "best_posterior": float(best["posterior"]),
            "best_delta": best_delta,
            "best_abs_delta": abs(best_delta),
            "best_delta_fraction_of_market_move": best_delta_fraction,
            "best_direction": sign_label(best_delta),
            "best_error": best_error,
            "best_error_bin": error_bin(best_error),
            "oracle_improvement_vs_persistence": persistence_error - best_error,
            "oracle_error_reduction_ratio": (persistence_error - best_error) / persistence_error
            if persistence_error > EPSILON
            else math.nan,
            "helpful_candidate_available": bool(group["is_positive_improvement"].any()),
            "best_beats_persistence": bool(best_error < persistence_error - EPSILON),
            "best_direction_match": best_direction_match,
            "any_direction_match": any_direction_match,
            "all_candidates_flat": set(candidate_directions) == {"flat"},
            "multi_direction_candidates": len(set(candidate_directions) - {"flat"}) > 1
            or ("flat" in candidate_directions and len(candidate_directions) > 1),
            "candidate_directions": "|".join(candidate_directions),
            "candidate_min_posterior": candidate_min,
            "candidate_max_posterior": candidate_max,
            "candidate_range": candidate_max - candidate_min,
            "candidate_range_fraction_of_market_move": candidate_range_fraction,
            "candidate_posterior_std": float(group["posterior"].std(ddof=0)),
            "candidate_posteriors": "|".join(f"{value:.4f}" for value in group["posterior"]),
            "candidate_deltas": "|".join(f"{value:.4f}" for value in group["explanation_delta"]),
            "bracket_status": bracket_status(candidate_min, candidate_max, market_after),
            "target_bracketed_by_candidate_range": candidate_min - EPSILON
            <= market_after
            <= candidate_max + EPSILON,
            "magnitude_cover": magnitude_cover(group, market_direction, market_after),
            "mean_selected_evidence_count": float(group["selected_evidence_count"].mean()),
            "max_selected_evidence_count": float(group["selected_evidence_count"].max()),
            "recommended_candidate_id": str(
                group[group["is_recommended_candidate"]]["explanation_id"].iloc[0]
            )
            if bool(group["is_recommended_candidate"].any())
            else "",
        }
        row["gap_type"] = classify_gap(row, near_threshold)
        rows.append(row)
    return pd.DataFrame(rows)


def safe_mean(series: pd.Series) -> float:
    return float(series.mean()) if len(series) else math.nan


def summarize(group: pd.DataFrame, *, dataset: str, stratum_type: str, stratum: str) -> dict[str, Any]:
    ratio = group["oracle_error_reduction_ratio"].replace([np.inf, -np.inf], np.nan)
    return {
        "dataset": dataset,
        "stratum_type": stratum_type,
        "stratum": stratum,
        "prompt_count": int(len(group)),
        "mean_persistence_error": safe_mean(group["persistence_error"]),
        "mean_best_error": safe_mean(group["best_error"]),
        "median_best_error": float(group["best_error"].median()) if len(group) else math.nan,
        "p75_best_error": float(group["best_error"].quantile(0.75)) if len(group) else math.nan,
        "mean_oracle_improvement": safe_mean(group["oracle_improvement_vs_persistence"]),
        "mean_oracle_error_reduction_ratio": float(ratio.mean(skipna=True)),
        "helpful_candidate_available_rate": safe_mean(group["helpful_candidate_available"]),
        "best_direction_match_rate": safe_mean(group["best_direction_match"]),
        "any_direction_match_rate": safe_mean(group["any_direction_match"]),
        "target_bracketed_rate": safe_mean(group["target_bracketed_by_candidate_range"]),
        "magnitude_cover_rate": safe_mean(group["magnitude_cover"]),
        "multi_direction_rate": safe_mean(group["multi_direction_candidates"]),
        "all_flat_rate": safe_mean(group["all_candidates_flat"]),
        "within_1pp_rate": safe_mean(group["best_error"].le(0.01)),
        "within_2pp_rate": safe_mean(group["best_error"].le(0.02)),
        "within_5pp_rate": safe_mean(group["best_error"].le(0.05)),
        "within_10pp_rate": safe_mean(group["best_error"].le(0.10)),
        "over_20pp_rate": safe_mean(group["best_error"].gt(0.20)),
        "mean_candidate_range": safe_mean(group["candidate_range"]),
        "median_candidate_range": float(group["candidate_range"].median()) if len(group) else math.nan,
        "mean_candidate_range_fraction_of_market_move": float(
            group["candidate_range_fraction_of_market_move"].replace([np.inf, -np.inf], np.nan).mean()
        ),
        "median_best_delta_fraction_of_market_move_when_direction_match": float(
            group.loc[
                group["best_direction_match"],
                "best_delta_fraction_of_market_move",
            ]
            .replace([np.inf, -np.inf], np.nan)
            .median()
        ),
    }


def aggregate(prompt_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, dataset_group in prompt_frame.groupby("dataset", sort=False):
        rows.append(summarize(dataset_group, dataset=dataset, stratum_type="overall", stratum="all"))
        for stratum_type, column in [
            ("category", "category"),
            ("market_direction", "market_direction"),
            ("market_move_bin", "market_move_bin"),
            ("gap_type", "gap_type"),
            ("best_error_bin", "best_error_bin"),
            ("bracket_status", "bracket_status"),
            ("candidate_count", "candidate_count"),
        ]:
            for value, group in dataset_group.groupby(column, sort=False):
                rows.append(
                    summarize(
                        group,
                        dataset=dataset,
                        stratum_type=stratum_type,
                        stratum=str(value),
                    )
                )
    return pd.DataFrame(rows)


def top_examples(prompt_frame: pd.DataFrame, n: int) -> pd.DataFrame:
    columns = [
        "dataset",
        "custom_id",
        "pilot_row_id",
        "category",
        "market_direction",
        "market_delta",
        "prior",
        "market_after",
        "best_candidate_id",
        "best_posterior",
        "best_delta",
        "best_error",
        "oracle_improvement_vs_persistence",
        "gap_type",
        "bracket_status",
        "candidate_posteriors",
        "candidate_deltas",
        "candidate_directions",
        "recommended_candidate_id",
    ]
    worst = prompt_frame.sort_values("best_error", ascending=False).head(n).copy()
    best = prompt_frame.sort_values("best_error", ascending=True).head(n).copy()
    worst.insert(0, "example_set", "largest_generation_gap")
    best.insert(0, "example_set", "smallest_generation_gap")
    return pd.concat([worst, best], ignore_index=True)[["example_set", *columns]]


def write_outputs(output_dir: Path, prefix: str, frames: dict[str, pd.DataFrame]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(output_dir / f"{prefix}_{name}.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-input", type=Path, default=DEFAULT_TEST_INPUT)
    parser.add_argument("--train-input", type=Path, default=DEFAULT_TRAIN_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--near-threshold", type=float, default=0.02)
    parser.add_argument("--example-count", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train = prep_frame(pd.read_csv(args.train_input), "train_all_batches")
    test = prep_frame(pd.read_csv(args.test_input), "heldout_test72")
    prompt_frame = pd.concat(
        [
            prompt_level(train, args.near_threshold),
            prompt_level(test, args.near_threshold),
        ],
        ignore_index=True,
    )
    aggregate_frame = aggregate(prompt_frame)
    examples = top_examples(prompt_frame[prompt_frame["dataset"].eq("heldout_test72")], args.example_count)
    summary = {
        "train_input": str(args.train_input),
        "test_input": str(args.test_input),
        "near_threshold": args.near_threshold,
        "train_prompt_count": int(prompt_frame["dataset"].eq("train_all_batches").sum()),
        "test_prompt_count": int(prompt_frame["dataset"].eq("heldout_test72").sum()),
        "outputs": {
            "prompt_level": str(args.output_dir / f"{args.prefix}_prompt_level.csv"),
            "aggregate": str(args.output_dir / f"{args.prefix}_aggregate.csv"),
            "examples": str(args.output_dir / f"{args.prefix}_examples.csv"),
        },
    }
    write_outputs(
        args.output_dir,
        args.prefix,
        {
            "prompt_level": prompt_frame,
            "aggregate": aggregate_frame,
            "examples": examples,
        },
    )
    (args.output_dir / f"{args.prefix}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    print()
    print(
        aggregate_frame[
            aggregate_frame["stratum_type"].eq("overall")
        ][
            [
                "dataset",
                "prompt_count",
                "mean_persistence_error",
                "mean_best_error",
                "mean_oracle_improvement",
                "helpful_candidate_available_rate",
                "within_5pp_rate",
                "over_20pp_rate",
                "target_bracketed_rate",
                "any_direction_match_rate",
            ]
        ].to_string(index=False)
    )
    print()
    print(
        aggregate_frame[
            aggregate_frame["dataset"].eq("heldout_test72")
            & aggregate_frame["stratum_type"].eq("gap_type")
        ][["stratum", "prompt_count", "mean_best_error", "within_5pp_rate"]]
        .sort_values("prompt_count", ascending=False)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
