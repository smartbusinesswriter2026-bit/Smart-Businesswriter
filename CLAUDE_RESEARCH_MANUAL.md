# Orientation Manual for an External Research Agent (Claude)

**Subject:** Smart Business Writer — the self-healing capability, capability-gap research, and relevance/obsolescence review

**Prepared for:** A third-party Claude research agent asked to (a) understand how the system fills capability gaps it may have overlooked, (b) verify the system stays relevant and does not become obsolete, and (c) research universities and the open web for what the system should know next.

**Source of truth on disk:** `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline` (project root for code/tests). Admin console: `http://127.0.0.1:8021/admin-sbw.html`.

**Companion reading (binding):** `AGENTS.md`, `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md`, `docs/CONDUCTOR_MANUAL.md`, `docs/HOME_CHAT_ORCHESTRATION_MANUAL.md`, `docs/CAUSE_LOOP.md`, `docs/DEBUG_MANUAL.md`, `docs/VETTED_SOURCES.md`, `corpus-db/CORPUS_DB.md`.

---

## 1. How to use this manual

1. Read **§2 (identity and non-negotiables)** and **§3 (product overview)** first. They are the contract; nothing in this manual overrides them.
2. Read **§4 (self-healing capability)** to understand the repair and growth machinery you are being asked to orient on.
3. Read **§5 (how gaps are filled today)** and **§6 (capability landscape)** to know what exists and what is missing.
4. Read **§6 (capability landscape, incl. retrieval/evidence at §6.7)** and **§7 (hard constraints)** before proposing anything.
5. Read **§8 (your research mandate)** — this is your actual job.
6. Use **§9 (known limitations / open work)**, **§10 (file map)**, **§11 (glossary)**, **§12 (suggested research questions)** and **§13 (admin API)** as reference.

Append findings to a new file you create (do not overwrite this manual). Treat everything below as the system's *current* state as of build 1.144 (4698 tests green).

---

## 2. Identity and non-negotiables

**Product:** Smart Business Writer — a global, student-facing academic/professional business-paper generator. One open composer on Home; the chat is the macro conductor. Subject modules provide frameworks and computations; the writer and renderer only format.

**Non-negotiables (binding on you and on the system):**

1. **No invented evidence, sources, numbers, citations, frameworks, methods or charts.** If it is not in the catalogue or retrieved, it does not exist.
2. **The model never does math.** All computation is delegated to the frozen core and recorded as an artifact.
3. **A dimension with no citable evidence carries a labelled background paragraph** drawn from the weak/orientation sources the retriever saw. It is not evidence, is never cited; if no background exists, the paragraph says so. Missing data is `NULL`, never an estimate.
4. **Student inputs stay student inputs.** Declared costs, volumes, figures, thesis and judgments are supplied by the student. The system may propose, never silently adopt.
5. **No silent framework substitution.** A framework may be added or replaced only when declared to the student and recorded in the plan.
6. **Computations come from the frozen core.** Call the method; do not reimplement or re-round.
7. **A paper never contains template instructions.** No `(your analysis)`, `Not supplied yet`, placeholder prose, or template names.
8. **Export is blocked when the paper is incomplete.** HTTP 409 with the missing list.
9. **The model does not research.** It edits prose only after the deterministic draft exists.
10. **Stdlib only at runtime.** No new runtime dependencies.
11. **Global product.** No PSE/PSEi name, no Philippine place name, no Philippine-specific example, currency or market claim. Neutral places and USD only (decision B-177). No subject name, home exchange or home country in the paper.
12. **No generative image for data.** Charts are deterministic specs from stored artifacts only.
13. **Planner and auditor are read-only.** They may propose/flag; they may not retrieve, compute, write or mutate state.
14. **Human approval at every gate.** Thesis, plan, evidence, prose and final paper require student approval.
15. **No council.** One model proposes; gates verify.
16. **No patch fixes.** General capabilities only.

**Two model owners (B-066/B-080):** computation owner (DeepSeek lane) owns `src/bp/**`, `tests/**`, factual docs and every rule/number/citation/claim; design owner (MiniMax lane) owns the workbench presentation and may build additive product backend (routes/modules/storage/workflows) over the frozen core. Cross-domain features split into a computation commit then a design commit.

**Frozen core status:** The core deterministic backend is currently **UNFROZEN** (B-197) until the owner freezes it again — a standing rule. While unfrozen, the computation lane may change `src/bp/**` and the pinned fixture without a fresh per-change unfreeze request, but `tests/test_frozen_contract.py` must pass, `scripts/econ_shelf.py --check` must say "frozen fixture: in sync", no check is loosened or deleted, and every behaviour change ships with a trap test that fails on the old code. Never hand-edit `tests/fixtures/frozen_contract.json`.

---

## 3. What Smart Business Writer is (product overview)

- **Surface:** one open composer on Home (`web/index.html` `RENDERERS.home()`). Single `#objective` textarea, Attach files, Run. Sends `subject: "any"`.
- **Subject detection:** `src/bp/product/guard.py` `detect_subject()` scores brief words against subject hint vocabulary.
- **Capability resolution:** `src/bp/product/capabilities.py` `resolve()` matches brief intent cues against the catalogue (90+ capabilities).
- **Computation boundary:** refuses computation briefs on framework shelves unless subject is accounting/finance.
- **Plan card:** shows selected computations, inputs, figure quotes, dependencies, drop buttons.
- **Figure normalisation:** `src/bp/product/verify.py` `normalise_number()` parses written figures; refuses bad filings.
- **Reading verifier:** `verify_reading()` refuses unknown methods, non-substring quotes, figures without quotes, overclaims, missing rationale.
- **Recompute guard:** `chat._recompute_guard` re-runs every computation from stored inputs at draft time.
- **Export gate:** `src/bp/product/paper.check` rejects level jumps, missing conclusion/references, template text.
- **Charts:** `src/bp/product/charts.py` deterministic SVG from stored artifacts.
- **Framework profiles:** `src/bp/product/framework_profiles.py` (many frameworks as data).
- **Framework keys:** `src/bp/product/chat.py` `FRAMEWORKS` (nine conductor frameworks).
- **Computation blocks:** `src/bp/product/chat.py` `COMPUTATION_BLOCKS`.
- **Computation cap:** `MAX_COMPUTATIONS = 3` per paper.
- **Length:** body-word target 600–50,000, ±10% reported. Not an export gate.
- **Rubric support:** `src/bp/product/rubric.py`.
- **Case store:** `src/bp/product/cases.py`, `chat_store.py` (durable case bundles).
- **DOCX export:** `src/bp/product/docx.py`.
- **Retrieval:** local corpus (Meilisearch) first, then vetted web by topic, then journal APIs. Crossref/OpenAlex with declared failover, response SHA-256 + UTC time, durable append-only JSONL log, drift sweep, APA 7 + Harvard.
- **Ingestion:** CSV/TSV + XLSX into typed table with provenance; PDF/scan/OCR/SPSS refused explicitly.
- **Model boundary:** DeepSeek/OpenAI-compatible/Anthropic adapters, proposals-only validation, held-out evaluation scaffold (synthetic fixtures only).
- **Pricing/PayPal:** four tiers (Starter 14.99, Pro 29.99, Studio 49.99, Agency 99.99) in `bp/product/billing.py`; bundle $99.99/mo unlimited both products.
- **Statement plan/extraction:** `src/bp/statement_plan.py`, `src/bp/statement_extract.py` — the owner's four tips; generic plan (chart, policy, journal, adjustment DAG) gated on three articulation identities.

