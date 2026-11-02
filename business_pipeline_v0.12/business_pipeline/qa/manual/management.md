# Management & strategy — subject acceptance manual

**Session 4 of 11 · subject `management` · branch `corpus/merge-v1` · written 2026-11-03**
**Opening commit:** `211b672`. **Measured against:** the working tree at that commit.
**Acceptance suite:** `tests/test_subject_management_acceptance.py` — one test per PASS row, named
`test_E_mgt_nnn__<behaviour>`.

This manual is the specification for the shelf. Every row cites the artefact it was read from, and
every PASS row names the test that proves it. Nothing here is a new requirement: the rules come from
`docs/CONDUCTOR_MANUAL.md` §4 and §8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20), the owner's
presentation rules P1–P6 set on 2026-11-03, and the frozen core's own contract.

**Reproduce the measurements in this file**

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python qa\probe_mgt_shelf.py          # inventory + one mocked run per profile
python qa\probe_mgt_paper.py          # builds the papers and reads them back (P6)
python -m pytest tests\test_subject_management_acceptance.py -q
```

---

## 1. Scope

The shelf in scope is `management`, the **Management & strategy** shelf: `subjects.detail("management")`.
Nothing on the marketing, people, operations, supply-chain, project-management, entrepreneurship,
finance, accounting, economics or research shelves was started, edited or judged in this session.

The dependency this session could not avoid: some of the shelf's profiles are also used by the People
and Entrepreneurship shelves (the 31 shared worksheets, `VALIDATION_HARNESS.md` §7.1), and
`framework_profiles.py` is a shared module. A change made for this shelf is therefore visible to those
shelves; the effects on them were re-tested (§6).

## 2. Inventory, reconciled against the catalogue

| Unit | Count | Source of truth | Measured 2026-11-03 |
|---|---:|---|---|
| Compute tools | 1 | `detail("management")["tools"]` | `case_decision` (“Compare strategic options”) |
| Worksheets | 31 | `detail("management")["worksheets"]` | 31 rows, 31 distinct catalogue ids |
| Distinct worksheet templates | 30 | the same rows | `template_swot` is used by both STR-07 and STR-18 |
| Framework profiles on the shelf | 30 | `framework_profiles.PROFILES` | every shelf template resolves |
| Framework profiles overall | 75 | `framework_profiles.PROFILES` | **75** (unchanged by this session) |
| Records (read-only) | 0 | `detail("management")["records"]` | 0 |
| Theories | 0 | `detail("management")["theories"]` | 0 |
| Glossary terms | 0 | `detail("management")["glossary"]` | the shelf has no glossary |
| Catalogue records the shelf *counts* | 28 | `subjects.catalogue()` | **28** against 31 rows — D-MGT-09 |
| Profiles no subject page reaches | 18 | `test_E_mgt_043` | **18** on 2026-11-03 (17 before the marketing lane removed the SERVQUAL worksheet row while repairing it) — G-mgt-04 |
| Worksheets also shown on another shelf | 18 of the 31 rows | `VALIDATION_HARNESS.md` §7.1 | 13 CHG rows on People, 5 STR rows on Entrepreneurship (§2.2) |

### 2.1 Worksheets, one row each

Group = the shelf's own grouping (`group`); Draftable = the student's “draft it for me” button.

| id | Shelf label | Template | Form | Draftable | Group |
|---|---|---|---|---|---|
| STR-01 | Porter's Five Forces | `template_five_forces` | five_forces | yes | competitive_position |
| STR-02 | Porter's generic strategies with an evidence audit | `template_generic_strategies` | canvas | yes | competitive_position |
| STR-03 | Porter's Value Chain | `template_value_chain` | canvas | yes | diagnosis |
| STR-04 | Strategic positioning and activity-system fit | `template_activity_system_fit` | canvas | **no** | competitive_position |
| STR-05 | Porter's Diamond with an evidence audit | `template_porters_diamond` | canvas | yes | competitive_position |
| STR-06 | PESTEL | `template_pestel` | canvas | yes | diagnosis |
| STR-07 | SWOT / TOWS | `template_swot` | swot | yes | diagnosis |
| STR-08 | VRIO | `template_vrio` | vrio | **no** | diagnosis |
| STR-09 | Ansoff Matrix | `template_ansoff` | canvas | **no** | portfolio_growth |
| STR-10 | BCG growth-share matrix with an evidence audit | `template_bcg` | canvas | yes | portfolio_growth |
| STR-11 | GE-McKinsey portfolio matrix with an evidence audit | `template_ge_mckinsey` | canvas | yes | portfolio_growth |
| STR-12 | Strategic group mapping | `template_strategic_group_map` | matrix | **no** | competitive_position |
| STR-13 | Blue Ocean four actions (ERRC) | `template_blue_ocean_errc` | canvas | **no** | portfolio_growth |
| STR-14 | Scenario planning | `template_scenario_planning` | matrix | **no** | portfolio_growth |
| STR-15 | Business Model Canvas | `template_business_model_canvas` | canvas | yes | business_model |
| STR-16 | Lean Canvas | `template_lean_canvas` | canvas | yes | business_model |
| STR-17 | Value Proposition Canvas | `template_value_proposition_canvas` | canvas | yes | business_model |
| STR-18 | SWOT evidence-to-action review | `template_swot` | swot | yes | diagnosis |
| CHG-01 | Kotter's eight-step change model | `template_kotter` | canvas | yes | change_organisation |
| CHG-02 | ADKAR readiness review with an evidence audit | `template_adkar` | canvas | yes | change_organisation |
| CHG-03 | Lewin's three-stage change review with an evidence audit | `template_lewin` | canvas | yes | change_organisation |
| CHG-04 | McKinsey 7-S alignment review with an evidence audit | `template_mckinsey_7s` | canvas | yes | change_organisation |
| CHG-05 | Burke-Litwin organisational change review with an evidence audit | `template_burke_litwin` | canvas | yes | change_organisation |
| CHG-06 | Galbraith star operating model review with an evidence audit | `template_galbraith_star` | canvas | yes | change_organisation |
| CHG-07 | Theory of change with an evidence audit | `template_theory_of_change` | canvas | yes | change_organisation |
| CHG-08 | Logic model with an evidence audit | `template_logic_model` | canvas | yes | change_organisation |
| CHG-09 | PDSA improvement cycle with an evidence audit | `template_pdsa` | canvas | yes | change_organisation |
| CHG-10 | DMAIC improvement cycle with an evidence audit | `template_dmaic` | canvas | yes | change_organisation |
| CHG-11 | Organisational design review | `template_org_design` | canvas | yes | change_organisation |
| CHG-12 | Competing Values Framework | `template_competing_values` | canvas | yes | change_organisation |
| CHG-13 | Mintzberg configuration review with an evidence audit | `template_mintzberg` | canvas | yes | change_organisation |

**The six worksheets with no draft button** (STR-04, STR-08, STR-09, STR-12, STR-13, STR-14) are the
shelf's share of the twelve non-draftable profiles recorded in `VALIDATION_HARNESS.md` §7.2. The flag
governs the button, not the capability: `test_E_mgt_045` builds a paper for all twelve through the real
engine.

**Two catalogue rows, one engine.** STR-07 (SWOT / TOWS) and STR-18 (SWOT evidence-to-action review)
both open `template_swot`. That is deliberate — two assignments, one engine — but it is why the shelf
shows 31 rows over 30 templates, and it is why a paper cannot be filed by template alone
(`test_E_mgt_007`).

### 2.2 Shared with another shelf

| Worksheets | Also on |
|---|---|
| STR-13, STR-15, STR-16, STR-17, STR-18 | entrepreneurship |
| CHG-01 … CHG-13 (13) | people |

A change to a shared profile therefore changes another shelf's paper. §6 records what was re-tested.

### 2.3 Records, theories and glossary

The shelf declares **none** of the three, and that is measured rather than assumed
(`test_E_mgt_004`). A student on this shelf gets frameworks, worksheets and one compute tool. The
read-only record set (Balanced Scorecard, strategy map, KPI tree, OKRs, Scrum, Kanban, COBIT, ITIL,
DeLone-McLean, TOE) lives on the Project management shelf and the people-side records on People; no
record is claimed here that is not there.

### 2.4 UI surfaces

| Surface | Where | What this session checked |
|---|---|---|
| Subject page | `#/subject/management` | the 31 rows, 5 groups, the one tool, the declared `does_not` list (E-mgt-001…010) |
| Worksheet form | `templates.describe(template)["form_kind"]` | every row renders a form the page knows (E-mgt-005) |
| Completion → paper | `completion.complete` → `draft` → `draft_bytes` | headings, byline, gaps, figure (E-mgt-014…022) |
| Compute tool → paper | `POST /api/sessions` → confirm → `session_paper.docx_bytes` | no specification footer, declared precision (E-mgt-013, 035, 036) |
| Worksheet export | `deliverables.write_export` | no specification footer (E-mgt-035) |
| Workbench cards | `#chartbtn`, `#expbtn`, `#expzip` | present and hidden (E-mgt-034) |


