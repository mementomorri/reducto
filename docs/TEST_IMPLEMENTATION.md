# Testing

Requires **Python 3.14+** (matches CI and `pyproject.toml`).

New contributors: start with [ONBOARDING.md](ONBOARDING.md) for environment setup, then use this file for test commands and CI mapping.

## Run tests

```bash
pip install -e ".[dev,embeddings]"
pytest tests/ -v
```

LSP tests are excluded by default (`-m 'not lsp'` in `pyproject.toml`). Run them when a language server is on PATH:

```bash
pytest tests/unit/test_lsp.py -m lsp -v
```

## Layout

| Path | Scope |
|------|--------|
| `tests/unit/` | Agents, repo, diff, parse, git, workspace, session |
| `tests/scenario/` | Scenarios mapped to [TEST_RULES.md](TEST_RULES.md) |
| `tests/e2e/` | CLI smoke against `test-python-code/python` |
| `test-python-code/` | Fixture corpus (not shipped); used by unit/e2e tests |

Shared fixtures live in `tests/conftest.py` (`fixture_repo_root`, `fixture_files`, `temp_git_repo`).

## TEST_RULES mapping

| TEST_RULES | Automated test |
|------------|----------------|
| §1 Python-only recognition | `tests/scenario/test_test_rules.py::test_repo_detects_python_only` |
| §1 Project mapping | `test_analyze_returns_symbols` |
| §2 Cross-file dedup | `test_dedup_stub_plan_on_duplicate_pair` |
| §2 Idiomatic Python | `test_idiom_list_comp` |
| §2 Pattern injection | `test_pattern_strategy_on_complex_conditionals` |
| §3 Git checkpoint / rollback | `tests/unit/test_git.py`, `test_workspace.py` |
| §5 Report | `test_reporter_writes_markdown` |
| §6 CLI continuity | `tests/e2e/test_cli_smoke.py` |

## Lint

```bash
ruff check reducto/
black --check reducto/
mypy reducto/ --ignore-missing-imports
```

Coverage target: `reducto/` package (minimum 45% in CI; see `pyproject.toml`).

## CI analysis job

`.github/workflows/analysis.yml` runs product analysis separately from pytest:

- `reducto analyze reducto/ --report` (dogfood)
- `reducto analyze test-python-code/python --report` (fixture corpus)
- `reducto check test-python-code/python`

Markdown reports are copied to `ci-reports/` (`.reducto` is hidden and excluded by `upload-artifact` by default) and uploaded as the `reducto-analysis-reports` Actions artifact.
