# reducto Roadmap

What is shipped today versus what is planned. This is the actionable index;
[`docs/DESIGN.md`](docs/DESIGN.md) holds the long-form product vision.

Status legend: **done** = shipped & tested · **planned** = intended next · **idea** = vision, not scheduled.

## Now — v1.0 (shipped & tested)

| Capability | Status | Notes |
|------------|--------|-------|
| `analyze` — tree-sitter symbols + cyclomatic & cognitive-complexity hotspots | done | Static, no LLM. Cognitive complexity is nesting-weighted, distinct from cyclomatic. |
| `deduplicate` — embedding clustering → proposed `utils/<symbol>_dedup.py` | done | Proposes a shared module; does not yet rewrite call sites. |
| `idiomatize` — list/dict comprehensions, filtered comprehensions, `is None` | done | Line-level heuristics, Python-only. Optional LLM rewrite when `--model` is set. |
| `pattern` — factory/strategy/observer/singleton templates | done | Generates template modules / wraps global state. |
| `check` — naming, function length, per-function cyclomatic complexity | done | `critical` when CC ≥ 2× threshold. |
| Unified thresholds | done | `check` and `analyze` both read `AppConfig.complexity_thresholds`. |
| Git checkpoint + test-driven rollback | done | All-or-nothing apply; reverts if pytest fails. |
| Session persistence / replay (`apply`, `sessions`, `report`) | done | JSON under `.reducto/sessions/`. |
| LiteLLM model routing (local Ollama / remote) | done | Wired into `idiomatize` as an opt-in suggestion path. |
| Config: `.reducto.yaml` + `REDUCTO_*` env overrides | done | |

## Near-term (planned)

- **More idioms** — remaining patterns in `test-python-code/python/style/non_idiomatic.py`: `enumerate` (drop `range(len(...))`), f-strings, `with`-statement context managers, `itertools.product`, `str.join`. (Done so far: list/dict/filtered comprehensions, `is None`.)
- **LLM in `pattern`** — extend the opt-in LLM path from `idiomatize` to `pattern` for code-aware suggestions.
- **Real deduplication** — rewrite call sites to import the extracted util, not just emit the module. *Deferred:* safe only with cross-file symbol resolution + test coverage; blind apply on test-less code can change behaviour.
- **Pattern refactoring** — transform existing code into the pattern, not only generate a template. *Deferred:* needs the LLM path above to be reliable.

## Mid-term

- **Cross-file impact analysis** — re-introduce an LSP/symbol-graph layer *only when a command consumes it* (dead-code detection, safe-rename impact).
- **Report formats** — JSON / HTML alongside Markdown.
- **CI mode** — non-interactive `--ci` / pre-commit integration with meaningful exit codes.

## Vision (from DESIGN.md — not scheduled)

- Multi-agent orchestration (LangGraph) · pgvector persistent idiom memory · MCP server · autonomous PR-review mode · PDF reports · multi-language support.
