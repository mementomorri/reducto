"""
Integration tests for MCP protocol communication.
Tests the Go MCP Server and Python MCP Client.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest


class MockMCPServer:
    """Mock MCP server for testing Python client."""

    def __init__(self, responses: dict = None):
        self.responses = responses or {}
        self.requests_received = []

    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC request."""
        self.requests_received.append(request)

        method = request.get("method", "")
        req_id = request.get("id")

        if method in self.responses:
            result = self.responses[method]
            return {"jsonrpc": "2.0", "result": result, "id": req_id}

        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": req_id,
        }


@pytest.fixture
def temp_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary project for testing."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    (src_dir / "__init__.py").write_text("")
    (src_dir / "main.py").write_text('''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

class Calculator:
    """Simple calculator."""

    def __init__(self):
        self.value = 0

    def add(self, x: int) -> "Calculator":
        self.value += x
        return self
''')

    yield tmp_path


@pytest.fixture
def temp_go_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary Go project for testing."""
    (tmp_path / "go.mod").write_text('''module example.com/test

go 1.21
''')

    (tmp_path / "main.go").write_text('''package main

import "fmt"

func add(a, b int) int {
    return a + b
}

func main() {
    fmt.Println(add(1, 2))
}
''')

    yield tmp_path


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


class TestMCPServerIntegration:
    """Test Go MCP Server via JSON-RPC protocol."""

    @pytest.mark.integration
    def test_mcp_server_initialize(self, temp_project: Path, built_cli: Path):
        """Test MCP server initialize method."""
        import os

        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input=init_request + "\n", timeout=5)

            response = json.loads(stdout.strip())
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert response["result"]["status"] == "initialized"
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_mcp_server_list_files(self, temp_project: Path, built_cli: Path):
        """Test MCP server list_files method."""
        import os

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "list_files", "params": {}}),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            assert len(lines) >= 2

            list_response = json.loads(lines[1])
            assert "result" in list_response
            assert "files" in list_response["result"]
            assert list_response["result"]["total"] > 0
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_mcp_server_get_symbols(self, temp_project: Path, built_cli: Path):
        """Test MCP server get_symbols method."""
        import os

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "get_symbols",
                "params": {"path": "src/main.py"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            symbols_response = json.loads(lines[1])

            assert "result" in symbols_response
            assert "symbols" in symbols_response["result"]

            symbols = symbols_response["result"]["symbols"]
            symbol_names = [s["name"] for s in symbols]

            assert "hello" in symbol_names
            assert "add" in symbol_names
            assert "Calculator" in symbol_names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_mcp_server_read_file(self, temp_project: Path, built_cli: Path):
        """Test MCP server read_file method."""
        import os

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "read_file",
                "params": {"path": "src/main.py"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            file_response = json.loads(lines[1])

            assert "result" in file_response
            assert "content" in file_response["result"]
            assert "hello" in file_response["result"]["content"]
            assert "hash" in file_response["result"]
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_mcp_server_get_complexity(self, temp_project: Path, built_cli: Path):
        """Test MCP server get_complexity method."""
        import os

        complex_code = '''
def process_data(data):
    """Process data with complex logic."""
    result = []
    for item in data:
        if item is None:
            continue
        if isinstance(item, dict):
            if 'value' in item:
                if item['value'] > 0:
                    result.append(item['value'])
                else:
                    result.append(0)
    return result
'''
        (temp_project / "complex.py").write_text(complex_code)

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "get_complexity",
                "params": {"path": "complex.py"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            complexity_response = json.loads(lines[1])

            assert "result" in complexity_response
            assert "metrics" in complexity_response["result"]
            metrics = complexity_response["result"]["metrics"]
            assert "lines_of_code" in metrics
            assert metrics["lines_of_code"] > 0
        finally:
            proc.terminate()
            proc.wait()


class TestCLICommands:
    """Test CLI commands directly."""

    @pytest.mark.integration
    def test_cli_version(self, built_cli: Path):
        """Test version command."""
        result = subprocess.run(
            [str(built_cli), "version"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "reducto" in result.stdout

    @pytest.mark.integration
    def test_cli_help(self, built_cli: Path):
        """Test help command."""
        result = subprocess.run(
            [str(built_cli), "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "analyze" in result.stdout
        assert "deduplicate" in result.stdout

    @pytest.mark.integration
    def test_cli_analyze_help(self, built_cli: Path):
        """Test analyze command help."""
        result = subprocess.run(
            [str(built_cli), "analyze", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "repository" in result.stdout.lower() or "path" in result.stdout.lower()


class TestMCPErrorHandling:
    """Test MCP error responses."""

    @pytest.mark.integration
    def test_method_not_found(self, temp_project: Path, built_cli: Path):
        """Test error response for unknown method."""
        import os

        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown_method",
            "params": {}
        })

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input=request + "\n", timeout=5)

            response = json.loads(stdout.strip())
            assert "error" in response
            assert response["error"]["code"] == -32601
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_file_not_found(self, temp_project: Path, built_cli: Path):
        """Test error response for non-existent file."""
        import os

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "read_file",
                "params": {"path": "nonexistent.py"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            file_response = json.loads(lines[1])

            assert "error" in file_response
        finally:
            proc.terminate()
            proc.wait()


class TestMultiLanguage:
    """Test multi-language support."""

    @pytest.mark.integration
    def test_python_symbol_extraction(self, temp_project: Path, built_cli: Path):
        """Test Python symbol extraction."""
        import os

        (temp_project / "test.py").write_text('''
def foo():
    pass

class Bar:
    def method(self):
        pass
''')

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "get_symbols",
                "params": {"path": "test.py"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            symbols_response = json.loads(lines[1])

            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "foo" in names
            assert "Bar" in names
            assert "method" in names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_javascript_symbol_extraction(self, temp_project: Path, built_cli: Path):
        """Test JavaScript symbol extraction."""
        import os

        (temp_project / "test.js").write_text('''
function foo() {
    return 1;
}

class Bar {
    method() {
        return 2;
    }
}

const arrow = () => 3;
''')

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "get_symbols",
                "params": {"path": "test.js"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            symbols_response = json.loads(lines[1])

            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "foo" in names
            assert "Bar" in names
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.integration
    def test_go_symbol_extraction(self, temp_go_project: Path, built_cli: Path):
        """Test Go symbol extraction."""
        import os

        requests = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "get_symbols",
                "params": {"path": "main.go"}
            }),
        ]

        env = os.environ.copy()
        env["NO_SIDECAR"] = "1"

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(temp_go_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        try:
            stdout, _ = proc.communicate(input="\n".join(requests) + "\n", timeout=10)

            lines = stdout.strip().split("\n")
            symbols_response = json.loads(lines[1])

            symbols = symbols_response["result"]["symbols"]
            names = [s["name"] for s in symbols]

            assert "add" in names
            assert "main" in names
        finally:
            proc.terminate()
            proc.wait()
