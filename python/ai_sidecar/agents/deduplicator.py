"""
Deduplicator agent for finding and eliminating code duplication.
"""

from typing import List, Dict, Optional

from ai_sidecar.models import (
    DeduplicateRequest,
    RefactorPlan,
    FileChange,
    DuplicateGroup,
    CodeBlock,
    Language,
    ComplexityMetrics,
    ModelTier,
    FileInfo,
)
from ai_sidecar.embeddings import EmbeddingService
from ai_sidecar.session import SessionStore
from ai_sidecar.utils import (
    extract_python_function_name,
    extract_js_function_name,
    extract_go_function_name,
    find_python_block_end,
    find_js_block_end,
    calculate_complexity,
)
from ai_sidecar.agents.base import BaseAgent


class DeduplicatorAgent(BaseAgent):
    def __init__(
        self,
        embedding_service: EmbeddingService,
        llm_router=None,
        mcp_client=None,
        session_store: Optional[SessionStore] = None,
    ):
        super().__init__(llm_router, mcp_client, session_store)
        self.embedding_service = embedding_service

    async def find_duplicates(self, request: DeduplicateRequest) -> RefactorPlan:
        path = request.path
        files = request.files
        threshold = request.similarity_threshold

        blocks = await self._extract_blocks(files)
        duplicate_groups = await self.embedding_service.find_duplicates(blocks, threshold)

        changes = []
        for group in duplicate_groups:
            if len(group) >= 2:
                change = await self._create_dedup_change(group, path)
                if change:
                    changes.append(change)

        session_id = self._generate_session_id()
        plan = RefactorPlan(
            session_id=session_id,
            changes=changes,
            description=f"Found {len(duplicate_groups)} duplicate code blocks. "
                       f"Proposed {len(changes)} refactoring changes.",
        )

        # Save to both memory and disk
        self._save_plan(plan, command_type="deduplicate")

        return plan

    async def _extract_blocks(self, files: List[FileInfo]) -> List[CodeBlock]:
        blocks = []

        for file in files:
            path = file.path
            content = file.content if file.content else ""
            language = self._detect_language(path)

            file_blocks = await self._parse_blocks(content, path, language)
            blocks.extend(file_blocks)

        return blocks

    def _detect_language(self, path: str) -> Language:
        if path.endswith(".py"):
            return Language.PYTHON
        elif path.endswith(".js"):
            return Language.JAVASCRIPT
        elif path.endswith((".ts", ".tsx")):
            return Language.TYPESCRIPT
        elif path.endswith(".go"):
            return Language.GO
        return Language.UNKNOWN

    async def _parse_blocks(
        self,
        content: str,
        path: str,
        language: Language,
    ) -> List[CodeBlock]:
        """Parse code blocks using language-specific detection."""
        blocks = []
        lines = content.split("\n")

        # Language-specific detection and extraction
        if language == Language.PYTHON:
            detect_fn = lambda s: s.startswith(("def ", "async def "))
            extract_fn = lambda s: extract_python_function_name(s)
            find_end_fn = lambda lines, i: find_python_block_end(lines, i)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            detect_fn = lambda s: "function " in s
            extract_fn = lambda s: extract_js_function_name(s) or "anonymous"
            find_end_fn = lambda lines, i: find_js_block_end(lines, i)
        elif language == Language.GO:
            detect_fn = lambda s: s.startswith("func ")
            extract_fn = lambda s: extract_go_function_name(s[5:] if s.startswith("func ") else s)
            find_end_fn = lambda lines, i: find_js_block_end(lines, i)
        else:
            return []

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if detect_fn(stripped):
                start = i
                name = extract_fn(stripped)
                end = find_end_fn(lines, i)
                content_block = "\n".join(lines[start:end])

                blocks.append(CodeBlock(
                    id=f"{path}:{start}:{name}",
                    file=path,
                    start_line=start + 1,
                    end_line=end,
                    content=content_block,
                    language=language,
                    symbol_type="function",
                    symbol_name=name,
                    metrics=self._calculate_metrics(content_block),
                ))
                i = end
            i += 1

        return blocks

    def _calculate_metrics(self, content: str) -> ComplexityMetrics:
        return calculate_complexity(content)

    async def _create_dedup_change(
        self,
        group: List[CodeBlock],
        base_path: str,
    ) -> Optional[FileChange]:
        if len(group) < 2:
            return None

        primary = group[0]
        combined_names = "_".join(b.symbol_name for b in group[:3])
        if len(combined_names) > 30:
            combined_names = combined_names[:30]

        new_util_path = f"utils/{primary.symbol_name}_dedup.py"
        new_content = self._generate_util_function(primary)

        description = (
            f"Extract duplicate '{primary.symbol_name}' found in {len(group)} files: "
            f"{', '.join(b.file for b in group[:3])}"
        )

        return FileChange(
            path=new_util_path,
            original="",
            modified=new_content,
            description=description,
        )

    def _generate_util_function(self, block: CodeBlock) -> str:
        lines = block.content.split("\n")
        dedented = []
        min_indent = float("inf")

        for line in lines[1:]:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                min_indent = min(min_indent, indent)

        for line in lines:
            if len(line) >= min_indent and line.strip():
                dedented.append(line[min_indent:])
            else:
                dedented.append(line)

        return "\n".join(dedented)
