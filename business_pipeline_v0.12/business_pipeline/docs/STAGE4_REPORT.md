# Stage 4 report: first end-to-end business-case slice (2026-10-21)
**Status: PARTIAL.** The charter's default vertical slice (case facts, alternatives, one verified calculation, a report that separates facts, assumptions, computed results and judgment) is built for net present value. It was built after Stages 5 and 6, which it reuses.

## What was built (`case_decision`, tier T2 "custom analysis")
You supply: case facts (each tagged user, sourced, assumption or synthetic); 2 to 5 alternatives, each citing the facts it follows from and carrying its own cash flows and their provenance; a base discount rate and a [low, high] range; and optionally a decision rule (currently only "highest_npv"). The system:
1. computes each alternative's NPV with the vetted T1 method, in the sandbox;
2. finds every discount rate in your range where the NPV ranking of two alternatives changes (crossover rates), by grid scan and bisection;
3. reports the ranking at the base rate and at both ends of your range;
4. states a preference **only under your decision rule**, and says whether it holds across the whole range; with no rule it says no alternative is recommended;
5. flags alternatives resting on assumed cash flows, an assumed discount rate, synthetic inputs and negative NPVs.
The report is a fixed narrative whose every number is an artifact reference, followed by your facts and alternatives reproduced verbatim (your names and text are inserted after the audit and are never executed). Nothing is invented: no facts, alternatives, weights or winner.

## Verification (15 frozen checks)
Standard NPV checks for each alternative (second implementation, zero-rate boundary, t0 shift); base values against an independent recomputation; each crossover is a root of the NPV difference and the ranking flips there; a different, denser grid finds no missed crossover; ranking matches the recomputed order; reordering the alternatives changes nothing; analysis contains only supplied text and cash flows exactly as given; recommendation recomputed independently and absent without a rule; flags correct; deterministic rendering.

## Tests
`python -m unittest discover -s tests`: **199 tests, OK** (181 before; 18 new). Hand-checked cases: a crossover at exactly 10% (110/(1+r) = 121/(1+r)^2) and a two-root case (roots at 10% and 20%, from -100x^2 + 230x - 132 = 0). Intake errors (19 kinds), exact tie, dominance, rule on and off, token look-alikes in names, sandbox parity and re-performance with tampering detected, and eleven deliberately defective builders (wrong NPV, dropped or shifted crossover, swapped winners, reversed ranking, invented alternative, embellished fact, altered cash flow, false stability, wrong preference, unflagged assumption) plus an invented recommendation without a rule, all blocked.
Design note from testing: default alternative ids are positional (A1, A2), so reordering alternatives renames them; the invariance check therefore compares by name. Supply your own ids to keep them stable.

## What this slice does not do
- No model is involved: the system cannot read a case narrative, find facts, propose alternatives, or challenge your reasoning. The charter's independent-reviewer and student-feedback steps are not built.
- NPV only: no break-even comparison, probabilities, risk adjustment, unequal project lives, or multi-criteria scoring with your weights.
- It does not know whether your cash flows are realistic or your facts accurate.
- Custom analysis (T2) built on a method whose own expert review is still pending.

## Open items
B-029 to B-031 in `docs/DECISIONS.md`. The biggest one: whether to introduce a model provider so the system can propose alternatives and challenge reasoning under the same verification rules.
