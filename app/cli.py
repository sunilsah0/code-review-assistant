"""Command line use:  python -m app.cli changes.diff [--json]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.pipeline import review_diff
from app.reports.review_report import render_markdown


def read_text(path: str) -> str:
    """Read a diff file. Handles the odd encodings Windows PowerShell can produce."""
    raw = Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):  # UTF-16 (PowerShell '>' redirect)
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")  # also strips a BOM if present


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a unified diff (advisory only).")
    parser.add_argument("diff_file", help="path to a .diff/.patch file, or - for stdin")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = parser.parse_args()
    text = sys.stdin.read() if args.diff_file == "-" else read_text(args.diff_file)
    result = review_diff(text)
    print(result.model_dump_json(indent=2) if args.json else render_markdown(result))


if __name__ == "__main__":
    main()