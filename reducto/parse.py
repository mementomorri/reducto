"""Tree-sitter symbol extraction and complexity metrics."""

from __future__ import annotations

from functools import lru_cache

import tree_sitter_go as tsgo
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from reducto.models import ComplexityMetrics, Symbol
from reducto.models import Language as Lang

_PARSERS: dict[Lang, Parser] = {}


@lru_cache(maxsize=4)
def _parser(lang: Lang) -> Parser | None:
    try:
        if lang == Lang.PYTHON:
            language = Language(tspython.language())
        elif lang in (Lang.JAVASCRIPT, Lang.TYPESCRIPT):
            language = Language(tsjs.language())
        elif lang == Lang.GO:
            language = Language(tsgo.language())
        else:
            return None
        p = Parser(language)
        _PARSERS[lang] = p
        return p
    except Exception:
        return None


def get_symbols(content: str, path: str, language: Lang) -> list[Symbol]:
    parser = _parser(language)
    if not parser:
        return []
    tree = parser.parse(content.encode())
    lines = content.split("\n")
    if language == Lang.PYTHON:
        return _walk_python(tree.root_node, content.encode(), path, lines)
    if language in (Lang.JAVASCRIPT, Lang.TYPESCRIPT):
        return _walk_js(tree.root_node, content.encode(), path)
    if language == Lang.GO:
        return _walk_go(tree.root_node, content.encode(), path)
    return []


def _walk_python(
    node, source: bytes, path: str, lines: list[str], cls: str = "", indent: int = -1
) -> list[Symbol]:
    out: list[Symbol] = []
    for i in range(node.child_count):
        child = node.child(i)
        if child is None:
            continue
        kind = child.type
        if kind == "class_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode()
                start = child.start_point[0] + 1
                end = _python_block_end(lines, start - 1)
                out.append(
                    Symbol(name=name, type="class", file=path, start_line=start, end_line=end)
                )
                out.extend(_walk_python(child, source, path, lines, name, child.start_point[1]))
                continue
        if kind in ("function_definition", "async_function_definition"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = name_node.text.decode()
                stype = "method" if cls and child.start_point[1] > indent else "function"
                out.append(
                    Symbol(
                        name=name,
                        type=stype,
                        file=path,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                    )
                )
        out.extend(_walk_python(child, source, path, lines, cls, indent))
    return out


def _walk_js(node, source: bytes, path: str) -> list[Symbol]:
    out: list[Symbol] = []
    for i in range(node.child_count):
        child = node.child(i)
        if child is None:
            continue
        if child.type in (
            "function_declaration",
            "generator_function_declaration",
            "class_declaration",
        ):
            name_node = child.child_by_field_name("name")
            if name_node:
                stype = "class" if child.type == "class_declaration" else "function"
                out.append(
                    Symbol(
                        name=name_node.text.decode(),
                        type=stype,
                        file=path,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                    )
                )
        out.extend(_walk_js(child, source, path))
    return out


def _walk_go(node, source: bytes, path: str) -> list[Symbol]:
    out: list[Symbol] = []
    for i in range(node.child_count):
        child = node.child(i)
        if child is None:
            continue
        if child.type in ("function_declaration", "method_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                out.append(
                    Symbol(
                        name=name_node.text.decode(),
                        type="method" if child.type == "method_declaration" else "function",
                        file=path,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                    )
                )
        out.extend(_walk_go(child, source, path))
    return out


def _python_block_end(lines: list[str], start: int) -> int:
    if start >= len(lines):
        return len(lines)
    base = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip())) <= base:
            return i
    return len(lines)


def get_complexity(content: str) -> ComplexityMetrics:
    metrics = ComplexityMetrics(lines_of_code=max(1, content.count("\n") + 1))
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        for kw in ("if ", "elif ", "for ", "while ", "case ", "catch ", "&&", "||"):
            if kw in stripped:
                metrics.cyclomatic_complexity += 1
    return metrics
