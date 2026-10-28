# Agent instructions

Before working on the business writer chat, read:

- `business_pipeline_v0.12/business_pipeline/docs/CONDUCTOR_MANUAL.md` — the goal, paper model, framework/computation rules and extension checklist.
- `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md` — current build, tests and open work.

The chat is the macro conductor: it owns the decision, thesis, framework stack,
computation blocks and paper plan. Subject modules provide frameworks and
computations; the writer and DOCX renderer only format. Do not add a framework
by editing the sample builder or renderer.

Non-negotiables:

- no invented evidence, sources, numbers or citations;
- gaps are named, never filled;
- student inputs stay student inputs;
- no silent framework substitution;
- computations come from the frozen core;
- a paper never contains template instructions;
- export is blocked when the paper is incomplete.
