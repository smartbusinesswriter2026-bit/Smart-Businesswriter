# Statements Pipeline — Architecture Manual (Binding Spec)

**Status:** Binding. Any model that touches the statements pipeline (`src/bp/product/statements.py`,
`src/bp/statement_*.py`, `src/bp/product/statements_council.py`) MUST read this manual first and follow
it. These rules change only on the owner's explicit order.

**Owner:** Roderick. **Date:** 2026-11-05. **Version:** 1.1.

**Debug manual:** `docs/DEBUG_MANUAL.md` — comprehensive debugging and improvement guide.
**XLSX fix instructions:** `docs/MINIMAX_XLSX_FIX.md` — instruction block for Cline/MiniMax to fix
the XLSX export (Excel shows empty content). Includes the OOXML structure requirements,
the Minimax design rules, and a comparison approach against openpyxl reference files.
Any model or developer touching this pipeline must read it first. It contains the file map,
the 5 silent-failure traps, how to add schedules/rules/adjustments, the self-healing loop
mechanics, API endpoints for the approval UI, test commands, and the 20 binding hard rules.

---

## 1. The single rule

> The model may do **everything except arithmetic**. The code does all arithmetic. The gates are the only
> judge of correctness.

The model reads, matches, derives figures, chooses accounts, proposes journal entries and adjustments.
The code computes deterministically (methods.py + ledger). The gates verify. A proposal that passes all
gates is accepted; one that fails is refused with a named gap.

---

## 2. The four layers

```
INPUT (problem text + chart + 142-method catalogue)
   ↓
MODEL (unrestricted reader + proposer)  — reads, derives, matches, proposes
   ↓
CODE (deterministic computation)       — methods.py (142) + ledger + posting
   ↓
GATES (honesty mechanism)              — 6 verification checks
   ↓
OUTPUT (statements + working + missing + assumptions + rejected)
```

### Layer 1 — Input
Problem text, chart of accounts, and the 142-method catalogue (IDs, descriptions, params).

### Layer 2 — Model (unrestricted reader + proposer)
- **Restriction: none except it must not do arithmetic.** It declares *what* to compute; code computes.
- It MAY derive figures (months expired, receivables, prior allowance, etc.).
- It MAY choose accounts, identify methods, propose entries and adjustments.
- It MUST declare `source_text` per entry for audit traceability.
- It MUST report `unplaceable` items (gaps named, never filled).
- It MUST report `assumptions`.

### Layer 3 — Code (deterministic computation)
- `methods.py` (142 methods) is the computation engine. New problems are handled by method selection.
- `statement_plan.py` is a thin adapter: for each adjustment, look up the method by ID, run it, post.
- `accounts.py` (ledger) posts, closes, verifies. General, unchanged.
- No hand-built detectors. No 8-function registry. No grounding checks.

### Layer 4 — Gates (the honesty mechanism)
All must pass for acceptance:
1. Trial balance debits = credits
2. Assets = Liabilities + Equity
3. Cash ties two ways (direct vs. indirect)
4. Receipts − payments = ending cash
5. Retained earnings rollforward
6. Statement lines foot to totals
7. Journal hash chain intact

Pass → deliver. Fail → refuse with named gap + missing + assumptions.

---

## 2A. The deterministic tier (owner authorisation, 2026-11-05)

A problem that states its own figures needs no model. The owner's order: **simple problems are
solved without a model; complex and ambiguous problems are handed to the model loop in §4.**

