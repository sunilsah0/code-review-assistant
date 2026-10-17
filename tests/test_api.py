from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
BAD_DIFF = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a = 1\n+a = eval(input())\n"


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_review_text():
    r = client.post("/reviews", json={"diff": BAD_DIFF})
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert any(f["rule_id"] == "use-of-eval" and f["source"] == "static" for f in findings)


def test_review_upload_markdown():
    r = client.post("/reviews/upload?format=markdown",
                    files={"file": ("p.patch", BAD_DIFF.encode(), "text/plain")})
    assert r.status_code == 200 and "Confirmed by static analysis" in r.text