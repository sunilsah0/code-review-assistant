"""The review pipeline: parse diff -> static checks -> heuristics -> sorted report."""
from __future__ import annotations

import time

from app.ai.finding_schema import SEVERITY_RANK, Finding, ReviewResult
from app.analysis.change_impact import analyze_change_impact
from app.analysis.dependency_analysis import analyze_dependencies
from app.analysis.static_analysis import run_static_analysis
from app.git.diff_parser import parse_diff

MAX_DIFF_CHARS = 500_000


def review_diff(diff_text: str, file_contents: dict[str, str] | None = None) -> ReviewResult:
    start = time.perf_counter()
    if len(diff_text) > MAX_DIFF_CHARS:
        raise ValueError(f"diff is too large (limit {MAX_DIFF_CHARS} characters)")
    files = parse_diff(diff_text)
    notes: list[str] = []
    if not files:
        notes.append("No files found. Is this a unified diff (output of `git diff`)?")

    findings: list[Finding] = run_static_analysis(files, file_contents)
    findings += analyze_dependencies(files)
    findings += analyze_change_impact(files)

    findings.sort(key=lambda f: (SEVERITY_RANK[f.severity], f.file, f.line))
    for number, finding in enumerate(findings, start=1):
        finding.id = f"F{number:03d}"

    stats = {
        "static": sum(f.source == "static" for f in findings),
        "heuristic": sum(f.source == "heuristic" for f in findings),
    }
    return ReviewResult(
        files_reviewed=[f.path for f in files],
        findings=findings,
        notes=notes,
        stats=stats,
        elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
    )