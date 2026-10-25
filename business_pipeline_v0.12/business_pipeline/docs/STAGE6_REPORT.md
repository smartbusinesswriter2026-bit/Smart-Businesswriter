# Stage 6 report: framework, model, method and theory registry (2026-10-21)
**Status: PARTIAL.** Import, registry, contextual recommendation and user selection are built and tested. Framework templates, contraindications and evidence review are not.

## Sources read
Catalogue v0.2 (the supplied .md; all eight table sections, section 11 quantitative methods, section 12 theories, the record template and selection rules). Build Charter sections 5 and 6 (Stage 6). Prototype v0.1 (its hard-coded framework lists are superseded by the registry). The Business Frameworks catalogue's own warning applies throughout: its entries are candidates, each needing source checking.

## Audit: conflicts and gaps (nothing silently resolved)
| # | Finding | Handling |
|---|---|---|
| 1 | 15 catalogue rows have composite types (F/M, Q/M, Q/process, F/reference standard...). The charter says to model these as separate linked records. | Primary type plus `secondary_types` plus `type_note` (B-021). Not split into two records. |
| 2 | Theory of Change and Logic Model are listed twice (CHG-07/IMP-01, CHG-08/IMP-02). | Merged into one record each; both IDs resolve. Differences in wording kept in `*_alt` fields. |
| 3 | **Possible duplicate not merged:** CHG-09 "PDSA" and OPS-12 "PDCA / PDSA". Names differ, so the importer treats them as distinct. | Left as two records; owner decision needed. |
| 4 | Catalogue status words (candidate, reviewed, prototype, validated, approved, retired) differ from the charter's (catalogued, specified, prototyped, tested, approved, deprecated). | Two separate fields: `pipeline_status` (charter words) and `evidence_status` (my vocabulary: unreviewed, source_checked, reviewed, disputed, validated). The evidence vocabulary is **my own** and needs owner approval (B-023). |
| 5 | Quantitative methods (section 11) and theories (section 12) have no IDs; they are prose bullets naming several items each. | One record per bullet (50 Q, 7 T) with importer-assigned positional IDs (QNT-FIN-01, THE-02...). These IDs are fragile if the catalogue is reordered (B-022). Items inside a bullet are not split. |
| 6 | Theory member lists (e.g. Maslow, Herzberg...) are split from prose. | Heuristic; flagged `members_note: verify`. |
| 7 | Standards and proprietary items (ISO 31000, SCOR, PMBOK, COBIT, ITIL and anything typed "reference") need edition and permission checks. | Flagged `verify_edition_and_permissions`; shown in the UI and the report. No licensing review was done. |
| 8 | The catalogue supplies no limitations, contraindications or evidence ratings. | Left empty or "unreviewed". Nothing invented. The charter's "contraindications" and "state what it will miss" cannot be met until someone curates them. |

## What was built
- **Importer** (`catalogue_import.py`): deterministic markdown to JSON; the shipped registry equals a fresh import (tested). 91 table rows to 89 records; plus 44 Q and 7 T bullets = **140 records** (61 F, 22 M, 50 Q, 7 T), with source file hash, catalogue version and registry hash.
- **Registry** (`registry.py`): schema validation, search by name, alias or text, and a typed record view.
- **Method links:** six catalogue Q bullets link to implemented, tested methods (NPV, break-even, descriptive statistics, two-group tests, correlation and regression, sensitivity), always marked **partial** with what is not covered.
- **Recommendations:** transparent lexical matching (field-weighted, rare-word weighted, synonym groups, acronym expansion, generic words down-weighted). Rules from catalogue section 13: minimum sufficient set (at most four frameworks or models, two quantitative methods, two theories); a framework named in the request is honoured and flagged if nothing else in the request points to it; theories are never offered as templates; when nothing fits the system says so. Every suggestion states why, what evidence it needs, and that its status is unreviewed.
- **User choice:** nothing is applied unless the user ticks it. The selection (at most six) is frozen into the Problem Spec with the registry version and hash, so it changes the spec hash. Selections can come from suggestions, the user's own naming, or a library search.
- **Framework-only (T4) delivery:** a request with no method now returns "how to structure this and what data is needed", with no computed answer. For computed analyses the selection appears in the appendix and is stated **not** to have changed the computation.
- Workbench: suggestion list with checkboxes, evidence status, available methods, a library search box. API: `/api/frameworks?q=&type=` and `/api/frameworks/{id}`.

