"""Idiomatizer agent smoke test."""

import pytest

from reducto.agents.idiomatizer import IdiomatizerAgent
from reducto.models import IdiomatizeRequest, Language
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
