from app.analysis.dependency_analysis import analyze_dependencies
from app.analysis.static_analysis import run_builtin_rules
from app.git.diff_parser import DiffLine, FileDiff


def make_file(*lines: str, path: str = "app/x.py") -> FileDiff:
    return FileDiff(path=path, added=[DiffLine(i, t) for i, t in enumerate(lines, start=1)])


def rule_ids(*lines: str) -> set[str]:
    return {f.rule_id for f in run_builtin_rules([make_file(*lines)])}


def test_each_rule_fires():
    assert "use-of-eval" in rule_ids("return eval(text)")
    assert "bare-except" in rule_ids("except:")
    assert "mutable-default-arg" in rule_ids("def f(a, b=[]):")
    assert "hardcoded-secret" in rule_ids('API_KEY = "sk_live_1234567890"')
    assert "sql-string-building" in rule_ids("cursor.execute(f\"SELECT {x}\")")
    assert "shell-true" in rule_ids("subprocess.run(cmd, shell=True)")
    assert "pickle-load" in rule_ids("obj = pickle.loads(blob)")
    assert "weak-hash" in rule_ids("hashlib.md5(b'x')")
    assert "tls-verify-disabled" in rule_ids("requests.get(u, verify=False)")
    assert "is-literal-compare" in rule_ids('if name is "bob":')


def test_safe_code_is_not_flagged():
    assert not rule_ids('cursor.execute("SELECT * FROM t WHERE id = %s", (i,))')
    assert not rule_ids('API_KEY = os.environ["API_KEY"]')
    assert not rule_ids("data = yaml.safe_load(text)")
    assert not rule_ids("if value is None:")
    assert not rule_ids("# never call eval(x)")


def test_findings_are_confirmed_static_with_exact_evidence():
    finding = run_builtin_rules([make_file("x = 1", "y = eval(z)")])[0]
    assert finding.source == "static" and finding.confidence == "confirmed"
    assert finding.line == 2 and finding.evidence == "y = eval(z)"


def test_non_python_files_are_ignored_by_builtin_rules():
    assert run_builtin_rules([make_file("eval(x)", path="README.md")]) == []


def test_unpinned_dependency():
    req = make_file("requests", "flask==3.0.0", "# comment", path="requirements.txt")
    findings = analyze_dependencies([req])
    assert len(findings) == 1 and findings[0].evidence == "requests"