# Operations management — subject acceptance manual

**Session 8 of 11 · subject `operations` · branch `corpus/merge-v1` · written 2026-11-03**
**Opening commit:** `1660f25` (the tree moved under this session — another lane committed `f699579` while
it ran; every number below was re-measured, none was copied).
**Acceptance suite:** `tests/test_subject_operations_acceptance.py` — one test per PASS row, named
`test_E_ops_nnn__<behaviour>`.

This manual is the specification for the shelf. Every row cites the artefact it was read from, and every
PASS row names the test that proves it. Nothing here is a new requirement: the rules come from
`docs/CONDUCTOR_MANUAL.md` §4 and §8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20), the owner's
presentation rules P1–P6 set on 2026-11-03, and the frozen core's own contract.

**Reproduce the measurements in this file**

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python qa\probe_ops_shelf.py                   # inventory, forms, records, glossary, block provenance
python qa\probe_ops_shelf.py --auto            # the auto-fill trap (D-OPS-03)
python qa\probe_ops_shelf.py --papers --tools  # writes and reads the 11 worksheet papers + 14 tool papers
python qa\probe_mgt_debug.py template_scor template_sipoc template_value_stream_map template_5s `
    template_a3 template_toc template_root_cause template_fmea template_kraljic template_sop template_pdca
python -m pytest tests\test_subject_operations_acceptance.py -q
```

---

## 1. Scope

The shelf in scope is `operations`, the **Operations management** shelf: `subjects.detail("operations")`.
Nothing on the marketing, supply-chain, people, project-management, entrepreneurship, finance,
accounting, economics or research shelves was started, edited or judged in this session.

The dependency this session could not avoid: **eleven of this shelf's worksheets are shared with
`supply-chain`** (`VALIDATION_HARNESS.md` §7.1), and `framework_profiles.py`, `completion.py` and
`templates.py` are shared modules. The supply-chain shelf was **read** (its page and its papers) and
**re-tested**, never opened for its own sake (§6).

## 2. Inventory, reconciled against the catalogue

