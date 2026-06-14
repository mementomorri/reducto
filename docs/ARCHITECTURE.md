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
| `diff.py` | Apply unified diffs with context validation (raises `DiffError` on mismatch) |
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

Same walk scope. Non-`.py` paths are never loaded. Idiomatize uses Python line heuristics only and
emits **one whole-file change per file** (the diff is therefore file-relative). Deduplicate is
suggestion-only — it proposes a shared `utils/<symbol>_dedup.py` module and does not rewrite call sites.

### Apply

`apply_changes_safe` is an all-or-nothing transaction: snapshot (git checkpoint, or in-memory copy on a
non-git target) → apply diffs with **context validation** → **post-apply `ast.parse`** → run pytest (if
the project looks like Python) → roll the whole batch back on *any* failure. Create diffs refuse to
overwrite an existing file. See [SAFETY.md](SAFETY.md) for the full guarantees and limits.

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

See [SAFETY.md](SAFETY.md) for the apply/rollback safety model and [ONBOARDING.md](ONBOARDING.md) for maintainer workflows.
