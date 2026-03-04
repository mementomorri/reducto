"""
Shared utility functions for code analysis.

Provides common helper methods for extracting function names, class names,
finding block endings, and calculating code complexity across different
programming languages.
"""

import re
from typing import List, Optional

from ai_sidecar.models import ComplexityMetrics


def extract_python_function_name(line: str) -> str:
    """Extract function name from Python function definition."""
    match = re.match(r'(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
    return match.group(1) if match else ""


def extract_js_function_name(line: str) -> Optional[str]:
    """Extract function name from JavaScript function definition."""
    patterns = [
        r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?function",
        r"([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(?:async\s*)?function",
        r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def extract_go_function_name(line: str) -> str:
    """Extract function name from Go function definition."""
    line = line.strip()
    if line.startswith("("):
        paren_end = line.find(")")
        if paren_end > 0:
            line = line[paren_end + 1:]
    name = line.split("(")[0].strip()
    return name if name else "anonymous"


def extract_class_name(line: str) -> str:
    """Extract class name from class definition."""
    line = line.replace("class ", "").strip()
    for char in "(:[{":
        idx = line.find(char)
        if idx > 0:
            line = line[:idx]
    return line.strip()


def find_python_block_end(lines: List[str], start: int) -> int:
    """Find the end of a Python block based on indentation."""
    if start >= len(lines):
        return len(lines)
    
    indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        if lines[i].strip() and not lines[i].startswith(" " * (indent + 1)):
            return i
    return len(lines)


def find_js_block_end(lines: List[str], start: int) -> int:
    """Find the end of a JavaScript/Go block based on brace counting."""
    brace_count = 0
    for i in range(start, len(lines)):
        brace_count += lines[i].count("{") - lines[i].count("}")
        if brace_count == 0 and i > start:
            return i + 1
    return len(lines)


def to_snake_case(name: str) -> str:
    """Convert a name to snake_case."""
    result = re.sub(r'([A-Z])', r'_\1', name)
    return result.lower().lstrip("_")


def to_pascal_case(name: str) -> str:
    """Convert a name to PascalCase."""
    parts = name.split("_")
    return "".join(p.capitalize() for p in parts if p)


def calculate_complexity(content: str) -> ComplexityMetrics:
    """
    Calculate cyclomatic and cognitive complexity for code content.
    
    Args:
        content: Code content as a string
        
    Returns:
        ComplexityMetrics with cyclomatic, cognitive, and LOC metrics
    """
    lines = [l for l in content.split("\n") if l.strip()]
    loc = len(lines)
    
    # Cyclomatic complexity: count decision points
    cyclomatic = 1
    cognitive = 0
    nesting = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Count cyclomatic complexity keywords
        cc_keywords = [
            "if ", "elif ", "else:", "for ", "while ",
            "case ", "catch ", "except ", "finally:",
            "and ", "or ", "&&", "||", "?",
        ]
        for kw in cc_keywords:
            cyclomatic += stripped.count(kw)
        
        # Count cognitive complexity with nesting
        if any(stripped.startswith(kw) for kw in ["if ", "elif ", "for ", "while ", "case "]):
            cognitive += 1 + nesting
            nesting += 1
        elif stripped.startswith("else") or stripped.startswith("except"):
            cognitive += 1 + max(0, nesting - 1)
        elif stripped in ["break", "continue"]:
            cognitive += 1
        elif stripped in ["}", "endif", "end"]:
            nesting = max(0, nesting - 1)
    
    return ComplexityMetrics(
        cyclomatic_complexity=cyclomatic,
        cognitive_complexity=cognitive,
        lines_of_code=loc,
    )
