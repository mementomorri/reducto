"""
LLM mocking utilities for testing without real API calls.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock


class MockLLMResponse:
    """Mock LLM responses with recorded fixtures (no external dependencies)."""
    
    def __init__(self, fixture_path: str, fixtures_dir: Optional[Path] = None):
        if fixtures_dir is None:
            fixtures_dir = Path(__file__).parent.parent / "fixtures" / "llm_responses"
        
        fixture_file = fixtures_dir / fixture_path
        if not fixture_file.exists():
            raise FileNotFoundError(f"LLM fixture not found: {fixture_file}")
        
        self.fixture = json.loads(fixture_file.read_text())
        self.patcher = None
        self.active = False
    
    def __enter__(self):
        # Mark as active for tests to check
        self.active = True
        return self
    
    def __exit__(self, *args):
        self.active = False
    
    def get_response(self):
        """Get the mocked response data."""
        return self.fixture


class MockLLMResponses:
    """Context manager for multiple mock LLM calls (no external dependencies)."""
    
    def __init__(self, responses: list, fixtures_dir: Optional[Path] = None):
        self.responses = responses
        self.call_index = 0
        self.fixtures_dir = fixtures_dir or Path(__file__).parent.parent / "fixtures" / "llm_responses"
        self.active = False
    
    def get_next_response(self):
        """Get next response in sequence."""
        if self.call_index >= len(self.responses):
            raise RuntimeError("Not enough mock responses configured")
        
        response_data = self.responses[self.call_index]
        self.call_index += 1
        return response_data
    
    def __enter__(self):
        self.active = True
        return self
    
    def __exit__(self, *args):
        self.active = False


def create_mock_embedding(texts: list, dimension: int = 384) -> list:
    """Create mock embeddings for testing."""
    import numpy as np
    
    np.random.seed(42)
    embeddings = []
    for i, text in enumerate(texts):
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.randn(dimension).astype(float).tolist()
        embeddings.append(embedding)
    
    return embeddings


class MockEmbeddingService:
    """Mock embedding service for testing."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.cache = {}
    
    def embed_texts(self, texts: list) -> list:
        """Generate mock embeddings."""
        embeddings = []
        for text in texts:
            if text not in self.cache:
                import numpy as np
                np.random.seed(hash(text) % (2**32))
                self.cache[text] = np.random.randn(self.dimension).tolist()
            embeddings.append(self.cache[text])
        return embeddings
    
    def embed_query(self, query: str) -> list:
        """Generate mock embedding for query."""
        return self.embed_texts([query])[0]
