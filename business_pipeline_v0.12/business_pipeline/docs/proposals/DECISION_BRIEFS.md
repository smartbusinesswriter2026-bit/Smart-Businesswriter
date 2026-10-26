DRAFT - prepared by OpenCode/MiniMax for owner review. Not a decision. Facts must be verified by the computation owner (DeepSeek) before use.

REVIEWED (computation owner, DeepSeek) - 2026-10-21, at master `5023aa4` (build 0.53). The draft was written against build 0.49 / commit `c06c61f`, before B-077, B-078, B-079 and B-080. **Spot-verification:** 55 cited `path:line` claims were re-checked; 37 were exact at master, 13 had shifted by under 30 lines and 5 had shifted materially because B-077 inserted a new section - the cited content was found in every case and no factual claim was contradicted. Line numbers are therefore **as of the drafting base (commit `c06c61f`)**; use the quoted text or section heading where a number has moved. **Contradictions re-checked:** #1, #2, #3, #4, #6 and #7 confirmed; #8 was confirmed and has since been **fixed** in the docs-guard work (build 0.53); #5 is a wording matter rather than a real contradiction (B-052 is deferred and deliberately kept on the gate list). The stale REW inventory reported in #2-#4 is queued for a REW manual inventory refresh by the computation owner. A12 is correct for the drafting base; the live test count is now guarded by `tests/test_docs_sync.py`. This file **remains a draft**: a review aid for the owner, not a decision, and it amends no existing document.

# Decision briefs - five open owner decisions (DRAFT)

**What this file is.** A review aid. Each brief restates, from the repository only, one decision that is currently open for the owner, what it blocks, what exists in code today, the options with their costs, and one clearly labelled recommendation.

**What this file is not.** Not authority, not a decision, and not a plan of record. It is written by the design owner (MiniMax), who owns presentation only ([`docs/CONTRIBUTORS.md` §1A](../CONTRIBUTORS.md), decision B-066 in `docs/DECISIONS.md`); computation, the factual content of the `docs/` directory, and every number remain the computation owner's (DeepSeek's) domain. Nothing here changes a number, claim ceiling, threshold, check, schema meaning or test. Every recommendation below is labelled **MiniMax recommendation** and must never be read as the computation owner's advice.

