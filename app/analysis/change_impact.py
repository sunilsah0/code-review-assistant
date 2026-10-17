"""Rule-of-thumb notes about how risky a change looks. These are hints (source="heuristic"),
not proof, so they are never marked "confirmed"."""
from __future__ import annotations

import re

from app.ai.finding_schema import Finding
from app.git.diff_parser import FileDiff

SENSITIVE_PATH = re.compile(r"auth|security|payment|crypto|permission|login|session", re.I)
SAFETY_WORDS = re.compile(
    r"\b(raise|assert|validate|verify|authorize|authenticate|permission|is_admin|sanitize)\w*", re.I
)
LARGE_CHANGE_LINES = 400


def analyze_change_impact(files: list[FileDiff]) -> list[Finding]:
    findings: list[Finding] = []
    source_files = [f for f in files if f.is_python and not f.is_test and not f.is_deleted and f.added]
    if source_files and not any(f.is_test for f in files):
        first = source_files[0]
        findings.append(
            Finding(
                file=first.path, line=first.added[0].number, severity="low", category="test-gap",
                title="Source changed but no tests changed",
                explanation="This change touches Python source files, but no test file is part of it.",
                evidence=first.added[0].text.strip(), source="heuristic", confidence="uncertain",
                suggested_test="Add or update a test that covers the new behaviour.",
                evidence_verified=True,
            )
        )
    for file in files:
        for line in file.removed:
            if file.is_python and not file.is_test and SAFETY_WORDS.search(line.text):
                findings.append(
                    Finding(
                        file=file.path, line=line.number, severity="medium", category="risky-change",
                        title="A check or validation was removed (line number refers to the OLD file)",
                        explanation="Removed code looks like input validation, an assertion or a permission check.",
                        evidence=line.text.strip(), source="heuristic", confidence="likely",
                        suggested_test="Add a test that sends invalid input or an unauthorised user and expects a failure.",
                        evidence_verified=True,
                    )
                )
        if SENSITIVE_PATH.search(file.path) and file.added:
            findings.append(
                Finding(
                    file=file.path, line=file.added[0].number, severity="low", category="risky-change",
                    title="Change touches a sensitive area",
                    explanation="The file path suggests authentication, payments, crypto or permissions. Review with extra care.",
                    evidence=file.added[0].text.strip(), source="heuristic", confidence="uncertain",
                    evidence_verified=True,
                )
            )
        if len(file.added) > LARGE_CHANGE_LINES:
            findings.append(
                Finding(
                    file=file.path, line=file.added[0].number, severity="low", category="risky-change",
                    title=f"Very large change ({len(file.added)} added lines)",
                    explanation="Large changes are hard to review and more likely to hide bugs. Consider splitting.",
                    evidence=file.added[0].text.strip(), source="heuristic", confidence="uncertain",
                    evidence_verified=True,
                )
            )
    return findings