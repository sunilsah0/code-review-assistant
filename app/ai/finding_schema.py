"""The shape of a review finding, plus validation of what the AI sends back."""
from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
Category = Literal["bug", "security", "style", "test-gap", "risky-change"]
Source = Literal["static", "heuristic", "ai"]
Confidence = Literal["confirmed", "likely", "uncertain"]

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class Finding(BaseModel):
    id: str = ""
    file: str
    line: int = Field(ge=1)
    severity: Severity
    category: Category
    title: str
    explanation: str
    evidence: str  # the exact code line from the diff that supports the finding
    source: Source  # static = tool rule, heuristic = rule of thumb, ai = LLM opinion
    rule_id: str | None = None
    confidence: Confidence = "uncertain"
    suggested_test: str | None = None
    evidence_verified: bool = False


class AIFinding(BaseModel):
    """What we ask the LLM to return for each issue (it may never say 'confirmed')."""

    file: str
    line: int = Field(ge=1)
    severity: Severity
    category: Category
    title: str
    explanation: str
    evidence: str
    suggested_test: str | None = None
    confidence: Literal["likely", "uncertain"] = "uncertain"


class AIReviewResponse(BaseModel):
    findings: list[AIFinding] = []


class ReviewResult(BaseModel):
    files_reviewed: list[str]
    findings: list[Finding]
    notes: list[str] = []
    stats: dict[str, Any] = {}
    elapsed_ms: float = 0.0


def parse_ai_response(text: str) -> list[Finding]:
    """Parse the LLM's JSON answer. Raises ValueError if it is not valid."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON ({exc.msg})") from exc
    response = AIReviewResponse.model_validate(payload)
    return [
        Finding(
            file=item.file,
            line=item.line,
            severity=item.severity,
            category=item.category,
            title=item.title,
            explanation=item.explanation,
            evidence=item.evidence,
            source="ai",
            confidence=item.confidence,
            suggested_test=item.suggested_test,
        )
        for item in response.findings
    ]