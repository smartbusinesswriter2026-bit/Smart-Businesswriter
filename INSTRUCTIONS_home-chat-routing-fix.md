# Instruction block — Home chat must serve every subject

**How to use:** paste the block from "TASK" to the end into Cline (VS Code) as the task prompt, or save it as the prompt file for a terminal coding agent (Codex CLI / Roo Code / Claude Code). It is self-contained: the agent needs no conversation history. Nothing outside this repo is referenced.

---

## TASK

Fix the Home chat so that the open composer on Home accepts a brief from **any** business subject (marketing, operations, economics, finance, people, project management, research, accounting) and builds the best paper the product can honestly build — a framework alone, or a framework **plus** the computation the brief asks for — instead of refusing the brief with *"This does not look like a management or strategy instruction."*

The shelf boundary must survive: a brief that starts **from a named subject shelf** is still refused when it belongs to another shelf.

---

## WHERE

Repo root: `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline` (git branch `master`).

**The working tree is already dirty** (≈100 pre-existing modified/untracked files from in-flight work). Stage **only** the paths you touch (`git add <path> …`); never `git add -A` and never sweep the pre-existing changes into your commit.

---

## READ FIRST (mandatory, in this order)

1. `D:\SMART BUSINESSWRITER\AGENTS.md` (root)
2. `docs/CONDUCTOR_MANUAL.md` — §4 non-negotiables, §5/§6 checklists, §7 capabilities, §7.5 test matrix, §13 current limits
3. `docs/HANDOFF.md` — §2 non-negotiables, §3 what is already built
4. `docs/CONTRIBUTORS.md` — §1A/§1B (owner lanes) and §4 (the verifier is not yours to weaken)
5. `docs/BACKEND_CONTRACT.md` — §4 (product-backend lane: what you may and may not touch)

Do not re-architect anything. The rules below are the product.

---

## SYMPTOM (reported by the owner, verbatim)

Home composer → banner **"This analysis is not the right tool here"**, body **"This does not look like a management or strategy instruction. Name the firm, market, industry or decision you want to analyse."**

---

## ROOT CAUSE (verified against this tree — do not re-investigate, but do verify)

One hard-coded value plus three independent vocabulary gates:

1. `web/index.html:2237` — `const body = { brief: brief, subject: "management" };`
   The Home composer **hard-codes the management subject** on every start request. There is no way for Home to say "this brief is whatever subject it turns out to be".
2. `src/bp/product/chat.py:565` — `fits, message = guard.subject_fit(brief, subject or "management")`
   Every Home brief is therefore judged against the **management vocabulary**.
3. `src/bp/product/guard.py:74-96` — `subject_fit()` refuses any brief whose words miss `SUBJECT_HINTS["management"]` (18 nouns plus 4 substring words, `guard.py:11-15`). That refusal produces the exact message the owner saw.
4. `src/bp/product/guard.py:61-71` — `computation_boundary()`, called first inside `subject_fit()`, refuses **any** brief containing a computation word (`compute`, `calculate`, `balance sheet`, `income statement`, `npv`, `irr`, `debit`, `credit`, …) unless the subject is `accounting`/`finance`. On Home the subject is always `management`, so this gate always fires for such briefs.
5. `src/bp/product/chat.py:475-486` — `_fit()` is a **second, independent** gate: it refuses a brief whose words miss the 25-noun `EXTERNAL_HINTS` list (`chat.py:441-446`) when the framework is the PESTEL default, and it refuses any computation-word brief.
6. `src/bp/product/chat.py:618-619` — a refused brief becomes `state["stage"] = "not_supported"`, which `web/index.html:2052-2057` renders as the "This analysis is not the right tool here" banner.

**Evidence.** Running the conductor directly with `subject="management"` on ten realistic briefs: six are refused (marketing, operations, accounting, project management, people, research & statistics). The operations brief was refused **after** the resolver had already selected the `capacity_analysis` capability — the backend was ready and the gate was the only thing stopping it.

**Second finding — do not "fix" this by touching the cues.** `capabilities.resolve()` matches a deliberately narrow vocabulary and that vocabulary is pinned by the frozen test `tests/test_plan_corpus.py` (41 real briefs). The student can already attach **any** of the 126 catalogue capabilities to **any** evidence framework from the plan card (`chat._available_capabilities("pestel", [])` returns all 126), and every capability declares its own H1/H2 `slot`. So "framework + computation, whatever the subject" already works the moment the brief is accepted.

---

## THE RULE (what "correct" means)

