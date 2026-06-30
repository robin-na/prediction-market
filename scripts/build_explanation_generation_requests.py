#!/usr/bin/env python3
"""Build structured explanation-generation requests for the Kalshi pilot."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROWS = Path("data/derived/explanation_pilot/kalshi_100row_rows.jsonl")
DEFAULT_CANDIDATES = Path("data/derived/explanation_pilot/kalshi_100row_candidates.jsonl")
DEFAULT_OUTPUT = Path("data/derived/explanation_pilot/requests/gemma4_26b_smoke5_requests.jsonl")

PROMPT_VARIANTS: dict[str, str] = {
    "neutral_forecaster": (
        "Generate the most plausible evidence-to-belief update. Focus on what a "
        "well-calibrated forecaster should believe after reading the evidence."
    ),
    "source_skeptic": (
        "Focus on source reliability, directness, and whether each item has actual "
        "access to information about the market outcome."
    ),
    "base_rate_calibrator": (
        "Focus on base rates and update magnitude. Be especially careful not to "
        "move the prior too much from weak or indirect evidence."
    ),
    "resolution_rule_analyst": (
        "Focus on the exact market wording and whether the evidence affects the "
        "formal resolution criterion rather than only a related story."
    ),
    "contrarian_market_analyst": (
        "Look for reasons a market might underreact or overreact to the evidence, "
        "then give the posterior a disciplined forecaster should hold."
    ),
}

RELEVANCE_POLICIES: dict[str, str] = {
    "strict": (
        "- Most candidate evidence items may be distractors. It is acceptable, and often correct, to select no evidence.\n"
        "- Do not select an item because it is broadly about countries, politics, economics, sports, climate, technology, or celebrities.\n"
        "- Select evidence only if it directly affects the exact market question or gives a clear, short causal chain to the exact market outcome."
    ),
    "balanced": (
        "- Most candidate evidence items may be distractors, so reject broad topical matches.\n"
        "- A good answer is selective, not immobile: if an item directly changes the likelihood of the exact market outcome, select it and make a non-zero update.\n"
        "- Relevant evidence can be direct resolution information, credible official announcements, concrete policy/regulatory actions, event-specific data, or a short causal chain to the exact resolution criterion.\n"
        "- Use small updates for weak or indirect evidence, moderate or large updates only for direct or highly diagnostic evidence, and no update when no visible item is relevant."
    ),
}

GENERATION_MODES = {
    "freeform",
    "calibration_diverse",
}

CALIBRATION_DIVERSE_PROFILES = [
    {
        "id": "E1",
        "name": "evidence-strict/no-update model",
        "instruction": (
            "Select evidence only if it directly changes the exact resolution "
            "criterion. If the packet is indirect, stale, or merely topical, "
            "stay close to the prior."
        ),
    },
    {
        "id": "E2",
        "name": "conservative Bayesian update",
        "instruction": (
            "Use relevant evidence but discount weak source quality, indirect "
            "causal chains, and base-rate uncertainty. Prefer small updates."
        ),
    },
    {
        "id": "E3",
        "name": "moderate evidence-weighted update",
        "instruction": (
            "Use the strongest visible evidence and make the update a balanced "
            "market participant would make if the evidence is genuinely relevant."
        ),
    },
    {
        "id": "E4",
        "name": "aggressive market-reaction update",
        "instruction": (
            "Represent the largest defensible posterior move a trader might make "
            "if the evidence is interpreted as market-moving. Large updates are "
            "allowed when the evidence is direct, time-sensitive, or close to the "
            "resolution criterion."
        ),
    },
    {
        "id": "E5",
        "name": "contrarian/noise-or-overreaction model",
        "instruction": (
            "Consider whether the visible evidence is already priced, noisy, "
            "misleading, or likely to trigger market overreaction. This candidate "
            "may dampen, reverse, or reject the apparent update."
        ),
    },
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def iso_from_unix(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return ""


def candidate_id(candidate: dict[str, Any]) -> str:
    return f"{candidate['pilot_row_id']}__news_{candidate['candidate_news_idx']:03d}"


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    news = candidate.get("news") or {}
    return {
        "candidate_id": candidate_id(candidate),
        "published_at": news.get("published_at", ""),
        "source": news.get("source", ""),
        "title": news.get("title", ""),
        "description": news.get("description", ""),
    }


def compact_price_history(row: dict[str, Any]) -> list[dict[str, Any]]:
    history = []
    for point in row.get("price_history") or []:
        t_value = point.get("t") if isinstance(point, dict) else None
        p_value = point.get("p") if isinstance(point, dict) else None
        if not isinstance(t_value, (int, float)) or not isinstance(p_value, (int, float)):
            continue
        history.append(
            {
                "timestamp_utc": iso_from_unix(t_value),
                "probability": round(float(p_value), 6),
            }
        )
    return history


def evidence_packet(candidates: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    if regime == "history_only":
        return []

    if regime == "mixed_blind":
        selected = candidates
    elif regime == "prior_selected":
        selected = [
            cand
            for cand in candidates
            if {
                "top_prior",
                "prior_top_k",
                "lexical_hard_negative",
                "lexical_hard_negative_k",
            }
            & set(cand.get("selection_reasons") or [])
        ]
    elif regime == "posterior_oracle":
        selected = [
            cand
            for cand in candidates
            if {
                "top_posterior",
                "posterior_top_k",
                "lexical_hard_negative",
                "lexical_hard_negative_k",
            }
            & set(cand.get("selection_reasons") or [])
        ]
    else:
        raise ValueError(f"unknown evidence regime: {regime}")

    selected = sorted(selected, key=lambda cand: (cand.get("candidate_news_idx", 10**9), candidate_id(cand)))
    return [compact_candidate(cand) for cand in selected]


def hidden_candidate_metadata(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cand in sorted(candidates, key=lambda item: candidate_id(item)):
        rows.append(
            {
                "candidate_id": candidate_id(cand),
                "candidate_news_idx": cand.get("candidate_news_idx"),
                "selection_reasons": cand.get("selection_reasons") or [],
                "posterior_score": cand.get("posterior_score"),
                "prior_score": cand.get("prior_score"),
                "posterior_rank_positive_only": cand.get("posterior_rank_positive_only"),
                "prior_rank": cand.get("prior_rank"),
                "lexical_overlap_rank": cand.get("lexical_overlap_rank"),
            }
        )
    return rows


def sign_label(value: float, tol: float = 1e-9) -> str:
    if abs(value) <= tol:
        return "flat"
    return "up" if value > 0 else "down"


def select_rows(rows: list[dict[str, Any]], row_limit: int, seed: int) -> list[dict[str, Any]]:
    """Pick a small deterministic, bucket-diverse row subset."""

    if row_limit <= 0 or row_limit >= len(rows):
        return rows

    rng = random.Random(seed)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_bucket[str(row.get("row_bucket", "unknown"))].append(row)
    for bucket_rows in by_bucket.values():
        bucket_rows.sort(key=lambda row: (-float(row.get("abs_delta") or 0.0), str(row.get("pilot_row_id"))))

    bucket_order = ["posterior_attributed_move", "unattributed_moved", "stable_no_attribution"]
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    while len(selected) < row_limit:
        progressed = False
        for bucket in bucket_order:
            bucket_rows = by_bucket.get(bucket, [])
            if not bucket_rows:
                continue
            # Alternate between high-movement and later rows for small smoke diversity.
            idx = len([row for row in selected if row.get("row_bucket") == bucket])
            if idx >= len(bucket_rows):
                continue
            candidate = bucket_rows[idx]
            row_id = str(candidate.get("pilot_row_id"))
            if row_id in seen:
                continue
            selected.append(candidate)
            seen.add(row_id)
            progressed = True
            if len(selected) >= row_limit:
                break
        if not progressed:
            remaining = [row for row in rows if str(row.get("pilot_row_id")) not in seen]
            if not remaining:
                break
            candidate = rng.choice(remaining)
            selected.append(candidate)
            seen.add(str(candidate.get("pilot_row_id")))
    return selected


def filter_rows(rows: list[dict[str, Any]], row_buckets: list[str] | None) -> list[dict[str, Any]]:
    if not row_buckets:
        return rows
    allowed = set(row_buckets)
    return [row for row in rows if str(row.get("row_bucket", "")) in allowed]


def row_ids_from_path(path: Path) -> set[str]:
    ids: set[str] = set()
    for row in read_jsonl(path):
        row_id = row.get("pilot_row_id")
        if row_id:
            ids.add(str(row_id))
            continue
        metadata = row.get("metadata") if isinstance(row, dict) else None
        if isinstance(metadata, dict) and metadata.get("pilot_row_id"):
            ids.add(str(metadata["pilot_row_id"]))
    return ids


def exclude_rows(rows: list[dict[str, Any]], exclude_paths: list[Path] | None) -> tuple[list[dict[str, Any]], set[str]]:
    excluded_ids: set[str] = set()
    for path in exclude_paths or []:
        excluded_ids |= row_ids_from_path(path)
    if not excluded_ids:
        return rows, excluded_ids
    return [row for row in rows if str(row.get("pilot_row_id", "")) not in excluded_ids], excluded_ids


def render_user_prompt(
    *,
    row: dict[str, Any],
    packet: list[dict[str, Any]],
    evidence_regime: str,
    prompt_variant: str,
    relevance_policy: str,
    num_explanations: int,
    generation_mode: str,
) -> str:
    prior = float(row.get("before_p") or 0.0)
    variant_instruction = PROMPT_VARIANTS[prompt_variant]
    relevance_policy_text = RELEVANCE_POLICIES[relevance_policy]
    evidence_json = json.dumps(packet, ensure_ascii=True, indent=2)
    if not packet:
        evidence_json = "[]"
    history_json = json.dumps(compact_price_history(row), ensure_ascii=True, indent=2)
    if history_json == "[]":
        history_json = "[]"

    description = str(row.get("description") or "").strip()
    if not description:
        description = "(no additional description provided)"

    if generation_mode == "freeform":
        generation_task = (
            f"Generate {num_explanations} mutually distinct candidate explanation/update models linking the visible information to posterior beliefs.\n"
            "Each candidate should represent a plausible way a disciplined market participant might update from the same prior and evidence.\n"
            "Diversify candidates by evidence selection, causal mechanism, source skepticism, base-rate use, update magnitude, and possible market overreaction/underreaction.\n"
            "Flat/no-update is valid when warranted, but do not make all candidates flat unless the visible evidence packet truly gives no plausible market-relevant signal.\n"
            "Do not average the candidates into one answer before listing them."
        )
    elif generation_mode == "calibration_diverse":
        if num_explanations != len(CALIBRATION_DIVERSE_PROFILES):
            raise ValueError(
                "calibration_diverse generation requires num_explanations="
                f"{len(CALIBRATION_DIVERSE_PROFILES)}"
            )
        profile_lines = "\n".join(
            f"- {profile['id']} ({profile['name']}): {profile['instruction']}"
            for profile in CALIBRATION_DIVERSE_PROFILES
        )
        generation_task = (
            "Generate exactly five candidate explanation/update models using these fixed profiles:\n"
            f"{profile_lines}\n\n"
            "The purpose is posterior-support coverage, not consensus. The candidates should span a wide but defensible range of posterior updates from the same prior and evidence.\n"
            "When the visible evidence is relevant, at least one candidate should test a materially larger market-style update than a cautious analyst would choose.\n"
            "When the visible evidence is genuinely irrelevant, all candidates may stay close to the prior, but they should still differ in why they reject the evidence.\n"
            "Do not average the profiles into one answer before listing them. Keep each candidate faithful to its assigned profile."
        )
    else:
        raise ValueError(f"unknown generation mode: {generation_mode}")

    return f"""You are generating candidate explanations for a prediction-market belief update.

