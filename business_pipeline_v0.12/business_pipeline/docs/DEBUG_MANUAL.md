---

## 10. Debugging guide (for any model or developer touching this pipeline)

### 10.1 Before you touch anything

1. Read this manual in full. It is binding. Changes to rules require the owner's explicit order.
2. Read `docs/HANDOFF.md` for current build state, tests, and open work.
3. Read `corpus-db/CORPUS_DB.md` for retrieval/citation work.
4. Read `docs/TIPS_FINANCIAL_STATEMENTS.md` for financial statement work.
5. Run the test suite first to establish a baseline:
   ```
   $env:PYTHONPATH="src"; python -m pytest tests/test_statement_plan.py tests/test_statement_reader_seams.py tests/test_product_statements.py tests/test_product_statements_api.py tests/test_schedule_routes.py tests/test_statements_render_contract.py -q
   ```
   Expected: 184 passed, 8 subtests passed. If not, the tree is already broken — fix that first.

### 10.2 File map (what lives where)

| File | Purpose | Mutable by self-heal? |
|---|---|---|
| `src/bp/statement_plan.py` | Plan layer: 59 adjustment functions, build(), resolve_adjustments() | No (frozen core) |
| `src/bp/statement_extract.py` | Model prompt builder, validate() | No (frozen core) |
| `src/bp/statement_chart.py` | Default chart of accounts | No (frozen core) |
| `src/bp/statement_detect.py` | Detection cues (optional fast-path) | No (frozen core) |
| `src/bp/schedule_math.py` | Frozen schedule arithmetic (7 kinds) | No (frozen core) |
| `src/bp/finance_methods.py` | Additional registered methods | No (frozen core) |
| `src/bp/methods.py` | Method registry (185 methods) | No (frozen core) |
| `src/bp/ledger.py` | Account, Chart, Entry, posting | No (frozen core) |
| `src/bp/product/statements.py` | Tile logic: solve(), _record(), routes, handle() | No (logic) |
| `src/bp/product/schedules.py` | Schedule detection + rendering | No (logic) |
| `src/bp/product/tier1_tables.py` | Data-table loader (RULES, SCHEMAS) | Yes (data only) |
| `src/bp/product/statement_library.py` | Learning library (SQLite) | Yes (data only) |
| `src/bp/product/income_statement.py` | Income statement computation + classification | No (logic) |
| `src/bp/product/statements_verify.py` | Output verification | No (frozen core) |
| `src/bp/product/verify.py` | freeze(), plan hash | No (frozen core) |
| `src/bp/server.py` | Server, attach_core() | No (wiring) |

### 10.3 The 5 traps (silent failures)

1. **Stale server process.** Code changes on disk are not picked up by a running server.
   Always kill python, clear `__pycache__`, restart. Symptoms: "model returned nothing" on a
   problem that should be a schedule.

2. **Encoding.** Files may contain non-UTF-8 bytes (0x97, 0x9d). Always read/write with
   `encoding='utf-8'`. PowerShell heredocs mangle quotes — write `.py` files instead.

3. **Circular imports.** `tier1_tables.py` loads lazily. If you add a new import that triggers
   a circular dependency, the module will partially initialize. Test with `python -c "import bp.product.statements"`.

4. **Frozen contract fixture.** `tests/fixtures/statements-record.json` must regenerate
   byte-identically. If you change pipeline output, run
   `python qa/manual/make_statements_fixture.py` and verify the contract test passes.
   Never hand-edit the fixture.

5. **Test pollution.** Tests write to the real library DB unless `BP_STATEMENT_LIBRARY_DIR`
   is set. The conftest.py handles this. If you add a new test file, ensure it sets the env var
   or uses the conftest.

### 10.4 How to add a new schedule (the sanctioned way)

1. Add a function to `src/bp/schedule_math.py` (frozen arithmetic).
2. Add an entry to `schedules.SCHEMAS` (or append via `tier1_tables.append_schema()`).
3. Add detection + rendering in `src/bp/product/schedules.py` if needed.
4. Add to `COMPUTATIONS` dict in `schedule_math.py`.
5. Add a test in `tests/test_schedule_routes.py` with the exact answer key.
6. Run the full suite.