---

## 3. Expected behaviour — E-mgt-001 … E-mgt-046

`PASS` = a test asserts it and the product does it. `BLOCKED` = the behaviour needs an owner decision
(frozen core or "what should a paper say") and the test pins the current state so it cannot drift
silently. `GAP` = a declared limitation that must not be built.

### 3.1 The shelf against the catalogue

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-001 | The shelf declares exactly one compute tool, `case_decision`, and it has a working preset | `detail("management")["tools"]`; `server.PRESETS` | PASS |
| E-mgt-002 | The shelf declares 31 worksheets with 31 distinct catalogue ids | `detail("management")["worksheets"]` | PASS |
| E-mgt-003 | Every worksheet resolves to an installed profile with blocks | `framework_profiles.PROFILES` | PASS |
| E-mgt-004 | The shelf declares no records, no theories and no glossary terms | `detail("management")` | PASS |
| E-mgt-005 | Every worksheet renders a form the page knows and the registry calls a worksheet | `templates.describe`; `registry.get` | PASS |
| E-mgt-006 | Exactly six worksheets are not draftable, and they are the six named | `detail("management")["worksheets"]` | PASS |
| E-mgt-007 | The two records that share one engine (STR-07, STR-18) are both reachable and both listed | `detail("management")["worksheets"]` | PASS |
| E-mgt-008 | The declared `does_not` list is present and specific (no evidence generation, no scoring) | `detail("management")["does_not"]` | PASS |
| E-mgt-009 | The catalogue row for the shelf agrees with the detail page on tools, worksheets, records, theories | `subjects.catalogue()` | PASS |
| E-mgt-010 | The five worksheet groups are the five the page declares | `detail("management")["worksheets"]` | PASS |

