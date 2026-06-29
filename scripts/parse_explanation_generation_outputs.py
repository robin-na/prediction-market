#!/usr/bin/env python3
"""Parse and lightly score explanation-generation outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


DEFAULT_OUTPUTS = Path("data/derived/explanation_pilot/outputs/gemma4_26b_smoke5_outputs.jsonl")
DEFAULT_PARSED = Path("data/derived/explanation_pilot/outputs/gemma4_26b_smoke5_parsed.jsonl")
DEFAULT_SCORES = Path("data/derived/explanation_pilot/outputs/gemma4_26b_smoke5_scores.csv")
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

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found")
    parsed = json_loads_lenient(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("parsed JSON is not an object")
    return parsed


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


def score_row(output_row: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    metadata = output_row.get("metadata") or {}
    prior = as_float(metadata.get("before_p"))
    after = as_float(metadata.get("after_p"))
    posterior = as_float(parsed.get("posterior_probability"))
    delta_from_prior = posterior - prior
    market_delta = after - prior
    selected_ids = parsed.get("selected_evidence_ids")
    if not isinstance(selected_ids, list):
        selected_ids = []
    selected_set = {str(item) for item in selected_ids}
    ignored_ids = parsed.get("ignored_evidence_ids")
    if not isinstance(ignored_ids, list):
        ignored_ids = []
    classes = [str(item) for item in parsed.get("explanation_classes") or []]
    reason_sets = candidate_reason_sets(metadata)

    top_posterior_ids = {cid for cid, reasons in reason_sets.items() if "top_posterior" in reasons}
    top_prior_ids = {cid for cid, reasons in reason_sets.items() if "top_prior" in reasons}
    hard_negative_ids = {cid for cid, reasons in reason_sets.items() if "lexical_hard_negative" in reasons}

    market_direction = sign_label(market_delta)
    explanation_direction = sign_label(delta_from_prior)
    return {
        "custom_id": output_row.get("custom_id", ""),
        "status": output_row.get("status", ""),
        "pilot_row_id": metadata.get("pilot_row_id", ""),
        "row_bucket": metadata.get("row_bucket", ""),
        "category": metadata.get("category", ""),
        "evidence_regime": metadata.get("evidence_regime", ""),
        "prompt_variant": metadata.get("prompt_variant", ""),
        "sample_index": metadata.get("sample_index", ""),
        "prior": prior,
        "after": after,
        "posterior": posterior,
        "market_delta": market_delta,
        "explanation_delta": delta_from_prior,
        "delta_error": abs(delta_from_prior - market_delta)
        if math.isfinite(delta_from_prior) and math.isfinite(market_delta)
        else math.nan,
        "posterior_error_to_market": abs(posterior - after)
        if math.isfinite(posterior) and math.isfinite(after)
        else math.nan,
        "market_direction": market_direction,
        "explanation_direction": explanation_direction,
        "direction_match": explanation_direction == market_direction,
        "top_posterior_selected": bool(selected_set & top_posterior_ids),
        "top_prior_selected": bool(selected_set & top_prior_ids),
        "hard_negative_selected": bool(selected_set & hard_negative_ids),
        "selected_evidence_count": len(selected_ids),
        "ignored_evidence_count": len(ignored_ids),
        "selected_evidence_ids": "|".join(str(item) for item in selected_ids),
        "has_evidence_irrelevance": "evidence_irrelevance" in classes,
        "selected_with_irrelevance": bool(selected_ids) and "evidence_irrelevance" in classes,
        "explanation_classes": "|".join(classes),
        "magnitude": parsed.get("magnitude", ""),
        "confidence": as_float(parsed.get("confidence")),
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
            parsed_row = {
                "custom_id": row.get("custom_id", ""),
                "metadata": row.get("metadata") or {},
                "parsed": parsed,
                "raw_content": row.get("content", ""),
                "status": "parsed",
            }
            parsed_rows.append(parsed_row)
            score_rows.append(score_row(row, parsed))
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
        "pilot_row_id",
        "row_bucket",
        "category",
        "evidence_regime",
        "prompt_variant",
        "sample_index",
        "prior",
        "after",
        "posterior",
        "market_delta",
        "explanation_delta",
        "delta_error",
        "posterior_error_to_market",
        "market_direction",
        "explanation_direction",
        "direction_match",
        "top_posterior_selected",
        "top_prior_selected",
        "hard_negative_selected",
        "selected_evidence_count",
        "ignored_evidence_count",
        "selected_evidence_ids",
        "has_evidence_irrelevance",
        "selected_with_irrelevance",
        "explanation_classes",
        "magnitude",
        "confidence",
    ]
    with args.scores_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in score_rows:
            writer.writerow(row)

    summary = {
        "outputs": str(args.outputs),
        "parsed_output": str(args.parsed_output),
        "scores_output": str(args.scores_output),
        "errors_output": str(errors_output),
        "input_rows": len(outputs),
        "parsed_rows": len(parsed_rows),
        "parse_errors": len(error_rows),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
