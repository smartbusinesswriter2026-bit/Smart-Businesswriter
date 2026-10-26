# HANDOFF — instructions for the next coding agent

You are taking over a working repo, not starting one. Read this file first, then `CONTRIBUTORS.md`, `HOME.md`, and the top three entries of `WORKLOG.md`. Do not re-architect anything; the rules below are the product.

## 1. Where things are and how to run them

```
Project root : D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline
Python       : 3.14 (stdlib only at runtime; scipy/numpy are offline fixture generators, never imported by src/)
Git          : branch master, last commit 3dfb56d, no remote, clean tree expected
Build        : 0.40 (see docs/CHANGELOG.md)
Tests        : 510 tests, all passing
```

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python -m unittest discover -s tests     # expect the final line "OK"; pwsh may still print [exit code: 1] because ResourceWarnings go to stderr - read the "OK" line, not the exit code
python -m bp.server 8000                 # workbench at http://127.0.0.1:8000
python -m bp.ingest file.csv             # ingestion CLI
python -m bp.literature drift retrieval_log.jsonl 20
```

## 2. The non-negotiables (short version of CONTRIBUTORS.md)

1. A model may propose; **code computes every number**. No model-authored figures.
2. **No invented sources.** Citations are resolved-and-verified or labelled `unverified_user_supplied`.
3. **Never weaken the verifier** to get green: no loosened tolerances, no deleted checks, no edited expected values, no skipped tests.
4. **Fail closed**: unknown method, unsupported format, failed check, unwritable audit log → block with a reason.
5. **Stdlib only at runtime.** No new runtime dependencies.
6. Every increment: tests + `CHANGELOG.md` + `WORKLOG.md` entry + `DECISIONS.md` B-number if a convention is chosen + updated `KNOWN_LIMITATIONS.md`/`PRODUCT_GAP_MAP.md` + README/HOME if the surface changed. One commit per increment.
7. `docs/sources/` is read-only authority material. Never edit it.
8. Do not mark a gap closed, or a PROPOSAL ratified, without the tests and an owner decision.
9. **Two model owners (B-066).** The computation owner (DeepSeek) exclusively owns `src/bp/**`, `tests/**`, the factual docs and every rule/number/citation/claim; the design owner (MiniMax) exclusively owns the workbench's presentation and aesthetics. Read `CONTRIBUTORS.md` §1A before editing; write only in your domain, and split cross-domain features into a computation commit then a design commit.

## 3. What is already built (do not rebuild)

- **Core**: frozen spec/hashed artefacts, sandboxed execution, second-route verification, claim ceilings, re-performance bundles, deterministic reports (`spec.py`, `orchestrator.py`, `sandbox.py`, `artifacts.py`, `claims.py`, `reperform.py`).
- **Methods (T1 unless noted)**: npv, breakeven, descriptive_stats, pearson/spearman, ols/ols_robust, welch_t, mann_whitney, anova, kruskal_wallis, chi_square, trend_forecast, ratio_analysis, multiple_comparison, power_analysis, missing_data_bounds, weighted_summary. Templates: SWOT, Five Forces, case_decision (T2/T4).
- **Accounting (Stage 8, T2)**: ledger kernel, schedules (depreciation/amortization/accruals), two-route cash flow, closing + retained-earnings rollforward, declarative engagement spec, reconciliation, account-mapping checkpoint, plain-text statement exports. Ledger engine choice open (B-032).
- **Retrieval**: Crossref→OpenAlex with declared failover and recorded attempts, response SHA-256 + UTC time, durable append-only JSONL log, drift sweep, APA 7 + Harvard citation formatting.
- **Ingestion**: CSV/TSV + XLSX → typed table with provenance; PDF/scan/OCR/SPSS refused explicitly.
- **Model boundary**: DeepSeek/OpenAI-compatible/Anthropic adapters, proposals-only validation, held-out evaluation scaffold (synthetic fixtures only).
- **Research & Evidence Workflow (REW)**: living manual ratified as authority (R11) with stages R0–R8 **proposed**, none built.
- **Documentation spine**: CONTRIBUTORS, HOME, WORKLOG, DECISIONS (B-001…B-065), CHANGELOG, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP.

## 4. Owner decisions that gate work (ask before building)

| Id | Decision needed | Blocks |
|---|---|---|
| B-005 | Name expert reviewers, or accept T2 relabelling | Any T2→T1 promotion, breadth |
| B-028 | Pick next framework templates (PESTEL, VRIO, Value Chain, BMC, MCDA) | P2 breadth |
| B-032 | Ledger engine: custom kernel vs Beancount arm | Accounting tier, tax/valuation |
| B-052 | Taxation deferred; do not build without resuming the decision | Tax work |
| REW R1–R10 | Ratify (or not) the proposed stages/checkpoints/taxonomy | Any REW stage build |

Do not invent answers to these. If the owner says "go", build only what is listed below as unblocked.

## 5. The work left, in priority order, with acceptance criteria

### A. Ingestion → method-input mapping (unblocked, recommended first)
**Why**: ingestion produces a table, but a user must still copy values by hand into a method request.
**Do**: add a pure helper `ingest.to_method_inputs(table, method_id, columns: dict)` that maps named columns to a method's declared `input_schema` and refuses type conflicts (e.g. a `text` column into `values`). Extend `POST /api/ingest` with optional `map: {"method": ..., "columns": {"values": "score"}}` → response gains `inputs` (ready for `POST /api/sessions`) plus a note that mapped inputs carry provenance `sourced` with the file's SHA-256. No column semantics invented: only the user's mapping is used.
**Acceptance**: unit tests (valid mapping, wrong type refused, unmapped required input refused, unknown method refused, determinism), API tests, workbench "Use column…" wiring or at least a documented JSON example, docs (B-066, changelog, limitations, gap map row), full suite green.

### B. Standards / filings / tax retrieval sources (blocked on an owner source decision)
**Do not implement** until the owner names sources and licensing. Questions to ask: which accounting standards (and is retrieval licensed?), which filing source (e.g. SEC EDGAR is free; confirm jurisdiction), tax (B-052 deferred). When answered: add sources behind the existing `Source` boundary, keep fail-closed verification, extend `test_literature*`, docs.

### C. Statistics remainder (partly blocked on a declared model)
1. **Paired / one-sample t-tests** — unblocked. T1: impl + Fraction/float second route + goldens (scipy offline) + 5 frozen checks + sandbox `CASES` + session input map + preset + docs.
2. **Factorial ANOVA / ANCOVA / repeated measures / post-hoc** — post-hoc needs `multiple_comparison` (already built) as the declared correction; factorial needs a declared sums-of-squares convention.
3. **Logistic regression** — needs declared convergence/regularisation defaults.
4. **Reliability (Cronbach's α), factor analysis, clustering** — need declared extraction/rotation/k conventions; clustering T2 with a labelled evaluation set.
5. **Imputation / complex-design inference** — requires an owner-declared model (recommended default: none; keep extreme-case bounds only). Do not invent.

### D. REW stages (blocked until R1–R10 ratified)
If ratified, start with the cheapest real slice: R0 intake → R1 literature search with the existing retrieval + screening log → R2 gap statement. Acceptance includes the stage contracts in the manual.

### E. Breadth (blocked on B-005/B-028)
Framework templates as T4 structure-only, each with evidence schema + checks, registry linkage, docs.

### F. Non-computational product gaps (unblocked but larger)
AI-use disclosure export, reviewer sign-off workflow, multi-period comparatives, case workspace retention/privacy, model pinning/drift gate, security/privacy review, budgets/observability. Each needs its own B-decision before building.

### G. Stage 8 remainder (blocked on B-032)
Beancount arm / final engine decision; standards retrieval feeding the statements; tax once resumed.

## 6. Definition of done for the whole product (checklist)

- [ ] All owner decisions in §4 resolved.
- [ ] REW stages built and ratified (R1–R10).
- [ ] Statistics set complete per manual §9B.2/9B.3 (ipso facto no undisclosed under-reporting).
- [ ] Finance/valuation: DCF+WACC, unit economics, CBA/CEA/SROI.
- [ ] Accounting: engine decided, standards retrieval, tax (or explicit non-goal re-confirmed).
- [ ] Retrieval covers standards/filings/tax + literature; every number-bearing rule retrievable.
- [ ] Ingestion covers PDF/scan (with unverified-text labelling + human confirm) and SPSS.
- [ ] AI-use disclosure export + reviewer workflow + case workspace.
- [ ] Model quality measured on real held-out cases, not synthetic fixtures.
- [ ] Full suite green; KNOWN_LIMITATIONS matches reality; WORKLOG current.

## 7. Working style that keeps this repo healthy

- Run the full suite before and after; report the true count.
- Prefer editing over rewriting; read a file before changing it.
- Add the trap test for every bug fixed; never edit an expected value to go green.
- Keep new methods/templates behind the existing contract (`Method(...)` with tests, second route, checks, sandbox parity, preset).
- Commit with a message that states what changed, what verifies it, and the test count; update docs in the same commit.
- If you are unsure whether something is a convention decision, stop and log it as a B-decision question rather than inventing a default.
