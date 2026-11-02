# Rubric reader — acceptance manual

**Subject:** any shelf (a rubric is shelf-neutral).
**Module:** `src/bp/product/rubric.py`. **Decision:** B-187. **Suite:** `tests/test_product_rubric.py`.
**Increment:** reading and refusals (R1). Binding to a paper is the next increment — see §7.

This is the manual that did not exist. Every row cites a source of truth: the module contract
itself (rank 1), the owner's instruction of 2026-11-02 (rank 3), and the paper rules in
`docs/CONDUCTOR_MANUAL.md` §4/§8 and `docs/VALIDATION_HARNESS.md` §5 (rank 3). No row states an
opinion, and no row states a behaviour the code does not have.

---

## 1. Who it serves

A student who is given a **rubric** — a marking guide — and told to write to it. The rubric is the
only input in the product that changes what the paper must *do*: its required sections, its word
budget, and the concrete elements each criterion asks for ("shows a break-even calculation",
"cites three sources"). It serves every shelf and every course level, because the marking guide is
the student's, not the product's.

## 2. Scope, and what this increment does not do

| Built now | Not built yet (declared) |
|---|---|
| Read a rubric in three layouts (pipe table, numbered/bulleted list, headed criteria) | The upload role and button for a rubric specifically (the intake store has roles; the rubric button does not exist) |
| Carry weight, descriptor, required elements, sections, word budget, citation style | An OCR engine chain, so a scanned rubric can be read |
| Refuse a rubric it cannot read, **before** any research run, preserving the raw text | A "Recommendations" section the engine writes � the engine never writes advice |
| Ask the student to confirm an uncertain parse (`confirm_required`) | A score, a mark or a predicted grade of any kind |
| Measure coverage against the finished paper (addressed / partly / named gap) | Section injection: a rubric heading the profile does not have is reported, not created |
| Report the rubric's word budget beside the paper's own count | |
| Block export on an unaddressed **weighted** criterion, with the criterion named, and demote to warnings when the student turns the gate off | |
| Never score, never invent a weight, never convert pages to words | |

The declared limits are repeated in `docs/KNOWN_LIMITATIONS.md` under **Rubric**. Source: B-187.

## 3. The reader contract

### 3.1 Inputs

| Layout | Recognised as | Example |
|---|---|---|
| `table` | a header row, a `---` separator row, then one row per criterion; at least two `|` in the header | `| Criterion | Weight | Descriptor |` |
| `list` | a line beginning with a bullet, a number, or a letter, that states a weight or a `name: descriptor` pair | `2. Evidence - 40% - should include three sources` |
| `none` | nothing recognisable | prose, a title, a case brief |

Column roles are matched by name, not by position: `criterion|criteria|assessment|item|element|
component|area|task|question` → name; `weight|weighting|%|percent|percentage|marks|points|value`
→ weight; `descriptor|description|criteria for|standard|expectation|requirement|detail` →
descriptor; `required|must include|should include|evidence|includes|elements` → required elements.

### 3.2 Outputs

`parse(text)` returns `format`, `ok`, `layout`, `criteria[]` (`name`, `weight`, `weight_text`,
`descriptor`, `required_elements[]`), `sections[]`, `word_budget` (`words`, `tolerance`, `text`),
`citation_style`, `total_weight`, `problems[]`, `confirm_required`, `chars`, `text`,
`scores_nothing`. `summary(parsed)` returns the badge-sized subset. `as_json(parsed)` is stable.

### 3.3 The six rules (each one is a refusal to invent)

| Rule | Statement |
|---|---|
| R1 | A **weight** is read only when the rubric states one; otherwise it is `None`. No `1/n` is ever assumed. |
| R2 | Weights that miss 100 are **reported, never rescaled** — rescaling rewrites the student's own statement. |
| R3 | A **required element** comes only from an explicit column or clause, and is carried **verbatim**, split on `;` and `•` only. |
| R4 | A **word budget** is read only from a stated number of words. A page limit is never converted. |
| R5 | **Sections** come only from an explicit structure label (`Required sections`, `Structure`, `Report structure`, `Outline`, `Headings`). |
| R6 | A **citation style** is named only when exactly one is named; two named styles are a problem, not a choice. |

### 3.4 Refusals and the confirm flag

| Condition | Behaviour |
|---|---|
| text shorter than 15 characters | `ok: False`, problem names the empty/short text |
| text longer than `MAX_CHARS` (200 000) | `ok: False`, problem names the limit; the text is **not** truncated |
| no criterion readable | `ok: False`, problem asks the student to confirm the criteria |
| parse usable but uncertain (no weights, partial weights, total ≠ 100, ambiguous style) | `ok: True`, every cause named in `problems`, `confirm_required: True` |
| parse complete and consistent (all weights present, total 100, one style) | `ok: True`, `problems: []`, `confirm_required: False` |

