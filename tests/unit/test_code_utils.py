"""Tests for code_utils helpers."""

from reducto.utils.code_utils import find_go_block_end, find_js_block_end, find_python_block_end


def test_find_go_block_end_counts_braces():
    lines = [
        "func foo() {",
        "    x := 1",
        "}",
        "func bar() {",
    ]
    assert find_go_block_end(lines, 0) == 3
    assert find_js_block_end(lines, 0) == find_go_block_end(lines, 0)


def test_find_python_block_end_uses_indent():
    lines = ["def foo():", "    a = 1", "    b = 2", "def bar():"]
    assert find_python_block_end(lines, 0) == 3
