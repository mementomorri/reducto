# reducto Architecture

Python 3.14+ CLI for semantic compression of **Python source code**. One process: Typer CLI, in-process `Workspace`, optional embeddings.

## Overview

```
User
  → reducto.cli (Typer)
       → reducto.services.App
            → Workspace (repo walk *.py, parse, diff, git, pytest)
            → Agents (analyze, deduplicate, idiomatize, pattern, check)
            → LLMRouter (LiteLLM; Ollama local-first)
            → EmbeddingService ([embeddings] extra)
            → SessionStore (.reducto/sessions)
            → Reporter (.reducto/*.md)
```

## Package map

| Module | Role |
|--------|------|
| `cli.py` | Commands, git dirty check, asyncio bridge, session subcommands |
| `services.py` | `App`: orchestrates agents, apply, embedding lazy init |
| `workspace.py` | Files, symbols, diffs, git, tests |
| `repo.py` | Walk repo; include `*.py` by default; `detect_language` → Python or unknown |
| `parse.py` | Tree-sitter Python symbols and complexity heuristics |
| `diff.py` | Apply unified diffs |
| `git_safety.py` | Checkpoint, rollback (GitPython) |
| `runner.py` | `pytest` / `unittest` for Python projects |
| `session.py` | JSON persistence for `RefactorPlan` |
| `reporter.py` | Markdown reports |
| `config.py` | `.reducto.yaml` + env |
| `models.py` | Pydantic models and `AppConfig` |
| `agents/*` | Planning agents (idiomatize is Python-only) |
| `llm/router.py` | LiteLLM tiers |
| `embeddings/service.py` | ChromaDB similarity for deduplication |

## Request flows

### Analyze

1. `repo.walk` → `.py` files only (per `include_patterns`).
2. `parse.get_symbols` per file.
3. Hotspots where cyclomatic complexity ≥ threshold.

### Deduplicate / idiomatize / pattern / check

Same walk scope. Non-`.py` paths are never loaded. Idiomatize uses Python line heuristics only.

### Apply

Git checkpoint → apply diffs → run pytest (if project looks like Python) → rollback on failure.

## Distribution

- PyPI: `reducto`, entrypoint `reducto.cli:app`
- **Python 3.14+**
- Extras: `embeddings`, `dev`
- Docker: `.[embeddings]`, `ENTRYPOINT ["reducto"]`

## External dependencies

| Concern | Technology |
|---------|------------|
| CLI | Typer |
| Models | Pydantic v2 |
| Parse | tree-sitter-python |
| LLM | LiteLLM |
| VCS | GitPython |
| Dedup | ChromaDB, sentence-transformers |

See [ONBOARDING.md](ONBOARDING.md) for maintainer workflows.