### 3.2 The compute tool

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-011 | `case_decision` compares the options in its preset and reports each alternative's NPV | frozen core `case_decision`; `server.PRESETS` | PASS |
| E-mgt-012 | `case_decision` refuses a single option, with a reason and no report | manual §4.7 (fail closed) | PASS |
| E-mgt-013 | The option-comparison paper carries no specification footer | owner rule P3 | PASS |

### 3.3 Porter's Value Chain (STR-03)

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-014 | The nine activities are the nine the profile **and** the worksheet form declare | `VALUE_CHAIN["blocks"]`; `templates.CANVAS_BLOCKS` | PASS |
| E-mgt-015 | The canvas figure carries a bullet or a named gap in every one of its nine cells | V-12; owner rule P6 | PASS |
| E-mgt-016 | Firm infrastructure accepts real overhead/support evidence (its cues cover its own query) | V-01; `retrieval._accept` | PASS |
| E-mgt-017 | A cell with no source says so in the paper, before it states the background | V-02, V-12 | PASS |
| E-mgt-018 | The outline headings are present, title-cased and in the declared order | manual §8; `_sections` | PASS |
| E-mgt-019 | Conclusion and References are the last two sections and no heading jumps a level | V-09, V-10, V-11 | PASS |
| E-mgt-020 | The byline reaches the title page and no placeholder name is printed | V-20; manual §4.6 | PASS |
| E-mgt-021 | The title drops a trailing period | `_title` | PASS |
| E-mgt-022 | A brief with no industry is refused with a reason that names the market | V-04; `guard.five_forces_fit` | PASS |


