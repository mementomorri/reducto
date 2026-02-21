"""
Minimal test sidecar that works without heavy dependencies.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI(title="reducto Test Sidecar")

# Mock embedding service
class MockEmbeddingService:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            import hashlib
            import numpy as np
            
            # Normalize text for better similarity matching
            normalized = ' '.join(text.lower().split())
            
            # Use hash to generate deterministic embedding
            hash_bytes = hashlib.sha256(normalized.encode()).digest()
            np.random.seed(int.from_bytes(hash_bytes[:4], 'big'))
            base_embedding = np.random.randn(384).astype(float)
            
            # Add some noise but keep similar texts similar
            normalized_words = set(normalized.split())
            for word in normalized_words:
                word_hash = int.from_bytes(hashlib.md5(word.encode()).digest()[:4], 'big')
                np.random.seed(word_hash)
                base_embedding += np.random.randn(384).astype(float) * 0.3
            
            # Normalize
            base_embedding = base_embedding / np.linalg.norm(base_embedding)
            embeddings.append(base_embedding.tolist())
        
        return embeddings

embedding_service = MockEmbeddingService()

# Simple tree-sitter based analyzer (no heavy dependencies)
class SimpleAnalyzer:
    def analyze_code(self, content: str, language: str) -> Dict[str, Any]:
        """Simple code analysis without heavy ML dependencies."""
        lines = content.split('\n')
        
        symbols = []
        symbol_count = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Simple pattern matching for function/class definitions
            if language == "python":
                if stripped.startswith('def '):
                    name = stripped.split('(')[0].replace('def ', '').strip()
                    symbols.append({
                        "name": name,
                        "type": "function",
                        "file": "test.py",
                        "start_line": i,
                        "end_line": i,
                        "signature": stripped
                    })
                    symbol_count += 1
                elif stripped.startswith('class '):
                    name = stripped.split('(')[0].replace('class ', '').strip(':').strip()
                    symbols.append({
                        "name": name,
                        "type": "class",
                        "file": "test.py",
                        "start_line": i,
                        "end_line": i,
                        "signature": stripped
                    })
                    symbol_count += 1
            
            elif language in ["javascript", "typescript"]:
                if 'function ' in stripped:
                    symbols.append({
                        "name": f"func_{symbol_count}",
                        "type": "function",
                        "file": "test.js",
                        "start_line": i,
                        "end_line": i
                    })
                    symbol_count += 1
        
        return {
            "symbols": symbols,
            "total_symbols": symbol_count
        }
    
    def calculate_complexity(self, content: str) -> Dict[str, int]:
        """Calculate simple complexity metrics."""
        lines = content.split('\n')
        
        # Simple cyclomatic complexity estimation
        complexity_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'and ', 'or ', 'try:', 'except:']
        cyclomatic = 1  # Base complexity
        
        for line in lines:
            for keyword in complexity_keywords:
                if keyword in line:
                    cyclomatic += 1
        
        return {
            "cyclomatic_complexity": cyclomatic,
            "cognitive_complexity": cyclomatic,
            "lines_of_code": len([l for l in lines if l.strip()]),
            "maintainability_index": max(0, 100 - cyclomatic * 5),
            "halstead_difficulty": 10.0
        }

analyzer = SimpleAnalyzer()


# Models
class FileInfo(BaseModel):
    path: str
    content: str
    hash: str = None


class AnalyzeRequest(BaseModel):
    path: str
    files: List[FileInfo] = []
    config: Dict[str, Any] = {}


class DeduplicateRequest(BaseModel):
    path: str
    files: List[FileInfo] = []
    similarity_threshold: float = 0.85


class IdiomatizeRequest(BaseModel):
    path: str
    files: List[FileInfo] = []
    language: str = "python"


class PatternRequest(BaseModel):
    pattern: str
    path: str
    files: List[FileInfo] = []


class EmbedRequest(BaseModel):
    files: List[FileInfo]


# Endpoints
@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    """Analyze code files."""
    try:
        all_symbols = []
        total_files = len(request.files)
        
        for file_info in request.files:
            # Detect language
            ext = Path(file_info.path).suffix
            language = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.go': 'go'
            }.get(ext, 'unknown')
            
            result = analyzer.analyze_code(file_info.content, language)
            all_symbols.extend(result["symbols"])
        
        # Find hotspots
        hotspots = []
        for file_info in request.files:
            metrics = analyzer.calculate_complexity(file_info.content)
            if metrics["cyclomatic_complexity"] > 10:
                hotspots.append({
                    "file": file_info.path,
                    "line": 1,
                    "symbol": "unknown",
                    "cyclomatic_complexity": metrics["cyclomatic_complexity"],
                    "cognitive_complexity": metrics["cognitive_complexity"]
                })
        
        return {
            "status": "success",
            "data": {
                "total_files": total_files,
                "total_symbols": len(all_symbols),
                "symbols": all_symbols,
                "hotspots": hotspots,
                "duplicates": []
            },
            "error": None
        }
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@app.post("/deduplicate")
async def deduplicate(request: DeduplicateRequest):
    """Find duplicate code blocks using mock embeddings."""
    try:
        # Generate embeddings for all files
        blocks = []
        for file_info in request.files:
            lines = file_info.content.split('\n')
            
            # Split into smaller blocks for better matching
            for i in range(0, len(lines), 5):
                block_content = '\n'.join(lines[i:i+5])
                if block_content.strip():
                    blocks.append({
                        "id": f"{file_info.path}_block_{i}",
                        "file": file_info.path,
                        "start_line": i + 1,
                        "end_line": min(i + 5, len(lines)),
                        "content": block_content,
                        "language": "python"
                    })
        
        # Find similar blocks using mock embeddings
        embeddings = embedding_service.embed_texts([b["content"] for b in blocks])
        
        duplicates = []
        seen_pairs = set()
        
        for i, block1 in enumerate(blocks):
            for j, block2 in enumerate(blocks[i+1:], i+1):
                # Skip if from same file
                if block1["file"] == block2["file"]:
                    continue
                
                # Simple cosine similarity
                import numpy as np
                emb1 = np.array(embeddings[i])
                emb2 = np.array(embeddings[j])
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = np.dot(emb1, emb2) / (norm1 * norm2)
                else:
                    similarity = 0.0
                
                # Lower threshold for testing
                if similarity > request.similarity_threshold:
                    pair_key = tuple(sorted([block1["id"], block2["id"]]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        duplicates.append({
                            "id": f"dup_{len(duplicates)}",
                            "blocks": [block1, block2],
                            "similarity": float(similarity),
                            "suggested_fix": f"Extract duplicate code from {block1['file']} and {block2['file']}"
                        })
        
        return {
            "status": "success",
            "data": {
                "duplicates": duplicates[:10]  # Limit to top 10
            },
            "error": None
        }
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@app.post("/idiomatize")
async def idiomatize(request: IdiomatizeRequest):
    """Suggest idiomatic improvements using local Ollama."""
    try:
        changes = []
        
        # Simple pattern matching for non-idiomatic code
        for file_info in request.files:
            original = file_info.content
            modified = original
            
            # Simple transformations
            if request.language == "python":
                # List comprehension suggestions
                import re
                pattern = r'(\w+)\s*=\s*\[\]\nfor\s+(\w+)\s+in\s+(.+?):\n\s+if\s+(.+?):\n\s+\1\.append\((.+?)\)'
                
                matches = list(re.finditer(pattern, original))
                if matches:
                    for match in reversed(matches):
                        var_name = match.group(1)
                        iter_var = match.group(2)
                        iterable = match.group(3)
                        condition = match.group(4)
                        expr = match.group(5)
                        
                        idiomatic = f"{var_name} = [{expr} for {iter_var} in {iterable} if {condition}]"
                        changes.append({
                            "path": file_info.path,
                            "original": match.group(0),
                            "modified": idiomatic,
                            "description": "Replace for loop with list comprehension"
                        })
                
                # F-string suggestions
                pattern = r'"([^"]*)"\s*\+\s*(\w+)\s*\+\s*"([^"]*)"'
                for match in re.finditer(pattern, original):
                    changes.append({
                        "path": file_info.path,
                        "original": match.group(0),
                        "modified": f'f"{match.group(1)}{{{match.group(2)}}}{match.group(3)}"',
                        "description": "Replace string concatenation with f-string"
                    })
        
        return {
            "status": "success",
            "data": {
                "session_id": "test-session",
                "changes": changes,
                "description": "Idiomatic improvements suggested"
            },
            "error": None
        }
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@app.post("/pattern")
async def apply_pattern(request: PatternRequest):
    """Apply design pattern suggestions."""
    try:
        # Mock pattern application
        changes = []
        
        if request.pattern == "factory":
            changes.append({
                "path": request.files[0].path if request.files else "unknown",
                "original": "if/else conditional",
                "modified": "Factory pattern implementation",
                "description": f"Apply {request.pattern} pattern"
            })
        elif request.pattern == "strategy":
            changes.append({
                "path": request.files[0].path if request.files else "unknown",
                "original": "complex conditional",
                "modified": "Strategy pattern implementation",
                "description": f"Apply {request.pattern} pattern"
            })
        
        return {
            "status": "success",
            "data": {
                "session_id": "test-session",
                "changes": changes,
                "description": f"Pattern {request.pattern} applied"
            },
            "error": None
        }
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@app.post("/embed")
async def embed(request: EmbedRequest):
    """Generate embeddings for files."""
    try:
        all_embeddings = []
        
        for file_info in request.files:
            embeddings = embedding_service.embed_texts([file_info.content])
            all_embeddings.append({
                "file": file_info.path,
                "embedding": embeddings[0]
            })
        
        return {
            "status": "success",
            "data": {
                "embeddings": all_embeddings
            },
            "error": None
        }
    except Exception as e:
        return {"status": "error", "data": None, "error": str(e)}


@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown."""
    import os
    os._exit(0)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SIDECAR_PORT", "9876"))
    uvicorn.run(app, host="127.0.0.1", port=port)
