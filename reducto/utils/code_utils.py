"""Helpers for quality checker."""

import re


def extract_python_function_name(line: str) -> str:
    m = re.match(r"(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
    return m.group(1) if m else ""


def extract_js_function_name(line: str) -> str | None:
    for pat in (r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)", r"const\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*="):
        m = re.search(pat, line)
        if m:
            return m.group(1)
    return None


def extract_go_function_name(line: str) -> str:
    line = line.strip().removeprefix("func ").strip()
    if line.startswith("("):
        line = line[line.find(")") + 1 :]
    return line.split("(")[0].strip() or "anonymous"


def find_python_block_end(lines: list[str], start: int) -> int:
    if start >= len(lines):
        return len(lines)
    indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        if lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip())) <= indent:
            return i
    return len(lines)


def find_js_block_end(lines: list[str], start: int) -> int:
    braces = 0
    for i in range(start, len(lines)):
        braces += lines[i].count("{") - lines[i].count("}")
        if braces == 0 and i > start:
            return i + 1
    return len(lines)


def extract_class_name(line: str) -> str:
    line = line.replace("class ", "").strip()
    for char in "(:[{":
        idx = line.find(char)
        if idx > 0:
            line = line[:idx]
    return line.strip()


def to_snake_case(name: str) -> str:
    return re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")


def to_pascal_case(name: str) -> str:
    return "".join(p.capitalize() for p in name.split("_") if p)
