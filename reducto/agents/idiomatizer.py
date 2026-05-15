"""
Idiomatizer agent for transforming code to idiomatic patterns (Python heuristics).
"""

import re

from reducto.agents.base import BaseAgent
from reducto.models import FileChange, IdiomatizeRequest, Language, ModelTier, RefactorPlan
from reducto.repo import detect_language
from reducto.session import SessionStore


class IdiomatizerAgent(BaseAgent):
    def __init__(self, workspace=None, llm_router=None, session_store: SessionStore | None = None):
        super().__init__(workspace, llm_router, session_store)

    async def idiomatize(self, request: IdiomatizeRequest) -> RefactorPlan:
        changes = []
        for file in request.files:
            changes.extend(await self._idiomatize_file(file))
        return self._finalize_plan(
            changes,
            f"Found {len(changes)} opportunities for idiomatic improvements.",
            "idiomatize",
        )

    async def _idiomatize_file(self, file) -> list[FileChange]:
        content, path = self._file_content_path(file)
        if detect_language(path) != Language.PYTHON:
            return []
        return self._idiomatize_python(content, path)

    def _idiomatize_python(self, content: str, path: str) -> list[FileChange]:
        changes = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            result = self._try_python_idiom(line, lines, i)
            if result:
                original, modified, description = result
                changes.append(
                    FileChange(
                        path=path,
                        original=original,
                        modified=modified,
                        description=f"Line {i+1}: {description}",
                    )
                )
        return changes

    def _try_python_idiom(self, line: str, lines: list[str], idx: int) -> tuple | None:
        if self._is_for_append_pattern(lines, idx):
            return self._convert_to_list_comp(lines, idx)
        return None

    def _is_for_append_pattern(self, lines: list[str], idx: int) -> bool:
        if idx + 1 >= len(lines):
            return False
        line = lines[idx].strip()
        if not line.startswith("for "):
            return False
        return ".append(" in lines[idx + 1].strip()

    def _convert_to_list_comp(self, lines: list[str], idx: int) -> tuple | None:
        for_line = lines[idx]
        append_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        for_match = re.match(r"for\s+(\w+)\s+in\s+(.+?):", for_line.strip())
        if not for_match:
            return None
        append_match = re.match(r"(\w+)\.append\((.+?)\)", append_line)
        if not append_match:
            return None
        var, iterable = for_match.group(1), for_match.group(2)
        list_var, expr = append_match.group(1), append_match.group(2)
        indent = len(for_line) - len(for_line.lstrip())
        list_comp = f"{' ' * indent}{list_var} = [{expr} for {var} in {iterable}]"
        return (
            f"{for_line}\n{append_line}",
            list_comp,
            "Convert for-loop with append to list comprehension",
        )

    async def suggest_idiomatic_version(
        self,
        code: str,
        language: Language,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        if not self.llm:
            return "LLM not available for idiomatization"
        goal = f"Transform this code to be more idiomatic {language.value}"
        return await self.llm.suggest_refactor(code, language.value, goal, tier=tier)
