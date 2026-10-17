"""Generate the JSONL benchmark files:  python -m benchmark.build_dataset"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from benchmark.cases_source import DATASETS

MARKER = re.compile(r"\s*#@expect:([\w-]+)\s*$")
HERE = Path(__file__).parent


def make_case(case: dict) -> dict:
    expected, new_lines = [], []
    for number, line in enumerate(case["new"].splitlines(), start=1):
        match = MARKER.search(line)
        if match:
            expected.append({"file": case["path"], "line": number, "category": match.group(1)})
            line = MARKER.sub("", line)
        new_lines.append(line)
    old_lines = case["old"].splitlines()
    body = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"a/{case['path']}", tofile=f"b/{case['path']}",
        lineterm="", n=3,
    )
    diff = f"diff --git a/{case['path']} b/{case['path']}\n" + "\n".join(body) + "\n"
    return {"id": case["id"], "description": case["description"], "diff": diff, "expected": expected}


def main() -> None:
    all_diffs = []
    for name, cases in DATASETS.items():
        rows = [make_case(c) for c in cases]
        (HERE / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        print(f"wrote {name}: {len(rows)} cases")
        all_diffs += [r["diff"] for r in rows[:3]]
    samples = HERE.parent / "samples"
    samples.mkdir(exist_ok=True)
    (samples / "demo.diff").write_text("".join(all_diffs), encoding="utf-8")
    print("wrote samples/demo.diff")


if __name__ == "__main__":
    main()