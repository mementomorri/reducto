"""LSP client tests (skip if no language server on PATH)."""

import shutil

import pytest

from reducto.lsp.client import LSPError
from reducto.workspace import Workspace

pytestmark = pytest.mark.skipif(
    not shutil.which("pylsp") and not shutil.which("pyright-langserver"),
    reason="no Python LSP on PATH",
)


def test_find_references_python(tmp_path):
    f = tmp_path / "main.py"
    f.write_text("def foo():\n    return 1\n\nx = foo()\n")
    ws = Workspace(str(tmp_path))
    try:
        refs = ws.find_references("main.py", line=1, character=4)
        assert isinstance(refs, list)
    except LSPError:
        pytest.skip("LSP server failed to start")
    finally:
        ws.shutdown_lsp()
