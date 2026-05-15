"""Characterization tests for QualityCheckerAgent."""

import pytest

from reducto.agents.quality_checker import QualityCheckerAgent
from reducto.models import FileInfo, Language


def _long_python_body() -> str:
    lines = ["def long_runner():"]
    lines.extend([f"    x = {i}" for i in range(55)])
    lines.append("    return x")
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_check_quality_flags_long_function():
    content = _long_python_body()
    agent = QualityCheckerAgent()
    report = await agent.check_quality(
        [FileInfo(path="sample.py", content=content)],
        path=".",
    )
    long_fn = [i for i in report.issues if i.issue_type == "long_function"]
    assert long_fn
    assert long_fn[0].line == 1
    assert long_fn[0].symbol == "long_runner"


@pytest.mark.asyncio
async def test_check_quality_flags_bad_variable_name():
    content = "def f():\n    qq = 1\n    return qq\n"
    agent = QualityCheckerAgent()
    report = await agent.check_quality(
        [FileInfo(path="sample.py", content=content)],
        path=".",
    )
    bad = [i for i in report.issues if i.issue_type == "bad_variable_name"]
    assert bad
    assert any(i.symbol == "qq" for i in bad)


def test_detect_language_via_repo():
    from reducto.repo import detect_language

    assert detect_language("a.py") == Language.PYTHON
    assert detect_language("b.js") == Language.JAVASCRIPT
    assert detect_language("c.go") == Language.GO