Important constraints:
- You are NOT shown the future market price, market delta, final outcome, or attribution labels.
- Do not rationalize a known move. Forecast what posterior a disciplined trader should hold after the visible information.
- Return only valid JSON. Do not use Markdown fences. Do not add commentary outside JSON.
- The evidence packet can contain many items. Do not enumerate all of them in the output.
- Any output array other than candidate_explanations and explanation_classes must contain at most 5 items.

Relevance policy ({relevance_policy}):
{relevance_policy_text}

Prompt variant:
{prompt_variant}: {variant_instruction}

Generation mode:
{generation_mode}

Market:
- market_id: {row.get("market_id", "")}
- event_id: {row.get("event_id", "")}
- category: {row.get("category", "")}
- question: {row.get("question", "")}
- description: {description}

Prior belief state:
- prior_probability: {prior:.4f}
- prior_timestamp_utc: {iso_from_unix(row.get("before_t"))}

Recent market price history available before the forecast time:
{history_json}

Visible evidence packet ({evidence_regime}):
{evidence_json}

Task:
{generation_task}

Use this exact JSON shape:
{{
  "candidate_explanations": [
    {{
      "explanation_id": "E1",
      "selected_evidence_ids": ["candidate_id"],
      "nonselected_evidence_summary": "brief reason the other visible items were not central to this update",
      "posterior_probability": 0.0,
      "delta_from_prior": 0.0,
      "direction": "up|down|flat",
      "magnitude": "none|small|moderate|large",
      "explanation_text": "short explanation of this market-specific update",
      "update_rule": "general reusable update rule, not just this case",
      "explanation_classes": ["source_credibility", "base_rate_calibration"],
      "evidence_weights": [
        {{"candidate_id": "candidate_id", "weight": 0.0, "role": "supports_upward_update|supports_downward_update|dampens_update"}}
      ],
      "calibration_rule": "why this posterior moves this much rather than more or less",
      "confidence": 0.0
    }}
  ],
  "ensemble_summary": {{
    "recommended_explanation_id": "E1",
    "posterior_mean": 0.0,
    "posterior_min": 0.0,
    "posterior_max": 0.0,
    "main_disagreement": "short description of why candidates differ"
  }}
}}

