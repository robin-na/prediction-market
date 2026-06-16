#!/usr/bin/env python3
"""Audit random-news selection against SWM-Bench posterior attributions.

The paper's random event-set ablation needs trained world-model predictions to
measure actual forecast harm. The public release includes the data and posterior
attributions, but not the random-ablation prediction outputs or model
checkpoints. This script computes the strongest directly-released proxy:
how much posterior attribution mass a random selector captures or misses.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.request import urlopen


HF_BASE = "https://huggingface.co/datasets/ulab-ai/swm-bench/resolve/main"
DEFAULT_DATASET = f"{HF_BASE}/Qwen3.5-397B-attributed-data/test_kalshi.jsonl"
DEFAULT_OUTPUT_DIR = Path("data/random_news_hurt_proxy")


def open_jsonl(path_or_url: str):
    if path_or_url.startswith(("http://", "https://")):
        with urlopen(path_or_url, timeout=180) as response:
            for raw in response:
                if raw.strip():
                    yield json.loads(raw)
        return

    with Path(path_or_url).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def posterior_pi(scores: dict[int, float], eps: float, rho0: float) -> dict[int, float]:
    odds: dict[int, float] = {}
    for idx, score in scores.items():
        if score <= 0:
            continue
        capped = min(score, 1.0 - eps)
        odds[idx] = (capped + eps) / (1.0 - capped + eps)
    denom = rho0 + sum(odds.values())
    if denom <= 0:
        return {}
    return {idx: odd / denom for idx, odd in odds.items()}


def score_map(record: dict[str, Any]) -> dict[int, float]:
    news_count = len(record.get("news") or [])
    scores: dict[int, float] = {}
    for attr in record.get("attributions") or []:
        idx = attr.get("news_idx")
        if isinstance(idx, int) and 0 <= idx < news_count:
            scores[idx] = float(attr.get("score") or 0.0)
    return scores


def source_of(record: dict[str, Any], idx: int) -> str:
    news = record.get("news") or []
    if not 0 <= idx < len(news):
        return "Unknown"
    return (news[idx].get("source") or "Unknown").strip() or "Unknown"


def title_of(record: dict[str, Any], idx: int) -> str:
    news = record.get("news") or []
    if not 0 <= idx < len(news):
        return ""
    return news[idx].get("title") or ""


def category_of(record: dict[str, Any]) -> str:
    categories = record.get("categories") or []
    return "|".join(categories) if categories else "Unknown"


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[idx]


def simulate(records: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    rng = random.Random(args.seed)
    set_sizes = [int(x) for x in args.set_sizes.split(",") if x]
    trials = args.trials
    eps = args.odds_eps
    rho0 = args.null_rho0

    rows = []
    source_misses = Counter()
    category_misses = Counter()
    source_selected = Counter()
    source_high = Counter()
    attr_records = 0
    high_records = 0
    all_records_with_news = 0
    top1_zero_misses = 0
    top1_nonzero_hits = 0
    top1_nonzero_hits_positive = 0
    top1_exact_hits = 0
    top1_exact_hits_high = 0
    top1_random_scores = []
    top1_top_scores = []
    top1_random_pi = []
    top1_total_pi = []

    recall_by_m = defaultdict(list)
    recall_positive_by_m = defaultdict(list)
    top_recall_by_m = defaultdict(list)
    top_recall_positive_by_m = defaultdict(list)

    for record in records:
        news = record.get("news") or []
        if not news:
            continue
        all_records_with_news += 1
        scores = score_map(record)
        positive = {idx: score for idx, score in scores.items() if score > 0}
        pi = posterior_pi(scores, eps, rho0)
        total_pi = sum(pi.values())
        if positive:
            attr_records += 1
        top_idx = max(scores, key=lambda idx: scores[idx]) if scores else None
        top_score = scores.get(top_idx, 0.0) if top_idx is not None else 0.0
        top_pi = pi.get(top_idx, 0.0) if top_idx is not None else 0.0
        if top_score >= args.high_threshold:
            high_records += 1
        top1_top_scores.append(top_score)
        top1_total_pi.append(total_pi)

        shuffled = list(range(len(news)))
        rng.shuffle(shuffled)
        random_idx = shuffled[0]
        random_score = scores.get(random_idx, 0.0)
        random_pi = pi.get(random_idx, 0.0)
        random_source = source_of(record, random_idx)
        source_selected[random_source] += 1
        top1_random_scores.append(random_score)
        top1_random_pi.append(random_pi)

        if random_score > 0:
            top1_nonzero_hits += 1
            if positive:
                top1_nonzero_hits_positive += 1
        if top_idx is not None and random_idx == top_idx:
            top1_exact_hits += 1
            if top_score >= args.high_threshold:
                top1_exact_hits_high += 1
        if random_score >= args.high_threshold:
            source_high[random_source] += 1
        if top_score >= args.high_threshold and random_score == 0:
            top1_zero_misses += 1
            source_misses[random_source] += 1
            category_misses[category_of(record)] += 1
            rows.append(
                {
                    "market_id": record.get("market_id", ""),
                    "event_id": record.get("event_id", ""),
                    "category": category_of(record),
                    "question": record.get("question", ""),
                    "before_price": (record.get("history") or [{}])[-1].get("p", ""),
                    "target_price": (record.get("target") or {}).get("p", ""),
                    "top_source": source_of(record, top_idx) if top_idx is not None else "",
                    "top_score": f"{top_score:.4f}",
                    "top_pi": f"{top_pi:.4f}",
                    "top_title": title_of(record, top_idx) if top_idx is not None else "",
                    "random_source": random_source,
                    "random_score": f"{random_score:.4f}",
                    "random_pi": f"{random_pi:.4f}",
                    "random_title": title_of(record, random_idx),
                }
            )

        for m in set_sizes:
            top_selection = sorted(scores, key=lambda idx: scores[idx], reverse=True)[:m]
            top_mass = sum(pi.get(idx, 0.0) for idx in top_selection)
            top_recall = top_mass / total_pi if total_pi > 0 else 1.0
            top_recall_by_m[m].append(top_recall)
            if total_pi > 0:
                top_recall_positive_by_m[m].append(top_recall)

            # Average random recall across trials for this record/set size.
            if len(news) <= m:
                random_recall = 1.0
            else:
                recalls = []
                universe = list(range(len(news)))
                for _ in range(trials):
                    selected = rng.sample(universe, m)
                    mass = sum(pi.get(idx, 0.0) for idx in selected)
                    recalls.append(mass / total_pi if total_pi > 0 else 1.0)
                random_recall = mean(recalls)
            recall_by_m[m].append(random_recall)
            if total_pi > 0:
                recall_positive_by_m[m].append(random_recall)

    summary = {
        "dataset": args.dataset,
        "records": len(records),
        "records_with_news": all_records_with_news,
        "records_with_positive_posterior": attr_records,
        "records_with_top_score_ge_threshold": high_records,
        "high_threshold": args.high_threshold,
        "random_top1_nonzero_hit_rate": top1_nonzero_hits / all_records_with_news,
        "random_top1_nonzero_hit_rate_given_positive": (
            top1_nonzero_hits_positive / attr_records if attr_records else 0.0
        ),
        "random_top1_exact_top_hit_rate": top1_exact_hits / all_records_with_news,
        "random_top1_exact_top_hit_rate_given_high": (
            top1_exact_hits_high / high_records if high_records else 0.0
        ),
        "random_top1_zero_miss_given_high_count": top1_zero_misses,
        "random_top1_zero_miss_given_high_rate": (
            top1_zero_misses / high_records if high_records else 0.0
        ),
        "mean_top_score": mean(top1_top_scores),
        "mean_random_score": mean(top1_random_scores),
        "mean_total_nonnull_pi": mean(top1_total_pi),
        "mean_random_pi": mean(top1_random_pi),
        "set_size_recall": {
            str(m): {
                "random_mean": mean(recall_by_m[m]),
                "random_p10": percentile(recall_by_m[m], 0.10),
                "random_p50": percentile(recall_by_m[m], 0.50),
                "top_mean": mean(top_recall_by_m[m]),
                "top_p50": percentile(top_recall_by_m[m], 0.50),
            }
            for m in set_sizes
        },
        "set_size_recall_positive_only": {
            str(m): {
                "random_mean": mean(recall_positive_by_m[m]),
                "random_p10": percentile(recall_positive_by_m[m], 0.10),
                "random_p50": percentile(recall_positive_by_m[m], 0.50),
                "top_mean": mean(top_recall_positive_by_m[m]),
                "top_p50": percentile(top_recall_positive_by_m[m], 0.50),
            }
            for m in set_sizes
        },
        "top_random_zero_miss_sources": source_misses.most_common(20),
        "top_random_zero_miss_categories": category_misses.most_common(20),
        "top_random_selected_sources": source_selected.most_common(20),
        "top_random_high_sources": source_high.most_common(20),
    }
    rows.sort(key=lambda row: float(row["top_score"]), reverse=True)
    return {"summary": summary, "miss_rows": rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Proxy audit for random-news selection using released posterior attributions."
    )
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--set-sizes", default="1,5,10,20,30")
    parser.add_argument("--high-threshold", type=float, default=0.5)
    parser.add_argument("--odds-eps", type=float, default=1e-3)
    parser.add_argument("--null-rho0", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = list(open_jsonl(args.dataset))
    result = simulate(records, args)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "summary.json"
    misses_path = args.output_dir / "random_top1_zero_misses.csv"

    summary_path.write_text(json.dumps(result["summary"], indent=2) + "\n", encoding="utf-8")
    fieldnames = [
        "market_id",
        "event_id",
        "category",
        "question",
        "before_price",
        "target_price",
        "top_source",
        "top_score",
        "top_pi",
        "top_title",
        "random_source",
        "random_score",
        "random_pi",
        "random_title",
    ]
    with misses_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result["miss_rows"])

    print(json.dumps(result["summary"], indent=2))
    print(f"Wrote {summary_path}", file=sys.stderr)
    print(f"Wrote {misses_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