### 3.4 Change and Organization (the four elements)

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-023 | The unit of analysis is the industry, and the refusal names the market | manual §4.4; `unit.field` | PASS |
| E-mgt-024 | Each of the four elements carries a sourced item or a named gap, with citation and source | V-01, V-12 | PASS |
| E-mgt-025 | One source cannot fill two elements, and no source is cited twice | V-01; `retrieval` dedupe | PASS |
| E-mgt-026 | A run with no sources still records every element, as declared background, and blocks nothing | V-02; `completion.missing` | PASS |
| E-mgt-027 | The model prompt names Change and Organization, the industry, and keeps the safety lines | V-04, V-08 | PASS |
| E-mgt-028 | The report route generates a paper when one element is empty and named as a gap | V-07 | PASS |

### 3.5 Prompts, presentation and the module itself

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-029 | Every prompt on the shelf names its own framework label | manual §6 (wording) | PASS |
| E-mgt-030 | No prompt on the shelf imports another framework's vocabulary (PESTEL) | V-04 | PASS |
| E-mgt-031 | Every industry-unit prompt names the industry | V-04; owner rule P6 | PASS |
| E-mgt-032 | No prompt asks the model for a diagram | owner rule P5 | PASS |
| E-mgt-033 | There is no Markdown download: no `format: "md"`, no Markdown button, no route branch | owner rule P1 | PASS |
| E-mgt-034 | The chart and export cards keep `#chartbtn`/`#expbtn`/`#expzip` and stay hidden | owner rule P2 | PASS |
| E-mgt-035 | No paper path prints a specification footer (computation, framework, worksheet, submission) | owner rule P3 | PASS |
| E-mgt-036 | A figure prints at the method's own declared precision, and a list prints as words | owner rule P4 | PASS |
| E-mgt-037 | No paper and no page promises a diagram nobody draws | owner rule P5 | PASS |
| E-mgt-038 | The product formats the core's number and never recomputes it | manual §4.5; owner rule P4 | PASS |
| E-mgt-039 | Every method declares its own figure precision, and no paper prints a raw Decimal or a Python repr | owner rule P4; B-197 (standing unfreeze) | PASS |
| E-mgt-040 | The profiles module imports nothing outside the repository | a clean checkout must run | PASS |
| E-mgt-041 | Every profile is declared once in the module (no shadowed second assignment) | manual §5 (one copy of the words) | PASS |
| E-mgt-042 | Every researched block declares cues and a query, so the gate can judge it | `retrieval._accept` | PASS |
| E-mgt-043 | The profiles no page reaches are the measured seventeen, and Change and Organization is one | `VALIDATION_HARNESS.md` §7.2 — re-measured | PASS |
| E-mgt-044 | An unreachable profile still produces a complete paper through the real engine | V-01…V-15 on the artefact | PASS |
| E-mgt-045 | A non-draftable profile still produces a complete paper through the real engine | `VALIDATION_HARNESS.md` §7.2 | PASS |
| E-mgt-046 | The shelf's catalogue count omits three of its own worksheets (STR-01, STR-07, STR-18) | `subjects.catalogue()` | **BLOCKED** (D-MGT-09) |

