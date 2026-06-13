# reducto Roadmap

What is shipped today versus what is planned. This is the actionable index;
[`docs/DESIGN.md`](docs/DESIGN.md) holds the long-form product vision.

Status legend: **done** = shipped & tested · **planned** = intended next · **idea** = vision, not scheduled.

## Path to v1 — what we are aiming at

**Goal.** A tool you can trust on a real Python repo: it *analyzes* safely (read-only) and *modifies*
code only when the edit is provably correct and reversible. We release in two lanes:

- **v1-analyzer (ready now):** `analyze`, `check`, and every `--dry-run` / `--report` flow. These are
  read-only, tested, and safe to ship today.
- **v1-modifier (blocked):** anything that writes to disk (`idiomatize`/`pattern`/`deduplicate`
  without `--dry-run`, and `apply`). **Not safe yet** — see P0 below.

**Why the split.** The whole value proposition of a "compression engine" is *safe in-place edits*.
Right now the apply path can silently corrupt files, so the modifier lane cannot be called v1 until
P0 lands. The analyzer lane already delivers real value (hotspots, quality issues, previews) with no
write risk.

### P0 — Fix the apply pipeline (blocker; corruption bug, not a feature)

**Problem (verified).** Heuristic `idiomatize` emits each `FileChange` from a *snippet* (the 2–3 loop
lines). `services._change_to_diff` runs `difflib.unified_diff` on that snippet, so the hunk line
numbers are relative to the snippet (1..N), not the file. `workspace.apply_diff` then applies them at
those absolute line numbers, and `diff._apply_hunk` never checks context — so the edit lands at the
top of the file. Reproduced: a docstring got overwritten and the file became invalid Python while the
original loop was left untouched. Scope: heuristic `idiomatize` apply (other paths use whole-file or
new-file `original`, so their diffs are positionally consistent).

**Steps.**
1. `reducto/agents/idiomatizer.py` — accumulate per-file edits as `(start_line, end_line, replacement)`
   spans and apply them to a copy of the file's lines (in reverse order), emitting **one** `FileChange`
   per file with `original = full file`, `modified = full new file`. This makes the diff file-relative
   and also fixes multi-edit line drift within a file.
2. `reducto/diff.py` — make `_apply_hunk` verify that context (` `) and removed (`-`) lines match the
   file at `old_start`; raise `DiffError` on mismatch instead of editing blindly. Defense-in-depth: a
   stale/misaligned diff then fails loudly and `apply_changes_safe` rolls back.
3. Confirm `pattern`/`deduplicate`/LLM-rewrite apply paths still work (they already pass whole-file or
   new-file `original`).

**How to test.**
- Unit (`tests/unit/test_idiomatizer.py` or a new `test_apply_idiomatize.py`): idiomatize a file whose
  idiom is **not** at line 1, run `App.apply_plan(plan, run_tests=False)` into a `tmp_path`, then assert
  the file `ast.parse`s, the edit landed at the right lines, and untouched defs/docstrings are intact.
- Diff unit (`tests/unit/test_diff.py`): a hunk whose context does not match the target raises `DiffError`.
- E2E (`tests/e2e/test_cli_smoke.py`): after `idiomatize --yes` on `sample_repo`, assert **every** `.py`
  still `ast.parse`s. (Today the e2e only checks exit code — which is exactly why the bug shipped.)

**Importance.** Highest. Until this lands, `--yes`/`apply` can commit broken code; git-rollback only
saves repos that have a failing test to trip on. This single fix is the gate to calling the modifier
lane v1.

### P1 — Make `deduplicate` honest (or real)

**Problem.** `deduplicate` only writes a copy into `utils/<symbol>_dedup.py`; it never removes the
duplicate definitions or rewrites call sites, so it does not actually reduce duplication.

**Steps (pick one for v1).**
- *Cheap/honest:* relabel output and `--help` to "propose shared util (suggestion only)"; keep it as a
  report, not an edit. Ship this for v1.
- *Real (post-v1):* rewrite call sites — only safe when duplicates share a name (replace each extra
  `def` with `from <pkg>.utils.<x> import <name>`), or behind an explicit `--rewrite` flag, and only
  with a correct import path (needs the cross-file symbol layer from Mid-term).

**How to test.** Unit asserting the suggestion-only plan and (for the real path) that call sites import
the canonical and the module still imports/`ast.parse`s; gate the destructive path behind tests in the
target repo.

**Importance.** Medium-high. It is a headline command; v1 must not *imply* it compresses when it only
suggests. Honest labeling is a 1-line-of-truth fix; real rewrite is a feature.

### P2 — Apply robustness & guard rails (hardening)

**Steps.** Default `idiomatize`/`pattern`/`deduplicate` to dry-run unless `--yes`/`--apply` (already
require approval); refuse to apply in a dirty git tree without `--yes` (already warns); surface a clear
message when `deduplicate` runs without embeddings (returns nothing today). Add a post-apply
`ast.parse` sanity check that triggers rollback on any syntactically-broken result.

**How to test.** Unit: apply that produces invalid Python rolls back and reports failure. E2E: dirty-tree
apply without `--yes` exits non-zero.

**Importance.** Medium. Turns "trust the tests" into "trust the tool even without tests."

### After v1
Resume the Near-term list below (remaining idioms via the LLM path, real dedup rewrite) and Mid-term
(cross-file symbol layer, JSON/HTML reports, `--ci` mode).

## Now — v1.0 (shipped & tested)

| Capability | Status | Notes |
|------------|--------|-------|
| `analyze` — tree-sitter symbols + cyclomatic & cognitive-complexity hotspots | done | Static, no LLM. Cognitive complexity is nesting-weighted, distinct from cyclomatic. |
| `deduplicate` — embedding clustering → proposed `utils/<symbol>_dedup.py` | done (suggest-only) | Proposes a shared module; does **not** remove dupes or rewrite call sites. See P1. |
| `idiomatize` — comprehensions (list/dict/filtered), `is None`, `len()` truthiness, `==`-chain → `in` | detection done; **apply broken** | Detection + `--dry-run` are correct. On-disk apply mis-places snippet edits and can corrupt files — see P0. Optional LLM whole-file rewrite (`--model`) applies correctly. |
| `pattern` — factory/strategy/observer/singleton templates | done | Generates template modules / wraps global state; opt-in LLM refactor of the matched file when `--model` is set. |
| `check` — naming, function length, per-function cyclomatic complexity | done | `critical` when CC ≥ 2× threshold. |
| Unified thresholds | done | `check` and `analyze` both read `AppConfig.complexity_thresholds`. |
| Git checkpoint + test-driven rollback | done | All-or-nothing apply; reverts if pytest fails. **Only protects repos that have tests** — a broken edit on a test-less repo is committed (see P0/P2). |
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
