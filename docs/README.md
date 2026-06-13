# reducto

**Semantic code compression for Python codebases**

Autonomously scan Python projects, propose refactors (deduplication, idioms, design patterns), and apply changes with git checkpoints and optional test rollback.

reducto is a **Python 3.14+** CLI and library. It only analyzes and refactors **`.py` files** in target repositories.

## Install

### pip (recommended)

```bash
pip install reducto
# semantic deduplication (ChromaDB + embeddings):
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
| `dev` | pytest, ruff, black, mypy (contributors) |

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

Run commands from the root of a **Python project** (with `.py` sources):

```bash
reducto analyze .              # Complexity hotspots and symbols
reducto deduplicate .          # Similar blocks → proposed utils modules
reducto idiomatize .           # Pythonic heuristics (comprehensions, etc.)
reducto pattern factory .      # Design-pattern templates
reducto check .                # Naming, function length, cyclomatic-complexity issues
reducto apply <session-id>     # Apply a saved plan
reducto sessions list          # List saved sessions
```

### Plan modes

| Command | What the plan contains |
|---------|-------------------------|
| `deduplicate` | Embeddings find similar functions/methods; proposes `utils/<symbol>_dedup.py`. Does **not** rewrite call sites yet. |
| `pattern` | Advisory templates under `strategies/`, `factories/`, etc. (or in-file singleton). |
| `idiomatize` | Line-level Python heuristics (e.g. list comprehensions). |
| `apply` | Applies diffs via git checkpoint; rolls back if pytest fails. |

### Flags

- `--dry-run` — preview without applying
- `--yes` — skip approval prompts
- `--report` — markdown report under `.reducto/`
- `--model` — LLM override (e.g. `gpt-4o`, `ollama/qwen2.5-coder:1.5b`)
- `--prefer-local` / `--prefer-remote` — Ollama vs cloud models

## Architecture

Single Python process: Typer CLI → `App` → `Workspace` (walk `*.py`, tree-sitter, git, pytest) + agents (LiteLLM + optional embeddings). Plans persist under `.reducto/sessions/`.

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Maintainer documentation

| Doc | Description |
|-----|-------------|
| [ONBOARDING.md](ONBOARDING.md) | Setup, layout, CI, extension points |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Modules and request flows |
| [TEST_IMPLEMENTATION.md](TEST_IMPLEMENTATION.md) | pytest and CI |
| [TEST_RULES.md](TEST_RULES.md) | Acceptance criteria |
| [DESIGN.md](DESIGN.md) | Product vision (long-form) |
| [ROADMAP.md](../ROADMAP.md) | What's shipped vs planned |

## License

[MIT](../LICENSE) © 2026 Alex Karsten
