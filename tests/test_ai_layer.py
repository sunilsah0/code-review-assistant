from app.ai.evidence_checker import verify_findings
from app.ai.finding_schema import Finding
from app.git.diff_parser import DiffLine, FileDiff
from app.pipeline import review_diff

DIFF = "--- a/app/x.py\n+++ b/app/x.py\n@@ -1 +1,2 @@\n def f(a, b):\n+    return a / b\n"


def ai_finding(**overrides) -> Finding:
    data = dict(
        file="app/x.py", line=2, severity="high", category="bug", title="Division by zero",
        explanation="b may be zero", evidence="return a / b", source="ai", confidence="likely",
    )
    data.update(overrides)
    return Finding(**data)


def files():
    return [FileDiff("app/x.py", added=[DiffLine(1, "def f(a, b):"), DiffLine(2, "    return a / b")])]


def test_evidence_checker_keeps_and_fixes_line():
    kept, dropped = verify_findings([ai_finding(line=1)], files())  # AI cited the wrong line
    assert len(kept) == 1 and not dropped
    assert kept[0].line == 2 and kept[0].evidence_verified


def test_evidence_checker_drops_invented_evidence():
    kept, dropped = verify_findings([ai_finding(evidence="os.system(cmd)")], files())
    assert not kept and len(dropped) == 1


def test_evidence_checker_drops_unknown_file():
    kept, dropped = verify_findings([ai_finding(file="other.py")], files())
    assert not kept and len(dropped) == 1


def test_pipeline_keeps_good_ai_and_drops_bad_ai(monkeypatch):
    fake = [ai_finding(), ai_finding(evidence="eval(secret)", line=2, title="Invented")]
    monkeypatch.setattr("app.pipeline.request_ai_findings", lambda f, k: (fake, ""))
    result = review_diff(DIFF, use_ai=True)
    ai = [f for f in result.findings if f.source == "ai"]
    assert [f.title for f in ai] == ["Division by zero"]
    assert ai[0].confidence == "likely" and ai[0].evidence_verified
    assert result.stats["ai_dropped"] == 1


def test_pipeline_without_ai_never_calls_the_model(monkeypatch):
    def boom(*args):
        raise AssertionError("AI must not be called")

    monkeypatch.setattr("app.pipeline.request_ai_findings", boom)
    assert review_diff(DIFF).stats["ai_enabled"] is False