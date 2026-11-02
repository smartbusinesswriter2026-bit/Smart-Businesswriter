# Entrepreneurship deliverable — VALIDATION_HARNESS §5

Produced by `python qa/probe_ent_plan.py` through the real path (chat.start → confirm_plan → set_inputs → compute → draft → export), offline and without a model.

| Rule | Status | Evidence |
|---|---|---|
| V-01 no invented evidence | PASS | no source was retrieved, so the paper asserts no external claim; 0 recorded sources |
| V-02 gaps named, never filled | PASS | 4 of 4 market dimensions name a gap in words; state['gaps'] carries nothing (no research run) |
| V-03 student inputs stay student inputs | PASS | the business description and the operations plan reproduce the student's own words |
| V-04 no silent framework substitution | N/A | a paper profile is not a framework: nothing was substituted or declared |
| V-05 computations come from the frozen core | PASS | 5 plan blocks re-run from their stored inputs: frommarket=same, breakeven=same, depreciation=same, proforma=same, sensitivity=same |
| V-06 no instructions or template text | PASS | paper.check meta_text issues: 0 |
| V-07 export blocked when incomplete | PASS | an incomplete plan is refused with 15 named items, e.g. ['the business name', 'what the business sells'] |
| V-08 the model does not research | PASS | no model was called; the draft is deterministic and no prose proposal exists |
| V-09 no heading level jump | PASS | structural issues: none |
| V-10 the paper has a Conclusion | PASS | Conclusion present |
| V-11 the paper has a reference list | PASS | reference heading: References |
| V-12 every dimension has a sourced item or a named gap | PASS | 4 market dimensions present, 4 of them naming a gap (no retrieval was run) |
| V-13 every reference is cited in the body | PASS | no reference-list entry exists to cite, because no source was retrieved |
| V-14 the Introduction states the decision and the thesis | HUMAN | the Executive Summary names the business, the market and the declared target revenue |
| V-15 the Conclusion answers the thesis and adds no evidence | HUMAN | the Conclusion restates the declared figures and claims nothing new |
| V-16 the Discussion integrates the frameworks | N/A | the plan integrates sections, not frameworks |
| V-17 no sentence claims more than a method licenses | PASS | claim_problems: none |
| V-18 combined papers name the origin of each item | N/A | the plan is one profile, not a combination of frameworks |
| V-19 the word count is inside the requested band | N/A | the plan declares no word target; a rubric word budget is reported, never enforced |
| V-20 no placeholder name, and the byline reaches the title page | PASS | no byline was declared and none is printed; 0 placeholder hits |
| B-187 the marking guide is followed | PASS | coverage: Market analysis: partially; Financial plan: addressed; Operations plan: addressed; Risks and limitations: addressed; Referencing: addressed |
