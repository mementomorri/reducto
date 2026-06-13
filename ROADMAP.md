# reducto Roadmap

What is shipped today versus what is planned. This is the actionable index;
[`docs/DESIGN.md`](docs/DESIGN.md) holds the long-form product vision.

Status legend: **done** = shipped & tested · **planned** = intended next · **idea** = vision, not scheduled.

## Now — v1.0 (shipped & tested)

| Capability | Status | Notes |
|------------|--------|-------|
| `analyze` — tree-sitter symbols + cyclomatic-complexity hotspots | done | Static, no LLM. |
| `deduplicate` — embedding clustering → proposed `utils/<symbol>_dedup.py` | done | Proposes a shared module; does not yet rewrite call sites. |
| `idiomatize` — for-append → list comprehension | done | Line-level heuristic, Python-only. |
| `pattern` — factory/strategy/observer/singleton templates | done | Generates template modules / wraps global state. |
| `check` — naming, function length, per-function cyclomatic complexity | done | `critical` when CC ≥ 2× threshold. |
| Git checkpoint + test-driven rollback | done | All-or-nothing apply; reverts if pytest fails. |
| Session persistence / replay (`apply`, `sessions`, `report`) | done | JSON under `.reducto/sessions/`. |
| LiteLLM model routing (local Ollama / remote) | done | Scaffolding; not yet invoked by commands. |
| Config: `.reducto.yaml` + `REDUCTO_*` env overrides | done | |

## Near-term (planned)

- **Wire LLM-driven refactors** — call the existing `LLMRouter.complete` from `idiomatize`/`pattern` for suggestions beyond the current heuristics.
- **More idioms** — cover the patterns in `test-python-code/python/style/non_idiomatic.py`: `enumerate`, f-strings, context managers, dict/set comprehensions, `itertools`.
- **Real deduplication** — rewrite call sites to import the extracted util, not just emit the module.
- **Pattern refactoring** — transform existing code into the pattern, not only generate a template.
- **Cognitive complexity** — compute it distinctly from cyclomatic (currently equal).
- **Unify thresholds** — drive `check` and `analyze` from a single `AppConfig.complexity_thresholds`.

## Mid-term

- **Cross-file impact analysis** — re-introduce an LSP/symbol-graph layer *only when a command consumes it* (dead-code detection, safe-rename impact).
- **Report formats** — JSON / HTML alongside Markdown.
- **CI mode** — non-interactive `--ci` / pre-commit integration with meaningful exit codes.

## Vision (from DESIGN.md — not scheduled)

- Multi-agent orchestration (LangGraph) · pgvector persistent idiom memory · MCP server · autonomous PR-review mode · PDF reports · multi-language support.
