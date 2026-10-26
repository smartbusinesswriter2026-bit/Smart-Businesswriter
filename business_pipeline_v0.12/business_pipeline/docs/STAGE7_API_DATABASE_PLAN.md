# Stage 7 API-based literature database — plan and first slice (decision B-040, PROVISIONAL)
**Owner direction (2026-10-21):** the research-pipeline manuals are not available, and the plan is to build an API-based literature database now, to be replaced or fronted by the proprietary database when it is finished. This is a data/retrieval layer, which the charter permits as a "shared interface / clearly unblocked piece"; it does **not** redefine the research pipeline.

## What is still blocked (unchanged)
The Stage 7 pipeline itself — the stage list from research problem to paper, the research-gap feasibility tiers, the qualitative/exploratory study taxonomy, data-output schemas, and citation/report requirements — is still blocked on the missing manuals (`docs/STAGE7_BLOCKER.md`). Nothing here reconstructs those from memory.

## What was built (first slice)
`src/bp/literature.py` + `tests/test_literature.py`, stdlib only, same rules as the model boundary:
- **Source boundary** (`Source`): `CrossrefSource` (REST, no key required) and `OpenAlexSource` (free, no key). Remote responses are untrusted data; a 404 means "DOI does not resolve" and errors are mapped, never retried silently.
- **`verify_reference(title, doi=None, source=None)`** returns a `Reference`. A citation is `verified` only when a DOI is provided, it resolves, and the title matches exactly after case/punctuation/whitespace normalisation. Everything else is `unverified_user_supplied` (fail-closed), which is the status the system can already hold offline.
- **No key required** for Crossref/OpenAlex basic metadata; the only optional config is `BP_CROSSREF_MAILTO` for a polite Crossref User-Agent.

## PROVISIONAL rules the manuals will replace (owner to confirm)
1. **"Verified" threshold.** Exact normalised-title equality is deliberately strict. The manual may instead require title *and* author match, or allow subtitle/substring variants. Until it arrives, strict equality fail-closes toward "unverified".
2. **Which sources.** Crossref primary, OpenAlex fallback. The manual may require a fixed source list (e.g. add PubMed, arXiv, Semantic Scholar) or forbid some.
3. **Citation format.** Not implemented (manual-defined). References stay as structured records, not formatted citations.
4. **What the system may never do.** Not implemented here, but binding from the charter: it may never cite from memory or invent studies. A reference with no DOI is always `unverified_user_supplied`.

## Still needed (in order)
1. **Source priority + failover policy** and any additional APIs the owner wants (arXiv, PubMed, Semantic Scholar, Europe PMC).
2. **Verification rules** for references supplied without a DOI (title/author/year search), if the owner wants any, and the accepted match threshold.
3. **Proprietary-database interface**: when the proprietary database exists, it should implement the same `Source` boundary so the rest of the system does not change.
4. **The research-pipeline manuals** to unblock the actual Stage 7 stages (still the hard blocker).

## Tests
`python -m unittest tests.test_literature tests.test_literature_api`: request construction (Crossref URL encoding + User-Agent, OpenAlex URL), title match/mismatch/canonicalisation, unresolved DOI, 404 vs non-404 error mapping, OpenAlex field mapping, and the HTTP endpoints (sources list, verify, 400/429/502) with a fake injected source. **Live smoke test (2026-10-21):** both Crossref and OpenAlex resolved DOI `10.1038/nature12373` and the exact title verified. Broader coverage of sources, formats and rate-limit behaviour is still unevaluated.
