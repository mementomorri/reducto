"""
Agent implementations for code analysis and refactoring.
"""

from reducto.agents.analyzer import AnalyzerAgent
from reducto.agents.deduplicator import DeduplicatorAgent
from reducto.agents.idiomatizer import IdiomatizerAgent
from reducto.agents.pattern import PatternAgent
from reducto.agents.quality_checker import QualityCheckerAgent

__all__ = [
    "AnalyzerAgent",
    "DeduplicatorAgent",
    "IdiomatizerAgent",
    "PatternAgent",
    "QualityCheckerAgent",
]
