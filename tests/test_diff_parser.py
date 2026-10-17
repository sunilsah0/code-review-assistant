from app.git.diff_parser import parse_diff

TWO_FILES = """diff --git a/app/a.py b/app/a.py
--- a/app/a.py
+++ b/app/a.py
@@ -1,3 +1,4 @@
 import os
-x = 1
+x = 2
+y = 3
 print(x)
diff --git a/tests/test_a.py b/tests/test_a.py
new file mode 100644
--- /dev/null
+++ b/tests/test_a.py
@@ -0,0 +1,2 @@
+def test_a():
+    assert True
"""


def test_two_files_and_line_numbers():
    files = parse_diff(TWO_FILES)
    assert [f.path for f in files] == ["app/a.py", "tests/test_a.py"]
    first = files[0]
    assert [(x.number, x.text) for x in first.added] == [(2, "x = 2"), (3, "y = 3")]
    assert [(x.number, x.text) for x in first.removed] == [(2, "x = 1")]


def test_new_file_and_test_detection():
    files = parse_diff(TWO_FILES)
    assert files[1].is_new
    assert files[1].is_test and not files[0].is_test
    assert [x.number for x in files[1].added] == [1, 2]


def test_removed_line_that_looks_like_a_header_is_not_confused():
    diff = """diff --git a/q.sql b/q.sql
--- a/q.sql
+++ b/q.sql
@@ -1,2 +1,1 @@
--- old comment
 SELECT 1;
"""
    files = parse_diff(diff)
    assert len(files) == 1
    assert files[0].removed[0].text == "-- old comment"


def test_plain_patch_without_diff_git_line():
    diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a = 1\n+a = 2\n"
    files = parse_diff(diff)
    assert files[0].path == "x.py" and files[0].added[0].number == 1


def test_empty_input():
    assert parse_diff("") == []