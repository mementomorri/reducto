"""Embedding service tests."""

import pytest

from reducto.embeddings.service import EmbeddingService
from reducto.models import CodeBlock, ComplexityMetrics, Language


@pytest.mark.asyncio
async def test_find_duplicates_without_real_embeddings_returns_empty():
    svc = EmbeddingService()
    svc._initialized = True
    svc._use_real_embeddings = False
    blocks = [
        CodeBlock(
            id="1",
            file="a.py",
            start_line=1,
            end_line=2,
            content="def a(): pass",
            language=Language.PYTHON,
            symbol_type="function",
            symbol_name="a",
            metrics=ComplexityMetrics(),
        )
    ]
    groups = await svc.find_duplicates(blocks, threshold=0.85)
    assert groups == []
