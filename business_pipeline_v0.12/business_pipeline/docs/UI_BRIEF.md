# Website UI brief (owner instruction)

**Status: owner instruction, 2026-10-21 — for the design owner (MiniMax in OpenCode).** The backend product sequence is complete; this is the UI phase. **First response must be a plan plus clarifying questions — no code until the owner approves it.**

Read with: [`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) (frozen core + product lane), [`CONTRIBUTORS.md`](CONTRIBUTORS.md) §1A/§1B, [`PRODUCT_BACKEND_PLAN.md`](PRODUCT_BACKEND_PLAN.md) Phase 5, [`DECISIONS.md`](DECISIONS.md) B-079/B-080/B-087/B-089.

## 1. What is being built

The workbench front end for the local product: a website that calls the existing local API and presents verified results. It is **presentation only**: every number, caveat, limitation, honesty notice, tier label and refusal message displayed must come from the API unchanged.

Start from the current vanilla-JS shell `web/index.html` served by the frozen server (`GET /`). You may replace its structure and styling; if you introduce a build step it must emit static files served by the same server, with no new routes. Work in **your own git worktree and branch** (`opencode/ui-site`) off `master`.

## 2. Brand assets (owner-supplied, at the workspace root — outside this repo)

- **Logo** (the website's logo): `D:\SMART BUSINESSWRITER\smart-business-writer-logo.png` — a navy + green mark (open book with rising bar chart), wordmark **Smart BusinessWriter**, tagline `BUSINESS | ACCOUNTING | ECONOMICS | FINANCE`. Copy it into `web/assets/logo.png` and commit that copy; sample the exact palette from the PNG (navy ≈ `#143E68`, green ≈ `#1E9E6B` — treat these as approximate until sampled).
- **Inspiration screenshot**: `D:\SMART BUSINESSWRITER\A1.jpg` — use it for **layout inspiration only**. Do not ship it, and do not copy its text or claims.

## 3. Layout direction from A1 — imitate the structure, not the content

**Keep (structure):**
- a narrow fixed **left icon rail**;
- a **centered hero**: logo mark above a short headline;
- a large **central action box** with a secondary controls row inside it;
- a row of **quick-action chips** beneath the box;
- a **floating circular chat button** in the bottom-right corner.

**Remove (owner instructions, non-negotiable):**
- the top-right **API / Enterprise / Pricing / Login / Sign up** items — delete them completely; v1 is local single-user, so no pricing, auth or API pages;
- the whole **"Trusted by 11 Million+ Researchers Worldwide"** block and the university logos (Harvard, Yale, Cambridge, Johns Hopkins, Stanford) — delete the block and the row entirely; **no fake social proof, counts or testimonials anywhere**.
- the top bar, if kept at all, is minimal: brand at the left and at most a local-status/help affordance; nothing invented.

**The circular chat button is retained** but restyled to the brand (logo mark and/or brand colors). It opens the optional **local assistant/help panel**, and must be honest: model assistance is **off by default**; when unconfigured the panel says so, there are no API keys in the browser, and the panel never presents model output as verified computation.

## 4. Left rail — the product's actual features, colored icons

Rail items are the website's real capabilities (final labels, icon choice and colors are the design owner's call in the plan; each is a distinct, brand-consistent color, with tooltip + accessible label, collapsed by default with an active state):

| # | Feature | What it opens | API it consumes |
|---|---|---|---|
| 1 | Home / New analysis | objective box, method + preset catalogue, session creation | `GET /api/presets`, `GET /api/methods`, `POST /api/sessions`, `POST /api/sessions/{id}/confirm|reject`, `GET /api/sessions/{id}` |
| 2 | Cases | stored cases, versions, comparison, reviewer sign-off, backup/restore | `GET/POST /api/cases`, `GET/DELETE /api/cases/{id}`, `/versions`, `/compare`, `/signoff`, `/backup`, `/restore`, `/backups` |
| 3 | Data | CSV/XLSX ingestion, sheet + merged-cell policy, column → method-input mapping | `POST /api/ingest` |
| 4 | References | DOI verification, APA 7 / Harvard citations, retrieval audit log, drift check | `GET /api/literature/sources`, `POST /api/literature/verify`, `GET /api/literature/log`, `GET /api/literature/drift` |
| 5 | Deliverables | HTML report, charts, CSV/SpreadsheetML, case backup | `POST /api/cases/{id}/render`, `POST /api/cases/{id}/export`, `/api/cases/backup` |
| 6 | Accounts | management accounts / ledger engagement flow (a preset + two checkpoints) | via `/api/presets` + `/api/sessions` |
| 7 | Frameworks & templates | SWOT, Five Forces, case decision; the catalogue registry | `GET /api/frameworks`, `GET /api/frameworks/{id}`, `GET /api/templates`, `GET /api/templates/{id}` |
| 8 | Assistant & method info | optional local assistant; method catalogue, limitations, honesty | `GET /api/assist/config`, `GET /api/methods` |
| 9 | Status | health, version, request-log state (dev-facing) | `GET /api/health` |

