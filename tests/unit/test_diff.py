"""Unit tests for diff application."""

from reducto.diff import apply_unified_diff


def test_apply_simple_hunk():
    original = "line1\nline2\nline3\n"
    diff = """@@ -2,1 +2,1 @@
-line2
+LINE2
"""
    result = apply_unified_diff(original, diff)
    assert "LINE2" in result
    assert "line2" not in result