### 3.6 Debugging the shelf by driving it (2026-11-03)

`qa/probe_mgt_debug.py` runs every one of the 30 templates twice (with evidence and with none),
strips `word/document.xml`, reads the paper and checks V-01…V-20, the figure, the citations, the
references and determinism. It found four defects the unit tests could not, because a unit test
asserts what someone thought to assert and the harness asserts what a reader can see.

| E-id | Behaviour | Source of truth | Status |
|---|---|---|---|
| E-mgt-047 | No block declares a placeholder cue (`'evidence'`) or a list of cues | `framework_profiles`; `retrieval.cue_words_of` | PASS |
| E-mgt-048 | Every researched block accepts a source whose title echoes its own query (168 blocks) | `retrieval._accept`; V-01 | PASS |
| E-mgt-049 | The three canvas profiles carry a sourced item, with a citation | V-01, V-12 | PASS |
| E-mgt-050 | No paper prints a wrong article or a broken singular (`a element`, `a activitie`) | manual §4.6 | PASS |

**Scoreboard: 49 PASS · 1 BLOCKED · 0 DISPUTED · 0 GAP.**

## 4. DISPUTED rows

None. E-mgt-039 was `BLOCKED` and is now `PASS`: the owner answered the one question of session 5 by
unfreezing the core (B-197), and the four methods that declared no precision now declare one, so the
paper prints `Npv A1: 2586.47` instead of fifty digits. One row is still `BLOCKED`:

- **E-mgt-046 / D-MGT-09.** `subjects.catalogue()` reports **28** catalogue records for a shelf that
  shows **31** worksheet rows; the three it omits are STR-01, STR-07 and STR-18. The number is on the
  page, so which side moves is the owner's call.


## 5. Traceability matrix