1. **Home is the open entry point.** It must accept a brief from any subject and route it. It must never refuse a brief for lacking management vocabulary.
2. **The shelf boundary stays.** A brief that starts from a named shelf (Accounting, Finance, Economics, Marketing, Operations, Project management, Entrepreneurship, People, Research, Management) is still refused when it belongs to another shelf, with **today's exact message**.
3. **A paper may combine one framework with one or more computations, whatever subject the computation comes from.** No new paper shape, no new framework, no new computation.
4. **A brief the product genuinely cannot serve is still refused** — but the refusal names the shelf and the tool that can do the work. No dead end, and never the "wrong tool here" banner for a brief that only failed a vocabulary test.
5. **Nothing is invented.** Routing is deterministic and vocabulary-based. A detected subject is a *routing hint for the student* — it is never a claim about the firm, it is never evidence, and it never appears in the paper.

---

## CHANGE SET (product lane only)

### 1. `src/bp/product/guard.py` — additive

- Add `SUBJECT_OPEN = "any"` and `is_open(subject)`.
- Add `detect_subject(text)` → `(subject_id, cue_word)`: score the brief's **words** (not substrings, so `"market"` inside another word cannot match) against `SUBJECT_HINTS` for every subject; return the best match and the cue that matched, or `("", "")` when nothing matches. Deterministic; ties broken by the fixed key order of `SUBJECT_HINTS`. Reuse `_words()`.
- `subject_fit(text, subject)`: in open mode return `(True, None)` and skip the vocabulary refusal. **Every explicit subject keeps today's behaviour byte-for-byte** — `tests/test_chat.py`, `tests/test_capability_papers.py` and `tests/test_plan_corpus.py` must stay green without being edited.
- `computation_boundary(text, subject)`: in open mode it must not refuse. The shelf refusal stays exactly as it is.

### 2. `src/bp/product/chat.py` — `start()` and the fit decision

- `start()` accepts the open subject. On an open request:
  - detect the subject with `guard.detect_subject(brief)`;
  - record it on the state: `state["subject_requested"] = "any"`, `state["subject_detected"] = {"id", "label", "cue"}` or `None`, and `state["subject"]` = the detected id or `""` (`""` means "no subject detected" — do **not** write `"management"` as if the student had chosen it; `chat_store.list_cases` only displays this field);
  - **decide the refusal after the resolver has run.** `capabilities.resolve(brief, framework, answers)` must be called before the open-mode refusal is taken, and the resolver itself must not change.
- The open-mode refusal fires **only** when all three hold: the brief is a pure computation brief (`chat.COMPUTATION_HINTS`), the resolver selected no capability, and the brief names no evidence framework. In that case the message must name the shelf that can do the work (accounting → the Accounting shelf and its ledger/trial-balance/check tools; finance → the Finance shelf) and point at `GET /api/cases/subjects/{id}`. Write a **new** message for this path; do not reuse or reword the shelf refusal strings.
- Otherwise accept. A brief with no external hint word is **not** refused — the paper's Introduction carries the decision from the brief and the existing clarifying questions (`decision`, `geography`, `period`, `style`) still run.
- `_fit(brief, framework)` keeps today's behaviour for shelf mode. Put the open-mode branch in `start()` or give `_fit` an explicit open-mode parameter — but **do not change what `_fit` returns for a shelf subject**.

### 3. `src/bp/product/api.py`

`POST /api/cases/chat` already forwards `body.get("subject")`. No change is required. If you add validation, accept exactly `"any"` plus the ten shelf ids and refuse anything else with a reason (fail closed).

### 4. `web/index.html`

- `startChat()` (line 2230): stop hard-coding `subject: "management"`; send the open subject (`subject: "any"`). Keep `words` and the hidden `#chatframework` behaviour as they are.
- `renderChat()` `not_supported` branch (line 2052): when the backend reported a detected subject, offer **that shelf** ("Open the Accounting shelf") instead of the generic "Browse the subjects".
- Plan card (around line 2103, where `plan.framework` is printed): show the detected subject as a routing hint, e.g. *"Read as: Marketing & customers (detected from your brief)"*. It must read as where the brief sits, not as a finding, and it must never reach the paper.

### 5. Tests — NEW FILE ONLY

Create `tests/test_product_home_routing.py` (the product-lane convention is `tests/test_product_*.py`). **Do not edit any existing test file** and **do not touch `tests/fixtures/frozen_contract.json`**.

| # | Case | Expectation |
|---|---|---|
| 1 | open + marketing brief | not refused; detected subject `marketing`; a plan is reachable |
| 2 | open + operations brief naming capacity/demand | resolver selects `capacity_analysis` |
| 3 | open + finance brief with declared cash flows | resolver selects `npv`; the plan carries the framework **and** the slot `Financial Feasibility / Net Present Value` |
| 4 | open + economics brief (VAT / policy) | not refused |
| 5 | open + people, project-management and research briefs | not refused |
| 6 | open + pure accounting brief (journal entries, trial balance) | still refused, and the message names Accounting |
| 7 | **shelf mode control**: `chat.start(brief, "management")` with a marketing brief | still `not_supported`, and the message still says "does not look like a management or strategy instruction" (pins the shelf boundary) |
| 8 | `chat.start(brief)` with no subject | unchanged — still management semantics (pinned by `tests/test_chat.py`) |
| 9 | detection determinism | the same brief twice yields the same subject |
| 10 | nothing invented | the detected subject never appears in the drafted paper text |

