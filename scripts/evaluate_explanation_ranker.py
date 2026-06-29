#!/usr/bin/env python3
"""Evaluate simple rankers for selecting the best generated explanation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_INPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_72_valid_ranking_candidates.csv"
)
DEFAULT_OUTPUT = Path(
    "reports/explanation_pilot/"
    "gemma4_26b_grounded_nonnull_72_ranker_eval_20260629.json"
)

DEPLOYABLE_FEATURES = [
    "posterior",
    "explanation_delta",
    "selected_evidence_count",
    "evidence_weights_count",
    "confidence",
    "has_evidence_irrelevance",
    "selected_with_irrelevance",
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
    "magnitude_none",
    "magnitude_small",
    "magnitude_moderate",
    "magnitude_large",
]

DIAGNOSTIC_EXTRA_FEATURES = [
    "top_prior_selected",
    "prior_top_k_selected",
    "random_candidate_selected",
    # These are oracle-ish SWM metadata, not deployable features.
    "top_posterior_selected",
    "posterior_top_k_selected",
]


RELATIVE_BASE_COLUMNS = [
    "confidence",
    "posterior",
    "explanation_delta",
    "selected_evidence_count",
    "evidence_weights_count",
]


def booleanize(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for column in out.columns:
        if out[column].dtype == bool:
            out[column] = out[column].astype(int)
        elif out[column].dtype == object:
            lowered = out[column].astype(str).str.lower()
            if lowered.isin(["true", "false"]).all():
                out[column] = lowered.eq("true").astype(int)
    return out


def add_prompt_relative_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["abs_explanation_delta"] = out["explanation_delta"].abs()
    out["abs_posterior_minus_0_5"] = (out["posterior"] - 0.5).abs()
    relative_columns = [
        column for column in RELATIVE_BASE_COLUMNS + ["abs_explanation_delta"] if column in out.columns
    ]
    for column in relative_columns:
        group = out.groupby("custom_id")[column]
        out[f"{column}_rank_desc"] = group.rank(method="average", ascending=False)
        out[f"{column}_rank_asc"] = group.rank(method="average", ascending=True)
        mean = group.transform("mean")
        std = group.transform("std").replace(0, np.nan)
        out[f"{column}_rel_mean"] = out[column] - mean
        out[f"{column}_z"] = ((out[column] - mean) / std).replace([np.inf, -np.inf], np.nan).fillna(0)
    return out


def relative_feature_names(frame: pd.DataFrame) -> list[str]:
    features = ["abs_explanation_delta", "abs_posterior_minus_0_5"]
    relative_columns = [
        column for column in RELATIVE_BASE_COLUMNS + ["abs_explanation_delta"] if column in frame.columns
    ]
    for column in relative_columns:
        features.extend(
            [
                f"{column}_rank_desc",
                f"{column}_rank_asc",
                f"{column}_rel_mean",
                f"{column}_z",
            ]
        )
    return [feature for feature in features if feature in frame.columns]


def make_model(model_name: str):
    if model_name == "logit":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=3000, class_weight="balanced"),
        )
    if model_name == "random_forest":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(
                n_estimators=300,
                min_samples_leaf=4,
                class_weight="balanced_subsample",
                random_state=0,
            ),
        )
    if model_name == "extra_trees":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesClassifier(
                n_estimators=400,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=0,
            ),
        )
    if model_name == "hist_gradient_boosting":
        return make_pipeline(
            SimpleImputer(strategy="median"),
            HistGradientBoostingClassifier(
                max_iter=200,
                learning_rate=0.04,
                l2_regularization=0.1,
                random_state=0,
            ),
        )
    raise ValueError(f"unknown model: {model_name}")


def group_top1_rate(frame: pd.DataFrame, score_column: str) -> float:
    hits = []
    for _, group in frame.groupby("custom_id"):
        top = group.sort_values(score_column, ascending=False).iloc[0]
        hits.append(bool(top["is_best_candidate"]))
    return float(np.mean(hits)) if hits else float("nan")


def recommended_top1_rate(frame: pd.DataFrame) -> float:
    hits = []
    for _, group in frame.groupby("custom_id"):
        recommended = group[group["is_recommended_candidate"].astype(bool)]
        if recommended.empty:
            continue
        hits.append(bool(recommended.iloc[0]["is_best_candidate"]))
    return float(np.mean(hits)) if hits else float("nan")


def random_top1_rate(frame: pd.DataFrame) -> float:
    rates = []
    for _, group in frame.groupby("custom_id"):
        rates.append(1.0 / len(group))
    return float(np.mean(rates)) if rates else float("nan")


def evaluate(
    frame: pd.DataFrame,
    features: list[str],
    n_splits: int,
    *,
    model_name: str,
) -> dict[str, float | int]:
    frame = frame.copy()
    frame["is_best_candidate"] = frame["is_best_candidate"].astype(bool)
    groups = frame["custom_id"].astype(str)
    y = frame["is_best_candidate"].astype(int).to_numpy()
    x = booleanize(frame[features]).apply(pd.to_numeric, errors="coerce")

    unique_groups = groups.nunique()
    splits = min(n_splits, unique_groups)
    if splits < 2:
        raise ValueError("need at least two prompt groups for group cross-validation")

    predictions = np.full(len(frame), np.nan)
    splitter = GroupKFold(n_splits=splits)
    for train_idx, test_idx in splitter.split(x, y, groups):
        model = make_model(model_name)
        model.fit(x.iloc[train_idx], y[train_idx])
        predictions[test_idx] = model.predict_proba(x.iloc[test_idx])[:, 1]

    evaluated = frame.copy()
    evaluated["ranker_score"] = predictions
    auc = roc_auc_score(y, predictions) if len(set(y)) > 1 else float("nan")
    ap = average_precision_score(y, predictions) if len(set(y)) > 1 else float("nan")
    return {
        "rows": int(len(frame)),
        "prompt_count": int(unique_groups),
        "n_splits": int(splits),
        "evaluation_mode": "group_cv",
        "model": model_name,
        "positive_rate": float(np.mean(y)),
        "ranker_top1_rate": group_top1_rate(evaluated, "ranker_score"),
        "recommended_top1_rate": recommended_top1_rate(frame),
        "random_top1_rate": random_top1_rate(frame),
        "confidence_top1_rate": group_top1_rate(frame, "confidence"),
        "roc_auc": float(auc),
        "average_precision": float(ap),
    }


def evaluate_external(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    features: list[str],
    *,
    model_name: str,
) -> dict[str, float | int]:
    train_frame = train_frame.copy()
    test_frame = test_frame.copy()
    train_frame["is_best_candidate"] = train_frame["is_best_candidate"].astype(bool)
    test_frame["is_best_candidate"] = test_frame["is_best_candidate"].astype(bool)
    y_train = train_frame["is_best_candidate"].astype(int).to_numpy()
    y_test = test_frame["is_best_candidate"].astype(int).to_numpy()
    x_train = booleanize(train_frame[features]).apply(pd.to_numeric, errors="coerce")
    x_test = booleanize(test_frame[features]).apply(pd.to_numeric, errors="coerce")

    model = make_model(model_name)
    model.fit(x_train, y_train)
    evaluated = test_frame.copy()
    evaluated["ranker_score"] = model.predict_proba(x_test)[:, 1]
    auc = roc_auc_score(y_test, evaluated["ranker_score"]) if len(set(y_test)) > 1 else float("nan")
    ap = (
        average_precision_score(y_test, evaluated["ranker_score"])
        if len(set(y_test)) > 1
        else float("nan")
    )
    return {
        "evaluation_mode": "train_test",
        "model": model_name,
        "train_rows": int(len(train_frame)),
        "train_prompt_count": int(train_frame["custom_id"].nunique()),
        "test_rows": int(len(test_frame)),
        "test_prompt_count": int(test_frame["custom_id"].nunique()),
        "train_positive_rate": float(np.mean(y_train)),
        "test_positive_rate": float(np.mean(y_test)),
        "ranker_top1_rate": group_top1_rate(evaluated, "ranker_score"),
        "recommended_top1_rate": recommended_top1_rate(test_frame),
        "random_top1_rate": random_top1_rate(test_frame),
        "confidence_top1_rate": group_top1_rate(test_frame, "confidence"),
        "roc_auc": float(auc),
        "average_precision": float(ap),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--train-input", type=Path, default=None)
    parser.add_argument("--test-input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--feature-set",
        choices=["deployable", "deployable_relative", "diagnostic", "diagnostic_relative"],
        default="deployable",
    )
    parser.add_argument(
        "--model",
        choices=["logit", "random_forest", "extra_trees", "hist_gradient_boosting"],
        default="logit",
    )
    parser.add_argument("--n-splits", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if bool(args.train_input) != bool(args.test_input):
        raise ValueError("--train-input and --test-input must be provided together")
    frame = pd.read_csv(args.input) if not args.train_input else pd.read_csv(args.train_input)
    if "relative" in args.feature_set:
        frame = add_prompt_relative_features(frame)
    features = [feature for feature in DEPLOYABLE_FEATURES if feature in frame.columns]
    if "relative" in args.feature_set:
        features += relative_feature_names(frame)
    if args.feature_set.startswith("diagnostic"):
        features += [feature for feature in DIAGNOSTIC_EXTRA_FEATURES if feature in frame.columns]
    if args.train_input and args.test_input:
        test_frame = pd.read_csv(args.test_input)
        if "relative" in args.feature_set:
            test_frame = add_prompt_relative_features(test_frame)
        missing = [feature for feature in features if feature not in test_frame.columns]
        if missing:
            raise ValueError(f"test input is missing features: {missing}")
        result = evaluate_external(frame, test_frame, features, model_name=args.model)
        result["train_input"] = str(args.train_input)
        result["test_input"] = str(args.test_input)
    else:
        result = evaluate(frame, features, args.n_splits, model_name=args.model)
        result["input"] = str(args.input)
    result["feature_set"] = args.feature_set
    result["features"] = features
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
