"""Project test runner."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    success: bool
    output: str
    command: str
    exit_code: int = 0


class ProjectRunner:
    def __init__(self, path: str):
        self.path = Path(path).resolve()

    def _exists(self, name: str) -> bool:
        return (self.path / name).exists()

    def _project_type(self) -> str:
        if self._exists("go.mod"):
            return "go"
        if (
            self._exists("pyproject.toml")
            or self._exists("setup.py")
            or self._exists("requirements.txt")
        ):
            return "python"
        if self._exists("package.json"):
            pkg = (self.path / "package.json").read_text()
            return "typescript" if "typescript" in pkg else "javascript"
        return "unknown"

    def _run(self, cmd: list[str]) -> TestResult:
        proc = subprocess.run(cmd, cwd=self.path, capture_output=True, text=True, timeout=300)
        out = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
        return TestResult(
            success=proc.returncode == 0,
            output=out.strip(),
            command=" ".join(cmd),
            exit_code=proc.returncode,
        )

    def run_tests(self) -> TestResult:
        pt = self._project_type()
        if pt == "python":
            cmd = (
                ["python", "-m", "pytest", "-x", "-q"]
                if self._exists("pytest.ini") or self._exists("pyproject.toml")
                else ["python", "-m", "unittest", "discover", "-v"]
            )
        elif pt in ("javascript", "typescript"):
            cmd = ["npm", "test"]
        elif pt == "go":
            cmd = ["go", "test", "./..."]
        else:
            return TestResult(success=True, output="No test command detected", command="")
        return self._run(cmd)
