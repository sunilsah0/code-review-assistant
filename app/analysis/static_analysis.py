"""Static analysis: fast built-in rules, plus Ruff and Semgrep when they are installed.

Anything reported here is source="static" and confidence="confirmed":
a tool rule matched, no AI opinion involved.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.ai.finding_schema import Category, Finding, Severity
from app.git.diff_parser import FileDiff


@dataclass
class Rule:
    id: str
    pattern: re.Pattern[str]
    severity: Severity
    category: Category
    title: str
    explanation: str
    suggested_test: str


def _rule(id, pattern, severity, category, title, explanation, test) -> Rule:
    return Rule(id, re.compile(pattern), severity, category, title, explanation, test)


RULES: list[Rule] = [
    _rule(
        "hardcoded-secret",
        r"(?i)\b\w*(password|passwd|secret|api[_-]?key|token)\w*\s*=\s*['\"][^'\"\s]{8,}['\"]",
        "high", "security", "Possible hardcoded secret",
        "A credential-like value is written directly in the code. Anyone with repo access can read it.",
        "Assert the value is loaded from an environment variable or secret store, not a literal.",
    ),
    _rule(
        "use-of-eval", r"\b(eval|exec)\s*\(",
        "high", "security", "Use of eval/exec",
        "eval/exec run arbitrary code. With user-controlled input this allows code execution.",
        "Test with malicious input such as \"__import__('os').system('id')\" and expect rejection.",
    ),
    _rule(
        "shell-true", r"subprocess\.\w+\(.*shell\s*=\s*True",
        "high", "security", "subprocess call with shell=True",
        "shell=True lets special characters in the command string be interpreted by the shell (command injection).",
        "Test with an argument like '; echo hacked' and assert no extra command runs.",
    ),
    _rule(
        "sql-string-building",
        r"\.execute\(\s*(f['\"]|.*['\"]\s*(%|\+)\s*\w|.*\.format\()",
        "high", "security", "SQL built from strings",
        "Building SQL with string formatting allows SQL injection. Use parameterised queries.",
        "Test with the input \"' OR '1'='1\" and assert it is treated as plain data.",
    ),
    _rule(
        "bare-except", r"^\s*except\s*:",
        "medium", "bug", "Bare except hides errors",
        "A bare 'except:' also catches KeyboardInterrupt/SystemExit and silently hides real bugs.",
        "Test that an unexpected error inside the try block is raised or logged, not swallowed.",
    ),
    _rule(
        "mutable-default-arg", r"\bdef\s+\w+\(.*=\s*(\[\]|\{\}|set\(\))",
        "medium", "bug", "Mutable default argument",
        "A list/dict default is created once and shared between calls, so data leaks between calls.",
        "Call the function twice without the argument and assert the second result is not polluted.",
    ),
    _rule(
        "is-literal-compare", r"\b(is|is not)\s+(['\"]|-?\d)",
        "medium", "bug", "Identity comparison with a literal",
        "'is' checks object identity, not equality. Comparing to a string/number literal is unreliable.",
        "Test with an equal value built at runtime (e.g. ''.join(['ac','tive'])) and assert it matches.",
    ),
    _rule(
        "pickle-load", r"\bpickle\.loads?\(",
        "high", "security", "Unsafe deserialisation with pickle",
        "Unpickling untrusted data can execute arbitrary code.",
        "Test that untrusted bytes are rejected, or use a safe format such as JSON.",
    ),
    _rule(
        "yaml-unsafe-load", r"\byaml\.load\((?!.*Loader)",
        "high", "security", "yaml.load without a safe Loader",
        "yaml.load can construct arbitrary Python objects. Use yaml.safe_load.",
        "Test that a YAML document containing a python object tag is rejected.",
    ),
    _rule(
        "weak-hash", r"hashlib\.(md5|sha1)\(",
        "medium", "security", "Weak hash function",
        "MD5/SHA-1 are broken for security use (passwords, signatures). Use a modern password hash.",
        "Test that stored password hashes use bcrypt/argon2/scrypt.",
    ),
    _rule(
        "tls-verify-disabled", r"verify\s*=\s*False",
        "high", "security", "TLS certificate verification disabled",
        "verify=False makes HTTPS connections vulnerable to man-in-the-middle attacks.",
        "Test that a request to a host with an invalid certificate fails.",
    ),
    _rule(
        "debug-enabled", r"(?i)\bdebug\s*=\s*True",
        "low", "risky-change", "Debug mode enabled",
        "Debug mode can leak internal details in production.",
        "Test that the production config has debug disabled.",
    ),
]


def _is_comment(text: str) -> bool:
    return text.strip().startswith("#")


def run_builtin_rules(files: list[FileDiff]) -> list[Finding]:
    findings: list[Finding] = []
    for file in files:
        if not file.is_python or file.is_deleted:
            continue
        for line in file.added:
            if _is_comment(line.text):
                continue
            for rule in RULES:
                if rule.pattern.search(line.text):
                    findings.append(
                        Finding(
                            file=file.path, line=line.number, severity=rule.severity,
                            category=rule.category, title=rule.title,
                            explanation=rule.explanation, evidence=line.text.strip(),
                            source="static", rule_id=rule.id, confidence="confirmed",
                            suggested_test=rule.suggested_test, evidence_verified=True,
                        )
                    )
    return findings


def run_ruff(path: str, content: str, added: dict[int, str]) -> list[Finding]:
    """Run Ruff on the FULL new version of a file; keep only issues on added lines."""
    if shutil.which("ruff") is None:
        return []
    try:
        proc = subprocess.run(
            ["ruff", "check", "--select", "E9,F,B,S", "--output-format", "json",
             "--stdin-filename", path, "-"],
            input=content, capture_output=True, text=True, timeout=30,
        )
        items = json.loads(proc.stdout or "[]")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return []
    findings = []
    for item in items:
        row = item.get("location", {}).get("row", 0)
        if row not in added:
            continue
        code = item.get("code") or "ruff"
        findings.append(
            Finding(
                file=path, line=row, severity="medium",
                category="security" if code.startswith("S") else "bug",
                title=f"Ruff {code}", explanation=item.get("message", ""),
                evidence=added[row].strip(), source="static", rule_id=f"ruff:{code}",
                confidence="confirmed", evidence_verified=True,
            )
        )
    return findings


def run_semgrep(path: str, content: str, added: dict[int, str]) -> list[Finding]:
    """Optional. Needs `pip install semgrep`; some configs (like p/python) need internet."""
    if shutil.which("semgrep") is None:
        return []
    config = os.getenv("SEMGREP_CONFIG", "p/python")
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / Path(path).name
        target.write_text(content, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["semgrep", "--config", config, "--json", "--quiet", str(target)],
                capture_output=True, text=True, timeout=90,
            )
            results = json.loads(proc.stdout or "{}").get("results", [])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            return []
    findings = []
    for item in results:
        row = item.get("start", {}).get("line", 0)
        if row not in added:
            continue
        extra = item.get("extra", {})
        findings.append(
            Finding(
                file=path, line=row, severity="medium", category="security",
                title=f"Semgrep: {item.get('check_id', 'rule').split('.')[-1]}",
                explanation=extra.get("message", ""), evidence=added[row].strip(),
                source="static", rule_id=f"semgrep:{item.get('check_id')}",
                confidence="confirmed", evidence_verified=True,
            )
        )
    return findings


def run_static_analysis(
    files: list[FileDiff], file_contents: dict[str, str] | None = None
) -> list[Finding]:
    findings = run_builtin_rules(files)
    seen = {(f.file, f.line) for f in findings}
    for file in files:
        content = (file_contents or {}).get(file.path)
        if content is None or not file.is_python:
            continue
        added = {line.number: line.text for line in file.added}
        for extra in run_ruff(file.path, content, added) + run_semgrep(file.path, content, added):
            if (extra.file, extra.line) not in seen:  # don't report the same line twice
                seen.add((extra.file, extra.line))
                findings.append(extra)
    return findings