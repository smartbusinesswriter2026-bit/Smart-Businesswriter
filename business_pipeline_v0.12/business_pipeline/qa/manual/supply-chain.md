# Supply chain & logistics — acceptance manual (session 9)

**Subject:** `supply-chain` · **branch:** `corpus/merge-v1` · **opening commit:** `f699579`,
**rebased onto `2cd3347`** (the Operations session) before this commit.
**Suite at close of baseline:** 3171 tests, 6 failures, 4 errors (946 s) — measured here, not copied.
**Acceptance suite:** `tests/test_subject_supply_chain_acceptance.py` — **62 tests, 62 passed.**

This shelf is the first in the product to own **nothing of its own**. It has no framework
profile with `subject == "supply-chain"`, no `SCL-` catalogue id, and no method that is not
also an Operations method. It re-exports eight Operations compute tools and eleven Operations
worksheets. That is a legitimate design — a shared evidence shelf — and this manual is written
against the shelf's own declared contract:

> "The same evidence tools as Operations, with the inventory and network gaps stated plainly."

Everything below asks the same three questions of that sentence: **is it true, is it complete,
and can a student see it?**

---

## 1. Baseline, measured before any change

| Measure | Documented in the work order | Measured here | Verdict |
|---|---:|---:|---|
| Tests | 3184 | **3171** | the documented count was stale (fixed this session) |
| Failures | 1 known | **6** | 1 known-historical + 5 in flight in other lanes |
| Errors | — | **4** | all four in one shared-worksheet test file |
| Wall time | — | 946 s | — |
| `scripts/econ_shelf.py --check` | in sync | **frozen fixture: in sync** | — |

Raw output: `qa/baseline/scl-before-suite-err.txt`.

### 1.1 Every failure classified

| # | Test | Class | Owner |
|---:|---|---|---|
| 1–4 | `test_operations_frameworks.ExampleTest` ×4 — `KeyError: 'template_sipoc'` from `templates.EXAMPLES` | **KNOWN-HISTORICAL** | shared worksheet test — see D-SCL-03. **Fixed by the Operations session `2cd3347` while this session was in flight** |
| 5 | `test_chat.ResearchTest.test_a_hung_dimension_becomes_a_named_gap_instead_of_blocking` | **NETWORK-ENV** (a hung retrieval no longer reports "timed out") | chat/retrieval lane |
| 6 | `test_docs_sync…test_documented_test_count_matches_the_real_suite` — "HOME.md says 3184, the suite holds 3171" | **NEW-UNEXPLAINED → FIXED here** | this session |
| 7 | `test_paper_documents…test_generating_a_paper_saves_it_to_the_store` — 409 ≠ 200 | **FOREIGN-LANE** (export gate) | paper lane |
| 8 | `test_product_profile_cues…test_every_researched_block_accepts_its_own_query` — `template_balanced_scorecard` | **FOREIGN-LANE** | project-management lane |
| 9 | `test_product_subjects…test_the_rail_carries_the_portfolio_lab_above_the_calculator` | **KNOWN-HISTORICAL** (named in the work order) | rail/UI lane |
| 10 | `test_sources…test_brave_failure_falls_back_to_firecrawl` | **NETWORK-ENV** (named in `docs/OPEN_ISSUES.md`) | retrieval lane |

**0 of the 10 are on this shelf.** No failure names a supply-chain tool, worksheet or record.

---

## 2. The shelf as measured

```
subjects.detail("supply-chain")
  label      Supply chain & logistics
  tools      8      breakeven · multibreakeven · unitecon · forecast ·
                    inventory · queue · capacity · missing
  groups     3      Cost and mix (3) · Demand and planning (2) · Inventory and network (3)
  worksheets 11     OPS-01…08, OPS-10…12 — one not draftable (OPS-03)
  records    9      OPS-09 (computed) + QNT-OPS-01…08 (6 computed, 2 read_only)
  theories   0
  glossary   20     terms, all defined
  catalogue  20     worksheets (11) + records (9); no theory rows
  profiles   0      no framework profile carries subject == "supply-chain"
```

### 2.1 The scope question this session had to settle

**Q1. Are the "gaps stated plainly" actually stated where the student sees them?**

**Yes — declared and visible.** This is the one place the shelf is deliberately *wider* than
Operations, and it is the design working as advertised:

- `QNT-OPS-03` (linear programming, integer optimisation, scheduling and network optimisation)
  and `QNT-OPS-07` (SPC and measurement-system checks) **render on this page** as read-only
  records with `status_short = "Method not built"`. Operations' own definition lists its
  `catalogue_ids` explicitly and **omits both**; supply-chain leaves `catalogue_ids: None`, so
  the two absences fall through from the discipline tags and are shown. That difference is
  measured by `test_E_scl_007` and `test_E_scl_061`.
- The page's `guidance` says the gaps "are stated rather than filled"; its `does_not` list names
  network design, routing, supplier selection, freight/tariff retrieval, disruption,
  multi-echelon inventory and simulation (`test_E_scl_059`, `test_E_scl_060`).
- `docs/CURRICULUM_MAP.md` names location, routing, transport optimisation, multi-echelon
  inventory and supplier risk, and now also names the unbuilt LP/network method (`test_E_scl_062`).

Verdict: **GAP, declared and visible** for both read-only records. No defect.

**Q2. Should the shelf get frameworks of its own?** — proposed, not built. See §3.

**Q3. Is `missing_data_bounds` correctly placed here?** — settled with one line of evidence:

> A demand plan built on a series with missing observations needs a *bounded* answer, and the
> method's own report says so: *"Under the extreme-case convention the complete-data mean lies
> between 12.00 and 14.00. The declared missing-data mechanism is recorded as a declaration, not
> as a verification."* — measured output of the `missing` preset on this page.

