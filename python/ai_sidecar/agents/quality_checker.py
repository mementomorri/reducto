"""
Quality checker agent for detecting code quality issues.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from ai_sidecar.models import (
    Language,
    FileInfo,
)

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    file: str
    line: int
    issue_type: str
    severity: str
    message: str
    symbol: str = ""
    suggestion: str = ""


@dataclass
class QualityReport:
    total_issues: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0
    issues: List[QualityIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_issues": self.total_issues,
            "critical": self.critical,
            "warning": self.warning,
            "info": self.info,
            "issues": [
                {
                    "file": i.file,
                    "line": i.line,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "message": i.message,
                    "symbol": i.symbol,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ]
        }


class QualityCheckerAgent:
    def __init__(self, mcp_client=None):
        self.mcp = mcp_client
        self.max_function_lines = 50
        self.max_complexity = 10
        self.min_variable_name_length = 2

    async def check_quality(self, files: List[FileInfo], path: str) -> QualityReport:
        report = QualityReport()

        for file in files:
            file_path = file.path
            content = file.content if file.content else ""
            language = self._detect_language(file_path)

            if not content or language == Language.UNKNOWN:
                continue

            issues = await self._check_file(file_path, content, language)
            report.issues.extend(issues)

        report.issues.sort(key=lambda x: (x.severity == "critical", x.severity == "warning"), reverse=True)
        report.total_issues = len(report.issues)
        report.critical = sum(1 for i in report.issues if i.severity == "critical")
        report.warning = sum(1 for i in report.issues if i.severity == "warning")
        report.info = sum(1 for i in report.issues if i.severity == "info")

        return report

    def _detect_language(self, path: str) -> Language:
        _, ext = re.subn(r'\.[^.]+$', '', path)
        mapping = {
            ".py": Language.PYTHON,
            ".js": Language.JAVASCRIPT,
            ".ts": Language.TYPESCRIPT,
            ".tsx": Language.TYPESCRIPT,
            ".go": Language.GO,
        }
        for ext, lang in mapping.items():
            if path.endswith(ext):
                return lang
        return Language.UNKNOWN

    async def _check_file(self, file_path: str, content: str, language: Language) -> List[QualityIssue]:
        issues = []
        lines = content.split("\n")

        issues.extend(self._check_variable_names(file_path, lines, language))
        issues.extend(self._check_function_length(file_path, lines, language))
        issues.extend(self._check_complexity(file_path, lines, language))
        issues.extend(self._check_naming_conventions(file_path, lines, language))

        return issues

    def _check_variable_names(self, file_path: str, lines: List[str], language: Language) -> List[QualityIssue]:
        issues = []
        loop_vars = {"i", "j", "k", "n", "x", "y", "z", "_"}
        common_short_vars = {"a", "b", "c", "n", "m", "p", "q"}

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue

            is_loop = any(kw in stripped for kw in ["for ", "for(", "while "])

            if language == Language.PYTHON:
                issues.extend(self._check_python_variables(file_path, line_num, line, stripped, loop_vars, common_short_vars, is_loop))
            elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
                issues.extend(self._check_js_variables(file_path, line_num, line, stripped, loop_vars, common_short_vars, is_loop))
            elif language == Language.GO:
                issues.extend(self._check_go_variables(file_path, line_num, line, stripped, loop_vars, common_short_vars, is_loop))

        return issues

    def _check_python_variables(self, file_path: str, line_num: int, line: str, stripped: str, loop_vars: set, common_short_vars: set, is_loop: bool) -> List[QualityIssue]:
        issues = []

        var_patterns = [
            (r'\b([a-z][a-z0-9_]*)\s*=', 'assignment'),
            (r'\bdef\s+\w+\s*\(([^)]+)\)', 'parameter'),
            (r'\b([a-z][a-z0-9_]*)\s*:', 'type_annotation'),
        ]

        for pattern, context in var_patterns:
            matches = re.finditer(pattern, stripped)
            for match in matches:
                var_name = match.group(1) if context != 'parameter' else match.group(1)

                if context == 'parameter':
                    params = match.group(1)
                    for param in params.split(','):
                        param = param.strip().split('=')[0].split(':')[0].strip()
                        if param and self._is_bad_variable_name(param, is_loop, loop_vars, common_short_vars):
                            issues.append(QualityIssue(
                                file=file_path,
                                line=line_num,
                                issue_type="bad_parameter_name",
                                severity="warning",
                                message=f"Parameter '{param}' has an unclear name",
                                symbol=param,
                                suggestion=f"Consider using a more descriptive name like '{param}_value' or '{param}_data'",
                            ))
                elif var_name and self._is_bad_variable_name(var_name, is_loop, loop_vars, common_short_vars):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=line_num,
                        issue_type="bad_variable_name",
                        severity="warning",
                        message=f"Variable '{var_name}' has an unclear name",
                        symbol=var_name,
                        suggestion=f"Consider using a more descriptive name",
                    ))

        return issues

    def _check_js_variables(self, file_path: str, line_num: int, line: str, stripped: str, loop_vars: set, common_short_vars: set, is_loop: bool) -> List[QualityIssue]:
        issues = []

        patterns = [
            (r'\b(?:var|let|const)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', 'declaration'),
        ]

        for pattern, context in patterns:
            matches = re.finditer(pattern, stripped)
            for match in matches:
                var_name = match.group(1)
                if self._is_bad_variable_name(var_name, is_loop, loop_vars, common_short_vars):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=line_num,
                        issue_type="bad_variable_name",
                        severity="warning",
                        message=f"Variable '{var_name}' has an unclear name",
                        symbol=var_name,
                        suggestion="Consider using a more descriptive name",
                    ))

        return issues

    def _check_go_variables(self, file_path: str, line_num: int, line: str, stripped: str, loop_vars: set, common_short_vars: set, is_loop: bool) -> List[QualityIssue]:
        issues = []

        patterns = [
            (r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:=', 'short_declaration'),
            (r'\bvar\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+', 'var_declaration'),
        ]

        for pattern, context in patterns:
            matches = re.finditer(pattern, stripped)
            for match in matches:
                var_name = match.group(1)
                if self._is_bad_variable_name(var_name, is_loop, loop_vars, common_short_vars):
                    issues.append(QualityIssue(
                        file=file_path,
                        line=line_num,
                        issue_type="bad_variable_name",
                        severity="warning",
                        message=f"Variable '{var_name}' has an unclear name",
                        symbol=var_name,
                        suggestion="Consider using a more descriptive name",
                    ))

        return issues

    def _is_bad_variable_name(self, name: str, is_loop: bool, loop_vars: set, common_short_vars: set) -> bool:
        if not name or name.startswith("_"):
            return False

        if is_loop and name in loop_vars:
            return False

        if not name[0].isalpha() and name[0] != '_':
            return False

        has_letters = any(c.isalpha() for c in name)
        has_numbers = any(c.isdigit() for c in name)
        letter_ratio = sum(1 for c in name if c.isalpha()) / len(name) if name else 0

        if has_letters and has_numbers and letter_ratio < 0.4:
            return True

        if len(name) <= 2 and name not in loop_vars and name not in common_short_vars:
            return True

        if re.match(r'^[a-z]+\d+[a-z]+\d+', name.lower()):
            return True

        if re.match(r'^x\d+[a-z]+\d*', name.lower()):
            return True

        return False

    def _check_function_length(self, file_path: str, lines: List[str], language: Language) -> List[QualityIssue]:
        issues = []

        if language == Language.PYTHON:
            issues.extend(self._check_python_function_length(file_path, lines))
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            issues.extend(self._check_js_function_length(file_path, lines))
        elif language == Language.GO:
            issues.extend(self._check_go_function_length(file_path, lines))

        return issues

    def _check_python_function_length(self, file_path: str, lines: List[str]) -> List[QualityIssue]:
        issues = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                func_name = self._extract_python_function_name(stripped)
                end_line = self._find_python_block_end(lines, i)
                func_length = end_line - i

                if func_length > self.max_function_lines:
                    severity = "critical" if func_length > self.max_function_lines * 2 else "warning"
                    issues.append(QualityIssue(
                        file=file_path,
                        line=i + 1,
                        issue_type="long_function",
                        severity=severity,
                        message=f"Function '{func_name}' is {func_length} lines (max {self.max_function_lines})",
                        symbol=func_name,
                        suggestion="Consider breaking this function into smaller functions",
                    ))

        return issues

    def _check_js_function_length(self, file_path: str, lines: List[str]) -> List[QualityIssue]:
        issues = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if "function " in stripped or stripped.startswith("const ") and "=>" in stripped:
                func_name = self._extract_js_function_name(stripped)
                end_line = self._find_js_block_end(lines, i)
                func_length = end_line - i

                if func_length > self.max_function_lines:
                    severity = "critical" if func_length > self.max_function_lines * 2 else "warning"
                    issues.append(QualityIssue(
                        file=file_path,
                        line=i + 1,
                        issue_type="long_function",
                        severity=severity,
                        message=f"Function '{func_name}' is {func_length} lines (max {self.max_function_lines})",
                        symbol=func_name,
                        suggestion="Consider breaking this function into smaller functions",
                    ))

        return issues

    def _check_go_function_length(self, file_path: str, lines: List[str]) -> List[QualityIssue]:
        issues = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("func "):
                func_name = self._extract_go_function_name(stripped)
                end_line = self._find_go_block_end(lines, i)
                func_length = end_line - i

                if func_length > self.max_function_lines:
                    severity = "critical" if func_length > self.max_function_lines * 2 else "warning"
                    issues.append(QualityIssue(
                        file=file_path,
                        line=i + 1,
                        issue_type="long_function",
                        severity=severity,
                        message=f"Function '{func_name}' is {func_length} lines (max {self.max_function_lines})",
                        symbol=func_name,
                        suggestion="Consider breaking this function into smaller functions",
                    ))

        return issues

    def _check_complexity(self, file_path: str, lines: List[str], language: Language) -> List[QualityIssue]:
        issues = []

        complexity_keywords = [
            "if ", "elif ", "else:", "for ", "while ", "case ",
            "catch ", "except ", "switch ", "&&", "||", "and ", "or ",
        ]

        for line_num, line in enumerate(lines, 1):
            complexity = sum(line.count(kw) for kw in complexity_keywords)

            if complexity > 3:
                issues.append(QualityIssue(
                    file=file_path,
                    line=line_num,
                    issue_type="high_complexity_line",
                    severity="info",
                    message=f"Line has {complexity} branching conditions",
                    suggestion="Consider extracting logic to separate functions",
                ))

        return issues

    def _check_naming_conventions(self, file_path: str, lines: List[str], language: Language) -> List[QualityIssue]:
        issues = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if language == Language.PYTHON:
                if stripped.startswith("def "):
                    func_name = self._extract_python_function_name(stripped)
                    if func_name and not func_name[0].islower() and not func_name.startswith("_"):
                        issues.append(QualityIssue(
                            file=file_path,
                            line=line_num,
                            issue_type="naming_convention",
                            severity="info",
                            message=f"Function '{func_name}' should use snake_case",
                            symbol=func_name,
                            suggestion=f"Consider renaming to '{self._to_snake_case(func_name)}'",
                        ))

                elif stripped.startswith("class "):
                    class_name = self._extract_class_name(stripped)
                    if class_name and not class_name[0].isupper():
                        issues.append(QualityIssue(
                            file=file_path,
                            line=line_num,
                            issue_type="naming_convention",
                            severity="info",
                            message=f"Class '{class_name}' should use PascalCase",
                            symbol=class_name,
                            suggestion=f"Consider renaming to '{self._to_pascal_case(class_name)}'",
                        ))

        return issues

    def _extract_python_function_name(self, line: str) -> str:
        match = re.match(r'(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
        return match.group(1) if match else ""

    def _extract_js_function_name(self, line: str) -> str:
        patterns = [
            r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:async\s*)?function",
            r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",
        ]
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return "anonymous"

    def _extract_go_function_name(self, line: str) -> str:
        line = line[5:].strip()
        if line.startswith("("):
            paren_end = line.find(")")
            if paren_end > 0:
                line = line[paren_end + 1:]
        name = line.split("(")[0].strip()
        return name if name else "anonymous"

    def _extract_class_name(self, line: str) -> str:
        line = line.replace("class ", "").strip()
        for char in "(:[":
            idx = line.find(char)
            if idx > 0:
                line = line[:idx]
        return line.strip()

    def _find_python_block_end(self, lines: List[str], start: int) -> int:
        indent = len(lines[start]) - len(lines[start].lstrip())
        for i in range(start + 1, len(lines)):
            if lines[i].strip() and not lines[i].startswith(" " * (indent + 1)):
                return i
        return len(lines)

    def _find_js_block_end(self, lines: List[str], start: int) -> int:
        brace_count = 0
        for i in range(start, len(lines)):
            brace_count += lines[i].count("{") - lines[i].count("}")
            if brace_count == 0 and i > start:
                return i + 1
        return len(lines)

    def _find_go_block_end(self, lines: List[str], start: int) -> int:
        brace_count = 0
        for i in range(start, len(lines)):
            brace_count += lines[i].count("{") - lines[i].count("}")
            if brace_count == 0 and i > start:
                return i + 1
        return len(lines)

    def _to_snake_case(self, name: str) -> str:
        result = re.sub(r'([A-Z])', r'_\1', name)
        return result.lower().lstrip("_")

    def _to_pascal_case(self, name: str) -> str:
        parts = name.split("_")
        return "".join(p.capitalize() for p in parts if p)