## Evaluation
`tests/fixtures/framework_requests.json`: 14 tuning cases and 7 held-out cases, including negatives (a poem, a trivia question, a translation). After tuning the routing policy on the tuning set only, **14/14 tuning and 7/7 held-out** pass. Read this carefully: the same author who read the catalogue wrote the held-out cases and their expected answers, there are only seven, and the matching is lexical, so a request that does not use the catalogue's words (for example "a new supermarket is taking our customers" without the word "competition") will miss. Expert-written cases are still needed. The expected IDs are my reading of the catalogue and are marked `expert_review: pending`.

## Tests
`python -m unittest discover -s tests`: **161 tests, OK** (125 before). Registry: import fidelity, counts, duplicates, composite types, nothing-invented checks, validation against deliberately corrupted data, method-link integrity, determinism. Recommendations: both fixture splits, explanation and caps, theories-never-templates, no-fit, named-by-user. Flow: selection frozen into the spec, invalid or oversized selections rejected, rejected sessions record nothing, framework-only delivery, API and UI content.
**Not tested:** the UI in a browser; real user requests; synonym and weight choices beyond the fixtures.

## Open items for the owner
- B-021 to B-026 in `docs/DECISIONS.md` (type handling, positional IDs, status vocabularies, the PDSA/PDCA question, routing policy values, selection cap).
- Who curates limitations, contraindications and evidence status, and from which sources.
- Whether to build framework templates next (for example SWOT and Five Forces as structured, evidence-linked outputs), which is the real Stage 6 "specify templates" step.

---
# Increment 2: framework templates, SWOT and Five Forces (2026-10-21)
**Status: PARTIAL.** Two structured templates. Every other catalogue framework is still suggestion-only.

## What was built
- **`template_swot`** (registry STR-07, plus the STR-18 "evidence-to-action" audit layer): your evidence items go into strengths, weaknesses, opportunities and threats exactly as you assign them (internal and external scope fixed by the framework). Your strategic options must each cite the items they follow from; a TOWS pairing label (SO, ST, WO, WT) is derived only when an option cites items from exactly one internal and one external dimension. The audit lists empty quadrants, items with no resulting option, items resting on assumptions, synthetic items, and materiality only if you rated it.
- **`template_five_forces`** (STR-01): evidence per force, with your own low, moderate or high rating and a one-line rationale. A rating without supporting evidence for that force is rejected. Forces with no evidence are reported as gaps. No score and no overall industry measure is produced.
- **Nothing is invented.** The system adds no evidence, rating, weight, option, score or ranking (charter 1.3). Fixed narrative has no digits; counts come from artifacts; your evidence is reproduced verbatim in a listing after the narrative audit, labelled user-supplied, sourced (with your source), assumption (unsupported) or synthetic.
- Tier T4 (framework only, nothing computed). Run inside the sandbox when it is on. Requesting a template records its registry entries as selected in the frozen spec (source "requested_template"). Each delivery carries a re-performance bundle.
- Workbench: suggestions with a template show a "Load the template request" button that fills the request box with a synthetic example to replace with your own evidence; presets `swot` and `five_forces`; `GET /api/templates` and `/api/templates/{id}`.

## Verification (frozen before running, recomputed from your raw input)
Each item placed exactly once and in the dimension you assigned; counts agree with an independent recount; every input text appears verbatim in the listing; nothing appears that was not supplied; scopes match the framework definition; TOWS labels recomputed; gaps reported, not filled; assumption and synthetic flags correct; for Five Forces, ratings match yours, unrated forces carry none, and no aggregate key exists; rendering is deterministic.

## Tests
`python -m unittest discover -s tests`: **181 tests, OK** (161 before; 20 new). Includes intake error messages, hand-checked counts and TOWS labels, end-to-end deliveries, sandbox parity and re-performance with tampering detected, API, and fourteen deliberately defective builders (dropped, moved, altered or invented items, wrong scope, wrong labels, unflagged assumptions, invented or changed ratings, an added score, a filled gap, evidence on the wrong force) all blocked.
**Defect found and fixed while testing:** the one-line check let tab and newline characters through, so a multi-line evidence text could have forged extra listing lines (for example a fake "[E9]" entry). It now rejects every control character and line separator.
**Not tested:** the UI in a browser; very large inputs beyond the 60-item cap; real users' evidence.

## Open items
- Rating scale (low, moderate, high) and materiality scale are provisional; the catalogue defines none (B-027).
- The system cannot judge whether an item is truly internal or external, or whether evidence is accurate; quality depends on what you supply.
- No templates yet for PESTEL, VRIO, Value Chain, Business Model Canvas or the other frameworks; the catalogue says each should stay separate (B-028).