That is a demand-planning sentence, not a statistics sentence, so the placement is **defensible
and stays**. The lens that settles it is **the shelf's own declared period for the tool**
(`per observation`, shared with Operations) rather than a subject taxonomy — no owner decision
needed. It is also on Research and Operations; sharing a method across three shelves is the
product's normal pattern, not a duplicate.

### 2.2 The 28-item inventory — the deliverable of this session

`completes a task?` = can a student get a finished artefact from a brief plus evidence.
`draftable` = is there a "draft it for me" button. `gap mode` = what a block or method does
when nothing usable is accepted. Every cell is measured; §4 cites the E-row.

| id | name | kind | completes a task? | unit of analysis | draftable | evidence gate | gap mode | reachable from the page? | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `breakeven` | Break-even point | tool | **yes** | one product line over a period | n/a | declared inputs only; no retrieval | n/a | yes | **WORKS** |
| `multibreakeven` | Multi-product break-even | tool | **yes** | a declared product mix for a period | n/a | declared inputs only | n/a | yes | **WORKS** |
| `unitecon` | Unit economics | tool | **yes** | one customer, one period | n/a | declared inputs only | n/a | yes | **WORKS** |
| `forecast` | Trend forecast | tool | **yes** | one time series | n/a | declared inputs; missing codes declared | listwise exclusion disclosed; mechanism not established | yes | **WORKS** |
| `inventory` | Order quantity and reorder point | tool | **yes** | one item at one location | n/a | declared inputs | safety stock omitted unless level + SD are both declared | yes | **WORKS** |
| `queue` | Queue length and waiting time | tool | **yes** | one service point with *c* servers | n/a | declared inputs | refuses at or above capacity | yes | **WORKS** |
| `capacity` | Capacity and bottleneck | tool | **yes** | one process of named resources | n/a | declared inputs | demand optional; utilisation omitted without it | yes | **WORKS** |
| `missing` | Missing-data bounds | tool | **yes** | one variable's observations | n/a | declared inputs; missing codes declared | bounds only — no imputation | yes | **WORKS** |
| `OPS-01` | SCOR supply-chain map | worksheet | **yes** — needs the student's own six process cells | the supply chain of the declared unit | yes | research, then the student's words | named gap, disclosed | yes | **WORKS** |
| `OPS-02` | SIPOC process map | worksheet | **yes** — verified end to end (§7) | one bounded process | yes | suppliers/inputs researched; steps, outputs, customers quoted from the brief | named gap, disclosed | yes | **WORKS** |
| `OPS-03` | Value stream map | worksheet | **no** — no drafting button | one value stream | **no** | — | named gap | yes | **GAP, declared and visible** (D-SCL-02) |
| `OPS-04` | 5S workplace audit | worksheet | **yes** — needs the student's own five cells | one workplace | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-05` | A3 problem solving | worksheet | **yes** | one problem on one process | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-06` | Theory of Constraints: five focusing steps | worksheet | **yes** | one constraint | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-07` | Root cause analysis (5 Whys / fishbone) | worksheet | **yes** | one problem | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-08` | Failure mode and effects analysis | worksheet | **yes** | one process or design | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-10` | Kraljic purchasing portfolio | worksheet | **yes** | the purchased item portfolio | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-11` | Sales and operations plan | worksheet | **yes** | one planning period | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-12` | PDCA improvement cycle | worksheet | **yes** | one improvement cycle | yes | research, then the student's words | named gap | yes | **WORKS** |
| `OPS-09` | Statistical Process Control | record (`computed`) | **no, not from this page** — links `process_control`, no tile here | one process | n/a | the method's own gate | the method's own refusal | **no tile** | **GAP, declared and visible** (G-scl-01) |
| `QNT-OPS-01` | EOQ, reorder point, safety stock, service level | record (`computed`) | **yes** — tile `inventory` | one item at one location | n/a | declared inputs | method refusal | yes | **WORKS** |
| `QNT-OPS-02` | Demand / lead-time forecasts | record (`computed`) | **yes** — tile `forecast` | one series | n/a | declared inputs | method refusal | yes | **WORKS** |
| `QNT-OPS-03` | LP, integer optimisation, scheduling, network optimisation | record (`read_only`) | **no** — nothing built | — | n/a | — | read-only | yes (read and cite) | **READ-ONLY, correct as declared** |
| `QNT-OPS-04` | Queueing, throughput, utilisation, capacity | record (`computed`) | **yes** — tiles `queue`, `capacity` | one service point / one process | n/a | declared inputs | method refusal | yes | **WORKS** |
| `QNT-OPS-05` | CPM, PERT, schedule risk | record (`computed`) | **no, not from this page** — links `cpm_schedule`, no tile here | one project network | n/a | declared inputs | method refusal | **no tile** | **GAP, declared and visible** (G-scl-01) |
| `QNT-OPS-06` | OEE, process capability, control charts | record (`computed`) | **no, not from this page** — links `oee_analysis`, `process_control`, no tiles here | one machine / one process | n/a | declared inputs | method refusal | **no tile** | **GAP, declared and visible** (G-scl-01) |
| `QNT-OPS-07` | SPC and measurement-system checks | record (`read_only`) | **no** — nothing built | — | n/a | — | read-only | yes (read and cite) | **READ-ONLY, correct as declared** |
| `QNT-OPS-08` | Throughput and constraint analysis | record (`computed`) | **yes** — tiles `capacity`, `queue` | one process | n/a | declared inputs | method refusal | yes | **WORKS** |

**Measured counts:** **22 of 28** items do something a student can finish from this page
(8 tools + 10 draftable worksheets + 4 computed records whose method has a tile); **2** are
read-only as declared (`QNT-OPS-03`, `QNT-OPS-07`); **3** computed records link a method this
page cannot launch (G-scl-01); **1** worksheet has no drafting button (D-SCL-02).
22 + 2 + 3 + 1 = 28. All 28 rows render on the page.

