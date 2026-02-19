"""
Test configuration for local Ollama models.
"""
import os
import pytest
from pathlib import Path

# Available local Ollama models
AVAILABLE_MODELS = {
    "light": "gemma3:270m",
    "medium": "codegemma:2b", 
    "heavy": "qwen2.5-coder:1.5b",
    "cloud": "glm-5:cloud"
}

# Test configuration
TEST_CONFIG = {
    "use_local_ollama": True,
    "ollama_base_url": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "default_model": AVAILABLE_MODELS["medium"],
    "timeout": 60
}


def check_ollama_available():
    """Check if Ollama is running and accessible."""
    import requests
    try:
        response = requests.get(f"{TEST_CONFIG['ollama_base_url']}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def get_test_model(tier="medium"):
    """Get appropriate test model for tier."""
    return AVAILABLE_MODELS.get(tier, AVAILABLE_MODELS["medium"])


@pytest.fixture(scope="session")
def ollama_available():
    """Fixture to check if Ollama is available."""
    return check_ollama_available()


@pytest.fixture
def test_config_path():
    """Get path to test configuration file."""
    return Path(__file__).parent / "test_config.yaml"


@pytest.fixture
def mock_embedding_service():
    """
    Mock embedding service for tests without chromadb/sentence-transformers.
    Uses simple hash-based mock embeddings.
    """
    class MockEmbeddingService:
        def __init__(self, dimension=384):
            self.dimension = dimension
        
        def embed_texts(self, texts):
            """Generate mock embeddings based on text hash."""
            embeddings = []
            for text in texts:
                import hashlib
                import numpy as np
                # Use hash to generate deterministic embedding
                hash_bytes = hashlib.sha256(text.encode()).digest()
                np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
                embedding = np.random.randn(self.dimension).astype(float).tolist()
                embeddings.append(embedding)
            return embeddings
        
        def embed_query(self, query):
            return self.embed_texts([query])[0]
    
    return MockEmbeddingService()


# Skip tests that require unavailable dependencies
def skip_if_no_ollama():
    """Decorator to skip test if Ollama not available."""
    return pytest.mark.skipif(
        not check_ollama_available(),
        reason="Ollama not running or accessible"
    )