**Key documents** (all relative links resolve from this folder): [`docs/HANDOFF.md`](../HANDOFF.md) · [`docs/DECISIONS.md`](../DECISIONS.md) · [`docs/PRODUCT_GAP_MAP.md`](../PRODUCT_GAP_MAP.md) · [`docs/PARKED_QUEUE.md`](../PARKED_QUEUE.md) · [`docs/RESEARCH_EVIDENCE_WORKFLOW.md`](../RESEARCH_EVIDENCE_WORKFLOW.md) · [`docs/KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md) · [`docs/STAGE8_SPIKE_REPORT.md`](../STAGE8_SPIKE_REPORT.md) · [`docs/CONTRIBUTORS.md`](../CONTRIBUTORS.md) · [`docs/HOME.md`](../HOME.md) · [`README.md`](../../README.md) · [`docs/sources/business_pipeline_v0_3.md`](../sources/business_pipeline_v0_3.md) (read-only) · [`docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md`](../sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md) (read-only).

**Marker legend.**

- `OPEN - external, unverified` - a claim about something outside this repository (a tool's behaviour, a licence, a law, a standard) that this repository has never verified.
- `OPEN - could not verify in repo` - a statement this repository does not settle either way.

**How to read a brief.** "What it blocks today" cites `path:line` so the claim can be checked directly. "State of the code" names files and test names so the owner can see the evidence rather than take it on trust. "Rough size" is an estimate in files and test methods, not a commitment.

---

## Brief 1 - B-005: expert reviewers, and T2 to T1 promotion

### What the owner is asked to decide

Whether to name the expert reviewers (and the process that gates promotion) that the v0.3 manual requires, or to accept relabelling the three methods that currently carry the T1 label without a named reviewer - NPV, break-even and descriptive statistics - as T2 until a reviewer exists. These are the two answers the decision register itself offers at `docs/DECISIONS.md:9`.

### What it blocks today

- `docs/HANDOFF.md:51` - "| B-005 | Name expert reviewers, or accept T2 relabelling | Any T2->T1 promotion, breadth |".
- `docs/HANDOFF.md:75-76` - section 5.E, "Breadth (blocked on B-005/B-028)".
- `docs/PRODUCT_GAP_MAP.md:28` - decision dependencies: "Reviewers to promote T2->T1 (B-005)".
- `docs/PRODUCT_GAP_MAP.md:80` - breadth work "only after reviewers are named (B-005) and templates are chosen (B-028)".
- `docs/PARKED_QUEUE.md:29` - breadth templates "gated on B-028 (next templates) and B-005 (reviewers for any promotion)".
- `docs/sources/business_pipeline_v0_3.md:139` - "Library promotion. A T2 solution that passes human expert review MAY be promoted to T1. ... Promotion requires tests, documentation and a named reviewer. [DECIDED]".
- `docs/sources/business_pipeline_v0_3.md:562` - open question: "Names and process for the expert reviewers who gate T2 to T1 promotion. [OPEN]".

### State of the code

- `src/bp/methods.py:23` - the `Method` dataclass carries `review_status: str = "pending_named_reviewer"`, commented "T1 label stays, but review is disclosed (manual 5.3 promotion rule)".
- `src/bp/methods.py:3003` (`npv`), `src/bp/methods.py:3011` (`breakeven`), `src/bp/methods.py:3071` (`descriptive_stats`) - the three `LIBRARY` entries named in `docs/DECISIONS.md:9`, all at tier `"T1"`.
- `src/bp/session.py:31` - the tier label is derived from the tier and `review_status`: `"standard method; expert review pending"` while review is pending, `"custom analysis (T2); expert review pending"` for T2, `"standard method"` otherwise.
- `src/bp/orchestrator.py:313` - the delivery note branches on the same pending state ("Custom analysis (T2, expert review pending) ...").
- `src/bp/methods.py:2982` and `src/bp/methods.py:3000` - the `management_accounts` caveats ("this is custom analysis (T2), expert review pending" and "The ledger engine decision (custom kernel vs Beancount) is still open (B-032)").
- `src/bp/case_decision.py:207` - `case_decision` is T2 with "expert review pending" in its limitations.
- `src/bp/claims.py:4` - the claim ceiling is keyed on the ceiling type, not on the tier; the tier and the label text are what carry the pending-review disclosure.
- Evidence in tests: `tests/test_stage5.py:34` `test_t1_label_discloses_pending_review` asserts `"review pending"` is in the plan label; `tests/test_accounts.py:74` asserts `"expert review pending"` in the delivered report; `tests/test_case_decision.py:80` asserts the exact pair `("T2", "custom analysis (T2); expert review pending")`.
- The three named methods are verified independently of the review question: `tests/test_pipeline.py:33` `test_npv_known_value` and `tests/test_pipeline.py:48` `test_breakeven` (analytic checks), and `tests/test_stage5.py:16` `test_golden_set` against `tests/fixtures/descriptive_golden.json`.

### Options

**Option A - name the expert reviewers and the promotion process.**

- Trade-offs: this is the only option that satisfies `docs/sources/business_pipeline_v0_3.md:139` as written and it unblocks both promotion and the breadth track (`docs/PRODUCT_GAP_MAP.md:80`). It requires a real person, role or panel, which only the owner can supply; nothing in the repository can stand in for it.
- What would have to change: a decision row in `docs/DECISIONS.md`; `review_status` and `tier` on the promoted `Method` entries in `src/bp/methods.py`; the label branches in `src/bp/session.py:31` and the note in `src/bp/orchestrator.py:313`; the caveat strings in `src/bp/methods.py:2982`, `src/bp/methods.py:3000` and `src/bp/case_decision.py:207`; the documentation set (`docs/HOME.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/KNOWN_LIMITATIONS.md`).
- Rough size (estimate): 1 decision row + 1-3 `Method` entries + 2 label/note sites + 4-8 test methods.

**Option B - accept T2 relabelling for NPV, break-even and descriptive statistics.**

- Trade-offs: it is the honest reading of the manual's own tier table (`docs/sources/business_pipeline_v0_3.md:130-133`), where T2 is "Bespoke code ... Heavier verification ... 'custom analysis'". The cost is that three widely used methods lose the "standard method" label and their delivery wording changes; no reviewer is needed at all.
- What would have to change: the `tier` field on `src/bp/methods.py:3003`, `:3011` and `:3071`; the label branches in `src/bp/session.py:31`; the delivery note in `src/bp/orchestrator.py:313`; any test asserting tier labels (`tests/test_stage5.py:34`, `tests/test_case_decision.py:80`); the documentation set.
- Rough size (estimate): 3 `Method` entries + 2-3 label/note sites + 4-8 test methods.

**Option C - keep the current state: T1 with the disclosed "expert review pending".**

- Trade-offs: no rework, no reviewer cost, and the compromise is disclosed in the product output rather than hidden. The cost is that promotion and breadth stay blocked, and the tier label rests on a promise the repository cannot keep on its own.
- What would have to change: nothing. The disclosure already ships (`src/bp/session.py:31`).
- Rough size (estimate): 0 files, 0 tests.

**Option D - name reviewers, but promote method by method, keeping the current labels until each method has actually been reviewed.**

- Trade-offs: it unblocks the breadth track without relabelling three methods whose verification is already in place, and it matches the manual's wording ("A T2 solution that passes human expert review MAY be promoted"), which makes promotion a per-method event. The cost is that it needs a review status that does not exist in the code today, and reviewer capacity.
- What would have to change: a second `review_status` value and its label branch in `src/bp/session.py:31`; the `review_status` field on the reviewed `Method` entries; a decision row; the documentation set.
- Rough size (estimate): 1-3 `Method` entries + 1 label branch + 2-5 test methods.

### Recommendation

**MiniMax recommendation: Option D** - name the reviewer and the promotion process, and promote method by method, keeping the current labels until each method has been reviewed. It is the only option that satisfies `docs/sources/business_pipeline_v0_3.md:139` without relabelling three already-verified methods, and it unblocks the breadth track, which is the reason the decision is on the gate list (`docs/HANDOFF.md:51`, `docs/PRODUCT_GAP_MAP.md:80`). This recommendation is a presentation-side judgement about sequencing only; the reviewer, the process and any tier change are the owner's and the computation owner's calls, and no reviewer is named here.

### Needed from the owner

Do you name an expert reviewer (name or role) and the T2-to-T1 promotion process now, or do you instruct that NPV, break-even and descriptive statistics be relabelled T2 until a reviewer exists?

---

## Brief 2 - B-028: which framework templates come next

### What the owner is asked to decide

Which of the five candidate templates comes next - PESTEL, VRIO, Porter's Value Chain, Business Model Canvas or MCDA - and for MCDA specifically, whether it is a structure-only evidence template or a template that computes with user-owned weights. The candidate list and the "do not merge them" constraint are both in `docs/DECISIONS.md:32`.

### What it blocks today

- `docs/HANDOFF.md:52` - "| B-028 | Pick next framework templates (PESTEL, VRIO, Value Chain, BMC, MCDA) | P2 breadth |".
- `docs/HANDOFF.md:75-76` - section 5.E, breadth blocked on B-005/B-028.
- `docs/PRODUCT_GAP_MAP.md:56` - "The open decision on which templates come next is B-028 (PESTEL, VRIO, Value Chain, BMC, MCDA)"; the same section lists the marketing, operations, risk and people candidates that are "registry only today".
- `docs/PRODUCT_GAP_MAP.md:85` - "Pick the next framework templates (B-028) for section D".
- `docs/PARKED_QUEUE.md:29` - breadth templates gated on B-028 and B-005.
- `docs/DECISIONS.md:32` - the open decision row itself.

### State of the code

- `src/bp/templates.py` holds exactly two templates, both structure-only T4: `src/bp/templates.py:194` (`template_swot`, registry ids `STR-07`, `STR-18`) and `src/bp/templates.py:205` (`template_five_forces`, registry id `STR-01`). Each entry carries `id`, `version`, `name`, `registry_ids`, `build`, `render` and `tests`.
- The build functions return the registry ids and an audit (`src/bp/templates.py:103`, `src/bp/templates.py:116`); nothing in them computes a score.
- `src/bp/data/registry_v0_2.json` is the imported catalogue with 140 records (61 framework, 22 operational model, 50 quantitative method, 7 theory cluster), including `STR-03` Porter's Value Chain, `STR-06` PESTEL, `STR-08` VRIO, `STR-15` Business Model Canvas and `RSK-09` Multi-Criteria Decision Analysis. `src/bp/catalogue_import.py` and `src/bp/registry.py` are the import and lookup path.
- Catalogue entries, as written: `docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md:55` (PESTEL - "Dated, cited external evidence"), `:52` (Value Chain - "Activity costs, margin/cost drivers"), `:57` (VRIO - "avoid unsupported yes/no scoring"), `:64` (Business Model Canvas - "Customer evidence, revenue logic, cost estimates, and consistency across blocks"), `:148` (MCDA - "Score definitions, weights, normalization, sensitivity analysis and user-owned value judgments"). `:69` states that Porter's frameworks "should be kept as separate entries ... SWOT, Five Forces, and the Value Chain should not be merged into one generic 'strategy analysis'"; `:150` adds that "A risk matrix or MCDA score must not turn subjective estimates into false precision".
- The template tier rules: `docs/DECISIONS.md:31` (B-027 - templates are tier T4, user-evidence only; "the catalogue defines no scales") and `docs/sources/business_pipeline_v0_3.md:133` (T4 is "Framework only ... No computed answer is given").
- Evidence in tests: `tests/test_templates.py` holds 20 test methods, for example `test_swot_intake_errors_are_actionable` (`:27`), `test_five_forces_statuses` (`:51`), `test_gaps_assumptions_and_materiality_are_reported_not_filled` (`:63`), `test_sourced_items_show_their_source` (`:66`), `test_swot_defects_are_blocked` (`:91`), `test_five_forces_defects_are_blocked` (`:103`), `test_sandbox_result_equals_in_process` (`:115`), `test_pipeline_with_sandbox_matches_and_reperforms` (`:118`), `test_registry_links` (`:124`), `test_http` (`:131`).

### Options

**Option A - build one structure-only template next, and the owner names which one.**

- Trade-offs: the smallest increment that follows the existing pattern exactly; it organises the owner's evidence and computes nothing, which is exactly what T4 means. The cost is that the owner gets one framework at a time and the breadth queue in `docs/PRODUCT_GAP_MAP.md:58-61` stays long.
- What would have to change: one entry in the `TEMPLATES` mapping in `src/bp/templates.py` with its build, render and test triple and its `registry_ids`; a new decision id for the conventions; the documentation set.
- Rough size (estimate): 1 source file + 1 test file, 8-15 test methods, plus 4 documentation files.

**Option B - MCDA only, as a structure-only evidence template.**

- Trade-offs: MCDA is the candidate whose catalogue entry asks for weights, normalisation and sensitivity (`:148`) and whose guardrail forbids false precision (`:150`). A structure-only MCDA can organise criteria, weights and scores as user evidence without producing a number - which is safe - but it will disappoint anyone expecting a comparison, because no ranking is computed.
- What would have to change: as Option A, plus an explicit "no score is computed here" caveat in the template's limitations and its claim ceiling.
- Rough size (estimate): as Option A.

**Option C - MCDA as a scoring template with user-owned weights (a computation, not a template).**

- Trade-offs: this is the version that matches the catalogue's intent, but it is no longer T4 and no longer structure-only: it produces a number, so it needs a method contract, an independent second route, a claim ceiling, a frozen check set and a claim about what the score may say. It also inherits B-005, because a number without a named reviewer cannot be labelled T1 (`docs/sources/business_pipeline_v0_3.md:139`). It should not start before B-005 is answered.
- What would have to change: a new method in `src/bp/methods.py` or a new module, a `LIBRARY` entry with the full contract, a ceiling entry in `src/bp/claims.py`, offline goldens, a sandbox case, a workbench preset, and the documentation set.
- Rough size (estimate): 1-2 source files + 1-2 test files, 15-25 test methods, plus 5 documentation files.

**Option D - defer breadth until B-005 is answered.**

- Trade-offs: nothing is built and nothing is risk-free; it keeps the current sequencing rationale at `docs/PRODUCT_GAP_MAP.md:80` ("breadth only after reviewers are named and templates are chosen") intact.
- What would have to change: nothing.
- Rough size (estimate): 0 files, 0 tests.

### Recommendation

**MiniMax recommendation: Option A, one structure-only template chosen by the owner, with Option B's caveat pattern if MCDA is picked.** It is the increment that matches the existing template machinery and the T4 definition without producing numbers, so it does not wait on B-005; Option C should stay blocked until B-005 is answered, because a scored MCDA produces a number that would then have no named reviewer. Whether a single template or a small batch is right is the owner's call; this is a sequencing judgement about risk, not a claim that one framework matters more than another.

### Needed from the owner

Which single template do you want next - PESTEL (`STR-06`), VRIO (`STR-08`), Porter's Value Chain (`STR-03`), Business Model Canvas (`STR-15`) or MCDA (`RSK-09`) - and is MCDA structure-only or a scoring template with user-owned weights?

---

## Brief 3 - B-032: the ledger engine - custom kernel or Beancount

### What the owner is asked to decide

Whether the custom ledger kernel becomes the ledger of record for management accounts v1 now, with the manual's two-arm comparison recorded as incomplete, or whether the Beancount arm of the spike is run first and the decision is made from the results. The manual requires the spike before the decision (`docs/sources/business_pipeline_v0_3.md:275-289`).

### What it blocks today

- `docs/HANDOFF.md:53` - "| B-032 | Ledger engine: custom kernel vs Beancount arm | Accounting tier, tax/valuation |".
- `docs/HANDOFF.md:40` - Stage 8 accounting is T2 and "Ledger engine choice open (B-032)".
- `docs/HANDOFF.md:81-82` - section 5.G, "Stage 8 remainder (blocked on B-032)".
- `docs/PRODUCT_GAP_MAP.md:86` - "Decide the ledger engine (B-032) before tax/valuation sit on the ledger for real".
- `docs/DECISIONS.md:36` - the open row: "Custom arm of the spike run; Beancount arm not run".
- `docs/DECISIONS.md:49` - B-044: "Stage 8 continues on the custom kernel (B-032 stays OPEN pending the Beancount arm)".
- `docs/KNOWN_LIMITATIONS.md:69` - "Beancount was not evaluated; the manual's statements about it are unverified."
- `docs/STAGE8_SPIKE_REPORT.md:2` - "Only the custom-kernel arm was run. The Beancount arm was NOT run ... The comparison the manual requires is therefore incomplete, and the engine decision stays OPEN."

### State of the code

- `src/bp/ledger.py` is the custom kernel, 295 lines: `Account` (`:20`), `Chart` (`:32`), `Entry` (`:55`), `Journal` (`:75`), `trial_balance` (`:106`), `statements` (`:118`), `cash_flow` (`:142`, the two routes), `closing_entries` (`:174`), `retained_earnings_rollforward` (`:200`), `closing_balances` (`:231`), `opening_lines` (`:235`), `check_invariants` (`:246`), `flags` (`:275`), `require_framework` (`:293`).
- `spike/trap_cases.py` holds 12 neutral trap cases designed so that "any arm (custom kernel, Beancount, ...) can run them": `clean_baseline`, `unbalanced_entry`, `float_amount`, `silent_rounding`, `unknown_account`, `date_outside_period`, `flipped_sign_expense`, `misclassified_contra`, `missing_accrual`, `opening_not_prior_closing`, `tampered_journal`, `mid_year_policy_change`. `spike/run_custom_arm.py:24` runs them against the custom kernel. There is no Beancount arm script in the repository.
- `tests/test_ledger.py` holds 22 test methods, for example `test_unbalanced_and_malformed_entries_cannot_be_built` (`:21`), `test_hash_chain_detects_edits_and_reordering` (`:48`), `test_each_invariant_fails_when_its_target_is_corrupted` (`:68`), `test_custom_arm_results_match_expectations` (`:123`).
- The layers above the kernel are built and tested: `src/bp/schedules.py` (`tests/test_schedules.py`), `src/bp/accounts.py` (the declarative engagement and `management_accounts`; `tests/test_accounts.py`, 21 methods), `src/bp/reconcile.py` (`tests/test_reconcile.py`), `src/bp/report.py` (`tests/test_report.py`), plus `tests/test_cashflow.py` and `tests/test_closing.py` for the two-route cash flow and closing.
- The accounting method is T2 with the engine caveat at `src/bp/methods.py:2982` and `src/bp/methods.py:3000`, and it is reached through `src/bp/methods.py:3376`.
- The manual's Beancount findings are marked unverified in the manual itself (`docs/sources/business_pipeline_v0_3.md:281` "Decimal amounts [UNVERIFIED]"; `:283` gaps "[UNVERIFIED unless noted]"; `:279` licensing "GPLv2-only"; `:285` "Obtain legal review before any on-prem or embedded distribution"). `docs/STAGE8_SPIKE_REPORT.md:23` repeats that these remain unverified and that the GPLv2 question needs legal review. Beancount's features, licence terms and ecosystem are therefore `OPEN - external, unverified` - this repository has never run it.
- The spike report already records the protocol for the missing arm (`docs/STAGE8_SPIKE_REPORT.md:23`): install Beancount 3 in a normal environment, feed each case in `spike/trap_cases.py` through its data structures (not generated text, per manual 9.2), record whether each case is rejected, flagged, caught by a check or missed, count the glue code, export the same journal and judge readability with an accountant.

### Options

**Option A - run the Beancount arm, then decide from the results.**

- Trade-offs: it is the procedure the manual specifies (`docs/sources/business_pipeline_v0_3.md:289`: compare the number caught by construction, glue code required, and accountant readability). It needs an environment with Beancount 3 installed and network access; neither is available here (`docs/STAGE8_SPIKE_REPORT.md:2`). It also brings a licence question into the decision (`docs/sources/business_pipeline_v0_3.md:285`) that is `OPEN - external, unverified` and needs legal review.
- What would have to change: a new spike script alongside `spike/run_custom_arm.py`, a results section in `docs/STAGE8_SPIKE_REPORT.md`, and then a decision row in `docs/DECISIONS.md`. No change under `src/bp/` is needed until the decision is made.
- Rough size (estimate): 1 new script + 1 document + 0-2 test methods (the spike harness lives outside the unittest suite today).

**Option B - decide "custom kernel" now and record that the comparison was incomplete.**

- Trade-offs: it unblocks the accounting tier and the tax/valuation track that sits on the ledger (`docs/PRODUCT_GAP_MAP.md:86`) and stops the engine question from gating further accounting increments. The cost is that the manual's comparison is never made, and `docs/STAGE8_SPIKE_REPORT.md:26` says "Record the decision only after the Beancount arm has been run" - so this option contradicts the repository's own guidance (see Appendix B).
- What would have to change: one decision row in `docs/DECISIONS.md`; the caveat strings at `src/bp/methods.py:3000` (and possibly `:2982`); `docs/KNOWN_LIMITATIONS.md:69`; `docs/HANDOFF.md` sections 4 and 5; `docs/CHANGELOG.md` and `docs/WORKLOG.md`.
- Rough size (estimate): 2 source strings + 4 documents + 2-6 test methods (anything asserting the caveat text, for example `tests/test_accounts.py:74`).

**Option C - keep B-032 open and keep building on the custom kernel as a declared provisional.**

- Trade-offs: no rework risk and no premature decision; the cost is that every accounting increment is built on an engine that could still be replaced, and `management_accounts` stays T2 ("custom analysis (T2), expert review pending", `src/bp/methods.py:2982`), which keeps `docs/DECISIONS.md:52` (B-047) provisional.
- What would have to change: nothing.
- Rough size (estimate): 0 files, 0 tests.

**Option D - take the engine decision together with the framework and jurisdiction question.**

- Trade-offs: one owner conversation instead of two, and the manual itself couples them (`docs/sources/business_pipeline_v0_3.md:556`: "Which frameworks and jurisdictions are in scope for version 1? Initial proposal: management accounts, three statements, five or six schedule types, one framework. [PROPOSIONAL]"; and `:554` lists the ledger engine choice as an open question). The risk is coupling an engine choice to a framework and jurisdiction choice that also needs source decisions the owner has not made.
- What would have to change: as Option B, plus one further decision row for the framework/jurisdiction scope.
- Rough size (estimate): as Option B, plus 1-2 decisions.

### Recommendation

**MiniMax recommendation: Option C** - keep B-032 open and keep building on the custom kernel as a declared provisional, until the Beancount arm has been run. The comparative data is the point of the decision (`docs/sources/business_pipeline_v0_3.md:289`), the repository's own spike guidance asks for exactly that ordering (`docs/STAGE8_SPIKE_REPORT.md:26`), and the cost of waiting is a T2 label rather than a rewrite. This is a sequencing judgement; the engine choice and any licence review remain the owner's and the computation owner's calls.

### Needed from the owner

Should the Beancount spike arm be run in an environment that has Beancount 3 installed before B-032 is recorded, or do you instruct the decision now with the comparison marked incomplete?

---

## Brief 4 - B-052: taxation scope

### What the owner is asked to decide

Whether taxation stays deferred (its state today, `docs/DECISIONS.md:57`), or which of the four senses that decision names - VAT/GST on transactions, income tax in the accounts, after-tax cash flows and the depreciation tax shield in appraisal, and tax filing - is resumed, and for which declared jurisdiction. Any resumption also needs the source and licensing decision described in `docs/HANDOFF.md:64-65`, and the owner's answer has to carry a jurisdiction that this repository does not know.

### What it blocks today

- `docs/HANDOFF.md:54` - "| B-052 | Taxation deferred; do not build without resuming the decision | Tax work |".
- `docs/HANDOFF.md:64-65` - section 5.B, standards / filings / tax retrieval "blocked on an owner source decision", with tax listed as deferred.
- `docs/HANDOFF.md:81-82` - section 5.G, "tax once resumed".
- `docs/DECISIONS.md:57` - the deferred decision, with the four senses and the resume conditions: a declared jurisdiction, user-supplied or retrieved-and-cited rates (never invented), expert review, and the "outputs to tax authorities" risk answer.
- `docs/KNOWN_LIMITATIONS.md:247` - "Taxation (B-052): out of scope - the pipeline can hold tax balances (accounts + declared entries) but computes no VAT/GST, income tax, deferred tax, capital allowances or tax-aware appraisal, and does not file."
- `docs/KNOWN_LIMITATIONS.md:200` - the standards, company-filing and tax source families are still not implemented.
- `docs/PARKED_QUEUE.md:27` - "Standards / filings / tax retrieval - needs the owner to name sources, jurisdictions and licensing (B-052 deferred)."
- `docs/PRODUCT_GAP_MAP.md:26` - the retrieval layer "unblocks framework citation, tax (B-052), the research workflow (REW), and valuation multiples".
- Manual: `docs/sources/business_pipeline_v0_3.md:31` - non-goal, "It does not file taxes"; `:520` - "Standards drift: accounting standards and tax rules change after any model's training. Retrieval is mandatory."

### State of the code

- No tax number is computed anywhere in the method library. The declared "no tax" statements are in `src/bp/methods.py:1518` (ratio analysis input: "no tax computation is performed"), `:2523` (`wacc`: "no tax is computed by this method"), `:2597` (`dcf_valuation`: "No tax is computed: supply after-tax cash flows"), `:3123` (`ratio_analysis` limitation), `:1969` and `:3227` (appraisal), `:2165` and `:3269` (`unit_economics`), `:2247` and `:3283` (`multi_product_breakeven`), `:3319` (`currency_convert` unsupported use).
- After-tax figures are already user-declared inputs, not computations: `src/bp/methods.py:2479` and `:2486` require `cost_of_debt_after_tax`, and `tests/test_valuation.py:8` supplies it in the WACC fixture.
- Tax *balances* are already representable, because the ledger is account-driven: `src/bp/ledger.py:20` (`Account`) and `src/bp/ledger.py:32` (`Chart`), with entries posted through `src/bp/ledger.py:55` and `src/bp/ledger.py:75`.
- Evidence in tests that the "no tax computed" position is enforced in the output: `tests/test_valuation.py` (11 methods, including `test_frozen_checks_pass_and_are_declared` at `:31` and `:65`), `tests/test_appraisal.py` (11 methods), `tests/test_ratio.py` (15 methods), `tests/test_accounts.py` (21 methods).
- What does not exist and cannot be verified here: any tax rule, rate, treatment or jurisdiction. Every such item is `OPEN - external, unverified`; the repository also has no retrieval source family for tax (`docs/KNOWN_LIMITATIONS.md:200`).

### Options

**Option A - keep taxation deferred.**

- Trade-offs: no work, no exposure to an unverifiable rule, and the repository's current honesty statements stay accurate. The cost is that anything wanting after-tax or tax-inclusive numbers must compute them outside the system, and the tax track stays on the gate list (`docs/HANDOFF.md:54`).
- What would have to change: nothing; `docs/KNOWN_LIMITATIONS.md:247` already states the position.
- Rough size (estimate): 0 files, 0 tests.

**Option B - resume only sense (c): after-tax cash flows and the depreciation tax shield in appraisal, with every rate user-declared or retrieved-and-cited.**

- Trade-offs: the smallest slice that adds no unverifiable arithmetic, because the methods already accept after-tax inputs and compute no tax (`src/bp/methods.py:2523`, `:2597`). The cost is that it still needs a declared jurisdiction and a cited rate source (`docs/DECISIONS.md:57`), and it adds no computation, so the deliverable is a declared-input discipline plus disclosure.
- What would have to change: the caveat and limitation strings on the appraisal and valuation methods in `src/bp/methods.py`; possibly a new declared input or an explicit "no tax computed" statement in the appendix; a new decision id; `docs/KNOWN_LIMITATIONS.md`; the documentation set.
- Rough size (estimate): 1 source file (caveats and inputs) + 1 test file, 4-8 test methods, plus 4 documentation files.

**Option C - resume sense (b): income tax as balances and expense in the accounts.**

- Trade-offs: the most useful for a bookkeeping workflow, but it needs jurisdiction-specific treatment and a source decision the owner has not made (`docs/HANDOFF.md:65`, `docs/PARKED_QUEUE.md:27`), it keeps `management_accounts` at T2 (`src/bp/methods.py:2982`), and it depends on the ledger-engine question (B-032) because tax balances live in the chart of accounts.
- What would have to change: chart and spec handling in `src/bp/accounts.py` and `src/bp/schedules.py`; a method or schedule for the tax treatment if any is computed at all; `src/bp/methods.py` caveats; the documentation set.
- Rough size (estimate): 2 source files + 1-2 test files, 10-20 test methods, plus 5 documentation files.

**Option D - resume sense (a) VAT/GST or sense (d) filing.**

- Trade-offs: these are the senses the manual's non-goal names directly (`docs/sources/business_pipeline_v0_3.md:31`), so resuming either needs a manual-level amendment and a jurisdiction answer, and (d) additionally needs the "outputs to tax authorities" risk answer that `docs/DECISIONS.md:57` lists and that `docs/sources/business_pipeline_v0_3.md:550` leaves open. Highest risk and highest cost.
- What would have to change: an amendment to the manual's non-goals, an owner instruction to change the product's scope, a jurisdiction and rate source, and a new source family in `src/bp/literature.py`; the documentation set.
- Rough size (estimate): 2-3 source files + 2 test files, 20+ test methods, plus 6 documentation files, and a manual amendment.

### Recommendation

**MiniMax recommendation: Option A now, with the "sense" recorded when the owner names a jurisdiction and a source.** The four senses are not equally sized: (a) and (d) contradict a non-goal the manual states, and (c) needs an external rate source that does not exist in the repository yet (`docs/KNOWN_LIMITATIONS.md:200`). If the owner wants visible progress before that, Option B is the only slice that adds no unverifiable external rule. This recommendation is about scope hygiene, not a view on tax policy.

### Needed from the owner

Which of the four senses in B-052 do you want resumed - (a) VAT/GST on transactions, (b) income tax in the accounts, (c) after-tax cash flows in appraisal, or (d) tax filing - and for which jurisdiction, or do you confirm that taxation stays deferred?

---

## Brief 5 - REW R1-R10 ratification

### What the owner is asked to decide

Whether to ratify the proposed research-workflow stage list, checkpoints and taxonomy (register rows R1-R10 in `docs/RESEARCH_EVIDENCE_WORKFLOW.md:170-179`) as written, in slices, or not at all. R11 - the manual's own authority as the working reference - is already ratified and B-053 is closed (`docs/DECISIONS.md:58`), so the open question is only about R1-R10.

### What it blocks today

- `docs/HANDOFF.md:55` - "| REW R1-R10 | Ratify (or not) the proposed stages/checkpoints/taxonomy | Any REW stage build |".
- `docs/HANDOFF.md:72-73` - section 5.D, "REW stages (blocked until R1-R10 ratified)"; the cheapest first slice is named: "R0 intake -> R1 literature search with the existing retrieval + screening log -> R2 gap statement. Acceptance includes the stage contracts in the manual."
- `docs/PARKED_QUEUE.md:30` - "REW stages R0-R8 - gated on ratifying R1-R10."
- `docs/RESEARCH_EVIDENCE_WORKFLOW.md:50` - "All of section 5 is [PROPOSAL]."
- `docs/RESEARCH_EVIDENCE_WORKFLOW.md:166` - "Each item needs the owner's yes/no; ratifying edits the tag in this file and logs it ... The rest remain proposals; a proposal is not binding merely because the manual is authoritative."
- `docs/RESEARCH_EVIDENCE_WORKFLOW.md:170-179` - the register rows R1-R10, each PROPOSAL.
- `docs/KNOWN_LIMITATIONS.md:70` - "the research workflow ... has a ratified living manual but no built stages".
- `docs/PRODUCT_GAP_MAP.md:75` - recommended order item 1 is to ratify R1-R10 first.

### State of the code

- No research stage is wired into the pipeline. `docs/RESEARCH_EVIDENCE_WORKFLOW.md:156` lists "Stage list, checkpoints, research spec, screening log, study spec" as "Not built", and `:162` states "No REW stage is wired into the pipeline."
- The building blocks the stages would use exist and are tested: `src/bp/literature.py` (`tests/test_literature.py`, `tests/test_literature_api.py`, `tests/test_literature_log.py`), `src/bp/quantity.py` (typed provenance), `src/bp/claims.py` (claim ceilings), `src/bp/methods.py` (the verified statistics), `src/bp/templates.py` (structure-only templates), `src/bp/sandbox.py` with `src/bp/reperform.py` and `src/bp/orchestrator.py` (sandbox, re-performance, run log), and the pause/resume contract in `src/bp/session.py` that the manual proposes reusing for R0 (`docs/RESEARCH_EVIDENCE_WORKFLOW.md:54`).
- The retrieval rules the manual's section 9 and Q10 refer to are already implemented: `docs/DECISIONS.md:59` (B-054, response SHA-256 and UTC time), `:63` (B-058, durable append-only log with fail-closed writes and reverify), `:64` (B-059, APA 7 and Harvard), `:69` (B-064, source priority, failover, drift sweep).
- The register itself flags what should not be ratified blindly: `:172` (R3, "PROPOSAL (names are second-hand)"), `:170` (R1, "PROPOSAL - do not build stages as if frozen"), `:178` (R9, "PROPOSAL - charter wording is binding; the paper-specific additions are not").
- The preserved open questions still gate parts of the register: `docs/RESEARCH_EVIDENCE_WORKFLOW.md:188` (Q1 blocks R1), `:195` (Q8 blocks R0 and R7 - whether "papers" means academic papers, business reports or both), `:196` (Q9 - the match threshold remains open), `:200` (Q13 - "Which research-gap path to build first (T-A is the cheapest real end-to-end slice)?").
- The manual is explicit about provenance: `docs/RESEARCH_EVIDENCE_WORKFLOW.md:9` - "Is not: a recovered copy of the Smart Researcher research-pipeline manuals. Those were never supplied."

### Options

**Option A - ratify R1-R10 as written.**

- Trade-offs: one step turns proposals into a build specification, which is what `docs/PRODUCT_GAP_MAP.md:75` recommends. The cost is that it commits to a stage list, three checkpoints and a study taxonomy whose original manuals were never supplied (`docs/RESEARCH_EVIDENCE_WORKFLOW.md:9`), and some register entries are explicitly second-hand (`:172`) or already known to be blocked by an unanswered question (`:195`, Q8 blocks R0 and R7).
- What would have to change: the provenance tags in `docs/RESEARCH_EVIDENCE_WORKFLOW.md` sections 5 and 14, the change log at `:202` and a decision row in `docs/DECISIONS.md`; then each stage becomes its own slice.
- Rough size (estimate): 2 document files + 1 decision row for the ratification itself, then the stage slices (roughly 1 module and 1 test file per stage, estimate).

**Option B - ratify in slices: R1 (stage list), R2 (three checkpoints) and R6 (freeze-before-compute) first.**

- Trade-offs: the smallest ratified surface that still unlocks the first slice the handoff already names - "R0 intake -> R1 literature search ... -> R2 gap statement" (`docs/HANDOFF.md:73`) - and it avoids ratifying entries the manual itself marks as second-hand or blocked (`:172`, `:195`). The cost is that R3-R5 and R7-R10 stay proposals, so later stages may need a second ratification, and the decision is split across two owner conversations.
- What would have to change: three tag edits plus the change log in `docs/RESEARCH_EVIDENCE_WORKFLOW.md`, one decision row in `docs/DECISIONS.md`, `docs/CHANGELOG.md` and `docs/WORKLOG.md`; then the R0-R2 slice itself (stage contracts, a research spec, a screening log, a gap statement).
- Rough size (estimate): 1 document file + 1 decision row + 3 log entries for the ratification, then roughly 1 new module and 1 new test file with 15-25 test methods for the R0-R2 slice (estimate).

**Option C - do not ratify; keep R1-R10 as proposals and build only the non-stage pieces.**

- Trade-offs: retrieval, ingestion and disclosure work can continue without committing to a stage contract, and nothing is ratified that the owner has not read. The cost is that no REW stage can be built at all (`docs/HANDOFF.md:55`), the first item of the gap map's recommended order stays blocked (`docs/PRODUCT_GAP_MAP.md:75`), and the manual remains a proposal set.
- What would have to change: nothing.
- Rough size (estimate): 0 files, 0 tests.

**Option D - supply the original Smart Researcher research-pipeline manuals and reconcile the living manual against them.**

- Trade-offs: it resolves the provenance gap at the root, which is what the register's open question Q1 asks for (`docs/RESEARCH_EVIDENCE_WORKFLOW.md:188`). The cost is that the manuals were never supplied (`:9`) and the Build Charter forbids reconstructing them, so this depends on the owner producing documents; the reconciliation would then be a revision pass over the manual rather than a ratification.
- What would have to change: owner action, then a reconciliation pass over `docs/RESEARCH_EVIDENCE_WORKFLOW.md` and the register rows.
- Rough size (estimate): owner action + 1-2 document files.

### Recommendation

**MiniMax recommendation: Option B** - ratify R1, R2 and R6 only. Those three enable the slice the handoff already names at `docs/HANDOFF.md:73`, and they leave untouched the register entries that the manual itself marks as second-hand (`:172`) or as blocked by an unanswered question (`:195`). Ratifying everything at once (Option A) would commit the owner to taxonomy detail whose source was never supplied. This is a sequencing judgement about how much to ratify at once; the ratification itself is the owner's.

### Needed from the owner

Do you ratify R1, R2 and R6 (stage list, three checkpoints, freeze-before-compute) so that the R0-to-R2 slice can be built, ratify R1-R10 as written, or keep them as proposals?

---

## Appendix A - OPEN items in these briefs

| # | Item | Where | Marker |
|---|---|---|---|
| A1 | Beancount's features, licence terms (GPLv2), plugin system, Decimal amounts, ecosystem and accountant readability | `docs/sources/business_pipeline_v0_3.md:279-285`, `docs/STAGE8_SPIKE_REPORT.md:23`, `docs/KNOWN_LIMITATIONS.md:69` | `OPEN - external, unverified` - never run in this repository |
| A2 | Whether the Beancount arm would catch more or fewer of the 12 trap cases than the custom kernel | `spike/trap_cases.py`, `docs/sources/business_pipeline_v0_3.md:289` | `OPEN - could not verify in repo` - the arm has not been run |
| A3 | Legal review of the GPLv2 question before any distribution | `docs/sources/business_pipeline_v0_3.md:285`, `docs/STAGE8_SPIKE_REPORT.md:23` | `OPEN - external, unverified` - needs counsel, not code |
| A4 | Which tax jurisdiction, rates and treatments apply, and whether outputs ever go to tax authorities | `docs/DECISIONS.md:57`, `docs/sources/business_pipeline_v0_3.md:550` | `OPEN - external, unverified` / `OPEN - could not verify in repo` |
| A5 | Which accounting standards and filing sources are in scope, and whether retrieval of them is licensed | `docs/HANDOFF.md:64-65`, `docs/PARKED_QUEUE.md:27` | `OPEN - external, unverified` - owner must name sources |
| A6 | Whether any expert reviewer exists, and who | `docs/DECISIONS.md:9`, `docs/sources/business_pipeline_v0_3.md:562` | `OPEN - could not verify in repo` - no reviewer is named anywhere in the repository, and none is named in this file |
| A7 | The original Smart Researcher research-pipeline manuals (stage list, tier names, taxonomy, instruments) | `docs/RESEARCH_EVIDENCE_WORKFLOW.md:9`, `:188`, `:200` | `OPEN - could not verify in repo` - never supplied |
| A8 | Whether "papers" means academic papers, business reports or both, and the institution AI-use requirements | `docs/RESEARCH_EVIDENCE_WORKFLOW.md:195`, `:199` | `OPEN - could not verify in repo` - owner question Q8 / Q12 |
| A9 | Which frameworks and jurisdictions are in scope for version 1 | `docs/sources/business_pipeline_v0_3.md:556` | `OPEN - could not verify in repo` - marked PROPOSIONAL in the manual |
| A10 | Whether the applicable privacy law for user data (the manual names one jurisdiction's privacy act, marked unverified) constrains the workspace | `docs/sources/business_pipeline_v0_3.md:526` | `OPEN - external, unverified` - counsel review required |
| A11 | The catalogue's own evidence needs and guardrails for MCDA (weights, normalisation, sensitivity) - whether a structure-only template satisfies the owner's intent | `docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md:148`, `:150` | `OPEN - could not verify in repo` - no MCDA template exists to compare against |
| A12 | Whether the test count quoted in the repository docs still matches the code (it read 598 at the drafting base, build 0.49) | `docs/HANDOFF.md:12`, `docs/HOME.md:3`, `docs/CONTRIBUTORS.md:51` | **Resolved by review**: 598 was correct at the drafting base; the live count is now guarded by `tests/test_docs_sync.py`, so this cannot silently drift again |

## Appendix B - contradictions found between repository documents (reported, not fixed)

These are reported only. Nothing in this file changes any existing document.

1. **Two B-031 rows with different statuses.** `docs/DECISIONS.md:35` reads "| B-031 | OPEN (owner) | Introduce a model provider ... |" and `docs/DECISIONS.md:40` reads "| B-031 | RESOLVED 2026-10-21 | Owner approved introducing a model provider ... |". A reader scanning for status gets two answers for the same id.
2. **The REW manual's own inventory is stale about the retrieval log.** `docs/RESEARCH_EVIDENCE_WORKFLOW.md:150` says "no durable log yet", while the same file's Q10 row (`:197`) and `docs/DECISIONS.md:63` (B-058) state that the durable append-only retrieval log with fail-closed writes is implemented.
3. **The same inventory is stale about Excel ingestion.** `docs/RESEARCH_EVIDENCE_WORKFLOW.md:158` lists "Ingestion from PDF/scan/Excel/SPSS" as "Not built", while `docs/DECISIONS.md:70` (B-065) and `docs/HANDOFF.md:42` state that CSV/TSV **and XLSX** ingestion is built in `src/bp/ingest.py` (only PDF/OCR/SPSS are refused).
4. **The same inventory is stale about the method library.** `docs/RESEARCH_EVIDENCE_WORKFLOW.md:153` lists the statistics library as "descriptive, correlation, regression, two-group, ANOVA/KW, chi-square, linear trend", omitting everything added since build 0.42 (for example `paired_t`, `one_sample_t`, `two_way_anova`, `posthoc_pairwise`, `logistic_regression`, `reliability_alpha`, `multiple_comparison`, `power_analysis`, `missing_data_bounds`, `weighted_summary`, `wacc`, `dcf_valuation` and the appraisal methods - all present in `src/bp/methods.py`).
5. **B-052 is listed as an open gate while the register marks it deferred.** `docs/HANDOFF.md:54` puts B-052 in "Owner decisions that gate work (ask before building)", while `docs/DECISIONS.md:57` records it as "DEFERRED (owner, 2026-10-21)".
6. **The ledger engine decision has been provisionally pre-empted.** `docs/STAGE8_SPIKE_REPORT.md:26` says "Record the decision only after the Beancount arm has been run", yet `docs/DECISIONS.md:36` already carries a provisional recommendation for the custom kernel and `docs/DECISIONS.md:49` (B-044) records that Stage 8 "continues on the custom kernel" while B-032 stays OPEN.
7. **The R1-R10 ratification has no decision id of its own.** `docs/PRODUCT_GAP_MAP.md:28` attributes the open item to "B-053; R11 done, R1-R10 open", but `docs/DECISIONS.md:58` records B-053 as RESOLVED, so the open R1-R10 ratification is registered only as rows in `docs/RESEARCH_EVIDENCE_WORKFLOW.md:170-179`.
8. **Documentation spine coverage.** `docs/SOURCE_INVENTORY.md` is a document in `docs/` but has no row in the documentation-spine table in `docs/HOME.md:91-104`, while `docs/HOME.md:110` states that "Every new document gets a row in section 4". **FIXED at build 0.53** (computation owner, during review): the spine now has a row for it, and the docs-state guard (`tests/test_docs_sync.py`) fails on this class of gap from now on.

*Checked and found consistent (recorded so the next reader does not re-raise them):* the ingestion row of `docs/PRODUCT_GAP_MAP.md:27` was contradictory in an earlier revision of this draft - it claimed both that named columns map into a method's inputs (built, B-071) and that "automatic column->method-input mapping" was "Still missing" - and the current text has been rewritten to say "unattended column->method mapping (deliberately not built: which column is `values`/`y`/`predictors` is the user's declaration)". It is no longer a contradiction.

## Appendix C - what was read to prepare this file

- [`docs/HANDOFF.md`](../HANDOFF.md) (sections 4 and 5) · [`docs/DECISIONS.md`](../DECISIONS.md) (B-005, B-028, B-032, B-052, B-053, B-066, and the rows cited in each brief)
- [`docs/PRODUCT_GAP_MAP.md`](../PRODUCT_GAP_MAP.md) · [`docs/PARKED_QUEUE.md`](../PARKED_QUEUE.md) · [`docs/RESEARCH_EVIDENCE_WORKFLOW.md`](../RESEARCH_EVIDENCE_WORKFLOW.md) (sections 5, 13, 14, 15)
- [`docs/KNOWN_LIMITATIONS.md`](../KNOWN_LIMITATIONS.md) · [`docs/STAGE8_SPIKE_REPORT.md`](../STAGE8_SPIKE_REPORT.md) · [`docs/CONTRIBUTORS.md`](../CONTRIBUTORS.md) · [`docs/HOME.md`](../HOME.md) · [`README.md`](../../README.md)
- [`docs/sources/business_pipeline_v0_3.md`](../sources/business_pipeline_v0_3.md) (read-only): sections 1, 5.3, 9.1-9.5, 15, 15B, 16 · [`docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md`](../sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md) (read-only): the framework and risk records cited in Brief 2
- Code and tests cited in each brief, under `src/bp/`, `tests/`, `spike/` and `docs/sources/`.
