"""Characterization tests for PatternAgent."""

from pathlib import Path

import pytest

from reducto.agents.pattern import PatternAgent
from reducto.models import FileInfo, PatternRequest

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "test-python-code"
    / "python"
    / "patterns"
    / "complex_conditionals.py"
)


@pytest.mark.asyncio
async def test_strategy_pattern_on_complex_conditionals():
    content = FIXTURE.read_text(encoding="utf-8")
    agent = PatternAgent()
    plan = await agent.apply_pattern(
        PatternRequest(
            pattern="strategy",
            path=str(FIXTURE.parent),
            files=[FileInfo(path=str(FIXTURE.name), content=content)],
        )
    )
    assert plan.session_id
    assert len(plan.changes) >= 1
    assert any("strategies/" in c.path for c in plan.changes)
