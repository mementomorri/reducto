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


async def _apply(pattern: str, content: str):
    return await PatternAgent().apply_pattern(
        PatternRequest(pattern=pattern, path=".", files=[FileInfo(path="m.py", content=content)])
    )


@pytest.mark.asyncio
async def test_factory_pattern_on_conditional_instantiation():
    content = (
        "def make(k):\n    if k == 'a':\n        return FooHandler()\n    return BarHandler()\n"
    )
    plan = await _apply("factory", content)
    assert any("factories/" in c.path for c in plan.changes)


@pytest.mark.asyncio
async def test_singleton_pattern_wraps_global_state():
    content = "count = 0\n\ndef bump():\n    global count\n    count += 1\n"
    plan = await _apply("singleton", content)
    assert plan.changes
    assert plan.changes[0].original == content  # in-place rewrite
    assert "class Singleton" in plan.changes[0].modified


@pytest.mark.asyncio
async def test_observer_pattern_on_event_keywords():
    plan = await _apply("observer", "def notify(self):\n    self.subscribe()\n")
    assert any("observers/" in c.path for c in plan.changes)


@pytest.mark.asyncio
async def test_unknown_pattern_returns_no_changes():
    plan = await _apply("banana", "x = 1\n")
    assert plan.changes == []
