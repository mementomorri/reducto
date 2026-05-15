"""Embeddings (optional — requires reducto[embeddings])."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reducto.embeddings.service import EmbeddingService

__all__ = ["EmbeddingService"]


def __getattr__(name: str):
    if name == "EmbeddingService":
        from reducto.embeddings.service import EmbeddingService

        return EmbeddingService
    raise AttributeError(name)