| Unit | Count | Source of truth | Measured 2026-11-03 |
|---|---:|---|---|
| Compute tools | 14 | `detail("operations")["tools"]` | 14, each with a `server.PRESETS` entry (§2.5) |
| Worksheets | 11 | `detail("operations")["worksheets"]` | 11 rows, 11 distinct catalogue ids |
| Distinct worksheet templates | 11 | the same rows | no template serves two rows on this shelf |
| Framework profiles on the shelf | 11 | `framework_profiles.PROFILES` | every shelf template resolves, 4–8 blocks each |
| Framework profiles overall | 79 | `framework_profiles.PROFILES` | **79** (75 at the start of the session + the project-management lane's four) |
| Records (read-only) | 7 | `detail("operations")["records"]` | OPS-09 and QNT-OPS-01/02/04/05/06/08, all `form: computed` |
| Theories | 0 | `detail("operations")["theories"]` | 0 |
| Glossary terms | 20 | `detail("operations")["glossary"]` | 20, **20 defined**, 0 undefined |
| Catalogue records the shelf counts | 18 | `subjects.catalogue()` | **18** = 11 worksheets + 7 records, reconciled |
| Profiles on the shelf no page reaches | 0 | the sweep in §2.2 | 0 — every shelf template is on a page |
| Worksheets also shown on another shelf | 11 of 11 | `VALIDATION_HARNESS.md` §7.1 | all eleven are also on `supply-chain` (§2.2) |
| Worksheet groups | 3 tiles | `detail("operations")["tiles"]` | **3** — "Process and capacity", "Inventory and planning", "Quality and evidence" (D-OPS-06 closed) |
| Tiles | 3 | `detail("operations")["tiles"]` | 3, each with its worksheets, its calculators and its records |

### 2.1 Worksheets, one row each

Form = `templates.describe(template)["form_kind"]`; Fills = the profile's `fill` policy per block, which
is what the pipeline may do with each part.

| id | Shelf label | Template | Form | Draftable | Fills (`fill_of`) | Blocks |
|---|---|---|---|---|---|---|
| OPS-01 | SCOR supply-chain map | `template_scor` | canvas | yes | 6 × auto | plan, source, make, deliver, return, enable |
| OPS-02 | SIPOC process map | `template_sipoc` | canvas | yes | 2 research + 3 quote | suppliers, inputs, process, outputs, customers |
| OPS-03 | Value stream map | `template_value_stream_map` | canvas | **no** | 4 quote + 2 gap | process_steps, cycle_and_lead_times, inventory_wip, waits_delays, value_added, improvements |
| OPS-04 | 5S workplace audit | `template_5s` | canvas | yes | 5 × auto | sort, set_in_order, shine, standardize, sustain |
| OPS-05 | A3 problem solving | `template_a3` | canvas | yes | 7 × auto | problem, current_condition, target, causes, countermeasures, plan, follow_up |
| OPS-06 | Theory of Constraints: five focusing steps | `template_toc` | canvas | yes | 5 × auto | identify, exploit, subordinate, elevate, reassess |
| OPS-07 | Root cause analysis (5 Whys / fishbone) | `template_root_cause` | canvas | yes | 8 × auto | problem, people, process, equipment, materials, measurement, environment, root_cause |
| OPS-08 | Failure mode and effects analysis (FMEA) | `template_fmea` | canvas | yes | 6 × auto | failure_modes, effects, causes, controls, actions, owners |
| OPS-10 | Kraljic purchasing portfolio | `template_kraljic` | canvas | yes | 5 × auto | criteria, strategic, leverage, bottleneck, non_critical |
| OPS-11 | Sales and operations plan (S&OP) | `template_sop` | canvas | yes | 6 × auto | demand_plan, supply_plan, inventory_plan, capacity_plan, financial_plan, decisions |
| OPS-12 | PDCA improvement cycle | `template_pdca` | canvas | yes | 4 × auto | plan, do, check, act |

**The one worksheet with no draft button** is OPS-03, and it is the only `quote`+`gap` profile on the
shelf: a value stream map is the student's own process, so there is nothing legitimate for the pipeline
to research. The flag governs the button, not the capability — `test_E_ops_006` and `test_E_ops_041`
build its paper through the real engine.

**Nine of the eleven profiles are `auto` per block**, which is the shelf's highest-risk declaration: an
`auto` block researches first, then falls back to the student's own sentences. D-OPS-03 (§4) is what that
fallback did before this session.

**One worked example per worksheet** now exists in `templates.EXAMPLES` (`test_E_ops_007`). Before this
session none of the eleven had one, and the four `ExampleTest` cases in
`tests/test_operations_frameworks.py` errored with `KeyError` instead of testing anything (D-OPS-01).

### 2.1.1 The three tiles, and what sits in each (D-OPS-06, closed 2026-11-03)

The tile keys **are the shelf's own tool-group names** (`OPERATIONS_GROUPS`), because `_tiles()` places a
calculator in the tile whose key equals the tool's `group`; a different vocabulary would have taken all
fourteen calculators off the page.

| Tile | Worksheets | Calculators | Records |
|---|---|---|---|
| Process and capacity | OPS-01 SCOR, OPS-02 SIPOC, OPS-03 value stream, OPS-06 TOC | `breakeven`, `multibreakeven`, `unitecon`, `queue`, `capacity`, `linebalance` | QNT-OPS-04, QNT-OPS-05, QNT-OPS-08 |
| Inventory and planning | OPS-10 Kraljic, OPS-11 S&OP | `inventory`, `forecast`, `missing`, `descriptive` | QNT-OPS-01, QNT-OPS-02 |
| Quality and evidence | OPS-04 5S, OPS-05 A3, OPS-07 root cause, OPS-08 FMEA, OPS-12 PDCA | `oee`, `spc`, `chi_square`, `power` | OPS-09, QNT-OPS-06 |

**Nothing is dropped and nothing is counted twice** — 11 worksheets, 14 calculators and 7 records, each in
exactly one tile (`test_E_ops_010`). The record map is not decoration: with no record group the seven
computed records are claimed by no tile, and the page's leftover heading prints them as *"read and cite —
no worksheet yet"* cards, which is a calculator described as something to cite.

### 2.2 Shared with another shelf, and reachability

| Worksheets | Also on |
|---|---|
| OPS-01 … OPS-08, OPS-10 … OPS-12 (all eleven) | `supply-chain` |

A change to any of these profiles changes the supply-chain shelf's paper. §6 records what was re-tested.
The reverse measurement: **no profile on this shelf is unreachable** — all eleven templates appear on a
subject page, so there is no operations equivalent of G-mgt-02.

### 2.3 Records, theories and glossary

| id | Name | Form | Linked methods |
|---|---|---|---|
| OPS-09 | Statistical Process Control (SPC) | computed | `process_control` |
| QNT-OPS-01 | EOQ, reorder point, safety stock and inventory-service-level calculations | computed | `inventory_policy` |
| QNT-OPS-02 | Demand/lead-time forecasts | computed | `trend_forecast` |
| QNT-OPS-04 | Queueing models, throughput, cycle/lead time, utilization and capacity analysis | computed | `queue_analysis`, `capacity_analysis` |
| QNT-OPS-05 | Critical Path Method (CPM), PERT estimates and schedule-risk analysis | computed | `cpm_schedule` |
| QNT-OPS-06 | Overall Equipment Effectiveness (OEE), process capability and control charts | computed | `oee_analysis`, `process_control` |
| QNT-OPS-08 | Throughput and constraint analysis | computed | `capacity_analysis`, `queue_analysis` |

Every record resolves in `bp.registry` with `form: computed` and **no template link**, so the page treats
it as read-only: it states what a method computes, it is not a form. Each `linked_method` resolves in
`bp.methods.LIBRARY` (`test_E_ops_003`). The shelf declares **no theories**.

#### 2.3.1 Glossary, one row each (20 terms, all defined)

| Term | Definition (as served) |
|---|---|
| Throughput | The rate at which the process produces finished units; it is set by the bottleneck. |
| Capacity | The most a resource can produce in a period at its declared rate. |
| Bottleneck | The resource with the smallest capacity; extra capacity elsewhere does not raise output. |
| Utilisation | Demand or load divided by capacity. |
| Cycle time | The time between one unit leaving the process and the next. |
| Takt time | Available time divided by customer demand: the pace the process must keep. |
| Work in progress | Units started but not finished; it ties up cash and lengthens the lead time. |
| Lead time | The elapsed time from an order being placed to the goods arriving. |
| EOQ | Economic order quantity: the order size that minimises ordering plus holding cost. |
| Safety stock | Buffer inventory held against demand or lead-time variability. |
| Reorder point | The inventory level at which a new order is placed: lead-time demand plus safety stock. |
| Service level | The probability of not running out during a replenishment cycle, declared by you. |
| Arrival rate | The average number of customers or jobs arriving per period. |
| Service rate | The average number a single server can complete per period. |
| Queue length | Customers waiting, excluding the one being served. |
| Little's law | Average customers in a system equal the arrival rate times the average time in it. |
| M/M/1 | One server, random arrivals and random service times with constant averages. |
| Changeover | The time to switch a resource from one product to another; it is not in a steady-state capacity figure. |
| Line balancing | Assigning tasks to workstations so each station fits inside the cycle time while respecting precedence. |
| Ranked positional weight | A task's own time plus the time of every task that must follow it; used to rank tasks when balancing. |

### 2.4 UI surfaces

| Surface | Where | What this session checked |
|---|---|---|
| Subject page | `#/subject/operations` | the three tiles (D-OPS-06 closed), the 11 rows, the 14 tools, the 7 records inside their tiles, the 20 terms, the declared `does_not` list (E-ops-001…010) |
| Worksheet form | `templates.describe(template)["form_kind"]` | every row renders a canvas form the page knows, and the registry calls it a worksheet (E-ops-005) |
| Example request | `templates.describe(template)["example_request"]` | every one of the eleven now carries its own worked example (E-ops-007) |
| Completion → paper | `completion.complete` → `draft` → `draft_bytes` | headings, byline, gaps, figure, citations (E-ops-011…020) |
| Compute tool → paper | `POST /api/sessions` → confirm → `session_paper.docx_bytes` | no specification footer, declared precision (E-ops-021…028) |
| Worksheet export | `deliverables.write_export` | no specification footer, no hash (E-ops-027) |
| Workbench cards | `#chartbtn`, `#expbtn`, `#expzip` | present and hidden (E-ops-026) |

### 2.5 Compute tools, one row each (14)

`preset` is the `server.PRESETS` entry the page calls; `method` is the frozen-core method that computes
the figures. Every row was driven by `qa/probe_ops_shelf.py --tools`: `preset` → `Pipeline.run` →
`session_paper.docx_bytes` → the text a reader holds.

| Tool | Preset | Method | Level | Checks | Status |
|---|---|---|---|---|---|
| `breakeven` | `breakeven` | `breakeven` | intro | 5 | delivered |
| `multibreakeven` | `multibreakeven` | `multi_product_breakeven` | intermediate | 5 | delivered |
| `unitecon` | `unitecon` | `unit_economics` | intermediate | 5 | delivered |
| `forecast` | `forecast` | `trend_forecast` | intermediate | 5 | delivered |
| `inventory` | `inventory` | `inventory_policy` | intermediate | 5 | delivered |
| `queue` | `queue` | `queue_analysis` | intermediate | 6 | delivered |
| `capacity` | `capacity` | `capacity_analysis` | intermediate | 5 | delivered |
| `linebalance` | `linebalance` | `line_balancing` | advanced | 5 | delivered |
| `oee` | `oee` | `oee_analysis` | intermediate | 5 | delivered |
| `spc` | `spc` | `process_control` | intermediate | 5 | delivered |
| `chi_square` | `chi_square` | `chi_square` | intermediate | 6 | delivered |
| `power` | `power` | `power_analysis` | intermediate | 5 | delivered |
| `missing` | `missing` | `missing_data_bounds` | intermediate | 5 | delivered |
| `descriptive` | `descriptive` | `descriptive_stats` | intro | 6 | delivered |

No tool printed a raw Decimal, a scientific figure, a Python repr or a specification footer, and two
identical runs produced identical bytes (`E-ops-029`…`E-ops-032`).

---

## 3. Expected behaviour — E-ops-001 … E-ops-046

`PASS` = a test asserts it and the product does it. `BLOCKED` = the behaviour needs an owner decision and
the test pins the current state so it cannot drift silently. `GAP` = a declared limitation that must not
be built.

### 3.1 The shelf against the catalogue

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-001 | The shelf declares 14 compute tools, each with a working preset whose method exists | `detail("operations")["tools"]`; `server.PRESETS`; `methods.LIBRARY` | PASS |
| E-ops-002 | The shelf declares 11 worksheets with 11 distinct catalogue ids | `detail("operations")["worksheets"]` | PASS |
| E-ops-003 | Every worksheet resolves to an installed profile, and every read-only record resolves in the registry with `form: computed` and its linked methods in `LIBRARY` | `framework_profiles.PROFILES`; `bp.registry` | PASS |
| E-ops-004 | The shelf declares 7 read-only records, 0 theories and 20 glossary terms, and every term is defined | `detail("operations")` | PASS |
| E-ops-005 | Every worksheet renders a form the page knows and the registry calls a worksheet | `templates.describe`; `registry.get` | PASS |
| E-ops-006 | Exactly one worksheet (OPS-03) is not draftable, and it is the `quote`+`gap` profile | `detail("operations")["worksheets"]`; `fill_of` | PASS |
| E-ops-007 | Every worksheet has a worked example that is labelled synthetic and passes its own `validate()` and every one of its own checks | `templates.EXAMPLES`; `templates.run_template` | PASS |
| E-ops-008 | The declared `does_not` list is present and specific (no data retrieval, no schedule optimisation, no plant visit) | `detail("operations")["does_not"]` | PASS |
| E-ops-009 | The catalogue row agrees with the detail page on tools, worksheets, records, theories and the 18 it counts | `subjects.catalogue()` | PASS |
| E-ops-010 | All eleven worksheets are also on the `supply-chain` shelf, no template is unreachable, and the page groups worksheets, calculators and records into three tiles with nothing dropped | `VALIDATION_HARNESS.md` §7.1; `detail("operations")["tiles"]` | PASS |

### 3.2 The eleven papers (V-01…V-20, read on the artefact)

One paper per worksheet was produced through `completion.complete` → `draft` → `draft_bytes`, written to
`qa/evidence/operations/ops-*.docx`, and read back from `word/document.xml` (P6).

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-011 | Every worksheet produces a paper: Introduction first, Conclusion and References last, no heading-level jump | V-09, V-10, V-11 | PASS |
| E-ops-012 | Every block of every worksheet carries a sourced item, the student's own sentence, or a named gap — never a blank | V-12 | PASS |
| E-ops-013 | A named gap says **what to state**; a judgement cell says what the student must decide | V-02 | PASS |
| E-ops-014 | The byline reaches the title page and no placeholder name or template text is printed | V-20, V-06 | PASS |
| E-ops-015 | No paper prints an instructional phrase ("add your", "not supplied", "Diagram to draw") | V-06 | PASS |
| E-ops-016 | Every sourced item carries a source and a citation, and the citation reaches its own section **once** | V-01, V-13 | PASS |
| E-ops-017 | Every reference printed in References is cited in the body, and no source fills two dimensions | V-01, V-13 | PASS |
| E-ops-018 | The canvas figure carries one labelled cell per block, in the declared order, with the block's accepted items or its named gap — and the figure adds no number and no evidence | V-12; P6; `matrix.LAYOUTS` (closed by owner instruction, 2026-11-03) | PASS |
| E-ops-019 | Two identical runs produce byte-identical papers (determinism) | core invariant | PASS |
| E-ops-020 | No paper ranks, scores or recommends: the conclusion states the count of accepted items per part and never which part "carries the most weight" | shelf declaration (no scoring, no ranking) | PASS |

**What the old conclusion sentence did (D-OPS-02).** Read on the eleven papers it said *"… and Process
steps carries the most weight in the reading offered here, while Process steps carries the least."* — the
same part named both strongest and weakest, because `index(max())` and `index(min())` resolve to the same
element whenever every part carries one item, which is what an operations completion produces. The
sentence also ranked the parts, which this shelf declares it never does. It now prints the count and says
a count is not a weight.

### 3.3 Fill policy: what the pipeline may do with each part

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-021 | A `research` part accepts a source whose title echoes its own query (SIPOC suppliers, inputs) | V-01; `retrieval._accept` | PASS |
| E-ops-022 | A `quote` part takes the student's own sentence verbatim and never a paraphrase | manual §4.3; `_quote_block` | PASS |
| E-ops-023 | A `quote`/`auto` part is filled only by a sentence **about that part**; a sentence that merely shares a generic word ("change", "review", "cost", "flow") is refused and becomes a named gap | V-01, V-03; D-OPS-03 | PASS |
| E-ops-024 | A `gap` part is never filled by the pipeline, and says what the student must state | V-02; owner rule P6 | PASS |
| E-ops-025 | A value stream map never searches the databases for a part the student owns | V-03; `fill_of` | PASS |
| E-ops-026 | The chart and export cards keep their ids (`#chartbtn`, `#expbtn`, `#expzip`) and stay hidden | owner rule P2 | PASS |

### 3.4 The compute tools, end to end

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-027 | Every tool delivers, its paper carries no specification footer and no hash, and the hash stays in the record | owner rule P3 | PASS |
| E-ops-028 | Every figure prints at the method's declared precision (`method.typing(key)`): no raw Decimal, no 50 digits, no scientific notation in a computed figure, no Python repr | owner rule P4; B-197 | PASS |
| E-ops-029 | No paper or page promises a "Diagram to draw" | owner rule P5 | PASS |
| E-ops-030 | There is no Markdown download anywhere: no `format:"md"`, no Markdown button, no route branch | owner rule P1 | PASS |

### 3.5 Debugging the shelf by driving it (2026-11-03)

`qa/probe_mgt_debug.py` was pointed at this shelf for the first time. It reported **5 problems and all
five were the harness** — two of them are this session's first fix (§6), and the other three were the
same two false positives firing twice.

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-031 | No block on the shelf declares a placeholder cue or a list of cues, and every researched block declares cues and a query | `framework_profiles`; `retrieval.cue_words_of` | PASS |
| E-ops-032 | Every researched block on the shelf accepts a source whose title echoes its own query (all 54 researched blocks) | `retrieval._accept`; V-01 | PASS |
| E-ops-033 | No operations paper prints a wrong article or a broken singular | manual §4.6 | PASS |
| E-ops-034 | The eleven papers contain no Python repr and no raw decimal | owner rule P4 | PASS |
| E-ops-035 | The spec hash stays in the record and out of **every** download (paper, worksheet, CSV, workbook) | owner rule P3 | PASS |
| E-ops-036 | The probe reports **0 problems** over 11 worksheets × (evidence, no evidence, determinism) and 14 tools after the two harness fixes | `qa/baseline/ops-probe-after-harness-fix.txt` | PASS |

**Scoreboard: 36 PASS · 0 BLOCKED · 0 GAP.** Ten further rows (§3.6) are the shelf-wide traps the
acceptance suite adds; the traceability matrix in §5 lists all 46.

### 3.6 Shelf-wide traps carried by the acceptance suite

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-ops-037 | Every `auto` and `quote` block on the shelf declares a `quote_cues` vocabulary, so no block can borrow a sentence on the strength of the retrieval cue list (D-OPS-03) | `framework_profiles.QUOTE_CUES` | PASS |
| E-ops-038 | With a brief that only mentions cost, quality and flow and no source available, **no** block on the shelf claims an item for a part the brief does not describe (0 of 11 templates quote anything) | V-01, V-03; measured in `qa/baseline/ops-probe-auto-trap.txt` | PASS |
| E-ops-039 | With a brief that genuinely describes the process, the parts it describes still fill from the student's own words — the fix narrows the match, it does not switch the fallback off | V-03; `tests/test_operations_frameworks.py` | PASS |
| E-ops-040 | No operations paper's conclusion ranks the parts or names the same part as strongest and weakest | shelf declaration; D-OPS-02 | PASS |
| E-ops-041 | The non-draftable value stream map still produces a complete paper through the real engine | `VALIDATION_HARNESS.md` §7.2 | PASS |
| E-ops-042 | A run with no source at all still records every block: each is a named gap that says what to state, and no cell is blank | V-02, V-12 | PASS |
| E-ops-043 | Every worksheet serves its worked example to the page (`describe(template)["example_request"]`), and the example is labelled synthetic | `templates.describe` | PASS |
| E-ops-044 | The `supply-chain` shelf still serves the same eleven worksheets, and its paper still builds (a change here is a change there) | D6; `subjects.detail("supply-chain")` | PASS |
| E-ops-045 | No paper prints its citation twice (`(Lovelace, 2024) (Lovelace, 2024)`) | V-13; D-OPS-04 | PASS |
| E-ops-046 | No researched block builds its query from the raw block key: every query is the framework's own language | V-04; the retrieval contract | PASS |

## 4. DISPUTED rows

None. One row is `GAP` rather than `PASS`, and it is declared rather than disputed:

- **E-ops-006 / OPS-03.** The value stream map has no “draft it for me” button. That is deliberate — the
  four `quote` cells are the student's own process and the two `gap` cells are their judgement — and the
  paper is still produced (E-ops-041).

The worksheet groups are no longer a gap: the shelf declares three tiles (§2.1.1) and the page groups its
worksheets, calculators and records inside them, with the record map that keeps the seven computed records
from being printed as "read and cite" cards.

## 5. Traceability matrix

| E-id | Test | E-id | Test |
|---|---|---|---|
| E-ops-001 | `test_E_ops_001__the_shelf_declares_14_tools_with_a_preset_and_a_method` | E-ops-024 | `test_E_ops_024__a_gap_part_is_never_filled_and_says_what_to_state` |
| E-ops-002 | `test_E_ops_002__the_shelf_declares_11_worksheets_with_distinct_catalogue_ids` | E-ops-025 | `test_E_ops_025__a_value_stream_map_never_searches_for_a_part_the_student_owns` |
| E-ops-003 | `test_E_ops_003__every_worksheet_resolves_and_every_record_is_read_only` | E-ops-026 | `test_E_ops_026__the_chart_and_export_cards_keep_their_ids_and_stay_hidden` |
| E-ops-004 | `test_E_ops_004__seven_records_twenty_defined_terms_and_no_theories` | E-ops-027 | `test_E_ops_027__no_download_carries_a_specification_footer_or_a_hash` |
| E-ops-005 | `test_E_ops_005__every_worksheet_is_a_form_the_page_can_render` | E-ops-028 | `test_E_ops_028__every_figure_prints_at_the_methods_declared_precision` |
| E-ops-006 | `test_E_ops_006__ops_03_is_the_one_non_draftable_worksheet` | E-ops-029 | `test_E_ops_029__no_paper_or_page_promises_a_diagram` |
| E-ops-007 | `test_E_ops_007__every_worksheet_has_a_worked_example_that_passes_its_own_checks` | E-ops-030 | `test_E_ops_030__there_is_no_markdown_download_anywhere` |
| E-ops-008 | `test_E_ops_008__the_declared_does_not_list_is_present_and_specific` | E-ops-031 | `test_E_ops_031__no_block_declares_a_placeholder_cue_or_a_list_of_cues` |
| E-ops-009 | `test_E_ops_009__the_catalogue_row_agrees_with_the_detail_page` | E-ops-032 | `test_E_ops_032__every_researched_block_accepts_evidence_for_its_own_question` |
| E-ops-010 | `test_E_ops_010__all_eleven_worksheets_are_shared_and_the_page_groups_them` | E-ops-033 | `test_E_ops_033__no_paper_prints_a_wrong_article_or_a_broken_singular` |
| E-ops-011 | `test_E_ops_011__every_worksheet_paper_opens_and_closes_in_the_declared_order` | E-ops-034 | `test_E_ops_034__no_paper_prints_a_python_repr_or_a_raw_decimal` |
| E-ops-012 | `test_E_ops_012__every_block_carries_an_item_or_a_named_gap` | E-ops-035 | `test_E_ops_035__the_hash_stays_in_the_record_and_out_of_every_download` |
| E-ops-013 | `test_E_ops_013__a_named_gap_says_what_to_state` | E-ops-036 | `test_E_ops_036__the_probe_reports_no_problem_on_this_shelf` |
| E-ops-014 | `test_E_ops_014__the_byline_reaches_the_title_page_and_no_placeholder_is_printed` | E-ops-037 | `test_E_ops_037__every_auto_and_quote_block_declares_its_quote_vocabulary` |
| E-ops-015 | `test_E_ops_015__no_paper_prints_an_instructional_phrase` | E-ops-038 | `test_E_ops_038__a_generic_brief_fills_no_part_it_does_not_describe` |
| E-ops-016 | `test_E_ops_016__every_sourced_item_carries_one_citation_in_its_own_section` | E-ops-039 | `test_E_ops_039__an_honest_brief_still_fills_the_parts_it_describes` |
| E-ops-017 | `test_E_ops_017__every_reference_is_cited_and_no_source_fills_two_parts` | E-ops-040 | `test_E_ops_040__no_conclusion_ranks_the_parts` |
| E-ops-018 | `test_E_ops_018__the_figure_carries_one_labelled_cell_per_block` | E-ops-041 | `test_E_ops_041__a_non_draftable_profile_still_produces_a_paper` |
| E-ops-019 | `test_E_ops_019__two_identical_runs_produce_identical_bytes` | E-ops-042 | `test_E_ops_042__a_run_without_sources_names_every_part_and_fills_nothing` |
| E-ops-020 | `test_E_ops_020__no_paper_scores_ranks_or_recommends` | E-ops-043 | `test_E_ops_043__every_worksheet_serves_its_example_and_the_example_is_synthetic` |
| E-ops-021 | `test_E_ops_021__a_research_part_accepts_its_own_vocabulary` | E-ops-044 | `test_E_ops_044__the_supply_chain_shelf_still_serves_and_builds_the_eleven` |
| E-ops-022 | `test_E_ops_022__a_quote_part_takes_the_students_own_sentence_verbatim` | E-ops-045 | `test_E_ops_045__no_paper_prints_its_citation_twice` |
| E-ops-023 | `test_E_ops_023__a_sentence_that_only_shares_a_generic_word_is_refused` | E-ops-046 | `test_E_ops_046__no_query_is_built_from_a_raw_block_key` |

Every row maps to exactly one test; no test is unused and no row is untested.

## 6. What this session changed, and what it re-tested

`framework_profiles.py`, `completion.py` and `templates.py` are shared with the other ten shelves, and all
eleven operations worksheets are also on `supply-chain`, so every edit was re-tested (§6.1).

| Change | File | Why it could not be done anywhere else | Re-tested |
|---|---|---|---|
| Eleven worked examples, one per operations worksheet | `bp/templates.py` (`EXAMPLES`) | the example is the template's own declaration; nothing else can supply it | `run_template` on all 11, the sandbox parity test, the whole `template_*` suite |
| `quote_cues`: a block may declare the words that make a sentence *about that part* | `bp/product/completion.py` (`_quote_block`) | one matcher serves all 79 profiles; the declaration is data, the rule is code | every completion suite, the corpus cue sweep; no other profile declares the key, so no other shelf changes |
| The shelf's per-part quote vocabulary, 59 blocks | `bp/product/framework_profiles.py` (`QUOTE_CUES`) | the declaration belongs with the profile data | the 11 papers, the trap brief, `test_operations_frameworks` |
| A `gap` cell now prints its own probe (D-OPS-05) | `bp/product/completion.py` (`_gap_note`) | one gap sentence serves the corpus; only this shelf's two blocks have a probe | the 11 papers |
| No duplicated citation in any framework paper (D-OPS-04) | `bp/product/completion.py` (`_sections`) | one renderer serves every shelf | completion slice (584 passed), 11 papers |
| The conclusion states a count instead of a ranking (D-OPS-02) | `bp/product/completion.py` (`_draft_data`) | one conclusion serves every shelf | completion slice, 11 papers |
| The probe's two false positives, and a 14-tool pass | `qa/probe_mgt_debug.py` | it is the harness, not the product | re-run over this shelf: 5 problems → 0 |
| The shelf's own probe | `qa/probe_ops_shelf.py` | no read-only probe existed for this shelf | it is the evidence behind every number here |
| Three tiles for the shelf, and a record map so no calculator is described as something to cite | `bp/product/subjects.py` (`OPERATIONS_TILES`, `OPERATIONS_WORKSHEET_GROUPS`, `OPERATIONS_RECORD_GROUPS`) | the tile keys must be the shelf's own tool groups or `_tiles()` drops every calculator; the page is generated from `detail()` | `test_E_ops_010`, `test_product_subjects`, `test_people_frameworks`, `test_operations_frameworks` (150 passed) |
| Eleven figure layouts for the eleven worksheets | `bp/product/matrix.py` (`LAYOUTS`) | the geometry is declared per template and the builder writes no content | the eleven papers, `test_matrix_figure`, `test_E_ops_018`, the probe (0 problems) |

**Not touched:** `src/bp/methods.py`, `src/bp/server.py`, `src/bp/registry.py`,
`tests/fixtures/frozen_contract.json`, any preset, any route family, any input schema, `docs/sources/**`.
No new dependency, no network call, no model call, no new worksheet, no new record, no new method.

### 6.1 Measured effect

| Slice | Before | After |
|---|---|---|
| `tests/test_operations_frameworks.py` | 49 tests, **4 errors** (`ExampleTest`: `KeyError: 'template_sipoc'`) | **50 passed** (one trap test added) |
| `tests/test_subject_operations_acceptance.py` | — (new) | **46 passed** (`qa/baseline/ops-acceptance-out.txt`) |
| Framework-completion slice (`-k completion`) | — | **584 passed, 0 failed** (`qa/baseline/ops-completion-slice-out.txt`) |
| `qa/probe_mgt_debug.py` on 11 worksheets + 14 tools | 5 problems, **all five the harness** | **0 problems** (`qa/baseline/ops-probe-after-harness-fix.txt`) |
| Full suite | 3184 tests, 5 failures, 4 errors (`qa/baseline/ops-base-suite-err.txt`) | **3409 tests, 0 failures, 0 errors** on the integrated tree (`qa/baseline/ops-final-suite-err.txt`) |

### 6.2 The full suite, before and after

| | Tests | Failures | Errors | Distinct failure names |
|---|---:|---:|---:|---:|
| Baseline at `1660f25` + the other lane's in-flight work (`qa/baseline/ops-base-suite-err.txt`) | 3184 | 5 | 4 | 9 |
| After this session (`qa/baseline/ops-after-suite-err.txt`) | **3236** | **7** | **0** | 7 |
| Final, on the integrated tree (`qa/baseline/ops-final-suite-err.txt`) | **3409** | **0** | **0** | 0 |

The baseline's four errors were **this shelf's** (`ExampleTest`, `KeyError: 'template_sipoc'`) and are gone.
The seven failures the after-run still showed were all foreign — three KNOWN-HISTORICAL, the foreign
`balanced_scorecard` cue set, and three caused by another lane's in-flight work — and the lanes that owned
them repaired them as they landed: **the final run on the integrated tree is 3409 tests, 0 failures,
0 errors** (`qa/baseline/ops-final-suite-err.txt`).

### 6.3 The tree moved under this session

`HEAD` was `1660f25` when the session started and `f699579` after another lane's commit mid-run, which
also swept four profiles into `framework_profiles.py` (now **79** profiles, not 75). Every number in this
manual was re-measured on the tree that answered, and the baseline is labelled with that caveat rather
than presented as a clean measurement of `1660f25`.

## 7. Defects found, and where they are recorded

The ledger rows are `D-OPS-01 … D-OPS-07` and `G-ops-01 … G-ops-03` in `qa/QA_DEFECTS.md`. Four of the
seven were found only by reading the produced `.docx` (P6), which is why the probe exists.

| Ledger | What the reader saw | Class | Status |
|---|---|---|---|
| D-OPS-01 | four test errors instead of four tests: no worksheet had a worked example | WIRING | FIXED |
| D-OPS-02 | “and Problem carries the most weight …, while Problem carries the least” | HONESTY | FIXED |
| D-OPS-03 | “The manager reviews the change next term” printed as what PDCA's *act* stage standardised | HONESTY (BLOCKER) | FIXED |
| D-OPS-04 | “(Lovelace, 2024) (Lovelace, 2024)” in every sourced cell | HONESTY | FIXED |
| D-OPS-05 | a judgement cell that never said what to state, though the profile declares it | HONESTY | FIXED |
| D-OPS-06 | eleven worksheets in one flat list, no groups | UI | **FIXED** (three tiles, B-206) |
| D-OPS-07 | “the lunch service at the meal counter **lunch service meal** …” in every query | WIRING | **OPEN** (MINOR) |
| D-OPS-08 | the three count documents said 3165 tests; the loader says 3184 and then 3236 | DOC-DRIFT | FIXED (set from the loader) |
| G-ops-01 | no figure in any of the eleven papers: `matrix.LAYOUTS` had no operations entry | PRESENTATION | **FIXED** (owner instruction; eleven layouts, B-202) |
| G-ops-01 | no figure in any of the eleven papers | — | **GAP** (owner decision) |
| G-ops-03 | one brief sentence printed under two adjacent SIPOC parts | HONESTY | **GAP** (declared) |

## 8. Evidence

| Artefact | Path |
|---|---|
| The eleven worksheet papers, sourced run | `qa/evidence/operations/ops-*.docx` / `.txt` |
| The fourteen compute-tool papers | `qa/evidence/operations/tool-*.docx` / `.txt` |
| The probe's inventory, forms, records, glossary and block provenance | `qa/baseline/ops-probe-shelf.txt` |
| The auto-fill trap, before and after (D-OPS-03) | `qa/baseline/ops-probe-auto-trap.txt` |
| The repaired harness over this shelf: 0 problems | `qa/baseline/ops-probe-after-harness-fix.txt` |
| Baseline full suite, before any change | `qa/baseline/ops-base-suite-err.txt` (3184 / 5 / 4) |
| Baseline failure names | `qa/baseline/ops-base-failure-names.txt` |
| Acceptance suite | `qa/baseline/ops-acceptance-out.txt` (46 passed) |
| Framework-completion slice | `qa/baseline/ops-completion-slice-out.txt` (584 passed) |
| Full suite, after | `qa/baseline/ops-after-suite-err.txt` |

## 9. Declared gaps

| Id | Gap | Why it is not built |
|---|---|---|
| G-ops-01 | ~~No figure in any of the eleven papers~~ — **closed 2026-11-03** by owner instruction | eleven layouts now sit in `matrix.LAYOUTS` (B-202): each cell is labelled with the block's own label and carries the items already accepted or the gap already named. No new number, no new evidence |
| G-ops-02 | ~~The eleven worksheets have no `group`, so the page shows one flat list~~ — **closed 2026-11-03** by owner instruction | three tiles now group the shelf (B-206): their keys are the shelf's own tool groups, so each tile holds the worksheets, the calculators and the records of one question. `test_E_ops_010` fails if a tile drops or duplicates an item |
| G-ops-03 | One brief sentence can be quoted into two adjacent parts | the match is lexical by design; a paraphrase matcher is not built, and the paper labels every quoted cell as the student's own words |
| G-ops-04 | The shelf has no theories, and none is claimed | by design: the record sets live on Project management and People |
| G-ops-05 | `inventory_policy`, `queue_analysis` and `capacity_analysis` are also on the supply-chain page | deliberate: four capabilities serve both shelves (`VALIDATION_HARNESS.md` §7.1) |

## 10. Residual risk

1. **The live gate is stricter than the mocks.** Every sourced-item row here was measured with a mocked
   retrieval whose title carries the query. The real gate needs a cue word *and* the process in the
   title, so a thin live topic still returns gaps. That is fail-closed behaviour, not a defect.
2. **`quote_cues` is now a second vocabulary to maintain.** If a future edit widens `cues` and forgets
   `quote_cues`, the borrowing rule stays as declared — by design: the retrieval vocabulary is not the
   quote vocabulary. `test_E_ops_037` fails if an `auto`/`quote` block is added without one.
3. **The tree moved mid-session and will move again.** Another lane committed while this session ran and
   four profiles appeared in a shared module. Every commit here is path-scoped, and `git status` was read
   before and after each one.
4. **The D-OPS-03 fix changes other shelves' borrowing only if they declare `quote_cues`** — none does
   today, so the blast radius on the corpus is the eleven operations templates plus the two SIPOC/VSM
   quote blocks. `test_product_profile_cues` (the corpus sweep) and the completion slice were re-run.









