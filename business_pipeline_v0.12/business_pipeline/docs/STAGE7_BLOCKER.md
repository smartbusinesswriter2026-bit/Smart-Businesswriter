# Stage 7 (research-gap, study-design and manuscript workflow): blocked, and exactly what is needed
**Status: BLOCKED for the pipeline definition; a first clearly-unblocked piece is built.** Nothing from the pipeline was reconstructed from memory. The charter (Stage 7) says: follow the original research-pipeline manual; if it is unavailable, build only the shared interfaces and clearly unblocked pieces, and do not redefine the pipeline from assumptions. Under the owner's API-database plan (B-040), the literature retrieval/verification boundary is now that first shared interface (`src/bp/literature.py`, see `docs/STAGE7_API_DATABASE_PLAN.md`). The stage list, gap tiers and study taxonomy below are still blocked.

## What is missing
The Smart Researcher research-pipeline manuals. The UI review (v0.1) describes them only second-hand ("earlier Smart Researcher design discussions") and states they were not available as files. They are not in this project's files either.

## Questions the manuals must answer before Stage 7 can start
1. The stage list from research problem or question to proposal and paper, with inputs, outputs and user checkpoints for each stage.
2. The **research-gap feasibility tiers** (the UI review names: literature-only, existing public data, computational end to end, new empirical work). Exact names, rules for assigning a tier, and how they relate to the manual's T1 to T4 (the charter says they classify different things and must not be conflated).
3. The study-type taxonomy, especially the **qualitative and exploratory** path and its instruments.
4. The data outputs expected (statistical analysis and CSV outputs are mentioned; schemas are not).
5. How literature is searched, retrieved and **verified**: which sources or APIs, what counts as a verified citation, what the system may never do (cite from memory, invent studies).
6. Citation and reference style requirements, and what the manuscript must contain (methods generated from the run log, evidence appendix).
7. Rules for **synthetic data** in a paper (the charter says it must be labelled and never presented as observed).
8. Institutional AI-use, ethics and privacy requirements the UI must show.
9. What is already implemented in code for the research pipeline, if anything, and must be preserved exactly.
10. Whether "papers" means academic papers or business reports (open question 5 in manual v0.3), because verification differs.

## What can be reused when the manuals arrive
The frozen Problem Spec, hashed artifacts, provenance tags (including synthetic), claim licensing with wording ceilings, the sandbox and re-performance bundles, the registry (frameworks and theories as pointers), the evidence-with-provenance pattern used by the templates, and the statistics methods (descriptive, correlation, regression, two-group tests).

## What cannot be done offline
Verifying citations needs a retrieval service. The owner has now decided that service: an API-based literature database via public scholarly APIs (Crossref primary, OpenAlex fallback) while the proprietary database is under construction (B-040). The first slice (`src/bp/literature.py`) resolves a DOI and marks a citation `verified` only on a strict title match; citation formatting and the manual's exact verification rules are still open.

## How to unblock
Provide the manuals (or the old chat exports that define the research pipeline) and say which research-gap path to build first. I will then do the charter's audit (inventory, conflicts, gaps) before any code. The retrieval layer no longer waits on the manuals; the pipeline definition still does.
