from app.git.diff_parser import parse_diff

SAMPLE_DIFF = """diff --git a/app/a.py b/app/a.py
--- a/app/a.py
+++ b/app/a.py
@@ -1,3 +1,4 @@
 import os
-x = 1
+x = eval("2")
+y = 3
 print(x)
"""

for file in parse_diff(SAMPLE_DIFF):
    print("File:", file.path)
    for line in file.added:
        print(f"  ADDED   line {line.number}: {line.text}")
    for line in file.removed:
        print(f"  REMOVED line {line.number}: {line.text}")