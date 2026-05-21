"""Base agent class."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from reducto.models import RefactorPlan
from reducto.session import SessionStore
from reducto.workspace import Workspace

if TYPE_CHECKING:
    from reducto.llm.router import LLMRouter


class BaseAgent:
    def __init__(
        self,
        workspace: Workspace | None = None,
        llm_router: LLMRouter | None = None,
        session_store: SessionStore | None = None,
    ):
        self.workspace = workspace
        self.llm = llm_router
        self.session_store = session_store or SessionStore()
        self._session_plans: dict[str, RefactorPlan] = {}

    def _generate_session_id(self) -> str:
        return str(uuid.uuid4())

    def _save_plan(self, plan: RefactorPlan, command_type: str) -> None:
        self._session_plans[plan.session_id] = plan
        self.session_store.save_plan(plan, command_type=command_type)

    def get_plan(self, session_id: str) -> RefactorPlan | None:
        if session_id in self._session_plans:
            return self._session_plans[session_id]
        return self.session_store.load_plan(session_id)

    def _file_content_path(self, file) -> tuple[str, str]:
        if hasattr(file, "content"):
            return file.content, file.path
        return file["content"], file["path"]

    def _finalize_plan(
        self, changes: list, description: str, command_type: str, **plan_kw
    ) -> RefactorPlan:
        plan = RefactorPlan(
            session_id=self._generate_session_id(),
            changes=changes,
            description=description,
            **plan_kw,
        )
        self._save_plan(plan, command_type)
        return plan
