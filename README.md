# reducto

**Semantic Code Compression Engine**

Autonomously refactor codebases to reduce complexity and eliminate duplication while maintaining functional parity.

## Install

### pip (recommended)

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

- **Python 3.10+**
- *(Optional)* **Ollama** for local LLM inference
- *(Optional)* API keys for cloud models via LiteLLM

## Usage

```bash
reducto analyze .              # Scan for complexity hotspots
reducto deduplicate .          # Find and eliminate duplication
reducto idiomatize .           # Suggest idiomatic improvements
reducto pattern factory .      # Apply a design pattern
reducto check .                # Quality checks
reducto apply <session-id>     # Apply a saved plan
reducto sessions list          # List saved sessions
```

### Flags

- `--dry-run` — preview changes without applying
- `--yes` — skip approval prompts
- `--report` — write markdown report under `.reducto/`
- `--model` — LLM override (e.g. `gpt-4o`, `ollama/qwen2.5-coder:1.5b`)
- `--prefer-local` / `--prefer-remote` — Ollama vs cloud models

## Architecture

Single Python package: Typer CLI, in-process `Workspace` (repo walk, tree-sitter parse, git safety, tests), and AI agents (LiteLLM + optional embeddings).

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Migrating from pre-1.0 (Go + sidecar)

- Install via `pip install reducto` (no Go binary).
- `reducto mcp` removed; tools run in-process.
- Deduplication needs `pip install "reducto[embeddings]"`.
- Config env prefix: `REDUCTO_*` (replaces legacy `DEHYDRATE_*`).

## License

[MIT](LICENSE) © 2026 Alex Karsten
