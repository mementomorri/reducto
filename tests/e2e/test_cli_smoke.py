"""E2E smoke tests for reducto CLI."""

import subprocess
import sys


def test_help():
    r = subprocess.run(
        [sys.executable, "-m", "reducto.cli", "--help"], capture_output=True, text=True
    )
    assert r.returncode == 0
    assert "analyze" in r.stdout


def test_analyze_sample_repo():
    r = subprocess.run(
        [sys.executable, "-m", "reducto.cli", "analyze", "test-python-code/python"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0
    assert "Files:" in r.stdout


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "reducto.cli", *args],
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_check_sample_repo():
    r = _run_cli("check", "test-python-code/python")
    assert r.returncode == 0
    assert "Issues:" in r.stdout or "issues" in r.stdout.lower()


def test_idiomatize_sample_repo():
    r = _run_cli("idiomatize", "test-python-code/python", "--yes")
    assert r.returncode == 0


def test_deduplicate_sample_repo():
    r = _run_cli("deduplicate", "test-python-code/python/duplicates", "--yes")
    assert r.returncode == 0
    assert "session" in r.stdout.lower() or "duplicate" in r.stdout.lower()
