"""Idiomatizer agent smoke test."""

import pytest

from reducto.agents.idiomatizer import IdiomatizerAgent
from reducto.models import FileInfo, IdiomatizeRequest, Language
from reducto.workspace import Workspace


@pytest.mark.asyncio
async def test_idiomatize_empty_files(tmp_path):
    ws = Workspace(str(tmp_path))
    agent = IdiomatizerAgent(ws)
    plan = await agent.idiomatize(
        IdiomatizeRequest(path=str(tmp_path), files=[], language=Language.PYTHON)
    )
    assert plan.session_id
    assert isinstance(plan.changes, list)


@pytest.mark.asyncio
async def test_idiomatize_list_comp_from_for_append(tmp_path):
    content = (
        "def build():\n"
        "    out = []\n"
        "    for x in range(3):\n"
        "        out.append(x * 2)\n"
        "    return out\n"
    )
    ws = Workspace(str(tmp_path))
    agent = IdiomatizerAgent(ws)
    plan = await agent.idiomatize(
        IdiomatizeRequest(
            path=str(tmp_path),
            files=[{"path": "build.py", "content": content}],
            language=Language.PYTHON,
        )
    )
    assert len(plan.changes) == 1
    assert "for " in plan.changes[0].original
    assert "for " in plan.changes[0].modified and " in " in plan.changes[0].modified


@pytest.mark.asyncio
async def test_idiomatize_skips_non_python(tmp_path):
    content = "var x = 1;\nfunction f() { return x; }\n"
    ws = Workspace(str(tmp_path))
    agent = IdiomatizerAgent(ws)
    plan = await agent.idiomatize(
        IdiomatizeRequest(
            path=str(tmp_path),
            files=[FileInfo(path="app.js", content=content)],
            language=Language.JAVASCRIPT,
        )
    )
    assert plan.changes == []
