"""
End-to-end tests for semantic compression and refactoring.
From TEST_RULES.md Category 2.
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


@pytest.fixture
def non_idiomatic_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create non-idiomatic Python code."""
    (tmp_path / "non_idiomatic.py").write_text('''
# Non-idiomatic list filtering
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
evens = []
for num in numbers:
    if num % 2 == 0:
        evens.append(num)

# Non-idiomatic string formatting
name = "Alice"
age = 30
message = "Hello, " + name + "! You are " + str(age) + " years old."

# Non-idiomatic file reading
file = open("data.txt", "r")
try:
    content = file.read()
finally:
    file.close()

# Non-idiomatic dictionary building
result = {}
for item in items:
    if item.value > 0:
        result[item.key] = item.value
''')

    yield tmp_path


@pytest.fixture
def complex_conditional_project(tmp_path: Path) -> Generator[Path, None, None]:
    """Create complex conditional code for pattern injection tests."""
    (tmp_path / "complex.py").write_text('''
def process_payment(payment_type, amount, currency):
    """Process payment based on type, amount, and currency."""
    if payment_type == "credit_card":
        if currency == "USD":
            if amount > 10000:
                return process_high_value_cc_usd()
            else:
                return process_standard_cc_usd()
        elif currency == "EUR":
            if amount > 9000:
                return process_high_value_cc_eur()
            else:
                return process_standard_cc_eur()
    elif payment_type == "paypal":
        if currency == "USD":
            return process_paypal_usd()
        elif currency == "EUR":
            return process_paypal_eur()
    elif payment_type == "bank_transfer":
        if currency == "USD":
            if amount > 50000:
                return process_wire_usd()
            else:
                return process_ach_usd()
    else:
        raise ValueError("Unsupported payment type")

def process_high_value_cc_usd():
    pass

def process_standard_cc_usd():
    pass

def process_high_value_cc_eur():
    pass

def process_standard_cc_eur():
    pass

def process_paypal_usd():
    pass

def process_paypal_eur():
    pass

def process_wire_usd():
    pass

def process_ach_usd():
    pass
''')

    yield tmp_path


class TestDeduplicationDetection:
    """Test duplicate code detection capabilities."""

    @pytest.mark.e2e
    def test_list_files_with_duplicates(self, duplicate_code_project: Path, built_cli: Path):
        """Test that duplicate files are listed."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        list_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "list_files", "params": {}})

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(duplicate_code_project)],
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
            file_paths = [f["path"] for f in files]

            assert "auth.py" in file_paths
            assert "user.py" in file_paths
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_extract_symbols_from_duplicates(self, duplicate_code_project: Path, built_cli: Path):
        """Test symbol extraction from files with duplicates."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})

        auth_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_symbols",
            "params": {"path": "auth.py"}
        })

        user_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "get_symbols",
            "params": {"path": "user.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(duplicate_code_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{auth_req}\n{user_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            auth_response = json.loads(lines[1])
            user_response = json.loads(lines[2])

            auth_symbols = auth_response["result"]["symbols"]
            user_symbols = user_response["result"]["symbols"]

            auth_names = [s["name"] for s in auth_symbols]
            user_names = [s["name"] for s in user_symbols]

            assert "validate_email" in auth_names
            assert "validate_password" in auth_names
            assert "check_email_address" in user_names
            assert "check_password" in user_names
        finally:
            proc.terminate()
            proc.wait()


class TestComplexityAnalysis:
    """Test complexity analysis for refactoring."""

    @pytest.mark.e2e
    def test_complexity_hotspot_detection(self, complex_conditional_project: Path, built_cli: Path):
        """Test detection of complexity hotspots."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        complexity_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_complexity",
            "params": {"path": "complex.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(complex_conditional_project)],
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
            assert metrics["cyclomatic_complexity"] > 5
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_non_idiomatic_complexity(self, non_idiomatic_project: Path, built_cli: Path):
        """Test complexity analysis of non-idiomatic code."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        complexity_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "get_complexity",
            "params": {"path": "non_idiomatic.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(non_idiomatic_project)],
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
        finally:
            proc.terminate()
            proc.wait()


class TestCodeTransformation:
    """Test code transformation capabilities."""

    @pytest.mark.e2e
    def test_apply_refactoring_diff(self, tmp_path: Path, built_cli: Path):
        """Test applying a refactoring diff."""
        (tmp_path / "target.py").write_text('''
def old_implementation(x, y):
    """Old implementation."""
    result = 0
    for i in range(x):
        result += y
    return result
''')

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        diff_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "apply_diff",
            "params": {
                "path": "target.py",
                "diff": """--- a/target.py
+++ b/target.py
@@ -1,6 +1,3 @@
-def old_implementation(x, y):
-    \"\"\"Old implementation.\"\"\"
-    result = 0
-    for i in range(x):
-        result += y
-    return result
+def new_implementation(x, y):
+    return x * y
"""
            }
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(tmp_path)],
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

            updated = (tmp_path / "target.py").read_text()
            assert "new_implementation" in updated
            assert "old_implementation" not in updated
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_extract_method_refactoring(self, tmp_path: Path, built_cli: Path):
        """Test extracting a method via diff."""
        (tmp_path / "source.py").write_text('''def process_data(data):
    total = 0
    for item in data:
        if item > 0:
            total += item
    return total
''')

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        diff_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "apply_diff",
            "params": {
                "path": "source.py",
                "diff": """--- a/source.py
+++ b/source.py
@@ -1,6 +1,3 @@
 def process_data(data):
-    total = 0
-    for item in data:
-        if item > 0:
-            total += item
-    return total
+    return sum(item for item in data if item > 0)
"""
            }
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(tmp_path)],
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

            updated = (tmp_path / "source.py").read_text()
            assert "sum(item for item in data if item > 0)" in updated
            assert "process_data" in updated
        finally:
            proc.terminate()
            proc.wait()


class TestReadAndWrite:
    """Test file read/write operations."""

    @pytest.mark.e2e
    def test_read_file(self, non_idiomatic_project: Path, built_cli: Path):
        """Test reading a file through MCP."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        read_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "read_file",
            "params": {"path": "non_idiomatic.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(non_idiomatic_project)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{read_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            read_response = json.loads(lines[1])
            assert "result" in read_response

            result = read_response["result"]
            assert "content" in result
            assert "hash" in result
            assert "evens" in result["content"]
        finally:
            proc.terminate()
            proc.wait()

    @pytest.mark.e2e
    def test_write_preserves_content(self, tmp_path: Path, built_cli: Path):
        """Test that writing via diff preserves intended content."""
        (tmp_path / "test.py").write_text("x = 1\n")

        init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        diff_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "apply_diff",
            "params": {
                "path": "test.py",
                "diff": "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
            }
        })
        read_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "read_file",
            "params": {"path": "test.py"}
        })

        proc = subprocess.Popen(
            [str(built_cli), "mcp", str(tmp_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, _ = proc.communicate(input=f"{init_req}\n{diff_req}\n{read_req}\n", timeout=10)
            lines = stdout.strip().split("\n")

            read_response = json.loads(lines[2])
            content = read_response["result"]["content"]

            assert "x = 2" in content
            assert "x = 1" not in content
        finally:
            proc.terminate()
            proc.wait()
