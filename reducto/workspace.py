"""Workspace facade — in-process repo tools."""

from __future__ import annotations

import hashlib
from pathlib import Path

from reducto import diff as diff_mod
from reducto import parse, repo
from reducto.git_safety import GitError, GitSafety
from reducto.models import AppConfig, ComplexityMetrics, FileChange, FileInfo, Symbol
from reducto.lsp import LSPManager, Reference
from reducto.runner import ProjectRunner


class PathEscapeError(ValueError):
    pass


class Workspace:
    def __init__(self, root_dir: str, cfg: AppConfig | None = None):
        self.root = Path(root_dir).resolve()
        self.cfg = cfg or AppConfig()
        self._git = GitSafety(str(self.root))
        self._runner = ProjectRunner(str(self.root))
        self._lsp: LSPManager | None = None

    def _resolve_path(self, path: str) -> Path:
        full = (self.root / path).resolve()
        try:
            full.relative_to(self.root)
        except ValueError as e:
            raise PathEscapeError(f"path escapes workspace: {path}") from e
        return full

    def list_files(self) -> list[FileInfo]:
        return repo.walk(
            str(self.root),
            self.cfg.exclude_patterns,
            self.cfg.include_patterns,
        )

    def read_file(self, path: str) -> FileInfo:
        full = self._resolve_path(path)
        content = full.read_text(encoding="utf-8", errors="replace")
        rel = str(full.relative_to(self.root))
        h = hashlib.sha256(content.encode()).hexdigest()
        return FileInfo(path=rel, content=content, hash=h)

    def get_symbols(self, path: str, content: str | None = None) -> list[Symbol]:
        if content is None:
            content = self.read_file(path).content
        lang = repo.detect_language(path)
        symbols = parse.get_symbols(content, path, lang)
        for s in symbols:
            if not s.file:
                s.file = path
        return symbols

    def get_complexity(self, path: str, content: str | None = None) -> ComplexityMetrics:
        if content is None:
            content = self.read_file(path).content
        return parse.get_complexity(content)

    def _lsp_mgr(self) -> LSPManager:
        if self._lsp is None:
            self._lsp = LSPManager(str(self.root))
        return self._lsp

    def find_references(self, path: str, line: int, character: int = 0) -> list[Reference]:
        return self._lsp_mgr().find_references(path, line, character)

    def shutdown_lsp(self) -> None:
        if self._lsp:
            self._lsp.shutdown()
            self._lsp = None

    def apply_diff(self, path: str, diff_text: str) -> dict:
        full = self._resolve_path(path)
        original = full.read_text(encoding="utf-8") if full.exists() else ""
        new_content = diff_mod.apply_unified_diff(original, diff_text)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(new_content, encoding="utf-8")
        rel = str(full.relative_to(self.root))
        return {"success": True, "path": rel}

    def apply_diff_safe(
        self,
        path: str,
        diff_text: str,
        run_tests: bool = True,
        *,
        use_git: bool = True,
    ) -> dict:
        if use_git and self._git.is_repo():
            try:
                checkpoint = self._git.create_checkpoint("reducto checkpoint before diff")
            except GitError as e:
                return {"success": False, "path": path, "error": str(e)}
            try:
                self.apply_diff(path, diff_text)
            except Exception as e:
                try:
                    self._git.rollback()
                except GitError:
                    pass
                return {
                    "success": False,
                    "path": path,
                    "checkpoint": checkpoint,
                    "rolled_back": True,
                    "error": str(e),
                }
            if not run_tests:
                return {
                    "success": True,
                    "path": path,
                    "checkpoint": checkpoint,
                    "tests_run": False,
                    "tests_passed": True,
                    "rolled_back": False,
                }
            result = self._runner.run_tests()
            if not result.success:
                try:
                    self._git.rollback()
                except GitError:
                    pass
                return {
                    "success": False,
                    "path": path,
                    "checkpoint": checkpoint,
                    "tests_run": True,
                    "tests_passed": False,
                    "rolled_back": True,
                    "test_output": result.output,
                    "error": "Tests failed after diff, rolled back",
                }
            return {
                "success": True,
                "path": path,
                "checkpoint": checkpoint,
                "tests_run": True,
                "tests_passed": True,
                "rolled_back": False,
                "test_output": result.output,
            }
        # no git: apply only
        try:
            self.apply_diff(path, diff_text)
        except Exception as e:
            return {"success": False, "path": path, "error": str(e)}
        if run_tests:
            result = self._runner.run_tests()
            return {
                "success": result.success,
                "path": path,
                "tests_run": True,
                "tests_passed": result.success,
                "test_output": result.output,
                "error": None if result.success else "tests failed",
            }
        return {"success": True, "path": path, "tests_run": False, "tests_passed": True}

    def apply_changes_safe(
        self,
        changes: list[tuple[str, str]],
        run_tests: bool = True,
    ) -> dict:
        """Apply multiple diffs under one checkpoint; rollback all on failure."""
        if not changes:
            return {"success": True, "applied": 0}
        checkpoint = None
        if self._git.is_repo():
            try:
                checkpoint = self._git.create_checkpoint("reducto checkpoint before plan")
            except GitError as e:
                return {"success": False, "error": str(e), "applied": 0}
        for path, diff_text in changes:
            try:
                self.apply_diff(path, diff_text)
            except Exception as e:
                if checkpoint:
                    try:
                        self._git.rollback()
                    except GitError:
                        pass
                return {
                    "success": False,
                    "error": str(e),
                    "path": path,
                    "rolled_back": bool(checkpoint),
                    "applied": 0,
                }
        if run_tests:
            result = self._runner.run_tests()
            if not result.success:
                if checkpoint:
                    try:
                        self._git.rollback()
                    except GitError:
                        pass
                return {
                    "success": False,
                    "tests_passed": False,
                    "rolled_back": bool(checkpoint),
                    "test_output": result.output,
                    "error": "Tests failed after plan, rolled back",
                    "applied": len(changes),
                }
        return {
            "success": True,
            "tests_passed": True,
            "rolled_back": False,
            "applied": len(changes),
            "checkpoint": checkpoint,
        }

    def commit_changes(self, message: str, changes: list[FileChange]) -> None:
        if self._git.is_repo():
            self._git.commit(message, changes)

    def run_tests(self) -> dict:
        r = self._runner.run_tests()
        return {
            "success": r.success,
            "output": r.output,
            "command": r.command,
            "exit_code": r.exit_code,
        }

    def git_checkpoint(self, message: str) -> dict:
        try:
            h = self._git.create_checkpoint(message)
            return {"success": True, "commit_hash": h}
        except GitError as e:
            return {"success": False, "error": str(e)}

    def git_rollback(self) -> dict:
        try:
            self._git.rollback()
            return {"success": True}
        except GitError as e:
            return {"success": False, "error": str(e)}

    def is_git_clean(self) -> bool:
        return self._git.is_clean()
