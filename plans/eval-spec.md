# Eval Program Spec — Smart BusinessWriter Pipeline

**Status:** Step 2 locked (spec). Step 3 task breakdown + Step 4 build not started.
**Owner (decision):** Beam drafted; implementation split per ownership rules (see §7).
**Last updated:** 2026-11-10
**Companion docs (read first):** `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md`, `CONDUCTOR_MANUAL.md`, `HOME_CHAT_ORCHESTRATION_MANUAL.md`, `CONTRIBUTORS.md`, `docs/DEBUG_MANUAL.md`, `docs/CAUSE_LOOP.md`.

---

## 1. Purpose

Build an eval that measures the pipeline's ability to:

1. **Deliver the correct paper per subject/tile** (computation + structure + workbook).
2. **Retrieve quality sources from the proprietary corpus (RAG)** — on-topic, resolvable, no invented evidence.
3. **Run the self-healing / recursive / self-growth loops** with measured efficacy and cost-efficiency.
4. **Produce paper quality** (prose, no template instructions, no invented content).

The eval is a **program of three directions** (§3) sharing one downloadable docx report.

## 2. Non-negotiables (inherited, do not relax)

- No invented evidence, sources, numbers or citations.
- A dimension with no citable evidence carries a labelled background paragraph from the weak sources the retriever saw; never filled with invented evidence.
- Student inputs stay student inputs.
- No silent framework substitution.
- Computations come from the frozen core.
- A paper never contains template instructions.
- Export blocked when paper incomplete.
- Global product: no PSE/PSEi, no Philippine place name, no Philippine-specific example/currency/market claim; neutral places + USD.
- Never weaken the verifier to get green (no loosened tolerances, no deleted checks, no edited expected values, no skipped tests).
- Stdlib only at runtime.

## 3. Scope — three directions

### Direction 1 — Deterministic golden replay (offline, full coverage)
- Run `case_runner.run_cases` over all 246 seeded cases (`qa/cases/<subject>/<tile-slug>/case_NNN.json`).
- Checks per case (already in `case_runner._check`): status, expected result keys/values (1e-9 tolerance, rounded-display accepted), invariant violations (`case_invariants`), required paper phrases (contract sections + legacy mapping), paper shows ≥1 computed value, workbook sheets + values.
- **Model cost:** 0 tokens.
- **Deliverable:** pass/fail per case + invariant-breakdown + failure counter.

### Direction 2 — Live end-to-end with rubric (budget-gated)
- Run `paper_batch.generate_one` per tile through the real conductor.
- **Coverage:** at least one run per tile (246) when budget allows; start with a representative sample (~1 tile per subject, ~15–20) and scale up via a budget knob.
- **Rubric (automated):**
  - Required sections present in rendered docx.
  - Computed values appear in paper and workbook.
  - No template instructions in paper text.
  - No invented citations: every citation string resolves to a corpus page returned by `_seed_corpus` for that tile.
  - Background labelling correct (weak page → "Background Reading (not cited)", not a citation).
  - Length band met (`met_target`/`words`/`length_band`).
- **RAG scoring (locked):** (a) citation resolves to a real corpus page + (c) on-topic by rubric. Verbatim not required, but the system must be *capable* of direct quotes (the quote field must be a sentence from the page).
- **Model cost:** bounded; sample size × ~1 conductor run. Budget knob controls scale.
- **Deliverable:** per-tile score + per-tile cost + owner-readable summary.

### Direction 3 — Self-heal loop eval (fault injection + cost accounting)
- Seed known faults: broken inputs, tampered case expectation, missing paper phrase, bad corpus query.
- Run `autoresearch` / `auto_resolve`; record:
  - Causes closed (pipeline causes only; input/transient refused at intake never reach ledger).
  - Tokens spent (flash vs pro) and $ cost.
  - Durability: a fix counts only after 3 consecutive green replays.
  - Recurrence rate (cause comes back after fix).
  - Growth-loop scaffold quality: PROVISIONAL scaffold passes suite after human finishes logic.
- **Model cost:** medium-high.
- **Deliverable:** efficacy + cost-efficiency report.

## 4. Success criteria

- **Fail tolerance:** ≤2 failures allowed out of the full 246-case suite (≈0.8%). A failure counter tracks failures per run and trend over runs.
- **Coverage:** every tile run at least once in Direction 2 when budget allows; sample otherwise.
- **No regression:** a previously-passing case that fails is a build-blocker regardless of the ≤2 allowance (the allowance is for pre-existing/known failures, not new ones).
- **RAG:** zero invented citations; every cited source resolves to a corpus page; background pages are never cited.
- **Cost:** each run reports tokens and $; Direction 2/3 runs must not exceed the configured ceiling.
- **Report:** one downloadable docx, owner-readable, aggregating Directions 1–3.

