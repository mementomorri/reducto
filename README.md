# reducto

**Semantic Code Compression Engine**

Autonomously refactor codebases to reduce complexity and eliminate duplication while maintaining functional parity.

## Install

### pip (recommended)

Requires **Python 3.14+**.

```bash
pip install reducto
# or with semantic deduplication (ChromaDB + embeddings):
pip install "reducto[embeddings]"
```

### From source

```bash
git clone https://github.com/alexkarsten/reducto.git
cd reducto
pip install -e ".[embeddings]"
```

### Optional extras

| Extra | Purpose |
|-------|---------|
| `embeddings` | Semantic deduplication (ChromaDB + sentence-transformers) |
| `go` | Marker for Go target repos — requires `go` on PATH for `go test` when analyzing `go.mod` projects |

**LSP (Linux):** `find_references` uses `pylsp`, `pyright-langserver`, `gopls`, or `typescript-language-server` if installed on PATH.

### Quick install script

```bash
curl -sSL https://raw.githubusercontent.com/alexkarsten/reducto/main/install.sh | sh
```

### Docker

```bash
docker build -t reducto .
docker run -v "$(pwd):/work" -w /work reducto analyze .
```

## Prerequisites

- **Python 3.14+**
- *(Optional)* **Ollama** for local LLM inference
- *(Optional)* API keys for cloud models via LiteLLM

## Usage

```bash
reducto analyze .              # Scan for complexity hotspots
reducto deduplicate .          # Find duplicate blocks; suggest shared utils (see Plan modes)
reducto idiomatize .           # Suggest idiomatic improvements (Python heuristics)
reducto pattern factory .      # Suggest design-pattern templates
reducto check .                # Quality checks
reducto apply <session-id>     # Apply a saved plan
reducto sessions list          # List saved sessions
```

### Plan modes

| Command | What the plan contains |
|---------|-------------------------|
| `deduplicate` | Embeddings find similar blocks; proposes new `utils/<symbol>_dedup.py` files. Does **not** rewrite call sites yet. |
| `pattern` | Adds advisory templates under `strategies/`, `factories/`, etc. (or in-file singleton suggestion). |
| `idiomatize` | Python-only heuristics (e.g. list comprehensions). Skips non-`.py` files. |
| `apply` | Applies diffs via git checkpoint; rolls back if tests fail. |

### Flags

- `--dry-run` — preview changes without applying
- `--yes` — skip approval prompts
- `--report` — write markdown report under `.reducto/`
- `--model` — LLM override (e.g. `gpt-4o`, `ollama/qwen2.5-coder:1.5b`)
- `--prefer-local` / `--prefer-remote` — Ollama vs cloud models

## Architecture

Single Python package: Typer CLI, in-process `Workspace` (repo walk, tree-sitter parse, git safety, tests), and AI agents (LiteLLM + optional embeddings).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


## License

[MIT](LICENSE) © 2026 Alex Karsten
