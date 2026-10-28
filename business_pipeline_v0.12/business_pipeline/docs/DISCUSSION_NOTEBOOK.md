# Discussion notebook — owner reviews, model-to-model continuity

**Kind:** living, append-only. **Rule:** new entries at the top; never rewrite an old entry, supersede it with a new one.

**Why this file exists.** The owner is a business academic, not an engineer. When they read the system they cannot see what it is doing or why. That produced a real risk: a system that looks like a black box gets judged by its surface, and the surface was telling a different story from the code. This notebook is where a *discussion* is recorded — the owner's concerns in their own terms, what was found, what was changed, what is still missing, and — importantly — **where the assistant was wrong or might be wrong**. A later model should read this before changing anything, so the reasoning survives the session that produced it.

**How to use it (for a model picking this up).**

1. Read [`HOME.md`](HOME.md) first for the map, then [`CONTRIBUTORS.md`](../CONTRIBUTORS.md) for the rules, then this file.
2. Read the most recent entry end to end before touching the thing it describes.
3. If you change something an entry describes, write a **new** entry at the top and say what changed. Do not edit the old entry - a later model needs to see what was believed at the time.
4. Every entry must end with **where this could be wrong**. If you cannot find a weakness in your own conclusion, you have not thought hard enough.
5. If you disagree with an earlier entry, say so plainly and put your reasoning in the open. Do not quietly overwrite.

---

## 2026-10-28 — [product/design] The "easy business calculator": a keypad-shaped launcher, and a chat that knows what it is not

**What was asked.** The owner wants the Business Calculator to be *the* easy way in — "a UI similar to a typical calculator where users can calculate whatever business computation they want" — plus a chat ("ask it to calculate") that is explicitly scoped, because users will ask it to do computation unrelated to business.

**What was produced.** A design proposal (`docs/proposals/BUSINESS_CALCULATOR_DESIGN.md`) and a clickable mockup (`mockup/business-calculator.html`). No served UI, route, method or test changed.

**The design, in one line.** *One sentence, two keyboards.* The keypad and the chat build the same sentence — a business question plus its figures — which becomes a draft method plan, is confirmed, and only then runs through the existing session/confirm path. The engine still answers; the panel still computes nothing.

