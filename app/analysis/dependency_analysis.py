"""Look at changes to requirements files."""
from __future__ import annotations

import re

from app.ai.finding_schema import Finding
from app.git.diff_parser import FileDiff

REQ_RE = re.compile(r"^([A-Za-z0-9_.\-]+)(\[[^\]]+\])?\s*(.*)$")


def analyze_dependencies(files: list[FileDiff]) -> list[Finding]:
    findings: list[Finding] = []
    for file in files:
        name = file.path.lower().split("/")[-1]
        if not (name.startswith("requirements") and name.endswith(".txt")):
            continue
        for line in file.added:
            text = line.text.strip()
            if not text or text.startswith(("#", "-", "git+", "http")):
                continue
            match = REQ_RE.match(text)
            if match and "==" not in match.group(3):
                findings.append(
                    Finding(
                        file=file.path, line=line.number, severity="low",
                        category="risky-change", title="Unpinned dependency",
                        explanation=f"'{match.group(1)}' is not pinned with '=='. Builds can "
                        "change or break when a new release appears, and it is harder to audit.",
                        evidence=text, source="static", rule_id="unpinned-dependency",
                        confidence="confirmed",
                        suggested_test="Add a CI step that installs from the pinned file and runs the tests.",
                        evidence_verified=True,
                    )
                )
    return findings