"""Unit tests for parsing."""

from reducto.parse import get_complexity, get_symbols
from reducto.models import Language


def test_get_complexity_counts_branches():
    code = "def f():\n    if a:\n        if b:\n            return 1\n"
    m = get_complexity(code)
    assert m.cyclomatic_complexity >= 2


def test_python_symbols():
    code = "class Foo:\n    def bar(self):\n        pass\n"
    syms = get_symbols(code, "t.py", Language.PYTHON)
    names = {s.name for s in syms}
    assert "Foo" in names
    assert "bar" in names
