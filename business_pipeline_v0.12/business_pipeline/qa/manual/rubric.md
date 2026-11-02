# Rubric reader â€” acceptance manual

**Subject:** any shelf (a rubric is shelf-neutral).
**Module:** `src/bp/product/rubric.py`. **Decision:** B-187. **Suite:** `tests/test_product_rubric.py`.
**Increment:** reading and refusals (R1). Binding to a paper is the next increment â€” see Â§7.

This is the manual that did not exist. Every row cites a source of truth: the module contract
itself (rank 1), the owner's instruction of 2026-11-02 (rank 3), and the paper rules in
`docs/CONDUCTOR_MANUAL.md` Â§4/Â§8 and `docs/VALIDATION_HARNESS.md` Â§5 (rank 3). No row states an
opinion, and no row states a behaviour the code does not have.

---

## 1. Who it serves

A student who is given a **rubric** â€” a marking guide â€” and told to write to it. The rubric is the
only input in the product that changes what the paper must *do*: its required sections, its word
budget, and the concrete elements each criterion asks for ("shows a break-even calculation",
"cites three sources"). It serves every shelf and every course level, because the marking guide is
the student's, not the product's.

## 2. Scope, and what this increment does not do

| Built now | Not built yet (declared) |
|---|---|
| Read a rubric in three layouts (pipe table, numbered/bulleted list, headed criteria) | Binding the parsed rubric to the paper's outline and word band |
| Carry weight, descriptor, required elements, sections, word budget, citation style | A "Rubric coverage" appendix section on the paper |
| Refuse a rubric it cannot read, preserving the raw text | Blocking export when a *required* criterion has no content |
| Ask the student to confirm an uncertain parse (`confirm_required`) | The upload surface (this increment has no route; the next one adds it) |
| Never score, never invent a weight, never convert pages to words | An OCR engine chain for a scanned rubric (see the OCR plan) |

The declared limits are repeated in `docs/KNOWN_LIMITATIONS.md` under **Rubric**. Source: B-187.

## 3. The reader contract

### 3.1 Inputs

| Layout | Recognised as | Example |
|---|---|---|
| `table` | a header row, a `---` separator row, then one row per criterion; at least two `|` in the header | `| Criterion | Weight | Descriptor |` |
| `list` | a line beginning with a bullet, a number, or a letter, that states a weight or a `name: descriptor` pair | `2. Evidence - 40% - should include three sources` |
| `none` | nothing recognisable | prose, a title, a case brief |

Column roles are matched by name, not by position: `criterion|criteria|assessment|item|element|
component|area|task|question` â†’ name; `weight|weighting|%|percent|percentage|marks|points|value`
â†’ weight; `descriptor|description|criteria for|standard|expectation|requirement|detail` â†’
descriptor; `required|must include|should include|evidence|includes|elements` â†’ required elements.

### 3.2 Outputs

`parse(text)` returns `format`, `ok`, `layout`, `criteria[]` (`name`, `weight`, `weight_text`,
`descriptor`, `required_elements[]`), `sections[]`, `word_budget` (`words`, `tolerance`, `text`),
`citation_style`, `total_weight`, `problems[]`, `confirm_required`, `chars`, `text`,
`scores_nothing`. `summary(parsed)` returns the badge-sized subset. `as_json(parsed)` is stable.

### 3.3 The six rules (each one is a refusal to invent)

| Rule | Statement |
|---|---|
| R1 | A **weight** is read only when the rubric states one; otherwise it is `None`. No `1/n` is ever assumed. |
| R2 | Weights that miss 100 are **reported, never rescaled** â€” rescaling rewrites the student's own statement. |
| R3 | A **required element** comes only from an explicit column or clause, and is carried **verbatim**, split on `;` and `â€¢` only. |
| R4 | A **word budget** is read only from a stated number of words. A page limit is never converted. |
| R5 | **Sections** come only from an explicit structure label (`Required sections`, `Structure`, `Report structure`, `Outline`, `Headings`). |
| R6 | A **citation style** is named only when exactly one is named; two named styles are a problem, not a choice. |

### 3.4 Refusals and the confirm flag

| Condition | Behaviour |
|---|---|
| text shorter than 15 characters | `ok: False`, problem names the empty/short text |
| text longer than `MAX_CHARS` (200 000) | `ok: False`, problem names the limit; the text is **not** truncated |
| no criterion readable | `ok: False`, problem asks the student to confirm the criteria |
| parse usable but uncertain (no weights, partial weights, total â‰  100, ambiguous style) | `ok: True`, every cause named in `problems`, `confirm_required: True` |
| parse complete and consistent (all weights present, total 100, one style) | `ok: True`, `problems: []`, `confirm_required: False` |

`confirm_required` is the product's honesty switch: when it is true the student must see and
confirm the parsed criteria before a paper follows them.


## 4. Expected behaviour â€” `E-rub-001â€¦018`

