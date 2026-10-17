"""Prompt text for the LLM. The model only ever sees the diff, never your machine."""
from __future__ import annotations

from app.ai.finding_schema import Finding
from app.git.diff_parser import FileDiff

MAX_PROMPT_CHARS = 24_000

SYSTEM_PROMPT = """You are a cautious senior code reviewer.
You will receive the ADDED lines of a pull request, each prefixed with its line number
(for example "L12: some code"), plus issues that static tools already found.

Rules:
1. Report only real problems visible in the added lines: bugs, security risks, missing
   error handling, risky behaviour changes. Do NOT report style nitpicks.
2. Do NOT repeat issues already listed under "Known findings".
3. Every finding must cite a line number that exists in the input, and "evidence" must be
   copied EXACTLY from that line.
4. If you are not sure, set "confidence" to "uncertain". Never claim certainty.
5. For each finding suggest one concrete pytest-style test idea in "suggested_test".
6. You only review. You never propose to run or execute anything.
7. If there is nothing worth reporting, return {"findings": []}.

Return ONLY a JSON object, no markdown, in exactly this shape:
{"findings": [{"file": "path.py", "line": 12, "severity": "low|medium|high|critical",
"category": "bug|security|style|test-gap|risky-change", "title": "short title",
"explanation": "why this is a problem", "evidence": "exact code from the line",
"suggested_test": "test idea", "confidence": "likely|uncertain"}]}"""


def build_user_prompt(files: list[FileDiff], known: list[Finding]) -> str:
    parts: list[str] = []
    for file in files:
        if not file.added or file.is_deleted:
            continue
        parts.append(f"FILE: {file.path}")
        parts.extend(f"L{line.number}: {line.text}" for line in file.added)
        parts.append("")
    if known:
        parts.append("Known findings (do not repeat):")
        parts.extend(f"- {f.file}:{f.line} {f.title}" for f in known)
    text = "\n".join(parts)
    if len(text) > MAX_PROMPT_CHARS:
        text = text[:MAX_PROMPT_CHARS] + "\n[truncated]"
    return text