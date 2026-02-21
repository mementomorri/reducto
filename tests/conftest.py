"""
Pytest configuration and shared fixtures for MCP-based architecture.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator
import asyncio
import json

import pytest
import pytest_asyncio


@pytest.fixture
def test_fixtures_dir() -> Path:
    """Get fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True
    )
    
    yield repo_dir


@pytest.fixture
def mock_llm_env(monkeypatch):
    """Set environment variables for LLM mocking."""
    monkeypatch.setenv("LITELLM_MOCK", "true")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-mock-key")


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    code = '''
def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total

def calculate_average(numbers):
    """Calculate average of numbers."""
    if not numbers:
        return 0
    return calculate_sum(numbers) / len(numbers)

class Calculator:
    """Simple calculator class."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, value):
        self.result += value
        return self
    
    def multiply(self, value):
        self.result *= value
        return self
'''
    
    file_path = tmp_path / "calculator.py"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def sample_javascript_file(tmp_path: Path) -> Path:
    """Create a sample JavaScript file for testing."""
    code = '''
function calculateSum(numbers) {
    let total = 0;
    for (let num of numbers) {
        total += num;
    }
    return total;
}

function calculateAverage(numbers) {
    if (numbers.length === 0) {
        return 0;
    }
    return calculateSum(numbers) / numbers.length;
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(value) {
        this.result += value;
        return this;
    }
    
    multiply(value) {
        this.result *= value;
        return this;
    }
}
'''
    
    file_path = tmp_path / "calculator.js"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def sample_go_file(tmp_path: Path) -> Path:
    """Create a sample Go file for testing."""
    code = '''
package main

import "fmt"

func calculateSum(numbers []int) int {
    total := 0
    for _, num := range numbers {
        total += num
    }
    return total
}

func calculateAverage(numbers []int) float64 {
    if len(numbers) == 0 {
        return 0
    }
    return float64(calculateSum(numbers)) / float64(len(numbers))
}

type Calculator struct {
    result int
}

func (c *Calculator) Add(value int) *Calculator {
    c.result += value
    return c
}

func (c *Calculator) Multiply(value int) *Calculator {
    c.result *= value
    return c
}

func main() {
    fmt.Println("Calculator ready")
}
'''
    
    file_path = tmp_path / "calculator.go"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def multi_file_project(tmp_path: Path) -> Path:
    """Create a multi-file Python project for testing."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    
    (src_dir / "__init__.py").write_text("")
    
    (src_dir / "utils.py").write_text('''
from typing import List

def format_output(data: dict) -> str:
    return str(data)

def validate_input(items: List[str]) -> bool:
    return len(items) > 0
''')
    
    (src_dir / "main.py").write_text('''
from utils import format_output, validate_input

def process_items(items):
    if validate_input(items):
        result = {"items": items, "count": len(items)}
        return format_output(result)
    return "No items"
''')
    
    (tmp_path / "README.md").write_text("# Test Project")
    (tmp_path / "requirements.txt").write_text("pytest>=7.0.0")
    
    return tmp_path


@pytest.fixture
def duplicate_code_files(tmp_path: Path) -> Path:
    """Create files with duplicate code for testing."""
    (tmp_path / "auth.py").write_text('''
def validate_email(email):
    if not email:
        raise ValueError("Email required")
    if '@' not in email:
        raise ValueError("Invalid email format")
    if len(email) > 255:
        raise ValueError("Email too long")
    return email.lower().strip()

def validate_password(password):
    if not password:
        raise ValueError("Password required")
    if len(password) < 8:
        raise ValueError("Password too short")
    return password
''')
    
    (tmp_path / "user.py").write_text('''
def check_email_address(email_addr):
    if not email_addr:
        raise Exception("Email is required")
    if '@' not in email_addr:
        raise Exception("Email format is invalid")
    if len(email_addr) > 255:
        raise Exception("Email address too long")
    return email_addr.lower().strip()

def check_password(pwd):
    if not pwd:
        raise Exception("Password is required")
    if len(pwd) < 8:
        raise Exception("Password is too short")
    return pwd
''')
    
    return tmp_path


@pytest.fixture
def complex_python_file(tmp_path: Path) -> Path:
    """Create a Python file with high complexity for testing."""
    code = '''
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
'''
    
    file_path = tmp_path / "complex_processor.py"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def built_cli(tmp_path: Path) -> Path:
    """Build the CLI binary and return its path."""
    cli_path = tmp_path / "reducto"
    
    result = subprocess.run(
        ["go", "build", "-o", str(cli_path), "./cmd/reducto"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build CLI: {result.stderr}")
    
    return cli_path


@pytest.fixture
def cli_runner(built_cli: Path):
    """Provide CLI test runner."""
    from subprocess import CompletedProcess
    
    def run_cli(args: list, cwd: Path = None, input_data: str = None, timeout: int = 30) -> CompletedProcess:
        """Run reducto CLI with given arguments."""
        cmd = [str(built_cli)] + args
        
        return subprocess.run(
            cmd,
            cwd=cwd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout
        )
    
    return run_cli


@pytest_asyncio.fixture
async def mcp_client():
    """Create an MCP client for testing."""
    from ai_sidecar.mcp import MCPClient
    
    client = MCPClient()
    yield client
    
    if client._writer:
        client._writer.close()


class MockMCPResponse:
    """Mock MCP response for testing."""
    
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server for unit testing."""
    class MockServer:
        def __init__(self):
            self.tools_called = []
            self.responses = {}
        
        def set_response(self, method: str, result):
            self.responses[method] = result
        
        async def call_tool(self, method: str, params: dict):
            self.tools_called.append((method, params))
            if method in self.responses:
                return self.responses[method]
            return {}
    
    return MockServer()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent
