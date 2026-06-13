"""E2E smoke tests for the reducto CLI (hermetic — never mutate the tracked corpus)."""

import subprocess
import sys


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "reducto.cli", *args],
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_help():
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "analyze" in r.stdout


def test_analyze_sample_repo(sample_repo):
    r = _run_cli("analyze", str(sample_repo))
    assert r.returncode == 0
    assert "Files:" in r.stdout
    assert "Symbols: 0" not in r.stdout  # parser must extract symbols


def test_check_sample_repo(sample_repo):
    r = _run_cli("check", str(sample_repo))
    assert r.returncode == 0
    assert "Issues:" in r.stdout


def test_idiomatize_sample_repo(sample_repo):
    r = _run_cli("idiomatize", str(sample_repo), "--yes")
    assert r.returncode == 0


def test_deduplicate_sample_repo(sample_repo):
    r = _run_cli("deduplicate", str(sample_repo / "duplicates"), "--yes")
    assert r.returncode == 0
    assert "duplicate" in r.stdout.lower()


def test_apply_unknown_session_exits_1(sample_repo):
    r = _run_cli("apply", "does-not-exist", str(sample_repo))
    assert r.returncode == 1
    assert "not found" in r.stderr.lower()


def test_sessions_show_unknown_exits_1(sample_repo):
    r = _run_cli("sessions", "show", "nope", "-C", str(sample_repo))
    assert r.returncode == 1