**The one finding the work order did not predict.** The page carries eight tools but nine
records, and three of those records (`OPS-09`, `QNT-OPS-05`, `QNT-OPS-06`) point at methods —
`process_control`, `cpm_schedule`, `oee_analysis` — that have **no tile on this shelf**. A
logistics student reading "SPC — Computed" on this page cannot compute it here. The record is
honest (it does not claim a worksheet) but the page promises a computation it cannot start.
That is G-scl-01, and it is a *presentation* gap: the fix is either three more tiles or a
one-line "available on the Operations shelf" note on those rows. Nothing is built here.

---

## 3. Proposal — frameworks this shelf should have of its own (owner-gated)

**This is a NEW PROFILE set: propose only, nothing built** (work order §9). Every candidate
below is a structure-and-evidence worksheet the existing machinery can already carry: the same
`framework_profiles` block shapes (`research` / `quote` / `auto` / `gap`), the same T4 matrix or
canvas renderer, the same named-gap wording. None needs a new renderer, a new method or a new
route. Ranked by what closes the largest gap for the least new machinery.

| rank | candidate | proposed form | why it earns its place | status |
|---:|---|---|---|---|
| 1 | **Safety-stock and service-level policy** | `matrix` — item × {service level, demand SD, lead time, safety stock, reorder point, policy} | the one calculation this shelf already runs (`inventory_policy`) has no worksheet around it, so the *policy* — the sentence a planner actually writes — is the missing artefact; the arithmetic is already frozen and tested | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 2 | **ABC–XYZ classification** | `matrix` — SKU × {value share, volume share, variability, class} | every logistics course assigns it; it is a ranking with a declared threshold, so it needs no new method and no score | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 3 | **Supplier scorecard / vendor rating** | `matrix` — supplier × {criterion, weight, rating, evidence, verdict} | the shelf's `does_not` says it "does not select a supplier"; a scorecard is the structure that makes the *student's* selection auditable without the product recommending anyone | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 4 | **Bullwhip / demand amplification** | `canvas` — the amplification chain, the declared causes, the evidence per tier | names the single most-taught supply-chain phenomenon the shelf cannot currently discuss; purely structural, no computation | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 5 | **Network design (location–allocation)** | `matrix` — candidate site × {fixed cost, capacity, transport cost, service, decision} | the declared headline gap; a worksheet can structure the *evidence* for a location decision without pretending to solve the optimisation — but it must say so in the same breath | **SHOULD BECOME A WORKSHEET — needs owner approval**, lowest rank because it flirts with the thing the shelf refuses to do |
| 6 | **Reverse logistics and returns** | `canvas` — return reason, route, disposition, cost bearer, evidence | a real gap and a real assignment topic, but the least connected to the existing toolset | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 7 | **Incoterms and customs handover** | `matrix` — term × {seller obligation, buyer obligation, risk transfer point, cost bearer} | pure reference structure with no evidence gate; high value for a trade-logistics course, but it is a lookup table rather than an analysis | **SHOULD BECOME A WORKSHEET — needs owner approval** |

**What is deliberately *not* proposed.** No routing or transport-optimisation worksheet and no
multi-echelon inventory worksheet. Both would need a solver the frozen core does not have, and a
worksheet that structures evidence for an optimisation it cannot perform would be the exact
dishonesty the shelf's `does_not` list exists to prevent. They stay named gaps.

**Also owner-gated and *not* built:** the two unit corrections in §5 (D-SCL-01) and the
`OPS-03` wording in D-SCL-02. Both are one-line changes in `src/bp/methods.py` / the catalogue
row, and the work order puts both behind §9.

---

## 4. Acceptance rows (E-scl-001 … E-scl-062)

One row per test in `tests/test_subject_supply_chain_acceptance.py`. **62 tests, one per row.**

### 4.1 Inventory and page (E-scl-001 … 012)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-001 | the page offers the eight declared calculators, in order | `test_E_scl_001` | PASS |
| E-scl-002 | three groups in the declared order, with 3 / 2 / 3 members | `test_E_scl_002` | PASS |
| E-scl-003 | every tool carries formula, steps, common mistakes, level, period, related | `test_E_scl_003` | PASS |
| E-scl-004 | eleven worksheets, all `OPS-` ids, every template in `T.TEMPLATES` | `test_E_scl_004` | PASS |
| E-scl-005 | exactly one worksheet is not draftable, and it is `OPS-03` | `test_E_scl_005` | PASS |
| E-scl-006 | the not-draftable tile's measured pair (draftable False / "worksheet available") | `test_E_scl_006` | PASS — **pins D-SCL-02** |
| E-scl-007 | nine records, two read-only (`QNT-OPS-03`, `QNT-OPS-07`), all type Q | `test_E_scl_007` | PASS |
| E-scl-008 | every computed record links a method that exists in `LIBRARY` | `test_E_scl_008` | PASS |
| E-scl-009 | no record masquerades as a calculator | `test_E_scl_009` | PASS |
| E-scl-010 | the glossary carries 20 terms, each with a real definition | `test_E_scl_010` | PASS |
| E-scl-011 | worksheets + records + theories partition the 20 catalogue rows | `test_E_scl_011` | PASS |
| E-scl-012 | the page states the contract it is judged against | `test_E_scl_012` | PASS |

### 4.2 Contract (E-scl-013 … 019)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-013 | use, unsupported use, assumptions and limitations all declared | `test_E_scl_013` | PASS |
| E-scl-014 | ≥3 named checks, and the names that run are the names declared | `test_E_scl_014` | PASS |
| E-scl-015 | tier T1, a metric, a unit, a valid claim ceiling | `test_E_scl_015` | PASS |
| E-scl-016 | every input declares a type and a description | `test_E_scl_016` | PASS |
| E-scl-017 | every tool has a server preset for the same method | `test_E_scl_017` | PASS |
| E-scl-018 | every tool declares the period its inputs are read in | `test_E_scl_018` | PASS |
| E-scl-019 | every output has a declared unit and an integer precision | `test_E_scl_019` | PASS |

