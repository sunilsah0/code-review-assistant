import json

import pytest

from app.ai.finding_schema import Finding, parse_ai_response


def ai_json(**overrides) -> str:
    item = {
        "file": "app/x.py", "line": 2, "severity": "high", "category": "bug",
        "title": "t", "explanation": "e", "evidence": "return a / b",
        "suggested_test": "test it", "confidence": "likely",
    }
    item.update(overrides)
    return json.dumps({"findings": [item]})


def test_parse_valid_ai_response_marks_source_ai():
    finding = parse_ai_response("```json\n" + ai_json() + "\n```")[0]
    assert finding.source == "ai" and finding.confidence == "likely"


def test_ai_cannot_claim_confirmed():
    with pytest.raises(ValueError):
        parse_ai_response(ai_json(confidence="confirmed"))


def test_invalid_severity_and_line_rejected():
    with pytest.raises(ValueError):
        parse_ai_response(ai_json(severity="catastrophic"))
    with pytest.raises(ValueError):
        parse_ai_response(ai_json(line=0))


def test_garbage_is_rejected():
    with pytest.raises(ValueError):
        parse_ai_response("sorry, I cannot do that")


def test_finding_requires_valid_fields():
    with pytest.raises(ValueError):
        Finding(file="a.py", line=0, severity="low", category="bug", title="t",
                explanation="e", evidence="x", source="static")