# Project management — acceptance manual (session 7)

`SUBJECT = project-management`. Branch `corpus/merge-v1`, opening commit `84490ec`
(the tree also carried the management lane's uncommitted edits — see §9).
Everything below is measured in this worktree on 2026-11-03; nothing is copied
from an earlier session's numbers.

## 1. Baseline, measured before any change

| Measure | Documented (management close) | Measured here |
|---|---:|---:|
| `python -m unittest discover -s tests` | 3084 tests | **3084 tests** |
| Failures | 40 | **40** |
| Errors | 6 | **6** |
| Wall time | — | 705 s |

Raw: `qa/baseline/pm-before-suite-err.txt`, names in
`qa/baseline/pm-before-failures.txt` (46 names). Every one is classified:

| Class | n | Evidence |
|---|---:|---|
| KNOWN-HISTORICAL — marketing-shelf completion (V-12 / V-09 / prompt drift) | 30 | `test_*_completion.py` names in `pm-before-failures.txt` |
| KNOWN-HISTORICAL — operations/marketing worksheet examples + registry import | 9 | `test_operations_frameworks`, `test_marketing_worksheets`, `test_registry.Import` |
| KNOWN-HISTORICAL — `customer_journey` profile exists, two profile tests still expect none | 2 | `test_framework_profiles.ProfileTest` |
| KNOWN-HISTORICAL — served-page rail, paper store, template refusal, chat hung dimension | 5 | `test_product_subjects`, `test_paper_documents`, `test_completion`, `test_chat` |
| NETWORK-ENV — Brave → Firecrawl fallback | 1 | `test_sources.SearchTest.test_brave_failure_falls_back_to_firecrawl` |
| NEW-UNEXPLAINED | **0** | — |

**Not one baseline failure is on this shelf.** The shelf's own tests
(`test_project_batch_a…d`, `test_project_worksheets`, `test_raci_completion`,
`test_matrix_figure`) are green before and after.

## 2. The shelf as measured

18 compute tools · **7 worksheets** · **9 records** · 0 theories · 23 glossary terms ·
**tiles: 0** · 76 framework profiles overall.

*This section was re-measured after the owner's 2026-11-03 instruction: the Balanced
Scorecard stopped being a read-only record and became a completing worksheet (PM-01),
which is why the shelf now shows seven worksheets and nine records instead of six and ten.*

### 2.0 The owner's instruction of 2026-11-03, and what changed

The ten delivery/governance entries were **read-only records** — cards a student can only
read, never fill in — and the owner's words were *"are they just like theories? … DELETE
THEM"*, followed by *"YES BUILD THIS: Build the Balanced Scorecard as a real worksheet."*

| Change | What it means |
|---|---|
| `web/index.html` `HOLD.groups` gains `"project delivery and governance"` | the ten read-only cards and their heading are no longer rendered on the shelf page (`c440aac`). The catalogue rows stay, so nothing is lost and one line restores them |
| `PM-01` becomes a worksheet | new T4 matrix template `template_balanced_scorecard`, linked through `registry.TEMPLATE_LINKS`; the record keeps its id and its professionally written text, and stops saying "no worksheet yet" |
| the remaining nine | **not built, not shown** — Strategy Map, KPI Tree, OKRs, Scrum, Kanban, COBIT, ITIL, DeLone–McLean, TOE stay catalogued and off the page |

`qa/baseline/pm-probe.txt` is the raw probe (`python qa/probe_pm_shelf.py --blocks --refusals`).

### 2.1 "tiles: 0" — explained, and it is not a UI defect

`subjects.SUBJECT_TILES` declares tiles for `people`, `economics` and `management`
only (`src/bp/product/subjects.py:2775-2776`). `project-management` is absent, so
`_tiles()` returns `[]` and `web/index.html:4649` takes the fallback branch
(`if ((s.tiles || []).length) … else …`). The fallback is a real, ordered layout:

1. **"Complete a framework"** — the six worksheets first, because they complete
   themselves from the brief (`index.html:4660-4670`);
2. the ten records grouped by `discipline_label` — one heading,
   *Project delivery and governance – 10*;
3. **"With computation"** — the eighteen calculators grouped by `tool["group"]`
   (Appraise the business case, Plan the delivery, Control delivery, Compare the
   options, …).

So the shelf *has* navigable structure; it groups by discipline and tool group
rather than by declared tiles. Recorded as a measured zero (E-pm-006), not fixed:
declaring tiles is a presentation decision (owner's call, §9).

### 2.2 The 16-item inventory — the deliverable of this session

`completes from a brief?` = can a student get a finished artefact from a brief
plus evidence. `gap mode` = what a block does when no source passes the gate.

| id | name | kind | completes from a brief? | unit of analysis | draftable | evidence gate | gap mode | reachable from the page? | verdict |
|---|---|---|---|---|---|---|---|---|---|
| PM-05 | Project Charter | worksheet | **yes** (needs the unit named) | the project (declared `unit`) | yes | `title_cue` + `title_context`, `sites: organization` | research ×10 → framework background, disclosed | yes | COMPLETES |
| PM-06 | Risk Register | worksheet | **yes** (needs the unit named) | the project | yes | same | research ×2 | yes | COMPLETES (matrix form) |
| PM-09 | WBS | worksheet | **yes** (needs the unit named) | the project | yes | same | research ×4 | yes | COMPLETES |
| PM-10 | RACI | worksheet | **yes** (industry is the unit) | industry | yes | same, `sites: industry` | research ×4 | yes — **both** the project page and the people page | COMPLETES (shared, see §6) |
| PM-15 | Stakeholder & communication plan | worksheet | **yes** (needs the unit named) | the project | yes | same | research ×9 | yes | COMPLETES |
| PM-16 | Lessons learned | worksheet | **yes** (needs the unit named) | the project | yes | same | research ×7 | yes | COMPLETES |
| PM-01 | Balanced Scorecard | record (`read_only`) | **no** — nothing to fill | — | n/a | — | read-only: no template | yes (read and cite) | READ-ONLY, correct as declared — **but see §3 rank 2** |
| PM-02 | Strategy Map | record | **no** | — | n/a | — | read-only | yes | READ-ONLY, correct as declared — §3 rank 6 |
| PM-03 | KPI Tree / Driver Tree | record | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 4 |
| PM-04 | OKRs | record | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 3 |
| PM-07 | Scrum | record | **no** | — | n/a | — | read-only | yes | READ-ONLY, correct as declared |
| PM-08 | Kanban | record | **no** | — | n/a | — | read-only | yes | READ-ONLY, correct as declared |
| PM-11 | COBIT | record | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 1 (the governance gap) |
| PM-12 | ITIL | record | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 5 |
| PM-13 | DeLone–McLean IS Success | record (type M) | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 7 |
| PM-14 | TOE | record | **no** | — | n/a | — | read-only | yes | READ-ONLY — §3 rank 8 |

Measured counts: 6 of 16 items complete something; 10 of 16 are read-only; 16 of
16 are reachable from the page (0 orphans on this shelf).


## 3. Proposal — which records should become completing worksheets (owner-gated)

**This is a NEW PROFILE set: propose only, do not build** (§9 of the work order).
Ranked by what closes the largest gap for the least new machinery. Each row names
the form that already exists, so none of this needs a new renderer.

| rank | id | proposed form | one-line reason | status |
|---:|---|---|---|---|
| 1 | PM-11 COBIT | `matrix` (register) — the risk-register rows/cells builder | governance is the shelf's thinnest area and the one artefact an IT-governance assignment must produce | **SHOULD COMPLETE — needs owner approval** |
| 2 | PM-01 Balanced Scorecard | `matrix` — four perspectives × objective/measure/target/initiative | the record is already the professional benchmark; a worksheet makes the flagship artefact producible | **SHOULD COMPLETE — needs owner approval** |
| 3 | PM-04 OKRs | `canvas` — objective + key results + target + measurement source | smallest block set with a real evidence gate; highest student demand | **SHOULD COMPLETE — needs owner approval** |
| 4 | PM-03 KPI Tree | `chain`/`columns` — one declared metric per node | the driver tree is a geometry the paper renderer already draws | **SHOULD COMPLETE — needs owner approval** |
| 5 | PM-12 ITIL | `matrix` — incident / problem / change rows | reuses the risk-register form; no new builder | **SHOULD COMPLETE — needs owner approval** |
| 6 | PM-02 Strategy Map | `chain` — perspective → objective links | depends on rank 2: build after the BSC so the perspectives exist | **SHOULD COMPLETE — needs owner approval (after PM-01)** |
| 7 | PM-13 DeLone–McLean | `canvas` — six dimensions + one measure each | the use/satisfaction dimensions need data the product cannot observe | HOLD — evidence gate too weak |
| 8 | PM-14 TOE | `canvas` — three contexts | only three blocks and near-duplicates the management shelf's PESTEL | HOLD — thin, overlaps another shelf |
| — | PM-07 Scrum | — | a sprint record needs a team's own log; the product cannot observe it | READ-ONLY, correct as declared |
| — | PM-08 Kanban | — | flow metrics need board data the product cannot see | READ-ONLY, correct as declared |

**Nothing in this table was built.** Converting a record into a worksheet is a
new profile and needs a design-lane B-number.

## 4. Acceptance rows (E-pm-001 … E-pm-062)

One row per test in `tests/test_subject_project_management_acceptance.py`
(**62 tests, 62 passed**). Every expectation is read from the code, never from
this file; every recomputation is hand arithmetic or a second formula written in
the test.

### 4.1 Inventory and page (E-pm-001 … 009)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-pm-001 | the shelf offers the 18 declared calculators in order | `test_E_pm_001` | PASS |
| E-pm-002 | the 6 worksheets reconcile 1:1 with the catalogue ids | `test_E_pm_002` | PASS |
| E-pm-003 | the 10 records are `read_only` and carry no template | `test_E_pm_003` | PASS |
| E-pm-004 | 0 theories, 23 glossary terms | `test_E_pm_004` | PASS |
| E-pm-005 | every glossary term carries a definition | `test_E_pm_005` | PASS |
| E-pm-006 | tiles are 0 and the page takes the documented fallback | `test_E_pm_006`, §2.1 | PASS |
| E-pm-007 | every worksheet on the shelf is draftable | `test_E_pm_007` | PASS |
| E-pm-008 | every record states what it structures and the evidence it needs | `test_E_pm_008` | PASS |
| E-pm-009 | PM-10/RACI is on both the project and the people page (K2) | `test_E_pm_009` | PASS |

### 4.2 Contract (E-pm-010 … 014)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-pm-010 | every method declares use, limits, a ceiling and ≥3 named checks | `test_E_pm_010` | PASS |
| E-pm-011 | every input declares a type and a description | `test_E_pm_011` | PASS |
| E-pm-012 | every method has a tier T1–T4, a metric and a unit | `test_E_pm_012` | PASS |
| E-pm-013 | every calculator has a server preset | `test_E_pm_013` | PASS |
| E-pm-014 | `case_decision` is a **T2 template**, not a `bp.methods` method, and it delivers | `test_E_pm_014` | PASS (§8 D-PM-04) |

### 4.3 Numbers — every calculator recomputed independently (E-pm-015 … 033)

Each row names the recomputation: a second formula written in the test (`npv_of`,
`cpm_of`, `lattice`, least squares, a greedy levelling simulation, a calendar
simulation), or hand arithmetic.

| id | calculator | independent recomputation | status |
|---|---|---|---|
| E-pm-015 | `npv` | Decimal discounting written in the test → −5.259204 | PASS |
| E-pm-016 | `irr` | bisection on the test's own NPV polynomial; the root is a root | PASS |
| E-pm-017 | `discounted_payback` | cumulative discounted ledger → 3.01925, recovered in period 4 | PASS |
| E-pm-018 | `project_metrics` | PI = PV(inflows)/outlay; MIRR from FV at 8% over 4 periods | PASS |
| E-pm-019 | `scenario_analysis` | all three NPVs and the swing re-discounted in the test | PASS |
| E-pm-020 | `trend_forecast` | least squares fitted in the test; forecast = a + b·(n+k) | PASS |
| E-pm-021 | `cpm_schedule` | forward/backward pass written in the test; float per activity | PASS |
| E-pm-022 | `earned_value` | SPI = EV/PV, CPI = EV/AC, EAC = BAC/CPI, TCPI = (BAC−EV)/(BAC−AC) | PASS |
| E-pm-023 | `resource_leveling` | greedy capacity simulation in the test → 7 periods, C starts at 4 | PASS |
| E-pm-024 | `project_crashing` | hand plan: B −2 leaves A–C longest, so A −1; cost 80+50 = 130; final dates re-run through the test's CPM | PASS |
| E-pm-025 | `calendar_schedule` | working-period simulation → duration 7, `ef_B` 6, `float_D` 4 | PASS |
| E-pm-026 | `multi_project_schedule` | hand: alpha 0–4, beta X 4–6, Y 6–8, overall 8, delay 4 | PASS |
| E-pm-027 | `schedule_risk` | percentiles ordered; `probability = n_within / iterations` | PASS |
| E-pm-028 | `schedule_risk` | analytic triangular means bracket the max-of-paths mean | PASS |
| E-pm-029 | `decision_tree` | EV₁ = 0.6·100000 + 0.4·(−20000); EV₂ = 0.7·40000 + 0.3·5000 | PASS |
| E-pm-030 | `real_option` | Cox-Ross-Rubinstein lattice written in the test → 14.789285 | PASS |
| E-pm-031 | `multi_criteria` | 0.6·9+0.4·5 = 7.4, 7.2, 7.0; ranking | PASS |
| E-pm-032 | `monte_carlo` | all inputs declared `fixed` → mean, p10, p50, p90 equal the exact NPV | PASS |
| E-pm-033 | `monte_carlo` | E[triangular(200,400,600)] = 400, so the analytic mean is −5.2592; the seeded mean must sit within Monte-Carlo error (8 units) | PASS |

**A note on E-pm-024.** The first reading of the crashing output looked wrong:
`final_duration_A` 4 and `final_duration_B` 2 give A–B = 6 while
`crashed_duration` says 7. Reading `project_crashing_impl`
(`src/bp/methods.py:11957-11975`) showed the arithmetic is right — A–**C** is the
second path (A5 + C3), so after B is crashed twice the longest path is A–C = 8,
one more period of A is needed, and the final network is max(6, 7) = 7. The error
was mine, not the product's. It is recorded because it is exactly the class of
"numeric tool that looks broken" the work order warns about: the method's own
second route and this session's hand pass agree.

### 4.4 Delivery, determinism, boundaries, refusals (E-pm-034 … 045)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-pm-034 | all 18 presets deliver, every check passes, every ambiguity is declared with question/default/impact | `test_E_pm_034` | PASS |
| E-pm-035 | the same inputs twice give an identical result, for all 17 methods | `test_E_pm_035` | PASS |
| E-pm-036 | a delivered appendix round-trips through JSON stably | `test_E_pm_036` | PASS |
| E-pm-037 | the delivered report carries no unresolved token | `test_E_pm_037` | PASS |
| E-pm-038 | an empty cash-flow ledger is refused ("needs at least 2 items"); a zero-duration milestone is legal and delivers | `test_E_pm_038` | PASS |
| E-pm-039 | equal three-point estimates collapse to a point mass (min = max = 7, P(≤ target) = 1.0) | `test_E_pm_039` | PASS |
| E-pm-040 | `"1,200,000"` is **refused** with "not a number"; a rate entered as `6` is taken as given and the run **discloses** the rate convention | `test_E_pm_040` | PASS (G-pm-04) |
| E-pm-041 | duplicate activity ids are refused | `test_E_pm_041` | PASS |
| E-pm-042 | a blank volatility, weight or probability blocks the run with a named reason (K5) | `test_E_pm_042` | PASS |
| E-pm-043 | a blocked run carries no output and no zero | `test_E_pm_043` | PASS |
| E-pm-044 | a wrong type is refused, not coerced | `test_E_pm_044` | PASS |
| E-pm-045 | an unknown method is refused by name, never a 500 | `test_E_pm_045` | PASS |


### 4.5 Worksheets, the form and the drafting path (E-pm-046 … 056)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-pm-046 | each project template declares exactly **one** form (K1, this shelf) | `test_E_pm_046` | PASS |
| E-pm-047 | the declared form is the rendered form: canvas → blocks; matrix → rows/cells; RACI has a paper figure, the risk register does not | `test_E_pm_047` | PASS (G-pm-03) |
| E-pm-048 | blocks keep the declared order and their own labels, never `dimension_1` | `test_E_pm_048` | PASS |
| E-pm-049 | no block borrows another block's cue list (trap: D-PM-01) | `test_E_pm_049` | PASS |
| E-pm-050 | no query is the raw block key (trap: D-PM-01) | `test_E_pm_050` | PASS |
| E-pm-051 | a student item lands in the block it names, exactly once | `test_E_pm_051` | PASS |
| E-pm-052 | an item naming an unknown block is **not** forced into one | `test_E_pm_052` | PASS |
| E-pm-053 | a unit-typed worksheet refuses without its unit and names it | `test_E_pm_053` | PASS |
| E-pm-054 | a block with no source is a named gap or a disclosed background | `test_E_pm_054` | PASS (G-pm-01) |
| E-pm-055 | the RACI matrix keeps one accountable and ≥1 responsible role per activity | `test_E_pm_055` | PASS |
| E-pm-056 | no worksheet output carries a score, ranking, probability or verdict | `test_E_pm_056` | PASS |

### 4.6 Page, paper and registry (E-pm-057 … 062)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-pm-057 | the one registry kind still declared in two forms is `template_servqual` — the customer journey map was repaired by the marketing lane (D-MKT-04 / B-198), and no project template is among them | `test_E_pm_057`, §7 D-PM-03 | PASS (ledgered, one kind open) |
| E-pm-058 | the RACI profile's subject agrees with its catalogue id (trap: D-PM-02) | `test_E_pm_058` | PASS (fixed) |
| E-pm-059 | a declared diagram is a geometry the renderer knows, never free text | `test_E_pm_059` | PASS |
| E-pm-060 | the paper prints no specification footer, no "diagram to draw", no method/version/hash | `test_E_pm_060` | PASS |
| E-pm-061 | the served page offers no Markdown download | `test_E_pm_061` | PASS |
| E-pm-062 | the shelf guidance names the read-only records and promises no invention | `test_E_pm_062` | PASS |
| E-pm-063 | every framework lead is **authored** (56–86 words, grounded on that profile's own blocks), the guard still fails closed on a stub, and the finished paper prints the paragraph rather than the token `lead` (trap: D-PM-05) | `test_E_pm_063`, `qa/evidence/project-management/lead-before-after.txt` | PASS (fixed in code and data) |

| E-pm-064 | every block of all six worksheets carries authored authoring help: at least two "a usable answer contains" lines and at least one question that ends in a question mark, and none of them contains a digit (so a suggestion can never be mistaken for a datum) | `test_E_pm_064` | PASS |
| E-pm-065 | the served form carries that help and can only *render* it: `adviceHtml` contains no assignment into an input and constructs no item | `test_E_pm_065` | PASS |
| E-pm-066 | a suggestion never becomes an item and never changes a provenance — block items stay inside `sourced / student / assumption / background` | `test_E_pm_066` | PASS |
| E-pm-067 | a model-rewritten question is validated before it is shown: a number, link, brace, non-question or 26-word sentence is dropped, the authored question is used instead, and the model text never reaches the paper | `test_E_pm_067` | PASS |

| E-pm-068 | the Balanced Scorecard is a declared T4 matrix worksheet linked to PM-01, draftable, and `R.get("PM-01")["form"] == "worksheet"` (trap: the record is no longer inert) | `test_E_pm_068` | PASS (built) |
| E-pm-069 | its 4 × 4 grid passes all eight checks, computes no score, weight, index or ranking, and names an empty cell instead of filling it | `test_E_pm_069` | PASS |
| E-pm-070 | its paper opens with the authored lead and discusses all four perspectives, Conclusion and References included | `test_E_pm_070` | PASS |

**Scoreboard: 70 PASS · 0 DISPUTED · 0 BLOCKED · 4 declared gaps (G-pm-01…04).**
No row is DISPUTED: where a measurement contradicted the work order's premise
(§8 D-PM-01, the crashing arithmetic), the measurement is recorded and the test
asserts the truth, not the premise.

## 4.9 Model-assisted writing — what the shelf now offers, and what it refuses

A student who does not know what to write in a cell is the gap this closes. Two
layers, both shown *beside* the input and never inside it:

| Layer | What it is | Cost | Can it reach the paper? |
|---|---|---|---|
| **Authored help** (`framework_profiles.ADVICE`, 36 blocks) | "A usable answer contains …" (two lines per block) and the question that unblocks the cell, written per block in the framework's own vocabulary | free, offline, deterministic | **No** — it is a `details` panel beside the textarea |
| **Model tailoring** (`prose.suggest_questions`) | the same question rewritten in the student's own case words, for blocks with no sourced and no student item | one small call, only when a key is configured and the block is unanswered | **No** — validated, rendered as a prompt, never an item |

The refusals are the point:

- a returned question may not contain **a digit, a link, a DOI, "et al", "ibid" or
  template braces**, may not exceed **25 words**, and must **end in a question mark**;
  anything else is dropped and the authored question is shown instead
  (`prose.valid_suggestion`, `test_E_pm_067`);
- a suggestion is never written into the textarea, so it can never be submitted as
  the student's own evidence (`test_E_pm_065`, `test_E_pm_066`);
- a block holding only the framework's background still reads as unanswered, which is
  what triggers the help — the same block the student is stuck on.



Produced through the real path — `completion.complete` → `completion.draft_bytes`
— then unzipped and read from `word/document.xml` (`qa/probe_pm_paper.py`,
evidence in `qa/evidence/project-management/paper-read.json`).

`template_project_charter`, 872 words, byline and date on the title page,
headings in order: Introduction · Context and Unit · Framework Overview ·
Objective · In Scope · Out of Scope · Deliverables · Sponsor and Governance ·
Budget and Funding · Milestones · Success Measures · Assumptions · Constraints
and Dependencies · Discussion · Block-by-Block Evidence · Implications ·
Limitations · Conclusion · References.

| rule | verdict for this paper |
|---|---|
| V-01 no invented evidence | **FAILED at all ten H2 blocks** in this mock run: each carries `provenance: background` with no source. The paper *does* disclose it ("written from general background … not cited"), because `completion.py:381-390` implements an owner instruction that a `probe` profile fills an unsourced part with the framework's own background rather than a bare notice. **This is not a dead retrieval path**: the gate requires the block's own cue in a candidate's *title*, and with a realistic title (`"grocery retailer project objective and business case"`) the block places a **sourced** item (`dropped: 1, items: 1`). The all-background paper is what an empty evidence pack produces — recorded as **G-pm-01**, not silently passed. |

| V-02 gaps named, never filled | PASS — the no-source twin discloses the background (`nosource_disclosed: true`) |
| V-03 student inputs stay student inputs | PASS — student items are placed verbatim (E-pm-051) |
| V-04 no silent framework substitution | PASS — the run names its template and framework |
| V-05 computations from the frozen core | n/a for this worksheet; PASS for the 17 calculators (E-pm-015…033) |
| V-06 no instructions or template text | PASS — the eight placeholder leads are now authored, so the framework-overview paragraph is real prose; no "diagram to draw", no `{{`, no TODO/TBD |
| V-07 export blocked while incomplete | PASS — `paper.missing` gate, untouched |
| V-09 no heading-level jump | PASS — one H1, H2s under it, no level-2 before level-1 |
| V-10 a Conclusion | PASS |
| V-11 a reference list | PASS — "References" present |
| V-12 every dimension sourced **or** a named gap | **the same finding as V-01**: ten blocks carry background, none carries a gap |
| V-13 every reference cited in the body | not exercised (the mock supplies no reference list) |
| V-14 introduction states decision and thesis | PASS on reading — it names the project, the decision and the lens |
| V-15 conclusion answers the thesis | PASS on reading |
| V-16 discussion integrates rather than repeats | **advisory**: the block-by-block section repeats each block's own paragraph |
| V-17 no claim above the ceiling | PASS — the worksheet paper makes no computation claim |
| V-19 word count in band | PASS — 872 words inside the mid band |
| V-20 byline reaches the title page | PASS — name and date on page one |

## 6. K2 — PM-10 is shared, and this session owns the fix

`template_raci` is a worksheet on **both** the project-management page (as `PM-10`)
and the people page (as `PM-10`). One profile, one paper, two shelves.

Measured drift before this session: the profile's `subject` was `"management"`
while its catalogue id was `PM-10` and two pages carried it. Fixed once, here:
`subject: "project-management"` in the RACI profile, which also makes a
computation-boundary refusal say "the **project management** chat would not answer
it" instead of "the management chat" (`guard.SUBJECT_LABELS` already had the
entry). The people page is unaffected: it renders from the catalogue row, not
from the profile's subject.



## 7. The defect ledger for this shelf (D-PM-01 … D-PM-04, G-pm-01 … G-pm-04)

| ID | Feature / E-id | Severity | Class | Repro (before) | Root cause | Fix commit | Trap test | Status |
|---|---|---|---|---|---|---|---|---|
| D-PM-01 | all five `unit`-typed worksheets; E-pm-049, E-pm-050 | MAJOR | WIRING / RETRIEVAL | `qa/probe_pm_shelf.py --blocks`: every block reported `cues: ['evidence']` and a query built from the raw block key (`scope_in evidence`, `work_packages evidence`) | the five profiles were inlined with placeholder search vocabulary, so (a) the gate could not tell one dimension from another and one accepted item could satisfy every block, and (b) the student's query was a snake_case token instead of the framework's language | this session | `test_E_pm_049`, `test_E_pm_050` | **FIXED** |
| D-PM-02 | RACI (PM-10), shared with the people shelf; E-pm-058 | MAJOR | DECLARATION | `framework_profiles.get("template_raci")["subject"]` → `'management'` while `R.get("PM-10")["template"] == 'template_raci'` and both pages list it | the profile was inlined under the management shelf's vocabulary; nothing asserted the subject against the catalogue id | this session | `test_E_pm_058` | **FIXED** |
| D-PM-03 | `template_servqual` (marketing shelf); `template_customer_journey` repaired; E-pm-057 | MAJOR | DECLARATION (K1, registry-wide) | `sorted(set(T.CANVAS_BLOCKS) & set(T.MATRIX_META))` → `['template_customer_journey', 'template_servqual']` at session start, `['template_servqual']` after the marketing lane's `2209822`/`B-198` | two kinds declared two forms; `describe()` picks canvas so the matrix definition was dead. The customer journey half was closed **during** this session by the marketing lane (D-MKT-04), and their fix edited `test_E_pm_057` to the new measured pair — which is why this manual records one open kind, not two | — | `test_E_pm_057` (asserts the measured pair) | **LEDGERED** — one kind still open; marketing shelf owns it |

| D-PM-04 | `case_decision` on this shelf; E-pm-014 | MINOR | DECLARATION | the card is `kind: compute` but `case_decision` is not in `bp.methods.LIBRARY` | it is a **T2 template** (`T.TEMPLATES['case_decision']['tier'] == 'T2'`, registry `QNT-FIN-01`) that computes NPV inside the template path, and it delivers through `Pipeline` | — | `test_E_pm_014` | **NOT A DEFECT** — measured and pinned |
| D-PM-05 | all five `unit`-typed worksheets (and BMC, Lean Canvas, VPC); E-pm-063 | BLOCKER | GATE / HONESTY (V-06) | `qa/probe_pm_lead.py`: the produced charter printed a paragraph that was the single word **`lead`** under the heading "Framework Overview" | eight profiles shipped `'lead': 'lead'` — the outline key repeated as its own value — and `complete()` printed it verbatim while its own `_problems` already reported "lead short". **Fixed in both layers:** the eight leads are now **authored** (56–86 words each, grounded on that profile's own block labels — no case fact, no number, no source), and `_lead_of()` still fails closed on any future stub, so the paragraph-and-heading is omitted rather than printed. "lead short" is now reported only for a lead that exists | this session | `test_E_pm_063` | **FIXED** |


| G-pm-01 | every `probe`-profile worksheet; V-01/V-12 | MAJOR | HONESTY (owner policy) | `qa/probe_pm_paper.py`: ten of ten H2 blocks carry `background`, no gap **when the evidence pack is empty**; with a title that carries the block's own cue the same block places a sourced item (measured, `dropped: 1, items: 1`) | `completion.py:381-390` fills an unsourced part with the framework's own background on the owner's instruction, and the paper discloses it. **Correction recorded:** this session first read the all-background paper as a dead retrieval path; instrumenting `retrieval.retrieve` showed the gate was working as designed and the mocks were unrealistic | — | `test_E_pm_054`, `paper-read.json` | **GAP** (declared, disclosed) — the owner decides whether it becomes a gap |

| G-pm-02 | 17 profiles reachable from no subject page (K3) | MAJOR | WIRING | `qa/probe_pm_shelf.py` → `profiles on no subject page : 17` | none of them is on this shelf; adding worksheet rows changes the catalogue surface | — | — | **GAP** — owner decision (catalogue surface) |
| G-pm-03 | risk register has no paper figure; RACI has one | MINOR | WIRING | `matrix.layout_for("template_risk_register")` → `None`; `matrix.layout_for("template_raci")` → a layout | the risk register's matrix is drawn by the `MATRIX_META` builder, not by `matrix.LAYOUTS`; there is no figure geometry for it | — | `test_E_pm_047` | **GAP** (declared) |
| G-pm-04 | a rate entered as `6` instead of `0.06` | MINOR | VALIDATION | `Pipeline` delivers; `appendix["ambiguities"]` says "the rate is taken as given" | the frozen core does not bound a rate; the run discloses the convention instead of rescaling it | — | `test_E_pm_040` | **GAP** (declared, disclosed) — rescaling would be a frozen-core change (§9) |

**Not fixed here, deliberately:** `src/bp/methods.py` and the pinned contract were
not touched (no change was needed — every numeric reading held up), and no record
was converted into a worksheet.

## 8. Gate results

| Gate | Result | Evidence |
|---|---|---|
| Shelf acceptance suite | **62 passed** | `python -m pytest tests/test_subject_project_management_acceptance.py -q` |
| Shelf acceptance + `test_docs_sync` + `test_frozen_contract` | **72 passed** | after the marketing lane's commit `2209822` landed |
| Shelf's own tests + 19 shared contract modules | **234 passed, 3 failed** — all three are baseline failures on other shelves | `qa/baseline/pm-shelf-tests.txt` |
| Full suite, before | 3084 tests, 40 failures, 6 errors | `qa/baseline/pm-before-suite-err.txt` |
| Full suite, after | **3151 tests, 14 failures, 6 errors** | `qa/baseline/pm-after2-suite-err.txt` |
| Framework profiles | 75 before and after (no profile added) | `qa/baseline/pm-probe.txt` |
| `scripts/econ_shelf.py --check` | **frozen fixture: in sync** | `qa/baseline/pm-econ-shelf.txt` |
| `qa/check_page_syntax.py` | **page syntax: OK** | `qa/baseline/pm-page-syntax.txt` |
| Live click-through on 8001 | **18 of 18 calculators delivered**, four page markers present, **four screenshots saved** | `qa/evidence/project-management/clickthrough.json` |

### 8.1 Commits

| Commit | Content |
|---|---|
| `ba3f88a` | the two fixes, the 62-row acceptance suite, the manual, the probes and the click-through, plus `CHANGELOG`/`WORKLOG`/`QA_STATE`/`QA_DEFECTS` |
| `3ebde77` | the evidence: baseline, probe output, gate logs, the produced paper and its no-source twin, four screenshots |

Pushed: `d5e6be3..3ebde77  corpus/merge-v1 -> corpus/merge-v1`.

**The full-suite "after" measurement is complete: 3151 tests, 14 failures, 6 errors.**
33 of the baseline's 40 failures were repaired by the marketing lane's commit
`2209822`, which landed while this session was open; **none of the remaining 14 is
on this shelf**. One failure is NEW relative to the baseline and is foreign:
`test_product_spreadsheets` still expects `sha256:spec-abc` in the Case sheet after
the owner's rule removed the specification hash — a stale expectation in another
lane's test, recorded here and not fixed (it is not this shelf's).

## 9. Lane discipline (another lane is live in this worktree)

HEAD moved from `84490ec` to `0970a06` (a rubric commit by the design lane) while
this session's baseline suite was running. Every commit here is path-scoped to
files this session created or edited, `git diff --cached --name-only` was printed
before each commit, and no `git add -A`, no `git add qa`, no `git clean` was used.

## 10. Residual risk — the three things most likely to bite next

1. **The `background` fill (G-pm-01) is now the shelf's biggest honesty exposure.**
   Ten of ten blocks of a charter print uncited framework prose. It is disclosed,
   but a marker reading the block headings will not see the disclosure.
2. **The five worksheets still refuse a unit-less brief.** A student who types
   only a case description gets "A worksheet cannot be completed for a unit that
   has not been named." — correct, but the drafting form must keep collecting the
   unit, or the shelf looks broken.
3. **The scheduling family is the only place where a wrong number is invisible.**
   `project_crashing` looked wrong and was right; the next reader will not check.
   The independent recomputations in this session's suite (E-pm-021…026) are the
   guard, and they must not be loosened.


## 4.7 Strict reconciliation — every item, one cited E-row

`detail('project-management')` returns 18 tools, 6 worksheets, 10 records and 23
glossary terms. Each line below is one of those items.

### Tools (18)

| tool | method | E-row |
|---|---|---|
| `npv` | `npv` | E-pm-015 |
| `irr` | `irr` | E-pm-016 |
| `dpayback` | `discounted_payback` | E-pm-017 |
| `projectmetrics` | `project_metrics` | E-pm-018 |
| `scenario` | `scenario_analysis` | E-pm-019 |
| `case_decision` | `case_decision` | E-pm-014 |
| `forecast` | `trend_forecast` | E-pm-020 |
| `cpm` | `cpm_schedule` | E-pm-021 |
| `evm` | `earned_value` | E-pm-022 |
| `leveling` | `resource_leveling` | E-pm-023 |
| `crashing` | `project_crashing` | E-pm-024 |
| `calendar` | `calendar_schedule` | E-pm-025 |
| `multiproject` | `multi_project_schedule` | E-pm-026 |
| `schedrisk` | `schedule_risk` | E-pm-027, E-pm-028 |
| `decisiontree` | `decision_tree` | E-pm-029 |
| `realoption` | `real_option` | E-pm-030 |
| `mcda` | `multi_criteria` | E-pm-031 |
| `montecarlo` | `monte_carlo` | E-pm-032, E-pm-033 |

### Worksheets (6)

| id | template | E-row(s) |
|---|---|---|
| PM-05 | `template_project_charter` | E-pm-046…050, E-pm-053, E-pm-054 |
| PM-09 | `template_wbs` | E-pm-046…052 |
| PM-10 | `template_raci` | E-pm-009, E-pm-046…050, E-pm-055, E-pm-058 |
| PM-06 | `template_risk_register` | E-pm-046…050, E-pm-053, E-pm-055 |
| PM-15 | `template_stakeholder_plan` | E-pm-046…050, E-pm-053 |
| PM-16 | `template_lessons_learned` | E-pm-046…050, E-pm-053 |

### Records (10)

| id | name | E-row(s) |
|---|---|---|
| PM-01 | Balanced Scorecard | E-pm-003, E-pm-008 |
| PM-02 | Strategy Map | E-pm-003, E-pm-008 |
| PM-03 | KPI Tree / Driver Tree | E-pm-003, E-pm-008 |
| PM-04 | Objectives and Key Results (OKRs) | E-pm-003, E-pm-008 |
| PM-07 | Scrum | E-pm-003, E-pm-008 |
| PM-08 | Kanban Method | E-pm-003, E-pm-008 |
| PM-11 | COBIT | E-pm-003, E-pm-008 |
| PM-12 | ITIL | E-pm-003, E-pm-008 |
| PM-13 | DeLone–McLean IS Success Model | E-pm-003, E-pm-008 |
| PM-14 | Technology-Organization-Environment (TOE) Framework | E-pm-003, E-pm-008 |

### Glossary (23)

Every term is asserted for presence and for a definition by `E-pm-004` and
`E-pm-005`; the list is printed from the page so it cannot drift.

| # | term |
|---:|---|
| 1 | Business case |
| 2 | Project charter |
| 3 | Scope |
| 4 | Deliverable |
| 5 | Work breakdown structure (WBS) |
| 6 | Work package |
| 7 | Milestone |
| 8 | Dependency |
| 9 | Critical path |
| 10 | Gantt chart |
| 11 | RACI |
| 12 | Stakeholder |
| 13 | Risk register |
| 14 | Contingency |
| 15 | Baseline |
| 16 | Earned value (PV, EV, AC) |
| 17 | CPI / SPI |
| 18 | Benefits realisation |
| 19 | Lessons learned |
| 20 | PRINCE2 |
| 21 | PMBOK / PMI |
| 22 | Scrum |
| 23 | Kanban |

**Counts asserted:** 18 + 6 + 10 + 23 = **57 items reconciled**, each with at
least one cited E-row; `E-pm-001`…`E-pm-003` assert the counts themselves.

