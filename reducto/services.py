"""Application services — wires workspace, agents, and apply logic."""

from __future__ import annotations

import difflib
from typing import Any

from reducto.agents import (
    AnalyzerAgent,
    DeduplicatorAgent,
    IdiomatizerAgent,
    PatternAgent,
    QualityCheckerAgent,
)
from reducto.config import apply_env, load_config
from reducto.llm import LLMRouter
from reducto.models import (
    AnalyzeRequest,
    AnalyzeResult,
    AppConfig,
    DeduplicateRequest,
    FileInfo,
    IdiomatizeRequest,
    PatternRequest,
    RefactorPlan,
    RefactorResult,
)
from reducto.session import SessionStore
from reducto.workspace import Workspace


class App:
    def __init__(self, root: str, cfg: AppConfig | None = None):
        self.cfg = apply_env(cfg or load_config())
        self.root = root
        self.workspace = Workspace(root, self.cfg)
        self.sessions = SessionStore(storage_dir=str(self.workspace.root / ".reducto" / "sessions"))
        self.llm = LLMRouter(
            verbose=self.cfg.verbose,
            model_override=self.cfg.model or None,
            prefer_local=self.cfg.prefer_local,
        )
        self._embedding = None
        self.analyzer = AnalyzerAgent(self.workspace)
        self.quality = QualityCheckerAgent(self.workspace)

    async def _embeddings(self):
        if self._embedding is None:
            from reducto.embeddings import EmbeddingService

            self._embedding = EmbeddingService()
            await self._embedding.initialize(verbose=self.cfg.verbose)
        return self._embedding

    def _files(self) -> list[FileInfo]:
        return self.workspace.list_files()

    async def analyze(self, path: str) -> AnalyzeResult:
        return await self.analyzer.analyze(AnalyzeRequest(path=path, files=self._files()))

    async def deduplicate(self, path: str) -> RefactorPlan:
        emb = await self._embeddings()
        agent = DeduplicatorAgent(self.workspace, emb, self.llm, self.sessions)
        return await agent.find_duplicates(DeduplicateRequest(path=path, files=self._files()))

    async def idiomatize(self, path: str) -> RefactorPlan:
        agent = IdiomatizerAgent(self.workspace, self.llm, self.sessions)
        return await agent.idiomatize(IdiomatizeRequest(path=path, files=self._files()))

    async def pattern(self, pattern_name: str, path: str) -> RefactorPlan:
        agent = PatternAgent(self.workspace, self.llm, self.sessions)
        return await agent.apply_pattern(
            PatternRequest(pattern=pattern_name, path=path, files=self._files())
        )

    async def check(self, path: str) -> dict[str, Any]:
        report = await self.quality.check_quality(self._files(), path)
        return report.to_dict()

    def apply_plan(self, plan: RefactorPlan, run_tests: bool = True) -> RefactorResult:
        pairs = [(c.path, _change_to_diff(c)) for c in plan.changes]
        result = self.workspace.apply_changes_safe(pairs, run_tests=run_tests)
        if not result.get("success"):
            return RefactorResult(
                session_id=plan.session_id,
                success=False,
                changes=plan.changes[: result.get("applied", 0)],
                tests_passed=False,
                error=result.get("error", "apply failed"),
            )
        if self.cfg.commit_changes:
            self.workspace.commit_changes(f"reducto: {plan.description[:72]}", plan.changes)
        return RefactorResult(
            session_id=plan.session_id,
            success=True,
            changes=plan.changes,
            tests_passed=result.get("tests_passed", True),
        )


def _change_to_diff(change) -> str:
    if not change.original and change.modified:
        lines = change.modified.splitlines()
        body = "\n".join(f"+{ln}" for ln in lines)
        return f"--- /dev/null\n+++ b/{change.path}\n@@ -0,0 +1,{len(lines)} @@\n{body}"
    # Split on "\n" (not splitlines) so difflib's 1-based line numbers line up
    # exactly with diff.apply_unified_diff's split("\n") — context validation then
    # passes when disk == original and fails loudly on real drift.
    diff = list(
        difflib.unified_diff(
            change.original.split("\n"),
            change.modified.split("\n"),
            fromfile=f"a/{change.path}",
            tofile=f"b/{change.path}",
            lineterm="",
        )
    )
    return "\n".join(diff)
