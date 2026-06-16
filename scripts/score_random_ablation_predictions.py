#!/usr/bin/env python3
"""Score random-news ablation prediction outputs.

Expected inputs are JSONL files like the paper repo's
scripts/inference_multievent_world_model.py output, with fields:
market_id, t, pred_price, true_price, before_price, and optionally related_news.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def key(row: dict[str, Any]) -> tuple[str, Any]:
    return (str(row.get("market_id")), row.get("t"))


def price_fields(row: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(row["pred_price"]),
        float(row["true_price"]),
        float(row["before_price"]),
    )


def sign(value: float, tol: float = 1e-9) -> int:
    if value > tol:
        return 1
    if value < -tol:
        return -1
    return 0


def first_news_title(row: dict[str, Any]) -> str:
    for field in ("related_news", "random_news", "selected_news", "news"):
        items = row.get(field)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                return first.get("title") or ""
    return ""


def first_news_source(row: dict[str, Any]) -> str:
    for field in ("related_news", "random_news", "selected_news", "news"):
        items = row.get(field)
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                return first.get("source") or ""
    return ""


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": float("nan"), "median": float("nan")}
    ordered = sorted(values)
    return {
        "mean": sum(values) / len(values),
        "median": ordered[len(ordered) // 2],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score random-news ablation predictions.")
    parser.add_argument("--random-predictions", type=Path, required=True)
    parser.add_argument("--optimized-predictions", type=Path)
    parser.add_argument("--output-csv", type=Path, default=Path("data/random_news_hurt_cases.csv"))
    parser.add_argument("--top-n", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    random_rows = {key(row): row for row in read_jsonl(args.random_predictions)}
    optimized_rows = (
        {key(row): row for row in read_jsonl(args.optimized_predictions)}
        if args.optimized_predictions
        else {}
    )

    cases = []
    hurt_persist = []
    hurt_opt = []
    wrong_direction = 0
    improved_vs_persist = 0

    for row_key, random_row in random_rows.items():
        pred, true, before = price_fields(random_row)
        random_abs = abs(pred - true)
        persist_abs = abs(before - true)
        h_persist = random_abs - persist_abs
        hurt_persist.append(h_persist)
        if h_persist < 0:
            improved_vs_persist += 1

        true_delta = true - before
        pred_delta = pred - before
        if sign(true_delta) != 0 and sign(pred_delta) != sign(true_delta):
            wrong_direction += 1

        opt_abs = None
        h_opt = None
        if row_key in optimized_rows:
            opt_pred, opt_true, opt_before = price_fields(optimized_rows[row_key])
            if not math.isclose(opt_true, true) or not math.isclose(opt_before, before):
                raise ValueError(f"Mismatched true/before price for {row_key}")
            opt_abs = abs(opt_pred - true)
            h_opt = random_abs - opt_abs
            hurt_opt.append(h_opt)

        cases.append(
            {
                "market_id": random_row.get("market_id", ""),
                "t": random_row.get("t", ""),
                "question": random_row.get("question", ""),
                "before_price": before,
                "true_price": true,
                "random_pred_price": pred,
                "true_delta": true_delta,
                "random_pred_delta": pred_delta,
                "random_abs_error": random_abs,
                "persistence_abs_error": persist_abs,
                "hurt_vs_persistence": h_persist,
                "optimized_abs_error": opt_abs if opt_abs is not None else "",
                "hurt_vs_optimized": h_opt if h_opt is not None else "",
                "wrong_direction": int(sign(true_delta) != 0 and sign(pred_delta) != sign(true_delta)),
                "news_source": first_news_source(random_row),
                "news_title": first_news_title(random_row),
            }
        )

    cases.sort(
        key=lambda row: (
            float(row["hurt_vs_optimized"]) if row["hurt_vs_optimized"] != "" else float(row["hurt_vs_persistence"])
        ),
        reverse=True,
    )
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cases[0].keys()) if cases else [])
        if cases:
            writer.writeheader()
            writer.writerows(cases[: args.top_n])

    summary = {
        "n": len(cases),
        "random_improved_vs_persistence_rate": improved_vs_persist / len(cases) if cases else 0.0,
        "random_wrong_direction_rate": wrong_direction / len(cases) if cases else 0.0,
        "hurt_vs_persistence": summarize(hurt_persist),
        "hurt_vs_optimized": summarize(hurt_opt),
        "output_csv": str(args.output_csv),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