`confirm_required` is the product's honesty switch: when it is true the student must see and
confirm the parsed criteria before a paper follows them.

### 3.5 Binding: coverage, the appendix and the export gate

`completion.complete(..., rubric=�)` reads the rubric **before any research runs** (a marking guide
that cannot be read costs a sentence, not a wasted run) and refuses one it cannot read. It attaches
the parsed rubric to the completion result; `completion.draft(result)` then measures it:

| Step | Rule |
|---|---|
| Coverage | `rubric.coverage(parsed, sections)` compares each criterion with the paper's **headings** and with the **required elements** it states. `addressed` = a heading names it and every stated element is present; `partially` = some of that; `gap` = neither. Matching is case-insensitive and token-based, and is never shown as a judgement of quality. |
| Order of measurement | Coverage is measured **before** the "Rubric coverage" appendix is inserted, so the appendix cannot satisfy the criterion it reports on (`E-rub-022`). |
| Appendix | The paper gains a level-1 section **Rubric coverage** immediately before the reference list: one line per criterion with its weight, its status and where it is addressed, plus a statement that gaps are reported, not filled. It contains no score and no mark. |
| Word budget | `report["word_target"]` carries the rubric's stated words, its tolerance and the paper's own count. With a tolerance, `met` is a real comparison against the stated range; **without one, `met` is `None`** � a bare count does not say floor or ceiling, and guessing would invent a requirement (`E-rub-023`). |
| Gate on | `paper.missing(state)` names every criterion in `coverage["blocking"]` (a **weighted** criterion that is a gap, or every criterion when the rubric states no weights), so the Word export is blocked with the criterion named (`E-rub-024`). |
| Gate off | `state["rubric_gate"] = False` demotes every row to a `medium` warning: nothing is required, the rows are still reported, and the choice is recorded on the paper (`E-rub-025`). |


## 4. Expected behaviour — `E-rub-001…018`

| E-id | Statement (atomic, testable) | Source of truth |
|---|---|---|
| E-rub-001 | A pipe-table rubric is read with its stated weights, in the row order written; weights 30/40/30 give `total_weight` 100 and no problem. | B-187 R1; module contract |
| E-rub-002 | A numbered-list rubric (`N. Name - 30% - descriptor`) is read with the same fields as a table. | B-187 §3.1 |
| E-rub-003 | A weight is never invented: a rubric stating none gives `weight: None` on **every** criterion, a named problem, and `confirm_required: True`. | B-187 R1 |
| E-rub-004 | Weights that miss 100 are reported with the stated total and are **not** rescaled. | B-187 R2 |
| E-rub-005 | A rubric with no readable criterion is not half-read: `ok: False`, `criteria: []`, raw text preserved, confirm required. | B-187 §3.4 |
| E-rub-006 | An empty or too-short rubric is refused by name. | B-187 §3.4 |
| E-rub-007 | A stated word budget is read as an integer of words with its tolerance (`2,500 words (+/- 10%)` → 2500, 0.10). | B-187 R4 |
| E-rub-008 | A page limit is never converted into a word budget (`8 pages` → `word_budget: None`). | B-187 R4 |
| E-rub-009 | Required elements are carried verbatim from an explicit clause, and a criterion with no clause gets an empty list. | B-187 R3 |
| E-rub-010 | A descriptor is carried verbatim and is never rewritten or re-worded. | B-187 R3 |
| E-rub-011 | Sections are read only from an explicit structure label, in the order written. | B-187 R5 |
| E-rub-012 | One named citation style is taken (`APA 7th` → `apa`; `Harvard` → `harvard`). | B-187 R6 |
| E-rub-012b | Two named citation styles are refused, not chosen, and the problem names both. | B-187 R6 |
| E-rub-013 | The reader scores nothing: no mark, grade, awarded score or "percent met" key exists in `parse` or `summary`. | `VALIDATION_HARNESS.md` §5.2 (quality is a human step) |
| E-rub-014 | The parse is deterministic and JSON-safe: the same text twice gives equal results and equal JSON; a round trip preserves `criteria`. | `CONDUCTOR_MANUAL.md` §7.5 (determinism) |
| E-rub-015 | The reader imports neither the frozen core nor any network client. | `HANDOFF.md` non-negotiables 5–6 |
| E-rub-016 | A lead-in line is not a criterion: "The report is marked on:" never becomes a criterion row. | B-187 R1 (trap found by `qa/probe_rubric.py`) |
| E-rub-017 | A bare number in a `Marks`/`Weight`/`%` column is the weight (25/45/30 → 100, no problem). | B-187 R1 (trap: the `\b` defect that dropped `30%`) |
| E-rub-018 | A rubric longer than the limit is refused by name and **not** truncated. | B-187 §3.4; `documents.py` limit rule |
| E-rub-019 | A paper heading that names a criterion (case-insensitively, by its own words) marks that criterion `addressed`, and the heading is named in `where`. | B-187 §3.5 (coverage) |
| E-rub-020 | A criterion no heading and no element mentions is a named `gap`; when it carries a weight it is `blocking` and the gate reads `blocked`. | B-187 §3.5 |
| E-rub-021 | A stated required element that does not appear in the paper downgrades an otherwise-present criterion to `partially`, and the element is named. | B-187 §3.5 |
| E-rub-022 | The "Rubric coverage" appendix is present, sits before the reference list, names every gap, and **cannot** turn a gap into an addressed criterion. | B-187 §3.5 (order of measurement) |
| E-rub-023 | The word budget is reported with the paper's own count; with a stated tolerance `met` is a real comparison, without one `met` is `None`. | B-187 §3.5 |
| E-rub-024 | An unaddressed **weighted** criterion blocks export, and `paper.missing` names the criterion in words. | `CONDUCTOR_MANUAL.md` §8 (export gate) |
| E-rub-025 | With `rubric_gate` false, nothing is required before export and every gap is still reported as a `medium` warning. | B-187 §3.5 (owner choice recorded) |
| E-rub-026 | A rubric that cannot be read is refused by `complete` **before** any research run, with the reader's own reason. | B-187 §3.5 (fail fast) |
| E-rub-027 | Coverage is deterministic (same paper, same rows) and carries no mark, grade or score. | `VALIDATION_HARNESS.md` §5.2 |
| E-rub-028 | A paper completed without a rubric is unchanged: no appendix, no `rubric` key in the report. | B-187 (no silent behaviour change) |


