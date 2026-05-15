"""Pytest fixtures."""

import subprocess
from pathlib import Path

import pytest

from reducto.models import ComplexityMetrics

FIXTURE_REPO = Path(__file__).resolve().parents[1] / "test-python-code" / "python"


@pytest.fixture
def fixture_repo_root() -> Path:
    return FIXTURE_REPO


@pytest.fixture
def fixture_files():
    from reducto.repo import walk

    return walk(str(FIXTURE_REPO))


@pytest.fixture
def sample_complexity_metrics() -> ComplexityMetrics:
    return ComplexityMetrics(
        cyclomatic_complexity=5,
        cognitive_complexity=3,
        lines_of_code=20,
    )


@pytest.fixture
def temp_git_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@e.com"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True
    )
    (repo / "main.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo
