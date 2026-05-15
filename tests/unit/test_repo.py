"""Unit tests for repo walking."""

from pathlib import Path

from reducto.models import Language
from reducto.repo import detect_language, walk


def test_detect_language():
    assert detect_language("foo.py") == Language.PYTHON
    assert detect_language("bar.go") == Language.GO


def test_walk_excludes_git(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    files = walk(str(tmp_path))
    assert len(files) == 1
    assert files[0].path == "a.py"