## 5. Traceability matrix

| E-id | Test (`tests/test_product_rubric.py`) | Status |
|---|---|---|
| E-rub-001 | `test_e_rub_001__a_table_rubric_carries_its_stated_weights` | PASS |
| E-rub-002 | `test_e_rub_002__a_numbered_list_rubric_carries_its_stated_weights` | PASS |
| E-rub-003 | `test_e_rub_003__a_weight_is_never_invented` | PASS |
| E-rub-004 | `test_e_rub_004__weights_that_miss_a_hundred_are_reported_not_rescaled` | PASS |
| E-rub-005 | `test_e_rub_005__an_unreadable_rubric_asks_the_student_instead_of_guessing` | PASS |
| E-rub-006 | `test_e_rub_006__an_empty_rubric_is_refused_by_name` | PASS |
| E-rub-007 | `test_e_rub_007__a_stated_word_budget_is_read_with_its_tolerance` | PASS |
| E-rub-008 | `test_e_rub_008__a_page_limit_is_never_converted_into_a_word_budget` | PASS |
| E-rub-009 | `test_e_rub_009__required_elements_are_carried_verbatim` | PASS |
| E-rub-010 | `test_e_rub_010__a_descriptor_is_never_rewritten` | PASS |
| E-rub-011 | `test_e_rub_011__sections_are_read_from_an_explicit_structure_label` | PASS |
| E-rub-012 | `test_e_rub_012__one_named_citation_style_is_taken` | PASS |
| E-rub-012b | `test_e_rub_012b__two_named_citation_styles_are_refused_not_chosen` | PASS |
| E-rub-013 | `test_e_rub_013__the_reader_scores_nothing` | PASS |
| E-rub-014 | `test_e_rub_014__the_parse_is_deterministic_and_json_safe` | PASS |
| E-rub-015 | `test_e_rub_015__the_reader_reaches_neither_the_core_nor_the_network` | PASS |
| E-rub-016 | `test_e_rub_016__a_lead_in_line_is_not_a_criterion` | PASS |
| E-rub-017 | `test_e_rub_017__a_bare_number_in_a_marks_column_is_the_weight` | PASS |
| E-rub-018 | `test_e_rub_018__an_oversized_rubric_is_refused_by_name_not_truncated` | PASS |
| E-rub-019 | `test_e_rub_019__a_heading_that_names_the_criterion_addresses_it` | PASS |
| E-rub-020 | `test_e_rub_020__a_criterion_the_paper_never_mentions_is_a_named_gap` | PASS |
| E-rub-021 | `test_e_rub_021__a_stated_element_that_is_absent_downgrades_to_partial` | PASS |
| E-rub-022 | `test_e_rub_022__the_appendix_reports_coverage_and_cannot_satisfy_it` | PASS |
| E-rub-023 | `test_e_rub_023__the_word_budget_is_reported_and_never_guessed` | PASS |
| E-rub-024 | `test_e_rub_024__a_weighted_criterion_gap_blocks_export` | PASS |
| E-rub-025 | `test_e_rub_025__turning_the_gate_off_demotes_the_rows_to_warnings` | PASS |
| E-rub-026 | `test_e_rub_026__an_unreadable_rubric_is_refused_before_any_research` | PASS |
| E-rub-027 | `test_e_rub_027__coverage_is_deterministic_and_scores_nothing` | PASS |
| E-rub-028 | `test_e_rub_028__a_paper_without_a_rubric_is_unchanged` | PASS |


