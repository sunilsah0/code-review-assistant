"""Turn a ReviewResult into a readable Markdown report."""
from __future__ import annotations

from app.ai.finding_schema import ReviewResult

SECTIONS = [
    ("Confirmed by static analysis", "static"),
    ("AI suggestions (verify before acting)", "ai"),
    ("Heuristic notes (rules of thumb, not proof)", "heuristic"),
]


def render_markdown(result: ReviewResult) -> str:
    out = ["# Code review report", ""]
    out.append(f"Files reviewed: {', '.join(result.files_reviewed) or 'none'}")
    out.append(f"Findings: {len(result.findings)} | Time: {result.elapsed_ms:.0f} ms")
    out.append("")
    for note in result.notes:
        out.append(f"> Note: {note}")
    if result.notes:
        out.append("")
    if not result.findings:
        out.append("No findings. This does not prove the change is bug-free.")
    for title, source in SECTIONS:
        items = [f for f in result.findings if f.source == source]
        if not items:
            continue
        out += [f"## {title}", ""]
        for f in items:
            out.append(f"### {f.id} [{f.severity}] {f.title}")
            out.append(f"`{f.file}:{f.line}`  | category: {f.category} | confidence: {f.confidence}")
            out += ["", f.explanation, "", "Evidence:", "```", f.evidence, "```"]
            if f.suggested_test:
                out.append(f"Suggested test: {f.suggested_test}")
            out.append("")
    tests = [f for f in result.findings if f.suggested_test]
    if tests:
        out += ["## Suggested tests", ""]
        out += [f"- {f.id}: {f.suggested_test}" for f in tests]
        out.append("")
    out.append("_This review is advisory. Nothing was changed or executed._")
    return "\n".join(out)