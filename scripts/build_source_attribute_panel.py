#!/usr/bin/env python3
"""Join SWM Kalshi source weights with external source attributes.

This script uses the released Kalshi prior/posterior attribution splits from
SWM-Bench. It builds domain/source panels and compares posterior helpfulness
against learned prior attention and external credibility/attention proxies.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd


DEFAULT_RAW_DIR = Path("data/swm-bench/raw/kalshi/splitted_v2_0102")
DEFAULT_EXTERNAL_DIR = Path("data/external")
DEFAULT_OUTPUT_DIR = Path("data/source_attribute_panel")

BAD_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "com.mx",
    "com.tr",
    "co.jp",
    "co.kr",
    "com.cn",
    "com.sg",
    "com.my",
    "co.in",
    "com.ph",
    "co.za",
}

CREDIBILITY_NUM = {
    "low-credibility": 0,
    "medium-credibility": 1,
    "high-credibility": 2,
}
REPORTING_NUM = {
    "very-low": 0,
    "low": 1,
    "mixed": 2,
    "mostly-factual": 3,
    "high": 4,
    "very-high": 5,
}
TRAFFIC_NUM = {
    "no-data": 0,
    "minimal-traffic": 1,
    "medium-traffic": 2,
    "high-traffic": 3,
}
BIAS_NUM = {
    "left": -2,
    "left-center": -1,
    "center": 0,
    "right-center": 1,
    "right": 2,
    "pro-science": 0,
    "satire": math.nan,
    "fake-news": math.nan,
    "conspiracy-pseudoscience": math.nan,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_host(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def host_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.netloc and "://" not in url:
        parsed = urlparse(f"https://{url}")
    host = parsed.netloc.split("@")[-1].split(":")[0]
    return normalize_host(host)


def suffix_candidates(host: str) -> list[str]:
    parts = [part for part in host.split(".") if part]
    candidates: list[str] = []
    for start in range(max(0, len(parts) - 2), -1, -1):
        candidate = ".".join(parts[start:])
        if candidate and candidate not in BAD_SUFFIXES:
            candidates.append(candidate)
    if host and host not in candidates:
        candidates.insert(0, host)
    # Prefer exact/subdomain-preserving candidates first, then parent domains.
    ordered: list[str] = []
    for candidate in [host, *candidates, ".".join(parts[-2:]) if len(parts) >= 2 else host]:
        if candidate and candidate not in ordered and candidate not in BAD_SUFFIXES:
            ordered.append(candidate)
    return ordered


def canonical_domain(host: str, known_domains: set[str]) -> str:
    if not host:
        return ""
    for candidate in suffix_candidates(host):
        if candidate in known_domains:
            return candidate
    parts = host.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in BAD_SUFFIXES:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def load_mbfcext(path: Path) -> tuple[dict[str, dict[str, Any]], set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    aliases = {normalize_host(k): normalize_host(v) for k, v in payload.get("aliases", {}).items()}
    sources: dict[str, dict[str, Any]] = {}
    for source in payload.get("sources", []):
        domain = normalize_host(str(source.get("domain") or ""))
        if not domain:
            continue
        row = dict(source)
        row["domain"] = domain
        sources[domain] = row
    for alias, target in aliases.items():
        if target in sources and alias not in sources:
            sources[alias] = sources[target]
    return sources, set(sources)


def load_iffy(path: Path) -> tuple[dict[str, dict[str, Any]], set[str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        domain = normalize_host(str(row.get("Domain") or ""))
        if domain:
            out[domain] = row
    return out, set(out)


def load_tranco(path: Path) -> tuple[dict[str, int], set[str]]:
    ranks: dict[str, int] = {}
    with zipfile.ZipFile(path) as archive:
        name = archive.namelist()[0]
        with archive.open(name) as handle:
            text = (line.decode("utf-8").strip() for line in handle)
            reader = csv.reader(text)
            for row in reader:
                if len(row) >= 2:
                    ranks[normalize_host(row[1])] = int(row[0])
    return ranks, set(ranks)


def score_map(record: dict[str, Any]) -> dict[int, float]:
    scores: dict[int, float] = {}
    for attr in record.get("attributions") or []:
        idx = attr.get("news_idx")
        if isinstance(idx, int):
            scores[idx] = float(attr.get("score") or 0.0)
    return scores


def posterior_mass(scores: dict[int, float], news_count: int, eps: float, rho0: float) -> dict[int, float]:
    odds: dict[int, float] = {}
    for idx in range(news_count):
        score = float(scores.get(idx, 0.0))
        if score <= 0:
            odds[idx] = 0.0
            continue
        capped = min(score, 1.0 - eps)
        odds[idx] = (capped + eps) / (1.0 - capped + eps)
    denom = rho0 + sum(odds.values())
    if denom <= 0:
        return {idx: 0.0 for idx in range(news_count)}
    return {idx: odds[idx] / denom for idx in range(news_count)}


def category_of(record: dict[str, Any]) -> str:
    categories = record.get("categories")
    if isinstance(categories, list) and categories:
        return "|".join(str(cat) for cat in categories)
    category = record.get("category")
    if isinstance(category, list) and category:
        return "|".join(str(cat) for cat in category)
    return str(category or "Unknown")


def scalar_change(record: dict[str, Any]) -> float:
    change = record.get("change")
    if isinstance(change, (int, float)):
        return float(change)
    before = record.get("before")
    after = record.get("after")
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return float(after) - float(before)
    if isinstance(before, dict) and isinstance(after, dict):
        if "p" in before and "p" in after:
            return float(after["p"]) - float(before["p"])
    return math.nan


def pair_records(prior_path: Path, posterior_path: Path, split: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    prior_rows = read_jsonl(prior_path)
    posterior_rows = read_jsonl(posterior_path)
    if len(prior_rows) != len(posterior_rows):
        raise ValueError(f"{split}: prior/posterior row count mismatch")
    pairs = []
    for row_idx, (prior, posterior) in enumerate(zip(prior_rows, posterior_rows)):
        prior_key = (prior.get("market_id"), prior.get("event_id"), prior.get("question"))
        posterior_key = (posterior.get("market_id"), posterior.get("event_id"), posterior.get("question"))
        if prior_key != posterior_key:
            raise ValueError(f"{split}: mismatched row {row_idx}: {prior_key} != {posterior_key}")
        if len(prior.get("news") or []) != len(posterior.get("news") or []):
            raise ValueError(f"{split}: news length mismatch at row {row_idx}")
        pairs.append((prior, posterior))
    return pairs


def mode_or_empty(values: pd.Series) -> str:
    values = values.dropna()
    if values.empty:
        return ""
    return str(values.mode().iloc[0])


def aggregate_panel(rows: list[dict[str, Any]], group_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    grouped = df.groupby(group_cols, dropna=False)
    aggregations = {
        "candidate_articles": ("posterior_score", "size"),
        "candidate_records": ("record_key", "nunique"),
        "unique_markets": ("market_id", "nunique"),
        "posterior_positive_articles": ("posterior_positive", "sum"),
        "posterior_score_mean": ("posterior_score", "mean"),
        "posterior_score_sum": ("posterior_score", "sum"),
        "posterior_mass_mean": ("posterior_mass", "mean"),
        "posterior_mass_sum": ("posterior_mass", "sum"),
        "prior_weight_mean": ("prior_score", "mean"),
        "prior_weight_sum": ("prior_score", "sum"),
        "wasted_prior_mean": ("wasted_prior", "mean"),
        "wasted_prior_sum": ("wasted_prior", "sum"),
        "helpful_prior_sum": ("helpful_prior", "sum"),
        "abs_change_mean": ("abs_change", "mean"),
        "z_score_mean": ("z_score", "mean"),
        "title_example": ("title", mode_or_empty),
    }
    if "source" not in group_cols:
        aggregations["source"] = ("source", mode_or_empty)
    panel = grouped.agg(**aggregations).reset_index()
    panel["posterior_positive_rate"] = (
        panel["posterior_positive_articles"] / panel["candidate_articles"]
    )
    panel["prior_alignment_rate"] = panel["helpful_prior_sum"] / panel["prior_weight_sum"].replace(0, math.nan)
    panel["prior_waste_rate"] = panel["wasted_prior_sum"] / panel["prior_weight_sum"].replace(0, math.nan)
    return panel


def attach_external(
    panel: pd.DataFrame,
    mbfc: dict[str, dict[str, Any]],
    iffy: dict[str, dict[str, Any]],
    tranco: dict[str, int],
) -> pd.DataFrame:
    rows = []
    for row in panel.to_dict("records"):
        domain = str(row.get("domain") or "")
        mbfc_row = mbfc.get(domain, {})
        iffy_row = iffy.get(domain, {})
        tranco_rank = tranco.get(domain)
        questionable = mbfc_row.get("questionable") or []
        out = dict(row)
        out.update(
            {
                "mbfc_match": bool(mbfc_row),
                "mbfc_name": mbfc_row.get("name", ""),
                "mbfc_bias": mbfc_row.get("bias", ""),
                "mbfc_bias_num": BIAS_NUM.get(mbfc_row.get("bias"), math.nan),
                "mbfc_reporting": mbfc_row.get("reporting", ""),
                "mbfc_reporting_num": REPORTING_NUM.get(mbfc_row.get("reporting"), math.nan),
                "mbfc_credibility": mbfc_row.get("credibility", ""),
                "mbfc_credibility_num": CREDIBILITY_NUM.get(mbfc_row.get("credibility"), math.nan),
                "mbfc_traffic": mbfc_row.get("traffic", ""),
                "mbfc_traffic_num": TRAFFIC_NUM.get(mbfc_row.get("traffic"), math.nan),
                "mbfc_questionable_count": len(questionable) if isinstance(questionable, list) else 0,
                "mbfc_questionable": "|".join(questionable) if isinstance(questionable, list) else "",
                "iffy_flag": bool(iffy_row),
                "iffy_name": iffy_row.get("Name", ""),
                "iffy_score": safe_float(iffy_row.get("Score")),
                "iffy_quality": safe_float(iffy_row.get("Quality")),
                "iffy_misinfo_me": safe_float(iffy_row.get("MisinfoMe")),
                "iffy_site_rank": safe_float(iffy_row.get("Site Rank")),
                "tranco_rank": tranco_rank if tranco_rank is not None else math.nan,
                "tranco_log10_rank": math.log10(tranco_rank) if tranco_rank else math.nan,
                "tranco_attention": -math.log10(tranco_rank) if tranco_rank else math.nan,
            }
        )
        rows.append(out)
    return pd.DataFrame(rows)


def safe_float(value: Any) -> float:
    if value in (None, ""):
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def weighted_mean(series: pd.Series, weights: pd.Series) -> float:
    mask = series.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return math.nan
    return float((series[mask] * weights[mask]).sum() / weights[mask].sum())


def group_summary(article_df: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("mbfc_credibility", "mbfc_credibility"),
        ("mbfc_reporting", "mbfc_reporting"),
        ("mbfc_traffic", "mbfc_traffic"),
        ("mbfc_bias", "mbfc_bias"),
        ("iffy_flag", "iffy_flag"),
        ("tranco_decile", "tranco_decile"),
    ]
    rows: list[dict[str, Any]] = []
    for variable, col in specs:
        if col not in article_df:
            continue
        for group, sub in article_df.groupby(col, dropna=False):
            if len(sub) == 0:
                continue
            rows.append(
                {
                    "variable": variable,
                    "group": str(group),
                    "candidate_articles": len(sub),
                    "domains": sub["domain"].nunique(),
                    "posterior_score_mean": sub["posterior_score"].mean(),
                    "posterior_mass_mean": sub["posterior_mass"].mean(),
                    "posterior_positive_rate": sub["posterior_positive"].mean(),
                    "prior_weight_mean": sub["prior_score"].mean(),
                    "wasted_prior_mean": sub["wasted_prior"].mean(),
                    "prior_alignment_rate": (
                        sub["helpful_prior"].sum() / sub["prior_score"].sum()
                        if sub["prior_score"].sum() > 0
                        else math.nan
                    ),
                    "mean_tranco_rank": sub["tranco_rank"].mean(),
                }
            )
    return pd.DataFrame(rows)


def correlations(domain_df: pd.DataFrame, min_articles: int) -> pd.DataFrame:
    predictors = [
        "tranco_log10_rank",
        "tranco_attention",
        "mbfc_credibility_num",
        "mbfc_reporting_num",
        "mbfc_traffic_num",
        "mbfc_bias_num",
        "mbfc_questionable_count",
        "iffy_flag_num",
    ]
    outcomes = [
        "posterior_score_mean",
        "posterior_mass_mean",
        "posterior_positive_rate",
        "prior_weight_mean",
        "wasted_prior_mean",
        "prior_alignment_rate",
        "prior_waste_rate",
    ]
    df = domain_df.loc[domain_df["candidate_articles"] >= min_articles].copy()
    df["iffy_flag_num"] = df["iffy_flag"].astype(float)
    rows: list[dict[str, Any]] = []
    for predictor in predictors:
        for outcome in outcomes:
            sub = df[[predictor, outcome]].dropna()
            if len(sub) < 5 or sub[predictor].nunique() < 2:
                continue
            rows.append(
                {
                    "predictor": predictor,
                    "outcome": outcome,
                    "n_domains": len(sub),
                    "pearson": sub[predictor].corr(sub[outcome], method="pearson"),
                    "spearman": sub[predictor].corr(sub[outcome], method="spearman"),
                }
            )
    return pd.DataFrame(rows)


def single_predictor_slopes(domain_df: pd.DataFrame, min_articles: int) -> pd.DataFrame:
    predictors = [
        "tranco_log10_rank",
        "tranco_attention",
        "mbfc_credibility_num",
        "mbfc_reporting_num",
        "mbfc_traffic_num",
        "mbfc_questionable_count",
        "iffy_flag_num",
    ]
    outcomes = [
        "posterior_score_mean",
        "posterior_mass_mean",
        "prior_weight_mean",
        "wasted_prior_mean",
        "prior_alignment_rate",
    ]
    df = domain_df.loc[domain_df["candidate_articles"] >= min_articles].copy()
    df["iffy_flag_num"] = df["iffy_flag"].astype(float)
    rows: list[dict[str, Any]] = []
    for predictor in predictors:
        for outcome in outcomes:
            sub = df[[predictor, outcome, "candidate_articles"]].dropna()
            if len(sub) < 5 or sub[predictor].nunique() < 2:
                continue
            x = zscore(sub[predictor])
            y = zscore(sub[outcome])
            w = sub["candidate_articles"].astype(float)
            slope, intercept, r2 = weighted_simple_ols(x, y, w)
            rows.append(
                {
                    "predictor": predictor,
                    "outcome": outcome,
                    "n_domains": len(sub),
                    "weighted_standardized_slope": slope,
                    "weighted_intercept": intercept,
                    "weighted_r2": r2,
                }
            )
    return pd.DataFrame(rows)


def zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if not std or math.isnan(std):
        return series * math.nan
    return (series - series.mean()) / std


def weighted_simple_ols(x: pd.Series, y: pd.Series, w: pd.Series) -> tuple[float, float, float]:
    x_arr = x.to_numpy(dtype=float)
    y_arr = y.to_numpy(dtype=float)
    w_arr = w.to_numpy(dtype=float)
    w_arr = w_arr / w_arr.sum()
    x_bar = float((w_arr * x_arr).sum())
    y_bar = float((w_arr * y_arr).sum())
    cov = float((w_arr * (x_arr - x_bar) * (y_arr - y_bar)).sum())
    var = float((w_arr * (x_arr - x_bar) ** 2).sum())
    slope = cov / var if var > 0 else math.nan
    intercept = y_bar - slope * x_bar if not math.isnan(slope) else math.nan
    pred = intercept + slope * x_arr
    sse = float((w_arr * (y_arr - pred) ** 2).sum())
    sst = float((w_arr * (y_arr - y_bar) ** 2).sum())
    r2 = 1.0 - sse / sst if sst > 0 else math.nan
    return slope, intercept, r2


def add_external_to_articles(
    article_df: pd.DataFrame,
    mbfc: dict[str, dict[str, Any]],
    iffy: dict[str, dict[str, Any]],
    tranco: dict[str, int],
) -> pd.DataFrame:
    article_df = article_df.copy()
    article_df["mbfc_credibility"] = article_df["domain"].map(
        lambda d: mbfc.get(d, {}).get("credibility", "")
    )
    article_df["mbfc_reporting"] = article_df["domain"].map(lambda d: mbfc.get(d, {}).get("reporting", ""))
    article_df["mbfc_traffic"] = article_df["domain"].map(lambda d: mbfc.get(d, {}).get("traffic", ""))
    article_df["mbfc_bias"] = article_df["domain"].map(lambda d: mbfc.get(d, {}).get("bias", ""))
    article_df["iffy_flag"] = article_df["domain"].map(lambda d: d in iffy)
    article_df["tranco_rank"] = article_df["domain"].map(lambda d: tranco.get(d, math.nan))
    article_df["tranco_decile"] = pd.qcut(
        article_df["tranco_rank"],
        q=10,
        duplicates="drop",
        labels=False,
    )
    return article_df


def build_rows(
    raw_dir: Path,
    known_domains: set[str],
    eps: float,
    rho0: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    specs = [
        (
            "train",
            raw_dir / "kalshi_prior_attributed_train_2025-11-01.jsonl",
            raw_dir / "kalshi_data_processed_with_news_attributed_train_2025-11-01.jsonl",
        ),
        (
            "test",
            raw_dir / "kalshi_prior_attributed_test_2025-11-01.jsonl",
            raw_dir / "kalshi_data_processed_with_news_attributed_test_2025-11-01.jsonl",
        ),
    ]
    rows: list[dict[str, Any]] = []
    coverage = {
        "splits": {},
        "records": 0,
        "candidate_articles": 0,
        "records_with_positive_posterior": 0,
    }
    for split, prior_path, posterior_path in specs:
        pairs = pair_records(prior_path, posterior_path, split)
        split_positive = 0
        for record_idx, (prior, posterior) in enumerate(pairs):
            news = posterior.get("news") or []
            prior_scores = score_map(prior)
            post_scores = score_map(posterior)
            post_mass = posterior_mass(post_scores, len(news), eps, rho0)
            record_positive = any(score > 0 for score in post_scores.values())
            split_positive += int(record_positive)
            category = category_of(posterior)
            change = scalar_change(posterior)
            abs_change = abs(change) if not math.isnan(change) else math.nan
            z_score = safe_float(posterior.get("z_score"))
            record_key = f"{split}:{record_idx}:{posterior.get('market_id')}:{posterior.get('event_id')}"
            for idx, item in enumerate(news):
                host = host_from_url(str(item.get("url") or ""))
                domain = canonical_domain(host, known_domains)
                posterior_score = float(post_scores.get(idx, 0.0))
                prior_score = float(prior_scores.get(idx, 0.0))
                posterior_positive = posterior_score > 0
                rows.append(
                    {
                        "split": split,
                        "record_key": record_key,
                        "market_id": posterior.get("market_id", ""),
                        "event_id": posterior.get("event_id", ""),
                        "question": posterior.get("question", ""),
                        "category": category,
                        "news_idx": idx,
                        "source": (item.get("source") or "").strip(),
                        "title": (item.get("title") or "").strip(),
                        "url": item.get("url") or "",
                        "host": host,
                        "domain": domain,
                        "published_at": item.get("published_at") or "",
                        "posterior_score": posterior_score,
                        "posterior_mass": post_mass.get(idx, 0.0),
                        "posterior_positive": posterior_positive,
                        "prior_score": prior_score,
                        "helpful_prior": prior_score if posterior_positive else 0.0,
                        "wasted_prior": prior_score if not posterior_positive else 0.0,
                        "abs_change": abs_change,
                        "z_score": z_score,
                    }
                )
        coverage["splits"][split] = {
            "records": len(pairs),
            "records_with_positive_posterior": split_positive,
        }
        coverage["records"] += len(pairs)
        coverage["records_with_positive_posterior"] += split_positive
    coverage["candidate_articles"] = len(rows)
    return rows, coverage


def write_top_tables(domain_df: pd.DataFrame, out_dir: Path, min_articles: int) -> None:
    eligible = domain_df.loc[domain_df["candidate_articles"] >= min_articles].copy()
    tables = {
        "top_domains_by_posterior_score.csv": eligible.sort_values(
            ["posterior_score_mean", "candidate_articles"], ascending=[False, False]
        ).head(50),
        "top_domains_by_prior_weight.csv": eligible.sort_values(
            ["prior_weight_mean", "candidate_articles"], ascending=[False, False]
        ).head(50),
        "top_domains_by_wasted_prior.csv": eligible.sort_values(
            ["wasted_prior_mean", "candidate_articles"], ascending=[False, False]
        ).head(50),
        "least_helpful_domains.csv": eligible.sort_values(
            ["posterior_score_mean", "candidate_articles"], ascending=[True, False]
        ).head(50),
    }
    for name, table in tables.items():
        table.to_csv(out_dir / name, index=False)


def write_category_top(category_df: pd.DataFrame, out_dir: Path, min_articles: int) -> None:
    rows: list[pd.DataFrame] = []
    for category, sub in category_df.groupby("category", dropna=False):
        eligible = sub.loc[sub["candidate_articles"] >= min_articles].copy()
        if eligible.empty:
            continue
        ranked = eligible.sort_values(["posterior_score_mean", "candidate_articles"], ascending=[False, False])
        rows.append(ranked.head(10).assign(rank=range(1, min(10, len(ranked)) + 1)))
    if rows:
        pd.concat(rows, ignore_index=True).to_csv(out_dir / "top_domains_by_category.csv", index=False)


def coverage_summary(
    coverage: dict[str, Any],
    rows: list[dict[str, Any]],
    domain_df: pd.DataFrame,
    article_df: pd.DataFrame,
) -> dict[str, Any]:
    source_counts = Counter(row["source"] for row in rows)
    domain_counts = Counter(row["domain"] for row in rows)
    out = dict(coverage)
    out.update(
        {
            "domains": int(article_df["domain"].nunique()),
            "sources": int(article_df["source"].nunique()),
            "mbfc_matched_domains": int(domain_df["mbfc_match"].sum()),
            "mbfc_matched_articles": int(article_df["domain"].isin(domain_df.loc[domain_df["mbfc_match"], "domain"]).sum()),
            "iffy_flagged_domains": int(domain_df["iffy_flag"].sum()),
            "iffy_flagged_articles": int(article_df["domain"].isin(domain_df.loc[domain_df["iffy_flag"], "domain"]).sum()),
            "tranco_matched_domains": int(domain_df["tranco_rank"].notna().sum()),
            "tranco_matched_articles": int(article_df["tranco_rank"].notna().sum()),
            "top_sources_by_candidate_count": source_counts.most_common(20),
            "top_domains_by_candidate_count": domain_counts.most_common(20),
        }
    )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--external-dir", type=Path, default=DEFAULT_EXTERNAL_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--mbfc-combined", type=Path, default=DEFAULT_EXTERNAL_DIR / "mbfcext_combined.json")
    parser.add_argument("--iffy-index", type=Path, default=DEFAULT_EXTERNAL_DIR / "iffy_index.json")
    parser.add_argument("--tranco-zip", type=Path, default=DEFAULT_EXTERNAL_DIR / "tranco_top_1m.csv.zip")
    parser.add_argument("--min-domain-articles", type=int, default=20)
    parser.add_argument("--min-category-articles", type=int, default=10)
    parser.add_argument("--odds-eps", type=float, default=1e-6)
    parser.add_argument("--null-rho0", type=float, default=1.0)
    parser.add_argument("--write-article-csv", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    mbfc, mbfc_domains = load_mbfcext(args.mbfc_combined)
    iffy, iffy_domains = load_iffy(args.iffy_index)
    tranco, tranco_domains = load_tranco(args.tranco_zip)
    known_domains = mbfc_domains | iffy_domains | tranco_domains

    rows, coverage = build_rows(args.raw_dir, known_domains, args.odds_eps, args.null_rho0)
    article_df = pd.DataFrame(rows)
    article_df = add_external_to_articles(article_df, mbfc, iffy, tranco)
    if args.write_article_csv:
        article_df.to_csv(args.out_dir / "article_level_prior_posterior.csv", index=False)

    domain_panel = aggregate_panel(rows, ["domain"])
    domain_panel = attach_external(domain_panel, mbfc, iffy, tranco)
    domain_panel.to_csv(args.out_dir / "domain_panel.csv", index=False)

    source_panel = aggregate_panel(rows, ["source", "domain"])
    source_panel = attach_external(source_panel, mbfc, iffy, tranco)
    source_panel.to_csv(args.out_dir / "source_domain_panel.csv", index=False)

    category_panel = aggregate_panel(rows, ["category", "domain"])
    category_panel = attach_external(category_panel, mbfc, iffy, tranco)
    category_panel.to_csv(args.out_dir / "category_domain_panel.csv", index=False)

    group_summary(article_df).to_csv(args.out_dir / "external_attribute_group_summary.csv", index=False)
    correlations(domain_panel, args.min_domain_articles).to_csv(args.out_dir / "domain_correlations.csv", index=False)
    single_predictor_slopes(domain_panel, args.min_domain_articles).to_csv(
        args.out_dir / "single_predictor_slopes.csv",
        index=False,
    )
    write_top_tables(domain_panel, args.out_dir, args.min_domain_articles)
    write_category_top(category_panel, args.out_dir, args.min_category_articles)

    summary = coverage_summary(coverage, rows, domain_panel, article_df)
    summary.update(
        {
            "mbfc_source_domains": len(mbfc_domains),
            "iffy_domains": len(iffy_domains),
            "tranco_domains": len(tranco_domains),
            "min_domain_articles_for_rankings": args.min_domain_articles,
            "outputs": sorted(path.name for path in args.out_dir.glob("*")),
        }
    )
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