### 10.5 How to add a new account placement rule

1. Add a tuple to `RULES` in `src/bp/product/statements.py` (or via `tier1_tables.append_rule()`).
2. Format: `(pattern, type, section, line, role, activity, contra)`.
3. Test: `place("your label")` should return candidates.
4. Add a test in `tests/test_statement_reader_seams.py`.

### 10.6 How to add a new adjustment type

1. Add a function to `statement_plan.FUNCTIONS` (frozen computation).
2. Add a branch in `_adjustment_specs()` in `statements.py`.
3. Test with a problem that uses the adjustment.

### 10.7 The self-healing loop (for debug models)

The loop is:
1. Tier 1 fails → records `tier1_gaps` (missing/unplaceable labels)
2. Model loop solves it → records entries/adjustments
3. Reading diff computed → proposal generated
4. Proposal validated against held-out set (8 solved + corpus seeds)
5. If valid: applied to `tier1_tables.json` (data only)
6. Original problem re-run through tier 1 → "healed" record

**What a debug model may auto-change:**
- `tier1_tables.json` (synonyms, classifier patterns, schedule schemas)
- `checklist.json` (new verification steps — proposed, not code)

**What a debug model must NEVER auto-change:**
- Any `.py` file (logic)
- `methods.py`, `statement_plan.py`, `ledger.py`, `schedule_math.py` (frozen core)
- `STATEMENTS_PIPELINE_MANUAL.md` (binding rules)
- Test files (they are the specification)

**What a debug model may propose (but not apply):**
- New methods in `methods.py` (as a PR for owner review)
- New routes in `statements.py` (as a PR for owner review)
- New adjustment types in `_adjustment_specs` (as a PR for owner review)

### 10.8 API endpoints for the self-healing UI

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/cases/statements/proposals` | GET | List pending proposals from gap report |
| `/api/cases/statements/heal-log` | GET | View heal history |
| `/api/cases/statements/heal` | POST | Apply a proposal (body: {proposal, held_out}) |
| `/api/cases/statements/heal/history` | GET | View heal history (with limit) |
| `/api/cases/statements` | POST | Solve a problem (records to library) |
| `/api/cases/statements/{id}` | GET | View a solved record |

### 10.9 Test commands

```powershell
# Core statement tests (fast, ~2s)
$env:PYTHONPATH="src"; python -m pytest tests/test_statement_plan.py tests/test_statement_reader_seams.py tests/test_product_statements.py tests/test_product_statements_api.py tests/test_schedule_routes.py tests/test_statements_render_contract.py -q

# Gap report
$env:PYTHONPATH="src"; python scripts/gap_report.py

# Regenerate frozen fixture (only after intended pipeline change)
$env:PYTHONPATH="src"; python qa/manual/make_statements_fixture.py
```

### 10.10 Hard rules summary (binding, never violated)

1. No invented evidence, sources, numbers or citations.
2. Gaps named, never filled.
3. Student inputs stay student inputs.
4. No silent framework substitution.
5. Computations come from the frozen core.
6. A paper never contains template instructions.
7. Export blocked when paper is incomplete.
8. Global product: no PSE/PSEi, no Philippine place names, USD only.
9. The model may do everything except arithmetic.
10. Grounding is lifted. The model may propose derived figures.
11. No council. One model proposes; gates verify.
12. No hand-built detectors (except tier-1 data tables).
13. No 8-function registry. methods.py (185 methods) is the coverage.
14. Gaps named, never filled.
15. Learning library is append-only. Never auto-changes code.
16. Deterministic tier never refuses in place of model loop.
17. Stated rules never disregarded or altered without owner permission.
18. No patch fixes. General capabilities only.
19. Auto-apply limited to tier-1 data tables. Logic files frozen.
20. Held-out validation before application. Regressions rejected.
MDEOF
echo "written"