### 4.3 Numbers — every calculator recomputed independently (E-scl-020 … 036)

Each row names the recomputation: a second formula written in the test, or hand arithmetic.

| id | calculator | independent recomputation | status |
|---|---|---|---|
| E-scl-020 | `breakeven` | CM = p − v = 10; units = F/CM = 100; revenue = units × p = 2,000 | PASS |
| E-scl-021 | `multi_product_breakeven` | weighted CM = (3·3 + 1·3)/4 = 3; batches = 6,000/12 = 500; units 2,000; revenue 10,500 | PASS |
| E-scl-022 | `multi_product_breakeven` | the fixed cost is covered exactly once (1,500·3 + 500·3 = 6,000); one batch short falls short | PASS |
| E-scl-023 | `unit_economics` | margin 49 − 12 = 37; payback 80/37 = 2.162162; LTV 37/0.04 = 925; LTV/CAC 11.5625 | PASS |
| E-scl-024 | `unit_economics` | churn is a **period** rate: LTV = margin/churn for three rates; 6 and 0 refused | PASS |
| E-scl-025 | `trend_forecast` | OLS slope/intercept fitted in the test (1.003497, 9.060606) | PASS |
| E-scl-026 | `trend_forecast` | forecastₖ = a + b·(n+k) for every k in the horizon; intervals ordered | PASS |
| E-scl-027 | `trend_forecast` | holdout MAE recomputed from a fit on the first n−3 points → 1.133333 | PASS |
| E-scl-028 | `missing_data_bounds` | bounds are the extreme cases: (52 + 2·10)/6 = 12 and (52 + 2·16)/6 = 14 | PASS |
| E-scl-029 | `missing_data_bounds` | no imputation anywhere: no `mean_complete`, no filled observation, bounds bracket the observed mean | PASS |
| E-scl-030 | `inventory_policy` | EOQ = √(2DS/H) = 632.455532; orders 18.973666; cycle stock 316.227766 | PASS |
| E-scl-031 | `inventory_policy` | z = Φ⁻¹(0.95) by bisection on erf → 1.6448536; SS = z·σ·√L = 104.029677; ROP = d·L + SS = 432.796801 | PASS |
| E-scl-032 | `inventory_policy` | days-vs-periods: 365 → d = 32.876712; 250 → d = 48.0; ROP moves, EOQ does not | PASS |
| E-scl-033 | `queue_analysis` | M/M/1: ρ = 0.75, Lq = 2.25, L = 3.00, Wq = 0.125, W = 0.166667, P₀ = 0.25 | PASS |
| E-scl-034 | `queue_analysis` | Erlang C written out (P₀, C, Lq, Wq, L, W) at c = 2; c = 1 reduces to M/M/1 | PASS |
| E-scl-035 | `capacity_analysis` | capacities 96/60/160; bottleneck 60 at index 2; throughput ≠ sum (316); util 0.8333; gap 10 | PASS |
| E-scl-036 | `capacity_analysis` | implied cycle time 8·60/60 = 8 minutes a unit | PASS |

### 4.4 The unit audit (E-scl-037 … 039)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-037 | every declared unit is in the engine's vocabulary; precision ≤ 6 | `test_E_scl_037` | PASS |
| E-scl-038 | the unit contradictions are **exactly** the three measured ones | `test_E_scl_038` | PASS — **pins D-SCL-01** |
| E-scl-039 | the units that are right stay right (days, rate, units, currency, ratio, periods, probability, count) | `test_E_scl_039` | PASS |

### 4.5 Boundaries and refusals (E-scl-040 … 050)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-040 | zero and negative refused where undefined; zero fixed cost defined and returns zero | `test_E_scl_040` | PASS |
| E-scl-041 | an empty list refused by validation *and* by the method | `test_E_scl_041` | PASS |
| E-scl-042 | a single element is defined (bounds, one resource) or refused with a reason (forecast) | `test_E_scl_042` | PASS |
| E-scl-043 | all-equal values give a zero-width bound; a constant series is refused | `test_E_scl_043` | PASS |
| E-scl-044 | duplicates are counted, not collapsed | `test_E_scl_044` | PASS |
| E-scl-045 | very large values stay exact (1.2 × 10¹² fixed cost → 1.2 × 10⁶ units) | `test_E_scl_045` | PASS |
| E-scl-046 | `"1,200,000"` is refused **by name** — `'fixed' … not a valid number` | `test_E_scl_046` | PASS |
| E-scl-047 | a rate entered as `6` is refused, never rescaled | `test_E_scl_047` | PASS |
| E-scl-048 | a period mismatch is taken as given and disclosed by the caveat | `test_E_scl_048` | PASS — GAP, declared |
| E-scl-049 | a currency label changes no number (identical hash under PHP and USD) | `test_E_scl_049` | PASS |
| E-scl-050 | unknown method / unknown input / wrong type → actionable block, no traceback | `test_E_scl_050` | PASS |

### 4.6 Parity with the Operations shelf (E-scl-051 … 053)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-051 | the eight tools are declared on both shelves with the same method and preset | `test_E_scl_051` | PASS |
| E-scl-052 | the period metadata is identical on both shelves | `test_E_scl_052` | PASS |
| E-scl-053 | the same preset returns an identical `reperform` block, hash, checks, limitations, assumptions and report | `test_E_scl_053` | PASS |

**Measured parity, all eight tools.** `outputs_hash` is identical across the two shelves for every
tool, and `reperform`, `tests`, `limitations`, `assumptions`, `spec_hash` and `report` are
byte-identical. The only per-run difference is `run_id` (a fresh UUID), which is why the test
compares the reproducible half of the appendix rather than the whole dict.

