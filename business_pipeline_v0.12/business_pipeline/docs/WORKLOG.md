# Worklog — append-only record of what was done

**Newest first. Never rewrite an entry.** One entry per increment (not per message): the ask, what changed, what verified it, the commit, and what is next. Link to the source of truth rather than restating it — `CHANGELOG.md` has the build detail, `DECISIONS.md` the reasoning, this file the narrative and the sequence.

---

## 2026-10-21 — Documentation spine: contributors' manual, home map, this worklog

**Ask:** after the gap discussion, the owner asked for a log that traces the work, a manual for any model that will touch or fix the files, and an Obsidian-like map to find things — then "go".
**Did:** added three documents and wired them in: `docs/CONTRIBUTORS.md` (ten non-negotiables, the add-a-method checklist, bug-fix rules, boundary-change rules, the testing contract, environment traps, "where each fact belongs", rejection list, stop-and-ask list), `docs/HOME.md` (task view, module map, capability status, documentation spine, map conventions), and this `docs/WORKLOG.md`. Design choices confirmed with the owner: `CONTRIBUTORS.md` is a repo-level bridge (not part of the authority manual), `HOME.md` uses plain Markdown links rather than Obsidian wikilinks, and the worklog starts now with a backfill pointer rather than reconstructing history.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HOME.md`, `docs/WORKLOG.md`, `README.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md` (B-055).
**Verified:** docs only; suite unaffected (400 tests OK run in the previous increment). Links checked against the files present in the repo.
**Commit:** this commit.
**Open/next:** Slice 1 of the gap plan — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison, power/precision, missing-data mechanism, weights/clusters) as the risky half, paired with the safe half: financial-statement ratio analysis (T1 arithmetic on the ledger artifacts).

---

## 2026-10-21 — Retrieval audit: response SHA-256 and UTC time per reference

**Ask:** "okay do 3 first" — the cheapest REW increment, Q10 in the living manual: make the hash-audit claim true.
**Did:** `CrossrefSource`/`OpenAlexSource` capture the raw response bytes and record `response_hash` (SHA-256 of those exact bytes) plus `retrieved_at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) on every resolved retrieval; the fields travel through `POST /api/literature/verify` and show in the workbench References panel. A reference that never reached a source (no DOI, 404, source error) carries neither, fail-closed. Clock is injectable for deterministic tests. Hash is byte-level on purpose: the same semantic record received with different whitespace hashes differently, so the audit pins what was served.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_api.py`, docs (REW manual v0.3, DECISIONS B-054, CHANGELOG 0.29, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, README).
**Decisions:** B-054 (PROVISIONAL); REW manual Q10 marked answered.
**Verified:** five new tests (byte-level pin vs parsed record, injected clock, audit survives a title mismatch, no audit without retrieval, OpenAlex parity) plus API/UI assertions; **400 tests OK**; live smoke against Crossref recorded a real sha256 for DOI `10.1038/nature12373`.
**Commit:** `3189816`.
**Open/next:** no durable retrieval log yet (documented); citation formatting is still `[OPEN]` Q9.

---

## 2026-10-21 — Owner ratifies R11: the REW living manual is the working authority

**Ask:** "yes to R11".
**Did:** ratified R11. The manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) is now the working authority for the Research & Evidence Workflow; B-035 (blocked on the missing Smart Researcher manuals) is closed and B-053 resolved. Manual to v0.2, stating explicitly that R11 ratifies the **document**, not its proposals — R1–R10 (stage list, checkpoints, tiers, taxonomy, etc.) remain unratified.
**Files:** REW manual, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Decisions:** B-053 RESOLVED; B-035 SUPERSEDED.
**Verified:** docs only; no code changed.
**Commit:** `7d73b6d`.
**Open/next:** cheap code increment that makes the manual honest — the retrieval audit (Q10).

---

## 2026-10-21 — Living manual for the research workflow (REW), replacing "Stage 7"

**Ask:** the owner believed Stage 7 had already been built; asked "what are these: reviewers, next templates, ledger engine, Stage 7 manuals?" and "create a living stage 7 manual and probably, rename that appropriately".
**Did:** explained the four owner asks (B-005 reviewers, B-028 next templates, B-032 ledger engine, B-035 missing research-pipeline manuals) and corrected the record: what existed was the Stage 7 **blocker** document plus the literature retrieval/verification boundary, not the workflow definition. Created `docs/RESEARCH_EVIDENCE_WORKFLOW.md` as a living manual, renamed the capability **Research & Evidence Workflow (REW)** — "Stage 7" was a build-order label, not a product name. Merged and removed `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md`; updated every reference. The manual refuses to pretend it is the lost Smart Researcher manual: every section is tagged `[OWNER]`, `[REPO]`, `[2ND]`, `[PROPOSAL]` (R1–R11) or `[OPEN]` (Q1–Q12), with stages R0–R8 proposed, three mandatory checkpoints, feasibility tiers, study taxonomy, retrieval/citation rules, claim rules, synthetic-data and AI-use policy, an honest inventory, and a ratification register.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (new), two Stage 7 docs (removed), `README.md`, `docs/DECISIONS.md` (B-035 superseded, B-040 pointer, B-053), `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`, `src/bp/literature.py` docstring.
**Decisions:** B-053 created; B-035 superseded.
**Verified:** docs only; **395 tests OK**.
**Commit:** `896372e`.
**Open/next:** owner ratification of the register (R11 asked first).

---

## 2026-10-21 — Product gap map

**Ask:** "what else in business have we overlooked?" (after the taxation discussion).
**Did:** wrote `docs/PRODUCT_GAP_MAP.md`: what the catalogue/manual call for versus what is built, ordered P0 gatekeepers (retrieval+citation, ingestion, decision dependencies), P1 statistics completion and finance/valuation, P2 catalogue breadth, plus the non-computational gaps in manual §15B/§16; with tier/verification notes and a recommended order.
**Files:** `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Verified:** docs only; cross-checked against `DECISIONS.md` and module inventory.
**Commit:** `8c71814`.
**Open/next:** decide which gap to close first (the recommended order was discussed, not started).

---

## 2026-10-21 — Taxation recorded as deferred

**Ask:** "does the jobs you did in creating the pipeline include taxation?" → no; "put it in your memory".
**Did:** recorded **B-052 DEFERRED**: the manual makes tax a non-goal and a jurisdiction-specific area to keep out of the autonomous path or gate behind retrieved sources; resume conditions (VAT/GST, income tax in the accounts, after-tax appraisal, filing) and the evidence lines from the manual are in the decision.
**Files:** `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
**Decisions:** B-052.
**Verified:** read-only analysis against `docs/sources/business_pipeline_v0_3.md` and `src/bp/methods.py`.
**Commit:** `efa9404`.
**Open/next:** product gap map.

---

## Backfill — earlier increments (v0.13 … 0.25)

Earlier work predates this log. The full ordered record is `docs/CHANGELOG.md` (0.13–0.25) and the stage reports; do not duplicate it here. In short: deterministic pipeline + spec/freeze (Stage 0–4), method library and golden fixtures (Stage 5), catalogue registry and T4 templates (Stage 6), model-provider boundary with evaluation scaffold (B-031/B-036/B-038/B-039), literature retrieval boundary (B-040), statistics increments (B-042), forecasting (B-043), and the Stage 8 accounting chain — schedules, two-route cash flow, closing/rollforward, declarative engagement, reconciliation, account-mapping checkpoint, policy changes, statement exports (B-044–B-051). The first commit in this repository is `1ab1d05`; the last pre-worklog increment is `efa9404`.