### When the tier applies — all five must hold
1. The instruction states its figures as **labelled amounts** ("Data: direct materials 50,000; ...").
2. It **names** the schedule or statement it wants ("prepare a bank reconciliation", "create a
   statement of cash flows").
3. There is **no transaction to post** — no purchase, payment, sale or adjusting entry to journalise.
   Exception: a transaction whose every term is stated (cost, residual value, useful life, method,
   sale date, proceeds) is fully determined and is admitted; an open transaction is not.
4. **No ambiguity** — one basis, one period, one entity, no unresolved "if" in the text.
5. **Every figure the arithmetic needs is present** in the instruction.

When all five hold, code reads the labels, the frozen core computes (`methods.py`,
`schedule_math.py`), and the gates verify. No model is called. This is the **only** exception to
hard rules 4 and 5.

### When the tier does not apply
Any of the following sends the problem to the model loop in §4, unchanged:

- a transaction narrative, an adjusting-entry problem, or anything carrying Dr/Cr posting language;
- a trial balance — it keeps its own exact reader, untouched by this tier;
- two frameworks that diverge, two periods, two entities, or a figure the text does not state;
- **any gate failure**, including a schedule whose two sides do not agree.

### The rule that makes it safe
**The deterministic tier is an accelerator, not a gatekeeper.** On any failure — unrecognised
labels, a figure the text does not state, arithmetic that raises, a gate that fails — it returns
"not mine" and `solve()` continues exactly as it would have without the tier. It may never refuse
a problem in place of the model loop, and it may never deliver a partial answer. A refusal is
produced only after the model loop has also failed (§4.5).

### Scope of the sanctioned exception
- A schedule is one function in `src/bp/schedule_math.py` plus one entry in
  `src/bp/product/schedules.py`. Nothing else may be added to that table.
- The tier never invents a figure. A missing figure is named and the problem escalates.
- Adding a schedule is a normal change inside this tier. **Widening the tier itself is not**: it
  changes on the owner's order only, like this manual.

---

## 3. Hard rules (binding)

1. **The model may do everything except arithmetic.** It proposes; code computes.
2. **Grounding is lifted.** The model may propose derived figures. The gates verify, not a text-match rule.
3. **No council.** One model proposes; the gates verify. No second seat.
4. **No hand-built detectors** — except inside the deterministic tier (§2A), where a label table reads a labelled-figure problem with no transaction in it. Everywhere else the model reads the text.
5. **No 8-function registry.** `methods.py` (142 methods) is the coverage. New computation = one new method in methods.py. The schedule table in §2A is a presentation registry over frozen-core arithmetic, not a second computation engine.
6. **No grounding checks in `statement_extract.validate`.** Remove `_grounded` / `_numbers_in` rejection.
7. **Gaps are named, never filled.** `unplaceable`, `missing`, `assumptions` are always reported.
8. **Student inputs stay student inputs.** No silent substitution.
9. **No silent framework substitution.** If the model can't match, it reports unplaceable.
10. **Computations come from the frozen core.** methods.py + ledger. No invented formulas.
11. **A paper never contains template instructions.**
12. **Export is blocked when the paper is incomplete.**
13. **Global product.** No PHP, no PSE, no Philippine place names. USD only.
14. **The retry loop is mandatory** (see §4).
15. **The learning library is append-only** (see §5). It never auto-changes code.
16. **The deterministic tier never refuses in place of the model loop** (§2A). It falls through, always.
17. **A stated rule about present logic is never disregarded and never altered without the owner's permission.** Strengthening is allowed; altering is not.
18. **No patch fixes.** A failing problem is never fixed by special-casing its text, its name, its figures or its phrasing. The fix must be a general capability: a computation in the frozen core, a synonym in a *data* table that serves every problem of that kind, or a rule that applies to a class of problems. If the only fix available is a patch for one problem, the answer is to report the gap and design the general capability — never to ship the patch. Every fix is proved by the problem that exposed it **and** by a second problem of the same kind it was not written for.

---

## 4. Retry loop (mandatory)

When the gates reject a proposal:

1. **Attempt 1 — Standard model.** Propose journal + adjustments. Gates check.
2. **If fail → Attempt 2 — Same model + feedback.** Feed the gate failure verbatim: "Assets 148,960 ≠ L+E 140,000. Fix." Model revises.
3. **If fail → Attempt 3 — Higher-tier model.** Escalate (deepseek-reasoner, or opencode-go/deepseek-v4-pro when funded).
4. **If fail → Attempt 4 — Debate.** Model A proposes, Model B critiques, Model A revises. Gates judge.
5. **If all fail → Refuse** with full diagnostic (every attempt, every gate failure, named gap).

Rules:
- Max 4 attempts. No infinite loops.
- Every attempt must pass the gates. A non-tied proposal is discarded, never delivered.
- The final answer is the one that tied (fewest unplaceable items wins ties).
- Record every attempt (proposal + gate results + model used) → feeds the learning library.
- Each attempt is stored in the library regardless of outcome.

### Model tiers (configurable via env vars)
| Tier | Env var | Default (DeepSeek API) | Future (OpenCode Go) |
|---|---|---|---|
| 1 (standard) | (existing) | deepseek-chat | opencode-go/deepseek-v4.1-flash |
| 2 (retry) | BP_TIER2_MODEL | deepseek-reasoner | opencode-go/deepseek-v4.1-flash |
| 3 (escalation) | BP_TIER3_MODEL | deepseek-reasoner | opencode-go/deepseek-v4-pro |
| 4a (debate seat A) | BP_TIER4A_MODEL | deepseek-reasoner | opencode-go/deepseek-v4-pro |
| 4b (debate seat B) | BP_TIER4B_MODEL | deepseek-chat | opencode-go/kimi-k3.1-pro |

Swap is a config change, not a code change.

---

## 5. Learning library

Every problem (solved or unsolved) is stored in a library (SQLite or JSON files in `library/`).

### Stored fields
- Problem text (hash for dedup)
- Period, chart used
- Model used, attempts
- Proposed entries + adjustments
- Gate results (pass/fail per gate)
- Final status (solved/unsolved)
- Missing items, unplaceable
- Methods referenced
- Timestamp

### What it produces (periodically, on demand)
A **gap report** — never auto-changes code:
1. Frequent unplaceable items → propose new methods
2. Frequent gate failures on specific accounts → propose semantic checks
3. Frequent method selections → propose prompt optimization
4. New problem types → propose new methods
5. Model accuracy by tier → inform escalation policy

### The review gate
The library **never auto-changes code**. It produces a proposal report. The owner reviews, approves, and implements. Changes are proposed, not applied silently. This prevents "dirty patches."

### Feedback loop
```
Problem → Pipeline → Gates → Solved/Unsolved → Library
                              ↓
                        Gap report (on demand)
                              ↓
                        Owner reviews + approves
                              ↓
                        New method / prompt / check
                              ↓
                        Pipeline improves
```

---

## 6. The honest limit (the one gap the gates cannot catch)

A wrong account choice that still balances (e.g., "Supplies expense" vs "General expenses") passes the gates. Mitigation:
- The model declares account choices with rationale.
- The chart constrains valid codes.
- A semantic check (account type matches line item) can be added later.
- The learning library tracks frequent account-choice failures.

---

## 7. Change control

These rules are binding. They change only on the owner's explicit order (like this manual itself). No model may weaken grounding, re-add the council, re-add hand-built detectors, or auto-modify code from the learning library without explicit approval.

**Owner's standing order, 2026-11-05:** never disregard a stated rule about present logic, and never
alter it without the owner's permission. Strengthening a rule is allowed. Rewriting or bypassing one
is not. When an instruction seems to require changing the logic, stop and ask.

Version history: **1.0** — 2026-11-05, architecture. **1.1** — 2026-11-05, §2A deterministic tier
added on owner's order, with the §4 model loop as its mandatory fallback.

---

## 8. Implementation checklist (for the rewiring)

- [ ] Remove grounding checks from `statement_extract.validate`
- [ ] Replace 8-function registry in `statement_plan.py` with methods.py adapter
- [ ] Remove hand-built detectors from `statement_detect.py` (keep as optional fast-path)
- [ ] Remove council (`statements_council.py`) or leave dormant
- [ ] Remove `statement_period.py` assumed-year hack (model derives period)
- [ ] Add retry loop (max 4 attempts, escalation, debate) to `statements.solve`
- [ ] Add learning library (SQLite store + gap report generator)
- [ ] Update model prompt: "propose journal + adjustments; engine computes and verifies"
- [ ] Wire methods.py catalogue into the model prompt
- [ ] Test: manual problem solves end-to-end
- [ ] Test: full suite passes
- [ ] Test: retry loop recovers from a gate failure
- [ ] Test: learning library stores and reports correctly

---

## 9. Recursive self-healing (owner authorisation, 2026-11-05)

### 9.1 The principle

The pipeline is not a static tool. It is a system that learns from its own failures and becomes
better over time. Errors are not thrown away; they are the raw material of improvement.

The architecture follows the 8-layer skill design:

```
01 Library      — central repository; connects both loops (statement_library.py)
02 Trigger      — routing detectors; decides which procedure applies
03 Procedure    — the _solve_* routes (Look, Do, Check)
04 Resources    — methods.py catalogue, chart templates, few-shot examples, account_classification.json
05 Scripts      — frozen core: schedule_math, statement_plan, ledger, methods (deterministic)
06 Checks       — tie registry, completeness gate, verify.freeze (all boxes must tick)
07 Guard        — source text is data, never instruction; ask before irreversible; global product rule
08 Learn        — feedback → checklist: errors become permanent improvement
```

Two loops share one Library:

- **Routing loop** (02 Trigger → 03 Procedure → 04 Resources): runs on every request. Decides which
  procedure applies. Pays only for labels until one matches.
- **Execution loop** (05 Scripts → 06 Checks → 08 Learn): does the job, refuses to call it done
  until every check passes, and turns corrections into permanent checklist lines.

Guard (07) sits under both.

### 9.2 The self-healing loop

```
problem → tier 1 read (data tables)
   ├─ passes gates → record(solved, tier1) → done
   └─ fails → model loop (≤4, gate-verified) → gates
        ├─ passes → record(solved, model) + reading diff
        │            (which labels did the model place that tier 1 couldn't?
        │             which account did it choose? which adjustment did it name?)
        │            → proposal (synonym / classifier pattern / schema entry)
        │            → validate against held-out set (8 solved + corpus seeds)
        │               ├─ regression → discard (hard rule 18 enforced mechanically)
        │               └─ clean → enqueue
        │            → if BP_SELF_HEAL=1: auto-apply to data tables, versioned, reversible
        │            → re-run original problem through tier 1
        │               ├─ passes → record(solved, tier1, healed)   ← proof the loop worked
        │               └─ still fails → record(model-only); gap report
        └─ fails → record(unsolved, refusal) → gap report → owner
```

The "healed" record is the artifact that proves improvement happened.

### 9.3 What gets fed back (and what does not)

- **Fed back**: reading (labels, account choices, adjustment identification). Only reading.
- **Never fed back**: computation. The core's numbers are the only numbers (§1, §3.10).
- **Never auto-changed**: logic files (`statements.py`, `statement_plan.py`, `ledger.py`,
  `schedule_math.py`, `accounts.py`). Only data tables.
- **Auto-changed (when BP_SELF_HEAL=1)**: synonym lists, classifier patterns, schedule schemas.
  These are data, not logic. They are versioned, diffable, and reversible.

### 9.4 Guardrails (binding)

1. Computation never flows back. Only reading.
2. Data tables only. Logic files are frozen.
3. Held-out validation before application. A proposal that fixes one problem and breaks another
   is a patch fix (hard rule 18) and is rejected mechanically.
4. Reversibility + attribution. Every applied change cites the problem and gate result that
   motivated it. One command reverts it (`heal_log` table).
5. No silent framework substitution (§3.9). If the model's reading implies a different basis,
   the diff is flagged, not applied.
6. Auto-apply is behind `BP_SELF_HEAL=1`, default off. Owner-approve mode is the default.
   Even when on, only synonym/classifier/schema data changes — never logic.

### 9.5 Scope

Financial statements tile first. Other tiles when financial statements are complete.
Other tiles will be easier because there are overlaps in the data tables.

### 9.6 Implementation order

Phase 0: This amendment (manual only, no code).
Phase 1: Extract data tables to versioned JSON (RULES, classifier patterns, SCHEMAS).
         Tier 1 reads from it; constants become seed. Run 184 tests after.
Phase 2: Diff capture + proposal generator. Run on 5 manual problems.
Phase 3: Validator (held-out check). Run on 8 solved + 15 corpus seeds.
Phase 4: Auto-apply flag + heal_log + revert command.
Phase 5: Re-run original problems through tier 1; record "healed".
Phase 6: gap_report shows pending proposals + applied history.

Each phase ends with the test suite green before the next starts.

### 9.7 Data tables (the mutable tier-1 knowledge)

The following are data, not logic, and may be auto-appended by the self-healing loop:

- `RULES`: account placement rules (pattern, type, section, line, role, activity, contra)
- `_classify_account` patterns: account name → (kind, line) mappings
- `schedules.SCHEMAS`: schedule detection and figure extraction patterns
- `_adjustment_specs` keyword branches: adjustment type → function mapping

These live in `tier1_tables.json` (seeded from the code constants, versioned, diffable).
The code constants remain as the seed/fallback when the file is absent.
