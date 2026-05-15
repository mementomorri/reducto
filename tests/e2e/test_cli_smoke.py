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
