from app.pipeline import review_diff
from app.reports.review_report import render_markdown

SAMPLE_DIFF = """diff --git a/app/login.py b/app/login.py
--- a/app/login.py
+++ b/app/login.py
@@ -1,4 +1,3 @@
 def login(user, password):
-    if not password:
-        raise ValueError("password required")
+    result = eval(user)
     return True
diff --git a/requirements.txt b/requirements.txt
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1,2 @@
 flask==3.0.0
+requests
"""

result = review_diff(SAMPLE_DIFF)
print(render_markdown(result))