Requirements:
- candidate_explanations must contain exactly {num_explanations} objects with IDs E1, E2, ...
- Each posterior_probability must be between 0 and 1.
- Each delta_from_prior must equal posterior_probability - {prior:.4f}, up to rounding.
- selected_evidence_ids and evidence_weights must use only candidate IDs from the visible evidence packet.
- selected_evidence_ids must contain at most 5 IDs; choose only the evidence central to the update.
- evidence_weights must contain at most 5 objects and must refer only to IDs in selected_evidence_ids.
- Do not put irrelevant evidence in evidence_weights. If evidence is irrelevant, leave it out and summarize the pattern in nonselected_evidence_summary.
- Do not enumerate ignored evidence IDs. Summarize why nonselected evidence was not central in nonselected_evidence_summary.
- If a candidate treats all visible evidence as irrelevant, selected_evidence_ids must be empty, evidence_weights must be empty, explanation_classes must include "evidence_irrelevance", nonselected_evidence_summary should explain the irrelevance pattern, and posterior_probability should stay close to the prior.
- If the evidence packet is empty, selected_evidence_ids and evidence_weights must be empty and the update should rely only on the price history, prior, and market wording.
- The ensemble_summary posterior fields must be computed from the candidate posterior_probability values.
- Before returning, check that every selected_evidence_ids array has length <= 5 and every evidence_weights array has length <= 5. If not, shorten the arrays before returning JSON.

