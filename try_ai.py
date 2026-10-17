from app.pipeline import review_diff
from app.reports.review_report import render_markdown

SAMPLE_DIFF = """diff --git a/app/report.py b/app/report.py
--- a/app/report.py
+++ b/app/report.py
@@ -1,3 +1,3 @@
 def show(rows):
-    for i in range(len(rows)):
+    for i in range(len(rows) + 1):
         print(rows[i])
"""

print("--- WITHOUT AI ---")
print(render_markdown(review_diff(SAMPLE_DIFF)))

print("\n--- WITH AI (the first run can take a few minutes while the model loads) ---")
print(render_markdown(review_diff(SAMPLE_DIFF, use_ai=True)))