**Scoreboard: 29 rows, 29 PASS, 0 FAIL, 0 BLOCKED.** Green under both
`python -m pytest tests/test_product_rubric.py` (19 passed) and
`python -m unittest tests.test_product_rubric` (19 OK).

## 6. Defects found and fixed during this increment

| ID | Severity | Defect | Found by | Fix | Trap test |
|---|---|---|---|---|---|
| D-RUB-01 | BLOCKER | `WEIGHT_RE` ended in `\b`, so `30%` at the end of a cell never matched and **every percentage weight was silently dropped** (`weighted: 0` on a rubric whose weights total 100). | `qa/probe_rubric.py` | the boundary is taken after the word alternatives only | `E-rub-017`, `E-rub-001` |
| D-RUB-02 | MAJOR | An unbulleted lead-in line ("The report is marked on:") was read as a criterion. | `qa/probe_rubric.py` | an unbulleted row with no weight must carry a descriptor | `E-rub-016` |
| D-RUB-03 | MAJOR (QA tool) | `qa/_count.py` put `qa/` on `sys.path`, shadowing a module during discovery: it reported **2878** where the gate computed **2880**, so the counter disagreed with the check it exists to predict. | the docs gate disagreeing with the counter | the script rebuilds the gate's own context before counting | the counter now agrees with `test_docs_sync` |
| D-RUB-04 | MAJOR | An unreadable rubric was validated **after** the research run, so a brief with a broken rubric wasted four research queries before reporting the error. | writing `E-rub-026` | the rubric is read immediately after the computation-boundary guard, before any block is researched | `E-rub-026` |
| D-RUB-05 | MAJOR (data corruption, self-inflicted) | Two PowerShell passes double-decoded UTF-8 while editing docs, turning `—` into `├óΓé¼ΓÇ¥` in `HOME`, `HANDOFF`, `CONTRIBUTORS`, `WORKLOG` and this manual. | git showing whole-file diffs | three files restored from HEAD; `WORKLOG.md` and this manual reverse-transcoded; verified 0 mojibake markers with their `B-188` work and all section marks intact | the diffs are now line-level, not whole-file |

D-RUB-01 and D-RUB-02 were caught by the probe before the suite existed; D-RUB-04 was caught while
writing the test that proves the fail-fast rule; D-RUB-05 was caught by reading the whole-file diff
git showed. None of them reached a paper a student would submit.

### 6.1 How the corruption was found, because it will happen again

`Get-Content -Raw` in Windows PowerShell 5.1 decodes a UTF-8 file with the system ANSI code page, and
`Set-Content -Encoding utf8` then writes the mojibake back as valid UTF-8 — so the file is silently
doubly-encoded and every non-ASCII character changes. **The lesson is not "be careful": it is that a
file edit must go through a tool that states its encoding.** Every edit in this increment was made
with an editor or with `[IO.File]::WriteAllText(..., UTF8Encoding($false))`, and the repair was
verified by counting `§`, `—`, `•` and the mojibake markers rather than by eye.

## 7. Known gaps (declared, never converted into an expectation)

| Gap | Declared in | Consequence today |
|---|---|---|
| **Section injection is not built.** A rubric heading the profile does not have (for example "Recommendations") is reported as a gap, never created as an empty section. | B-187; `docs/KNOWN_LIMITATIONS.md` | The student must add that section themselves; the appendix names it. |
| **No upload role or button for a rubric specifically.** The intake store has roles and a "use as the instruction" action; a rubric action does not exist yet. | B-187 | The reader and the gate are reachable from the API and the engine, but the page has no rubric button. |
| **A scanned rubric needs OCR.** The reader takes text. | OCR plan; `requirements-optional.txt` | Unreadable text is refused by name, never guessed. |
| **Quality is a human judgement.** The reader cannot say whether a criterion is *met well*. | `VALIDATION_HARNESS.md` §5.2 | Stated on the paper; never replaced by a machine score. |
| **The engine never writes advice.** A rubric demanding "recommendations" gets a named gap, not prose. | B-154; B-187 | The student writes the recommendation; the system only checks whether something is there. |

## 8. What only a human can find (not tested here)

1. Whether the parsed criterion names are the course's own vocabulary — a rubric may use house
   labels ("Q1", "Criterion A") that the reader faithfully copies and a human must map.
2. Whether a required element is *adequately* evidenced by the prose: presence is mechanical,
   adequacy is judgement.
3. Whether the uploaded rubric belongs to this assignment at all (a student may attach last term's).