**Paper families (§6.1 of HOME_CHAT_ORCHESTRATION_MANUAL):** Analytical report, Case analysis, Plan/proposal, Financial/valuation, Literature/synthesis, Argumentative essay, Memo/brief, Reflective, Legal/regulatory, Empirical/research, Communication. Readiness varies (some "not built": literature synthesis, reflective, legal/regulatory, communication, empirical partial).

**Subjects / shelves:** accounting, finance, marketing, management, operations, supply chain, HR/people, entrepreneurship, economics, statistics, project management, quality, and more. Framework profiles cover Five Forces, Generic Strategies, Porter's Diamond, Ansoff, BCG, GE-McKinsey, ERRC, BMC, Lean, VPC, RCA, FMEA, PDCA, Five-S, SWOT, PESTEL, Value Chain, VRIO, plus quiet document profiles (business plan, marketing plan, project plan, feasibility study, proposal).

**Conductor frameworks (9):** PESTEL, SWOT, PESTEL+SWOT, Five Forces, Value Chain, Ansoff, VRIO, Break-even, Five Forces+Break-even. (More frameworks exist as profiles/worksheets; the conductor's *registered* set is these nine.)

---

## 4. The self-healing capability (admin-sbw.html)

**URL:** `http://127.0.0.1:8021/admin-sbw.html` (served by `bp/server.py`; defaults to the Self-Healing panel). Six tabs: **Overview, Errors & fixes, Testing, Cases, Uploads, Tools**. Plus top-level Monitor (Self-Healing, Autoresearch, Run log), Quality (Validation), Tools (Chat box, Problem generation, Health, Server and storage).

### 4.1 Overview tab
- Open errors count, tile cases count, repair loop status, testable tiles count.
- Quick status cards.

### 4.2 Errors & fixes tab
- Lane filter: all / computation / framework / prose / paper / statement / tile-case.
- Status filter: open / resolved / invalid / dismissed / all.
- Select an error → "Generate problems" → model writes test problems → "Propose fix" → "Apply fix" → "Run tests".
- Regenerate problems.
- Auto-fix, propose fix, apply fix, run tests buttons.

### 4.3 Testing tab (Automated testing)
- Generate the writer's own paper for a tile from its prefilled instruction.
- Every subject is a section; tile groups collapsible; ticks survive subsection switch.
- Corpus source cited only when a page matches; empty result is a named gap.
- Style: APA 7 / Harvard. Format: Word (.docx) / Excel (.xlsx) / Both. Length: Short (600) / Mid (1,200) / Long (2,500).
- Test source: System-generated / Uploaded files / Both. Reload subjects.
- Results table with docx/xlsx/explainer downloads.

### 4.4 Cases tab (Tile cases)
- Each case is one tile's instruction, declared figures and the frozen method's result.
- A failure is logged as a tile-case error with its case id; the loop re-checks it by code with no model call.
- A pass is a stored regression test.
- Seed missing cases; Run all cases; loading indicator.

### 4.5 Uploads tab
- One upload store for both testers. A file is parsed, mapped to the selected tile's inputs automatically, gated by replay before accepted.
- Subject + Tile selectors. Dropzone + picker. Accepted: JSON, CSV/TSV, Excel, Word, PDF, TXT, image. Limit 5 MB per file.
- Multiple files at once, each gated separately.
- Coverage: cases per tile.

### 4.6 Tools tab
- Chat box (problem generation), Health, Server and storage.
- Hallucination checker: paste generated prose + evidence (JSON) → rule check or deep check (model).
- Error database card: search, rebuild.

### 4.7 Validation tab (Quality)
- Findings and proposals. Code and data proposals raised against findings.
- Source filter: all / capability_gap / validation-harness / manual.
- Status filter: open / resolved / all.
- Ingest manifest; Add finding.

### 4.8 Autoresearch panel (Monitor)
- Status: idle/running. Causes fixed %, best fixed %, fixes tried, kept/reverted.
- Start / Stop / Refresh status.
- Experiment history: what the loop tried, kept and why.
- Instruction input + "Number of problems" + "Generate problems" / "Solve problems" / "Write improvements" / "Run tests on results".

### 4.9 The error taxonomy (scopes)
`src/bp/product/causes.py` classifies every failure before it is written:

| Scope | Meaning | Written to error log? | Closed how |
|---|---|---|---|
| `transient` | provider timeout, rate limit, unreachable host | **no** | retried; re-run reopens |
| `input` | student's/generator's figures: unbalanced TB, missing figures, not an accounting problem, unsupported consolidated accounts, malformed request | **no** | refused to caller with reason |
| `pipeline` | real defect in the pipeline | **yes** | only with a durable artifact |

Only a pipeline cause is a defect.

### 4.10 Remedies (durable artifacts required to "fix")
`REMEDIES` names, per cause, the durable change a fix must write:

| Cause | Remedy | Artifact |
|---|---|---|
| `pipeline.vocabulary` | add a vocabulary rule typed from the label's keywords | `tier1_rule` |
| `pipeline.parser_shape` | a normalizer change, pinned as a golden case | `golden_case` |
| `pipeline.case_expectation` | refresh the stored case expectation | (human) |
| `pipeline.journal_human` | a human decides the abnormal balances | (human) |
| `pipeline.method_contract` | fix the method | `code` |
| `pipeline.core_missing` | wire the tile to the frozen core | (human) |
| `pipeline.unknown` | investigate | (none) |

A replay that passes **once** closes the instance and is recorded with `artifact: ""`. The ledger calls that `closed_instance`, never `fixed`. A cause with no artifact is marked **attended** with the remedy it needs, so the loop stops retrying and the owner sees what kind of change would fix it.

### 4.11 Recurrence ledger
`src/bp/product/cause_ledger.py` reads the append-only error log and reports, per pipeline cause:
- `occurrences` — instances logged
- `artifacts` — durable fixes recorded
- `fixed_at` — earliest close carrying an artifact
- `recurrences` — instances logged **after** `fixed_at`
- `status` — `fixed` (no recurrence), `recurring` (fix did not hold), `unfixed` (open, no durable fix), `closed_instance` (all closed, no artifact)

`fixed_pct = fixed / causes` is the only percentage that says the pipeline learned something. It drops when a class comes back. Admin Autoresearch panel shows the table; `/api/ops/causes` serves it.

### 4.12 Recording a cause fix
A fix lives in the repository (a paper heading, a refreshed case expectation, a vocabulary rule, a reviewed code change). Record it once, with the artifact named:
```python
ops_log.log_cause_fix("pipeline.case_expectation", "case_expectation",
  "the paper carries 'What you declared'; the checker maps the old phrase...")
```
The ledger dates the class from that record. Every occurrence before it is history; every occurrence after it is a recurrence.

### 4.13 Intake guards
A durable fix is usually a gate, not a better repair:
- **Narrative trial balance** (`problem_norm.narrative_balance`): reads `Account $amount` pairs, types each by its normal side (`normal_side`), returns debits − credits. Conservative: applies only when the problem asks for a trial balance, carries no adjusting entry, has at least four recognised accounts, and every amount-bearing label is recognised. `trial_balance_imbalance` falls back to it when the tabular reader sees no journal.
- **Request validation** and **transient provider** failures are answered to the caller and never written as errors.
- `ops_log.log_error(..., force=True)` records a legacy input error anyway; only a test of the fixer's handling of an existing record needs it.

### 4.14 Adding a cause (procedure)
1. Add one row to `REMEDIES` in `src/bp/product/causes.py` with scope, remedy, artifact, title.
2. Add the message pattern to `_RULES`, ordered before any broader pattern it would otherwise match.
3. Add classification and closure assertions to `tests/test_causes.py`.
4. If the remedy is an intake guard, wire it where the problem enters (the tile route and `chat_heal`), not only in the fixer.
5. If the remedy is a code change, the loop may **propose** it (`/api/ops/findings/*/propose-code`) but never applies it: approval is a human action, and the change ships with a test.

### 4.15 The error database (growth loop's memory)
`src/bp/product/error_db.py`:
- `qa/errors/error_registry.jsonl` — reviewable source. One line per mistake: `id`, `date`, `scope`, `cause`, `symptom`, `trigger`, `fix`, `artifact`, `files`, `tests`, `avoid`, `subject`, `tile`.
- `state/error_db.sqlite3` — cache built from the registry plus the live error log, the cause ledger and the golden regression cases. `rebuild()` regenerates it; never the source.
- `growth_brief(subject, tile, text)` — returns the lessons that match, with their "avoid" lines and the causes still open. The growth loop reads this before it scaffolds a new capability.
- `/api/ops/error-db` serves the summary and the brief; `/api/ops/error-db/search?q=` searches; `/api/ops/error-db/rebuild` rebuilds.

When a fix is learned, add its line to the registry in the same change that adds the test. A lesson with no test is a claim, not a fix.

### 4.16 What the loop does NOT do
The loop does not edit code. `autoresearch` replays, writes vocabulary rules and golden cases, and records what it could not fix; it never commits a patch. A cause that needs a code change stays `unfixed` until someone writes it. The panel says so instead of counting a dismissal as a win.

### 4.17 Autoresearch (the Karpathy loop)
`src/bp/product/autoresearch.py`:
- Picks the highest-impact open error.
- Skips errors with neither a problem nor a case id (no model call).
- Resolves a case by code (zero tokens) and a problem by flash → pro (OpenCode Go catalogue: `deepseek-v4.1-flash` then `deepseek-v4-pro`).
- When no open errors remain, replays the whole 246-case suite and stops only when that passes.
- Metric is errors-closed %.
- One attempt per error per cycle.
- Runs in a background thread. Trigger: open errors or schedule (twice daily).
- Config: `BP_AUTORESEARCH_MODEL` (default deepseek-chat), `BP_AUTORESEARCH_INTERVAL` (default 3600s), `BP_AUTORESEARCH_MAX_EXP` (default 3). `BP_AUTORESEARCH_AUTOSTART=0` opts out of auto-start at boot.
- Logs to `state/autoresearch/experiments.jsonl`. Status via `/api/ops/autoresearch/status`, experiments via `/api/ops/autoresearch/experiments`.
- Start/stop: `POST /api/ops/autoresearch/start`, `POST /api/ops/autoresearch/stop`.
- Repair runs on OpenCode Go, not platform.deepseek.com. `BP_ENABLE_DEEPSEEK` only gates platform.deepseek.com calls (statements LLM fallback, hallucination deep-check, DeepSeek search API); it does not gate repair.

### 4.18 Tile cases (stored regression tests)
`src/bp/product/case_store.py` seeds one case per testable tile under `qa/cases/<subject>/<tile>/case_NNN.json`: the tile's prefilled instruction, its declared figures, and the frozen method's own result. 246 cases seeded from published presets.

`src/bp/product/case_runner.py` replays a case through the paper path and checks:
- computation (numeric tolerance 1e-9 for Decimal trailing digits)
- paper's required phrases
- workbook sheets

A failing case logs one `tile-case` error carrying its `case_id` and the instruction. `run_cases` stores a run manifest under `state/case_runs/<run_id>/`.

`src/bp/product/auto_resolve.py`: a `case_id` error is replayed by code (zero tokens); a legacy error with a stored problem uses flash → pro. A fix is marked verified only when replay passes.

`case_invariants.py` checks that the numbers a case records agree with each other (accounting equation, ratio identities, DuPont, break-even formulas, loan totals, NPV discounting, IRR zero, WACC weights, DCF split, proforma totals, sales projection, Gini/HDI bounds, TAM>=SAM>=SOM, cap-table shares, inventory reorder point, queue utilisation). A missing input/output key skips the invariant; a wrong relationship fails the case.

### 4.19 Paper batch (Testing tab engine)
`src/bp/product/paper_batch.py` generates one real paper per subject tile from the tile's published preset objective and declared figures. The conductor runs with no framework wrapper, so the paper shows the tile's computation, not a PESTEL essay. Format selector: Word/Excel/Both. Excel workbook is the product's own `spreadsheets.to_xlsx` (Cover, Summary, Inputs, Working, Results, Notes, Record).

Financial statements tile is a service, not a frozen preset, added to Accounting/Bookkeeping group explicitly with `service: "statements"`, `supported: true`, `has_defaults: true`. Special-cased in `generate_one`: calls the statements service injected via `configure(...)`, using a deterministic sample trial balance (`STATEMENTS_BRIEF`), so preview needs no model and no API spend.

### 4.20 Upload store
One upload facility on the Uploads tab. A file is dropped or picked once, against a chosen subject and tile, stored as a case under `qa/cases/<subject>/<tile-slug>/case_NNN.json` with `origin: "uploaded"`. Upload path: read file → parse by extension → map table headers (or JSON `inputs`) onto the tile's input names → `validate_inputs` → run the method → only then write the case. A file that cannot be replayed is rejected with the reason; never stored as a case that fails later. Accepted: JSON, CSV/TSV, XLSX/XLSM (first worksheet), Word (.docx/.docm), PDF, TXT/MD, images. Limit 5 MB/file. Several files at once, each gated separately.

### 4.21 Explainer
Every paper-preview run writes `explainer.docx` into the run folder, into the ZIP, and behind `?format=explainer`. Carries per tile: objective, prefilled instruction, declared inputs, computed result, evidence counts (cited sources, background pages, named gaps) and generation status (labelled "Generation", never "test passed"). Every case run writes one `<case>_explainer.docx` per result plus a run-level `explainer.docx`. Per-case file has a "Check" section: status, problems (or the sentence that computation, invariants, paper and workbook all agree), and evidence counts.

### 4.22 Tile paper is the computation record
`paper_batch.generate_one` builds the same record the real download renders and passes it through the same renderer (`session_paper.docx_bytes`). Sections: Result; Inputs and results (What you declared / What was computed); Assumptions made; Limitations; How the figures were checked. No framework section, no "Scope and Method", no "Evidence Base", no "Discussion", no reference list (unless a source was actually declared).

### 4.23 Hallucination checker
Paste generated prose + evidence (JSON) → rule-based check or model deep-check. Endpoint implied by admin UI.

### 4.24 Admin API endpoints (self-healing)
Papers/testing:
- `GET /api/ops/papers/tiles`
- `POST /api/ops/papers/batch`
- `GET /api/ops/papers/batch/{id}`
- `GET /api/ops/papers/batch/{id}/download?format=zip|docx|explainer`
- `GET /api/ops/papers/batch/{id}/file/{name}`
- `GET /api/ops/papers/runs`

Cases:
- `GET /api/ops/cases`
- `POST /api/ops/cases/seed`
- `POST /api/ops/cases/upload`
- `POST /api/ops/cases/run`
- `GET /api/ops/cases/runs`
- `GET /api/ops/cases/runs/{id}`
- `GET /api/ops/cases/runs/{id}/file/{name}`

Errors/resolve:
- `POST /api/ops/errors/resolve` (in-pipeline fix ladder)
- `GET /api/ops/errors` (list; status filter)
- (plus cause endpoints below)

Causes:
- `/api/ops/causes` (cause ledger)
- `/api/ops/autoresearch/status`, `/api/ops/autoresearch/experiments`, `/api/ops/autoresearch/start`, `/api/ops/autoresearch/stop`

Validation/findings:
- `GET /api/cases/statements/proposals`
- `GET /api/cases/statements/heal-log`
- `POST /api/cases/statements/heal`
- `GET /api/cases/statements/heal/history`
- (validation findings/proposals endpoints referenced in admin UI)

Error DB:
- `/api/ops/error-db` (summary + brief)
- `/api/ops/error-db/search?q=`
- `/api/ops/error-db/rebuild`

Sources:
- `GET /api/cases/sources/sites?topic=`

---

## 5. How the system fills capability gaps today (growth loop)

**Current reality (honest boundary):** What exists today is a **repair loop + a test harness + a case store**. It is good at detecting that something broke, verifying a fix by replay, keeping the fix durable, and surfacing what it cannot fix. It is **not** a software engineer and does not pretend to be.

Two loops, distinct:

### 5.1 Repair loop (autonomous)
`autoresearch` + `auto_resolve`. Picks an open error, replays it, fixes it, pins a regression case. Creates nothing new; only checks whether something that used to work still works. Autonomous because a reference implementation exists for every check.

### 5.2 Growth loop (proposed, human-gated; NOT fully built)
When a capability gap is logged (an instruction the system refuses as out of scope), the system should scaffold a new method, capability entry, preset and test sketch. A human writes the logic, runs the suite, and only then is the capability committed and a case seeded. The repair loop then protects it.

**Why human approval is the thing that makes it sound:** A capability gap has no reference implementation — the code you write *is* the reference. If a model wrote both the method and the test, the test would pass by construction and prove nothing. So the first gate is not a formality; it is what makes verification possible.

### 5.3 Connection point = case store
Growth loop creates a new tile capability → case store seeds a case from its published preset → repair loop now has a reference to check against. Growth loop *creates* references; repair loop *protects* them.

### 5.4 Soundness gates (all must hold)
| Gate | Who enforces | What it prevents |
|---|---|---|
| Human writes the method logic | Computation owner | Invented formulas, silent substitutions |
| Human runs the suite | Computation owner | Green-by-construction tests |
| Frozen contract passes | `test_frozen_contract.py` | Unreviewed core changes |
| Case seeded from the preset | `case_store.seed` | A capability with no test |
| Repair loop replays the case | `auto_resolve` | A fix that does not actually work |
| Regression suite pins the fix | `regression_cases` | The same error reappearing |

Remove any gate and the growth loop stops being sound.

### 5.5 What is built for gap handling (partial)
- `ops_log.log_finding(rule="capability_gap", ...)` — gap logging path exists (used by `chat.start`'s `not_supported` and case runner's "no method").
- Validation panel gains `source=capability_gap` triage filter (proposed).
- Scaffold generator emits skeleton files into `qa/scaffolds/<subject>/<tile>/` (proposed, design lane, no core edits).
- Error DB `growth_brief(subject, tile, text)` returns lessons matching, with "avoid" lines and open causes. The growth loop must read it before proposing a method, and add a lesson in the same change that adds a test.

### 5.6 What is NOT built (honest boundary) — do not claim otherwise
- Autonomous code writing. (The patch cannot be verified without a reference.)
- Auto-wiring of scaffolds. (A scaffold is a draft; wiring before review lets unverified computation into the frozen core.)
- Agent factory (agents creating agents). (Recursive agent creation without a trust boundary = runaway cost and unreviewed computation.)
- Gap logging fully wired into the running system? The design note says "Today those refusals are shown to the user and then lost." So gap capture is incomplete.

### 5.7 Open future work (§9 of HANDOFF)
1. Human-gated growth loop (gap logging + scaffold generator) — designed, not built.
2. Local models — rejected on this hardware (Ryzen 5 2600 / 16 GB / RX 580 4 GB, no CUDA/ROCm). Stay on beam → flash → pro.
3. XLSX per tile cell-level assertions (sheet-name only today).
4. Multi-case upload ZIP (several files already supported, but not ZIP).
5. Excel upload mapping: merged cells and multi-sheet workbooks.
6. Re-open a dismissed error (no reopen route).
7. Case versioning (one case per tile today).

---

## 6. Capability landscape (what exists)

### 6.1 Conductor frameworks (registered, `FRAMEWORKS`)
PESTEL, SWOT, PESTEL+SWOT, Five Forces, Value Chain, Ansoff, VRIO, Break-even, Five Forces+Break-even.

### 6.2 Framework profiles (worksheets, many `draftable`)
Five Forces, Generic Strategies, Porter's Diamond, Ansoff, BCG, GE-McKinsey, ERRC, Business Model Canvas, Lean Canvas, Value Proposition Canvas, RCA, FMEA, PDCA, Five-S, SWOT, PESTEL, Value Chain, VRIO, Break-even, plus quiet document profiles (business plan, marketing plan, project plan, feasibility study, proposal).

### 6.3 Capabilities (90+, `capabilities.ENTRIES`) — categories
Financial feasibility: breakeven, npv, irr, discounted_payback, project_metrics, unit_economics, wacc, return_on_investment, startup_capital, cash_runway, time_value, loan_amortization, leverage_analysis, inventory_policy, sales_projection, sales_from_market, depreciation_schedule, tax_declared, equity_bridge, multi_product_breakeven, capm, bond_analysis, ratio_analysis, dcf_valuation, multiples_valuation, option_pricing, real_option, portfolio_analysis, scenario_analysis, risk_metrics, fx_parity, currency_convert, ols, ols_robust, dupont_analysis, trend_analysis, working_capital, proforma_statements, sensitivity_table, sroi, cost_benefit, cost_effectiveness, dcf_valuation.

Market/structure: market_sizing, market_share, market_concentration, cost_curves, market_power, demand_supply_equilibrium, price_control, profit_maximization, price_discrimination, cournot_duopoly, nash_equilibrium, demand_curve, elasticity, pricing_decision, fx_parity.

Customer/marketing: clv_model, campaign_efficiency, purchase_intent, rfm_scoring, sales_funnel, ab_test_two_proportion, social_engagement, cohort_retention, media_plan, web_analytics, email_list_health, customer_profitability, channel_economics, attribution_split.

Operations: queue_analysis, capacity_analysis, oee_analysis, process_control, line_balancing.

Data/stats: descriptive_stats, pearson, welch_t, anova, chi_square, trend_forecast, missing_data_bounds, weighted_summary, power_analysis, reliability_alpha, expected_utility, prospect_theory, difference_in_differences, instrumental_variables, panel_regression, regression_discontinuity, probit.

Economics/policy: growth_rate, inflation_cpi, tax_incidence, national_income, unemployment_rate, labour_market, money_multiplier, fiscal_multiplier, budget_debt, output_gap_okun, externality_pigouvian, public_good, optimal_pollution, social_welfare, gini_coefficient, poverty_measures, tax_progressivity, tariff_welfare, comparative_advantage, exchange_rate_ppp, interest_rate_parity, balance_of_payments, hdi.

Project/delivery: cpm_schedule, resource_leveling, project_crashing, schedule_risk, calendar_schedule, multi_criteria, monte_carlo, decision_tree, multi_project_schedule, earned_value.

Impact: sroi, cost_benefit, cost_effectiveness.

(Plus many more; the authoritative list is `capabilities.ENTRIES` and the CONDUCTOR_MANUAL §7.3 table.)

### 6.4 Methods (frozen core)
185 methods in `bp/methods.py` (registry). `bp/methods.describe(method)["input_schema"]`. Plan-level T1: sales_from_market, depreciation_schedule, proforma_statements, sensitivity_table. Templates: SWOT, Five Forces, case_decision (T2/T4). Statement engine: 128 specs in `financial_computations.py`, 218 distinct input names, 44 supplyable by text, 50 by another spec's output, 131 by nothing at all (43 of 128 specs have no reachable input).

### 6.5 Subjects (shelves)
Accounting, finance, marketing, management, operations, supply chain, HR/people, entrepreneurship, economics, statistics, project management, quality. Plus tools (financial statements, charts, etc.).

### 6.6 Paper families and readiness
See §3 above and HOME_CHAT_ORCHESTRATION_MANUAL §6.2. Not built: literature/synthesis, reflective, legal/regulatory, communication, empirical (partial). Mostly ready: analytical report, case analysis, plan/proposal, financial/valuation.

### 6.7 Retrieval layers
1. Corpus / Meilisearch (cited; searched alone; fastest)
2. Web (only on corpus miss; vetted pages may be cited; Wikipedia/explainers orientation only — actually Wikipedia blocked entirely now)
3. Journal APIs (only when 1 and 2 miss; slowest)

Vetted sites registry: `src/bp/product/sources.py` (`VETTED_SITES`, `TOPIC_SITES`, `TOPICS`, `SITE_TOPICS`, `SITE_PRIORITY`). Topics: ethics, culture, finance, accounting, marketing, management, operations, supply chain, HR, entrepreneurship, technology, environment, health, law, project management, industry data, company/filings, economics/policy, country data, research methods, news. Wikipedia and same-class sources blocked at provider boundary and in every layer.

### 6.8 Corpus (proprietary PDF evidence)
R2 bytes + SQLite/Meilisearch index. Living design record: `corpus-db/CORPUS_DB.md`. Build manual: `DATABASE.md` (how) and `WALKTHROUGH.md` (shape). Three ways the corpus fills itself: manual ingest, enrichment worker from learning log, etc.

---

## 7. Hard constraints any proposal must respect

If your research proposes changes, they must be compatible with:

1. **No invented evidence/numbers/citations.** Every claim needs a source or a computation artifact or a student input.
2. **Model never does math.** Proposals involving model computation are out.
3. **Frozen core.** Computation changes require the computation owner and a trap test. You may propose; you may not apply.
4. **Human gates.** Growth-loop additions require human writing the method logic and running the suite. Autonomous code writing is explicitly rejected.
5. **Stdlib only at runtime.** No new runtime deps.
6. **Global product.** No country-specific examples; neutral places and USD.
7. **No silent framework substitution.**
8. **Export blocked when incomplete.**
9. **No template text in paper.**
10. **No council.** One model proposes; gates verify.
11. **No patch fixes; general capabilities only.**
12. **Auto-apply limited to tier-1 data tables** (synonyms, classifier patterns, schedule schemas). Logic files frozen unless unfrozen under B-197.
13. **Held-out validation before application.** Regressions rejected.
14. **Wikipedia never a source or background.** Named gap instead.
15. **Parked frontier-model queue** (Tukey/Dunnett/Games-Howell, unbalanced ANOVA/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series) — do not start without an explicit owner grant of the DeepSeek Pro lane. A "continue" does not un-park them.

---

## 8. Your research mandate

You are a **research agent**, not a code writer. Your job: orient on the self-healing capability (§4), then research (universities, industry, standards bodies, academic literature, online) to find capability gaps the system may have overlooked and to ensure it stays relevant and does not become obsolete. Produce a structured findings report (a new file; do not overwrite this manual).

### 8.1 Core questions to answer
1. **Coverage gaps in capabilities:** Which business/management/accounting/finance/marketing/operations/statistics/research-method capabilities do universities teach that this system lacks? Compare the 90+ capability list (§6.3) and the method registry (§6.4) against standard curricula.
2. **Framework gaps:** Which analytical frameworks are standard in business education but absent or only partially supported? (e.g., McKinsey 7S, BCG matrix is present; Kotler, Porter's Diamond present; but many others may be missing: Blue Ocean, OKR, Balanced Scorecard, Business Model Canvas present, Lean Canvas present, etc.)
3. **Evidence/retrieval relevance:** Are the vetted sources (§6.7) still the right ones? Which official/data/research sources have emerged or changed (e.g., new standards, new databases)? Are there paywalled-vs-free shifts?
4. **Self-healing / growth-loop soundness:** Is the human-gated growth loop the right design? What do university/research sources say about autonomous self-repair in software, AI-assisted code generation verification, and human-in-the-loop ML? Are there better verification strategies?
5. **Obsolescence risks:** Which parts of the system risk becoming obsolete (e.g., model providers, retrieval APIs, standards like IFRS updates, citation styles, statistical methods)? What migration paths exist?
6. **Capability-gap logging:** The system's gap logging is incomplete (§5.6). What should a robust capability-gap capture look like per research on user-feedback mining, issue triage, and demand sensing?
7. **Evaluation/measurement:** How should the system measure "relevance" and "not obsolete"? Propose metrics (coverage of curriculum topics, freshness of sources, test pass rates, user task success, etc.).
8. **Student-facing relevance:** Does the system's output match what instructors/universities actually grade? Research rubrics, assignment types, expected deliverables.

### 8.2 Research sources to consult (universities + online)
- **Universities:** business school curricula (MBA/undergrad): Harvard Business School, Wharton, Stanford GSB, MIT Sloan, INSEAD, LBS, Chicago Booth, Kellogg, Columbia, Yale SOM, Oxford Saïd, Cambridge Judge, NUS, HKUST, IESE, HEC Paris, etc. Course syllabi, case methods, framework lists.
- **Standards bodies:** IFRS/IASB, FASB, AICPA, CFA Institute, PMI, SHRM, CIPD, AMA, ASCM, ISO, WEF, OECD, World Bank, IMF.
- **Academic literature:** Google Scholar, SSRN, arXiv (cs.CL, cs.SE), ACM/IEEE on self-healing systems, autonomous repair, LLM code generation verification, human-in-the-loop.
- **Industry/analyst:** Gartner, Forrester, McKinsey, BCG, Bain, Deloitte, PwC, Accenture insights; HBR; MIT Sloan Management Review.
- **Open web:** official documentation, GitHub repos on self-healing/autoresearch (Karpathy's autoresearch), evaluation harnesses, curriculum databases.
- **Citation/academic writing standards:** APA 7, Harvard, Chicago, MLA, Vancouver, IEEE, OSCOLA manuals.

### 8.3 What to look for (categories of gaps)
A. **Analytical frameworks** not in the conductor or profiles.
B. **Computation methods** not in the 185-method registry or the 90+ capability list.
C. **Evidence sources** missing or stale in the vetted registry.
D. **Paper types / archetypes** not supported (literature review, empirical research, legal, reflective, communication).
E. **Retrieval/verification techniques** (new relevance gates, citation verification, hallucination detection).
F. **Self-healing/repair techniques** (better error classification, recurrence handling, durable fixes).
G. **Growth-loop design** (gap capture, scaffold generation, human gates, evaluation).
H. **Obsolescence** (deprecated APIs, model providers, standards changes).
I. **Accessibility/usability** of the admin console and the research workflow.
J. **Ethics/governance** of AI-assisted academic writing (disclosure, plagiarism, academic integrity).

### 8.4 Evaluation criteria for any proposed addition
- Does it violate any non-negotiable (§2)? If yes, reject or redesign.
- Is it a general capability (not a patch fix)?
- Does it have a clear, testable acceptance criterion?
- Is there a reference implementation or authoritative source?
- Does it fit the frozen-core / product-backend boundary?
- Is it globally applicable (no country-specific)?
- Does it preserve the "model never does math" rule?
- Is the human gate preserved where needed?
- What is the cost/benefit (tokens, time, complexity)?

### 8.5 Output format expected from you
Produce a findings report (new markdown file, e.g., `CLAUDE_RESEARCH_FINDINGS.md`) with:
1. **Executive summary** (1 page).
2. **Methodology** (sources consulted, search terms, date range).
3. **Findings by category** (A–J above), each with: observation, evidence (source + link), impact on Smart Business Writer, recommendation, priority (P0/P1/P2), effort estimate (S/M/L), risk.
4. **Capability gap matrix** (proposed capability → current state → gap → suggested owner lane → test idea).
5. **Obsolescence watchlist** (item, why at risk, signal to monitor, migration path).
6. **Self-healing/growth-loop assessment** (strengths, weaknesses, recommended changes).
7. **Metrics proposal** (how to measure relevance and non-obsolescence).
8. **Recommended next steps** (ordered, with owners).
9. **Open questions for the owner** (decisions needed).
10. **Appendix:** sources list with URLs.

Be explicit about uncertainty. Mark anything you could not verify. Do not invent sources or numbers. If a source is paywalled, mark it `access: paywalled` and treat its snippet as orientation only (per VETTED_SOURCES.md).

### 8.6 Things you must NOT do
- Do not edit code, tests, or the frozen core.
- Do not apply fixes or run the repair loop.
- Do not claim the system is broken without evidence.
- Do not propose autonomous code writing (explicitly rejected by the owner).
- Do not un-park the frontier-model queue without an explicit owner grant.
- Do not invent sources, numbers, citations, frameworks, methods.
- Do not weaken or bypass human gates.
- Do not propose country-specific or exchange-specific features.

---

## 9. Known limitations and open work (from HANDOFF §5 and §9)

- 5 red tests on HEAD named in `OPEN_ISSUES.md` (Item 18): 3 product-boundary (relative import), 1 calculator keypad contract, 1 build 1.99's own test (passes alone, fails in suite due to `bp.server` wiring).
- Statements reader: live model extraction proved on two synthetic problems only, not tuned broadly.
- Retrieval: standards/filings/tax retrieval blocked on owner source decision (do not implement until owner names sources/licensing).
- Statistics remainder parked (Tukey/Dunnett/Games-Howell, unbalanced ANOVA/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series) — needs frontier-model grant.
- REW stages (R1–R10) blocked until ratified.
- Ledger engine decision (B-032) open.
- Taxation deferred (B-052).
- Bundle pricing: no live charge taken yet; I4 (shared login) not built.
- Gap logging not fully wired (refusals shown then lost).
- Scaffold generator not built.
- Case versioning: one case per tile.
- Re-open dismissed error: no route.
- Excel upload: merged cells and multi-sheet not supported.
- Multi-case upload ZIP not supported.
- XLSX cell-level assertions not built.
- Local models rejected on hardware.
- Charts in Word: table-only in phase 1; images undecided.
- Thesis/dissertation/capstone deferred (length max 5,000 words).
- Business communication: separate lane, not the paper pipeline.
- Peer review: separate workflow.

---

## 10. File map (where to look)

Project root: `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline`

Key files:
- `src/bp/server.py` — server, attach_core, routes (incl. admin endpoints).
- `src/bp/product/autoresearch.py` — the Karpathy loop.
- `src/bp/product/auto_resolve.py` — case replay + fix ladder.
- `src/bp/product/case_store.py` — seed/store cases.
- `src/bp/product/case_runner.py` — replay + checks.
- `src/bp/product/case_invariants.py` — cross-checks.
- `src/bp/product/causes.py` — scope classification, remedies, rules.
- `src/bp/product/cause_ledger.py` — recurrence ledger.
- `src/bp/product/ops_log.py` — error logging, findings, severity.
- `src/bp/product/error_db.py` — error database (registry + sqlite cache).
- `src/bp/product/paper_batch.py` — Testing tab engine.
- `src/bp/product/capabilities.py` — capability catalogue + resolver.
- `src/bp/product/chat.py` — conductor, frameworks, computation blocks.
- `src/bp/product/framework_profiles.py` — framework profiles.
- `src/bp/product/sources.py` — vetted sites registry.
- `src/bp/product/retrieval.py` — retrieval engine.
- `src/bp/product/verify.py` — reading verifier, normalise_number.
- `src/bp/product/methods.py` — method registry (185).
- `src/bp/product/charts.py` — deterministic SVG.
- `src/bp/product/docx.py` — DOCX renderer.
- `src/bp/product/paper.py` — section shape + structural checks.
- `src/bp/product/guard.py` — subject detection, fit, computation boundary.
- `src/bp/product/instruction_reading.py` — typed instruction reading.
- `src/bp/product/plan_proposal.py` — plan proposal.
- `src/bp/methods.py` — core method registry.
- `src/bp/statement_plan.py`, `src/bp/statement_extract.py` — statements.
- `src/bp/statement_chart.py`, `src/bp/statement_detect.py`, `src/bp/statement_period.py`.
- `src/bp/schedule_math.py` — frozen schedule arithmetic.
- `src/bp/product/financial_computations.py` — 128-spec engine.
- `src/bp/product/framework_writing.py`, `framework_calc.py`, `framework_figures.py`.
- `src/bp/product/portfolio_reader.py`, `project_reader.py`, `feasibility_reader.py`, `proposal_reader.py`.
- `web/admin-sbw.html` — the admin console.
- `web/index.html` — Home.
- `qa/cases/` — stored tile cases.
- `qa/errors/error_registry.jsonl` — error registry.
- `state/` — runtime state (error_db.sqlite3, case_runs, autoresearch).
- `tests/` — 4698 tests.
- `docs/` — manuals (CONDUCTOR, HOME_CHAT_ORCHESTRATION, DEBUG, CAUSE_LOOP, VETTED_SOURCES, TIPS_FINANCIAL_STATEMENTS, FINANCIAL_COMPUTATIONS_MANUAL, etc.).
- `corpus-db/` — corpus design/build/walkthrough.

Docs to read before any change (binding): `AGENTS.md`, `CONDUCTOR_MANUAL.md`, `HANDOFF.md`, `HOME_CHAT_ORCHESTRATION_MANUAL.md`, `VETTED_SOURCES.md`, `CORPUS_DB.md`, `DATABASE.md`, `WALKTHROUGH.md`, `TIPS_FINANCIAL_STATEMENTS.md`, `DEBUG_MANUAL.md`, `CAUSE_LOOP.md`.

---

## 11. Glossary

- **Capability:** a registered computation the conductor may select for a paper (90+). Each has intent cues, required inputs, slot (H1/H2), integration paragraph, licenses/limitations.
- **Framework:** an analytical lens (PESTEL, SWOT, Five Forces, etc.) with dimensions, question bank, search terms, draft branch.
- **Profile:** a framework completion configuration (dimensions, cues, queries, unit of analysis, gate, voice slots, optional writing module).
- **Block:** one unit of the paper plan (framework, computation, evidence, chart, prose, audit).
- **Plan IR:** the ordered, dependency-aware set of blocks.
- **Paper contract:** frozen agreement about what the paper is (archetype, thesis, scope, length, style, rubric, constraints).
- **Evidence ledger:** registry of retrieved sources, claims, numbers, citations, charts, gaps.
- **Claim-to-source map:** link from every claim to its evidence/computation/student input.
- **Audit:** read-only verification against contract/plan/ledger/rubric.
- **Repair:** targeted fix stage acting on audit findings.
- **Production check:** dry run proving the plan can be executed before research starts.
- **Scope (error):** transient / input / pipeline.
- **Cause:** a classified pipeline defect (`pipeline.vocabulary`, `pipeline.parser_shape`, `pipeline.case_expectation`, `pipeline.journal_human`, `pipeline.method_contract`, `pipeline.core_missing`, `pipeline.unknown`).
- **Remedy:** the durable change a fix must write (tier1_rule, golden_case, code, or human).
- **Artifact:** the durable thing a fix produces; a replay-only pass has `artifact: ""` (`closed_instance`, not `fixed`).
- **Recurrence:** instances logged after `fixed_at`.
- **Fixed pct:** `fixed / causes` — the only percentage saying the pipeline learned something.
- **Tile case:** one tile's instruction + declared figures + frozen method's result, stored as regression test.
- **Growth loop:** proposed human-gated capability scaffolding (not fully built).
- **Repair loop:** autonomous error replay + fix + regression pin.
- **Frozen core:** `src/bp/**` deterministic computation; must pass frozen contract test.
- **Vetted web:** curated registry of official/data/research/press sites, ranked by topic.
- **Orientation (background):** weak sources used for a labelled background paragraph; not cited.
- **Named gap:** a dimension with no citable evidence; never filled.

---

## 12. Suggested research questions (concrete, to seed your work)

1. What business-analysis frameworks do top-20 MBA programs require that are absent here? (McKinsey 7S, Balanced Scorecard, Blue Ocean, OKR, Hoshin Kanri, Lean Six Sigma DMAIC — PDCA present, Six Sigma not; Kotter 8-step, ADKAR, McKinsey 3 horizons, etc.)
2. Which statistical methods required in business research courses are missing from the 185-method registry? (factor analysis, cluster analysis/k-means, SEM, mediation/moderation, panel data advanced, time series ARIMA, survival analysis, conjoint, etc. — many parked.)
3. Which accounting standards updates (IFRS 18 Presentation, IFRS 9 ECL, IFRS 17 insurance, Pillar Two) require computation changes?
4. Which citation styles beyond the 8 implemented are commonly required? (APA 7, Harvard, Chicago author-date/notes, MLA 9, Vancouver, IEEE, OSCOLA present.)
5. Which evidence databases are becoming standard for business research? (Scopus, Web of Science, EBSCO, ProQuest, JSTOR, Google Scholar, SSRN, RePEc, FRED, World Bank Open Data, OECD, Eurostat, etc.)
6. How do universities handle AI-use disclosure in student papers, and what should the system's disclosure export contain? (partially parked as product-backend candidate.)
7. What are best practices for human-in-the-loop verification of LLM-generated code/scaffolds? (relevant to growth loop.)
8. How do self-healing systems in software engineering classify and repair defects? (relevant to cause taxonomy.)
9. What metrics measure "relevance" and "non-obsolescence" for an educational tool? (curriculum coverage %, source freshness, test pass rate, user task success, time-to-paper, error recurrence rate.)
10. What are the emerging requirements for accessibility, privacy, and data retention in edtech? (GDPR, FERPA, etc.)

---

## 13. Admin API quick reference (self-healing subset)

See §4.24 for the full list. Key ones:
- Status: `GET /api/ops/autoresearch/status`
- Experiments: `GET /api/ops/autoresearch/experiments?limit=20`
- Start/stop: `POST /api/ops/autoresearch/start`, `POST /api/ops/autoresearch/stop`
- Causes: `GET /api/ops/causes`
- Errors: `GET /api/ops/errors?lane=&status=&limit=`
- Resolve: `POST /api/ops/errors/resolve`
- Cases: `GET /api/ops/cases`, `POST /api/ops/cases/seed`, `POST /api/ops/cases/upload`, `POST /api/ops/cases/run`
- Case runs: `GET /api/ops/cases/runs`, `GET /api/ops/cases/runs/{id}`, `GET /api/ops/cases/runs/{id}/file/{name}`
- Papers: `GET /api/ops/papers/tiles`, `POST /api/ops/papers/batch`, `GET /api/ops/papers/batch/{id}`, `GET /api/ops/papers/batch/{id}/download?format=zip|docx|explainer`
- Error DB: `GET /api/ops/error-db`, `GET /api/ops/error-db/search?q=`, `POST /api/ops/error-db/rebuild`
- Sources: `GET /api/cases/sources/sites?topic=`
- Statements proposals/heal: `GET /api/cases/statements/proposals`, `GET /api/cases/statements/heal-log`, `POST /api/cases/statements/heal`, `GET /api/cases/statements/heal/history`

---

## 14. Final note to the research agent

- You are an orienter and researcher, not a builder. Produce findings and recommendations; do not modify the system.
- When in doubt about a constraint, default to the strictest reading of §2 and §7.
- Append your findings to a new file; never overwrite this manual or the binding docs.
- Be explicit about uncertainty and paywalled sources.
- The system's owner retains all decisions; your role is to expand the thinking, not to decide.

---

*End of manual. Version: orientation for build 1.144 (4698 tests). Update this file only when the system's self-healing capability materially changes.*
