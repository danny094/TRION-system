#!/usr/bin/env python3
"""Sweep conservative tool-selector thresholds against a golden set.

This script is intentionally offline from the runtime selector path.
It helps calibrate thresholds so false positives are punished harder than
false negatives.

Example:
    .venv/bin/python scripts/calibrate_tool_selector.py \
        --tools-json /tmp/tools.json \
        --golden-set tests/fixtures/tool_selector_golden_set.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.orchestrator.contracts import ToolDescriptor
from core.orchestrator.tools import list_available_tools
import core.orchestrator.tool_candidates.service as selector_service


@dataclass(frozen=True)
class ThresholdSet:
    low: float
    high: float
    lexical_min: int
    margin: float


def main() -> int:
    args = _parse_args()
    tools = _load_tools(args.tools_json)
    cases = _load_cases(args.golden_set)
    best, report = _evaluate_grid(
        tools,
        cases,
        low_values=args.low_values,
        high_values=args.high_values,
        lexical_values=args.lexical_values,
        margin_values=args.margin_values,
        false_positive_cost=args.false_positive_cost,
        false_negative_cost=args.false_negative_cost,
    )
    _print_report(best, report)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tools-json",
        type=Path,
        required=True,
        help="JSON array of raw tool descriptors as exported by the runtime.",
    )
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=ROOT / "tests" / "fixtures" / "tool_selector_golden_set.json",
        help="JSON golden set with query/expected_tools entries.",
    )
    parser.add_argument("--low-values", default="0.45,0.55,0.60")
    parser.add_argument("--high-values", default="0.75,0.80,0.85")
    parser.add_argument("--lexical-values", default="1,2,3")
    parser.add_argument("--margin-values", default="0.00,0.05,0.08,0.12")
    parser.add_argument("--false-positive-cost", type=int, default=5)
    parser.add_argument("--false-negative-cost", type=int, default=1)
    return parser.parse_args()


def _load_tools(path: Path) -> list[ToolDescriptor]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--tools-json must contain a JSON array")
    return list_available_tools(payload)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("--golden-set must contain a JSON array")
    return payload


def _evaluate_grid(
    tools: list[ToolDescriptor],
    cases: list[dict[str, Any]],
    *,
    low_values: str,
    high_values: str,
    lexical_values: str,
    margin_values: str,
    false_positive_cost: int,
    false_negative_cost: int,
) -> tuple[ThresholdSet, dict[str, Any]]:
    best_thresholds: ThresholdSet | None = None
    best_report: dict[str, Any] | None = None
    best_cost: int | None = None

    for thresholds in itertools.product(
        _float_values(low_values),
        _float_values(high_values),
        _int_values(lexical_values),
        _float_values(margin_values),
    ):
        low, high, lexical_min, margin = thresholds
        if high <= low:
            continue
        threshold_set = ThresholdSet(low=low, high=high, lexical_min=lexical_min, margin=margin)
        report = _run_cases(
            tools,
            cases,
            threshold_set,
            false_positive_cost=false_positive_cost,
            false_negative_cost=false_negative_cost,
        )
        cost = int(report["cost"])
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_thresholds = threshold_set
            best_report = report

    if best_thresholds is None or best_report is None:
        raise RuntimeError("No valid threshold combination could be evaluated")
    return best_thresholds, best_report


def _run_cases(
    tools: list[ToolDescriptor],
    cases: list[dict[str, Any]],
    threshold_set: ThresholdSet,
    *,
    false_positive_cost: int,
    false_negative_cost: int,
) -> dict[str, Any]:
    original = _capture_selector_policy()
    try:
        _apply_selector_policy(threshold_set)
        rows: list[dict[str, Any]] = []
        false_positives = 0
        false_negatives = 0
        true_positives = 0
        true_negatives = 0

        for case in cases:
            query = str(case.get("query") or "")
            expected = set(str(item) for item in case.get("expected_tools") or [])
            selected = [
                tool.name
                for tool in selector_service.select_top_k_tools(query, tools, top_k=5)
            ]
            selected_set = set(selected)
            fp = len(selected_set - expected)
            fn = len(expected - selected_set)
            if expected and selected_set == expected:
                true_positives += 1
            elif not expected and not selected_set:
                true_negatives += 1
            false_positives += fp
            false_negatives += fn
            rows.append(
                {
                    "query": query,
                    "expected_tools": sorted(expected),
                    "selected_tools": selected,
                    "false_positives": fp,
                    "false_negatives": fn,
                }
            )

        cost = false_positive_cost * false_positives + false_negative_cost * false_negatives
        return {
            "thresholds": threshold_set.__dict__,
            "cost": cost,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "rows": rows,
        }
    finally:
        _restore_selector_policy(original)


def _capture_selector_policy() -> dict[str, Any]:
    return {
        "get_tool_selector_min_similarity": selector_service.get_tool_selector_min_similarity,
        "get_tool_selector_high_similarity": selector_service.get_tool_selector_high_similarity,
        "get_tool_selector_lexical_support_min": selector_service.get_tool_selector_lexical_support_min,
        "get_tool_selector_ambiguity_margin": selector_service.get_tool_selector_ambiguity_margin,
    }


def _apply_selector_policy(threshold_set: ThresholdSet) -> None:
    selector_service.get_tool_selector_min_similarity = lambda: threshold_set.low
    selector_service.get_tool_selector_high_similarity = lambda: threshold_set.high
    selector_service.get_tool_selector_lexical_support_min = lambda: threshold_set.lexical_min
    selector_service.get_tool_selector_ambiguity_margin = lambda: threshold_set.margin


def _restore_selector_policy(original: dict[str, Any]) -> None:
    for name, value in original.items():
        setattr(selector_service, name, value)


def _float_values(raw: str) -> list[float]:
    return [float(value.strip()) for value in raw.split(",") if value.strip()]


def _int_values(raw: str) -> list[int]:
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


def _print_report(best: ThresholdSet, report: dict[str, Any]) -> None:
    print("Best thresholds:")
    print(f"  low={best.low:.2f}")
    print(f"  high={best.high:.2f}")
    print(f"  lexical_min={best.lexical_min}")
    print(f"  margin={best.margin:.2f}")
    print("")
    print("Summary:")
    print(f"  cost={report['cost']}")
    print(f"  false_positives={report['false_positives']}")
    print(f"  false_negatives={report['false_negatives']}")
    print(f"  true_positives={report['true_positives']}")
    print(f"  true_negatives={report['true_negatives']}")
    print("")
    print("Cases:")
    for row in report["rows"]:
        print(f"- query: {row['query']}")
        print(f"  expected: {row['expected_tools']}")
        print(f"  selected: {row['selected_tools']}")
        print(f"  fp={row['false_positives']} fn={row['false_negatives']}")


if __name__ == "__main__":
    raise SystemExit(main())
