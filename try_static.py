from app.analysis.static_analysis import run_static_analysis
from app.git.diff_parser import parse_diff

SAMPLE_DIFF = """diff --git a/app/demo.py b/app/demo.py
--- a/app/demo.py
+++ b/app/demo.py
@@ -1,2 +1,8 @@
 import os
+API_KEY = "sk_live_1234567890"
+def add_item(item, items=[]):
+    result = eval(item)
+    return result
+# never use eval() in real code
+if os.name is "nt":
 print("done")
"""

files = parse_diff(SAMPLE_DIFF)
findings = run_static_analysis(files)

for f in findings:
    print(f"{f.file}:{f.line} [{f.severity}] {f.title}  ({f.rule_id})")
    print(f"    evidence: {f.evidence}")
print("Total findings:", len(findings))