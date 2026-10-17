"""Turn a unified diff (text) into simple Python objects.

For every file we keep:
  - ADDED lines, with their line number in the NEW file
  - REMOVED lines, with their line number in the OLD file
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches headers like:  @@ -1,3 +1,4 @@
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class DiffLine:
    number: int
    text: str


@dataclass
class FileDiff:
    path: str
    added: list[DiffLine] = field(default_factory=list)
    removed: list[DiffLine] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    hunk_count: int = 0

    @property
    def added_numbers(self) -> set[int]:
        return {line.number for line in self.added}

    @property
    def is_python(self) -> bool:
        return self.path.endswith(".py")

    @property
    def is_test(self) -> bool:
        name = self.path.lower().split("/")[-1]
        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or "/tests/" in "/" + self.path.lower()
        )


def _clean_path(raw: str) -> str:
    raw = raw.split("\t")[0].strip()
    if raw.startswith(("a/", "b/")):
        raw = raw[2:]
    return raw


def parse_diff(diff_text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    old_path: str | None = None
    old_no = new_no = old_left = new_left = 0

    for raw in diff_text.splitlines():
        # 1) Inside a hunk: the numbers in the @@ header tell us when it ends.
        if (old_left > 0 or new_left > 0) and current is not None:
            if raw.startswith("+"):
                current.added.append(DiffLine(new_no, raw[1:]))
                new_no += 1
                new_left -= 1
            elif raw.startswith("-"):
                current.removed.append(DiffLine(old_no, raw[1:]))
                old_no += 1
                old_left -= 1
            elif raw.startswith("\\"):
                pass  # "\ No newline at end of file"
            else:  # unchanged context line
                old_no += 1
                new_no += 1
                old_left -= 1
                new_left -= 1
            continue

        # 2) Header lines
        if raw.startswith("diff --git "):
            match = re.match(r"diff --git a/(.+?) b/(.+)$", raw)
            current = FileDiff(match.group(2) if match else "unknown")
            files.append(current)
            old_path = None
        elif raw.startswith("new file mode") and current is not None:
            current.is_new = True
        elif raw.startswith("deleted file mode") and current is not None:
            current.is_deleted = True
        elif raw.startswith("--- "):
            old_path = _clean_path(raw[4:])
        elif raw.startswith("+++ "):
            new_path = _clean_path(raw[4:])
            if current is None or current.hunk_count > 0:
                current = FileDiff(new_path)
                files.append(current)
            if new_path == "/dev/null":
                current.is_deleted = True
                current.path = old_path or current.path
            else:
                current.path = new_path
            if old_path == "/dev/null":
                current.is_new = True
        else:
            match = HUNK_RE.match(raw)
            if match and current is not None:
                current.hunk_count += 1
                old_no = int(match.group(1))
                old_left = int(match.group(2)) if match.group(2) is not None else 1
                new_no = int(match.group(3))
                new_left = int(match.group(4)) if match.group(4) is not None else 1

    return files