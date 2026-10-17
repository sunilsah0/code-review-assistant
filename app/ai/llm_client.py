"""Asks a FREE local AI model (through Ollama) for extra review comments.

Ollama runs on your own computer, so there is no account, no API key and no cost.
If Ollama is not running, the review simply continues without AI.
"""
from __future__ import annotations

import os

from app.ai.finding_schema import Finding, parse_ai_response
from app.ai.review_prompts import SYSTEM_PROMPT, build_user_prompt
from app.git.diff_parser import FileDiff

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "qwen2.5-coder:7b"


def request_ai_findings(
    files: list[FileDiff], known: list[Finding]
) -> tuple[list[Finding], str]:
    """Return (findings, note). The note explains why AI was skipped or ignored."""
    prompt = build_user_prompt(files, known)
    if not prompt.strip():
        return [], ""
    model = os.getenv("REVIEW_MODEL", DEFAULT_MODEL)
    try:
        import httpx

        response = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
            timeout=600,
        )
        response.raise_for_status()
        text = response.json()["message"]["content"]
    except Exception as exc:  # never crash the whole review because of the AI part
        return [], (
            f"AI review skipped ({type(exc).__name__}). Is Ollama running, and did you run "
            f"'ollama pull {model}'? Showing static results only."
        )
    try:
        return parse_ai_response(text), ""
    except ValueError as exc:
        return [], f"AI answer was not valid structured output and was ignored: {exc}"