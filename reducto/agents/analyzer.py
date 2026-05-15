"""Analyzer agent for repository analysis."""

from __future__ import annotations

from reducto.models import (
    AnalyzeRequest,
    AnalyzeResult,
    ComplexityHotspot,
    ComplexityMetrics,
    FileInfo,
    Language,
    Symbol,
)
from reducto.parse import get_complexity
from reducto.repo import detect_language
from reducto.workspace import Workspace


class AnalyzerAgent:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResult:
        files = request.files or self.workspace.list_files()
        symbols = await self._extract_symbols(files)
        hotspots = self._find_hotspots(files, symbols)
        return AnalyzeResult(
            total_files=len(files),
            total_symbols=len(symbols),
            hotspots=hotspots,
            symbols=symbols,
        )

    async def _extract_symbols(self, files: list[FileInfo]) -> list[Symbol]:
        symbols: list[Symbol] = []
        for f in files:
            lang = detect_language(f.path)
            if lang == Language.UNKNOWN:
                continue
            for s in self.workspace.get_symbols(f.path, f.content):
                symbols.append(s)
        return symbols

    def _find_hotspots(
        self, files: list[FileInfo], symbols: list[Symbol]
    ) -> list[ComplexityHotspot]:
        threshold = self.workspace.cfg.complexity_thresholds.cyclomatic_complexity
        contents = {f.path: f.content for f in files}
        hotspots: list[ComplexityHotspot] = []
        for sym in symbols:
            text = ""
            if sym.file in contents:
                lines = contents[sym.file].split("\n")
                end = min(sym.end_line, len(lines))
                if sym.start_line <= len(lines):
                    text = "\n".join(lines[sym.start_line - 1 : end])
            metrics = get_complexity(text) if text else ComplexityMetrics()
            if metrics.cyclomatic_complexity >= threshold:
                hotspots.append(
                    ComplexityHotspot(
                        file=sym.file,
                        line=sym.start_line,
                        symbol=sym.name,
                        cyclomatic_complexity=metrics.cyclomatic_complexity,
                        cognitive_complexity=metrics.cognitive_complexity,
                    )
                )
        return sorted(hotspots, key=lambda x: -x.cyclomatic_complexity)[:20]
