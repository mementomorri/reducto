# reducto Roadmap

What is shipped today versus what is planned. This is the actionable index;
[`docs/DESIGN.md`](docs/DESIGN.md) holds the long-form product vision.

Status legend: **done** = shipped & tested · **planned** = intended next · **idea** = vision, not scheduled.

## Now — v1.0 (shipped & tested)

| Capability | Status | Notes |
|------------|--------|-------|
| `analyze` — tree-sitter symbols + cyclomatic & cognitive-complexity hotspots | done | Static, no LLM. Cognitive complexity is nesting-weighted, distinct from cyclomatic. |
| `deduplicate` — embedding clustering → proposed `utils/<symbol>_dedup.py` | done | Proposes a shared module; does not yet rewrite call sites. |
| `idiomatize` — comprehensions (list/dict/filtered), `is None`, `len()` truthiness, `==`-chain → `in` | done | Line-level heuristics, Python-only. Optional LLM rewrite when `--model` is set. |
| `pattern` — factory/strategy/observer/singleton templates | done | Generates template modules / wraps global state; opt-in LLM refactor of the matched file when `--model` is set. |
| `check` — naming, function length, per-function cyclomatic complexity | done | `critical` when CC ≥ 2× threshold. |
| Unified thresholds | done | `check` and `analyze` both read `AppConfig.complexity_thresholds`. |
| Git checkpoint + test-driven rollback | done | All-or-nothing apply; reverts if pytest fails. |
| Session persistence / replay (`apply`, `sessions`, `report`) | done | JSON under `.reducto/sessions/`. |
| LiteLLM model routing (local Ollama / remote) | done | Wired into `idiomatize` as an opt-in suggestion path. |
| Config: `.reducto.yaml` + `REDUCTO_*` env overrides | done | |

## Near-term (planned)

- **More idioms (heuristic tail)** — remaining patterns in `test-python-code/python/style/non_idiomatic.py` that need multi-line body rewrites: `enumerate` (drop `range(len(...))`), f-strings, `with`-statement context managers, `itertools.product`, `str.join`. These are better handled holistically by the opt-in LLM rewrite path; only add brittle regex versions if there is clear demand. (Done: list/dict/filtered comprehensions, `is None`, `len()` truthiness, `==`-chain → `in`.)
- **Real deduplication** — rewrite call sites to import the extracted util, not just emit the module. *Deferred:* safe only with cross-file symbol resolution + test coverage; the fixture duplicates have different names and the extracted module has no reliable import path. Safe interim options: rewrite only when duplicates share a name, or gate behind an explicit `--rewrite` flag.

## Mid-term

- **Cross-file impact analysis** — re-introduce an LSP/symbol-graph layer *only when a command consumes it* (dead-code detection, safe-rename impact).
- **Report formats** — JSON / HTML alongside Markdown.
- **CI mode** — non-interactive `--ci` / pre-commit integration with meaningful exit codes.

## Vision (from DESIGN.md — not scheduled)

- Multi-agent orchestration (LangGraph) · pgvector persistent idiom memory · MCP server · autonomous PR-review mode · PDF reports · multi-language support.
