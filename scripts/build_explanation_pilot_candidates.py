#!/usr/bin/env python3
"""Build a no-LLM explanation-pilot candidate set from SWM Kalshi data.

The output is meant for the first "market for explanations" pilot. It pairs the
released raw Kalshi posterior-attributed and prior-attributed SWM files, samples
an inspectable 100-row panel, and selects a small set of candidate news items per
row for later explanation generation or manual review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RAW_DIR = Path("data/swm-bench/raw/kalshi/splitted_v2_0102")
DEFAULT_POSTERIOR_TEST = (
    DEFAULT_RAW_DIR / "kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl"
)
DEFAULT_PRIOR_TEST = DEFAULT_RAW_DIR / "kalshi_prior_attributed_test_2025-11-01.jsonl"
DEFAULT_OUT_DIR = Path("data/derived/explanation_pilot")
DEFAULT_REPORT_DIR = Path("reports/explanation_pilot")

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "into",
    "is",
    "it",
    "more",
    "no",
    "not",
    "of",
    "on",
    "or",
    "than",
    "that",
    "the",
    "there",
    "this",
    "to",
    "will",
    "with",
    "yes",
}

GROUNDED_INCLUDE_PATTERNS: dict[str, re.Pattern[str]] = {
    "election_result": re.compile(
        r"\b(election|elected|mayor|president|governor|senate|house|primary|"
        r"nominee|nomination|vote share|margin of victory|polling average)\b",
        re.I,
    ),
    "official_political_process": re.compile(
        r"\b(vote|bill|spending bill|omnibus|minibus|government shutdown|"
        r"confirmation|impeached|supreme court|congress|senate|house|tariff|"
        r"sanction|ceasefire|treaty)\b",
        re.I,
    ),
    "economic_release": re.compile(
        r"\b(cpi|inflation|unemployment|jobs report|gdp|fed|fomc|interest rate|"
        r"rate cut|rate hike|treasury|recession)\b",
        re.I,
    ),
    "company_scheduled_disclosure": re.compile(
        r"\b(earnings call|earnings|revenue|eps|guidance|profit|sales|stock price|"
        r"market cap|ipo)\b",
        re.I,
    ),
    "legal_regulatory": re.compile(
        r"\b(court|judge|trial|lawsuit|settlement|regulat|sec|fda|approval|ban|"
        r"permit|license)\b",
        re.I,
    ),
}

GROUNDED_EXCLUDE_PATTERNS: dict[str, re.Pattern[str]] = {
    "attention_mentions": re.compile(
        r"\b(say|says|mention|tweet|post|truth|quote|word|phrase|crooked hillary|"
        r"press briefing)\b",
        re.I,
    ),
    "popularity_attention": re.compile(
        r"\b(wikipedia|most popular|person of the year|year in search|box office|"
        r"trailer|google trends)\b",
        re.I,
    ),
    "awards_entertainment": re.compile(
        r"\b(oscar|golden globe|grammy|emmy|award|nominee|nomination|best actor|"
        r"best director|best picture|best television)\b",
        re.I,
    ),
    "sports_or_game": re.compile(
        r"\b(nba|nfl|mlb|nhl|ufc|world cup|game|match|playoff|champion|"
        r"tournament)\b",
        re.I,
    ),
}

GROUNDED_ALLOWED_CATEGORIES = {
    "Politics",
    "Elections",
    "Economics",
    "Companies",
    "Financials",
    "World",
    "Health",
    "Science and Technology",
}

GROUNDED_EXCLUDED_CATEGORIES = {
    "Crypto",
    "Entertainment",
    "Mentions",
    "Social",
    "Sports",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def score_map(record: dict[str, Any]) -> dict[int, float]:
    out: dict[int, float] = {}
    for attr in record.get("attributions") or []:
        idx = attr.get("news_idx")
        if isinstance(idx, int):
            out[idx] = float(attr.get("score") or 0.0)
    return out


def category_of(record: dict[str, Any]) -> str:
    categories = record.get("categories")
    if isinstance(categories, list) and categories:
        return "|".join(str(cat) for cat in categories)
    category = record.get("category")
    if isinstance(category, list) and category:
        return "|".join(str(cat) for cat in category)
    return str(category or "Unknown")


def price_delta(record: dict[str, Any]) -> float:
    change = record.get("change")
    if isinstance(change, (int, float)):
        return float(change)
    before = record.get("before") or {}
    after = record.get("after") or {}
    if isinstance(before, dict) and isinstance(after, dict):
        if "p" in before and "p" in after:
            return float(after["p"]) - float(before["p"])
    return math.nan


def sign_label(x: float, tol: float = 1e-9) -> str:
    if not math.isfinite(x) or abs(x) <= tol:
        return "flat"
    return "up" if x > 0 else "down"


def parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None
    return None


def recency_hours(news: dict[str, Any], after: dict[str, Any]) -> float | None:
    news_time = parse_time(news.get("published_at") or news.get("date"))
    after_time = parse_time(after.get("t") if isinstance(after, dict) else None)
    if not news_time or not after_time:
        return None
    return (after_time - news_time).total_seconds() / 3600.0


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def lexical_overlap(question: str, news: dict[str, Any]) -> float:
    q_tokens = tokenize(question)
    n_tokens = tokenize(
        " ".join(
            str(news.get(key) or "")
            for key in ("title", "description", "source", "url")
        )
    )
    if not q_tokens or not n_tokens:
        return 0.0
    return len(q_tokens & n_tokens) / len(q_tokens)


def market_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(key) or "") for key in ("question", "description", "rules")
    )


def market_grounding(record: dict[str, Any]) -> dict[str, Any]:
    """Classify whether a market is suitable for the grounded-evidence pilot."""

    category = category_of(record)
    text = market_text(record)
    include_reasons = [
        name for name, pattern in GROUNDED_INCLUDE_PATTERNS.items() if pattern.search(text)
    ]
    raw_exclusions = [
        name for name, pattern in GROUNDED_EXCLUDE_PATTERNS.items() if pattern.search(text)
    ]

    exclusion_reasons = list(raw_exclusions)
    if category in GROUNDED_EXCLUDED_CATEGORIES:
        exclusion_reasons.append(f"excluded_category:{category}")
    if category not in GROUNDED_ALLOWED_CATEGORIES:
        exclusion_reasons.append(f"not_allowed_category:{category}")

    # Earnings-call markets use "say" language, but the relevant event is a
    # scheduled company disclosure rather than an open-ended attention/mentions market.
    if "company_scheduled_disclosure" in include_reasons and "attention_mentions" in exclusion_reasons:
        exclusion_reasons.remove("attention_mentions")

    is_grounded = bool(include_reasons) and not exclusion_reasons
    return {
        "is_grounded_market": is_grounded,
        "grounding_reasons": include_reasons,
        "grounding_exclusion_reasons": exclusion_reasons,
    }


def rank_map(scores: dict[int, float]) -> dict[int, int]:
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return {idx: rank + 1 for rank, (idx, _) in enumerate(ranked)}


def paired_rows(posterior_path: Path, prior_path: Path) -> list[dict[str, Any]]:
    posterior_rows = read_jsonl(posterior_path)
    prior_rows = read_jsonl(prior_path)
    if len(posterior_rows) != len(prior_rows):
        raise ValueError(
            f"prior/posterior row mismatch: {len(prior_rows)} != {len(posterior_rows)}"
        )

    rows: list[dict[str, Any]] = []
    for row_idx, (posterior, prior) in enumerate(zip(posterior_rows, prior_rows)):
        posterior_key = (
            posterior.get("market_id"),
            posterior.get("event_id"),
            posterior.get("question"),
        )
        prior_key = (prior.get("market_id"), prior.get("event_id"), prior.get("question"))
        if posterior_key != prior_key:
            raise ValueError(f"row {row_idx} key mismatch: {posterior_key} != {prior_key}")
        if len(posterior.get("news") or []) != len(prior.get("news") or []):
            raise ValueError(f"row {row_idx} news length mismatch")

        post_scores = score_map(posterior)
        prior_scores = score_map(prior)
        news = posterior.get("news") or []
        delta = price_delta(posterior)
        grounding = market_grounding(posterior)
        rows.append(
            {
                "row_idx": row_idx,
                "posterior": posterior,
                "prior": prior,
                "post_scores": post_scores,
                "prior_scores": prior_scores,
                "news_count": len(news),
                "max_posterior_score": max(post_scores.values()) if post_scores else 0.0,
                "max_prior_score": max(prior_scores.values()) if prior_scores else 0.0,
                "positive_posterior": any(score > 0 for score in post_scores.values()),
                "price_delta": delta,
                "abs_delta": abs(delta) if math.isfinite(delta) else math.nan,
                "category": category_of(posterior),
                "sample_type": str(posterior.get("sample_type") or ""),
                **grounding,
            }
        )
    return rows


def filter_rows_by_market(rows: list[dict[str, Any]], market_filter: str) -> list[dict[str, Any]]:
    if market_filter == "all":
        return rows
    if market_filter == "grounded":
        return [row for row in rows if row.get("is_grounded_market")]
    raise ValueError(f"unknown market filter: {market_filter}")


def select_with_cap(rows: list[dict[str, Any]], n: int, category_cap: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    by_category: Counter[str] = Counter()
    for row in rows:
        category = row["category"]
        if by_category[category] >= category_cap:
            continue
        selected.append(row)
        by_category[category] += 1
        if len(selected) >= n:
            return selected

    seen = {row["row_idx"] for row in selected}
    for row in rows:
        if row["row_idx"] not in seen:
            selected.append(row)
            if len(selected) >= n:
                break
    return selected


def assign_bucket(row: dict[str, Any], bucket: str) -> dict[str, Any]:
    out = dict(row)
    out["row_bucket"] = bucket
    return out


def build_row_sample(rows: list[dict[str, Any]], sample_mode: str) -> list[dict[str, Any]]:
    if sample_mode == "all_positive":
        positive = sorted(
            [row for row in rows if row["positive_posterior"]],
            key=lambda row: (-row["abs_delta"], row["row_idx"]),
        )
        return [assign_bucket(row, "posterior_attributed_move") for row in positive]

    if sample_mode != "balanced_100":
        raise ValueError(f"unknown sample mode: {sample_mode}")

    positive = sorted(
        [row for row in rows if row["positive_posterior"]],
        key=lambda row: (-row["abs_delta"], row["row_idx"]),
    )
    zero = [row for row in rows if not row["positive_posterior"]]
    zero_moved = sorted(
        [row for row in zero if row["abs_delta"] >= 0.02],
        key=lambda row: (-row["abs_delta"], row["row_idx"]),
    )
    zero_stable = sorted(
        [row for row in zero if row["abs_delta"] <= 0.005],
        key=lambda row: (row["row_idx"]),
    )

    sampled: list[dict[str, Any]] = []
    for bucket, bucket_rows, n, cap in [
        ("posterior_attributed_move", positive, 50, 18),
        ("unattributed_moved", zero_moved, 25, 10),
        ("stable_no_attribution", zero_stable, 25, 10),
    ]:
        part = select_with_cap(bucket_rows, n, cap)
        if len(part) < n:
            raise ValueError(f"not enough rows for {bucket}: needed {n}, found {len(part)}")
        for row in part:
            sampled.append(assign_bucket(row, bucket))
    return sampled


def add_selection(selections: dict[int, set[str]], idx: int | None, reason: str) -> None:
    if idx is None:
        return
    selections.setdefault(idx, set()).add(reason)


def add_ranked_selections(
    selections: dict[int, set[str]],
    ranked_indices: list[int],
    k: int,
    primary_reason: str,
    top_k_reason: str,
) -> None:
    for rank, idx in enumerate(ranked_indices[: max(k, 0)], start=1):
        add_selection(selections, idx, top_k_reason)
        if rank == 1:
            add_selection(selections, idx, primary_reason)


def choose_candidates(
    row: dict[str, Any],
    rng: random.Random,
    *,
    top_posterior_k: int,
    top_prior_k: int,
    hard_negative_k: int,
    random_k: int,
) -> dict[int, set[str]]:
    posterior = row["posterior"]
    news = posterior.get("news") or []
    post_scores = row["post_scores"]
    prior_scores = row["prior_scores"]
    question = str(posterior.get("question") or "")
    selections: dict[int, set[str]] = {}

    positive_post = [(idx, score) for idx, score in post_scores.items() if score > 0]
    if positive_post:
        post_ranked = [idx for idx, _ in sorted(positive_post, key=lambda kv: (-kv[1], kv[0]))]
        add_ranked_selections(
            selections,
            post_ranked,
            top_posterior_k,
            "top_posterior",
            "posterior_top_k",
        )

    if prior_scores:
        prior_ranked = [idx for idx, _ in sorted(prior_scores.items(), key=lambda kv: (-kv[1], kv[0]))]
        add_ranked_selections(
            selections,
            prior_ranked,
            top_prior_k,
            "top_prior",
            "prior_top_k",
        )

    overlaps = {idx: lexical_overlap(question, item) for idx, item in enumerate(news)}
    hard_negative_pool = [
        idx
        for idx in range(len(news))
        if post_scores.get(idx, 0.0) <= 0 and idx not in selections
    ]
    if hard_negative_pool:
        hard_ranked = sorted(
            hard_negative_pool,
            key=lambda idx: (
                -overlaps.get(idx, 0.0),
                -prior_scores.get(idx, 0.0),
                idx,
            ),
        )
        add_ranked_selections(
            selections,
            hard_ranked,
            hard_negative_k,
            "lexical_hard_negative",
            "lexical_hard_negative_k",
        )

    random_pool = [idx for idx in range(len(news)) if idx not in selections]
    random_count = min(max(random_k, 0), len(random_pool))
    if random_count:
        for idx in rng.sample(random_pool, random_count):
            add_selection(selections, idx, "random_candidate")

    return selections


def compact_news(news: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": news.get("title") or "",
        "description": news.get("description") or "",
        "source": news.get("source") or "",
        "url": news.get("url") or "",
        "published_at": news.get("published_at") or news.get("date") or "",
    }


def pilot_row_id(row: dict[str, Any], row_id_prefix: str) -> str:
    prefix = row_id_prefix.strip() or "kalshi_test"
    return f"{prefix}_{row['row_idx']:04d}"


def candidate_rows(
    sampled_rows: list[dict[str, Any]],
    seed: int,
    *,
    top_posterior_k: int,
    top_prior_k: int,
    hard_negative_k: int,
    random_k: int,
    row_id_prefix: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in sampled_rows:
        rng = random.Random(seed + row["row_idx"])
        posterior = row["posterior"]
        prior = row["prior"]
        news = posterior.get("news") or []
        post_scores = row["post_scores"]
        prior_scores = row["prior_scores"]
        post_ranks = rank_map({idx: score for idx, score in post_scores.items() if score > 0})
        prior_ranks = rank_map(prior_scores)
        overlaps = {idx: lexical_overlap(str(posterior.get("question") or ""), item) for idx, item in enumerate(news)}
        overlap_ranks = rank_map(overlaps)
        before = posterior.get("before") or {}
        after = posterior.get("after") or {}
        delta = row["price_delta"]

        selections = choose_candidates(
            row,
            rng,
            top_posterior_k=top_posterior_k,
            top_prior_k=top_prior_k,
            hard_negative_k=hard_negative_k,
            random_k=random_k,
        )
        for idx, reasons in sorted(selections.items()):
            item = news[idx]
            out.append(
                {
                    "pilot_row_id": pilot_row_id(row, row_id_prefix),
                    "row_idx": row["row_idx"],
                    "row_bucket": row["row_bucket"],
                    "selection_reasons": sorted(reasons),
                    "market_id": posterior.get("market_id"),
                    "event_id": posterior.get("event_id"),
                    "question": posterior.get("question"),
                    "description": posterior.get("description") or prior.get("description") or "",
                    "category": row["category"],
                    "sample_type": row["sample_type"],
                    "is_grounded_market": row["is_grounded_market"],
                    "grounding_reasons": row["grounding_reasons"],
                    "grounding_exclusion_reasons": row["grounding_exclusion_reasons"],
                    "before_t": before.get("t"),
                    "before_p": before.get("p"),
                    "after_t": after.get("t"),
                    "after_p": after.get("p"),
                    "price_delta": delta,
                    "abs_delta": row["abs_delta"],
                    "price_direction": sign_label(delta),
                    "z_score": posterior.get("z_score"),
                    "window_start": posterior.get("window_start"),
                    "window_end": posterior.get("window_end"),
                    "news_count": row["news_count"],
                    "candidate_news_idx": idx,
                    "posterior_score": post_scores.get(idx, 0.0),
                    "posterior_rank_positive_only": post_ranks.get(idx),
                    "prior_score": prior_scores.get(idx, 0.0),
                    "prior_rank": prior_ranks.get(idx),
                    "lexical_overlap": overlaps.get(idx, 0.0),
                    "lexical_overlap_rank": overlap_ranks.get(idx),
                    "recency_hours_to_after": recency_hours(item, after),
                    "news": compact_news(item),
                }
            )
    return out


def row_records(sampled_rows: list[dict[str, Any]], row_id_prefix: str) -> list[dict[str, Any]]:
    rows = []
    for row in sampled_rows:
        posterior = row["posterior"]
        before = posterior.get("before") or {}
        after = posterior.get("after") or {}
        before_t = before.get("t")
        price_history = []
        for point in posterior.get("window_history") or []:
            t_value = point.get("t") if isinstance(point, dict) else None
            p_value = point.get("p") if isinstance(point, dict) else None
            if not isinstance(t_value, (int, float)) or not isinstance(p_value, (int, float)):
                continue
            if isinstance(before_t, (int, float)) and float(t_value) > float(before_t):
                continue
            price_history.append({"t": t_value, "p": p_value})
        rows.append(
            {
                "pilot_row_id": pilot_row_id(row, row_id_prefix),
                "row_idx": row["row_idx"],
                "row_bucket": row["row_bucket"],
                "market_id": posterior.get("market_id"),
                "event_id": posterior.get("event_id"),
                "question": posterior.get("question"),
                "category": row["category"],
                "sample_type": row["sample_type"],
                "is_grounded_market": row["is_grounded_market"],
                "grounding_reasons": row["grounding_reasons"],
                "grounding_exclusion_reasons": row["grounding_exclusion_reasons"],
                "before_t": before.get("t"),
                "before_p": before.get("p"),
                "price_history": price_history,
                "after_t": after.get("t"),
                "after_p": after.get("p"),
                "price_delta": row["price_delta"],
                "abs_delta": row["abs_delta"],
                "price_direction": sign_label(row["price_delta"]),
                "z_score": posterior.get("z_score"),
                "news_count": row["news_count"],
                "max_posterior_score": row["max_posterior_score"],
                "max_prior_score": row["max_prior_score"],
                "positive_posterior": row["positive_posterior"],
            }
        )
    return rows


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key)) for row in rows))


def full_input_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    positive_rows = [row for row in rows if row["positive_posterior"]]
    zero_rows = [row for row in rows if not row["positive_posterior"]]
    moved_rows = [row for row in rows if row["abs_delta"] >= 0.02]
    zero_moved_rows = [
        row for row in rows if not row["positive_posterior"] and row["abs_delta"] >= 0.02
    ]

    top_prior_rows = []
    top_prior_positive = []
    top_prior_exact_top_post = []
    for row in rows:
        prior_scores = row["prior_scores"]
        post_scores = row["post_scores"]
        positive_post = [(idx, score) for idx, score in post_scores.items() if score > 0]
        if not prior_scores:
            continue
        top_prior_idx = sorted(prior_scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        top_prior_rows.append(row)
        if post_scores.get(top_prior_idx, 0.0) > 0:
            top_prior_positive.append(row)
        if positive_post:
            top_post_idx = sorted(positive_post, key=lambda kv: (-kv[1], kv[0]))[0][0]
            if top_prior_idx == top_post_idx:
                top_prior_exact_top_post.append(row)

    positive_with_prior = [
        row for row in positive_rows if row["prior_scores"]
    ]
    return {
        "input_rows": len(rows),
        "positive_posterior_rows": len(positive_rows),
        "positive_posterior_rate": len(positive_rows) / len(rows) if rows else None,
        "zero_posterior_rows": len(zero_rows),
        "abs_delta_ge_0.02_rows": len(moved_rows),
        "zero_posterior_abs_delta_ge_0.02_rows": len(zero_moved_rows),
        "zero_posterior_abs_delta_ge_0.02_rate": (
            len(zero_moved_rows) / len(zero_rows) if zero_rows else None
        ),
        "top_prior_rows": len(top_prior_rows),
        "top_prior_posterior_positive_rate_all": (
            len(top_prior_positive) / len(top_prior_rows) if top_prior_rows else None
        ),
        "top_prior_exact_top_posterior_rate_positive_rows": (
            len(top_prior_exact_top_post) / len(positive_with_prior)
            if positive_with_prior
            else None
        ),
        "categories": dict(Counter(row["category"] for row in rows)),
        "sample_types": dict(Counter(row["sample_type"] for row in rows)),
    }


def build_summary(
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    *,
    candidate_config: dict[str, int],
    market_filter: str,
    eligible_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons = Counter(reason for cand in candidates for reason in cand["selection_reasons"])
    candidate_buckets = Counter(cand["row_bucket"] for cand in candidates)
    top_prior_positive = [
        cand
        for cand in candidates
        if "top_prior" in cand["selection_reasons"] and cand["posterior_score"] > 0
    ]
    top_prior_all = [
        cand for cand in candidates if "top_prior" in cand["selection_reasons"]
    ]
    hard_negative_scores = [
        cand["lexical_overlap"]
        for cand in candidates
        if "lexical_hard_negative" in cand["selection_reasons"]
    ]
    return {
        "row_count": len(rows),
        "candidate_count": len(candidates),
        "market_filter": market_filter,
        "candidate_config": candidate_config,
        "row_buckets": count_by(rows, "row_bucket"),
        "row_categories": count_by(rows, "category"),
        "row_sample_types": count_by(rows, "sample_type"),
        "candidate_buckets": dict(candidate_buckets),
        "selection_reason_counts": dict(reasons),
        "top_prior_candidates": len(top_prior_all),
        "top_prior_posterior_positive": len(top_prior_positive),
        "top_prior_posterior_positive_rate": (
            len(top_prior_positive) / len(top_prior_all) if top_prior_all else None
        ),
        "mean_hard_negative_lexical_overlap": (
            sum(hard_negative_scores) / len(hard_negative_scores)
            if hard_negative_scores
            else None
        ),
        "max_abs_delta": max(row["abs_delta"] for row in rows),
        "median_abs_delta": sorted(row["abs_delta"] for row in rows)[len(rows) // 2],
        "eligible_input_summary": full_input_summary(eligible_rows),
        "full_input_summary": full_input_summary(all_rows),
    }


def write_reason_summary(path: Path, candidates: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for cand in candidates:
        for reason in cand["selection_reasons"]:
            counts[(cand["row_bucket"], reason)] += 1
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_bucket", "selection_reason", "count"])
        writer.writeheader()
        for (bucket, reason), count in sorted(counts.items()):
            writer.writerow(
                {"row_bucket": bucket, "selection_reason": reason, "count": count}
            )


def short(text: str, n: int = 115) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= n:
        return text
    return text[: n - 3] + "..."


def write_markdown_report(
    path: Path,
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    output_files: list[Path],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cand in candidates:
        by_row[cand["pilot_row_id"]].append(cand)

    def row_line(row: dict[str, Any]) -> str:
        cands = by_row[row["pilot_row_id"]]
        top_post = next((c for c in cands if "top_posterior" in c["selection_reasons"]), None)
        top_prior = next((c for c in cands if "top_prior" in c["selection_reasons"]), None)
        return (
            f"- `{row['pilot_row_id']}` {row['price_direction']} "
            f"{row['price_delta']:+.3f}, {row['category']}: "
            f"{short(row['question'], 95)}\n"
            f"  - top posterior: {short((top_post or {}).get('news', {}).get('title', 'none'))}\n"
            f"  - top prior: {short((top_prior or {}).get('news', {}).get('title', 'none'))}"
        )

    top_positive = sorted(
        [row for row in rows if row["row_bucket"] == "posterior_attributed_move"],
        key=lambda row: (-row["abs_delta"], row["row_idx"]),
    )[:10]
    top_unattributed = sorted(
        [row for row in rows if row["row_bucket"] == "unattributed_moved"],
        key=lambda row: (-row["abs_delta"], row["row_idx"]),
    )[:10]

    mismatch = [
        row
        for row in rows
        if any(
            "top_posterior" in cand["selection_reasons"] for cand in by_row[row["pilot_row_id"]]
        )
        and len(
            {
                cand["candidate_news_idx"]
                for cand in by_row[row["pilot_row_id"]]
                if "top_posterior" in cand["selection_reasons"]
                or "top_prior" in cand["selection_reasons"]
            }
        )
        > 1
    ][:10]

    lines = [
        "# Explanation Pilot Data Prep Summary",
        "",
        "No LLM calls were used. This is the candidate dataset for later explanation generation or manual review.",
        "",
        "## Counts",
        "",
        f"- Market filter: `{summary['market_filter']}`",
        f"- Eligible input rows after filter: `{summary['eligible_input_summary']['input_rows']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Candidate news records: `{summary['candidate_count']}`",
        f"- Candidate config: `{summary['candidate_config']}`",
        f"- Row buckets: `{summary['row_buckets']}`",
        f"- Selection reasons: `{summary['selection_reason_counts']}`",
        f"- Top-prior candidates posterior-positive rate: `{summary['top_prior_posterior_positive_rate']:.3f}`",
        "",
        "## Full Raw Kalshi Test Context",
        "",
        f"- Input rows: `{summary['full_input_summary']['input_rows']}`",
        f"- Posterior-positive rows: `{summary['full_input_summary']['positive_posterior_rows']}` "
        f"(`{summary['full_input_summary']['positive_posterior_rate']:.3f}`)",
        f"- Zero-posterior rows with abs(delta) >= 0.02: "
        f"`{summary['full_input_summary']['zero_posterior_abs_delta_ge_0.02_rows']}` "
        f"(`{summary['full_input_summary']['zero_posterior_abs_delta_ge_0.02_rate']:.3f}` of zero-posterior rows)",
        f"- Top-prior posterior-positive rate over all rows with prior scores: "
        f"`{summary['full_input_summary']['top_prior_posterior_positive_rate_all']:.3f}`",
        f"- Top-prior exact top-posterior match rate on posterior-positive rows: "
        f"`{summary['full_input_summary']['top_prior_exact_top_posterior_rate_positive_rows']:.3f}`",
        "",
        "## Largest Posterior-Attributed Moves",
        "",
        *[row_line(row) for row in top_positive],
        "",
        "## Largest Unattributed Moves",
        "",
        *[row_line(row) for row in top_unattributed],
        "",
        "## Examples Where Top Prior And Top Posterior Differ",
        "",
        *[row_line(row) for row in mismatch],
        "",
        "## Output Files",
        "",
        *[f"- `{path.as_posix()}`" for path in output_files],
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_paths(out_dir: Path, report_dir: Path, prefix: str) -> dict[str, Path]:
    if prefix:
        return {
            "rows": out_dir / f"{prefix}_rows.jsonl",
            "candidates": out_dir / f"{prefix}_candidates.jsonl",
            "summary": out_dir / f"{prefix}_summary.json",
            "reason_summary": out_dir / f"{prefix}_candidate_selection_summary.csv",
            "report": report_dir / f"{prefix}_data_prep_summary.md",
        }
    return {
        "rows": out_dir / "kalshi_100row_rows.jsonl",
        "candidates": out_dir / "kalshi_100row_candidates.jsonl",
        "summary": out_dir / "summary.json",
        "reason_summary": out_dir / "candidate_selection_summary.csv",
        "report": report_dir / "initial_data_prep_summary.md",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build no-LLM explanation-pilot candidate rows from SWM Kalshi data."
    )
    parser.add_argument("--posterior-test", type=Path, default=DEFAULT_POSTERIOR_TEST)
    parser.add_argument("--prior-test", type=Path, default=DEFAULT_PRIOR_TEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--top-posterior-k", type=int, default=1)
    parser.add_argument("--top-prior-k", type=int, default=1)
    parser.add_argument("--hard-negative-k", type=int, default=1)
    parser.add_argument("--random-k", type=int, default=1)
    parser.add_argument(
        "--market-filter",
        default="all",
        choices=["all", "grounded"],
        help="Filter source markets before sampling rows.",
    )
    parser.add_argument(
        "--sample-mode",
        default="balanced_100",
        choices=["balanced_100", "all_positive"],
        help="Sampling scheme after market filtering.",
    )
    parser.add_argument(
        "--output-prefix",
        default="",
        help="Optional prefix for alternate output files, e.g. kalshi_100row_expanded_k10.",
    )
    parser.add_argument(
        "--row-id-prefix",
        default="kalshi_test",
        help="Prefix for pilot_row_id values. Use distinct prefixes when building multiple splits.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_rows = paired_rows(args.posterior_test, args.prior_test)
    rows = filter_rows_by_market(all_rows, args.market_filter)
    sampled = build_row_sample(rows, args.sample_mode)
    sampled_rows = row_records(sampled, args.row_id_prefix)
    candidate_config = {
        "top_posterior_k": args.top_posterior_k,
        "top_prior_k": args.top_prior_k,
        "hard_negative_k": args.hard_negative_k,
        "random_k": args.random_k,
    }
    candidates = candidate_rows(
        sampled,
        seed=args.seed,
        row_id_prefix=args.row_id_prefix,
        **candidate_config,
    )
    summary = build_summary(
        sampled_rows,
        candidates,
        all_rows,
        candidate_config=candidate_config,
        market_filter=args.market_filter,
        eligible_rows=rows,
    )
    paths = output_paths(args.out_dir, args.report_dir, args.output_prefix)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(paths["rows"], sampled_rows)
    write_jsonl(paths["candidates"], candidates)
    paths["summary"].write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_reason_summary(paths["reason_summary"], candidates)
    write_markdown_report(
        paths["report"],
        sampled_rows,
        candidates,
        summary,
        output_files=[
            paths["rows"],
            paths["candidates"],
            paths["summary"],
            paths["reason_summary"],
        ],
    )

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
