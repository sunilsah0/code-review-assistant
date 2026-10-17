"""Score the reviewer against the labelled cases.

    python -m benchmark.run_benchmark

Matching rule: a finding is a true positive when it points at the same file and line as an
expected bug. Findings elsewhere are false positives. Expected bugs nobody found are misses.
Heuristic notes (source="heuristic") are only hints, so they are not scored.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from app.pipeline import review_diff

HERE = Path(__file__).parent
FILES = ["known_bugs.jsonl", "security_examples.jsonl", "harmless_changes.jsonl"]


def load_cases() -> list[dict]:
    cases = []
    for name in FILES:
        for line in (HERE / name).read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                case["set"] = name.replace(".jsonl", "")
                cases.append(case)
    return cases


def score() -> dict:
    tp = fp = fn = 0
    times: list[float] = []
    per_case, false_positives, missed = [], [], []
    for case in load_cases():
        result = review_diff(case["diff"])
        times.append(result.elapsed_ms)
        expected = {(e["file"], e["line"]) for e in case["expected"]}
        found = {(f.file, f.line) for f in result.findings if f.source != "heuristic"}
        case_tp = len(found & expected)
        case_fp = len(found - expected)
        case_fn = len(expected - found)
        tp, fp, fn = tp + case_tp, fp + case_fp, fn + case_fn
        if case_fp:
            false_positives.append(case["id"])
        if case_fn:
            missed.append(case["id"])
        per_case.append({"id": case["id"], "set": case["set"], "tp": case_tp, "fp": case_fp, "fn": case_fn})
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    ordered = sorted(times)
    return {
        "mode": "static-only",
        "cases": len(per_case), "true_positives": tp, "false_positives": fp, "missed": fn,
        "precision": round(precision, 3), "recall": round(recall, 3),
        "avg_ms": round(statistics.mean(times), 2),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 2),
        "cases_with_false_positives": false_positives, "cases_with_misses": missed,
        "per_case": per_case,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-precision", type=float, default=0.0)
    parser.add_argument("--min-recall", type=float, default=0.0)
    args = parser.parse_args()
    report = score()
    (HERE / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for key, value in report.items():
        if key != "per_case":
            print(f"{key:28} {value}")
    if report["precision"] < args.min_precision or report["recall"] < args.min_recall:
        print("FAILED: below the minimum thresholds")
        sys.exit(1)


if __name__ == "__main__":
    main()