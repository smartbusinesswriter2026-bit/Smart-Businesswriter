# business_pipeline (Stage 5 first increment)
Tests: `python3 -m unittest discover -s tests -v` (run from this folder; Python 3.10+, stdlib only)
Run the workbench: `PYTHONPATH=src python3 -m bp.server 8000` then open http://127.0.0.1:8000
API: POST /api/sessions, POST /api/sessions/{id}/confirm|reject, GET /api/sessions/{id}, GET /api/presets
API also: GET /api/methods (discovery, never executes). Methods: npv, breakeven, descriptive_stats, pearson (falls back to spearman), spearman, ols (falls back to ols_robust), ols_robust, welch_t (falls back to mann_whitney), mann_whitney. See docs/ for decisions, limitations, STAGE0_REPORT.md and STAGE5_REPORT.md.

Sandbox: the server runs computations in a guarded subprocess by default (`python -m bp.server 8000`). Use `--no-sandbox` only for development.
Re-performance: `python -m bp.reperform bundle.json` (set PYTHONPATH=src) re-runs a delivered bundle and compares outputs.

Registry (Stage 6): `src/bp/data/registry_v0_2.json` is generated from the catalogue: `PYTHONPATH=src python -m bp.catalogue_import docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md src/bp/data/registry_v0_2.json`. API: GET /api/frameworks?q=&type=, GET /api/frameworks/{id}; POST /api/sessions/{id}/confirm accepts {"frameworks": [ids]}. A request with no `method` returns a framework-only (T4) answer.

Templates: methods `template_swot` and `template_five_forces` take your own evidence (see GET /api/templates for the input format and an example). They organize and audit evidence; they compute and invent nothing.

Business case: method `case_decision` compares 2-5 of your own alternatives by NPV, finds where the ranking changes across your rate range, and states a preference only under your decision rule. See GET /api/templates/case_decision for the input format and an example.

Spike (Stage 8): `python spike/run_custom_arm.py` runs the ledger trap cases against the custom kernel (src/bp/ledger.py). Not wired into the pipeline. See docs/STAGE8_SPIKE_REPORT.md. Stage 7 is blocked: docs/STAGE7_BLOCKER.md.

Model assistance (optional, off by default; providers: `deepseek`, `openai`, `anthropic`): see docs/MODEL_PROVIDER_REPORT.md for setup (environment variables) and the rules it runs under. The model proposes; code validates; you confirm; it writes no numbers.

Stage 7 literature source (first slice): `src/bp/literature.py` resolves and verifies references by DOI (Crossref primary, OpenAlex fallback). The research pipeline itself is still blocked: docs/STAGE7_BLOCKER.md and docs/STAGE7_API_DATABASE_PLAN.md.
