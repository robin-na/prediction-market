#!/usr/bin/env python3
"""Parse and score multi-explanation generation outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


DEFAULT_OUTPUTS = Path(
    "data/derived/explanation_pilot/outputs/"
    "gemma4_26b_fullnews_bounded_ensemble5_20260629_outputs.jsonl"
)
DEFAULT_PARSED = Path(
    "data/derived/explanation_pilot/outputs/"
    "gemma4_26b_fullnews_bounded_ensemble5_20260629_parsed.jsonl"
)
DEFAULT_SCORES = Path(
    "data/derived/explanation_pilot/outputs/"
    "gemma4_26b_fullnews_bounded_ensemble5_20260629_scores.csv"
)
INVALID_JSON_BACKSLASH = re.compile(r'\\(?!["\\/bfnrtu])')


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json_loads_lenient(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    for start, end in balanced_json_object_spans(stripped):
        try:
            parsed = json_loads_lenient(stripped[start:end])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("no JSON object found")


def balanced_json_object_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, index + 1))
                start = None
    return spans


def json_loads_lenient(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        repaired = INVALID_JSON_BACKSLASH.sub(r"\\\\", text)
        if repaired == text:
            raise
        return json.loads(repaired)


def as_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return math.nan
    return math.nan


def sign_label(value: float, tol: float = 1e-9) -> str:
    if not math.isfinite(value) or abs(value) <= tol:
        return "flat"
    return "up" if value > 0 else "down"


def candidate_reason_sets(metadata: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for candidate in metadata.get("all_candidate_metadata") or []:
        cid = str(candidate.get("candidate_id", ""))
        out[cid] = set(candidate.get("selection_reasons") or [])
    return out


def candidate_entries(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    entries = parsed.get("candidate_explanations")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]
    return [parsed]


def evidence_weight_entries(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    entries = candidate.get("evidence_weights")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def reported_delta_consistent(
    *,
    reported_delta: float,
    computed_delta: float,
    tolerance: float = 0.015,
) -> bool:
    if not math.isfinite(reported_delta) or not math.isfinite(computed_delta):
        return False
    return abs(reported_delta - computed_delta) <= tolerance


def score_candidate(
    output_row: dict[str, Any],
    parsed: dict[str, Any],
    candidate: dict[str, Any],
    candidate_index: int,
) -> dict[str, Any]:
    metadata = output_row.get("metadata") or {}
    prior = as_float(metadata.get("before_p"))
    after = as_float(metadata.get("after_p"))
    posterior = as_float(candidate.get("posterior_probability"))
    confidence = as_float(candidate.get("confidence"))
    delta_from_prior = posterior - prior
    market_delta = after - prior
    baseline_error = abs(after - prior) if math.isfinite(after) and math.isfinite(prior) else math.nan

    selected_ids = candidate.get("selected_evidence_ids")
    if not isinstance(selected_ids, list):
        selected_ids = []
    selected_set = {str(item) for item in selected_ids}
    visible_ids = {str(item) for item in metadata.get("visible_evidence_ids") or []}
    weight_entries = evidence_weight_entries(candidate)
    weight_ids = {str(item.get("candidate_id", "")) for item in weight_entries}
    ignored_ids = candidate.get("ignored_evidence_ids")
    if not isinstance(ignored_ids, list):
        ignored_ids = []
    classes = [str(item) for item in candidate.get("explanation_classes") or []]
    reason_sets = candidate_reason_sets(metadata)

    top_posterior_ids = {cid for cid, reasons in reason_sets.items() if "top_posterior" in reasons}
    top_prior_ids = {cid for cid, reasons in reason_sets.items() if "top_prior" in reasons}
    posterior_top_k_ids = {cid for cid, reasons in reason_sets.items() if "posterior_top_k" in reasons}
    prior_top_k_ids = {cid for cid, reasons in reason_sets.items() if "prior_top_k" in reasons}
    random_ids = {cid for cid, reasons in reason_sets.items() if "random_candidate" in reasons}

    posterior_error = abs(posterior - after) if math.isfinite(posterior) and math.isfinite(after) else math.nan
    market_direction = sign_label(market_delta)
    explanation_direction = sign_label(delta_from_prior)
    reported_delta = as_float(candidate.get("delta_from_prior"))
    reported_direction = str(candidate.get("direction") or "").strip().lower()
    entries = candidate_entries(parsed)
    candidate_count = len(entries)
    expected_candidate_count = metadata.get("num_explanations")
    recommended_id = (
        (parsed.get("ensemble_summary") or {}).get("recommended_explanation_id", "")
        if isinstance(parsed.get("ensemble_summary"), dict)
        else ""
    )
    candidate_ids = {
        str(entry.get("explanation_id", f"E{index + 1}"))
        for index, entry in enumerate(entries)
    }

    schema_selected_ids_bound_ok = len(selected_ids) <= 5
    schema_weights_bound_ok = len(weight_entries) <= 5
    schema_selected_ids_visible_ok = selected_set <= visible_ids
    schema_weights_subset_ok = weight_ids <= selected_set
    schema_posterior_valid = math.isfinite(posterior) and 0.0 <= posterior <= 1.0
    schema_confidence_valid = math.isfinite(confidence) and 0.0 <= confidence <= 1.0
    schema_delta_consistent = reported_delta_consistent(
        reported_delta=reported_delta,
        computed_delta=delta_from_prior,
    )
    schema_direction_consistent = reported_direction in {"up", "down", "flat"} and (
        reported_direction == explanation_direction
    )
    schema_candidate_count_ok = (
        not isinstance(expected_candidate_count, int) or candidate_count == expected_candidate_count
    )
    schema_recommended_id_valid = not recommended_id or recommended_id in candidate_ids
    schema_valid = all(
        [
            schema_selected_ids_bound_ok,
            schema_weights_bound_ok,
            schema_selected_ids_visible_ok,
            schema_weights_subset_ok,
            schema_posterior_valid,
            schema_confidence_valid,
            schema_delta_consistent,
            schema_direction_consistent,
            schema_candidate_count_ok,
            schema_recommended_id_valid,
        ]
    )

    return {
        "custom_id": output_row.get("custom_id", ""),
        "status": output_row.get("status", ""),
        "explanation_id": candidate.get("explanation_id", f"E{candidate_index + 1}"),
        "candidate_index": candidate_index,
        "num_candidates_in_response": candidate_count,
        "pilot_row_id": metadata.get("pilot_row_id", ""),
        "row_bucket": metadata.get("row_bucket", ""),
        "category": metadata.get("category", ""),
        "evidence_regime": metadata.get("evidence_regime", ""),
        "prompt_variant": metadata.get("prompt_variant", ""),
        "generation_mode": metadata.get("generation_mode", ""),
        "sample_index": metadata.get("sample_index", ""),
        "prior": prior,
        "after": after,
        "posterior": posterior,
        "market_delta": market_delta,
        "explanation_delta": delta_from_prior,
        "reported_delta_from_prior": reported_delta,
        "reported_direction": reported_direction,
        "baseline_error": baseline_error,
        "posterior_error_to_market": posterior_error,
        "improvement_vs_persistence": baseline_error - posterior_error
        if math.isfinite(baseline_error) and math.isfinite(posterior_error)
        else math.nan,
        "delta_error": abs(delta_from_prior - market_delta)
        if math.isfinite(delta_from_prior) and math.isfinite(market_delta)
        else math.nan,
        "market_direction": market_direction,
        "explanation_direction": explanation_direction,
        "direction_match": explanation_direction == market_direction,
        "top_posterior_selected": bool(selected_set & top_posterior_ids),
        "top_prior_selected": bool(selected_set & top_prior_ids),
        "posterior_top_k_selected": bool(selected_set & posterior_top_k_ids),
        "prior_top_k_selected": bool(selected_set & prior_top_k_ids),
        "random_candidate_selected": bool(selected_set & random_ids),
        "selected_evidence_count": len(selected_ids),
        "evidence_weights_count": len(weight_entries),
        "ignored_evidence_count": len(ignored_ids),
        "selected_evidence_ids": "|".join(str(item) for item in selected_ids),
        "nonselected_evidence_summary": candidate.get("nonselected_evidence_summary", ""),
        "has_evidence_irrelevance": "evidence_irrelevance" in classes,
        "selected_with_irrelevance": bool(selected_ids) and "evidence_irrelevance" in classes,
        "explanation_classes": "|".join(classes),
        "magnitude": candidate.get("magnitude", ""),
        "confidence": confidence,
        "ensemble_recommended_explanation_id": (parsed.get("ensemble_summary") or {}).get(
            "recommended_explanation_id", ""
        )
        if isinstance(parsed.get("ensemble_summary"), dict)
        else "",
        "schema_selected_ids_bound_ok": schema_selected_ids_bound_ok,
        "schema_weights_bound_ok": schema_weights_bound_ok,
        "schema_selected_ids_visible_ok": schema_selected_ids_visible_ok,
        "schema_weights_subset_ok": schema_weights_subset_ok,
        "schema_posterior_valid": schema_posterior_valid,
        "schema_confidence_valid": schema_confidence_valid,
        "schema_delta_consistent": schema_delta_consistent,
        "schema_direction_consistent": schema_direction_consistent,
        "schema_candidate_count_ok": schema_candidate_count_ok,
        "schema_recommended_id_valid": schema_recommended_id_valid,
        "schema_valid": schema_valid,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--parsed-output", type=Path, default=DEFAULT_PARSED)
    parser.add_argument("--scores-output", type=Path, default=DEFAULT_SCORES)
    parser.add_argument("--errors-output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors_output = args.errors_output or args.parsed_output.with_suffix(".errors.jsonl")
    outputs = read_jsonl(args.outputs)
    parsed_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []

    for row in outputs:
        try:
            parsed = extract_json_object(str(row.get("content") or ""))
            entries = candidate_entries(parsed)
            if not entries:
                raise ValueError("no candidate explanations found")
            parsed_rows.append(
                {
                    "custom_id": row.get("custom_id", ""),
                    "metadata": row.get("metadata") or {},
                    "parsed": parsed,
                    "raw_content": row.get("content", ""),
                    "status": "parsed",
                    "candidate_count": len(entries),
                }
            )
            for candidate_index, candidate in enumerate(entries):
                score_rows.append(score_candidate(row, parsed, candidate, candidate_index))
        except Exception as exc:  # noqa: BLE001 - preserve parse failures for audit
            error_rows.append(
                {
                    "custom_id": row.get("custom_id", ""),
                    "metadata": row.get("metadata") or {},
                    "raw_content": row.get("content", ""),
                    "error": repr(exc),
                    "status": "parse_error",
                }
            )

    write_jsonl(args.parsed_output, parsed_rows)
    write_jsonl(errors_output, error_rows)
    args.scores_output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "custom_id",
        "status",
        "explanation_id",
        "candidate_index",
        "num_candidates_in_response",
        "pilot_row_id",
        "row_bucket",
        "category",
        "evidence_regime",
        "prompt_variant",
        "generation_mode",
        "sample_index",
        "prior",
        "after",
        "posterior",
        "market_delta",
        "explanation_delta",
        "reported_delta_from_prior",
        "reported_direction",
        "baseline_error",
        "posterior_error_to_market",
        "improvement_vs_persistence",
        "delta_error",
        "market_direction",
        "explanation_direction",
        "direction_match",
        "top_posterior_selected",
        "top_prior_selected",
        "posterior_top_k_selected",
        "prior_top_k_selected",
        "random_candidate_selected",
        "selected_evidence_count",
        "evidence_weights_count",
        "ignored_evidence_count",
        "selected_evidence_ids",
        "nonselected_evidence_summary",
        "has_evidence_irrelevance",
        "selected_with_irrelevance",
        "explanation_classes",
        "magnitude",
        "confidence",
        "ensemble_recommended_explanation_id",
        "schema_selected_ids_bound_ok",
        "schema_weights_bound_ok",
        "schema_selected_ids_visible_ok",
        "schema_weights_subset_ok",
        "schema_posterior_valid",
        "schema_confidence_valid",
        "schema_delta_consistent",
        "schema_direction_consistent",
        "schema_candidate_count_ok",
        "schema_recommended_id_valid",
        "schema_valid",
    ]
    with args.scores_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(score_rows)

    summary = {
        "outputs": str(args.outputs),
        "parsed_output": str(args.parsed_output),
        "scores_output": str(args.scores_output),
        "errors_output": str(errors_output),
        "input_rows": len(outputs),
        "parsed_rows": len(parsed_rows),
        "score_rows": len(score_rows),
        "parse_errors": len(error_rows),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
