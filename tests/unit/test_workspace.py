"""Workspace safety tests."""

import pytest

from reducto.runner import TestResult as RunnerTestResult
from reducto.workspace import PathEscapeError, Workspace


def test_path_escape(tmp_path):
    ws = Workspace(str(tmp_path))
    with pytest.raises(PathEscapeError):
        ws.read_file("../../etc/passwd")


def test_apply_changes_no_git(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n")
    ws = Workspace(str(tmp_path))
    diff = "--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n"
    r = ws.apply_changes_safe([("a.py", diff)], run_tests=False)
    assert r["success"]
    assert f.read_text() == "x = 2\n"


def test_apply_changes_rollback_on_bad_diff(temp_git_repo):
    ws = Workspace(str(temp_git_repo))
    main = temp_git_repo / "main.py"
    good = "--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n"
    bad = "@@@ not a valid hunk @@@"
    r = ws.apply_changes_safe([("main.py", good), ("main.py", bad)], run_tests=False)
    assert not r["success"]
    assert r.get("rolled_back")
    assert main.read_text().strip() == "x = 1"


def test_apply_changes_test_failure_reports_zero_applied(temp_git_repo, monkeypatch):
    ws = Workspace(str(temp_git_repo))
    diff = "--- a/main.py\n+++ b/main.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2\n"
    monkeypatch.setattr(
        ws._runner,
        "run_tests",
        lambda: RunnerTestResult(success=False, output="fail", command="pytest", exit_code=1),
    )
    r = ws.apply_changes_safe([("main.py", diff)], run_tests=True)
    assert not r["success"]
    assert r.get("rolled_back")
    assert r["applied"] == 0
    assert (temp_git_repo / "main.py").read_text().strip() == "x = 1"
