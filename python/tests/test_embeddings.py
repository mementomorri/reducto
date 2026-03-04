"""
Unit tests for the embedding service.
"""

import pytest
from ai_sidecar.embeddings import EmbeddingService
from ai_sidecar.models import FileInfo, CodeBlock, Language, ComplexityMetrics


class TestEmbeddingService:
    """Test EmbeddingService class."""
    
    @pytest.fixture
    async def service(self):
        """Create initialized EmbeddingService."""
        service = EmbeddingService()
        await service.initialize()
        yield service
        await service.shutdown()
    
    def test_service_initialization(self, service):
        """Test service initializes correctly."""
        assert service._initialized is True
        assert service.client is not None
        assert service.collection is not None
    
    def test_mock_embedding_generation(self):
        """Test mock embedding generates correct dimensions."""
        service = EmbeddingService()
        embedding = service._mock_embedding("test code")
        
        assert len(embedding) == 384
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)
        assert all(0.0 <= x <= 1.0 for x in embedding)
    
    def test_mock_embedding_deterministic(self):
        """Test mock embeddings are deterministic."""
        service = EmbeddingService()
        emb1 = service._mock_embedding("same code")
        emb2 = service._mock_embedding("same code")
        
        assert emb1 == emb2
    
    def test_mock_embedding_different_inputs(self):
        """Test different inputs produce different embeddings."""
        service = EmbeddingService()
        emb1 = service._mock_embedding("code A")
        emb2 = service._mock_embedding("code B")
        
        assert emb1 != emb2


class TestEmbeddingMethods:
    """Test embedding generation methods."""
    
    @pytest.fixture
    async def service(self):
        """Create initialized EmbeddingService."""
        service = EmbeddingService()
        await service.initialize()
        yield service
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_embed_text(self, service):
        """Test embedding single text."""
        embedding = await service.embed_text("def hello(): pass")
        
        assert len(embedding) == 384
        assert isinstance(embedding, list)
    
    @pytest.mark.asyncio
    async def test_embed_batch(self, service):
        """Test embedding batch of texts."""
        texts = ["def foo(): pass", "def bar(): pass", "def baz(): pass"]
        embeddings = await service.embed_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_embed_files(self, service):
        """Test embedding files."""
        files = [
            FileInfo(path="test1.py", content="def hello(): pass"),
            FileInfo(path="test2.py", content="def world(): pass"),
        ]
        
        embeddings = await service.embed_files(files)
        
        assert len(embeddings) == 2
        assert "test1.py" in embeddings
        assert "test2.py" in embeddings
        assert all(len(emb) == 384 for emb in embeddings.values())
    
    @pytest.mark.asyncio
    async def test_embed_empty_list(self, service):
        """Test embedding empty list."""
        embeddings = await service.embed_files([])
        assert embeddings == {}


class TestSemanticSimilarity:
    """Test semantic similarity detection."""
    
    @pytest.fixture
    async def service(self):
        """Create initialized EmbeddingService."""
        service = EmbeddingService()
        await service.initialize()
        yield service
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_similar_code_has_similar_embedding(self, service):
        """Test that similar code produces similar embeddings."""
        code1 = "def add(a, b): return a + b"
        code2 = "def add(x, y): return x + y"
        
        emb1 = await service.embed_text(code1)
        emb2 = await service.embed_text(code2)
        
        # Calculate cosine similarity
        similarity = sum(a*b for a, b in zip(emb1, emb2))
        
        # Similar code should have positive similarity
        assert similarity > 0.5
    
    @pytest.mark.asyncio
    async def test_different_code_has_different_embedding(self, service):
        """Test that different code produces different embeddings."""
        code1 = "def add(a, b): return a + b"
        code2 = "class Car: def drive(self): pass"
        
        emb1 = await service.embed_text(code1)
        emb2 = await service.embed_text(code2)
        
        # Different code should have different embeddings
        assert emb1 != emb2
        
        # And lower similarity
        similarity = sum(a*b for a, b in zip(emb1, emb2))
        assert similarity < 0.9
    
    @pytest.mark.asyncio
    async def test_real_embeddings_if_available(self, service):
        """Test real embeddings if sentence-transformers available."""
        if not service.is_using_real_embeddings:
            pytest.skip("sentence-transformers not available")
        
        embedding = await service.embed_text("test code")
        
        assert len(embedding) == 384
        assert service._use_real_embeddings is True
