"""
Custom test assertions for DeHydrator test suite.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import subprocess


def assert_json_equal(actual: dict, expected_path: str):
    """
    Compare complete JSON against expected fixture.
    
    Args:
        actual: Actual JSON data
        expected_path: Path to expected JSON file (relative to fixtures/)
    """
    fixtures_dir = Path(__file__).parent.parent / "fixtures"
    expected_file = fixtures_dir / expected_path
    
    if not expected_file.exists():
        raise FileNotFoundError(f"Expected fixture not found: {expected_file}")
    
    expected = json.loads(expected_file.read_text())
    
    if actual != expected:
        import pprint
        actual_str = pprint.pformat(actual, width=120)
        expected_str = pprint.pformat(expected, width=120)
        
        raise AssertionError(
            f"JSON mismatch:\n\n"
            f"Actual:\n{actual_str}\n\n"
            f"Expected:\n{expected_str}"
        )


def assert_json_structure_equal(actual: Any, expected: Any, path: str = ""):
    """
    Compare JSON structure (allow value differences).
    
    Args:
        actual: Actual JSON data
        expected: Expected JSON structure (values are ignored)
        path: Current path in JSON tree (for error messages)
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(
                f"Expected dict at {path}, got {type(actual).__name__}"
            )
        
        for key in expected.keys():
            if key not in actual:
                raise AssertionError(f"Missing key '{key}' at {path}")
            
            assert_json_structure_equal(
                actual[key],
                expected[key],
                f"{path}.{key}" if path else key
            )
    
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            raise AssertionError(
                f"Expected list at {path}, got {type(actual).__name__}"
            )
        
        if len(expected) > 0 and len(actual) > 0:
            assert_json_structure_equal(
                actual[0],
                expected[0],
                f"{path}[0]"
            )
    
    elif isinstance(expected, type):
        if not isinstance(actual, expected):
            raise AssertionError(
                f"Expected type {expected.__name__} at {path}, "
                f"got {type(actual).__name__}"
            )


def assert_file_exists(path: Path):
    """Assert that a file exists."""
    if not path.exists():
        raise AssertionError(f"File does not exist: {path}")
    if not path.is_file():
        raise AssertionError(f"Path is not a file: {path}")


def assert_directory_exists(path: Path):
    """Assert that a directory exists."""
    if not path.exists():
        raise AssertionError(f"Directory does not exist: {path}")
    if not path.is_dir():
        raise AssertionError(f"Path is not a directory: {path}")


def assert_git_clean(repo_path: Path):
    """Assert that git repository has no uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.stdout.strip():
        raise AssertionError(
            f"Git repository has uncommitted changes:\n{result.stdout}"
        )


def assert_git_has_changes(repo_path: Path):
    """Assert that git repository has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        raise AssertionError("Git repository has no uncommitted changes")


def assert_valid_python_syntax(code: str):
    """Assert that Python code is syntactically valid."""
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        raise AssertionError(f"Invalid Python syntax: {e}")


def assert_valid_javascript_syntax(code: str):
    """Assert that JavaScript code is syntactically valid (requires node)."""
    try:
        result = subprocess.run(
            ["node", "--check", "-"],
            input=code,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise AssertionError(f"Invalid JavaScript syntax: {result.stderr}")
    except FileNotFoundError:
        raise AssertionError("Node.js not available for syntax validation")


def assert_complexity_metrics_valid(metrics: dict):
    """Assert that complexity metrics are valid."""
    required_fields = [
        "cyclomatic_complexity",
        "cognitive_complexity",
        "lines_of_code",
        "maintainability_index",
        "halstead_difficulty"
    ]
    
    for field in required_fields:
        if field not in metrics:
            raise AssertionError(f"Missing required metric: {field}")
        
        value = metrics[field]
        if not isinstance(value, (int, float)):
            raise AssertionError(
                f"Metric {field} must be numeric, got {type(value).__name__}"
            )
    
    if metrics["lines_of_code"] < 0:
        raise AssertionError("lines_of_code must be non-negative")
    
    if metrics["cyclomatic_complexity"] < 1:
        raise AssertionError("cyclomatic_complexity must be at least 1")


def assert_refactor_plan_valid(plan: dict):
    """Assert that refactor plan is valid."""
    if "session_id" not in plan:
        raise AssertionError("Refactor plan missing session_id")
    
    if "changes" not in plan:
        raise AssertionError("Refactor plan missing changes")
    
    if not isinstance(plan["changes"], list):
        raise AssertionError("Refactor plan changes must be a list")
    
    for i, change in enumerate(plan["changes"]):
        if "path" not in change:
            raise AssertionError(f"Change {i} missing path")
        if "original" not in change:
            raise AssertionError(f"Change {i} missing original")
        if "modified" not in change:
            raise AssertionError(f"Change {i} missing modified")


def parse_report_metrics(report_content: str) -> Dict[str, Any]:
    """Parse metrics from markdown report."""
    metrics = {}
    
    lines = report_content.split('\n')
    for line in lines:
        if 'LOC Before:' in line:
            metrics['loc_before'] = int(line.split(':')[1].strip())
        elif 'LOC After:' in line:
            metrics['loc_after'] = int(line.split(':')[1].strip())
        elif 'LOC Reduced:' in line:
            metrics['loc_reduced'] = int(line.split(':')[1].strip())
        elif 'Cyclomatic Complexity Delta:' in line:
            metrics['cc_delta'] = int(line.split(':')[1].strip())
        elif 'Cognitive Complexity Delta:' in line:
            metrics['cognitive_delta'] = int(line.split(':')[1].strip())
    
    return metrics


def assert_files_equal(file1: Path, file2: Path):
    """Assert that two files have identical content."""
    content1 = file1.read_text()
    content2 = file2.read_text()
    
    if content1 != content2:
        raise AssertionError(
            f"Files differ:\n"
            f"  {file1}\n"
            f"  {file2}"
        )
