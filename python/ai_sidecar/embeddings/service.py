"""
Embedding service for semantic code analysis.
"""

import hashlib
import logging
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings

from ai_sidecar.models import FileInfo, CodeBlock, Language

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection = None
        self.model = None
        self._initialized = False
        self._use_real_embeddings = False

    async def initialize(self):
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self._use_real_embeddings = True
            logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not available, using mock embeddings")
            self._use_real_embeddings = False
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers: {e}, using mock embeddings")
            self._use_real_embeddings = False

        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=None,
        ))

        self.collection = self.client.get_or_create_collection(
            name="code_embeddings",
            metadata={"hnsw:space": "cosine"}
        )

        self._initialized = True

    async def shutdown(self):
        if self.client:
            self.client = None
            self.collection = None
            self.model = None
            self._initialized = False
            self._use_real_embeddings = False

    def _mock_embedding(self, text: str) -> List[float]:
        h = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(0, 64, 4):
            val = int(h[i:i+4], 16) / 65535.0
            embedding.append(val)
        return embedding[:384]

    async def embed_text(self, text: str) -> List[float]:
        if self._use_real_embeddings and self.model:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        else:
            return self._mock_embedding(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._use_real_embeddings and self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            return [self._mock_embedding(t) for t in texts]

    async def embed_files(self, files: List[FileInfo]) -> Dict[str, List[float]]:
        if not files:
            return {}
        
        texts = [f.content for f in files]
        embeddings = await self.embed_batch(texts)
        return {f.path: emb for f, emb in zip(files, embeddings)}

    async def embed_blocks(self, blocks: List[CodeBlock]) -> List[CodeBlock]:
        if not blocks:
            return blocks
        
        texts = [block.content for block in blocks]
        embeddings = await self.embed_batch(texts)
        
        for block, embedding in zip(blocks, embeddings):
            block.embedding = embedding
        
        return blocks

    async def store_embeddings(self, blocks: List[CodeBlock]):
        if not self._initialized or not self.collection:
            return

        ids = [block.id for block in blocks]
        embeddings = [block.embedding for block in blocks if block.embedding]
        metadatas = [
            {
                "file": block.file,
                "start_line": block.start_line,
                "end_line": block.end_line,
                "symbol_type": block.symbol_type,
                "symbol_name": block.symbol_name,
                "language": block.language.value,
            }
            for block in blocks
        ]
        documents = [block.content for block in blocks]

        if embeddings:
            self.collection.add(
                ids=ids[:len(embeddings)],
                embeddings=embeddings,
                metadatas=metadatas[:len(embeddings)],
                documents=documents[:len(embeddings)],
            )

    async def find_similar(
        self,
        embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        if not self._initialized or not self.collection:
            return []

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
        )

        similar = []
        for i, id in enumerate(results["ids"][0]):
            similar.append({
                "id": id,
                "distance": results["distances"][0][i] if results.get("distances") else 0,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "content": results["documents"][0][i] if results.get("documents") else "",
            })

        return similar

    async def find_duplicates(
        self,
        blocks: List[CodeBlock],
        threshold: float = 0.85,
    ) -> List[List[CodeBlock]]:
        if not self._initialized:
            await self.initialize()

        blocks_with_embeddings = await self.embed_blocks(blocks)
        await self.store_embeddings(blocks_with_embeddings)

        groups = []
        processed = set()

        for block in blocks_with_embeddings:
            if block.id in processed or not block.embedding:
                continue

            similar = await self.find_similar(
                block.embedding,
                n_results=10,
            )

            group = [block]
            processed.add(block.id)

            for sim in similar:
                if sim["id"] == block.id:
                    continue

                similarity = 1 - sim["distance"]
                if similarity >= threshold:
                    for b in blocks_with_embeddings:
                        if b.id == sim["id"] and b.id not in processed:
                            group.append(b)
                            processed.add(b.id)
                            break

            if len(group) > 1:
                groups.append(group)

        return groups

    async def clear(self):
        if self._initialized and self.client:
            self.client.delete_collection("code_embeddings")
            self.collection = self.client.get_or_create_collection(
                name="code_embeddings",
                metadata={"hnsw:space": "cosine"}
            )

    @property
    def is_using_real_embeddings(self) -> bool:
        return self._use_real_embeddings
