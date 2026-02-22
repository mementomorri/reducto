# reducto

**Semantic Code Compression Engine**

Autonomously refactor codebases to reduce complexity and eliminate duplication while maintaining 100% functional parity.

## Install

### Quick Install (Linux/macOS)

```bash
curl -sSL https://raw.githubusercontent.com/alexkarsten/reducto/main/install.sh | sh
```

### Docker

```bash
docker pull ghcr.io/alexkarsten/reducto:latest
docker run -v $(pwd):/app ghcr.io/alexkarsten/reducto analyze /app
```

### Build from Source

Requires Go 1.24+ and Python 3.10+.

```bash
git clone https://github.com/alexkarsten/reducto.git
cd reducto

# Install Python dependencies
pip install python/

# Build and run
go build -o reducto ./cmd/reducto
./reducto analyze .
```

### Prerequisites

- **Python 3.10+** - Required for AI-powered analysis
- **pip or uv** - For Python dependency management
- *(Optional)* **Ollama** - For local LLM inference

## Usage

```bash
reducto analyze .              # Scan for complexity hotspots and duplicates
reducto deduplicate .          # Find and eliminate code duplication
reducto idiomatize .           # Transform code to idiomatic patterns
reducto pattern factory .      # Apply a design pattern
```

### Flags

- `--dry-run` - Show proposed changes without applying (useful for CI/CD)
- `--yes` - Skip approval prompts, apply changes automatically
- `--commit` - Commit changes to git after successful refactoring
- `--report` - Generate a detailed report

## Features

- **Cross-file deduplication** - Detect semantically similar code using embeddings
- **Idiomatic transformation** - Convert to Pythonic, modern JS, Go idioms
- **Design pattern injection** - Apply Factory, Strategy, Observer patterns
- **Complexity detection** - Identify cyclomatic/cognitive hotspots
- **Git-integrated safety** - Checkpoints, rollback on test failure
- **Local-first AI** - Use Ollama locally or cloud providers via LiteLLM

## Documentation

- [Architecture Overview](docs/TECH_STACK.md)
- [Design Rationale](docs/DESIGN.md)
- [Testing Philosophy](docs/TEST_RULES.md)
- [Contributing Guidelines](AGENTS.md)

## License

[MIT](LICENSE) © 2026 Alex Karsten
