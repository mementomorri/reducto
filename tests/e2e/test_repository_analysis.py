"""
End-to-end tests for repository analysis and context mapping.
From TEST_RULES.md Category 1.
"""

import pytest
from pathlib import Path
from tests.utils.repository_builder import RepositoryBuilder
from tests.utils.assertions import (
    assert_json_structure_equal,
    assert_complexity_metrics_valid
)


@pytest.mark.e2e
class TestRepositoryAnalysis:
    """Test Case: Initial Project Mapping"""
    
    def test_initial_project_mapping(self, tmp_path):
        """
        Scenario: Run tool in directory with multiple modules and utilities.
        Expectation: Identify key classes, functions, dependencies.
        Export summary map.
        """
        builder = RepositoryBuilder(tmp_path)
        builder.create_interdependent_modules()
        
        result = self.run_cli(["analyze", str(tmp_path)])
        
        assert result.exit_code == 0
        
        data = result.json()
        assert "total_files" in data
        assert "total_symbols" in data
        assert "symbols" in data
        assert data["total_files"] > 0
        assert data["total_symbols"] > 0
    
    @pytest.mark.parametrize("language,files,expected_min_symbols", [
        ("python", ["main.py", "utils.py"], 2),
        ("javascript", ["index.js", "helper.js"], 2),
        ("multi", ["main.py", "app.js"], 2),
    ])
    def test_language_recognition(
        self, language, files, expected_min_symbols, tmp_path
    ):
        """
        Scenario: Run tool on multi-language repository.
        Expectation: Detect syntax of both languages, apply correct parsing.
        """
        builder = RepositoryBuilder(tmp_path)
        
        if language == "python":
            builder.create_file("main.py", "def main(): pass")
            builder.create_file("utils.py", "def helper(): pass")
        elif language == "javascript":
            builder.create_file("index.js", "function main() {}")
            builder.create_file("helper.js", "function helper() {}")
        else:  # multi
            builder.create_file("main.py", "def py_func(): pass")
            builder.create_file("app.js", "function js_func() {}")
        
        result = self.run_cli(["analyze", str(tmp_path)])
        
        assert result.exit_code == 0
        data = result.json()
        
        assert data["total_files"] >= len(files)
        assert data["total_symbols"] >= expected_min_symbols
    
    def test_dependency_detection(self, tmp_path):
        """
        Scenario: Tool identifies dependencies across modules.
        Expectation: Export graph of imports/exports.
        """
        builder = RepositoryBuilder(tmp_path)
        builder.create_interdependent_modules()
        
        result = self.run_cli(["analyze", str(tmp_path)])
        
        assert result.exit_code == 0
        
        data = result.json()
        if "dependency_graph" in data:
            assert isinstance(data["dependency_graph"], dict)
    
    def test_complexity_hotspot_detection(self, tmp_path):
        """
        Scenario: Analyze code with high complexity.
        Expectation: Identify complexity hotspots.
        """
        builder = RepositoryBuilder(tmp_path)
        builder.create_complex_conditional_nesting()
        
        result = self.run_cli(["analyze", str(tmp_path)])
        
        assert result.exit_code == 0
        
        data = result.json()
        assert "hotspots" in data
        
        if len(data["hotspots"]) > 0:
            hotspot = data["hotspots"][0]
            assert "file" in hotspot
            assert "cyclomatic_complexity" in hotspot
            assert "cognitive_complexity" in hotspot
    
    def test_multi_file_project_scanning(self, multi_file_project):
        """Test scanning multi-file project structure."""
        result = self.run_cli(["analyze", str(multi_file_project)])
        
        assert result.exit_code == 0
        
        data = result.json()
        assert data["total_files"] >= 2
        assert len(data["symbols"]) >= 2
    
    def run_cli(self, args):
        """Helper to run CLI commands."""
        import subprocess
        import requests
        from pathlib import Path
        
        # For now, we'll simulate by calling Python sidecar directly
        # In real implementation, this would call the Go binary
        if args[0] == "analyze":
            path = args[1]
            files = []
            
            # Scan for all supported file types
            for ext in ["*.py", "*.js", "*.ts", "*.go"]:
                for code_file in Path(path).rglob(ext):
                    files.append({
                        "path": str(code_file.relative_to(path)),
                        "content": code_file.read_text()
                    })
            
            try:
                response = requests.post(
                    "http://localhost:9876/analyze",
                    json={"path": path, "files": files},
                    timeout=30
                )
                
                class Result:
                    exit_code = 0 if response.status_code == 200 else 1
                    
                    def json(self):
                        data = response.json()
                        return data.get("data", data)
                
                return Result()
            except Exception as e:
                class Result:
                    exit_code = 1
                    error = str(e)
                    
                    def json(self):
                        return {"error": self.error}
                
                return Result()
