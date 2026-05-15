# Testing

## Run tests

```bash
pip install -e ".[dev,embeddings]"
pytest tests/ -v
```

## Layout

| Path | Scope |
|------|--------|
| `tests/unit/` | `repo`, `diff`, `parse`, `git_safety`, `workspace` |
| `tests/e2e/` | CLI smoke (`reducto analyze`) |

## Lint

```bash
ruff check reducto/
black --check reducto/
mypy reducto/ --ignore-missing-imports
```

Coverage target: `reducto/` package (see `pyproject.toml` pytest config).
