"""
Analyzer agent for repository analysis and complexity detection.
"""

import asyncio
import logging
import os
import uuid
from typing import List, Dict, Any, Optional

from ai_sidecar.models import (
    AnalyzeRequest,
    AnalyzeResult,
    ComplexityHotspot,
    Symbol,
    Language,
    ComplexityMetrics,
    ModelTier,
)
from ai_sidecar.utils import calculate_complexity

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    def __init__(self, llm_router=None, mcp_client=None):
        self.llm = llm_router
        self.mcp = mcp_client
        self._session_cache: Dict[str, Any] = {}

    def _get_file_attr(self, file, attr: str):
        if hasattr(file, attr):
            return getattr(file, attr)
        return file.get(attr)

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResult:
        path = request.path
        files = request.files

        if not files:
            files = await self._scan_directory(path)

        symbols = await self._extract_symbols(files)
        hotspots = await self._find_hotspots(files, symbols)

        return AnalyzeResult(
            total_files=len(files),
            total_symbols=len(symbols),
            hotspots=hotspots,
            duplicates=[],
            symbols=symbols,
        )

    async def _scan_directory(self, path: str):
        if self.mcp:
            return await self._scan_directory_mcp(path)
        return await self._scan_directory_local(path)

    async def _scan_directory_mcp(self, path: str):
        result = await self.mcp.list_files()
        files = []
        for f in result.get("files") or []:
            file_data = await self.mcp.read_file(f.get("path") if hasattr(f, 'get') else f["path"])
            files.append({
                "path": f.get("path") if hasattr(f, 'get') else f["path"],
                "content": file_data.get("content", "") if hasattr(file_data, 'get') else file_data["content"],
            })
        return files

    async def _scan_directory_local(self, path: str):
        files = []
        exclude_dirs = {".git", "node_modules", "venv", "__pycache__", "vendor", "dist", "build"}

        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for filename in filenames:
                filepath = os.path.join(root, filename)
                relpath = os.path.relpath(filepath, path)

                if self._should_include(filename):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        files.append({
                            "path": relpath,
                            "content": content,
                        })
                    except (UnicodeDecodeError, IOError):
                        continue

        return files

    def _should_include(self, filename: str) -> bool:
        include_exts = {".py", ".js", ".ts", ".tsx", ".go", ".java"}
        _, ext = os.path.splitext(filename)
        return ext.lower() in include_exts

    async def _extract_symbols(self, files) -> List[Symbol]:
        symbols = []
        code_files = []
        
        for file in files:
            if hasattr(file, 'content'):
                content = file.content
                path = file.path
            else:
                content = file["content"]
                path = file["path"]
            
            if self._should_include(path):
                code_files.append((path, content))
        
        for path, content in code_files:
            language = self._detect_language(path)

            if self.mcp and not content:
                try:
                    result = await asyncio.wait_for(self.mcp.get_symbols(path), timeout=5.0)
                    if result and isinstance(result, dict):
                        for s in result.get("symbols") or []:
                            symbols.append(Symbol(
                                name=s.get("name", ""),
                                type=s.get("type", ""),
                                file=path,
                                start_line=s.get("start_line", 0),
                                end_line=s.get("end_line", 0),
                                signature=s.get("signature"),
                            ))
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout getting symbols for {path}")
                except Exception as e:
                    logger.warning(f"Error getting symbols for {path}: {e}")
            elif content:
                file_symbols = await self._parse_symbols(content, path, language)
                symbols.extend(file_symbols)
        
        return symbols

    def _detect_language(self, path: str) -> Language:
        _, ext = os.path.splitext(path)
        mapping = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".go": Language.GO,
        }
        return mapping.get(ext.lower(), Language.UNKNOWN)

    async def _parse_symbols(
        self,
        content: str,
        path: str,
        language: Language,
    ) -> List[Symbol]:
        """Parse symbols using Go MCP Tree-sitter parser."""
        if not self.mcp:
            return []
        
        # Call Go MCP tool for Tree-sitter based symbol extraction
        result = await self.mcp.get_symbols(path, content)
        symbols_data = result.get("symbols", [])
        
        return [
            Symbol(
                name=s["name"],
                type=s["type"],
                file=s["file"],
                start_line=s["start_line"],
                end_line=s["end_line"],
                signature=s.get("signature", ""),
            )
            for s in symbols_data
        ]

    async def _find_hotspots(
        self,
        files,
        symbols: List[Symbol],
    ) -> List[ComplexityHotspot]:
        hotspots = []
        complexity_threshold = 10
        
        file_contents = {}
        for f in files:
            fpath = self._get_file_attr(f, 'path')
            fcontent = self._get_file_attr(f, 'content') or ""
            file_contents[fpath] = fcontent
        
        for symbol in symbols:
            metrics = await self._calculate_complexity_fast(symbol, file_contents)
            if metrics.cyclomatic_complexity >= complexity_threshold:
                hotspots.append(ComplexityHotspot(
                    file=symbol.file,
                    line=symbol.start_line,
                    symbol=symbol.name,
                    cyclomatic_complexity=metrics.cyclomatic_complexity,
                    cognitive_complexity=metrics.cognitive_complexity,
                ))
        
        return sorted(hotspots, key=lambda x: -x.cyclomatic_complexity)[:20]

    async def _calculate_complexity_fast(
        self,
        symbol: Symbol,
        file_contents: Dict[str, str],
    ) -> ComplexityMetrics:
        content = ""
        if symbol.file in file_contents:
            lines = file_contents[symbol.file].split("\n")
            if symbol.start_line <= len(lines):
                end_line = min(symbol.end_line, len(lines))
                content = "\n".join(lines[symbol.start_line - 1:end_line])

        if not content:
            return ComplexityMetrics()

        return calculate_complexity(content)

    async def calculate_lmcc(self, code: str, language: Language) -> ComplexityMetrics:
        """Calculate LM-CC (LLM-perceived Code Complexity) metric."""
        if not self.llm:
            return ComplexityMetrics()
        
        # Truncate code to avoid token limits
        truncated_code = code[:2000]
        
        prompt = f"""Rate this {language.value} code complexity from 1-10:

```{truncated_code}```

Consider:
- Nesting depth
- Branching complexity  
- Cognitive load
- Abstraction level

Respond with just a number 1-10."""

        try:
            response = await self.llm.complete(prompt, tier=ModelTier.MEDIUM)
            score = int(response.strip()) * 10  # Convert to 0-100
        except (ValueError, Exception):
            score = 50  # Default if parsing fails
        
        rating = "high" if score > 70 else "medium" if score > 40 else "low"
        
        return ComplexityMetrics(
            lmcc_score=float(score),
            lmcc_rating=rating,
        )

    async def investigate_uncommon_patterns(
        self,
        code: str,
        language: Language,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        """Analyze code for uncommon or non-idiomatic patterns using LLM."""
        if not self.llm:
            return "LLM not available for pattern investigation"

        question = f"""Analyze this {language.value} code for uncommon or non-idiomatic patterns.

Consider:
1. Is this code following idiomatic {language.value} conventions?
2. Are there better design patterns that could be applied?
3. Is the code readable and maintainable?
4. Are there potential bugs or issues?

Provide specific recommendations for improvement."""

        return await self.llm.analyze_code(code, question, tier=tier)

    async def suggest_refactoring(
        self,
        code: str,
        language: Language,
        goal: str,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        """Suggest refactoring for a code block using LLM."""
        if not self.llm:
            return "LLM not available for refactoring suggestions"

        return await self.llm.suggest_refactor(code, language.value, goal, tier=tier)