### 4.7 Delivery, determinism and disclosure (E-scl-054 … 058)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-054 | every preset delivers, every check passes, no unresolved token, complete appendix, 0 amendments | `test_E_scl_054` | PASS |
| E-scl-055 | the same inputs twice give the same outputs, hash and report | `test_E_scl_055` | PASS |
| E-scl-056 | the appendix survives a JSON round trip unchanged | `test_E_scl_056` | PASS |
| E-scl-057 | a refusal is a refusal, not a zero: no `reperform`, no report | `test_E_scl_057` | PASS |
| E-scl-058 | the disclosure names what was not done (mechanism not established, no imputation, one item only, no priorities) | `test_E_scl_058` | PASS |

### 4.8 Page and guide (E-scl-059 … 062)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-scl-059 | the guidance names the network, routing and gap language | `test_E_scl_059` | PASS |
| E-scl-060 | `does_not` names network design, routing, multi-echelon and supplier selection | `test_E_scl_060` | PASS |
| E-scl-061 | both read-only records are reachable from the page | `test_E_scl_061` | PASS |
| E-scl-062 | `docs/CURRICULUM_MAP.md` names the eleven worksheets and the five named gaps | `test_E_scl_062` | PASS — **fixed this session** |

### 4.9 Strict reconciliation — every item, one cited E-row

**Tools (8)** — `breakeven` E-020 · `multibreakeven` E-021, E-022 · `unitecon` E-023, E-024 ·
`forecast` E-025, E-026, E-027 · `inventory` E-030, E-031, E-032 · `queue` E-033, E-034 ·
`capacity` E-035, E-036 · `missing` E-028, E-029.

**Worksheets (11)** — `OPS-01`…`OPS-08`, `OPS-10`…`OPS-12`: all eleven by E-004 (the set and the
templates), E-005 and E-006 (`OPS-03` alone is not draftable), E-053 (the shared-paper parity).

**Records (9)** — `OPS-09` E-007, E-008, E-009 · `QNT-OPS-01` E-007, E-008 · `QNT-OPS-02` E-007,
E-008 · `QNT-OPS-03` E-007, E-009, E-061 · `QNT-OPS-04` E-007, E-008 · `QNT-OPS-05` E-007, E-008 ·
`QNT-OPS-06` E-007, E-008 · `QNT-OPS-07` E-007, E-009, E-061 · `QNT-OPS-08` E-007, E-008.

**Glossary (20 terms)** — E-010 asserts all twenty carry a term and a definition of real length.

---

## 5. The unit audit — every output's declared unit and precision

`method.typing(key)` for every output of all eight methods, at the preset inputs.

| tool | output | unit | prec. | name agrees with unit? |
|---|---|---|---|---|
| `breakeven` | `breakeven_units` | units | 2 | yes |
| | `breakeven_revenue`, `contribution_margin` | currency | 2 | yes |
| | `contribution_margin_ratio` | ratio | 4 | yes |
| `multi_product_breakeven` | `breakeven_total_units`, `units_coffee`, `units_cake`, `total_mix_units` | units | 2 | yes |
| | `breakeven_revenue`, `fixed_costs`, `weighted_contribution` | currency | 2 | yes |
| `unit_economics` | `unit_margin`, `ltv`, `price`, `variable_cost`, `acquisition_cost` | currency | 2 | yes |
| | `margin_pct`, `ltv_cac` | ratio | 4 / 2 | yes |
| | `payback_periods` | periods | 2 | yes |
| | `churn_rate` | rate | 4 | yes |
| `trend_forecast` | `slope`, `intercept`, `forecast_1..3`, `mae_holdout`, `residual_se`, `ci_lower_*`, `ci_upper_*` | `@unit` (from the request) | 3 | yes |
| | `r_squared` | ratio | 3 | yes |
| | `p_slope` | probability | 4 | yes |
| | `coverage_holdout` | rate | 2 | yes |
| | `n_fitted`, `n_holdout`, `n_excluded`, `horizon` | count | 0 | yes |
| `inventory_policy` | `economic_order_quantity`, `cycle_stock`, `safety_stock`, `reorder_point`, `average_inventory`, `annual_demand`, `daily_demand`, `daily_demand_sd` | units | 2 | yes |
| | `annual_holding_cost`, `annual_ordering_cost`, `total_annual_cost`, `order_cost`, `holding_cost_per_unit` | currency | 2 | yes |
| | `lead_time_days` | days | 2 | yes |
| | `service_level` | rate | 4 | yes |
| | `safety_factor` | ratio | 4 | yes |
| | `orders_per_year` | units | 2 | **mild** — a count of orders typed "units" |
| | **`days_per_year`** | **currency** | 2 | **NO — BLOCKER class (D-SCL-01)** |
| `queue_analysis` | `utilisation`, `offered_load`, `probability_empty`, `probability_waiting` | ratio | 4 | yes |
| | `average_wait_in_queue`, `average_time_in_system` | periods | 4 | yes |
| | `arrival_rate`, `service_rate`, `servers` | count | 4 | mild — a rate typed as a count |
| | **`average_in_queue`** | **ratio** | 4 | **NO — a customer count typed a ratio (D-SCL-01)** |
| | **`average_in_system`** | **ratio** | 4 | **NO — a customer count typed a ratio (D-SCL-01)** |
| `capacity_analysis` | `capacity_1..3`, `max_output`, `capacity_gap`, `demand` | units | 2 | yes |
| | `utilisation_1..3`, `bottleneck_utilisation` | ratio | 4 | yes |
| | `bottleneck_index` | count | 0 | yes |
| `missing_data_bounds` | `bound_low`, `bound_high`, `bound_width`, `mean_observed` | `@unit` | 2 | yes |
| | `pct_missing` | probability | 4 | yes |
| | `n_valid`, `n_missing` | count | 0 | yes |

### 5.1 The contradiction that reaches a student's paper

`queue_analysis.average_wait_in_queue` is typed **`periods`**, and `periods` is **not** in the
currency-exempt list at `src/bp/orchestrator.py:235`. The delivered report therefore reads:

