"""
End-to-end tests for repository analysis and context mapping.
From TEST_RULES.md Category 1.
Tests the CLI binary directly via subprocess.
"""

import json
import subprocess
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def built_cli(tmp_path: Path) -> Path:
    """Build the CLI binary and return its path."""
    cli_path = tmp_path / "reducto"

    result = subprocess.run(
        ["go", "build", "-o", str(cli_path), "./cmd/reducto"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to build CLI: {result.stderr}")

    return cli_path


@pytest.fixture
def sample_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a sample project for testing."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "__init__.py").write_text("")

    (src_dir / "utils.py").write_text('''
from typing import List

def format_output(data: dict) -> str:
    """Format data as string."""
    return str(data)

def validate_input(items: List[str]) -> bool:
    """Validate input items."""
    return len(items) > 0
''')

    (src_dir / "main.py").write_text('''
from utils import format_output, validate_input

def process_items(items):
    """Process a list of items."""
    if validate_input(items):
        result = {"items": items, "count": len(items)}
        return format_output(result)
    return "No items"

def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total
''')

    yield tmp_path


@pytest.fixture
def complex_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a project with complex code for testing."""
    (tmp_path / "complex.py").write_text('''
def process_data(data, options=None):
    """Process data with various options."""
    if options is None:
        options = {}

    results = []
    errors = []

    for item in data:
        if item is None:
            errors.append("Null item found")
            continue

        if isinstance(item, dict):
            if 'type' in item:
                if item['type'] == 'user':
                    if 'email' in item:
                        if '@' in item['email']:
                            results.append({'type': 'valid_user', 'email': item['email']})
                        else:
                            errors.append(f"Invalid email: {item['email']}")
                    else:
                        errors.append("User missing email")
                elif item['type'] == 'admin':
                    if 'permissions' in item:
                        if isinstance(item['permissions'], list):
                            if len(item['permissions']) > 0:
                                results.append({'type': 'valid_admin', 'permissions': item['permissions']})
                            else:
                                errors.append("Admin has no permissions")
                        else:
                            errors.append("Invalid permissions format")
                    else:
                        errors.append("Admin missing permissions")
                else:
                    errors.append(f"Unknown type: {item['type']}")
            else:
                errors.append("Item missing type")
        elif isinstance(item, str):
            if item.startswith('user:'):
                email = item[5:]
                if '@' in email:
                    results.append({'type': 'valid_user', 'email': email})
                else:
                    errors.append(f"Invalid email: {email}")
            elif item.startswith('admin:'):
                parts = item[6:].split(',')
                if len(parts) > 0:
                    results.append({'type': 'valid_admin', 'permissions': parts})
                else:
                    errors.append("Admin has no permissions")
            else:
                errors.append(f"Unknown string format: {item}")
        else:
            errors.append(f"Unknown item type: {type(item)}")

    if options.get('verbose'):
        return {'results': results, 'errors': errors, 'count': len(results)}

    return results
''')

    yield tmp_path


@pytest.fixture
def multi_language_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a multi-language project for testing."""
    (tmp_path / "main.py").write_text('''
def python_func():
    """A Python function."""
    return "hello from python"

class PythonClass:
    """A Python class."""
    def method(self):
        return "method"
''')

    (tmp_path / "app.js").write_text('''
function jsFunc() {
    return "hello from js";
}

class JSClass {
    method() {
        return "js method";
    }
}
''')

    (tmp_path / "main.go").write_text('''package main

import "fmt"

func goFunc() string {
    return "hello from go"
}

func main() {
    fmt.Println(goFunc())
}
''')

    yield tmp_path


@pytest.fixture
def duplicate_code_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create files with duplicate code patterns."""
    (tmp_path / "auth.py").write_text('''
def validate_email(email):
    """Validate email address."""
    if not email:
        raise ValueError("Email required")
    if '@' not in email:
        raise ValueError("Invalid email format")
    if len(email) > 255:
        raise ValueError("Email too long")
    return email.lower().strip()

def validate_password(password):
    """Validate password."""
    if not password:
        raise ValueError("Password required")
    if len(password) < 8:
        raise ValueError("Password too short")
    return password
''')

    (tmp_path / "user.py").write_text('''
def check_email_address(email_addr):
    """Check email address."""
    if not email_addr:
        raise Exception("Email is required")
    if '@' not in email_addr:
        raise Exception("Email format is invalid")
    if len(email_addr) > 255:
        raise Exception("Email address too long")
    return email_addr.lower().strip()

def check_password(pwd):
    """Check password."""
    if not pwd:
        raise Exception("Password is required")
    if len(pwd) < 8:
        raise Exception("Password is too short")
    return pwd
''')

    yield tmp_path


class TestMCPServerAnalysis:
    """Test MCP server analysis capabilities via JSON-RPC."""

    @pytest.mark.e2e
    def test_list_files(self, sample_project: Path, built_cli: Path):
        """Test listing files in a project."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "list_files", "params": {}})

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{list_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            list_response = json.loads(lines[1])
            assert "result" in list_response

            files = list_response["result"]["files"]
            assert len(files) >= 2

            file_paths = [f["path"] for f in files]
            assert any("utils.py" in p for p in file_paths)
            assert any("main.py" in p for p in file_paths)
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_get_symbols(self, sample_project: Path, built_cli: Path):
        """Test symbol extraction."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        symbols_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_symbols",
            "params": {"path": "src/main.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{symbols_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            symbols_response = json.loads(lines[1])
            assert "result" in symbols_response

            symbols = symbols_response["result"]["symbols"]
            symbol_names = [s["name"] for s in symbols]

            assert "process_items" in symbol_names
            assert "calculate_sum" in symbol_names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_get_complexity(self, complex_project: Path, built_cli: Path):
        """Test complexity calculation."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        complexity_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_complexity",
            "params": {"path": "complex.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(complex_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{complexity_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            complexity_response = json.loads(lines[1])
            assert "result" in complexity_response

            metrics = complexity_response["result"]["metrics"]
            assert metrics["lines_of_code"] > 0
            assert metrics["cyclomatic_complexity"] > 10
            assert metrics["cognitive_complexity"] > 10
        finally:
            proc.terminate()
            proc.wait()


class TestMultiLanguageSupport:
    """Test multi-language support."""

    @pytest.mark.e2e
    def test_python_symbols(self, multi_language_project: Path, built_cli: Path):
        """Test Python symbol extraction."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        symbols_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_symbols",
            "params": {"path": "main.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(multi_language_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{symbols_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            symbols_response = json.loads(lines[1])
            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "python_func" in names
            assert "PythonClass" in names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_javascript_symbols(self, multi_language_project: Path, built_cli: Path):
        """Test JavaScript symbol extraction."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        symbols_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_symbols",
            "params": {"path": "app.js"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(multi_language_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{symbols_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            symbols_response = json.loads(lines[1])
            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "jsFunc" in names
            assert "JSClass" in names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_go_symbols(self, multi_language_project: Path, built_cli: Path):
        """Test Go symbol extraction."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        symbols_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_symbols",
            "params": {"path": "main.go"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(multi_language_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{symbols_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            symbols_response = json.loads(lines[1])
            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "goFunc" in names
            assert "main" in names
        finally:
            proc.terminate()
            proc.wait()


class TestDiffApplication:
    """Test diff application functionality."""

    @pytest.mark.e2e
    def test_apply_simple_diff(self, sample_project: Path, built_cli: Path):
        """Test applying a simple unified diff."""
        test_file = sample_project / "test.py"
        test_file.write_text("def old_name():\n    pass\n")

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        diff_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "apply_diff",
            "params": {
                "path": "test.py",
                "diff": "--- a/test.py\n+++ b/test.py\n@@ -1,2 +1,2 @@\n-def old_name():\n+def new_name():\n     pass\n"
            }
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{diff_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            diff_response = json.loads(lines[1])
            assert "result" in diff_response
            assert diff_response["result"]["success"] is True

            updated_content = test_file.read_text()
            assert "new_name" in updated_content
            assert "old_name" not in updated_content
        finally:
            proc.terminate()
            proc.wait()


class TestGitIntegration:
    """Test Git integration."""

    @pytest.mark.e2e
    def test_git_checkpoint(self, sample_project: Path, built_cli: Path):
        """Test creating a Git checkpoint."""
        subprocess.run(["git", "init"], cwd=sample_project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=sample_project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=sample_project, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=sample_project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=sample_project, check=True, capture_output=True)

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        checkpoint_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "git_checkpoint",
            "params": {"message": "test checkpoint"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{checkpoint_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            checkpoint_response = json.loads(lines[1])
            assert "result" in checkpoint_response
            assert checkpoint_response["result"]["success"] is True
            assert "commit_hash" in checkpoint_response["result"]
        finally:
            proc.terminate()
            proc.wait()


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.e2e
    def test_file_not_found_error(self, sample_project: Path, built_cli: Path):
        """Test error when file doesn't exist."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        read_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "read_file",
            "params": {"path": "nonexistent.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{read_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            read_response = json.loads(lines[1])
            assert "error" in read_response
            assert read_response["error"]["code"] != 0
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_invalid_diff_error(self, sample_project: Path, built_cli: Path):
        """Test error when diff is invalid."""
        test_file = sample_project / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        diff_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "apply_diff",
            "params": {
                "path": "test.py",
                "diff": "this is not a valid diff"
            }
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(sample_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{diff_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            diff_response = json.loads(lines[1])
            assert "error" in diff_response
        finally:
            proc.terminate()
            proc.wait()
