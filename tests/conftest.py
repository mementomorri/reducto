"""
Pytest configuration and shared fixtures.
"""

import os
import subprocess
from pathlib import Path
from typing import Generator

import pytest


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
''')
    
    return tmp_path


@pytest.fixture(scope="session")
def python_sidecar():
    """Start minimal test sidecar for integration tests."""
    import time
    import requests
    import signal
    
    # Use the minimal test sidecar instead of full sidecar
    proc = subprocess.Popen(
        [sys.executable, "tests/test_sidecar.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    try:
        # Wait for sidecar to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:9876/health", timeout=1)
                if response.status_code == 200:
                    break
            except:
                if i == max_retries - 1:
                    proc.terminate()
                    stdout, stderr = proc.communicate(timeout=5)
                    raise RuntimeError(
                        f"Test sidecar failed to start.\n"
                        f"stdout: {stdout.decode()}\n"
                        f"stderr: {stderr.decode()}"
                    )
                time.sleep(1)
        
        yield proc
    finally:
        # Cleanup
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=5)
        except:
            proc.kill()


@pytest.fixture
def cli_runner():
    """Provide CLI test runner."""
    from subprocess import CompletedProcess
    
    def run_cli(args: list, cwd: Path = None, input: str = None) -> CompletedProcess:
        """Run dehydrate CLI with given arguments."""
        cmd = ["python", "-m", "ai_sidecar.main"] + args
        
        return subprocess.run(
            cmd,
            cwd=cwd,
            input=input,
            capture_output=True,
            text=True
        )
    
    return run_cli