## 5. Locked open questions (answers from owner)

| # | Question | Locked answer |
|---|---|---|
| Q1 | Pass threshold | ≤2 failures allowed; failure counter per run + trend |
| Q2 | Sample selection for Direction 2 | At least once per tile; increase with budget. Start with representative sample |
| Q3 | Cost ceiling + which model may score rubric | Limited live calls; rubric scorer is code (no model) unless owner opts in |
| Q4 | RAG scoring | (a) resolves to corpus page + (c) on-topic by rubric; verbatim not required but direct-quote capable |
| Q5 | Consecutive green replays to count a cause "fixed" | 3 |
| Q6 | Report location | Downloadable docx owner reads; also surfaced in admin (design lane) |
| Q7 | Does ≤2 allowance apply to new regressions | No — new regressions are always blockers |

Remaining open questions for owner before Step 3:
- Whether Direction 3 fault injection runs in a sandboxed copy of `qa/cases/` (suggest yes, to protect real cases).

## 6. Stack

- **Runtime:** Python 3.14, stdlib only (no new runtime deps).
- **Existing machinery to reuse:** `case_store`, `case_runner`, `case_invariants`, `paper_batch`, `ops_log`, `autoresearch`, `auto_resolve`, `source_finder` (corpus search), `session_paper`/`docx` renderers.
- **Storage:** `qa/cases/`, `state/case_runs/`, `state/paper_previews/`, `state/eval_runs/` (new).
- **Report:** docx via existing `docx.render_bytes`/`render_academic`.
- **Models:** OpenCode Go (flash → pro) for any live calls; `BP_ENABLE_DEEPSEEK` gates platform.deepseek.com only, not repair.
- **No new model providers.**

## 7. Ownership (do not violate)

- **Computation owner (DeepSeek)** owns: `src/bp/**`, `tests/**`, citation/RAG scoring rules, invariant logic, any new method or frozen-core touch.
- **Design owner (MiniMax)** owns: admin UI, report rendering, docx export, budget ledger, new backend routes/storage/workflows over frozen core.
- Cross-domain features split into computation commit then design commit, each with tests + CHANGELOG + WORKLOG.
- Beam (this planner) drafts spec/tasks only; does not write `src/bp/**` or tests.

## 8. Task breakdown (Step 3 — to be expanded)

Each task gets: acceptance criteria + allowed file list. Skeleton:

- **T1 (computation):** Add eval runner module skeleton + manifest schema under `state/eval_runs/`. Allowed: `src/bp/product/eval_runner.py` (new), tests.
- **T2 (computation):** Failure counter + trend tracking (per run, rolling). Allowed: `src/bp/product/eval_runner.py`, `ops_log` integration.
- **T3 (computation):** Direction 1 orchestration: run all 246 cases, aggregate, emit manifest. Allowed: `src/bp/product/eval_runner.py`.
- **T4 (computation):** Direction 2 rubric scorer (code-only, no model): sections, values, template-instruction scan, citation resolution to corpus page, background labelling, length band. Allowed: `src/bp/product/eval_rubric.py` (new), tests.
- **T5 (computation):** Direction 2 orchestration + budget knob + per-tile cost. Allowed: `src/bp/product/eval_runner.py`.
- **T6 (computation):** Direction 3 fault-injection harness (sandboxed copy of `qa/cases/`). Allowed: `src/bp/product/eval_faults.py` (new), tests.
- **T7 (computation):** Direction 3 cost/efficacy accounting (tokens, $, durability N=3, recurrence). Allowed: `src/bp/product/eval_runner.py`.
- **T8 (design):** Downloadable docx report renderer (owner-readable, aggregates 1–3). Allowed: `src/bp/product/eval_report.py` (new), docx renderer.
- **T9 (design):** Admin UI tab + controls (run, progress, download). Allowed: `web/admin-sbw.html`, backend routes.
- **T10 (design):** Backend routes: `GET/POST /api/ops/eval/*`. Allowed: `src/bp/server.py` (design lane, additive).

## 9. Verification (Step 5)

- Full suite green before and after (`python -m unittest discover -s tests`).
- `scripts/econ_shelf.py --check` still in sync if core touched.
- Agent opens admin in browser, checks security, simplifies code.
- Trap test for every bug fixed; no edited expected values.

## 10. How another model should pick this up

1. Read this file fully, then `HANDOFF.md` and `CONDUCTOR_MANUAL.md`.
2. Expand §8 into per-task acceptance criteria + allowed file lists (Step 3).
3. Build test-first (red → green, slice by slice), respecting ownership (§7).
4. Do not implement until owner switches to the appropriate agent/lane.