Allowed explanation class labels:
- source_credibility
- base_rate_calibration
- resolution_rule
- causal_chain
- direct_resolution
- trend_continuation
- overreaction_correction
- underreaction_correction
- evidence_irrelevance
- market_microstructure
- other
"""


def build_request(
    *,
    row: dict[str, Any],
    row_candidates: list[dict[str, Any]],
    evidence_regime: str,
    prompt_variant: str,
    relevance_policy: str,
    sample_index: int,
    num_explanations: int,
    generation_mode: str,
    model: str,
    run_id: str,
) -> dict[str, Any] | None:
    packet = evidence_packet(row_candidates, evidence_regime)
    if evidence_regime != "history_only" and not packet:
        return None

    prior = float(row.get("before_p") or 0.0)
    after = float(row.get("after_p") or 0.0)
    delta = after - prior
    custom_id = (
        f"{run_id}__{row['pilot_row_id']}__{evidence_regime}__"
        f"{prompt_variant}__s{sample_index:02d}"
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful prediction-market analyst. Your output is a "
                "scoreable belief update and a reusable explanation class."
            ),
        },
        {
            "role": "user",
            "content": render_user_prompt(
                row=row,
                packet=packet,
                evidence_regime=evidence_regime,
                prompt_variant=prompt_variant,
                relevance_policy=relevance_policy,
                num_explanations=num_explanations,
                generation_mode=generation_mode,
            ),
        },
    ]
    return {
        "custom_id": custom_id,
        "messages": messages,
        "metadata": {
            "run_id": run_id,
            "target_model": model,
            "pilot_row_id": row.get("pilot_row_id"),
            "row_idx": row.get("row_idx"),
            "row_bucket": row.get("row_bucket"),
            "market_id": row.get("market_id"),
            "event_id": row.get("event_id"),
            "question": row.get("question"),
            "category": row.get("category"),
            "before_t": row.get("before_t"),
            "before_p": prior,
            "after_t": row.get("after_t"),
            "after_p": after,
            "price_delta": delta,
            "price_direction": sign_label(delta),
            "z_score": row.get("z_score"),
            "positive_posterior": row.get("positive_posterior"),
            "evidence_regime": evidence_regime,
            "prompt_variant": prompt_variant,
            "relevance_policy": relevance_policy,
            "generation_mode": generation_mode,
            "sample_index": sample_index,
            "num_explanations": num_explanations,
            "visible_evidence_ids": [item["candidate_id"] for item in packet],
            "all_candidate_metadata": hidden_candidate_metadata(row_candidates),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--run-id", default="gemma4_26b_explanation_smoke5")
    parser.add_argument("--model", default="google/gemma-4-26B-A4B")
    parser.add_argument("--row-limit", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--relevance-policy", default="balanced", choices=sorted(RELEVANCE_POLICIES))
    parser.add_argument(
        "--evidence-regimes",
        nargs="+",
        default=["mixed_blind", "prior_selected"],
        choices=["mixed_blind", "prior_selected", "posterior_oracle", "history_only"],
    )
    parser.add_argument(
        "--prompt-variants",
        nargs="+",
        default=["neutral_forecaster", "source_skeptic", "base_rate_calibrator"],
        choices=sorted(PROMPT_VARIANTS),
    )
    parser.add_argument("--samples-per-cell", type=int, default=1)
    parser.add_argument("--num-explanations", type=int, default=1)
    parser.add_argument(
        "--generation-mode",
        default="freeform",
        choices=sorted(GENERATION_MODES),
        help="How to specify diversity among generated candidate explanations.",
    )
    parser.add_argument(
        "--row-buckets",
        nargs="+",
        default=None,
        help="Optional row_bucket values to keep before row-limit sampling.",
    )
    parser.add_argument(
        "--exclude-rows-from",
        nargs="+",
        type=Path,
        default=None,
        help="JSONL files containing pilot_row_id or metadata.pilot_row_id values to exclude.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.rows)
    candidates = read_jsonl(args.candidates)
    candidates_by_row: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        candidates_by_row[str(candidate.get("pilot_row_id"))].append(candidate)

    filtered_rows = filter_rows(rows, args.row_buckets)
    filtered_rows, excluded_row_ids = exclude_rows(filtered_rows, args.exclude_rows_from)
    selected_rows = select_rows(filtered_rows, args.row_limit, args.seed)
    requests: list[dict[str, Any]] = []
    skipped = 0
    for row in selected_rows:
        row_id = str(row.get("pilot_row_id"))
        row_candidates = candidates_by_row.get(row_id, [])
        for evidence_regime in args.evidence_regimes:
            for prompt_variant in args.prompt_variants:
                for sample_index in range(args.samples_per_cell):
                    request = build_request(
                        row=row,
                        row_candidates=row_candidates,
                        evidence_regime=evidence_regime,
                        prompt_variant=prompt_variant,
                        relevance_policy=args.relevance_policy,
                        sample_index=sample_index,
                        num_explanations=args.num_explanations,
                        generation_mode=args.generation_mode,
                        model=args.model,
                        run_id=args.run_id,
                    )
                    if request is None:
                        skipped += 1
                        continue
                    requests.append(request)

    write_jsonl(args.output, requests)
    summary = {
        "run_id": args.run_id,
        "model": args.model,
        "row_limit": args.row_limit,
        "row_buckets_filter": args.row_buckets,
        "exclude_rows_from": [str(path) for path in args.exclude_rows_from or []],
        "excluded_row_count": len(excluded_row_ids),
        "available_rows_after_filter": len(filtered_rows),
        "selected_rows": [row.get("pilot_row_id") for row in selected_rows],
        "evidence_regimes": args.evidence_regimes,
        "prompt_variants": args.prompt_variants,
        "relevance_policy": args.relevance_policy,
        "generation_mode": args.generation_mode,
        "samples_per_cell": args.samples_per_cell,
        "num_explanations": args.num_explanations,
        "request_count": len(requests),
        "skipped_empty_packets": skipped,
        "output": str(args.output),
    }
    summary_path = args.output.with_suffix(args.output.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