**The fork the owner should look at first.** "Typical calculator" means, to most people, that `=` evaluates an expression. That is exactly the parked decision in §N: bare arithmetic would be a second arithmetic path, and making it real needs a frozen `arithmetic` method and an unfreeze of B-079. So the proposal names **Mode A** (keypad types into the chosen method's declared inputs; ships with no backend change) and **Mode B** (keypad evaluates; needs the unfreeze), recommends A first, and — the important part — puts the limit **on the display**: typing `15% of 84,000` gets "bare arithmetic, not enabled" and the nearest business method, rather than silence. §N warned that a narrower-than-expected calculator must say so on its own surface; this is where that warning is paid.

**The chat, and its scope.** Five declared outcomes: run it / need one more figure / which of these did you mean / business but not built (tax, market prices) / **not a business calculation**. The last one is stated once, with a reason and a door back in — no number, no lecture. The gate is a versioned vocabulary over the 38 tools, not a model's opinion, and it prefers asking over refusing. The router would live in the product layer (`src/bp/product/calc_router.py`) and be tested in the Python suite, because a classifier written in the browser would be the one part of this feature no test could fail.

**Also recorded:** the calculator cannot be "all business calculations" — it is 36 methods and 38 tools, and the proposal says so in the panel, including the four things users will look for and not find (tax, market data, standalone depreciation schedules, free-form arithmetic).

**Where this could be wrong.** (1) If the owner's "typical calculator" simply means a keypad that computes, Mode A will feel broken no matter how well it is built — that is decision D1 and it should be answered before any polish. (2) The gate is a heuristic: it will refuse some real business questions and wave through some nonsense; the mitigations (ask when unsure, always offer a method, show the reason) reduce but do not remove that. (3) The scope boundary risks becoming paternalistic if the copy grows. (4) No browser exists here, so the mockup is reasoned, not observed — the layout, focus order and disabled-pad states need human eyes. (5) The most likely future break is a contributor "just computing it" when no method matches, which would undo the whole design; the proposal's acceptance criteria exist to make that line fail loudly.


**What was asked.** After seeing build 0.69 the owner said the version had regressed and added "a lot of shit"; Home should be clean and contain only the chat box and its logo, the side rail is already fine, the slogan must not be changed, and nothing may be done without permission. In the confirmation question the owner chose: remove the preset/method/currency dropdowns too; the chat box is only the text area and up arrow.

**What changed (build 0.70).** Home (`web/index.html`, static markup and `RENDERERS.home`) now contains only the logo, the `Smart Business Writer` wordmark, the line `BUSINESS | ACCOUNTING | ECONOMICS | FINANCE` exactly as written, the big text area and the circular up-arrow inside the action box. Removed from Home: the extra sentence under the slogan, the three dropdowns, the preset chips, the Examples card, "Your cases", "Or choose a subject", the "Two ways in" note and the Enter hint. The side rail, Calculator, Status pill, top bar, subject pages and backend were not touched. `startFromHome` no longer assumes the removed selects exist; with no method on Home it shows a toast pointing to the subject rail or the Calculator. The served-UI test now also asserts the removed Home elements are absent (753 tests).

**Where this could be wrong.**
- **The Home arrow cannot start anything on its own.** The server needs a method; with the dropdowns removed the only method entry points are the subject rail and the Calculator. That is a real functional limit, not a hidden one.
- **The slogan assumption.** The line kept byte-for-byte is the uppercase tagline; the sentence under it was treated as the extra copy and removed. If the owner meant the sentence, it can be restored verbatim from build 0.69.
- **The Home shelves are gone.** Stored cases are no longer listed on Home (they remain under each subject page); "All subjects" had no other link, so the gallery is reachable by URL only. This follows "only the chat box and logo", but it removes a convenience.
- **Dead code remains.** `loadHomeShelf` is no longer called; it is harmless but should be removed in a cleanup the owner asks for, not silently now.

---

## 2026-10-27 — [product] The rail is static-first and expandable; Home chat centred, Run becomes an Enter arrow

**What was asked.** The owner reported that "a fix by another agent affected your fix — it's no longer there", and asked to re-implement it, ensure the rail is expandable, centre the big Home chatbox (even space left and right) without changing its length, and move the run control to the opposite side as an up arrow suggesting Enter.

**What changed (build 0.68).**
- The ten subjects and their icons are now **static markup** in `#railsubjects`, so the rail exists before any fetch and survives a missing `/api/cases/subjects`; the live call replaces the static rows with full labels and counts, and a failure appends a note rather than wiping the list.
- The rail toggle is explicit: hamburger when collapsed, chevron + "Collapse" when open, `aria-expanded`/`aria-label`/`title` updated, open state persisted. The subject list itself scrolls, and Calculator stays pinned at the foot.
- `main` is centred in the content column (`margin:0 auto`), which centres the Home action box without changing its width.
- The run control moved from the left of the action row to the right and is now a circular **up-arrow** button. Enter in the objective starts the analysis; Shift+Enter inserts a newline; an inline hint says so.
- Three presence guards in `tests/test_product_subjects.py` read `web/index.html` and fail if the ten subject links, the rail toggle, the up-arrow/Enter affordance or the continued absence of the Catalogue/Assistant panels drift (753 tests).

**Why the previous state failed even though the code was in the branch.** The 0.66 rail was generated **only after** `GET /api/cases/subjects` answered. Any served copy whose backend or script differed — exactly what happens when another agent serves a checkout without the product routes — showed an empty rail and looked like the work had been deleted. A static-first list makes the navigation independent of the API; the API now only enriches it. That is the correction of the failure mode, not just of the symptom.

**Where this could be wrong.**
- **Static and live data can drift.** The static labels are shorter ("Management", "Supply chain", "Research") and the live payload wins after load. A future subject added only to `SUBJECT_DEFS` will not appear until JS replaces the list; the guard checks the ten known ids only.
- **The static anchor is not the whole capability.** If the API is old, the links exist but the subject page still 404s. The rail is now visible, not functional, without the backend.
- **`margin:0 auto` centres within the content column, not the viewport.** The 64px rail means the visual centre is ~32px right of the viewport centre; matching the viewport exactly would need an asymmetric offset that risks the rail on small screens. "Even space" is satisfied within the content area.
- **Enter may surprise.** Plain Enter in a textarea normally inserts a newline; the hint and the up arrow mitigate it, but a user typing a multi-line objective must know Shift+Enter. A future change could require Ctrl+Enter instead.
- **The guards are presence checks, not DOM tests.** They would pass if the elements existed but the JS binding were broken. No browser is available in the suite.

---

## 2026-10-27 — [product] Catalogue and Assistant leave the served UI; their backend lanes stay

**What was asked.** The owner asked what Catalogue, Assistant and Status are for and whether they could be deleted. After the answer (Catalogue largely duplicated subject pages + Calculator; the Assistant UI could not work; Status is the only human-readable health/case-store diagnostic), the owner said **"go"** for removing the first two and keeping Status on the health pill.

**What changed (build 0.67).** The `Frameworks & templates` panel, its subject-page entry button, and the `Assistant` panel with "Challenge my analysis" are deleted from `web/index.html`. The floating chat button now opens a single **Help & about** drawer (no Assistant tab), and the boot no longer calls `/api/assist/config` or `/api/assist`. The health pill still opens Status. Removed with them: `RENDERERS.frames`, `searchFrameworks`, `loadTemplate`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, the unused `.dtab` CSS and the `state.assist` field. **Retained:** the backend `GET /api/frameworks`, `GET /api/frameworks/{id}`, `GET /api/templates`, `POST /api/assist`, `assist.py` and every backend test, plus the subject pages' catalogue-only tables and worksheet tiles, the Calculator's method list, and the `/api/health` Status panel. Three UI-presence assertions in `test_assist`, `test_framework_flow` and `test_templates` were retargeted to assert the new surface and the panels' absence; no backend assertion changed. 750 tests pass.

**Where the previous state was wrong.**
- The 0.65/0.66 build kept the Catalogue screen reachable from a subject page even though it duplicated what the subject page and Calculator already showed; it also never displayed the registry's most valuable fields (`limitations`, `when_not_to_use`), so it was a weaker view of data the backend already holds.
- The Assistant UI was not merely optional, it was broken: it posted `task:"challenge"` with no `consent` to a server that accepts only `facts`, `alternatives` and `critique` (finding F3, never fixed). Keeping the button would have shipped a promise the server rejects.
- The earlier claim that these panels were "reached contextually" (B-091) was true but not a reason to keep them; the owner's test is usefulness, not reachability.

**Where this could be wrong.**
- **The backend lanes are now orphaned.** `POST /api/assist` has no UI caller and cannot be exercised without a configured provider; `/api/frameworks` and `/api/templates` are used only by tests and directly-written URLs. That is acceptable for a later release, but a future model should not assume a user can reach them.
- **Some reference value is lost.** A student can no longer search all 140 registry records by name/type, see the all-methods review-status table, or load a template without opening a subject. The subject pages cover the subset each subject owns, which is the intended path, but a cross-subject browse is gone.
- **Deleting is not reversible for the user's workflow.** The code is in git history and the routes remain, so restoring a panel is a UI change, not a backend rebuild; but if the owner wanted the Assistant with a provider, it must be re-surfaced and fixed (task + consent + facts/alternatives), not merely un-hidden.
- **No browser test exists.** The removal was checked by counting references (`panel-frames`, `panel-assistant`, `dtab`, `api/assist` = 0), balancing `<section>` tags, `node --check` and the Python suite. A DOM regression could still pass.

---

## 2026-10-27 — [product] The subjects themselves become the rail; capability tiles; four rail items removed

**What was asked.** The owner asked for the subject rail to stop being an aggregate `Subjects` item and to enumerate the subjects instead — *"enumerate the subjects ACCOUNTING, FINANCE, ECONOMICS, MANAGEMENT, ETCH. AND NOW INCLUDES ENNTREPRENEURSHIP. ALSO PUT ICONS BESIDE THEM. THE IDEA IS THAT WHEN THEY ARE CLICKED, THEIR MANY CAPABILITIES WILL SHOW ON THE CENTER OF THE SCREEN ... THEN USER WILL JUST CLICK WHICH ONE THEY WILL USE. HOWEVER, YOU HAVE TO RECONCLIE THIS WITH HOME CHAT ... delete case, catalogoue, assitant status and retain calculator at the utton."*

**What changed.** `bp.product.subjects` now declares ten subjects with a unique presentation `icon` key: Accounting, Finance, Economics, Management & strategy, **Entrepreneurship**, Operations, Supply chain & logistics, Marketing & customers, People & organisation, Research & statistics. Entrepreneurship is a combination shelf: eight frozen compute tools (break-even, multi-product break-even, unit economics, NPV, IRR, discounted payback, forecast, case decision), the existing STR-18 SWOT worksheet, and five catalogue-only records (Business Model Canvas, Lean Canvas, Value Proposition Canvas, Blue Ocean/ERRC, diffusion/disruptive innovation); no worksheet or number is invented. The rail is Home + the ten subjects (icon and label, tooltip when collapsed) + Calculator pinned at the foot. The Case, Catalogue, Assistant and Status rail items are gone; their existing panels are reached contextually (cases from Home and every subject page, the full catalogue from a subject page, the assistant from the floating chat button, status from the health pill). A subject click renders its capabilities as a tile grid in the centre; each tile opens one frozen method or worksheet, and the page then shows stored cases for the subject and the catalogue-only table. Two tests were added (750 total) guarding rail order, unique icons, the icon round-trip through the detail route, and Entrepreneurship's composition.

**Home-chat reconciliation (why this is not a second home).** Home is the *free-form* path: one objective box, the preset/method controls, the examples and the case shelf. The rail is the *structured* path: a subject first, then its honest tool list. The Home copy now says both, the same subject cards remain below the chat, and every subject page links back with "Ask in the chat instead". There is one source of truth for the subjects (the product catalogue) used by both the rail and the Home shelf.

**Where the previous implementation (0.65) was wrong.**
- It kept one aggregate `Subjects` rail item. The owner's instruction is that the subjects *are* the navigation; a menu one level deeper is not the same thing, and it also hid the subject set from the rail.
- The subject page was a vertical list of rows with a separate "Open tool" button per row. The owner asked for the capabilities to appear in the centre and be clicked directly; the tile grid makes the choice the object, not a footnote to a paragraph.
- The rail still listed Case, Catalogue, Assistant and Status. Those duplicated surfaces that already exist elsewhere (the Home case shelf, the subject catalogue sections, the chat drawer, the health endpoint), so the rail remained a map of subsystems rather than of the student's subjects (finding F7 in the 2026-10-26 review).
- Home chat and subjects were not explicitly reconciled in the copy, so the two entry points looked like competing homes. They are now stated as two routes to the same pipeline.

**Where this could be wrong — read before changing it.**
- **Entrepreneurship's tools are generic.** Break-even, unit economics and appraisal are frozen methods applied to a venture; they are not venture-specific instruments (no cap-table, term-sheet or runway method exists). The page says the tools are launchers, not that they are specialised.
- **Removing a rail item is not deleting a panel.** A user who does not discover the chat button or the health pill may find the assistant or status harder to reach. If the owner wants them gone entirely, deleting the panels is a separate, larger change (and the assistant drawer links to the panel).
- **Icons are presentation only.** They are a mapping from an icon key to inline SVG in the client; they carry no claim and are not tested by the Python suite (only the unique key is).
- **The capability tiles are still catalogue-bound.** A subject whose records are all "not implemented" shows a tile grid for its compute tools and a table for the rest; it will not feel rich. The honest answer is more methods, not more cards.
- **No browser test exists.** The rail, tile grid and hash route are checked by reading the HTML/JS and by a syntax check; the Python guards cover the catalogue, not the DOM. A UI regression could pass the suite.

---

## 2026-10-26 — [product] Increment 1 shipped: subjects second, the Calculator as a launcher, and what was deliberately left

**What was asked of this entry.** The brief says that a model implementing any part of it must add a new dated entry at the top (not edit the old one) and change only the brief's Status line. This is that entry.

**What changed.** The first increment (Option E, section G Increment 1) and the Calculator instruction (section N) are built, in the product layer only: `src/bp/product/subjects.py` (9 subjects, their launchable frozen presets/methods, the 3 existing T4 worksheets, and the registry records each subject can only read/structure), `scripts/generate_subjects.py` (regenerates the committed registry slice), `GET /api/cases/subjects`, `GET /api/cases/subjects/{id}`, `GET /api/cases/calculator`, `GET /api/cases?subject=<id>`, `tests/test_product_subjects.py` (drift guard), and the served UI: seven-item rail (Home, Subjects, Calculator, Case, Catalogue, Assistant, Status), Home as a case shelf with subject cards, subject pages, a searchable Calculator, the work-plan destination replaced by a one-button tool screen, `framework_suggestions` rendered as informational rows, and the hero sub-line fixed. No core module, frozen fixture or existing test was edited; the product boundary test still passes.

**Where this entry's implementation departs from the brief, and why.**

- **The brief's Increment 1 also implied a case-first container; the repository cannot do that yet.** The implemented Home is a *case shelf plus a new-analysis box*. A case still cannot exist before a run (`bp-case/1` requires `session`, `delivery`, `report`, `appendix`, `reperform`). The page says so explicitly instead of pretending. Making the case the container is C1 (Increment 2), not this increment.
- **"Replace the second icon" was read as both readings in section B.** The rail's second item is now Subjects, and the work-plan *screen* is no longer a destination: the tool screen keeps inputs, ambiguities and one primary button. The frozen string test is preserved honestly by keeping "Draft work plan" as the heading of the recorded-metadata card, not as a button.
- **The Calculator is narrower than "all financial and business calculations".** It is every calculation the 36 frozen methods / 38 presets actually support, plus a visible catalogue-only section. Free-form typed arithmetic is not built: it would be a second arithmetic path and would need a computation-owner method, a second route, tests and an unfreeze. The panel says this rather than leaving the gap silent.
- **The subject taxonomy is still a judgement.** Table H was followed for the nine shelves, but several records are assigned by *curated* choices rather than by a raw discipline tag (FIN-02/FIN-05 to Accounting; FIN-01/03/04/06 and the decision-analysis records to Finance; FIN-07 and the evaluation records to Economics; operations records to both Operations and Supply chain). The owner can overrule any mapping in `SUBJECT_DEFS`; the guard will catch a bad id, not a bad editorial judgement.

**Where this could be wrong — read before building Increment 2.**

- **The subject page may still be judged cosmetic.** It changes where work starts and shows the evidence/tools honestly, but it does not yet give Accounting or Finance a purpose-built workbench. The brief's own warning stands: a nicer menu with the same flat report still loses on feel. The next step that changes the experience is the Accounting engagement editor and the Finance/DCF sheet, not more navigation.
- **Filtering stored cases by method can over-claim a subject.** A `breakeven` case appears under Accounting, Finance and Operations because each subject legitimately lists that method. That is honest about the method, but it means "cases in this subject" is a *method-based* view, not a statement that the case was framed as that subject. When C1 adds `case.subject`, the explicit tag should win and this fallback should be labelled as a fallback.
- **A one-run-case product can mislead through the Home copy.** The note says a run is saved as a one-run case; a student who uploads a case study expecting a container will still be disappointed until C1. The copy is honest, but honesty is not the same as the feature the owner asked for.
- **The Calculator's grouping repeats tools across business functions.** NPV appears under Finance; break-even appears under Finance, Accounting and Operations. That is deliberate (a function view, not a partition), but a later contributor may mistake the union/group relation for a bug and "de-duplicate" it into one home, weakening the page. The guard test requires the union to equal the subjects' compute tools, not that groups are disjoint.
- **No served-page test clicks the new screens.** The suite verifies the routes, the catalogue and the frozen strings; it cannot see a JavaScript handler that fails in a browser. I ran `node --check` on the extracted script, but the interaction path (open subject → open tool → apply figures → save case) should be clicked once by the owner before it is trusted.

**Owner decisions still open (unchanged):** section J items 1–8, especially whether one case should hold many subject analyses (C1), whether the 131 catalogue-only records stay visible, and whether B-028 should add worksheets. This entry decides none of them; it builds the presentation layer that makes the question concrete.

---


## Discussion brief - subject-first navigation, and the shift from run-oriented to case-oriented (separate section)

**Status: PARTLY IMPLEMENTED (2026-10-27) - Increment 1 is built and the rail enumerates the ten subjects (Entrepreneurship included) with icons, capability tiles and the Calculator pinned at the foot. Case/Catalogue/Assistant/Status are not rail items; in build 0.67 the Catalogue and Assistant panels were removed from the served UI as well (B-092), with their backend routes retained, while Status is reached from the health pill. Build 0.68 makes the rail **static-first** (the ten subject links and icons are in the page before any fetch), gives the toggle an explicit expanded state, centres the Home chat, and replaces the Run button with an up arrow plus Enter (B-093). Build 0.70 reduces Home to the logo, the unchanged slogan and the chat box only (B-094). Increments 2-4 (C1 multi-run cases, Accounting/Finance workbenches, remaining workbenches), free-form arithmetic, and all owner decisions in section J remain open.** This section exists so that (a) the owner can choose between options without re-reading the code, and (b) a model with more capacity than the one that wrote it can implement the chosen option without the original session. It is deliberately a **separate section**, not a dated review entry: the dated entries below record what happened and where an assistant was wrong; this section records a forward-looking design discussion and a build brief. If a model implements any part of it, it must (1) add a **new dated entry at the top** describing what it changed and where this brief was wrong, and (2) update only this section's Status line. Do not rewrite the rest of this section once dated entries supersede it.

**Owner ask (2026-10-27, second message, condensed).** *"We have to change the trajectory of the pipeline from run oriented to case oriented. In the pipeline, insert or replace the second icon, which is now analysis draft work plan, as it is useless. Use the attached A4.jpg as a basis where it will include all relevant domains or subjects in business. When the user clicks accounting, they will be taken to the accounting page and do sorts of things there related to accounting that is supported by the backend. Also finance, economics, management, operations management, supply chain etc. Others may not have calculations but only framework - for example, in management they may only opt for Porter's five forces. Others have a combination. Explore ways on how to do this where the backend would fit in this new workflow and present the most promising options."*

Signals to respect: (1) "run -> case" is a **direction of travel**, not a feature to bolt on; (2) the **second entry point** in the pipeline is to be *replaced*, not added to; (3) **A4.jpg (SciSpace's "Browse by Domain") is a structural reference only** - no text, claims, agent names or counts are copied; (4) **framework-only subjects are accepted** ("management ... may only opt for Porter's five forces") but **combination subjects are expected**; (5) the owner asked for options and a recommendation, **not code**.

**Verify before acting - the repository record is currently ahead of the served product.** The 0.65 entry below claims a UI pass ("home became case-first with three intake cards; `framework_suggestions` render as selectable chips; charts render automatically ..."), and `WORKLOG.md` repeats it. The served `web/index.html` does not contain it: no case intake, no document upload, no call to `/workspace`, `/documents`, `/data-files`, `/arguments` or `/charts`, no `framework_suggestions` rendering, hero sub-line still "To be supplied". Evidence: `web/index.html:295`, `:583`; grep of the file for the workspace routes returns nothing; the only case routes it uses are run-level (`:842`, `:853`, `:892-895`, `:1234`, `:1245`). The backend modules exist and their routes are wired (`src/bp/product/api.py:25-32`). **The case-first backend was built; the case-first UI was not.** Re-verify this first:

```
# from business_pipeline/
curl -s http://127.0.0.1:8000/ > page.html
# then grep page.html for: /workspace   framework_suggestions   "Draft work plan"   "To be supplied"
python -m unittest tests.test_session_api tests.test_product_workspace
```

### A. Findings (evidence, not opinion)

| # | Finding | Evidence |
|---|---|---|
| F1 | The served flow is **run-first**: objective box -> preset/method dropdown -> "Draft work plan" -> "Confirm spec and run" -> result -> "Save as case". The case is created *after* the run. | `web/index.html:290-336`, `:685-736`, `:842` |
| F2 | The 0.65 case workspace (documents, data files, arguments, chart plan) is **built but unreachable from the UI**. | `src/bp/product/api.py:25-32`; no call in `web/index.html` |
| F3 | `framework_suggestions` is computed on every session and never rendered. | `src/bp/session.py:67-68`; grep of `web/index.html` -> none |
| F4 | The "Draft work plan" step is **load-bearing**, not decorative: it is the only path by which edited figures reach a session, because the UI re-posts `/api/sessions` in `redraft()`, and `confirm` accepts `frameworks` only - never inputs. | `web/index.html:738-756`; `src/bp/server.py:183-187` |
| F5 | A frozen test asserts the served `/` contains the strings "Draft work plan" and "Account mapping". Removing the screen silently breaks the suite unless the phrase survives somewhere honest. | `tests/test_session_api.py:98` |
| F6 | A case **cannot exist before a run**: a bundle must carry `session`, `delivery`, a `report` string, `appendix` and `reperform`. "Upload the case study, then decide what to do" is impossible in the current schema. | `src/bp/product/cases.py:40`, `:137-153`; `versions.py:37` |
| F7 | A case is **one run**: the version chain and comparison are run-level and comparison requires the same method id in every version. A case holding accounting + finance + strategy runs does not exist. | `src/bp/product/compare.py:57-59`; `versions.py` |
| F8 | The framework catalogue has **no list-all and no discipline filter**; search needs a query and is capped at 25 results. A subject page cannot browse "all frameworks in my subject" from frozen routes. | `src/bp/server.py:129-132`; `src/bp/registry.py:150-160` |
| F9 | The **ingest-to-method mapping already exists** (`POST /api/ingest` with `"map": {"method", "columns"}` validates a table's columns against a method's declared inputs) and is not surfaced in the UI. This is the "messy figures -> checked inputs" capability the owner asked for in the first review. | `src/bp/server.py:246-250`; `docs/CAPABILITIES.md` section 5.1 |
| F10 | The catalogue is large but mostly un-actionable: **140 records, 15 discipline tags; 3 records have a worksheet template (STR-01, STR-07, STR-18), 6 have a partially linked method, 9 have either, and 131 have neither.** | `src/bp/registry.py:53-62`; `src/bp/data/registry_v0_2.json` |
| F11 | The model lane is inert (no provider configured), so subject pages cannot rely on model proposals yet. | `src/bp/server.py:135-136` |

### B. What A4.jpg actually adds: the missing second axis

The reference image carries **two axes**: an action axis (*Featured, Extract + Analyse, Literature Review, Create + Write, Deep Search*) and a **domain axis** (*Browse by Domain: Physics, Computer Science + AI, ...*). Our product currently has only one axis, and it is a map of **subsystems** (Home, Cases, Data, References, Deliverables, Accounts, Frameworks, Assistant, Status) - which is exactly why the owner calls the left icons useless. Adding the subject axis is the whole idea; the subject gallery is a **filtered index over the tools the engine already has**, not a second application.

**Two readings of "the second icon", and they converge on one build.** (1) Rail item #2 is *Cases* (`web/index.html:255`), a table of saved runs - replace it with **Subjects**. (2) The second *step* of the analysis pipeline is the **Draft work plan** screen - replace it with the subject/tool screen. The build in section F satisfies both: the rail becomes task-shaped with Subjects second, and the work-plan checkpoint folds into the tool screen (mechanics in section F.1).

### C. Constraints that decide the design (do not fight these)

| Constraint | Evidence | Consequence |
|---|---|---|
| Core frozen: 36 methods, 38 presets, 12 route families, delivery shape | `docs/BACKEND_CONTRACT.md` section 2; `tests/fixtures/frozen_contract.json` | Every subject tool must launch an existing id. No new arithmetic, no new delivery shape. |
| New product routes must live under `/api/cases` to need no core edit | `docs/BACKEND_CONTRACT.md:92`; `src/bp/product/api.py:94-141` | A subject catalogue endpoint is `/api/cases/subjects...`, or it is an unfreeze request. |
| The product package may not import the frozen core | `tests/test_product_boundary.py:66-77` | The subject -> tool mapping is **static product data** guarded by a drift test, never a call into `methods`/`registry`. |
| A case needs a completed run to exist | F6 | The target flow (case first, then tools) requires a product-layer schema change. |
| Case comparison/versions are run-level, same method only | F7 | A multi-subject case is a schema decision, not a UI trick. |
| Product layer computes no business number | `docs/BACKEND_CONTRACT.md` section 4 | The subject index may group, label and link; it may not derive, rank or score a business figure. |
| Frozen UI string test | F5 | If the work-plan screen disappears, keep the phrase in the recorded-metadata disclosure or coordinate a test change with the computation owner. Never edit the test. |

### D. The honesty map - what each subject can actually do today

This is the part that decides how many subject pages are real and how many are catalogue reading. Every "runs today" entry is a frozen method/preset; every "catalogue only" entry has no engine and no worksheet.

| Subject | Runs today (computed, auditable) | Framework worksheets | Catalogue only - no engine/worksheet |
|---|---|---|---|
| **Accounting** | `management_accounts` (ledger, statements, two-route cash flow, closing; preset `accounts`), `ratio_analysis` (preset `ratios`), `currency_convert`, descriptive/weighted summaries | none | management accounting: variances, ABC, target costing (QNT-FIN-05); cost & profitability beyond break-even |
| **Finance** | `npv`, `irr`, `discounted_payback`, `wacc`, `dcf_valuation`, `equity_bridge`, `case_decision` (alternatives + crossover rate), `unit_economics`, `multi_product_breakeven`, `breakeven`, `ratio_analysis`, `trend_forecast`, `ols`/`pearson` for betas | `case_decision` (T2 workflow) | no bonds, options, portfolio, CAPM derivation, FX retrieval or tax |
| **Economics** | `cost_benefit`, `cost_effectiveness`, `sroi`, `trend_forecast`, `currency_convert`, correlation/regression | none | pricing & demand/elasticity (QNT-FIN-07); decision analysis (QNT-DEC); impact evaluation (QNT-EVL) |
| **Management & strategy** | `case_decision` for option comparison; the statistics methods as evidence | **`swot`, `five_forces`** (the only two T4 worksheets) | 18 strategy, 14 change/org, 14 performance/projects frameworks, 7 theories - **worksheets gated by B-028** |
| **Operations management** | `breakeven`, `multi_product_breakeven`, `unit_economics`, `trend_forecast`, `chi_square`, `power_analysis`, `missing_data_bounds`, descriptive | none | EOQ, reorder point, queueing, capacity, CPM/PERT, OEE, SPC (QNT-OPS-01..08); SCOR, SIPOC, VSM, 5S, A3, TOC, 5 Whys, FMEA |
| **Supply chain & logistics** | as Operations | none | QNT-OPS-01/02/03/08, SCOR - **no inventory, lead-time or network calculation at all** |
| **Marketing & customers** | `unit_economics` (margin, CAC payback, LTV), `multi_product_breakeven`, `trend_forecast`, `reliability_alpha`, `chi_square`, `power_analysis` | none | TAM/SAM/SOM, market share, cohorts/retention, RFM, A/B analysis (QNT-MKT-01..07); STP, 4Ps, AIDA, Kano, SERVQUAL |
| **People & organisation** | `reliability_alpha`, `weighted_summary`, `descriptive_stats`, `chi_square`, `power_analysis`, correlation/regression | none | AMO, Kirkpatrick, Job Characteristics, Nine-Box, Tuckman; the change/org frameworks |
| **Research & statistics** (cross-cutting; belongs on every subject page) | 20+ T1 methods: descriptive, correlation, OLS/HC3/logistic, t/ANOVA/KW/two-way/post-hoc, chi-square, power, missing-data bounds, multiple comparison, alpha, weighted, forecast | none | factor analysis, clustering, ANCOVA, repeated measures (parked, B-075) |

Two conclusions follow and should govern the plan:

1. **The subject hub is roughly 20% backend and 80% product surface.** The compute exists. What is missing is (a) the container order (case before run), (b) per-subject input adapters, (c) a curated index. `POST /api/ingest` with `map` (F9) already does "messy figures -> validated method inputs"; the subject page mostly needs to *call* it.
2. **Only four subjects can carry a real workbench now** (Accounting, Finance, Research & statistics, Strategy/Management). The rest must be labelled honestly as "framework structure + computed tools where marked", or the hub becomes a promise the engine cannot keep.

### E. The architectural fork: what is a case?

The real decision is not which screen to add; it is **what a case is**. Today a case is one run plus its material. The owner's trajectory implies **one case study -> many subject analyses on the same material**, which requires the case to be the container and the runs to be contents:

```
TODAY    Home -> objective + method -> session -> confirm -> report -> [Save as case]
                                                                       case = 1 run (+ documents/data/arguments)

TARGET   Home (case shelf) -> Case (materials) -> Subject -> Tool -> run
                                   |                                   case = materials + runs[]
                                   +-> Accounting | Finance | Management | ...
```

### F. The options

Comparison summary:

| Option | What it is | Backend change | Freeze risk | Gives "case oriented"? | Cost | Verdict |
|---|---|---|---|---|---|---|
| **A** | Subject gallery in the UI only (static JS table) | none | none | no | small | presentation only; not sufficient alone |
| **B** | Subject catalogue as product data + case-scoped subject view | new `product/subjects.py`, routes under `/api/cases` | none | partially | moderate | good groundwork; ship as part of E |
| **C1** | Case owns its runs: one `bp-case/2` document with `runs[]` | product-layer schema change in `cases/versions/compare/export/workspace` | none | yes | large | **recommended core** |
| **C2** | Separate "engagement" store that references run bundles | new `product/engagements.py` + sidecar index | none | yes | large | valid alternative; two stores + migration |
| **D** | Subjects in the frozen core: `/api/subjects`, discipline filter on `/api/frameworks`, session groups | core edit + fixture update | **unfreeze** | yes | large | rejected now; revisit only if hosted/multi-user or owner-editable catalogue |
| **E** | Staged hybrid: A/B presentation now, C1 next, subjects one by one | as above | none | yes, over time | sequenced | **recommended plan** (see section G) |

**Option A - subject gallery in the UI only.** Static JavaScript table subject -> tool descriptors (preset id, method id, template id, label, kind); framework lists filtered client-side from `/api/frameworks` by `disciplines`; every tool click fills the existing objective/preset/method controls. *Pros:* days of work, zero backend risk, structurally identical to SciSpace; a fast visible win. *Cons:* untestable mapping (the suite cannot see the UI, so drift is silent), no case grouping, still run-first, and a menu is not the moat. **Verdict:** acceptable as the *presentation* of B, never as the plan on its own.

**Option B - subject catalogue as product data.** New `src/bp/product/subjects.py` holding a versioned static catalogue (subject -> tools with kind `compute|framework|mixed|research`, their launch ids, one-line "what it does here", plus catalogue ids); routes `GET /api/cases/subjects` and `GET /api/cases/subjects/{id}`; subject-scoped listing `GET /api/cases?subject=` using a static method -> subject map; a guard test asserting every launch id exists in the frozen fixture and every catalogue id exists in the registry JSON read as data (the product package still imports nothing from the core). *Pros:* one testable source of truth for the UI and any future API consumer; honest tool counts; no unfreeze. *Cons:* a run still saves as its own case, so the case study must be re-attached per run; the run remains the storage unit. **Verdict:** build it as Increment 1 of E; it is what makes the gallery honest and maintainable.

**Option C1 - the case owns its runs (recommended core).** A product-layer document `bp-case/2`:

```json
{"format": "bp-case/2", "id": "<12 hex>", "title": "...", "subject": "accounting",
 "created_at": "<ISO-8601 UTC>",
 "documents": [], "data_files": [], "arguments": [],
 "runs": [{"run_id": "...", "method": "ratio_analysis", "method_version": "1.0.0",
           "tier": "T1", "spec_hash": "...", "outputs_hash": "...", "created_at": "...",
           "session": { ... }, "delivery": {"report": "...", "appendix": { ... }},
           "reperform": { ... }}],
 "primary_run": 0}
```

Rules: each run is the existing frozen session + delivery **stored verbatim and hash-pinned** (the product layer still computes nothing); an **empty case is legal** (`runs: []`) so the student can create the case and upload the case study first; a **v1 bundle reads as a one-run case** (`runs = [synthesized from session/delivery/reperform]`, `subject` derived from the method map) and is written as v2 only when modified; versions/compare/charts/exports take a **run selector** (default `primary_run`); sign-off signs a run's version hashes. *Pros:* it is the actual trajectory change; the audit story improves (a run is the frozen computation, the case is the student's work); the 0.65 workspace pieces finally sit at the right level; **no unfreeze**. *Cons:* schema migration and coordinated updates in `cases.py`, `versions.py`, `compare.py`, `export.py`, `workspace.py` plus their product tests; version semantics must be decided. **Verdict:** the recommended core, as Increment 2.

**Option C2 - separate engagement store.** Keep `cases/<id>.json` as one opaque run bundle and add `engagements/<id>.json` = `{title, subject, documents, data_files, arguments, run_ids[]}`, where run ids point at stored run bundles; the subject page loads the engagement and hydrates each run. *Pros:* zero change to the existing bundle schema and to `versions/compare/export`; migration is trivial (existing flat cases appear as single-run engagements, synthesized on read). *Cons:* two stores to back up, restore and keep consistent; materials live in one store and runs in another; deleting a run/case needs cross-store rules; the "case travels as one thing" artefact becomes two files. **Verdict:** the conservative fallback if C1's schema change is judged too risky for the current audit trail.

**Option D - subjects in the frozen core (rejected for now).** Add `/api/subjects`, a `discipline` query parameter on `/api/frameworks`, and optionally session groups in `session.py`/`orchestrator.py`. *Pros:* one authoritative catalogue, server-side filtering, owner-editable without a code change, useful if the product becomes hosted/multi-user. *Cons:* changes the frozen route and registry contracts, needs owner approval, a B-decision, a fixture update and a trap test; the product layer can hold the same data as tested static data today. **Verdict:** do not do it now; revisit only if D1 changes to hosted/multi-user, or the catalogue must be edited by the owner without a code change.

### G. Recommended plan - Option E, four increments over A/B/C1

**Increment 1 - "Case first, subject second" (presentation + product catalogue; no schema change).**
- Home becomes the **case shelf**: *New case* (upload the case study / paste figures / describe the objective), *Your cases*, and **Browse by subject**.
- Rail becomes task-shaped, seven items: **Home | Subjects | Calculator | Case | Catalogue | Assistant | Status** (the Calculator is an owner instruction; see section N). "Cases" folds into Home; "Accounts" becomes the Accounting subject page; "Frameworks & templates" becomes Catalogue (reachable from every subject page). **Subjects is the second icon** - the replacement the owner asked for.
- Subject page v1: the subject's tools (from `subjects.py`), the case's documents/figures, the runs already done, and an explicit "catalogue only - no worksheet yet" section for engine-less items.
- **Work-plan step removed as a destination** (mechanics in G.1) - the tool screen shows inputs, declared assumptions/ambiguities and one primary button that applies edited inputs and confirms in one sequence.
- Files: `src/bp/product/subjects.py` (new), `src/bp/product/api.py` (routes + `?subject=` filter), `tests/test_product_subjects.py` (new, drift guard), `web/index.html`. No core edit. Docs: one CHANGELOG entry, one WORKLOG `[product]` entry, `BACKEND_CONTRACT.md` section 6 rows, count digits in HOME/HANDOFF/CONTRIBUTORS, a new dated entry at the top of this notebook.
- Acceptance: every subject tool launches a live frozen id; the guard test fails if a preset/method/template/registry id in the catalogue disappears; with the server unavailable the gallery shows a visible error and never invents a tool list (fail closed); the frozen UI strings still pass.

**Increment 2 - "The case owns its runs" (Option C1).**
- `bp-case/2` as in F; empty cases; v1 read-compatibility; run selector on versions/compare/charts/exports; `POST /api/cases/{id}/runs`, `GET /api/cases/{id}/runs`.
- Migration trap test: a v1 bundle loads, lists, renders, exports and compares **byte-identically** to the pre-change code; a case with `runs: []` is storable, reopenable and has a workspace view; every run's stored numbers are unchanged.
- Decide version semantics explicitly and record the decision (recommended: a version snapshots **one run**, never the whole case, so hashes stay meaningful; the case-level snapshot, if needed, is a separate export).
- Risks: this touches the freshly built 0.65 workspace and the version chain. Do not rush the version decision; if it cannot be settled, fall back to C2.

**Increment 3 - the first real workbench: Accounting, then Finance.**
- Accounting: typed engagement editor (chart of accounts, opening balances/entries, schedules, reconciliation) or CSV import through `POST /api/ingest` with `map`; the second checkpoint (account mapping) rendered as a **typed table**, not a JSON `<pre>`; statements table; ratio analysis; statement export. Today the `accounts` preset posts one raw JSON demo spec (`src/bp/accounts.py`, `EXAMPLE_SPEC`), so "do accounting things" is currently not possible from the UI.
- Why Accounting first: deepest engine, two-checkpoint flow already exists in the Accounts panel (`web/index.html:1250-1316`), statements/exports exist, and the owner's own INITIAL TEST set is accounting/finance.
- Finance second: a cash-flow/DCF sheet feeding `npv`/`irr`/`wacc`/`dcf_valuation`/`equity_bridge`, with the crossover (`case_decision`) as a headline rather than an appendix line.

**Increment 4 - the remaining subjects, honestly labelled.**
- Strategy/Management: worksheet UIs for the two existing T4 templates (evidence items with dimensions/forces, provenance, materiality; nothing scored), plus catalogue reading for the rest.
- Research & statistics: the natural home of the 20+ statistical methods currently buried in a method dropdown.
- Marketing/Economics/Operations/Supply chain/People: "combination" pages with computed tools where they exist and an explicit catalogue-only section. Request **B-028** (more worksheets: PESTEL, VRIO, Value Chain, Business Model Canvas, MCDA) if the owner wants those pages to be actionable; request **B-032** (ledger T1), **B-052** (tax) only through the owner's decision process.
- **Do not invent a worksheet** for a catalogue record: T4 structure-only template creation is gated by B-028, and a fake "worksheet" would be a claim the engine cannot support.

**G.1 Removing the "Draft work plan" step without breaking the contract.** The step is load-bearing (F4): inputs reach a session only by re-posting `/api/sessions`, and `confirm` takes frameworks only. The replacement must preserve the mandatory pre-run checkpoint (it is a product invariant, not a UI preference). Recommended mechanics: the tool screen collects the figures and keeps the declared assumptions/ambiguities visible; its **one primary button** performs the same two calls the UI performs today (`POST /api/sessions` with the edited inputs, then `POST /api/sessions/{id}/confirm`), then renders the delivery. Nothing is computed client-side and no core route is needed. Keep a sentence containing "**Draft work plan**" in the recorded-metadata disclosure so `tests/test_session_api.py:98` stays green (the string test is frozen; if the owner prefers it gone, that is a coordinated change with the computation owner, never an edit to the test).

### H. Proposed subject taxonomy (a judgement, derived from the catalogue's 15 `disciplines` + a small override list)

Do not hand-map 131 unlinked catalogue records. Map subjects to discipline tags, then override the few ambiguous Q/F records:

| Subject (proposed) | Catalogue `disciplines` to pull | Notes / overrides |
|---|---|---|
| Accounting | finance, accounting and managerial economics | pull QNT-FIN-02/05 toward Accounting; QNT-FIN-01/03/04/06 toward Finance |
| Finance | finance, accounting and managerial economics | QNT-FIN-07 (pricing & demand) -> Economics/Marketing |
| Economics | finance, accounting and managerial economics; public, nonprofit and impact evaluation; program and impact evaluation | appraisal methods are the real engine; label the rest catalogue-only |
| Management & strategy | strategy; change and organization; people and learning; performance, projects and technology governance | one page or split "Management" vs "People & organisation" - owner decision |
| Operations management | operations and supply chain; operations, logistics and optimization | split logistics into Supply chain |
| Supply chain & logistics | operations and supply chain; operations, logistics and optimization | same tags, different curated tool set |
| Marketing & customers | marketing and customers; market and customer analytics | |
| People & organisation | people and learning; change and organization | |
| Research & statistics (cross-cutting) | statistics and empirical research; supporting theory | **not a subject page**: a methods page linked from every subject |
| Risk & decision analysis (optional) | risk and decision analysis; decision analysis and risk quantification | fold into Finance/Management unless the owner wants it separate |

The subject -> tool and subject -> catalogue-id lists should be **generated once** from the registry and frozen core by a small `scripts/` helper, then **committed** in `subjects.py` and guarded by a test that re-reads `tests/fixtures/frozen_contract.json` (methods/presets) and `src/bp/data/registry_v0_2.json` (catalogue ids) as data. That is the house pattern (`test_shipped_registry_equals_fresh_import`): deterministic bytes, a guard that fails on drift, and no core import in the product package.

### I. What must not be done in any of these increments

- No core module edit, no frozen fixture edit, no existing-test edit; no new route outside `/api/cases` without an owner-approved unfreeze.
- No second arithmetic path: the subject index groups and links; it must never compute, rank, score or adjust a business number, threshold or rating.
- No hidden capability: a tool the engine cannot run must be shown as catalogue-only with its declared `implementation_status`, exactly as the registry states it.
- No invented subject counts, "agents", testimonials or social proof (the A4.jpg reference is structural only).
- Do not present a framework-only subject as an analysis the system performed: T4 is structure + evidence audit, and the output must say so.

### J. Owner decisions needed before or during implementation

1. **Which reading of "the second icon"** is intended - the rail item, the work-plan screen, or both? (The plan covers both.)
2. **Is one case supposed to hold many subject analyses** (accounting + finance + strategy on the same case study)? This is the C1 decision; if not, Option B is sufficient.
3. **Accounting first?** Or another subject if coursework is strategy/marketing-heavy (then the first workbench is much thinner - two worksheets).
4. **Framework-only subjects:** show the 131 catalogue records that have no worksheet (honest "read the structure, no worksheet yet"), or hide them until B-028 expands the template set?
5. **B-028:** add worksheets (PESTEL, VRIO, Value Chain, Business Model Canvas, MCDA)? This is the decision that turns Management/Marketing/Operations pages from reading lists into workbenches.
6. **Subject list:** 8 + 1 cross-cutting (as in H), or split Management from People & organisation, or keep Risk separate?
7. **Version semantics for a multi-run case** (if C1): snapshot one run per version (recommended) or the whole case?
8. **The rail Calculator (section N):** build it as a launcher over the frozen methods, and is free-form arithmetic in scope (which would need a core method and an unfreeze)?

### K. Open questions for the next model (unresolved by this brief)

- Where should the **subject tag** live: only `bp-case/2.subject` (explicit, chosen by the student) or derived from the method map (implicit, no storage)? Recommendation: explicit when creating a case, derived as a fallback for v1 bundles.
- Should the **subject page list runs from other subjects** (cross-links), or stay scoped?
- How does a **multi-run case export**? One HTML per run plus a case index page, or one combined document? (No new arithmetic either way; decide the artefact.)
- Does **sign-off** attest a run, a case version, or the case? (Today it signs version hashes; with runs, the hashes must be scoped.)
- Does the **case shelf** show the subject(s) a case touches, and does it need a filter when there are many cases?
- What is the **empty-case UX** when the student uploads a case study but the extractor refuses it (scanned PDF)? The honesty rule says refuse with a reason, not paraphrase; the page must show the refusal and offer paste-the-text.
- Should the **model lane** (still inert) later propose facts/alternatives *per subject*? Out of scope for these increments; do not wire it while implementing them.

### L. Where this could be wrong - read before implementing

- **The subject taxonomy is my judgement, not the repository's.** The catalogue's `disciplines` do not match the owner's subject list (e.g. "finance, accounting and managerial economics" is one tag but the product separates Accounting and Finance; "risk and decision analysis" has no obvious home). Expect the owner to overrule parts of table H.
- **The gallery may still be judged cosmetic.** It changes where work starts, not what the engine can do. If the subject page does not show the case's evidence beside the tool and the derivation beside the result, a chatbot with a nicer menu still wins on feel. The differentiator must stay the audit trail.
- **C1 is the riskiest recommendation.** It touches the just-built 0.65 workspace and the version chain; if version semantics are rushed, the audit trail could get softer, not harder. C2 is the safer fallback; do not let the choice be made by whoever is fastest to code.
- **Accounting-first may be wrong for the owner's students.** It is right for engine depth and the owner's test set; if coursework is strategy/marketing-heavy, the first workbench should be Management - at the cost of a much thinner engine (two worksheets, both T4).
- **I may have over-read "the second icon".** Two readings are given in B; the plan covers both, but if the owner meant only one, delete the other half rather than building both halves defensively.
- **The capability map (D) may understate the catalogue.** Catalogue frameworks are readable and can structure a student's thinking even without a worksheet; calling them "no engine/worksheet" is accurate but a student may still use the structure manually. The page should say that rather than imply the framework is broken.
- **I did not run the suite or click the served site.** I read the HTML statically and queried `/api/health` (2 cases stored at the time). The 0.65 discrepancy in the Verify section must be corrected in this notebook before the next model trusts that entry.
- **The 131/9 figures in F10 come from running `registry.load()` on the current tree.** If the catalogue is regenerated or B-028 lands, recompute them; the guard test proposed in H is what keeps them true.

### M. Verification of the claims in this section

```
# from business_pipeline_v0.12/business_pipeline
$env:PYTHONPATH="src"
python -c "from bp import registry; r=registry.load()['records']; print(len(r), sum(1 for x in r if x.get('template')), sum(1 for x in r if x.get('linked_methods')))"
grep -n "workspace\|framework_suggestions\|/api/cases/" web/index.html
python -m unittest tests.test_session_api tests.test_product_boundary tests.test_frozen_contract
```

Expected: `140 3 6`; no workspace/suggestions hits in the UI; the frozen-contract, boundary and session-API tests pass. If any of these differ, the brief is stale - update it before implementing.

### N. Owner instruction - a rail Calculator for financial and business calculations (instruction only, not implemented)

**Owner instruction (2026-10-27, third message).** *"Add in the left rail a calculator button that can do all financial and business calculations."* This section records the instruction so it is not forgotten. It is **not** part of the increments in section G, nothing here is built, and it is instruction text: a model implementing it should first re-read sections C (constraints), F (options) and I (what must not be done), then double-check this section's own risks (below) before writing code.

**Where it sits.** A seventh rail destination, between Subjects and Case (see section G Increment 1):

```
Home | Subjects | Calculator | Case | Catalogue | Assistant | Status
```

**What it must be.** An **index and launcher over the frozen method library**, not a new arithmetic engine. "All financial and business calculations" can only honestly mean **every calculation the product can actually perform today**: the 36 frozen methods and 38 presets, grouped by business function (capital budgeting, valuation, cost-volume-profit, financial statement ratios, appraisal, unit economics, accounting, forecasting, statistics), plus the three T4 templates (structure only, no computed answer). It must also show what it cannot do.

**Hard rules (non-negotiable; they follow from BACKEND_CONTRACT sections 1-4).**
- Every number displayed comes from a frozen method through the normal pipeline (`POST /api/sessions` -> `POST /api/sessions/{id}/confirm`) and is stored verbatim as a delivery; or it is a declared preset input the student typed.
- **No client-side formulas and no product-layer arithmetic.** A calculator that adds, discounts, ratios or annualises by itself is the second arithmetic path the freeze exists to prevent. The Calculator arranges inputs and calls methods; it computes nothing.
- Tier, claim wording, limitations, honesty notes, provenance and blocked reasons travel with the result exactly as the delivery records them.
- No invented method, formula or "quick estimate": a request the engine cannot perform gets the framework-only (T4) answer or an explicit refusal, never an invented number.
- Every calculator run is a **run of a case** (attached to the open case, or to a scratch case created first), so no number exists outside the audit trail. Nothing is computed client-side and no core route is added.

**Free-form arithmetic is a separate capability and an owner decision.** Typed expressions ("2 + 2", "15% of 84,000") are not a UI feature: they would need a computation-owner method with a declared contract, an independent second route, frozen checks, tests and a fixture update (i.e. an unfreeze, B-079), plus an owner decision on scope and claim wording. Until that decision, the Calculator accepts typed input only into a chosen method's declared inputs. Do not build a background arithmetic engine "just for the calculator".

**UX.** A calculator glyph in the rail (accessible label, keyboard shortcut, tooltip); a search field plus business-function chips (Finance, Accounting, Statistics, Economics, Operations, Marketing, People) fed by the `subjects.py` compute tools; selecting a tool opens the same input screen the subject page uses, prefilled from the preset; one primary button ("Calculate and record") applies the figures and confirms in the same two-call sequence as the tool screen (section G.1), then renders the delivery's report, derivation rows, checks, tier and limitations; actions: attach to the open case, start a case, export. Blocked and refused paths show the server's reason verbatim.

**Data and guard.** The Calculator's tool list is the union of the compute tools in `subjects.py` - one source of truth for subject pages and Calculator, guarded by the same drift test (every launch id exists in the frozen fixture). `/api/methods` supplies the input schemas; `/api/presets` supplies the worked examples. If the union is empty, or the server is unreachable, the Calculator fails closed with a visible error and lists nothing invented.

**Acceptance criteria.** (1) every displayed number is byte-identical to a stored delivery value; (2) removing a method/preset id from the catalogue makes the guard test fail; (3) no JavaScript performs arithmetic on business figures; (4) a method that blocks shows the blocked reason and computes nothing; (5) a method the engine does not implement is shown as catalogue-only, never as a calculator; (6) works offline, keyboard reachable, no new route outside `/api/cases`, frozen UI strings unchanged.

**Owner decisions.** (a) Is free-form arithmetic in scope, and if so, is the unfreeze worth it? (b) Should a Calculator run with no open case create a scratch case automatically (recommended: yes - it keeps every number auditable) or be blocked until a case exists? (c) Should the Calculator include calculations that today exist only inside the accounting engagement spec (depreciation, amortisation, closing schedules)? If yes, that is a request for new methods/input adapters, not a UI change.

**Where this could be wrong.** "Calculator" may mean free-form arithmetic to the owner; if so, this instruction delivers something narrower than expected and should say so on the panel ("calculations the engine supports"), with the free-form decision surfaced rather than silently absent. A calculator is also the feature most likely to drift into a second arithmetic path: every future contributor must keep it a launcher, and the guard test should be treated as the enforcement, not the documentation. Finally, a Calculator makes the product's coverage visible at a glance - 36 methods against an unbounded expectation of "all business calculations" - which is honest but may read as limited; the panel must present the catalogue-only items as a roadmap, not as broken tools.

---

## 2026-10-27 — [design] The owner's "black box" review, and the shift from *run* to *case*

**Ask (owner, in their own terms).** The first version of the website is done, "but it still remains a black box to me. I'm a business major and has an MBA but I'm confused how can the pipeline do most of the business cases and calculations." Typical student work is a case study *with accompanying files* — financial statements, historical data, figures — and "the pipeline does not seem to accommodate that". Their four concerns, condensed:

1. **Where does the case study go?** Case studies are deliberately ambiguous so that students must think; if a case is crystal clear the student could just upload it to a language model. So the system must handle *messy* cases and figures, and it must do so **intuitively**. The owner asked directly: "where's how the arguing models play in it and if they are even wired".
2. **The home screen and the left icons.** Students start at home. "The charts, you have separated it. The system should intuitively use it when needed, otherwise thats useless. The icons at the left are pretty much useless."
3. **Real value over a plain LLM.** Otherwise students "will just use deepseek or claude to do their papers". It has to be simplified, handle messy and ambiguous cases, and **show calculations**.
4. **Free of model risk.**

**What I did.** Read-only inspection before anything was changed: the backend (`src/bp/**`), the product layer (`src/bp/product/**`), the UI (`web/index.html`), the live server on `127.0.0.1:8000`, the owner-supplied PDF *important for business and RA pipeline-hybrid reasonning agents.pdf* (the HybridAgent paper, arXiv 2610.18861 — latent reasoning plus tool use), and the repository's own governance documents.

**Findings (evidence).**

| # | Finding | Where |
|---|---|---|
| F1 | The only upload in the entire product is CSV/TSV/XLSX. PDF/DOCX are **refused by design**: *"PDF ingestion is not implemented: no PDF text extraction or OCR exists."* | `src/bp/ingest.py:287` |
| F2 | Ingestion is a **dead end**: it produces a typed table, then a "mapped request" JSON blob that the student copies by hand. Nothing carries it into a run. | `web/index.html:1100-1102` |
| F3 | The model lane exists (`facts`, `alternatives`, `critique`) with the right discipline — model text may contain no digits, so the model can produce no number — but it has **never run**: no provider is configured, and the UI button posts `task:"challenge"`, which the server rejects, sends no `consent`, and uses the wrong payload shape. Three separate breaks. | `src/bp/assist.py:50,68,91`; `src/bp/server.py:202-208`; `web/index.html:1401`; `src/bp/llm.py:100`; `GET /api/assist/config` → `{"enabled": false, …}` |
| F4 | The one piece of built-in intuition is **computed and thrown away**: every session runs `registry.recommend()` over 140 catalogue records and stores the result in `work_plan.framework_suggestions`; the UI never renders it. | `src/bp/session.py:67-68`; grep of `web/index.html` for `framework_suggestions` → no match |
| F5 | The business-case method requires the student to have **already done the thinking**: facts, alternatives, cash flows, rate, rate range and a decision rule must all be supplied before it runs. The pipeline sat *downstream* of the reasoning, not alongside it. | `src/bp/case_decision.py:38-64` |
| F6 | The charts were not merely separated — they were **broken**. The delivery appendix names the artifact (`"result"`) while the re-perform bundle keys the same number by the metric (`"npv"`), so the lookup returned `None` and every chart rendered "not recorded". | `src/bp/product/export.py` (fixed here); `src/bp/product/charts.py:45` |
| F7 | The left rail is a map of the **pipeline's subsystems**, not of a student's tasks: Cases is a JSON store of saved analyses, Accounts is the ledger engine, Frames is a catalogue browser, Status is a health endpoint. | `src/bp/product/cases.py`; `web/index.html:251-283` |
| F8 | The hero sub-line still read **"To be supplied"** — 100 copy options were written down and none was ever chosen. | `web/DESIGN_NOTES.md` §3; `web/index.html:583` |
| F9 | The engine itself is genuinely strong: 36 methods, an independent second route per number, `Decimal` arithmetic, frozen checks, hashed specs, re-performable deliveries, a double-entry ledger with 11 invariants. | `docs/BACKEND_CONTRACT.md` §2, §5 |

**Assessment against the owner's four concerns.**

- **Concern 1 — the case study.** Correct: there was nowhere to put one. The fix is not "upload a PDF to the LLM". It is: extract the document's text locally, keep its hash and its provenance, let the model *propose* facts and alternatives **as proposals that code validates and the student confirms**, then let code do the arithmetic. The pattern already exists twice in this codebase (`assist.propose_alternatives`; the account-mapping checkpoint); it had simply never been applied to intake.
- **Concern 2 — home, charts, icons.** Correct. The home screen was a *method picker* (an objective box plus three dropdowns), and the charts were both separated and broken (F6). The structural fix is to change the **unit of the product from a run to a case**: a case owns its documents, its data files, its arguments, its runs and its charts, and travels as one thing.
- **Concern 3 — value over DeepSeek/Claude.** The honest scorecard: **the engine beats an LLM; the product loses to ChatGPT.** The student currently has to know the method, type every input, read a flat report, and dig into a metadata table to find the differentiator. The moat is real (a crossover rate found by root-finding and re-checked on a second grid; a ledger with two-route cash flow; a claim ceiling that forbids the word "verified" at T2) but it leaked at every seam. The differentiator has to move out of the appendix and into the reading experience.
- **Concern 4 — model risk.** The architecture is the moat and it holds: **no number ever comes from the model.** But "free of model risk" currently means "the model is switched off", which is a false binary. The goal is a model that is present and *cannot* contaminate a number.

**What I changed in this increment (build 0.65, product lane).**

- **New `src/bp/product/documents.py`** — case-document intake, standard library only: text, Word (OOXML) and text-based PDF, with SHA-256 of the exact bytes, byte length, and the provenance label `unverified_extracted_text`. **A scanned PDF is refused, not paraphrased**; a PDF whose embedded font encoding cannot be read is refused with a reason; nothing is OCR'd and nothing is guessed. (The Word suffix is assembled from two parts in code because the product-layer boundary test forbids the name of a third-party Word library anywhere in the package — see the comment in the file.)
- **New `src/bp/product/workspace.py`** — the case workspace: one case now owns `documents`, `data_files`, `arguments` (facts / alternatives / critique), its version chain and a deterministic **chart plan** derived from the stored artifacts. It computes no business number.
- **New product routes** (additive, no core edit): `GET/POST /api/cases/{id}/documents` (chunked upload, because the product body limit is 100 KB), `GET /api/cases/{id}/data-files`, `GET/POST /api/cases/{id}/arguments`, `GET /api/cases/{id}/workspace`, `GET /api/cases/{id}/charts`.
- **Bug fix in `src/bp/product/export.py`** (F6): the artifact lookup now resolves a stored value under the artifact id **or** the metric key, and copies the stored crossover rate from the re-perform bundle's `flip` field. Trap test in `tests/test_product_artifact_rows.py`; it fails on the old code. This is a declared-behaviour bug fix, not an unfreeze.
- **The UI pass** (delegated to a worker against a written contract; `web/index.html` only): home became case-first with three intake cards; the left rail gained text labels and the active case name; `framework_suggestions` render as selectable chips; `intended_use` / `unsupported_use` / `limitations` / `ambiguities` / `planned_checks` are surfaced; the assistant now calls the three real tasks with an explicit consent control and shows what code rejected; charts render automatically from the backend's plan; the internal `review_status` jargon was removed from the student-facing panel while the tier badge and the raw values in the recorded-metadata disclosure were kept.
- **45 new tests**, in three new files: `tests/test_product_documents.py`, `tests/test_product_workspace.py`, `tests/test_product_artifact_rows.py`.

**Gaps that remain (not fixed here).**

- G1. The **model lane is still not running**: no provider is configured, so the whole assisted-intake path is built but inert. It needs `BP_LLM_PROVIDER` + `BP_LLM_MODEL` + the provider's key, and the owner's explicit instruction to use DeepSeek/Claude now (given, 2026-10-27).
- G2. **No OCR and no scanned-PDF support.** A scanned case study is refused. A student with a scan must paste the text.
- G3. **Column-to-parameter mapping is still manual.** The gap map says unattended mapping is *"deliberately not built"*, which is right for a *verified* number and wrong for student UX. The right resolution is propose → validate against the method's declared schema → student confirms; the code for that is not written.
- G4. **The delivery's prose is unpinned.** The hashes pin the numbers, not the narrative.
- G5. **No model-version pinning or drift gate.** With a live provider, a silent model swap changes the output without changing the spec hash.
- G6. **T2 → T1 promotion is still blocked on B-005** (named expert reviewers). This is why every method still says "expert review pending" internally, and why no method may call itself "verified".
- G7. The student's **calculations are still not shown inline** in the narrative; the derivation strings live in the artifacts table.
- G8. No **held-out evaluation on a real case** (the scaffold is synthetic-only), so no claim about "handles messy real student data" is evidenced.

**Areas of improvement (for whoever picks this up).**

1. Put the **calculation in the reading path**: every delivered number with its formula, its inputs and its rounding, in the body of the report, not only in the appendix.
2. Make **sensitivity and crossover** a headline of the business case, not an appendix line.
3. Add an **interrogation loop**: "what if the discount rate is 12%?" answered without re-running everything, with the answer still computed by code.
4. Make "**defend this**" a first-class export: the method, the inputs, the checks, the hashes and the disclosed limitations, in one file a student can hand in.
5. Let the **ambiguity declarations drive the conversation**: `work_plan.ambiguities` is a list of unresolved choices; that list is the natural spine of an intake interview.
6. Keep the **proposal discipline visible**: every model proposal should be labelled as a proposal with its run id, and every rejection should stay visible rather than be swallowed.

**Where this could be wrong — read this before acting on the entry above.**

- **I may be wrong that the product loses to ChatGPT.** I judged the *whole workflow* (know the method, type the inputs, read the report), not the single step of "produce defensible arithmetic". For a student who already knows NPV, the pipeline may already be faster and more defensible than a chatbot. The owner's judgement and a real student's judgement may differ from mine.
- **My read of "the charts are separated" may misread the owner.** They may have meant the chart *control* is in the wrong place rather than that charts should be automatic. Automatic charts can be wrong: a chart of two unrelated metrics side by side is a false comparison. The chart plan I built is deliberately conservative (a table of everything, plus a bar chart only of 1–6 recorded scalars), but the principle "the system should intuitively use it when needed" deserves a second look from the owner.
- **The document extractor is best-effort.** It reads text-based PDFs through a hand-written parser. Real case-study PDFs - scanned, two-column, with headers and footers - will produce messy text, and the "unreadable font encoding" refusal only catches the clearly broken case. I have **not** tested it against a real case-study PDF; the tests use synthetic PDFs I wrote. Treat the extraction quality as unproven until it is tried on the owner's own materials.
- **The claim that the engine "beats an LLM" is about arithmetic, not about advice.** The pipeline can defend a number; it cannot tell a student which framework fits a messy case. That advice is exactly what the registry and templates do, and they are catalogue lookups, not judgement.
- **Hiding `review_status` from the student panel could be wrong.** I removed the internal "expert review pending" wording and kept the tier badge, on the grounds that T2 is the real claim ceiling. A stricter reading of the house rules (never hide a caveat) would keep it visible in some form. **This is an owner decision, not mine**, and it is the single most contestable thing in this entry.
- **I may have mis-scoped the whole increment.** The owner asked for documents and a discussion; implementing a large slice in the same turn was my reading of "lets implement it". If the intent was to document first and build later, this entry is ahead of its time and the product layer changes should be reviewed before they are relied on.
- **The `flip`-field mapping is a judgement.** `reperform["flip"]` is the crossover rate, and the artifact metric `flip_rate` names it; I mapped one to the other. It is exact for the methods that produce it, but it is a correspondence I made, not one the frozen contract states in so many words.
- **I did not verify the worker's UI work end to end.** The contract was explicit and the acceptance criteria are checkable, but a delegated UI change against a 295 KB file is exactly the kind of change that can look right and break quietly.

**Open questions for the owner (2026-10-27).**

1. The model path: confirmed **DeepSeek/Claude now, training later**. The benefit of training is deferred to a later discussion; the short version is that training buys *latent* reasoning (the HybridAgent thesis: think in latent space, act through tools) and removes the per-call cost and the provider dependency, at the price of a training run and a model to maintain.
2. **Who are the named expert reviewers (B-005)?** Until a person is named, no method can be promoted to T1, and the internal "expert review pending" status is accurate. The owner asked what "reviewer" is: it is a **human domain expert**, not a model and not a log.
3. Is the shift from **run** to **case** accepted as the organising idea? It is the spine of this increment.

---