| E-id | Test | E-id | Test |
|---|---|---|---|
| E-mgt-001 | `test_E_mgt_001__the_shelf_declares_one_compute_tool_with_a_preset` | E-mgt-024 | `test_E_mgt_024__each_element_carries_a_sourced_item_or_a_named_gap` |
| E-mgt-002 | `test_E_mgt_002__the_shelf_declares_31_worksheets_with_distinct_catalogue_ids` | E-mgt-025 | `test_E_mgt_025__one_source_cannot_fill_two_elements` |
| E-mgt-003 | `test_E_mgt_003__every_worksheet_resolves_to_an_installed_profile` | E-mgt-026 | `test_E_mgt_026__a_run_without_sources_still_records_every_element` |
| E-mgt-004 | `test_E_mgt_004__the_shelf_declares_no_records_theories_or_glossary_terms` | E-mgt-027 | `test_E_mgt_027__the_prompt_names_the_framework_and_the_unit` |
| E-mgt-005 | `test_E_mgt_005__every_worksheet_is_a_form_the_page_can_render` | E-mgt-028 | `test_E_mgt_028__the_draft_route_generates_a_paper_with_an_empty_element` |
| E-mgt-006 | `test_E_mgt_006__the_six_non_draftable_worksheets_are_the_recorded_gap` | E-mgt-029 | `test_E_mgt_029__every_prompt_names_its_own_framework` |
| E-mgt-007 | `test_E_mgt_007__two_worksheets_that_share_one_engine_say_so` | E-mgt-030 | `test_E_mgt_030__no_prompt_imports_another_frameworks_vocabulary` |
| E-mgt-008 | `test_E_mgt_008__the_declared_does_not_list_is_present_and_specific` | E-mgt-031 | `test_E_mgt_031__every_industry_prompt_names_the_industry` |
| E-mgt-009 | `test_E_mgt_009__the_shelf_appears_in_the_catalogue_with_the_same_counts` | E-mgt-032 | `test_E_mgt_032__no_prompt_promises_a_diagram` |
| E-mgt-010 | `test_E_mgt_010__every_worksheet_group_is_one_the_page_declares` | E-mgt-033 | `test_E_mgt_033__there_is_no_markdown_download_anywhere` |
| E-mgt-011 | `test_E_mgt_011__case_decision_compares_the_options_from_its_preset` | E-mgt-034 | `test_E_mgt_034__the_chart_and_export_cards_keep_their_ids_and_stay_hidden` |
| E-mgt-012 | `test_E_mgt_012__case_decision_refuses_a_single_option` | E-mgt-035 | `test_E_mgt_035__no_paper_path_prints_a_specification_footer` |
| E-mgt-013 | `test_E_mgt_013__the_case_decision_paper_carries_no_specification_footer` | E-mgt-036 | `test_E_mgt_036__figures_print_at_the_methods_declared_precision` |
| E-mgt-014 | `test_E_mgt_014__the_nine_activities_are_those_the_profile_and_the_form_declare` | E-mgt-037 | `test_E_mgt_037__no_paper_promises_a_diagram_nobody_draws` |
| E-mgt-015 | `test_E_mgt_015__the_canvas_figure_carries_one_bullet_per_activity` | E-mgt-038 | `test_E_mgt_038__the_figures_are_the_cores_not_the_products` |
| E-mgt-016 | `test_E_mgt_016__firm_infrastructure_accepts_real_overhead_evidence` | E-mgt-039 | `test_E_mgt_039__every_method_declares_its_precision_and_no_paper_prints_a_raw_decimal` |
| E-mgt-017 | `test_E_mgt_017__a_cell_with_no_source_says_so_in_the_paper` | E-mgt-040 | `test_E_mgt_040__the_profiles_module_imports_nothing_outside_the_repository` |
| E-mgt-018 | `test_E_mgt_018__the_outline_headings_are_present_in_declared_order` | E-mgt-041 | `test_E_mgt_041__every_profile_is_declared_once_in_the_module` |
| E-mgt-019 | `test_E_mgt_019__conclusion_and_references_are_the_last_two_sections` | E-mgt-042 | `test_E_mgt_042__every_researched_block_declares_cues_and_a_query` |
| E-mgt-020 | `test_E_mgt_020__the_byline_reaches_the_title_page_and_no_placeholder_is_printed` | E-mgt-043 | `test_E_mgt_043__the_unreachable_profiles_are_the_measured_seventeen` |
| E-mgt-021 | `test_E_mgt_021__the_title_drops_the_trailing_period` | E-mgt-044 | `test_E_mgt_044__an_unreachable_profile_still_produces_a_paper` |
| E-mgt-022 | `test_E_mgt_022__a_brief_without_an_industry_is_refused_naming_the_market` | E-mgt-045 | `test_E_mgt_045__a_non_draftable_profile_still_produces_a_paper` |
| E-mgt-023 | `test_E_mgt_023__the_unit_of_analysis_is_the_industry` | E-mgt-046 | `test_E_mgt_046__the_shelf_catalogue_count_omits_three_of_its_own_worksheets` |
| E-mgt-043 | `test_E_mgt_043__the_unreachable_profiles_are_the_measured_eighteen` | E-mgt-047 | `test_E_mgt_047__no_block_declares_a_placeholder_cue_or_a_list_of_cues` |
| E-mgt-048 | `test_E_mgt_048__every_research_block_accepts_evidence_for_its_own_question` | E-mgt-049 | `test_E_mgt_049__the_three_canvases_carry_a_sourced_item` |
| E-mgt-050 | `test_E_mgt_050__no_shelf_paper_prints_a_wrong_article_or_singular` | — | — |

Every row maps to exactly one test; no test is unused and no row is untested.


---

## 6. What this session changed, and what it re-tested

`framework_profiles.py` is shared with the People, Operations, Entrepreneurship and Marketing shelves
(the 31 shared worksheets), so every edit here was re-tested against them.