| E-id | Statement (atomic, testable) | Source of truth |
|---|---|---|
| E-rub-001 | A pipe-table rubric is read with its stated weights, in the row order written; weights 30/40/30 give `total_weight` 100 and no problem. | B-187 R1; module contract |
| E-rub-002 | A numbered-list rubric (`N. Name - 30% - descriptor`) is read with the same fields as a table. | B-187 Â§3.1 |
| E-rub-003 | A weight is never invented: a rubric stating none gives `weight: None` on **every** criterion, a named problem, and `confirm_required: True`. | B-187 R1 |
| E-rub-004 | Weights that miss 100 are reported with the stated total and are **not** rescaled. | B-187 R2 |
| E-rub-005 | A rubric with no readable criterion is not half-read: `ok: False`, `criteria: []`, raw text preserved, confirm required. | B-187 Â§3.4 |
| E-rub-006 | An empty or too-short rubric is refused by name. | B-187 Â§3.4 |
| E-rub-007 | A stated word budget is read as an integer of words with its tolerance (`2,500 words (+/- 10%)` â†’ 2500, 0.10). | B-187 R4 |
| E-rub-008 | A page limit is never converted into a word budget (`8 pages` â†’ `word_budget: None`). | B-187 R4 |
| E-rub-009 | Required elements are carried verbatim from an explicit clause, and a criterion with no clause gets an empty list. | B-187 R3 |
| E-rub-010 | A descriptor is carried verbatim and is never rewritten or re-worded. | B-187 R3 |
| E-rub-011 | Sections are read only from an explicit structure label, in the order written. | B-187 R5 |
| E-rub-012 | One named citation style is taken (`APA 7th` â†’ `apa`; `Harvard` â†’ `harvard`). | B-187 R6 |
| E-rub-012b | Two named citation styles are refused, not chosen, and the problem names both. | B-187 R6 |
| E-rub-013 | The reader scores nothing: no mark, grade, awarded score or "percent met" key exists in `parse` or `summary`. | `VALIDATION_HARNESS.md` Â§5.2 (quality is a human step) |
| E-rub-014 | The parse is deterministic and JSON-safe: the same text twice gives equal results and equal JSON; a round trip preserves `criteria`. | `CONDUCTOR_MANUAL.md` Â§7.5 (determinism) |
| E-rub-015 | The reader imports neither the frozen core nor any network client. | `HANDOFF.md` non-negotiables 5â€“6 |
| E-rub-016 | A lead-in line is not a criterion: "The report is marked on:" never becomes a criterion row. | B-187 R1 (trap found by `qa/probe_rubric.py`) |
| E-rub-017 | A bare number in a `Marks`/`Weight`/`%` column is the weight (25/45/30 â†’ 100, no problem). | B-187 R1 (trap: the `\b` defect that dropped `30%`) |
| E-rub-018 | A rubric longer than the limit is refused by name and **not** truncated. | B-187 Â§3.4; `documents.py` limit rule |

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

**Scoreboard: 19 rows, 19 PASS, 0 FAIL, 0 BLOCKED.** Green under both
`python -m pytest tests/test_product_rubric.py` (19 passed) and
`python -m unittest tests.test_product_rubric` (19 OK).

## 6. Defects found and fixed during this increment

| ID | Severity | Defect | Found by | Fix | Trap test |
|---|---|---|---|---|---|
| D-RUB-01 | BLOCKER | `WEIGHT_RE` ended in `\b`, so `30%` at the end of a cell never matched and **every percentage weight was silently dropped** (`weighted: 0` on a rubric whose weights total 100). | `qa/probe_rubric.py` | the boundary is taken after the word alternatives only | `E-rub-017`, `E-rub-001` |
| D-RUB-02 | MAJOR | An unbulleted lead-in line ("The report is marked on:") was read as a criterion. | `qa/probe_rubric.py` | an unbulleted row with no weight must carry a descriptor | `E-rub-016` |

Both were caught by the probe before the suite existed; neither reached a paper, because nothing
binds a rubric yet.

## 7. Known gaps (declared, never converted into an expectation)

| Gap | Declared in | Consequence today |
|---|---|---|
| **Binding is not built.** Nothing reads a parsed rubric yet: the outline, the word band and the required elements are not driven by it. | B-187; `docs/KNOWN_LIMITATIONS.md` | A paper does not yet follow a rubric. |
| **No coverage appendix, no export gate on a required criterion.** | B-187 | A paper cannot yet report which criteria it addresses. |
| **No upload role or button for a rubric specifically.** | B-187 | The next increment adds the role, the route and the surface. |
| **A scanned rubric needs OCR.** The reader takes text. | OCR plan; `requirements-optional.txt` | Unreadable text is refused by name, never guessed. |
| **Quality is a human judgement.** The reader cannot say whether a criterion is *met well*. | `VALIDATION_HARNESS.md` Â§5.2 | Stated on the paper; never replaced by a machine score. |

## 8. What only a human can find (not tested here)

1. Whether the parsed criterion names are the course's own vocabulary â€” a rubric may use house
   labels ("Q1", "Criterion A") that the reader faithfully copies and a human must map.
2. Whether a required element is *adequately* evidenced by the prose: presence is mechanical,
   adequacy is judgement.
3. Whether the uploaded rubric belongs to this assignment at all (a student may attach last term's).