**Current served UI (2026-10-27, build 0.67, B-092):** the rail enumerates the ten subjects (with Entrepreneurship) plus the Calculator. Items 7 (Catalogue) and 8 (Assistant) are **no longer surfaced in the served UI**; their backend routes remain and the assistant lane is retained for a later release. Item 9 (Status) remains, reached from the health pill rather than the rail. Subject pages carry their own catalogue-only tables and worksheet tiles, and the Calculator lists every calculation, so no computation or method is lost.

## 5. Fonts

- **UI text: a sans-serif system stack only** — e.g. `system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`. No remote/web fonts (the product is offline), no more than two families.
- **Generated document text is a document, not UI: Times New Roman (serif).** That applies to report/DOCX bodies when shown as a document preview. The current HTML export is a computation-owner file with Georgia; do not edit it — if the UI needs document typography it applies its own CSS to report text it displays.

## 6. Non-negotiables (computation/design boundary)

- You may edit **`web/**` only** (plus your own design notes in the plan/branch). Do not edit `src/bp/**`, `tests/**`, `tests/fixtures/**`, the frozen contract fixture, or factual docs.
- **Display, never compute.** Every number shown must be a value returned by the API, printed exactly as returned — no client-side sums, averages, percentages, rounding, rescaling or "nice" numbers. Charts come from `/api/cases/{id}/render`; never draw chart geometry in JavaScript from API values.
- **Never alter or hide** caveats, honesty notes, limitations, tier/review labels, blocked reasons, provenance notes, or claim wording. Show them adjacent to the results, in the API's words.
- **No invented content**: no fake data, metrics, researchers, testimonials, logos, ratings, or claims. Any example/demo content must be labelled "example".
- **Offline**: no external network calls, no CDNs (fonts, icons, JS). Icons are inline SVG or locally committed, license-clean assets.
- No new server routes without a request: if a screen genuinely needs one, write a `[design]` note in `WORKLOG.md` and stop — the computation owner adds the contract first, then you build against it.

## 7. Strings the existing tests assert (frozen; keep them present somewhere sensible)

`web/index.html` is asserted by the suite, so keep these strings until a coordinated change:
- Assistant panel: `Assistant (optional)`, `Challenge my analysis`, `The model writes no numbers`
- Ingestion card: `Data ingestion (structured files)`, `id="ingfile"`, `Ingest file`, `/api/ingest`, `no PDF text extraction or OCR`
- References panel: `References (optional)`, `Verify reference`, `/api/literature/sources`, `Retrieval audit`, `Get citation`, `Show retrieval log`, `Check drift`, `id="refstyle"`, `APA 7`, `Harvard`
- Session/accounts: `Draft work plan`, `Account mapping`, `Download financial statements`
- Templates: `Load the`

## 8. Plan-mode deliverable (your first reply — no code)

1. **Information architecture** and the final left-rail list: labels, colored icon style, tooltip/accessible names, active/collapsed behavior.
2. **Screen map**: each screen → API calls → loading/empty/error/blocked/honesty states.
3. **Wireframes** (ASCII or text) for: Home, New analysis, Results/report, Cases list, Case detail (versions, comparison, sign-off), Data ingestion, References, Deliverables/exports, Status, Assistant panel.
4. **Design tokens** sampled from the logo: exact palette hexes, type scale, spacing, radii, shadows; light theme (A1 is light) and whether dark is in scope.
5. **Component inventory**: prompt box, chips, cards, tables, tabs, banners (blocked / honesty / limitations), toast, modal, sign-off record, comparison table, chart container (SVG from the API), disclosure of provenance.
6. **Responsive + accessibility plan**: rail collapse, focus order, contrast, labels, reduced motion.
7. **Phased build plan** with a first slice that is genuinely shippable (suggest: shell + rail + Home + New analysis + Results, then Cases, Data, References, Deliverables, then Assistant/Status).
8. **Test-impact statement**: where each §7 string lives in the new design; no test edits.
9. **Questions for the owner** — list every ambiguity you would otherwise guess at (visual density, tone, whether a top bar is allowed at all, which screens are v1, whether the chat button opens a panel or a chat log, sample case data for demos, dark mode, language/branding of the tagline, etc.).

**Wait for the owner's approval of the plan before writing code.** After approval: implement in phases, keep the full suite green (frozen-contract and docs-state guards included), commit on `opencode/ui-site`, and record any backend need as a `[design]` WORKLOG request rather than inventing an endpoint.
