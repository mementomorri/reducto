"""
Idiomatizer agent for transforming code to idiomatic patterns.
"""

from reducto.agents.base import BaseAgent
from reducto.models import (
    FileChange,
    IdiomatizeRequest,
    Language,
    ModelTier,
    RefactorPlan,
)
from reducto.session import SessionStore


class IdiomatizerAgent(BaseAgent):
    def __init__(self, workspace=None, llm_router=None, session_store: SessionStore | None = None):
        super().__init__(workspace, llm_router, session_store)

    def _get_file_content_and_path(self, file) -> tuple[str, str]:
        if hasattr(file, "content"):
            return file.content, file.path
        return file["content"], file["path"]

    async def idiomatize(self, request: IdiomatizeRequest) -> RefactorPlan:
        path = request.path
        files = request.files
        language = request.language

        changes = []
        for file in files:
            file_changes = await self._idiomatize_file(file, language)
            changes.extend(file_changes)

        session_id = self._generate_session_id()
        plan = RefactorPlan(
            session_id=session_id,
            changes=changes,
            description=f"Found {len(changes)} opportunities for idiomatic improvements.",
        )

        # Save to both memory and disk
        self._save_plan(plan, command_type="idiomatize")

        return plan

    async def _idiomatize_file(
        self,
        file,
        language: Language,
    ) -> list[FileChange]:
        changes = []
        content, path = self._get_file_content_and_path(file)

        if language == Language.PYTHON:
            changes = self._idiomatize_python(content, path)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            changes = self._idiomatize_js(content, path, language)
        elif language == Language.GO:
            changes = self._idiomatize_go(content, path)

        return changes

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
        stripped = line.strip()

        if self._is_for_append_pattern(lines, idx):
            return self._convert_to_list_comp(lines, idx)

        return None

    def _is_for_append_pattern(self, lines: list[str], idx: int) -> bool:
        if idx + 1 >= len(lines):
            return False

        line = lines[idx].strip()
        if not line.startswith("for "):
            return False

        next_line = lines[idx + 1].strip()
        if ".append(" in next_line:
            return True

        return False

    def _convert_to_list_comp(self, lines: list[str], idx: int) -> tuple | None:
        for_line = lines[idx]
        append_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""

        import re

        for_match = re.match(r"for\s+(\w+)\s+in\s+(.+?):", for_line.strip())
        if not for_match:
            return None

        var = for_match.group(1)
        iterable = for_match.group(2)

        append_match = re.match(r"(\w+)\.append\((.+?)\)", append_line)
        if not append_match:
            return None

        list_var = append_match.group(1)
        expr = append_match.group(2)

        indent = len(for_line) - len(for_line.lstrip())
        list_comp = f"{' ' * indent}{list_var} = [{expr} for {var} in {iterable}]"

        original = f"{for_line}\n{append_line}"
        return (original, list_comp, "Convert for-loop with append to list comprehension")

    def _idiomatize_js(
        self,
        content: str,
        path: str,
        language: Language,
    ) -> list[FileChange]:
        changes = []

        if "var " in content:
            changes.append(
                FileChange(
                    path=path,
                    original="var ",
                    modified="const ",
                    description="Replace 'var' with 'const' or 'let'",
                )
            )

        if "for (var " in content or "for (let " in content:
            changes.append(
                FileChange(
                    path=path,
                    original="for (",
                    modified="for (const ",
                    description="Consider using for...of or array methods",
                )
            )

        return changes

    def _idiomatize_go(self, content: str, path: str) -> list[FileChange]:
        changes = []
        import re

        var_pattern = re.compile(r"\bvar\s+(\w+)\s+(\w+)\s*=\s*(.+)")
        for match in var_pattern.finditer(content):
            var_name = match.group(1)
            var_type = match.group(2)
            var_value = match.group(3)
            original = f"var {var_name} {var_type} = {var_value}"
            modified = f"{var_name} := {var_value}"
            if original in content:
                changes.append(
                    FileChange(
                        path=path,
                        original=original,
                        modified=modified,
                        description=f"Replace 'var {var_name}' with short variable declaration ':='",
                    )
                )

        if "interface{}" in content:
            changes.append(
                FileChange(
                    path=path,
                    original="interface{}",
                    modified="any",
                    description="Replace empty interface{} with any",
                )
            )

        if re.search(r'"\s*\+\s*"', content):
            changes.append(
                FileChange(
                    path=path,
                    original="+",
                    modified="fmt.Sprintf or strings.Builder",
                    description="Consider using fmt.Sprintf or strings.Builder for string concatenation",
                )
            )

        return changes

    async def suggest_idiomatic_version(
        self,
        code: str,
        language: Language,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        """Use LLM to suggest idiomatic version of code."""
        if not self.llm:
            return "LLM not available for idiomatization"

        goal = f"Transform this code to be more idiomatic {language.value}"
        return await self.llm.suggest_refactor(code, language.value, goal, tier=tier)
