# reducto Architecture

Python-only CLI for semantic code compression.

## Overview

```
User → Typer CLI (reducto.cli)
         → App (reducto.services)
              → Workspace (repo, parse, git, tests, diff)
              → Agents (analyzer, deduplicator, idiomatizer, pattern, quality)
              → LLMRouter (LiteLLM)
              → EmbeddingService (optional [embeddings] extra)
              → SessionStore (.reducto/sessions)
```

## Components

| Module | Role |
|--------|------|
| `cli.py` | Commands: analyze, deduplicate, idiomatize, pattern, check, apply, report, sessions |
| `workspace.py` | In-process API replacing the former Go MCP server |
| `repo.py` | Parallel file walk, language detection |
| `parse.py` | Tree-sitter symbols and complexity heuristics |
| `git_safety.py` | Checkpoint / rollback via GitPython |
| `runner.py` | pytest / npm / go test detection |
| `agents/` | LLM-driven planning |
| `embeddings/` | ChromaDB semantic dedup (optional install) |
| `lsp/` | Optional `find_references` via Linux language servers |

## Distribution

PyPI package `reducto` with console script `reducto`. No Go binary, no MCP JSON-RPC, no sidecar process.