> "…with 2.2500 customers waiting on average and a wait of **PHP 0.1250 periods**."

A waiting time in periods is printed with a money prefix. That is the B-190 family: a declared
unit that contradicts the value and reaches the export. `days_per_year` (typed currency) is the
same class and would print `PHP 365.00` wherever that figure is rendered through
`Quantity.display()`.

**All three live in `src/bp/methods.py` / `src/bp/orchestrator.py` — the core.** The work order
puts a core change behind §9, so **nothing is changed here**. `test_E_scl_038` pins the exact
measured set so the fix cannot land silently.

---

## 6. Parity — the same method on two shelves

The parity test is `Parity` (§4.6). Measured result for all eight tools:

| tool | method | preset | period (both shelves) | `outputs_hash` identical | appendix identical |
|---|---|---|---|---|---|
| `breakeven` | `breakeven` | `breakeven` | per period | yes | yes |
| `multibreakeven` | `multi_product_breakeven` | `multibreakeven` | per period | yes | yes |
| `unitecon` | `unit_economics` | `unitecon` | per period | yes | yes |
| `forecast` | `trend_forecast` | `forecast` | per period | yes | yes |
| `inventory` | `inventory_policy` | `inventory` | annual | yes | yes |
| `queue` | `queue_analysis` | `queue` | per period | yes | yes |
| `capacity` | `capacity_analysis` | `capacity` | per period | yes | yes |
| `missing` | `missing_data_bounds` | `missing` | per observation | yes | yes |

**The two shelves are not lying about what they run.** They differ in exactly three ways, all
declared: the group labels, the tool set (Operations has six more tools), and the record list
(supply-chain shows the two read-only quantitative rows that Operations omits).

---

## 7. One worksheet paper, read against V-01 … V-20