### 6. Docs and commit (design-lane limits are binding)

- Add **one** row to `docs/BACKEND_CONTRACT.md` §6 describing the open subject routing.
- Add **one** `docs/CHANGELOG.md` entry and **one** `docs/WORKLOG.md` entry tagged `[product]`.
- **Do not edit** `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md` or `docs/HANDOFF.md` — they are computation-owned. Instead, draft the proposed **B-170** decision text (owner instruction, what changes, why, what it does *not* change) at the end of your WORKLOG entry and hand it to the owner to ratify.
- One increment = one commit. The message states what changed, what verifies it, and the test count.

---

## HARD CONSTRAINTS (do not)

- Do not edit any existing file under `tests/**`; do not edit `tests/fixtures/frozen_contract.json`.
- Do not change any number, formula, tolerance, **capability cue**, priority, slot, licence or claim wording. `capabilities.ENTRIES`, `capabilities.CATALOGUE_VERSION`, `src/bp/methods.py` and the frozen core are untouched. (Changing a cue breaks the frozen `tests/test_plan_corpus.py`.)
- Do not weaken `verify.py`, `paper.check`, the export gate or `_recompute_guard`.
- Do not reword the existing shelf refusal messages, caveats, disclaimers or honesty notices.
- Do not let the detected subject become a claim, a citation or part of the paper.
- Do not turn Home into a subject picker; the owner asked for **one** open composer.
- Standard library only at runtime; no new runtime dependencies.
- Never invent a source, a number, a citation or a framework.

**Known limitation to state, not to fix:** a `vrio` or `breakeven` paper still carries no second computation (the catalogue excludes them from `applies_to` by design, B-151). Out of scope unless the owner rules otherwise.

---

## ACCEPTANCE (show these before reporting done)

1. `python -m unittest discover -s tests` → the final line is `OK`. Report the test count before and after; the count must not drop. Never silence a failure, never edit an expected value to go green.
2. The repro script below prints **no** `not_supported` for the marketing, operations, project, people, research and finance briefs in open mode, and **still** prints `not_supported` for the pure accounting brief and for the shelf-mode control.
3. `git status --porcelain` shows only your own paths staged.

### Repro script

Save as `scripts/_repro_home_routing.py`, run `python scripts/_repro_home_routing.py` from the repo root, and **delete the file before you commit** (it is a diagnostic, not a test — the permanent coverage is `tests/test_product_home_routing.py`).

```python
import sys
sys.path.insert(0, "src")
from bp.product import chat

BRIEFS = [
    ("marketing", "Evaluate the effectiveness of the brand new digital advertising campaign for the target segment of urban millennials."),
    ("operations", "Assess whether the current production line capacity can meet the declared demand of 4,000 units per month."),
    ("accounting", "Prepare the journal entries and the trial balance for the month from the declared transactions."),
    ("project", "Evaluate the schedule risk and the probability of meeting the target completion date for the construction project."),
    ("people", "Analyze employee turnover and its effect on the organization productivity."),
    ("research", "Test whether the observed relationship between advertising spend and revenue is significant across 24 observations."),
    ("finance", "Determine the net present value of the declared cash flows of 1500000, 2000000, 2200000, 2400000 and 2500000 pesos at a 9 percent discount rate."),
]
for label, brief in BRIEFS:
    st = chat.start(brief, "any")
    caps = [r["key"] for r in (st.get("selection") or {}).get("selected") or []]
    print(label, "stage=", st.get("stage"), "subject=", st.get("subject"), "caps=", caps)
print("shelf control:", chat.start(BRIEFS[0][1], "management")["stage"])
```

Expected after the fix: `marketing`, `operations`, `project`, `people`, `research` and `finance` all print a stage other than `not_supported`; `accounting` still prints `not_supported`; the shelf control still prints `not_supported`.

---

## DONE CHECKLIST

- [ ] `src/bp/product/guard.py`: open mode + `detect_subject`; shelf behaviour unchanged.
- [ ] `src/bp/product/chat.py`: open-mode start, detection recorded, refusal decided after the resolver, actionable Accounting/Finance pointer.
- [ ] `web/index.html`: Home sends the open subject; the refusal card points at the right shelf; the plan card shows the routing hint.
- [ ] `tests/test_product_home_routing.py` created with the 10 rows above; no existing test edited.
- [ ] Full suite green, count reported.
- [ ] `docs/BACKEND_CONTRACT.md` §6 row, one CHANGELOG entry, one `[product]` WORKLOG entry with the drafted B-170 text.
- [ ] One commit; pre-existing dirty files left unstaged.
