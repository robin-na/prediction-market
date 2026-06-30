#!/usr/bin/env python3
"""Build a candidate-level ranking dataset from explanation score CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path(
    "data/derived/explanation_pilot/ranking/"
    "gemma4_26b_grounded_nonnull_72_ranking_candidates.csv"
)

CLASS_LABELS = [
    "source_credibility",
    "base_rate_calibration",
    "resolution_rule",
    "causal_chain",
    "direct_resolution",
    "trend_continuation",
    "overreaction_correction",
    "underreaction_correction",
    "evidence_irrelevance",
    "market_microstructure",
    "other",
]

MAGNITUDES = ["none", "small", "moderate", "large"]


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def read_csvs(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows.extend(dict(row) for row in reader)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def class_set(row: dict[str, str]) -> set[str]:
    return {item for item in row.get("explanation_classes", "").split("|") if item}


def rank_rows(rows: list[dict[str, str]], *, valid_only: bool) -> list[dict[str, Any]]:
    if valid_only:
        rows = [row for row in rows if parse_bool(row.get("schema_valid", "true"))]

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get("custom_id", "")].append(row)

    ranked: list[dict[str, Any]] = []
    for custom_id, group in groups.items():
        if not custom_id or not group:
            continue
        sorted_group = sorted(
            group,
            key=lambda row: (
                parse_float(row.get("posterior_error_to_market")),
                parse_float(row.get("candidate_index")),
            ),
        )
        recommended_id = group[0].get("ensemble_recommended_explanation_id", "")
        for rank, row in enumerate(sorted_group, start=1):
            posterior_error = parse_float(row.get("posterior_error_to_market"))
            classes = class_set(row)
            magnitude = row.get("magnitude", "")
            out: dict[str, Any] = {
                "custom_id": custom_id,
                "pilot_row_id": row.get("pilot_row_id", ""),
                "category": row.get("category", ""),
                "generation_mode": row.get("generation_mode", ""),
                "explanation_id": row.get("explanation_id", ""),
                "candidate_index": row.get("candidate_index", ""),
                "candidate_rank_by_market_error": rank,
                "num_candidates_for_prompt": len(group),
                "is_best_candidate": rank == 1,
                "is_recommended_candidate": row.get("explanation_id", "") == recommended_id,
                "is_positive_improvement": parse_float(row.get("improvement_vs_persistence")) > 0,
                "schema_valid": parse_bool(row.get("schema_valid", "true")),
                "market_delta": parse_float(row.get("market_delta")),
                "explanation_delta": parse_float(row.get("explanation_delta")),
                "posterior": parse_float(row.get("posterior")),
                "posterior_error_to_market": posterior_error,
                "improvement_vs_persistence": parse_float(row.get("improvement_vs_persistence")),
                "delta_error": parse_float(row.get("delta_error")),
                "direction_match": parse_bool(row.get("direction_match")),
                "selected_evidence_count": parse_float(row.get("selected_evidence_count")),
                "evidence_weights_count": parse_float(row.get("evidence_weights_count")),
                "confidence": parse_float(row.get("confidence")),
                "has_evidence_irrelevance": parse_bool(row.get("has_evidence_irrelevance")),
                "selected_with_irrelevance": parse_bool(row.get("selected_with_irrelevance")),
                "top_posterior_selected": parse_bool(row.get("top_posterior_selected")),
                "top_prior_selected": parse_bool(row.get("top_prior_selected")),
                "posterior_top_k_selected": parse_bool(row.get("posterior_top_k_selected")),
                "prior_top_k_selected": parse_bool(row.get("prior_top_k_selected")),
                "random_candidate_selected": parse_bool(row.get("random_candidate_selected")),
                "magnitude": magnitude,
            }
            for label in CLASS_LABELS:
                out[f"class_{label}"] = label in classes
            for label in MAGNITUDES:
                out[f"magnitude_{label}"] = magnitude == label
            ranked.append(out)
    return ranked


def summarize(rows: list[dict[str, Any]], raw_rows: list[dict[str, str]], valid_only: bool) -> dict[str, Any]:
    prompts = {row["custom_id"] for row in rows}
    best_rows = [row for row in rows if row["is_best_candidate"]]
    recommended_rows = [row for row in rows if row["is_recommended_candidate"]]
    class_counts = Counter()
    for row in rows:
        for label in CLASS_LABELS:
            if row[f"class_{label}"]:
                class_counts[label] += 1
    schema_valid_rows = [row for row in raw_rows if parse_bool(row.get("schema_valid", "true"))]
    return {
        "input_score_rows": len(raw_rows),
        "schema_valid_input_rows": len(schema_valid_rows),
        "valid_only": valid_only,
        "ranking_rows": len(rows),
        "prompt_count": len(prompts),
        "best_rows": len(best_rows),
        "recommended_rows": len(recommended_rows),
        "recommended_is_best_rate": (
            sum(row["is_best_candidate"] for row in recommended_rows) / len(recommended_rows)
            if recommended_rows
            else None
        ),
        "positive_improvement_rate": (
            sum(row["is_positive_improvement"] for row in rows) / len(rows) if rows else None
        ),
        "best_positive_improvement_rate": (
            sum(row["is_positive_improvement"] for row in best_rows) / len(best_rows)
            if best_rows
            else None
        ),
        "class_counts": dict(class_counts),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=None)
    parser.add_argument(
        "--valid-only",
        action="store_true",
        help="Drop candidates that fail parser-level schema validation.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csvs(args.scores)
    ranked = rank_rows(rows, valid_only=args.valid_only)
    fieldnames = list(ranked[0].keys()) if ranked else []
    write_csv(args.output, ranked, fieldnames)
    summary = summarize(ranked, rows, args.valid_only)
    summary_output = args.summary_output or args.output.with_suffix(args.output.suffix + ".summary.json")
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({**summary, "output": str(args.output)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
