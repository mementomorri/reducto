"""Cognitive complexity is distinct from cyclomatic and nesting-weighted."""

from reducto.parse import get_complexity


def test_cognitive_grows_with_nesting():
    flat = "def f(a):\n    if a:\n        return 1\n    if a:\n        return 2\n"
    nested = "def g(a):\n    if a:\n        if a:\n            if a:\n                return 1\n"
    f, n = get_complexity(flat), get_complexity(nested)
    # Same kind of decision points, very different cognitive load due to nesting.
    assert n.cognitive_complexity > f.cognitive_complexity
    assert n.cognitive_complexity > n.cyclomatic_complexity


def test_boolean_operators_add_cognitive():
    m = get_complexity("def f(a, b):\n    if a and b or a:\n        return 1\n")
    assert m.cognitive_complexity >= 3  # if + and + or