**Produced through the real path**, not a fixture:
`completion.complete("template_sipoc", brief, industry=…, unit_value=…, student_items=…)` →
`completion.draft_bytes(result)` → **29,423-byte `.docx`**, 54 paragraphs, 1,519 words, and a
**grid** (the Operations session's `2d454ae` closed G-ops-01 for the eleven worksheet papers).
Retrieval was mocked with one citable record (`Lovelace, 2024`), as §8 of the harness requires.
Artifacts: `qa/evidence/supply-chain/sipoc-paper.docx` and `sipoc-paper.txt` (the stripped XML).

**This paper was re-produced twice**, because two lanes changed the drafting layer underneath it
(`2cd3347` and `2d454ae`). The reading below is of the **final** paper. Two findings the first
reading produced are now fixed by that work, and the grid the last commit added is the reason the
word count and the figure bullet are different — recorded rather than quietly dropped.

Case: *"A regional grocery distributor moves 4,000 pallets a month through one warehouse into
180 stores… the depot manager must show where the process loses time and stock before the peak
season."* The student supplied the same one-paragraph process description for every block, which
is the harshest honest input: it tests whether the machinery says something true when the input
is thin.

| rule | verdict | where, and what was seen |
|---|---|---|
| V-01 no invented evidence | **PASS with a finding** | one citation in the body (H2 Inputs); the four other parts carry the student's own words uncited, which is correct. **Finding:** the general sentences at H2 Suppliers / Inputs / Process Steps / Outputs / Customers are uncited framework commentary — declared as background, not as evidence |
| V-02 gaps named, never filled | **not exercised** | every part carried an item; 0 named gaps |
| V-03 student inputs stay student inputs | **PASS** | 5 of 6 items are `provenance: student` and appear as the student's own text |
| V-04 no silent substitution | **n/a** | the brief named no framework; SIPOC was chosen on the page |
| V-05 computations from the frozen core | **n/a** | the paper carries no computation |
| V-06 no instructions or template text | **PASS** | no `(your analysis)`, no "Not supplied yet", no template name, no placeholder |
| V-07 export blocked when incomplete | **PASS** | `draft_bytes` ran only after `completion.missing(result) == []` |
| V-08 model does not research | **PASS** | the draft is deterministic; no model was called |
| V-09 no heading jump | **PASS** | H1 → H2 → H1 throughout; no H2 before the first H1 |
| V-10 Conclusion present | **PASS** | "Conclusion" at the end, before References |
| V-11 reference list present | **PASS** | one entry, APA form |
| V-12 every dimension sourced **or** a named gap | **DISPUTED — see §7.1** | 1 sourced item, 4 student items, 0 named gaps |
| V-13 every reference cited | **PASS** | the one reference is cited, and **once**: "(Lovelace, 2024)" at H2 Inputs. The first reading found it printed twice; that was D-SCL-04 and the Operations session fixed it (`2cd3347`) |
| V-14 Introduction states the decision and the thesis | **PASS, weak** | the thesis is stated; the decision is named generically as "the course of action set out in the brief" rather than the depot's actual decision |
| V-15 Conclusion answers the thesis | **PASS** | it returns to the same proposition and introduces no new evidence |
| V-16 Discussion integrates | **PASS** | it reads the parts together instead of repeating them |
| V-17 no claim above the ceiling | **PASS** | the export gate's `claim_problems` was empty |
| V-18 combined papers name the origin | **n/a** | not a combined paper |
| V-19 word count inside the band | **PASS** | 1,519 words against a mid band of 1,200–2,500 |
| V-20 no placeholder name; byline on the title page | **PARTIAL** | no placeholder name — and no byline at all; the title page carries title and date only |

### 7.1 The one DISPUTED row, and why

**V-12.** The rule reads "every dimension has a sourced item **or** a named gap". In this paper
five dimensions each carry an item, but only one item is *sourced*; four are the student's own
words. So:

- if "sourced" means "retrieved from an external source", **V-12 fails at H2 Suppliers, H2 Process
  Steps, H2 Outputs and H2 Customers**;
- if student-supplied evidence counts as evidence, V-12 passes and the paper is complete.

The product's own position is the second: `completion.missing()` treats a block with items as
filled regardless of provenance, and `CONDUCTOR_MANUAL.md` §4.3 makes the student's inputs
authoritative. This session does not overrule that — it records that the *rule text* and the
*implementation* mean different things, so a later harness that enforces V-12 literally will fail
papers the product considers complete. **DISPUTED, needs the owner's reading of "sourced".**
Nothing is changed.

### 7.2 The presentation defects the reading found

- **D-SCL-04 (MINOR, presentation) — FIXED by the Operations session `2cd3347`.** The first
  reading of the paper found one sourced item printing its in-text citation twice:
  *"…(Lovelace, 2024) (Lovelace, 2024)"* at H2 Inputs. The Operations session found the same
  defect on its own shelf (D-OPS-04) and repaired `completion._sections`. The re-produced paper
  cites once, which is why V-13 is a plain PASS above.
- **D-SCL-05 (MINOR, presentation) — still open.** No byline block on the title page. V-20 is
  `partial` in the registry for exactly this reason; the paper does not invent a name, which is
  correct, but a student has nowhere to put their own.

---

## 8. The defect ledger for this shelf

| id | severity | class | what was measured | owner | status |
|---|---|---|---|---|---|
| **D-SCL-01** | **BLOCKER** | UNIT | `inventory_policy.days_per_year` → `("currency", 2)`; `queue_analysis.average_in_queue` and `average_in_system` → `("ratio", 4)`. The queue report prints **"a wait of PHP 0.1250 periods"**. `_inventory_typing` / `_queue_typing` in `src/bp/methods.py` fall through to a default; `periods` is also missing from the currency-exempt list at `src/bp/orchestrator.py:235` | core — **owner-gated (§9)** | **LEDGERED, not fixed.** Pinned by `test_E_scl_038` |
| **D-SCL-02** | MINOR | DECLARATION | `OPS-03` carries `draftable: False` while its catalogue row still reads "worksheet available: structure and evidence audit only"; nothing on the page says why the button is absent | presentation — this shelf's, but the row is shared with Operations | **LEDGERED, not fixed.** Pinned by `test_E_scl_006` |
| **D-SCL-03** | MINOR | TEST FIXTURE | four `test_operations_frameworks.ExampleTest` errors: `KeyError: 'template_sipoc'` from `templates.EXAMPLES` | **Operations session 8 (`2cd3347`)** — eleven worked examples added to `src/bp/templates.py` | **FIXED by the other lane mid-session** |
| **D-SCL-04** | MINOR | PRESENTATION | one sourced item rendered two identical in-text citations at H2 Inputs | **Operations session 8 (`2cd3347`)** — `completion._sections` repaired | **FIXED by the other lane mid-session** |
| **D-SCL-05** | MINOR | PRESENTATION | no byline block on the title page (V-20 partial) | shared drafting layer | **LEDGERED, not fixed** |
| **D-SCL-06** | MINOR | DOC-DRIFT | `docs/HANDOFF.md` cites `B-180a` and `B-180b`, which have no row in `docs/DECISIONS.md`, so `test_docs_sync` fails on the remote tip | either add the two decision rows or drop the references | **Operations lane** (present at `2d454ae` before this commit) | `test_every_mentioned_decision_id_has_a_row_in_the_decision_log` | **LEDGERED to the other lane** |
| **G-scl-01** | GAP | REACHABILITY | `OPS-09`, `QNT-OPS-05`, `QNT-OPS-06` are `computed` records whose methods (`process_control`, `cpm_schedule`, `oee_analysis`) have **no tile on this page** | presentation — a note or three tiles | **GAP, declared and visible** |
| **G-scl-02** | GAP | PERIOD | a monthly demand with a daily lead time is accepted as given and disclosed by the caveat, not converted | declared convention | **GAP, declared** |
| **G-scl-03** | GAP | RATE | a service level entered as `6` is refused (correct); a rate entered as a plausible-but-wrong decimal is taken as given and the disclosure layer flags any rate above 100% | declared | **GAP, declared** |
| **G-scl-04** | GAP | SUBJECT FIELD | all eleven profiles served here declare `subject: "operations"`, and **0** profiles declare `subject: "supply-chain"`. Any subject-keyed report files these papers under Operations; the harness files shared papers under both (§7.1 of the harness doc) | crosswalk — harness's own file | **GAP, declared** |
| **G-scl-05** | GAP | V-12 | the rule text says "sourced", the implementation counts any item | **owner's reading needed** | **DISPUTED** |

**Zero unexplained BLOCKER/MAJOR.** D-SCL-01 is a BLOCKER *class* finding, fully explained and
owner-gated; the rest are MINOR or declared gaps.

---

## 9. Gates at close

| gate | result |
|---|---|
| `tests/test_subject_supply_chain_acceptance.py` | **62 tests, 62 passed, 0 skipped** |
| shelf acceptance + `test_frozen_contract` | **green** (62 + frozen-contract tests passed) |
| Full suite before (opening tree `f699579`) | **3171 tests, 6 failures, 4 errors** (`qa/baseline/scl-before-suite-err.txt`) |
| Full suite after (pre-rebase tree) | **3227 tests, 4 failures, 4 errors** (944 s, `qa/baseline/scl-after-suite-err.txt`) — **0 new**, 56 added |
| Rebased onto `2cd3347` | the suite then held **3293 tests** (measured with `test_docs_sync._suite_count()`); the shelf suite was re-run green on that tree and the documents were set to 3293 |
| **Full suite, measured on `2cd3347` + an earlier version of this commit** | **3287 tests, 4 failures, 0 errors** (1108 s, `qa/baseline/scl-final-suite-err.txt`) — **0 new, 0 errors**. **Disclosed:** that run collected only **56** of this module's tests. Six (E-scl-007 … 012) had been appended after the `if __name__ == "__main__":` guard and never ran; an audit of defined-vs-collected ids found them, they were moved into the `Inventory` class, and the module now reports **62 tests, 62 passed**. The six are page/record/glossary assertions with no numeric content, so the failure count is unaffected — but the "0 new" claim was measured with them absent and is stated here as such |
| The tree then moved twice more (`d64cd0c`, `2d454ae`) | the suite count is now **3293** (re-measured with `_suite_count()`: 3231 upstream + 62 here); the same four failures remain, and the Operations lane's last commits add **one** more — D-SCL-06 (`B-180a`/`B-180b` in `HANDOFF.md` with no `DECISIONS.md` row), verified by running `tests.test_docs_sync` on this tree (7 tests, 6 passed). **Five problems, one of them theirs, none on this shelf** |
| `scripts/econ_shelf.py --check` | **frozen fixture: in sync** |
| `python -m unittest tests.test_docs_sync` | **7 tests, 6 passed, 1 failure** — the count assertion passes; `test_every_mentioned_decision_id_has_a_row_in_the_decision_log` fails because `docs/HANDOFF.md` cites **B-180a** and **B-180b**, which have no row in `docs/DECISIONS.md`. That text is on the **remote tip before this commit** (measured: present at `2d454ae`, absent from its `DECISIONS.md`), so it is the Operations lane's; ledgered as D-SCL-06 rather than silently deleted |
| `tests/test_frozen_contract.py` | **passed** — no core change was made |
| `tests/test_operations_frameworks.py` | **green after `2cd3347`** — the four errors this session measured in its baseline are D-SCL-03 and the Operations lane fixed them |
| `qa/check_page_syntax.py` | **page syntax: OK** (`qa/baseline/scl-page-syntax.txt`) |

**What moved between the three runs, measured.** The ten baseline problems became four, and none of
the six that went is a coincidence:

- the four `test_operations_frameworks.ExampleTest` **errors** went when the Operations session
  added the eleven worked examples (`2cd3347`) — D-SCL-03;
- `test_docs_sync…test_documented_test_count_matches_the_real_suite` went when the documented
  count was corrected in this session;
- `test_sources…test_brave_failure_falls_back_to_firecrawl` is the network-dependent test
  `docs/OPEN_ISSUES.md` already names; it passed on two runs and failed on one, which is exactly
  what a NETWORK-ENV classification predicts.

The four that remain — a hung retrieval dimension, the paper store route, a balanced-scorecard
profile cue, and the known rail test — are unchanged and none is on this shelf.

---

## 10. UI/UX verdict, and what was not done

| surface | verdict | evidence |
|---|---|---|
| The shelf page (`subjects.detail("supply-chain")`) | **PASS by contract** — 8 tools in three declared groups, 11 worksheets, 9 records, 20 glossary terms, the not-draftable tile present, the guidance and `does_not` naming the gaps | E-001 … E-012, E-059 … E-061 |
| The tool form | **PASS by contract** — every input declares a type and a description (E-016), so the form has the framework's own vocabulary and no `field`/`dimension_1` placeholder | E-016 |
| The drafting form | **PASS by contract** — `completion.missing()` names exactly the blocks that still block a paper, and `draft_bytes` refuses until it is empty | E-054, §7 |
| The finished paper | **PASS with findings** — §7 above; two presentation defects (D-SCL-04, D-SCL-05) | `qa/evidence/supply-chain/sipoc-paper.*` |
| Figures at the method's declared precision | **PASS with one exception** — the product formats from `method.typing` and never recomputes; the exception is D-SCL-01 | E-019, E-037 … E-039, §5 |

**What this session did NOT do, and says so plainly:**

- **No live click-through on port 8001 and no screenshots.** The work order's U7 asks for a live
  pass with a screenshot per surface under `qa/evidence/supply-chain/`. That was not run: this
  session worked in a second checkout of the same repository (`scl-work`) while another lane held
  the primary worktree, and starting a server is a live-state action the work order reserves.
  The evidence here is the Python contract tests over the served data plus the produced `.docx`,
  which is U7's first layer only. **This is the largest gap in this session's definition of done
  and is recorded as such rather than glossed.**
- **No `node --check` gate** for the same reason: no page script was changed by this session.

---

## 11. Lane discipline

- Every commit is path-scoped: `git commit -F msg.txt -- <explicit paths>`. No `git add -A`, no
  `git add qa`, no `git clean`.
- `git diff --cached --name-only` was printed before every commit; every path is this session's.
- No file under `qa/baseline/` was deleted; the two new baseline files are additions.
- No scratch script was left under `qa/` that mutates `src/`. The probes live outside the
  repository, in the session's scratch directory, and are not committed.
- **`docs/sources/**` and `tests/fixtures/frozen_contract.json` were not touched.**

---

## 12. Residual risk — the three things most likely to bite next

1. **D-SCL-01 is still live.** A logistics student can export a paper containing
   "a wait of PHP 0.1250 periods" today. It is one fall-through branch in `_queue_typing` and one
   missing word in the orchestrator's exempt list, but it is core and it is owner-gated. Until it
   is fixed, `test_E_scl_038` will keep asserting the wrong units *on purpose* — a future reader
   must not mistake that for approval.
2. **G-scl-01 is a promise the page cannot keep.** Three records say "Computed" on a page with no
   tile for their method. A student who clicks expecting a calculator finds nothing.
3. **The shared-shelf test that could not run is now repaired — by the other lane.** The four
   `test_operations_frameworks.ExampleTest` errors (D-SCL-03) were fixed in `2cd3347` while this
   session was in flight. The lesson is the one the work order repeats: a second lane is live, and
   a finding can be closed underneath you between measurement and commit.

**Next subject.** `docs/QA_STATE.md` names the shelf after this one. This session's
recommendation, on the evidence above: the next shelf should be one that **owns its own
catalogue ids**, because every finding here came from the shared-shelf design rather than from
the arithmetic — the eight calculators were correct on every one of the **seventeen** independent
recomputations in §4.3.