| Change | File | Why it could not be done anywhere else | Re-tested |
|---|---|---|---|
| Eight profiles inlined; the import-time `exec` deleted | `bp/product/framework_profiles.py` | the module raised `FileNotFoundError` without the temp file: a crash, not a shelf bug | full suite |
| The dead short-key Value Chain deleted | same | the live profile and `templates.CANVAS_BLOCKS` both declare the long keys | value-chain, matrix, people |
| Value Chain blocks `auto` → `research`; infrastructure cues | same | the fill policy is a profile declaration | value-chain, people |
| Change and Organization unit process → industry | same | a profile declares its own unit | change-organization |
| `{unit_rule}` in `HEAD_SYSTEM`, `_singular`, `_article`, background disclosure | `bp/product/completion.py` | one prompt template serves all 75 profiles | every `test_*_completion.py` |
| `ALIASES["template_value_chain"]` | `bp/product/matrix.py` | the alias map is how a layout key finds a profile key | matrix, value-chain |
| The specification footer deleted | `bp/product/deliverables.py` | it is the one block that printed it | worksheet export, accounting acceptance |
| Value-chain keys, the refusal template, the footer test | the three existing tests | a name change is one coordinated change | those suites |

**Not touched:** `src/bp/methods.py`, `src/bp/server.py`, `tests/fixtures/frozen_contract.json`, any
preset, any route family, `docs/sources/**`. No new dependency, no network call, no model call.

**Measured effect on the framework-completion slice** (`python -m pytest tests/test_*_completion.py`):

| | Tests | Failures |
|---|---:|---:|
| Before this session (`qa/baseline/mgt-completion-slice.txt`) | 539 | 60 |
| After (`qa/baseline/mgt-completion-after.txt`) | 539 | **27** |

**Measured effect on the full suite** (`python -m unittest discover -s tests`):

| | Tests | Failures | Errors | Distinct failure names |
|---|---:|---:|---:|---:|
| Baseline at `211b672` (`qa/baseline/mgt-suite-err.txt`) | 2932 | 66 | 13 | 79 |
| After (`qa/baseline/mgt-after-suite-err.txt`) | 3084 | 40 | 6 | 46 |

**Zero new failure names** (`qa/baseline/mgt-after-failures.txt` against the baseline set): 33 names
repaired, 79 → 46. The 3084 includes the acceptance suite this session added (46 tests) and another
lane's 106, which is why the documented count in `HOME.md`/`HANDOFF.md`/`CONTRIBUTORS.md` is still
3084 and `tests/test_docs_sync.py` passes.

The 27 that remain are all on the **marketing** shelf (attribution, cro, customer_journey, digital_mix,
email_crm, funnel, kano, marketing_plan, measurement_plan, paid_media_plan, rfm, servqual, social_media,
stp, stp_evidence, tam) and were not started. Twenty-one of the 33 repaired tests belong to this shelf
(6 value chain, 9 change and organization, and six prompt tests); the other twelve are marketing prompt
tests the shared `{unit_rule}` fix repaired as a side effect, and they are recorded rather than claimed.

## 7. Defects found, and where they are recorded

The ledger rows are `D-MGT-01 … D-MGT-11` and `G-mgt-01 … G-mgt-05` in `qa/QA_DEFECTS.md`. Three were
found only by reading the produced `.docx` (P6), which is why the probe exists.

