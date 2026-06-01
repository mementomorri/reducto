"""Automated coverage for docs/TEST_RULES.md scenarios."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from reducto.agents.analyzer import AnalyzerAgent
from reducto.agents.deduplicator import DeduplicatorAgent
from reducto.agents.idiomatizer import IdiomatizerAgent
from reducto.agents.pattern import PatternAgent
from reducto.models import (
    AnalyzeRequest,
    CodeBlock,
    ComplexityMetrics,
    DeduplicateRequest,
    FileInfo,
    IdiomatizeRequest,
    Language,
    PatternRequest,
)
from reducto.repo import detect_language
from reducto.reporter import Reporter
from reducto.workspace import Workspace

FIXTURE = Path(__file__).resolve().parents[2] / "test-python-code" / "python"


def test_repo_detects_python_only(fixture_files):
    langs = {detect_language(f.path) for f in fixture_files}
    assert langs == {Language.PYTHON}


@pytest.mark.asyncio
async def test_analyze_returns_symbols(fixture_files):
    ws = Workspace(str(FIXTURE.parent.parent))
    result = await AnalyzerAgent(ws).analyze(AnalyzeRequest(path=str(FIXTURE), files=fixture_files))
    assert result.total_symbols > 0


@pytest.mark.asyncio
async def test_dedup_stub_plan_on_duplicate_pair():
    auth = (FIXTURE / "duplicates" / "auth_validator.py").read_text(encoding="utf-8")
    user = (FIXTURE / "duplicates" / "user_validator.py").read_text(encoding="utf-8")
    block = CodeBlock(
        id="auth:1:validate_email",
        file="auth_validator.py",
        start_line=1,
        end_line=5,
        content="def validate_email(e):\n    return '@' in e\n",
        language=Language.PYTHON,
        symbol_type="function",
        symbol_name="validate_email",
        metrics=ComplexityMetrics(),
        embedding=[0.1] * 384,
    )
    emb = MagicMock()
    emb.find_duplicates = AsyncMock(return_value=[[block, block]])
    ws = Workspace(str(FIXTURE))
    plan = await DeduplicatorAgent(ws, emb).find_duplicates(
        DeduplicateRequest(
            path=str(FIXTURE),
            files=[
                FileInfo(path="auth_validator.py", content=auth),
                FileInfo(path="user_validator.py", content=user),
            ],
        )
    )
    assert plan.changes
    assert "utils/" in plan.changes[0].path


@pytest.mark.asyncio
async def test_idiom_list_comp():
    content = "def build():\n    out = []\n    for x in range(3):\n        out.append(x * 2)\n"
    plan = await IdiomatizerAgent().idiomatize(
        IdiomatizeRequest(
            path=".",
            files=[FileInfo(path="b.py", content=content)],
        )
    )
    assert len(plan.changes) == 1


@pytest.mark.asyncio
async def test_pattern_strategy_on_complex_conditionals():
    path = FIXTURE / "patterns" / "complex_conditionals.py"
    content = path.read_text(encoding="utf-8")
    plan = await PatternAgent().apply_pattern(
        PatternRequest(
            pattern="strategy",
            path=str(FIXTURE),
            files=[FileInfo(path=path.name, content=content)],
        )
    )
    assert any("strategies/" in c.path for c in plan.changes)


def test_reporter_writes_markdown(tmp_path):
    from reducto.models import AnalyzeResult

    out = tmp_path / ".reducto"
    path = Reporter(output_dir=str(out)).generate_baseline(
        AnalyzeResult(total_files=1, total_symbols=2, hotspots=[], symbols=[])
    )
    assert path.exists()
    assert "Baseline" in path.read_text(encoding="utf-8")
