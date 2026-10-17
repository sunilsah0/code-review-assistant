"""Guard against hallucinations: keep an AI finding only if its quoted evidence
really appears in the diff, at (or very near) the line the AI cited."""
from __future__ import annotations

from app.ai.finding_schema import Finding
from app.git.diff_parser import FileDiff

LINE_TOLERANCE = 3


def _norm(text: str) -> str:
    return " ".join(text.split())


def verify_findings(
    findings: list[Finding], files: list[FileDiff]
) -> tuple[list[Finding], list[Finding]]:
    """Return (kept, dropped). Kept findings get the corrected line + evidence_verified."""
    by_path = {f.path: f for f in files}
    kept: list[Finding] = []
    dropped: list[Finding] = []
    for finding in findings:
        file = by_path.get(finding.file)
        evidence = _norm(finding.evidence)
        if file is None or len(evidence) < 3:
            dropped.append(finding)
            continue
        nearby = sorted(
            (ln for ln in file.added if abs(ln.number - finding.line) <= LINE_TOLERANCE),
            key=lambda ln: abs(ln.number - finding.line),
        )
        match = next((ln for ln in nearby if evidence in _norm(ln.text)), None)
        if match is None:
            dropped.append(finding)
            continue
        finding.line = match.number
        finding.evidence = match.text.strip()
        finding.evidence_verified = True
        kept.append(finding)
    return kept, dropped