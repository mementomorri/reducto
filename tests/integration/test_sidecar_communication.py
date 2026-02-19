"""
Integration tests for Go-Python sidecar communication.
"""

import pytest
import subprocess
import time
import requests
from pathlib import Path


class TestSidecarIntegration:
    """Test Go CLI ↔ Python Sidecar HTTP communication."""
    
    @pytest.fixture(scope="class")
    def sidecar_url(self):
        """Get sidecar base URL."""
        return "http://localhost:9876"
    
    @pytest.mark.integration
    def test_health_endpoint(self, sidecar_url):
        """Test /health endpoint returns 200."""
        response = requests.get(f"{sidecar_url}/health", timeout=5)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.integration
    def test_analyze_endpoint_complete_json(self, sidecar_url):
        """Test /analyze endpoint with complete JSON comparison."""
        payload = {
            "path": "/test",
            "files": [
                {
                    "path": "test.py",
                    "content": "def foo():\n    pass"
                }
            ]
        }
        
        response = requests.post(
            f"{sidecar_url}/analyze",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["error"] is None
        
        result = data["data"]
        assert result["total_files"] == 1
        assert result["total_symbols"] >= 1
        assert isinstance(result["symbols"], list)
    
    @pytest.mark.integration
    def test_analyze_multi_language_project(self, sidecar_url):
        """Test analyzing multi-language project."""
        payload = {
            "path": "/multi-lang",
            "files": [
                {
                    "path": "main.py",
                    "content": "def python_func():\n    pass"
                },
                {
                    "path": "app.js",
                    "content": "function jsFunc() {}"
                }
            ]
        }
        
        response = requests.post(
            f"{sidecar_url}/analyze",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["total_files"] == 2
        assert len(data["data"]["symbols"]) >= 2
    
    @pytest.mark.integration
    def test_error_handling_invalid_request(self, sidecar_url):
        """Test error responses are properly formatted."""
        response = requests.post(
            f"{sidecar_url}/analyze",
            json={"invalid": "data"},
            timeout=5
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
    
    @pytest.mark.integration
    def test_error_handling_missing_required_fields(self, sidecar_url):
        """Test error when required fields are missing."""
        response = requests.post(
            f"{sidecar_url}/analyze",
            json={},
            timeout=5
        )
        
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_deduplicate_endpoint(self, sidecar_url):
        """Test /deduplicate endpoint."""
        payload = {
            "path": "/test",
            "files": [
                {
                    "path": "file1.py",
                    "content": "def validate_email(email):\n    if not email:\n        raise ValueError()\n    return email"
                },
                {
                    "path": "file2.py",
                    "content": "def check_email(email):\n    if not email:\n        raise Exception()\n    return email"
                }
            ],
            "similarity_threshold": 0.85
        }
        
        response = requests.post(
            f"{sidecar_url}/deduplicate",
            json=payload,
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "duplicates" in data["data"]
    
    @pytest.mark.integration
    def test_idiomatize_endpoint(self, sidecar_url):
        """Test /idiomatize endpoint."""
        payload = {
            "path": "/test",
            "files": [
                {
                    "path": "non_idiomatic.py",
                    "content": "evens = []\nfor x in range(10):\n    if x % 2 == 0:\n        evens.append(x)"
                }
            ],
            "language": "python"
        }
        
        response = requests.post(
            f"{sidecar_url}/idiomatize",
            json=payload,
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "changes" in data["data"]
    
    @pytest.mark.integration
    def test_embed_endpoint(self, sidecar_url):
        """Test /embed endpoint."""
        payload = {
            "files": [
                {
                    "path": "test.py",
                    "content": "def hello():\n    print('hello')"
                }
            ]
        }
        
        response = requests.post(
            f"{sidecar_url}/embed",
            json=payload,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "embeddings" in data["data"]
    
    @pytest.mark.integration
    def test_concurrent_requests(self, sidecar_url):
        """Test handling concurrent requests."""
        import concurrent.futures
        
        payloads = [
            {
                "path": f"/test{i}",
                "files": [{"path": "test.py", "content": f"# Test {i}"}]
            }
            for i in range(5)
        ]
        
        def make_request(payload):
            return requests.post(
                f"{sidecar_url}/analyze",
                json=payload,
                timeout=10
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, p) for p in payloads]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        for response in results:
            assert response.status_code == 200
    
    @pytest.mark.integration
    def test_large_file_handling(self, sidecar_url):
        """Test handling large files."""
        large_content = "\n".join([f"def func_{i}(): pass" for i in range(100)])
        
        payload = {
            "path": "/test",
            "files": [
                {
                    "path": "large.py",
                    "content": large_content
                }
            ]
        }
        
        response = requests.post(
            f"{sidecar_url}/analyze",
            json=payload,
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["total_symbols"] >= 100