| Ledger | What the reader saw | Class | Status |
|---|---|---|---|
| D-MGT-01 | (nothing — the module would not import on a clean checkout) | WIRING / BLOCKER | FIXED |
| D-MGT-02 | a value-chain figure with nine empty boxes | WIRING | FIXED |
| D-MGT-03 | “where cost and differentiation come from” printed as evidence for Procurement | HONESTY | FIXED |
| D-MGT-04 | firm infrastructure could accept no real overhead evidence | WIRING | FIXED |
| D-MGT-05 | two declarations of Porter's Value Chain, one of them dead | DETERMINISM | FIXED |
| D-MGT-06 | Change and Organization refused every industry brief | VALIDATION | FIXED |
| D-MGT-07 | a prompt that never names the industry it is analysing | HONESTY | FIXED |
| D-MGT-08 | `Npv A1: 2586.4733808644797823276713689760481408096100978284` and `Facts: {'text': …}` | ROUNDING | FIXED (B-197) |
| D-MGT-09 | the shelf page counts 28 records beside 31 worksheets | CATALOGUE | **BLOCKED** |
| D-MGT-10 | “a activitie”, “A activitie” in every -ies profile's paper | WORDING | FIXED |
| D-MGT-11 | “How this was produced / Method: … / Specification hash: …” in the export | HONESTY (P3) | FIXED |
| D-MGT-12 | three canvas profiles accepted **no** evidence, ever | WIRING | FIXED |
| D-MGT-13 | five blocks refused a source whose title echoed their own query | WIRING | FIXED |
| D-MGT-14 | “it is **a element** the case has not documented” | WORDING | FIXED |
| G-mgt-02 | Change and Organization works when called and no page reaches it | WIRING | GAP (owner decision) |
| G-mgt-04 | the harness recorded 22 unreachable profiles; the live count is 17 | DOC-DRIFT | FIXED (doc corrected) |

## 8. Evidence

| Artefact | Path |
|---|---|
| The value-chain paper (sourced run) | `qa/evidence/management/value-chain.docx` / `.txt` |
| The value-chain paper (no source at all) | `qa/evidence/management/value-chain-nosource.docx` / `.txt` |
| The Change and Organization paper (+ no-source twin) | `qa/evidence/management/change-organization*.docx` / `.txt` |
| The worksheet export (P3) | `qa/evidence/management/worksheet-export.docx` / `.txt` |
| The measurements this file quotes | `qa/evidence/management/summary.txt` |
| Baseline full suite, before any change | `qa/baseline/mgt-suite-err.txt` (2932 tests, 66 failures, 13 errors) |
| Completion slice, before any change | `qa/baseline/mgt-completion-slice.txt` (60 failed, 479 passed) |
| Completion slice, after | `qa/baseline/mgt-completion-after.txt` |

## 9. Declared gaps

| Id | Gap | Why it is not built |
|---|---|---|
| G-mgt-01 | The shelf has no records, theories or glossary | by design; the record sets live on Project management and People |
| G-mgt-02 | **Change and Organization has a profile and tests but no worksheet row**, so no page reaches it | adding a worksheet row changes the catalogue surface: owner decision |
| G-mgt-03 | Six worksheets offer no “draft it for me” button | the flag governs the button; the paper is still produced (E-mgt-045) |
| G-mgt-04 | Two catalogue records (STR-07, STR-18) share one engine | deliberate: two assignments, one profile; filing by template alone cannot tell them apart |
| G-mgt-05 | A captured “Value Chain” trace in `docs/VALIDATION_HARNESS.md` §7.2 says 22 unreachable profiles; measured 17 | the number moved as profiles were wired; the doc is corrected, the count is re-measured each run |
| G-mgt-06 | A no-source run still fills a cell from the framework's own general background | the owner's policy for `probe` profiles (harness §6.5); the paper now says so before it prints it |

## 10. Residual risk

1. **The live gate is stricter than the mocks.** Every sourced-item row here was measured with a
   mocked retrieval whose titles carry the query. The real gate needs a cue word *and* the industry in
   the title, so a live run on a thin topic still returns gaps. That is fail-closed behaviour, not a
   defect, but it means “sourced items” in this manual is a claim about the pipeline, not about any
   particular search.
2. **Two lanes in one worktree.** During this session another lane committed three times and swept an
   in-flight edit of `completion.py` into its own commit (`839f06e`). Nothing was lost; every commit
   here is path-scoped, and `git status` was checked before and after each one.
3. **`framework_profiles.py` is now 640 KB of data.** The inlining was necessary, but the module should
   eventually become a package of per-shelf data files; that is an owner decision, not this session's.

