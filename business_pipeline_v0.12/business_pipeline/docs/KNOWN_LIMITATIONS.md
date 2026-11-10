# Known limitations (release blockers marked *)
- * Sandbox is partial (see Stage 5 increment 5): vetted T1 code runs in a guarded child process, but this is NOT a security boundary. T2/T3 (model-written code) still need an OS-level container. Untested on Windows.
- * No authentication, tenant/case isolation or retention; sessions are in memory only.
- * No model calls: intake, formalization and drafting are deterministic templates, not model-assisted.
- Only NPV and break-even are executable (T1). No T2/T3, accounting, statistics, research or framework registry.
- "Revise brief" is intentionally absent (not built). Reject is the only alternative to confirm.
- Claim-wording phrase lists are placeholders [UNVERIFIED].
- Missing sources: v0.3 manual, research-pipeline manuals, frameworks catalogue.
- Server is for local development, not production.

## Added with the rubric reader (B-187)
- **A rubric is read, measured against the paper, and enforced at export.** `bp/product/rubric.py`
  parses a marking guide into criteria, weights, required elements, sections, a word budget and a
  citation style and refuses what it cannot read; `completion.draft` measures coverage, adds a
  "Rubric coverage" appendix before the reference list, and reports the rubric's word budget beside
  the paper's own count; `paper.missing`/`paper.check` block export when a **weighted** criterion is a
  gap, and demote every row to a warning when the student turns the gate off.
- **What is still not built.** A rubric heading the profile does not have is named as a gap, never
  created as an empty section (no section injection); and a scanned or photographed rubric needs the
  OCR chain before it can be read at all.
- **The student hands the rubric over from the page.** A stored PDF, Word, text or image file carries a
  **Use as the rubric** action beside **Use as the instruction**; the route reads and parses it, records
  the role `rubric` on the file, shows the student the criteria it read (and says the text is
  unverified), and starts nothing. The parsed rubric then travels with the next framework run.
- **The reader carries what the document states and nothing else.** A rubric with no weights gives
  `weight: None` on every criterion (never an assumed `1/n`); weights that miss 100 are reported as
  written (never rescaled); a page limit is never converted into a word count; two named citation
  styles are a problem, not a choice. `confirm_required` marks every parse the student must check.
- **Nothing is scored.** There is no mark, grade or predicted result anywhere in the module, the
  coverage report or the appendix; whether a criterion is *met well* is a human judgement
  (`VALIDATION_HARNESS.md` §5.2). Coverage answers presence only, and a rubric demanding
  recommendations gets a named gap rather than engine-written advice (B-154).
- **A scanned or photographed rubric is not readable yet** — the reader takes text, so a scan needs
  the OCR chain described in the OCR plan; until then it is refused by name, never guessed.

## Added with the dataset path (B-192)
- **A stored spreadsheet can now feed a method — as a proposal.** `intake.mapped_request` and
  `POST /api/intake/{id}/map` map the columns of an attached table through the frozen core's own
  mapper: inputs are validated against the method's `input_schema`, a scalar is refused rather than
  read from a column, and the response carries provenance and `not_mapped`. **Nothing runs** — there
  is no report, delivery or result in the response.
- **The calculator still has no picker for it.** No page surface offers a dataset to a tool yet, and
  the one "Your files" card on the calculator and subject pages is not built. Until it is, the path
  is reachable only from the API.

## Added with the vision-model OCR lane (B-191)
- **A scanned page is read when the machine has no OCR engine of its own.** The chain is the PDF's own
  text layer, then a local Tesseract, then an OpenAI-compatible **vision model** named by
  `BP_OCR_MODEL` and reached with `BP_OPENGO_API_KEY` (or `BP_OCR_KEY`; `BP_OCR_URL` names another
  gateway). Only a page neither of the first two can read reaches the network, the lane is off unless
  a key **and** a model id are configured, and a model id is never assumed.
- **The prompt transcribes and changes nothing.** It never summarises, translates, corrects or adds; a
  page the model read is recorded as `pdf_ocr_model` / `image_ocr_model` with the model's id, and the
  text is still unverified.
- **Every failure is named** — an HTTP status, an unreachable endpoint, an empty answer, or a page
  above the 8 MB limit. A page that cannot be read is refused, never returned blank.
- **A scanned PDF still needs `pypdfium2`** to render its pages before any engine can look at them;
  without it the file is refused naming the package.
- **No bundled weights, no auto-download, no GPU** — the engine is either the local Tesseract or a
  hosted model the owner configures.

## Added with the matrix figures (B-176)
- **The matrix figures are Word tables, not pictures.** They carry the framework's structure, cells and axes
  in academic styling; they do not reproduce the colour, icons or decoration of the slide templates in
  `Matrix templates/`. A layout that is genuinely radial (the McKinsey 7S hexagon) is drawn as its hub band
  between its two rows of elements, and a chain (Porter's value chain) as a support row above a primary row.
- **Four of the eight layouts reach the chat path.** SWOT, Ansoff, the value chain and VRIO build a figure
  from the chat's own answers and evidence; McKinsey 7S, BCG, GE/McKinsey and Blue Ocean ERRC build one on
  the worksheet path only, because the chat does not ask for their cells.
- **The figure is a summary, not the evidence.** A cell carries the identity of each item - the student's
  sentence, or the source's title with its citation - so the reader can see which cell rests on what. The
  prose below each heading carries the quotation and the interpretation; the figure alone cannot be cited
  from.
- **A proposed line of enquiry is not evidence.** `completion._suggest(mode="question")` and
  `proposals.propose()` help a student who is unsure, but a proposal closes no gap: the cell keeps its named
  gap, the block still counts as a gap, and the paper still asks the student to answer. A proposal carrying
  a number, a name, a link or a DOI the student did not write is refused, so the model can restate the
  student's own words and cannot add a fact.
- **The proposal needs a configured model.** With no model key the assistant is silent: the button is
  present, no candidate is offered, and the student answers in their own words. Nothing degrades and no
  error is raised.

## Added with the Project management subject (B-116)
- **Seven of the nine PM tiles are shared appraisal methods, and two are shared delivery methods.** NPV,
  IRR, discounted payback, project metrics, scenario analysis, business-case decision and trend forecast
  come from Finance; critical path/PERT and earned value come from the scheduling and project-control
  methods. The shelf adds no second arithmetic path.
- **Ten of the 16 delivery records remain read-only.** Balanced Scorecard, strategy map, KPI tree, OKRs,
  Scrum, Kanban, COBIT, ITIL, DeLone-McLean and TOE give structure and the evidence each one needs; none is
  filled in, scored or checked. PRINCE2 and PMBOK anchor the charter and risk register; WBS, RACI, the
  stakeholder/communication plan and lessons learned have their own worksheets.
- **The six delivery worksheets compute nothing.** The charter and WBS place supplied evidence and name
  empty blocks; the RACI refuses a cell that does not start R, A, C or I and blocks an activity without
  exactly one A or at least one R; the risk register records declared labels and computes no probability,
  expected value or score; the stakeholder plan records influence as a declared label with its evidence; the
  lessons-learned sheet names a lesson without an action or an action without an owner rather than filling it.
- **The schedule is deterministic.** CPM gives early/late dates, total float and the critical path from
  declared durations, with PERT expected durations and variance when three-point estimates are declared.
  The **Gantt chart draws the stored early dates, marks the critical path, shows float and draws the
  dependencies you declare**; it does not infer a sequence. **Resource levelling, crashing and one declared calendar are
  built**; levelling is greedy and non-preemptive, crashing is linear-cost and greedy rather than an LP
  optimum, and the calendar is a list of working period numbers. **Multi-project scheduling and a seeded
  schedule-risk simulation are built**; the multi-project rule is priority-ordered and greedy, and the risk
  sample assumes independent triangular durations with no resource limits. A decision tree, a binomial real
  option, a weighted decision matrix and an NPV/profit Monte Carlo are built; **arbitrary formulas, correlated
  inputs and fitted distributions are not**.
- **Earned value is arithmetic on one status date.** PV, EV and AC are cumulative figures the student
  declares; the method does not derive them from the schedule, and it cannot say whether the plan or the
  scope was right. EAC is one declared convention, not a forecast.
- **A critical path is not automatically the riskiest path**, and total float is shared: spending it twice
  is the student's error, not something the method models.
- **The project-ranking method fails closed when its MIRR check contradicts the NPV sign.** A project with a
  positive NPV at a high hurdle can still block because MIRR sits below that hurdle; the report is withheld
  rather than contradicting itself.
- **A stored appraisal case appears under both Finance and Project management**, because the subject filter
  is method-based. The case is not tagged with the shelf it was framed under.
- The PM **groups, glossary, guidance and student guide are teaching and presentation material**; they do not
  choose the project, validate an estimate or turn a read-only framework into a computed answer.

## Added with the conductor frameworks (B-151)
- **Value Chain and Ansoff place retrieved evidence by keyword** on nine and four dimensions; they do not collect activity costs, benchmark against rivals, size a market or rank the options. A dimension with no retrieved source is a named gap.
- **VRIO retrieves no external evidence.** The resources and the four judgments are the student's; the paper says so, and the export gate blocks until resources and at least one value judgment are supplied.
- **Break-even retrieves no external evidence** and reports only the frozen core's result from declared fixed cost, price and variable cost. It does not forecast demand or prove the expected volume.
- **Only break-even can be attached to a framework paper today** (`/api/cases/chat/{id}/computation`). Two-framework combinations remain limited to PESTEL + SWOT and Five Forces + Break-even.
- **Sample papers are generated, not written** (B-152): `scripts/build_conductor_samples.py` builds Ansoff, Value Chain, VRIO and Break-even papers through the conductor and renders them with `render_academic`. Their evidence is a frozen set of sources already cited in this repository; VRIO and Break-even use none and say so. A value-chain sample names its unsupported activity as a gap rather than filling it.
- **The title page has no invented author.** The byline is an optional list of the student's own lines; when it is empty the title page simply omits it, and the product never prints a placeholder.
## Added with the digital marketing lane (B-117, B-121, B-133)
- The seven digital methods are **arithmetic on declared counts**. Nothing reads Google Analytics, Google Ads, Meta, TikTok or an email platform: the counts, the conversion definition and the attribution window are the student's, and the report says so.
- **Attribution credit is not causation.** `attribution_split` compares first-click, last-click and linear shares from counts you supply; it does not process touchpoint logs, and no holdout, incrementality or lift test exists.
- **`ab_test_two_proportion` is one two-sided pooled normal test.** It has no sequential or peeking correction, supports two arms only, needs conversions in both arms, and its interval assumes independent observations - survey weights, clustering and repeated measures are not modelled.
- **Return on ad spend is attributed revenue over spend**, not profit and not incremental revenue. Break-even return on ad spend is 1 / contribution margin rate and appears only when that margin is declared.
- **Channel economics allocates nothing.** Shared, brand and overhead spend must be assigned by the student or left out; lifetime value is contribution margin / churn, undiscounted, with no survival curve or saturation effect.
- **Email opens include machine opens**, so the open rate is an upper bound on reading; no deliverability, consent, spam-complaint or list-deduplication check is performed.
- **Social and web rates use the platform's own definitions.** Engagement, session and conversion definitions differ between platforms and change over time, and no bot filtering, view-through, sentiment or cross-device identity resolution is applied.
- **No budget, bid or creative recommendation is made anywhere in the lane.** `MKT-13..MKT-21` are framework records: `MKT-14` (SEO/content), `MKT-21` (automation and lead scoring) and the planning records remain read-only until a worksheet is built.
- **RFM bands are relative to the file** (B-121). Quintile scores are ranks inside the uploaded customer list, so the same customer can score differently in another dataset; ties share the better band, so bands need not be equal in size, and no external or industry benchmark is applied.
- **The RFM segments are labels from declared rules**, tried in a fixed order; nothing tests whether a segment is stable over time, differs by more than chance, or predicts next-period value.
- **Media reach is declared, and combined reach is an estimate** (B-121). `media_plan` uses the random-duplication formula, which assumes different vehicles' audiences overlap only by chance; real overlap is usually higher, so the combined reach is an upper bound. There is no measured overlap, no effective frequency, no wear-out, no scheduling and no recommended buy.
- **Market share is arithmetic on the market you declare** (B-133). `market_share` divides declared firm sales by declared market sales; the boundary is the student's, no market data or competitor estimate is retrieved, and no share change is tested for significance.
- **Customer value rests on constant rates** (B-133). `clv_model` sums a constant margin at a constant churn and discount rate over a declared horizon; it fits no survival curve, models no expansion revenue and is not a perpetuity.
- **Segment profit carries the allocation you chose** (B-133). `customer_profitability` takes the allocated cost as declared, absorbs no fixed cost, applies no depreciation or capital charge, and reports no customer-level or time-series result.
- **Five marketing worksheets structure evidence and compute nothing** (B-133). The journey map, Kano grid, SERVQUAL grid, paid media plan and measurement plan name empty blocks and cells; they do not derive a Kano category, average a SERVQUAL gap, deploy a tag or read a platform.

## Added with free market-data lookups (B-106, B-109)
- Five sources are wired: **Frankfurter** for reference FX, the **U.S. Treasury par yield curve** for a risk-free rate, **Alpha Vantage** for equity quotes (the user's own free key; its fundamentals endpoint is premium and is not used), **SEC EDGAR** for US filings and XBRL fundamentals, and the **World Bank** for macro indicators. Yahoo Finance is **not** used: it has no public licence for this use.
- Alpha Vantage needs `BP_ALPHAVANTAGE_KEY` for the **quote**; on the free tier it allows 25 requests a day, cached for 24 hours. Without a key the quote refuses and says where to register. The **fundamentals** button reads SEC XBRL instead and needs no key.
- A retrieved value is **published by the source, not independently verified here**. There is no cross-source check, no correction and no guarantee that the source's terms will stay the same.
- The value is **never written into a method input automatically**. The panel shows the value, as-of date, source and a link to the provider; the student confirms and types it into the tool.
- A lookup needs network access. On failure it returns a reason and no value; it does not fall back to a remembered or invented rate. Caches are in memory only and clear on restart.
- FX is quoted as one unit of the base currency in the quote currency, on the source's latest business day unless a date is given. A Treasury par yield is a **US** rate, not any country's policy or lending rate.
- **Private-company figures and anything the five sources do not cover are manual entries.** The product says so rather than scraping a site.
- One observation (or one filing list) is returned at a time; there is no stored price history, chart or portfolio tracker.

## Added with document reading (B-107, B-110)
- PDF reading uses the **text layer** when there is one; a scanned PDF is rendered with `pypdfium2` and OCR'd with a local **Tesseract**. If either optional reader is absent, the file is stored and reported `ocr_required`.
- Image OCR runs only when **Tesseract**, `pytesseract` and Pillow are installed locally. The Windows build resolves the engine from `BP_TESSERACT_CMD`, PATH or the usual install folders.
- `pypdf`, `pypdfium2` and `pytesseract` are **optional product-layer dependencies**. If one is absent, the corresponding extraction is refused with a hint; structured CSV/XLSX ingestion is unaffected.
- Extracted text is **unverified**: columns, tables, headers and footers can be reordered or garbled, and ligatures, handwriting or unusual fonts may be lost. Check it against the document before using it.
- Limits are refused, not truncated: 5 MB upload, 50 PDF pages (20 for OCR), 200,000 characters, and encrypted PDFs. DOCX, legacy `.xls`, handwriting and forms are not read.
- OCR is CPU-bound: a page takes a moment, so a long scan is refused rather than holding the request open.
- Extracted text is stored beside the payload as `<id>.txt` and is **not** placed into a method input automatically; the user reads, confirms and types what is needed.


## Added with the student finance shelf (B-090)
- Every added finance method is **arithmetic on declared inputs**. Methods still retrieve nothing: the market panel can look up a labelled reference value (B-106), but the student confirms and types it, so a stale or wrong declaration still flows straight through.
- `time_value` and `loan_amortization` need the rate and term to be declared; there is no rate, term or payment solver. No fees, insurance, taxes, grace periods or variable rates.
- `bond_analysis` prices a plain fixed-coupon bond **on a coupon date** with no accrued interest, day-count convention, embedded option, credit spread or spot curve. Duration and convexity are local parallel-shift sensitivities.
- `capm` uses a declared risk-free rate, market return and beta, or estimates beta by OLS from the supplied series; it does not choose an index, test beta stability or model multiple factors. Hamada relevering is arithmetic on the declared debt-to-equity ratio and tax rate.
- `dupont_analysis` uses period-end balances and one period; no averages, benchmarks or adjustments. The five-step form appears only when EBIT, pre-tax income and tax are all declared, and a zero or negative equity blocks. Comparison is **one declared prior period** (simple relative growth), not a multi-year trend or index series.
- `trend_analysis` is historical arithmetic on declared periods: the common-size base is revenue and the index base is the first period, so changing either changes every percentage. No adjustment, restatement, accounting-policy alignment, forecast or industry benchmark. A compound rate uses only the endpoints; a net-income CAGR is omitted when the base period is not positive.
- `multiples_valuation` is **T2**: the peers are declared, not screened. No growth, risk, one-off-item or accounting-basis adjustment; no control premium, liquidity discount or fairness opinion.
- `working_capital` assumes constant demand and constant order/holding costs; no seasonality, quantity discounts, stock-outs or cash budget. The trade-credit cost is an annualised convention.
- `portfolio_analysis` is two assets with fixed weights; no multi-asset optimisation, efficient frontier, short selling, transaction costs or forecasting. Sharpe, Treynor and Jensen depend on the declared risk-free rate and benchmark series.
- `project_metrics` uses declared after-tax cash flows; no tax computation, depreciation shield, working-capital release, unequal-life ranking rule or real options. IRR is reported only when a single root exists.
- `option_pricing` is **T2**: European exercise only, constant volatility and rate, no jumps, stochastic volatility or credit risk. The binomial tree is a numerical cross-check of the same model, not independent evidence. Implied volatility is not computed.
- `risk_metrics` reports a quantile and a tail average: VaR is not a maximum loss, the parametric route assumes normality, and the square-root-of-time scaling assumes independent returns. No volatility model, simulation, backtest or credit/liquidity risk.
- `fx_parity` states the parity identities under their assumptions; it is not a forecast, and it ignores capital controls, transaction costs and risk premia. The quote convention is domestic currency per unit of foreign currency. The hedge comparison is **one declared forward against one expected spot**; no option, swap, rolling programme or hedge accounting.
- `leverage_analysis` is single-period and assumes the interest is deductible and the firm is profitable enough to use the shield. The Altman Z-score is computed but **no safe/grey/distress cut-off is applied**, because the thresholds are sample-specific and unverified here. EBIT-EPS indifference compares **two** plans only; it does not choose between them, and it ignores risk, covenants and issue costs.
- `scenario_analysis` changes only the discount rate; it is not a joint scenario, probability-weighted scenario or Monte Carlo simulation.
- The methods show the formula and the intermediate values a student needs, but they are **not a textbook**: they do not derive the formulas, teach the theory, or mark a student's working. A result is only as good as the declared inputs.
- The in-app topic groups, study notes, glossary and period badges are **presentation metadata**. They describe the method and its conventions; they do not validate the inputs, choose the right tool, or turn a per-period figure into an annual one.
- A rate above 100% in any output triggers a **warning note** that rates are decimals, but it does not refuse the run: a declared rate above 100% can be genuine, and refusing it would be a false block.

## Added at Stage 5
- Statistics: descriptive only, one variable. No inference, intervals, effect sizes, groups, weights, quartiles, .sav input.
- Golden fixtures are hand-verified; NIST and SPSS reference outputs have not been generated. Provenance of the NumAcc1-style case is [UNVERIFIED].
- env_hash now fingerprints the interpreter, platform and bp source; it does not pin third-party packages because none are used.
- Claim typing is still by phrase lists, not a reviewer model.
- Provenance tags on inputs are declared by the requester and not independently checked.
- Manual v0.3 features not built: case workspace (5.9), learning loop (10.1), ingestion controls, .sav/.sps handling, 15B items.

## Added with correlation
- Only two variables, one test; no multiple-comparison correction machinery beyond a declared "none".
- Normality screen is a skewness/kurtosis screen, not a formal test; linearity and independence are untested.
- Spearman interval and p-value are approximations; the interval formula is [UNVERIFIED].
- No power calculation, weights, clustering, partial correlation, or SPSS-default comparison (9B.4 register lists only our own defaults).

## Added with regression
- OLS only: numeric predictors, up to five; no categorical, interaction, polynomial, weighted, clustered or time-series models.
- Diagnostics are coarse screens with conventional limits [UNVERIFIED]; they may block valid data or pass flawed models.
- No out-of-sample validation, so no predictive claims (manual 7); associational ceiling only.
- No power or sample-size calculation; no multiple-comparison correction.

## Added with group comparison
- Two independent groups only: no paired data, more than two groups (ANOVA), proportions or counts (chi-square).
- Mann-Whitney interval and Hedges' g interval are approximations [UNVERIFIED against a published reference].
- Group-size minimum of three for Welch and about four for a Mann-Whitney interval.

## Added with the sandbox
- Guards are best-effort (patched socket, open, os and subprocess calls). Code using low-level calls (os.open, ctypes, native extensions) could bypass them. Do not run untrusted or model-written code on this layer.
- Memory cap uses the POSIX resource module; on Windows only the timeout applies. No CPU-time limit beyond the timeout.
- Developed and tested on Linux. The Windows path (python -S -s, SYSTEMROOT environment) is untested. If the sandbox fails there, runs block with "sandbox failure" and `--no-sandbox` is a development-only workaround.
- Builder patching is disabled when the sandbox is on (T1 only). Fallbacks still work.
- Re-performance compares outputs exactly or within 1e-12; results on another OS or Python version may differ in the last digits of float-derived values and are then reported as within tolerance, or as an environment difference.
- Unit tests run in-process for speed; sandbox behaviour is covered by tests/test_sandbox.py.

## Added with the registry
- Recommendations are lexical: they miss paraphrases and can suggest a loosely related item. They suggest; they never apply.
- Every record is "unreviewed". There is no limitations, contraindication or evidence data, so the system cannot yet say what a framework will miss or how well supported it is.
- No framework templates: selected frameworks guide a T4 text answer and are recorded in the spec; they do not yet drive a structured analysis.
- Theory citations must come from retrieved sources; the system has no retrieval of research literature, so supporting theories are pointers only.
- Evaluation set is small, author-written and not expert-reviewed.
- Edition and permission checks for standards are flagged, not performed.

## Added with framework templates
- Only SWOT (with STR-18 audit) and Five Forces have templates; the system cannot check that evidence is accurate or items are correctly classified.
- Evidence text is limited to 400 characters on one line, 60 items, 20 options, for safe verbatim reproduction.
- Reports quote your evidence; if it contains personal or confidential data, it appears in the report and bundle.
- TOWS pairing labels are derived, not judged; options themselves are yours.

## Added with the business-case slice
- The comparison is only as good as the facts, alternatives, cash flows and rates you enter; the system does not assess realism.
- NPV only, with certain cash flows; no risk weighting, probabilities, break-even comparison, or unequal-life adjustment.
- Decision rule "highest_npv" is the only rule; other rules (payback limits, budget constraints, multi-criteria weights) are not implemented.
- Default alternative ids are positional; supply ids to keep them stable when reordering.
- No model-assisted steps (no case reading, alternative generation or reviewer challenge).

## Added with the ledger spike
- The ledger kernel is a spike: not wired into the pipeline, no UI, no mapping-confirmation checkpoint, one period only, no schedules, no cash flow statement, no reconciliation, no standards retrieval.
- Flags (abnormal balance, contra-name heuristic, missing accrual) are heuristics that suggest items to confirm; they will miss problems and produce false alarms.
- Mid-year policy changes cannot be detected without a declared input.
- Beancount was not evaluated; the manual's statements about it are unverified.
- The research workflow (formerly Stage 7) has a **ratified living manual** but no built stages: `docs/RESEARCH_EVIDENCE_WORKFLOW.md` is the working authority for REW (B-053, R11 ratified), while its stages R0–R8, feasibility tiers and study taxonomy remain PROPOSAL/OPEN until the owner ratifies R1–R10; the ten original blocking questions are preserved there as Q1–Q12.
- Only the literature retrieval/verification boundary exists (src/bp/literature.py, PROVISIONAL; smoke-tested live against one DOI, not evaluated across sources or formats). It records a response SHA-256 + UTC retrieval time per resolved retrieval (B-054), but keeps no durable retrieval log, so a hash proves what the source served at verification time — not that its metadata is correct, nor that the DOI still resolves later.

## Added with the model provider
- Never run against a real model. The Anthropic, OpenAI-compatible and DeepSeek adapters are unit-tested with a fake opener only; no live call has been made.
- Proposal quality is unmeasured; no evaluation set of real cases exists yet (a scaffold with synthetic fixtures was added, `src/bp/evaluate.py`).
- The quote check prevents additions beyond submitted text but cannot stop quoted injected text; user review is the control.
- The PII scan is a heuristic. Text leaves the machine when assistance is used; personal data is allowed only with explicit acknowledgment (B-038).
- Proposals are not reproducible; only their hashes are recorded.
- Only three tasks (facts, alternatives, critique) and only the business-case flow use assistance; other methods and templates do not.
- Cost is capped by call count only; no price table.

## Added with ANOVA, Kruskal-Wallis and chi-square
- ANOVA covers three or more independent groups only; no post-hoc pairwise tests, repeated measures, factorial designs or Welch ANOVA (equal-variance failures switch to Kruskal-Wallis instead).
- Chi-square is independence-only on count tables; goodness of fit, Fisher's exact and Yates corrections are not implemented, and any expected count below the declared floor (5) blocks the analysis.
- Skew/kurtosis limits (2/7), Levene level (0.05), eta/epsilon cut-offs (0.01/0.06/0.14), Cramer's V cut-offs (0.1/0.3/0.5) and the expected-count floor (5) are conventions from memory [UNVERIFIED], declared and overridable (B-042).
- Kruskal-Wallis p-values and Cramer's V use approximations; no confidence interval is reported for the rank-based effect size.

## Added with trend forecasting
- The forecast is a linear trend only: no seasonality, cycles, external drivers, structural breaks, exponential smoothing or ARIMA, and it extrapolates beyond the observed range.
- The out-of-sample check holds out a quarter of the series (capped at 3 periods) and reports the recent-past error; it cannot measure future accuracy.
- The holdout-size rule, minimum series length (6), horizon cap (12) and small-sample wording threshold are placeholders (B-043).
- Prediction intervals assume independent, roughly normal errors around the trend.

## Added with the Stage 8 schedule engines
- Schedules cover straight-line, reducing-balance and units-of-production depreciation, level- or fixed-payment loan amortization, straight accruals, asset disposal, prepayments, deferred income, bad-debt allowances with an optional write-off, and revaluation of an asset. Not covered: sum-of-digits depreciation and variable-rate loans. A depreciation `method` is declared; `changes` (a prospective revision of life or residual) is supported by straight-line only, because a revised life has no defined meaning for the other two methods. A bad-debt allowance is an estimate: the owner declares the charge or the closing balance wanted, and the engine computes only the movement. Revaluation offers both permitted presentations (proportionate restatement and elimination) and follows IAS 16.39/16.40, but the engine does **not** track a surplus per asset: the part of a decline that reverses a prior surplus must be declared (`reverses_surplus`), and depreciation after a revaluation is not automatically restated onto the revalued carrying amount. **Disposal and revaluation read a single accumulated-depreciation account**, so two assets that share one accumulated account cannot be disposed of or revalued separately: give each asset its own accumulated-depreciation account. The engine refuses rather than guessing which asset the balance belongs to. **A schedule cannot span a period boundary:** every release, charge or recognition must fall inside the engagement period, so a prepayment or deferred-income balance that outlives the period must be carried into the next period as an opening balance rather than left in a schedule. Depreciation after a revaluation must likewise be declared against the revalued carrying amount; it is not restated automatically.
- Rounding rules are declared: depreciation's final period absorbs the remainder; interest rounds half-even; a payment never exceeds the balance due (so a large fixed payment repays early); the level annuity rounds up. Amounts beyond the currency places are rejected, never silently rounded.
- Schedule specs are validated data, but the module is not yet wired into the pipeline, the sandbox, or the workbench, and there is no account-mapping confirmation checkpoint yet.
- Management accounts only; not GAAP/IFRS-compliant statements (manual 9.5).

## Added with the cash flow statement
- The cash flow statement covers the period's movements only (opening balances excluded) and its two-route check guards the total change in cash, not the operating/investing/financing split.
- Activity classification is a declared heuristic: explicit account activity tags win; otherwise income/expense defaults to operating, assets to investing, liabilities/equity to financing. Mixed-counterpart entries are classified operating-first and flagged; cash-to-cash transfers are flagged. The manual's account-mapping checkpoint should replace these defaults.
- The cash flow check is a separate `cash_flow()` result, not part of the six frozen ledger invariants.

## Added with multi-period closing
- Closing moves income, expense and declared dividend balances into retained earnings through generated entries the caller posts; accounts with abnormal balances block closing until a human decides.
- The retained-earnings rollforward (B-034 resolved) and the zero-after-closing check are separate checks, not part of the six frozen ledger invariants.
- Multi-period support chains one period into the next (closing balances → opening entry → opening-balances invariant), but output is still per-period: no comparative multi-column statements.
- `statements` omits zero-net accounts, so a closed income/expense account or a fully repaid loan shows nothing rather than zero.

## Added with the declarative engagement
- The engagement method is T2 custom analysis pending the engine decision (B-032) and a named expert review; the report and the appendix state this.
- The spec must declare `prior_closing` balances ({} for a first period) and a reporting framework; the kernel posts only what the owner declares (entries, schedules, closing) and never posts silently.
- Structured results (statements, trial balance, cash flow, flags, export) travel in the appendix; the narrative report carries only scalar totals.

## Added with the reconciliation engine
- Matching pairs a book movement with a statement line of the same signed amount only; several lines with the same amount are paired first-unused and flagged `ambiguous_match`. No date or reference matching is implemented.
- Unrecorded statement items (for example bank charges) are listed for the owner to book; they are action items, not failures. The reconciliation ties once the disclosed adjustments are shown.
- The reconciliation checks are "not applicable" when the engagement supplies no reconciliation; they are counted in `checks_na` rather than silently passing.
- Reconciliation runs on the engagement's period only; opening balances come from the opening entries and must equal the statement's opening balance.

## Added with the account-mapping checkpoint
- The second mandatory checkpoint pauses after the spec is frozen and before anything is posted; the owner confirms a mapping table of code, name, type, statement line, role, activity and contra, plus three mapping checks. Rejecting blocks with nothing posted.
- `Pipeline.run` is a convenience path that confirms both checkpoints automatically (documented); the interactive path through the session/API honours the pause.
- The checkpoint is logged under the formalization stage (`checkpoint: account_mapping`) rather than as a new stage, so the stage list is unchanged for every method.
- Mapping checks are structural only (a statement line per account, a cash account, one retained-earnings account); they do not verify that the owner picked the right account for a transaction.

## Added with the policy-change input
- Only depreciation supports a computed policy change (useful-life and residual-value revisions); other estimate changes are disclosure-only, and retrospective restatement is not implemented (it blocks).
- A change is applied prospectively from the period containing its date; earlier periods are never restated.
- An UNDECLARED change remains undetectable from the journal alone — the spike's mid-year-change trap is unchanged; the declared input is the only way the system learns of it.
- The change total remains exact: the final period absorbs the rounding remainder, so accumulated depreciation still equals cost minus the final residual.

## Added with the statement exports
- Exports are plain text only (no PDF, XLSX or DOCX); fixed-width formatting is designed for a monospace view and a text download.
- The income statement is rendered from pre-closing figures while the balance sheet is post-closing, which is the correct pairing for a closed period; the trial balance omits zero-net rows.
- The cash flow statement presents the direct-route line items and the three activity totals; the indirect route appears only as its agreement check.
- Statements are management accounts prepared from the declared entries; they are not a GAAP/IFRS presentation and are not assurance.

## Added with logistic regression and Cronbach's alpha (B-074)
- `logistic_regression` supports **numeric predictors only** (no categorical dummies, interactions or splines), uses large-sample Wald inference and produces **no goodness-of-fit or calibration statistics**. There is no regularisation: complete separation, a single-class outcome or collinearity block the run instead of returning huge or unstable coefficients. Coefficients are log-odds, not effect sizes or probabilities.
- `reliability_alpha` measures **internal consistency only**: it is not validity, not unidimensionality and not a factor analysis. It uses listwise deletion and the classic formula (sample variances); ordinal items, standardised alpha, confidence intervals and missing-data mechanisms are not modelled.

## Added with cost-benefit, cost-effectiveness and SROI (B-073)
- All three appraisal methods are **arithmetic on declared valuations**. The system does not monetise an unvalued effect, choose a discount rate, apply deadweight/additionality/attribution adjustments, or assume a willingness-to-pay threshold.
- `cost_benefit` and `sroi` use one rate for all periods and end-of-period timing; there is no risk adjustment, sensitivity distribution or distributional weighting.
- `cost_effectiveness` compares each option with the **first-listed comparator** only, on one outcome scale. An option with the same effect as the comparator blocks (undefined ratio); dominance is flagged, not ranked; there is no threshold-based recommendation.
- SROI is not assurance and does not substitute for an audit.

## Added with ingestion mapping and finance methods (B-071, B-072)
- Ingestion mapping only handles **list-shaped inputs** (`value_list`, `code_list`, `column_map`); scalar inputs such as a discount rate cannot be mapped from a column. Long-format data (one row per observation with a group label) cannot be turned into the `groups` shape by mapping — the wide layout is required for group columns.
- Mapped inputs are recorded as owner-supplied with a file/SHA-256 provenance note; the hash identifies the source, it does **not** verify the data, and no conversion, cleaning or imputation is performed by the mapping.
- `unit_economics` uses a single constant churn rate and a period-value LTV (no discounting, no retention curve, no tax or financing); payback assumes the margin is earned every period.
- `multi_product_breakeven` assumes one fixed product mix and constant prices/costs; no step costs, capacity limits or price-volume effects. Per-product units are a break-even mix, not a target.

## Added with factorial ANOVA and post-hoc pairwise tests (B-070)
- `two_way_anova` is **balanced only**: every cell must hold the same number of observations. Unbalanced designs are refused because type I/II/III sums of squares are different conventions and none is ratified; three-way, repeated-measures and ANCOVA designs are not implemented, and factorial assumption checks (normality, homoscedasticity) are not run.
- An interaction makes the omnibus F tests insufficient: the method does not localise simple effects, and `posthoc_pairwise` is the separate tool for that.
- `posthoc_pairwise` compares every pair with a **Welch** test and a declared correction (Holm, Bonferroni, or explicitly `none`). There is no Tukey HSD, Dunnett (vs control), Games-Howell or Dunn test, and the family is whatever the user declared — choosing it after seeing the p-values is exactly what a correction cannot repair.

## Added with multi-currency support (B-069)
- The currency table is a **declared ISO 4217 table** (code, name, minor units) embedded in `src/bp/currency.py`; verify it against the current standard when precision matters. Metals (XAU/XAG/XPT/XPD), testing/no-currency codes (XTS/XXX) and units of account without a minor unit (XDR) are not accepted.
- **No exchange rate is retrieved, verified, interpolated or triangulated.** A conversion needs a rate the owner declares; its provenance (`user`/`sourced`/`assumption`), optional source and date are recorded as declarations, not facts. A stale rate gives a silently stale amount beyond the caveat text.
- **One currency per engagement.** The ledger, schedules and statements use a single declared currency; there is **no consolidation, translation, FX revaluation or multi-currency reporting**. That would need retrieved rates plus a translation standard, neither of which is implemented.
- The converted amount is carried in the request's `currency` field, so that field must be set to the **target** currency for the display label to be right; the appendix always records both codes.
- Unknown currency codes are now **refused at intake** (previously any string was accepted), which is a deliberate fail-closed behaviour change.

## Added with WACC and DCF valuation (B-068)
- `wacc` does not estimate anything: the cost of equity and the AFTER-TAX cost of debt are declared inputs, and **no tax is computed** (B-052 still deferred). There is no CAPM, no beta estimation, no target-capital-structure iteration and no leverage-dependent recalculation; market weights are current, not target.
- One WACC is a single discount rate; it is not appropriate for cash flows of materially different risk.
- `dcf_valuation` is **arithmetic under declared assumptions**, not a market price or a forecast: the method does not forecast cash flows or choose the rate; timing is end-of-period by default or the explicitly declared mid-year convention (B-078), and the enterprise-to-equity bridge is the separate `equity_bridge` method (B-078). No tax computation and no scenario or real-option analysis.
- The terminal value typically dominates the answer and rests entirely on the terminal-growth and discount-rate assumptions; the delivery flags a terminal share above three quarters.

## Added with paired and one-sample t-tests (B-067)
- `paired_t` matches pairs **by position** in the two columns; a mis-sorted file silently pairs the wrong observations and produces a wrong test. There is no signed-rank (Wilcoxon) fallback for non-normal differences.
- `one_sample_t` compares a mean with a reference the user declares; it cannot say whether the reference is right. There is no one-sided test, trimmed-mean or median test.
- Both assume approximate normality and independent observations, screened only by wording; neither tests normality. Missing entries are excluded and counted, never imputed.

## Added with structured-file ingestion (B-065)
- Only **CSV/TSV** and **XLSX** are read. **PDF, scans, images and SPSS `.sav` are refused** with explicit messages: no OCR and no PDF text extraction is implemented, so reading them would be invention. Convert the source or paste its values with the source named.
- XLSX: the **first sheet** is read by default; `sheet=<name>` (exact, case-sensitive) or `sheet=<n>` (1-based) selects another (B-076). Merged cells are refused by default; the declared `merged="top_left"` policy repeats each anchor value across its range and records the expansion (B-076). Styles beyond date detection and rich text are not handled. Formula cells use the cached value stored in the file; a formula with no cached value is a missing cell.
- Declared conventions: first non-empty row is the header; headers must be non-empty and unique after trimming; a column mixing numbers and text is typed `mixed` (never coerced); empty/whitespace means missing; dates are normalised to `YYYY-MM-DD` using the workbook date system.
- Caps are **refused, not truncated**: 5 MB, 1000 data rows, 50 columns.
- Provenance is table-level (file, SHA-256, data row i and column j, sheet): it says where every value came from, not that the value is correct. The importer performs no type coercion, no imputation and no unit inference.
- Ingested columns are **not mapped automatically** into a method's inputs: choosing which column is `values`, `y` or `predictors` is the user's decision, so no column semantics are invented.

## Added with the equity bridge and the mid-year DCF convention (B-078)
- `equity_bridge` subtracts only the claims the owner **declares** (net debt, minority interest, preferred equity). Pension deficits, lease liabilities, options/dilution, contingent liabilities and any other claim are missing unless the owner includes them — the bridge cannot discover them, and it says so.
- The enterprise value is an input: the method does not value the business, verify the EV, or state a market price, control premium or liquidity discount. A per-share value is reported only when `shares_outstanding` is declared, and no treasury-stock or dilution method is applied.
- A **negative equity value is reported**, not refused: an enterprise value that does not cover the declared claims is a real result, and refusing it would hide the finding. Negative bridge components are refused because they usually mean a sign error.
- `dcf_valuation`'s **mid-year convention** (`timing="mid"`) discounts explicit flow t and the terminal value at exponent t−0.5 / n−0.5, i.e. every flow is assumed to arrive mid-period. It is a declared convention, not evidence about actual timing; the default remains end-of-period, so existing valuations and their re-performance bundles keep their numbers. The method still does not choose the rate, growth or timing convention for the owner.
- The mid-year change applies to `dcf_valuation` only; other discounting methods (`npv`, `cost_benefit`, `sroi`) remain end-of-period with a t=0 first flow and do not accept a timing input.

## Added with IRR and discounted payback (B-077)
- `irr` reports **one** internal rate of return, found numerically in the declared range -99.99% to 1000%; a root outside that range is treated as absent. When the cash flows change sign more than once the NPV function can cross zero several times, so the method **refuses and lists the roots** instead of picking one — which IRR is "the" IRR is not something the method may decide.
- IRR is a rate, not a value: it says nothing about the scale of the investment, cannot rank projects by itself, and assumes cash flows are reinvested at the IRR (a convention the method does not verify). It uses the same end-of-period, t=0-first timing as `npv`; unequal period lengths are not modelled.
- `discounted_payback` is a **liquidity** measure: it ignores every cash flow after the recovery point, so a project that pays back quickly and then loses money still looks acceptable. Interpolation inside the recovering period assumes the flow is spread evenly, and the ordinary payback at rate 0 is the same convention.
- Discounted payback requires a **negative first cash flow**; a positive first cash flow is refused. An outlay that is never recovered within the declared horizon **blocks** rather than reporting "> n periods" as a number.
- Neither method discounts at a rate it chooses: the rate (payback) or the cash flows (IRR) are the owner's declared inputs. No tax, financing or mid-year convention is applied.

## Added with XLSX sheet selection and the merged-cell policy (B-076)
- Sheet selection is by **exact case-sensitive name** or **1-based position**; there is no fuzzy matching, wildcard or "all sheets" mode, and one table still comes from one sheet. Reading every sheet would need a declared concatenation rule (same header? same order?), which does not exist, so it is not offered.
- The workbook's sheet list is reported (`sheets`, `sheet_index`) but **not** sheet visibility (hidden/very-hidden sheets are selectable if named); a missing worksheet part for the selected sheet is refused rather than falling back to another sheet.
- Merged cells are **refused by default**: expanding an anchor value across a range repeats data the file only stores once, and silently blanking the range would lose the anchor. The refusal names the ranges and offers the declared `merged="top_left"` alternative.
- Under `merged="top_left"` the expansion is **a declared convention, not a verified fact**: the anchor value is assumed to apply to the whole range, ranges whose anchor is blank are left blank, and overlapping/nested merges (which Excel does not produce) are refused as malformed. A merged *header* row spans two columns and expands to two identical names, which the duplicate-header rule then refuses — unmerge the header or use a single header column.
- Merged-cell detection covers the standard `<mergeCells>` element only; an equivalent visual merge simulated with borders or repeated text is invisible to the importer.
- `merged` and `sheet` are **XLSX-only**: supplying them for CSV/TSV is refused instead of silently ignored. The workbench ingestion card does not yet expose either control (OPEN, design-owner wiring).

## Added with retrieval failover and the drift sweep (B-064)
- Failover covers only the two configured literature sources (Crossref, then OpenAlex). If both are unreachable the lookup fails with a 502 rather than silently marking the DOI unverified; if both report "not found", the reference stays unverified.
- The drift sweep is **manual**, bounded (API default 10, cap 25) and network-bound: it re-resolves recent logged DOIs and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable`. There is no scheduled or automatic re-check, and it never rewrites the log.
- A `hash_differs` result means the source served different bytes since the citation was logged — it is a prompt for a human to re-check the metadata and the citation, not an automatic correction. `hash_match` proves the bytes are identical, not that the record is correct.
- The sweep uses the same priority order as verification, so a source that is down can make entries `unreachable` even though the log itself is intact.
- Standards, company-filing and tax source families are still not implemented, and no additional scholarly APIs (arXiv, PubMed, Semantic Scholar, Europe PMC) are configured; adding them needs a source/licensing decision, not more code.

## Added with the weighted summary (B-063)
- `weighted_summary` produces **summaries only**: weighted mean, weighted standard deviation, effective sample size and design effect. There is **no standard error, confidence interval or test**, because design-based inference needs a declared complex design (stratification, clustering, replicate weights) that is not implemented. The delivery says this explicitly.
- The weight kind must be declared: `reliability` (precision-style, unbiased weighted variance) or `frequency` (counts of observations). The two give different standard deviations; the convention is stated in the appendix.
- Weights are not validated. A wrong design weight is used as given, and unequal weights reduce the effective sample size — the design effect shows by how much. Zero, negative, mismatched-length and blank weights are refused rather than silently dropped.
- This is the only method that accepts weights. Other statistical methods still refuse a `weights` input with a specific reason, so a weighted dataset cannot be analysed as if it were a simple random sample elsewhere.

## Added with the missing-data bounds (B-062)
- `missing_data_bounds` reports **extreme-case bounds** for the complete-data mean: every missing value at the observed minimum or maximum. The bounds are honest but can be very wide, and a wide bound is the correct answer when little can be assumed.
- There is **no imputation** and **no MAR/MCAR/MNAR model**. The `mechanism` input is the owner's declaration: it is recorded with a note that it cannot be verified from the data, and it changes no number.
- The bounds cover the mean only. They say nothing about other statistics, about which mechanism actually holds, or about the direction of bias in an association.
- The generic missing-data disclosure (listwise deletion) is suppressed for this method because its own convention is stronger; the method's own disclaimer is delivered instead.

## Added with the power and minimum-effect method (B-061)
- `power_analysis` uses the **normal approximation**: exact when the standard deviations are known or planned, but with sds estimated from a pilot the exact power is somewhat lower (noncentral t is not implemented). This is declared in the template, the caveats and the appendix.
- It covers a two-sample or one-sample comparison of means only: no proportions, no cluster/weighted/repeated designs, no multiplicity (a family needs a smaller per-test alpha; use `multiple_comparison`), and no correlation or regression power.
- Power is a property of the planned design, not evidence about a result; a low-power study can still be significant and a high-power one can still fail. The reported "smallest effect at target power" is not a licence to ignore smaller effects.

## Added with the multiple-comparison correction (B-060)
- `multiple_comparison` corrects a family the user has already declared: it does not decide what the family should be, and choosing the family after seeing the p-values cannot be undone by a correction.
- Only Holm and Bonferroni are implemented. Both control the family-wise error rate under arbitrary dependence; neither models dependence, and there is no false-discovery-rate control (Benjamini-Hochberg) or resampling correction.
- The correction changes the reported p-values, not the design: a biased sample, a violated test assumption or a badly specified model stays biased or violated after correction.
- The existing statistical methods do **not** apply a correction automatically; their honesty block says so and points to `multiple_comparison`. There is no facility to assemble a family across several separate method runs.
- Power/MDE calculation, missing-data mechanism modelling/imputation and survey weights remain unimplemented (B-057 disclosure still applies to them).

## Added with the retrieval log and provisional citations (B-058)
- The retrieval log is **local and append-only** (one JSONL file, default `retrieval_log.jsonl`, `BP_RETRIEVAL_LOG` overrides): it is not a shared cache, is not encrypted, has no rotation or retention policy yet, and has no locking between concurrent server instances. It holds DOIs, titles and hashes, not case text.
- The log records **what the source served at that moment**, not that the metadata is correct, and the source may change afterwards. `reverify` is manual — there is no scheduled drift check.
- Citations follow the owner-ratified styles **APA 7** and **Harvard (Cite Them Right)** (B-059), but in plain text: italics (journal names, volumes) are not representable, titles are printed as the source returns them rather than case-converted, and author names are inverted only when the source supplies family and given names (Crossref does; OpenAlex returns display names only, and its citations carry a note saying so). There is no bibliography ordering or de-duplication and no in-text citation numbering.
- Only journal articles and books are fully styled. Any other source type (report, chapter, thesis, dataset) gets a declared generic layout with a note naming the source type, rather than a style that would imply it was handled properly.
- An unverified reference is always formatted with the `[unverified user-supplied…]` prefix in either style; the system cannot stop that text being pasted elsewhere, but the label is in the text itself.
- The workbench citation and log views are read-only conveniences over the API; the durable record is the file itself.

## Added with the 9B.3 honesty layer (B-057) — disclosure only, not the fix
- Every delivered computation now **states** the 9B.3 limits in the report and in an `appendix.honesty` block: missing values are excluded listwise without an established mechanism; multiple hypotheses are not corrected; no power or minimum-detectable-effect is computed; weights, clusters and repeated measures are unsupported and observations are treated as independent.
- **No number changes.** The actual upgrades are NOT implemented: there is no Holm/Bonferroni or other multiple-comparison correction, no power/MDE calculation, no missing-data mechanism modelling or imputation, and no survey-weight or clustered-data estimation. The disclosure makes the gap visible; it does not close it.
- Inputs that name an unsupported structure (`weights`, `weight`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are refused with a specific reason at intake, so such a dataset cannot be passed in and silently analysed as independent observations.
- Single-method runs test one hypothesis (OLS tests one per coefficient, with the family-wise exposure named); there is no facility to combine several methods into one corrected family. Post-hoc pairwise tests do not exist yet, so no correction is applied to comparisons that are not made.

## Added with ratio analysis (B-056)
- `ratio_analysis` is purely descriptive arithmetic on figures the owner supplies: no benchmark, industry average, cut-off or good/bad verdict is applied, because none is supplied or verified. A ratio being high or low is for the reader and the context to judge.
- Period-end balances and a 365-day year are declared conventions; average balances or a 360-day year would give different efficiency ratios.
- A ratio with a missing figure or a zero denominator is reported as not computed with its reason and never estimated; a negative denominator (for example negative equity) is computed and flagged, not hidden or reinterpreted.
- The supplied figures are not validated against a trial balance here, and no tax computation is performed (net income is used exactly as supplied). Multi-period comparatives, segment and multi-currency analysis are not supported; use `management_accounts` for the bookkeeping-level check.

## Added with the economics micro core (B-097)
- The five micro methods use **linear** demand and supply curves and a **partial-equilibrium** market. They do not estimate the curves from data, model shifts, expectations, inventories, trade, general equilibrium or dynamics.
- `elasticity` reports the **arc (midpoint)** elasticity between two declared observations only. It is not a point elasticity, an income elasticity or a cross-price elasticity, and two observations cannot identify a demand curve or prove causality.
- `tax_incidence` models a **per-unit** tax on sellers. An ad valorem tax, a tax on buyers at a different rate, evasion, administration costs and other markets are not modelled. The economic incidence is determined by the declared slopes, not by the statutory side.
- `price_control` models a single enforced fixed price. Rationing, queues, black markets, quality changes and dynamic effects are not modelled; the short side determines quantity traded.
- `market_concentration` treats the declared firms and revenues as the market. It does not define the market, handle import competition or geography, simulate a merger, or apply a legal threshold; HHI uses percentage shares (0-10,000).
- The student notes and glossary are product-layer guidance, not a reviewed textbook. No teacher or student review has been recorded yet; the release is labelled accordingly until one is.
- Macro, welfare/public, international/development, behavioural and advanced econometrics are not implemented yet, and the economics diagram renderer is deferred to the next increment.

## Added with the economics macro and firm core (B-098)
- `cost_curves` describes one declared quadratic cost function at one quantity. It does not estimate costs, model step costs, learning, capacity limits or economies of scope, and the shutdown test assumes a non-negative quadratic term.
- `profit_maximization` is a single-product, single-period, single-price monopoly or monopoly-like optimum. It does not model price discrimination, strategic interaction, entry or a price-taking firm.
- `market_power` uses two declared numbers and is not evidence of harm or of a legal violation; the implied elasticity is model-conditional.
- `national_income` is the expenditure approach only. It cannot cross-check the income or production approach, does not rebase or chain-link, and does not adjust for informal or underground activity.
- `growth_rate` uses two observations and does not forecast, fit a trend or decompose growth into capital, labour and productivity. The rule of 72 is an approximation.
- `inflation_cpi` uses two CPI values; it does not construct or rebase the index, adjust for core versus headline inflation, or model expectations. Real wage growth is an index comparison, not a household cost-of-living measure.
- `unemployment_rate` uses the labour-force definition implied by the declared counts; it does not adjust for discouraged workers, underemployment, informal work or seasonality.
- `money_multiplier` assumes no excess reserves and a constant reserve ratio and currency drain; it is an identity, not a forecast of the money supply.
- `fiscal_multiplier` is a closed-economy Keynesian identity with no crowding out, confidence, supply-side effects, lags or open-economy leakages.
- `budget_debt` uses declared aggregates and holds growth and interest rates constant; it does not model contingent liabilities, off-budget items, debt composition or a sustainability path.

## Added with welfare, international, development, behavioural and game theory (B-099)
- `externality_pigouvian` and `optimal_pollution` use declared linear marginal-damage/abatement or external-cost curves; they do not estimate damages or value non-monetary effects.
- `public_good` uses two declared individual benefit schedules and the Samuelson condition; it does not model free riding, contribution games or provision mechanisms.
- `social_welfare`, `gini_coefficient`, `poverty_measures` and `tax_progressivity` use declared incomes and taxes; no equivalence scales, taxes/transfers, in-kind income, multidimensional poverty or full progressivity index is included.
- `comparative_advantage` is the two-country, two-good Ricardian model; no transport costs, tariffs, demand differences or increasing returns.
- `tariff_welfare` is a small-country, partial-equilibrium model; no retaliation, terms-of-trade effect, quota or general-equilibrium effect.
- `exchange_rate_ppp` and `interest_rate_parity` use declared price levels and rates; PPP is a long-run benchmark, covered parity is an arbitrage condition, and neither is a forecast.
- `balance_of_payments` checks the declared identity; it does not validate the underlying data or assess sustainability.
- `hdi` uses the declared UNDP goalposts and does not adjust for inequality or multidimensional poverty.
- `expected_utility` and `prospect_theory` use declared utility or prospect-theory parameters; they are not estimated and prospect theory is descriptive, not normative.
- `labour_market` is a simple real-wage and wage-share comparison; no hours, composition, taxes, benefits, bargaining or full labour-share decomposition.
- `price_discrimination` and `cournot_duopoly` are two-market or two-firm one-shot models; no entry, capacity, differentiation, repeated interaction or collusion.
- `difference_in_differences` is a two-group, two-period estimate; it cannot test parallel trends and has no covariates, clustering or staggered adoption.
- `nash_equilibrium` covers pure strategies of a 2x2 game only; mixed strategies, larger games, sequential play and equilibrium selection are not implemented.

## Added with advanced econometrics (B-100)
- `panel_regression` requires a balanced panel and uses only within-entity variation; time-invariant regressors are absorbed, and no standard errors, clustering or dynamic-panel correction is computed.
- `instrumental_variables` is just-identified with one endogenous regressor and one excluded instrument; relevance is checked but the exclusion restriction is assumed, not tested, and there is no weak-instrument or over-identification diagnostic.
- `regression_discontinuity` is a sharp design with a declared bandwidth and a separate local linear fit on each side; it cannot test manipulation, choose an optimal bandwidth or handle a fuzzy design.
- `probit` uses one predictor and maximum likelihood with Newton-Raphson; separation is refused, and no robust, clustered or bootstrapped standard errors are computed.
- VAR, cointegration and the remaining time-series estimators are still parked.

## Added with the entrepreneurship shelf (B-104, B-105)
- `market_sizing` is **top-down arithmetic** on the customers, annual spend and two shares you declare. It does not estimate demand, retrieve census or industry data, test the shares, or grow the market. SOM is not a sales forecast.
- `startup_capital` adds the declared set-up costs and working capital plus a declared contingency, then subtracts owner equity and one loan. It does not price the equipment, build a costed bill of materials, time the spend, cost the loan, or model equity dilution, grants or supplier credit. A negative amount to raise is reported as a surplus.
- `cash_runway` uses **one declared net monthly flow**, optionally growing at a constant rate. There is no month-by-month budget, seasonality, one-off purchase, tax timing or financing inflow, and growth is applied to the net flow rather than separately to revenue and costs. A flow that never burns cash **blocks** instead of reporting an infinite runway.
- `pricing_decision` implements four declared pricing rules. It does not research willingness to pay or competitor prices, estimate a demand response, apply psychological pricing, discounts or tax. The markup-on-cost and margin-on-price conventions give different prices and both are shown.
- `return_on_investment` uses the **total** net gain over the holding period, not an annual cash flow, and ignores the timing of the flows inside that period. The annualised return is a constant compound rate; a loss of 100% or more has no real annualised rate and is refused when a holding period is declared.
- The `breakeven` extension reports the margin of safety against **your declared expected volume**, not against a budget or forecast the method verifies. The target profit is pre-tax.
- **Not built on this shelf:** cohort survival models, market share with a retrieved competitor, multi-input sensitivity and Monte Carlo, pre-money/post-money across several rounds, a term sheet, liquidation preference and anti-dilution. The shelf's **five** worksheets are the Business Model Canvas (`STR-15`), the Lean Canvas (`STR-16`), the Value Proposition Canvas (`STR-17`), the SWOT evidence-to-action review (`STR-18`) and the Blue Ocean ERRC grid (`STR-13`, offered but not draftable); each is a structure and an evidence audit, not a score. The marketing plan (`MKT-02`, STP and the marketing mix) is **not** on this shelf: it belongs to the marketing shelf, where it is offered (B-196).
- The shelf's tool groups, period badges, study notes, glossary and the student guide are **presentation and teaching material**. They do not choose the tool for you, validate a declared share or volume, or turn an assumption into evidence.

## Added with the venture-planning lane (B-108, B-109)
- The **canvas and marketing-plan worksheets are T4**: they place the evidence you supply, reproduce it verbatim and report the empty blocks. They do not check that a customer segment exists, that a value proposition is attractive, that a claimed link holds, or that the plan will work. No score, ranking or recommendation is produced.
- `sales_projection` holds price, unit variable cost and period fixed cost **constant** and grows only the volume at one declared rate. It is a projection from your assumptions, not a fitted forecast; no seasonality, step cost, capacity limit, multi-product mix, tax or financing is modelled.
- `cap_table_round` models **one priced round** with ordinary shares. It does not model convertible notes, SAFEs, bridges, multiple rounds, liquidation preferences, anti-dilution, vesting, pro-rata rights, board seats or any other negotiated clause. The option pool is post-money; the pre-money pool shuffle is a different convention and is not applied. The valuation is an input.
- `sales_funnel` is arithmetic on the stage counts you declare. It does not choose the stages, estimate conversion, split by channel or cohort, attribute a sale, or test significance. A count that rises blocks rather than being smoothed.
- `cohort_retention` pools cohorts and weights each by its starting size. Every cohort must be observed for the same number of periods; a period not yet reached must be omitted, not zero-filled. No survival model, reactivation, seasonality, revenue weighting or significance test.
- `demand_curve` fits a straight line to your price-quantity pairs. It is an **association**, not an identified demand curve: omitted variables, simultaneity and measurement error are not addressed, and the revenue-maximising price exists only when the fitted slope is negative and only within the observed range.
- `purchase_intent` applies **declared weights** to stated intent. The weights are conventions, not estimates; stated intent overstates purchase; sampling error, non-response and representativeness are not modelled.

## Added with the accounting and operations shelves (B-114, B-115)
- `standard_cost_variances` is single-product, single-process standard costing on the standards you declare. It does not set standards, compute mix/yield/sales/planning variances, handle several products or post journal entries.
- `inventory_policy` assumes level annual demand, a constant lead time and constant ordering and holding costs. No quantity discounts, stock-out cost, variable lead time, multi-item constraint or budget cap. Safety stock uses a normal approximation and needs a declared service level and demand SD.
- `queue_analysis` is **M/M/c** with identical servers, exponential arrivals and service, unlimited waiting room, no priorities or abandonment. At or above servers x service rate the method blocks. It is not a schedule or a simulation.
- `capacity_analysis` is steady-state capacity with no breaks, changeover, maintenance or scrap, one product and a fixed routing. It is not a schedule or a simulation.
- The accounting and operations **groups, notes, glossaries and guides are presentation and teaching material**; they do not validate a policy, choose an account or judge a standard.

## Added with scheduling, quality and costing (B-118)
- `cpm_schedule` uses deterministic durations (or the PERT expected value) and an acyclic declared graph. It does not itself level resources, crash or apply a calendar; use `resource_leveling`, `project_crashing` or `calendar_schedule`. The critical path is the zero-float path, not the riskiest one.
- `resource_leveling` is a greedy serial schedule: one resource per activity, whole-period durations and demands, a fixed priority rule, and no calendars, preemption or resource smoothing.
- `project_crashing` is greedy and assumes a linear crash cost between the normal and crash durations. It is not an LP optimum, and shared or non-linear costs, quality trade-offs and resource limits are not modelled.
- `calendar_schedule` uses one declared list of working period numbers; it does not infer weekends, holidays or shifts, and float is measured in calendar periods.
- `multi_project_schedule` sequences projects by a declared priority, then early start, duration and id. It is greedy, not an optimal multi-project plan; it has no inter-project dependencies, calendars, preemption or multiple resources per activity, and a project's delay is measured against its own CPM.
- `schedule_risk` is a seeded Monte Carlo over independent triangular durations. Percentiles move with the seed and are not a guarantee; it has no resource limits, calendars, correlation or distribution fitting, and criticality is the share of runs with zero float, not a causal measure.
- `decision_tree` rolls back only the tree, probabilities and terminal values the student declares. Expected value ignores risk aversion; the loss probability and range are shown beside it, and no branch is pruned or recommended beyond the highest expected value.
- `real_option` is a Cox-Ross-Rubinstein lattice with a declared volatility, rate, horizon and step count. It is not a traded option: there is no market price, continuous hedging or volatility calibration, and more steps change the value slightly.
- `multi_criteria` multiplies the student's weights and scores on one common scale. A cost criterion must be scored as desirability; weights must sum to one, and the weighted total is a declared judgement, not a fact or a sensitivity analysis.
- `monte_carlo` supports two declared models only: NPV of cash flows and profit from price, variable cost and volume. Inputs are independent fixed, uniform or triangular draws; there is no arbitrary formula, correlation, fitted distribution, sensitivity analysis or guarantee, and the seed is part of the result.
- `earned_value` takes the three cumulative figures as at one declared status date. One EAC convention at a time; no earned schedule, forecast range, quality or scope performance.
- `oee_analysis` is one machine or line: no six-big-losses split, TEEP or multi-machine aggregation. Performance above one is reported, not capped.
- `process_control` is an **I-MR chart only**: no X-bar/R, p, c or u charts, EWMA, CUSUM, multivariate charts or measurement-system analysis. Cp/Cpk use the within-series sigma and the declared specification; no capability threshold is applied.
- `abc_costing` allocates every pool in full over the declared drivers; no idle/unused-capacity adjustment, activity hierarchy or time-driven ABC.
- `sales_variances` values mix and yield at budgeted prices with the budget mix as the standard. No market-size or market-share variance, and no explanation of why the movements occurred.

## Added with the operations frameworks (SIPOC and value stream map)
- The two worksheets **organise what you state and what is researched for you**. They observe no process, time no step, measure no capacity and read no machine. A cycle time in the paper is a time you declared, carried with the provenance that shows it is yours.
- Completion takes the steps, outputs and customers **verbatim** from your own brief: it never paraphrases, infers a step you did not write or guesses a process you did not name. A part with no matching sentence and no evidence is a named gap.
- The **supplier** and **input** parts are researched in the academic databases. A search that finds nothing returns a named gap and a probe; it never substitutes a nearby finding for the missing one.
- The **value-added judgement** and the **improvement proposals** are yours by design. The worksheet states what each needs and stays empty until you give it; no pipeline may judge which of your steps a customer pays for, because that is a claim about your customer.
- A **process** is never detected. Without the process you name in the unit field, completion refuses rather than inferring one from the brief.
- The paper computes nothing. A figure that needs arithmetic — capacity, utilisation, waiting time, OEE, takt, a saving — belongs to the matching operations tile, which is the only place a number is calculated.
- The **Theory of Constraints**, **A3**, **SCOR**, **5S**, **root cause**, **FMEA**, **Kraljic**, **S&OP** and **PDCA** worksheets complete themselves the same way as the SIPOC: a block is researched first, then taken from your own words, then left as a named gap. The research is evidence *about* the declared process or its industry, cited; it never measures your line.
- **No aggregate judgement is derived by any of them.** FMEA computes no risk priority number and ranks no mode; Kraljic computes no spend and recommends no strategy; 5S scores nothing; S&OP does not balance the plans; root cause does not declare a cause; PDCA and A3 compute no improvement. Each records the labels and decisions you supply.
- An **A3 countermeasure, owner, date or follow-up** that the brief does not state is a named gap. The pipeline proposes none of them, because a remedy aimed at a cause nobody evidenced is a guess dressed as a method.
- **A part may borrow your sentence only on a declared vocabulary** (B-201, session 8). Each of the eleven operations profiles declares, per part, the words that make a sentence *about that part* (`quote_cues`); the retrieval vocabulary is wider and is not used for borrowing. A brief that only mentions cost, quality or flow therefore fills nothing, and says what to state instead.
- **Every operations paper now carries its grid** (B-202, session 8). The eleven layouts in `matrix.LAYOUTS` place the block's own label and the items already accepted (or the gap already named); a figure adds no number, no evidence and no judgement of its own.
- **The eleven operations worksheets are grouped into three tiles** (B-206, session 8): "Process and capacity", "Inventory and planning" and "Quality and evidence", each holding the worksheets, the calculators and the records of one question. The tile names are the shelf's own tool groups, so a calculator and the worksheet that frames the same question sit together.
- **One sentence of your brief can fill two adjacent parts** (G-ops-03, session 8): a SIPOC process sentence that names the customer is quoted under both Process and Customers, because it describes both. The paper labels every quoted cell as your own words and never presents it as a finding.

## Needed by some students but deliberately not built (B-120)
These are not oversights and they are not approximations waiting to be shipped. Each would need a convention the app does not have the right to invent, or is infrastructure rather than a calculation.

- **A jurisdiction tax engine.** `tax_declared` applies the rates and taxable income you declare. It does not implement any country's credits, exemptions, thresholds, progressive bands, NOLCO, withholding, filing or penalties. A student in a taxation course must use the statute and their instructor's worked format.
- **Audit opinion and audit sampling.** An opinion is judgment. The only arithmetic part is sampling and materiality, which needs a declared confidence, reliability factor and evaluation convention; a generic version would teach a defensible-looking wrong answer. Not built.
- **Group consolidation.** A consolidated statement needs a declared policy: full goodwill versus proportionate goodwill, NCI at fair value versus proportionate share, and the treatment of intra-group balances and fair-value adjustments. Not built until that policy is declared.
- **Multi-echelon inventory.** Sizing safety stock across two or more stocking points needs a declared model (guaranteed-service or Clark–Scarf). The single-location EOQ must not be applied to a network as if it were the answer.
- **A shared session store for multi-instance serving.** Sessions are in memory by design. A durable shared store is feasible, but it is a serving decision with confirmation semantics to preserve, not a computation a student runs.

If an assignment needs one of these, say so in the limitations and show the method you used by hand. That is the same rule the shelf applies to itself.

## Business-plan profile (B-148)
- The plan is **composed from declared drivers, not forecast**. `proforma_statements` projects whatever revenue, margin, costs, depreciation, interest and principal (or the declared opening loan) tax and working-capital days you declare; it has no demand model, seasonality, ramp, multi-product mix, new borrowing beyond that opening loan, dividend, deferred-tax balance or disposal.
- The projected statements use **annual periods and one currency**. A monthly plan needs its own declared lists and days basis; the method does not convert them.
- **The opening balance sheet must balance.** An unbalanced opening is refused with the equity that would balance it; the system never plugs a difference. Every projected period is checked as an identity.
- `depreciation_schedule` is an **accounting allocation**, not a tax depreciation rule. It has no mid-year convention, revaluation, impairment, disposal or component accounting.
- `sales_from_market` multiplies two declarations (market size and share) by a declared price. It does not estimate the market, validate the share or prove that customers will buy.
- `sensitivity_table` changes price and volume only; unit cost and fixed cost stay at the base case. It is arithmetic, not a probability or a recommendation.
- The **cap table** is one priced round; it does not model convertible notes, SAFEs, multiple rounds, vesting or liquidation preferences.
- The **cost-effectiveness ratio** compares declared options on one declared effect measure; it is not a recommendation and has no threshold.
- The **market analysis** retrieves four dimensions and names a gap when no source matches. Retrieval quality and coverage are the source finder's limits; the plan does not fill a gap.
- The strict convention keeps every standard section; open composition may leave an optional section out but changes **no fact and no figure**, and the same export gate applies to both.
- **A marking guide the student attaches is followed by the plan too** (B-193). The paper carries a `Rubric coverage` table before its references, the coverage is measured on the paper before that table exists, and a criterion the guide **weights** and the plan does not address blocks the download and is named in `missing`. Nothing writes the missing section: the student writes it, or accepts the gap (the gate is theirs to turn off, and the decision is recorded). A criterion naming a section this profile does not carry stays a named gap — the plan never grows a heading to satisfy a rubric.
- **A dataset proposes a plan block's list columns, never its drivers** (D-ENT-02). `POST /api/intake/{id}/map` maps the columns a stored table holds and names every input still to be typed in `not_mapped`; a scalar asked to come from a column is still refused in the core's words, and nothing is executed. No plan form offers the picker yet (G-ent-05): the Calculator form is where a mapping is consumed today.

## Deferred areas
- Taxation (B-052): out of scope — the pipeline can hold tax balances (accounts + declared entries) but computes no VAT/GST, income tax, deferred tax, capital allowances or tax-aware appraisal, and does not file. Deferred by the owner; see `docs/DECISIONS.md` B-052 for the resume conditions.

## Added with the computation explainer (B-153)
- **The explainer formats, it does not derive.** It quotes the recorded inputs and outputs, the committed method contract and the catalogue's formula/steps notes. It never performs arithmetic, re-rounds a figure or asks a model to write the explanation.
- **Ten statistics tools have no catalogue formula/steps note** - factorial, Kruskal-Wallis, logistic regression, Mann-Whitney, multiple comparison, one-sample t, paired t, post-hoc, Spearman and weighted summary. Their companion names the gap and shows the contract and recorded results; it does not improvise the derivation. Writing the notes removes a tool from explain.NOTES_GAPS.
- **A companion is produced only when the paper carries a delivered computation.** A framework-only paper keeps the plain single-file download. A selected but refused or incomplete computation is blocked by the export gate, so no partial ZIP exists.
- **PDF is print-to-PDF, not a server renderer.** The companion is .docx by default and print-ready .html when the paper is HTML; the browser prints the HTML to PDF. There is no stdlib PDF writer.
- **The companion is not the assignment.** It is a study and defence aid; the paper remains the submitted record. It carries no new source, citation, recommendation or number.

## Added with the Portfolio Lab (B-154)
- **The instrument list is a fixed reference, not a market feed or advice** (B-178). Twenty widely held long-only US listings are described in one neutral line each with a source link; the list is not ranked, carries no expected return, rating or target price, and a listing on it is not a recommendation. It is not a complete market and it is not a screener; a symbol the student already knows can be typed in.
- **The guide is a decision aid** (B-178). It explains how to choose (mandate, mix, fit, reason, snapshot) and states its own limits; it does not tell the student what to buy.
- **Example books are examples** (B-178). Three compositions (diversified, balanced, concentrated) load editable rows into the import box; nothing is saved until the student imports, and the concentrated book deliberately breaches the default position limit so the limit is visible.
- **A reason is student-authored** (B-178). The *Why you hold it* field is free text stored with the holding; the app never generates or grades it, and the report prints "(not recorded)" when it is missing.
- **No instrument data is verified here** (B-178). A listing's description is a fixed product note, not a verified profile; fundamentals and filings come from the retrieved-source panel and are labelled not independently verified.
- **Fund mode is a journal, not a trading system.** A fund records weekly snapshots, a student note,
  the external flow and an optional benchmark level, and computes a time-weighted return from the
  dated snapshots. There is no order execution, broker connection or team authentication; the
  roster is a recorded label, not a login.
- **The flow is modelled at the start of its period.** The return is (end NAV - start NAV - flow) /
  (start NAV + flow); a contribution spread through the week or made at its end is not represented.
- **A benchmark is reported only when every period declares both levels.** A partial benchmark is a
  named gap, not a filled number.
- **Prices are declared; fetching is optional and explicit.** Manual entry and paste/CSV import remain the
  default. The **Fetch prices** button tries Alpha Vantage (primary, 25/day), then Massive
  (5/minute), then a declared QVeris capability (credits per call). Each provider has an internal
  ceiling; a reached ceiling or vendor limit skips to the next, and every attempt is named. The
  ceilings are held in memory, so restarting the server resets them; the vendor still enforces its
  real quota. QVeris needs an explicit tool id, parameter name and price path, so it is skipped
  until that contract is declared. Keys may live in the gitignored `state/market_keys.json`; an
  environment variable always wins, and that local file is the only place they are stored. When every provider is exhausted the fetch returns 429 and the
  UI points to manual entry or paste; a partial fetch stores only what succeeded. The frozen core
  has no network access: it values the stored prices only.
- **Import is all-or-nothing.** A pasted table is validated row by row before it is written; one bad row
  refuses the whole paste and names its line. A header row is recognised by its label (Symbol, Ticker,
  Shares, Price, ...), so a data row with a mistaken value is refused rather than skipped.
- **One base currency, no FX.** Every price and the cash balance must already be in the portfolio's base
  currency; the valuation does not convert. A holding quoted elsewhere is entered after conversion, and
  the snapshot records that convention.
- **Long-only cash plus equities/ETFs.** Short positions, margin, derivatives, fees, tax, dividends and
  corporate actions are not represented; NAV is a valuation, not a sale price.
- **No forecast, target price or recommendation.** The method reports weights and concentration from the
  declared book. It does not rank holdings, score them or suggest a trade; the student authors the
  decision and the rationale.
- **The report is a formatter.** The DOCX reads the stored snapshot; it performs no arithmetic and adds
  no figure that is not in the snapshot. Edits to a holding or price after a snapshot do not change that
  snapshot; a new date creates a new one.
- **Deletion is permanent.** There is no undo or trash for a portfolio; the store removes the directory.

## Added with pricing and PayPal (B-163)
- **Live checkout needs an HTTPS origin.** PayPal's live JS SDK generally refuses to render on
  `http://127.0.0.1:8000`. The code does not depend on the origin; a tunnel (or any HTTPS host) is
  enough. The pricing page says so instead of showing a button that cannot work. The owner confirmed
  on 2026-11-03 that the workbench runs over HTTPS on a VPS, so this origin now exists.
- **No webhook.** PayPal cannot reach a machine at 127.0.0.1, so a renewal, a failed payment or a
  cancellation made inside PayPal is not pushed to this server. Activation is verified against
  PayPal at approval, `GET /api/billing/status` is a read of the local ledger, and a subscription
  changed elsewhere shows as stale until it is re-read. A hosted deployment needs a webhook and its
  signature verification; neither is built.
- **Credit allowances are unset.** Every tier's `credits` is `null` and the page says "to be
  confirmed". `billing.grant_for()` is the wired hook and appends nothing until an allowance exists;
  no export balance is affected by a subscription today. **The Business Bundle is the one exception**
  (B-208): it grants no limit at all rather than a number, so the export wallet stops blocking for
  it. A tier whose allowance is still undecided keeps its meter - undecided is not free.
- **Cancelling is immediate at PayPal and local thereafter.** PayPal stops billing at once and this
  machine keeps the plan and its recorded period, so the paid period is not cut short. There is no
  proration, refund or dunning logic.
- **The subscription is per machine, not per person.** There is still no identity: the ledger records
  the payer e-mail PayPal reports for reference, and the "current plan" is whatever this machine
  last activated. **The shared login that changes this is not built** (B-208 promises it; B-209
  records it as the amendment to D1).
- **The secret is only as safe as the file.** `PAYPAL_CLIENT_SECRET` sits in `Backend/.env`, which
  git ignores; it is never returned by an API, logged or printed, but it is readable by anyone who
  can read that file on this machine.

## Added with the Business Bundle (B-208, B-209)
- **The bundle has never taken a real payment.** The code is built and unit-tested, but the live
  $99.99 charge - the first real charge this product has taken - has not happened. Every claim
  about PayPal's behaviour in the bundle path (the proration arithmetic, the vault handoff, the
  switch-off) is therefore **verified against fixtures, not against the live merchant account**.
  `docs/BUNDLE_PRICING_HANDOFF.md` §6 lists the seven checks that must be proved.
- **The one-charge rule depends on three settings the owner must supply.** `BP_WRITE_SMARTER_URL`,
  `BP_BUNDLE_HANDOFF_SECRET` (the same value on both products) and `PAYPAL_PLAN_ID_BUNDLE_RECORD`
  (a **$0** PayPal plan on the Write Smarter side). Until they exist the hand-off fails closed with
  a named reason; it never creates a record that could bill.
- **A failed hand-off leaves half a bundle, and says so.** The customer paid and the subscription is
  ACTIVE, so the local grant stands and the payment is never treated as failed. But the other
  product is not granted, so the reply and the account page report the hand-off's failure with its
  reason. The bundle is **half granted** until it is retried; nothing retries on its own, because
  PayPal cannot reach the server.
- **The bundle is granted per purchase, not per account, until the login exists.** The entitlement
  is keyed on the customer's e-mail address, so a customer who buys under one address and signs in
  under another would not be recognised. The shared login (I4) is what fixes this.
- **The lower rungs are not built.** The $18.99 / $35.99 / $59.99 rungs, the per-tier allowances
  and the per-cycle credit refill are all deferred by the owner (B-180a, B-180b). Nothing about them
  is estimated or shown.
- **The bundle's price is declared, not a discount.** "Unlimited Write Smarter + unlimited Smart
  Business Writer" has no published sum to take 20% off, so the card carries no "% off" and no
  "save $" line against a made-up total. Only the annual price ($959.90, derived as twelve months
  less 20%) is a saving, against the monthly price actually published.
- **The Write Smarter side's record is a mirror, not a subscription.** It exists so that product can
  watch the purchase, and it is switched off at PayPal and kept on a $0 plan. Its status is never
  what decides whether the customer has paid - the **real** subscription id is.

## Added with the portfolio screening lab (B-184)
- **The shortlist ranks sourced values; it does not recommend.** Criteria are declared (one-day
  return; recorded mean, volatility and Sharpe; price; market cap; P/E; ROE) and every metric a
  provider cannot supply is a named gap; the panel says "sourced, not a recommendation" and carries
  no expected return, rating or target price.
- **History is the student's own record, or seeded daily bars.** Mean, volatility, Sharpe and
  momentum exist only after at least three recorded returns; **Seed** fills up to 30 days from
  Massive daily bars and stores each bar with its provider, date and response hash. A provider
  failure is a gap, never a guess, and a seeded series is still the provider's history, not the
  student's decisions.
- **Derived fundamentals are arithmetic on sourced inputs, not verified profiles.** P/E = Massive
  market cap / SEC net income and ROE = SEC net income / SEC equity; a small equity base (buybacks)
  can make ROE look extreme, and non-US registrants keep both as gaps. The row is labelled derived
  and keeps its source URLs and response hash.
- **Prefill only fills the calculator.** It never runs a method: the student opens the Business
  Calculator with the fields filled and presses =, and the normal create-then-confirm path is
  unchanged.
- **The quote providers need institutional keys.** Alpha Vantage and Massive keys are configured
  server-side in `Backend/.env`; without a key the lookup fails closed with the variable to set and
  the shortlist shows the gap instead of a price.
- **The lab lives in the Portfolio Lab**, not on the Finance page (one home for the UI; the market
  data panels remain split per B-177).

## Added with the statements tile (B-204)
- A trial balance is read by a declared grammar and a ~19-rule account vocabulary. A label outside it
  is named in the working and left out, never guessed; but a genuinely novel name that the vocabulary
  places on the wrong line is a misclassification the checks cannot catch, because both placements
  balance.
- A transaction list still needs the model reader. With no BP_OPENGO_API_KEY the tile solves a trial
  balance only, and says so in the refusal instead of half-reading the problem.
- The cash-flow statement is **withheld** for a trial-balance problem and for an incomplete record, with
  the reason printed: one period-entry trial balance yields a statement that is internally consistent
  and false. It is presented for a transaction list, where the flows are declared.
- Intangible-asset amortisation is not modelled: schedules.amortization is a loan amortisation.
  Consolidated statements, suspense accounts and error correction are out of scope (phase 2).
- Ratios cover the core's 15 plus DuPont 3-step and 5-step. Market, cash-flow, quality/forensic and
  growth ratios are named with the input they need, never estimated.
- The export is plain text: a DOCX wrapper is not wired yet. Single entity only; no comparative period,
  segment or multi-currency analysis. A second set of balances, a second period, a comparative column or
  a consolidation mention is **refused by name with the reason** (B-212), not merged and not crashed on.

## Added with the figure layer (B-220)
- **A chart reaches a Word paper only when a rasterizer is installed.** `plotly` with `kaleido` draws a chart
  and returns its PNG; the headless Chrome that kaleido carries rasterizes the builtin SVG (diagrams, Gantt,
  table). `cairosvg` needs a native cairo DLL that is not on every machine, so it is tried first and skipped
  when absent. With no rasterizer at all the figure prints its stored values as a table under its caption:
  never a broken image, and never a figure that silently disappears.
- **Plotly, Mermaid and Graphviz are optional and never required at runtime.** The builtin
  standard-library SVG renderer always runs; the professional engines are used when present and fall
  back to it when absent, so a missing package costs polish, not the document.
- **The builtin chart look is still the old frame.** The Plotly template and the shared theme tokens
  are not built yet, so a Plotly chart carries the restrained inline layout in `renderers.py`, not the
  full design system.
- **Auto-placement is by section heading.** A figure names its section; a figure whose section the paper
  does not carry is reported as unplaced, never dropped into an arbitrary heading.
- **A stale figure is detectable, not yet blocked.** `figures.stale()` compares the record's digest with
  the stored values, but no export gate refuses a stale figure yet.
- **A chart reaches a spreadsheet two ways, and the native one needs numbers.** A bar, line, stacked bar,
  pie or pareto figure is written as **cells plus a `<c:chart>` part**: the labels and values sit on the
  sheet above a `xdr:graphicFrame`, the chart caches the record's own strings and references those cells,
  so Excel redraws it and a reader can check every figure in the cells. A waterfall, an area, a scatter,
  a candlestick, a gantt and a table keep their anchored picture, because there is no faithful native
  shape for them; a figure whose values are not all numbers also keeps its picture. A picture is only
  carried when a rasterizer produced the PNG.
- **A pareto is drawn from two stored series.** Each entry names its bar artifact and its running-total
  artifact; the drawing checks that the running total never falls, and scales the line to its own stored
  maximum. It never sums the bars to make the curve, so a pareto the record does not hold cannot appear.
- **A work breakdown is labels and codes.** A code may carry digits (`1.1.2`); a label may not, five levels
  is the limit, and the drawing places leaves across the page with parents centred over their children.
  A breakdown with more leaves than fit is drawn small rather than paginated.
- **A figure sheet is one Word page per visual, in the order given.** `visuals.export_sheet` exports as
  DOCX only; a PDF or a workbook sheet of several visuals is not built.
- **A deck carries speaker notes and one transition.** `deck.py` writes title, claim, figure, section and
  table slides with one theme, `notesSlide` parts for the speaker notes and a fade by default. A figure
  reaches a slide as a picture, or as its stored values when no rasterizer is installed.

## Added with the visual store (B-228)
- **A visual has its own store.** `state/visuals/` holds one JSON record per visual; a case is not
  required, and a visual is never merged into a case's artifacts.
- **A declared series is student data, not evidence.** It is labelled "Figures you declared" on the
  figure and in the record, and it never enters a case's artifact table.
- **The chart is proposed, not chosen by a model.** `visuals.propose()` ranks at most three kinds
  from the data shape and the student's words; the student confirms the kind.
- **A table has no SVG.** `visuals.export(..., "svg")` refuses a table and names the formats that work.
- **A PNG or PDF needs a rasterizer or Chrome.** Without one the export is refused with the reason,
  never an empty file.

## Added with the chart reader (B-250)
- **The reader does not guess a decimal separator.** A single three-digit
  separator is read as thousands (`1,200` -> 1200, `1.200` -> 1200) and shown as
  parsed. Write `1.2` when you mean one point two.
- **A bare number gets an `Item N` label.** The label is marked "auto" and is
  editable; the reader does not pretend it came from the student.
- **A pareto is never summed.** It needs a supplied running total on every line;
  a missing or falling running total is refused. This keeps B-248.
- **A PDF table may flatten.** DOCX tables are read structurally; a PDF whose
  labels and values are on separate lines is refused rather than guessed.
- **A scanned PDF needs a text layer or OCR.** Without one the reader refuses
  with the reader's reason.
- **An instruction file with no figures is refused.** The reader will not invent
  a table from prose.
- **An XLSX upload reads the first sheet.** The report names the sheet it used.
  If the data is on another sheet, save that sheet as a separate workbook or CSV.
- **The reader caps at 200 points.** A larger input is cut at the cap and the
  warning says so; the rest is not silently charted.
- **The public Cloudflare Pages copy is static.** The read/build routes run on
  the local workbench server; the published site has no backend, so the Chart
  window's upload and create actions work where the existing visuals API works.
- **A framework diagram carries words, not numbers.** The existing T4 rule
  still applies: write "Marketing mix", not "4Ps". A label with a digit is
  refused with that hint.
- **A Gantt timeline uses day numbers or ISO dates for every task.** Mixing the
  two forms is refused. The date text is a stored display artifact; the bars
  use day offsets, so the x-axis is numbered from the earliest start.
- **A scatter or candlestick line carries more numbers than a bar.** Typed input
  and an instruction file read `label, x, y` and `label, open, high, low, close`.
  A data-file upload still maps only label/value (and the pareto running total),
  so a scatter or candlestick from a CSV/XLSX must be typed or come from an
  instruction file. A scatter needs an x on every point; a candlestick refuses a
  high below its low or an open/close outside the high-low range.
- **An area chart reuses the line values.** It draws the same stored points as a
  line with a filled area; it does not stack several series.
- **A framework diagram is structure only.** It does not score, rank or compute;
  the subject worksheets still own the evidence and analysis.

## Added with the offline test suite
- **The suite never reaches a model.** `bp.server` maps `Backend/.env` onto `BP_LLM_PROVIDER`,
  `BP_OPENGO_API_KEY` and their siblings when those names are *absent*, so a developer machine
  handed the tests a live provider: the analysis lane drafted paragraphs no test expected, the
  proposal lane waited on HTTPS, and two runs of one template no longer produced the same bytes.
  `tests/__init__.py` (and `conftest.py` for pytest) now sets those names **empty** before any
  test module imports, and `bp.server` treats a name that is present-but-empty as "not
  configured". A test that wants a model patches `prose.available` and `prose._call`, as
  `tests/test_matrix_assist.py` does.
- **The suite therefore does not prove the model lanes against a live provider.** They are
  covered by stubs and by the provider unit tests with an injected opener; a live call is still
  the owner's first run, as `bp/llm.py` says of every provider.

## Deferred with the silent plan release (owner decision, 2026-11-09)
- **Full feasibility and project-proposal guide schemas.** The silent profiles read the labelled
  facts they are given (project, market, technical, legal, budget, beneficiaries, activities) and
  write the 13 guide sections. A project proposal with a work-plan or budget table now takes the
  work-plan route (B-254); a narrative proposal, and every feasibility table beyond the three the
  simplified route reads, keeps the guide schema, and the remaining schema is deferred, not
  silently invented.
- **Tax beyond the US effective-rate preset.** The product applies a stated rate, or 21% US
  federal corporate when none is stated, and labels the basis. Brackets, state tax, payroll tax,
  credits, losses carried forward and other jurisdictions are deferred. It is not a tax return
  and not tax advice.
- **Cited Market Analysis research.** Home does not retrieve market evidence for the plan's
  Market Analysis. The section is omitted when the brief does not support it; no uncited market
  claim is written.

These are accepted limitations for deployment, not open defects. A later lane can add each
without changing the silent Home contract.

## Added with the framework writing modules (B-251)
- **The rating is a judgment, not a measurement.** The model proposes it from the accepted items, code validates it, and the student confirms or overrides it. A rating can be wrong about the world; it cannot be unsupported by the items, because every fact or inference driver must name one.
- **The tier, recency and strength rules are product conventions.** Tier A-D, the three-year recency window and the Strong/Moderate/Weak scale are declared in the audit note. They are not claims the source makes, and an unknown database defaults to C, never A.
- **A thin run prints "not rated".** With no model, or when the model's reading is refused, the draft carries the evidence and the audit but no rating. The paper says so rather than inventing one.
- **The Diamond's outcome evidence is the model's section.** When it is empty, the audit labels the whole analysis an explanatory hypothesis; it never assumes an outcome.
- **Generic Strategies coverage depends on the model naming a value-chain area.** A driver without an area is not counted, so the coverage check can fail on an analysis that is otherwise sound; the audit says which areas it saw.

## Added with the quiet project-plan lane (B-252)
- **The record is the brief's tables.** The project plan reads a labelled charter and classified tables; it does not invent a work package, a cost, an owner, a duration, a RACI letter or a risk from prose alone. A brief with no WBS table produces a paper whose tables are missing or empty and whose `project_plan.validate` problems are named, not a guessed breakdown.
- **No web evidence is retrieved for a project plan.** The record is the source, so the paper cites nothing it fetched. A source the student declares in the brief is carried into the reference list and written in the paper's citation style (B-266), with one line saying it was declared and not verified; a brief that declares none still says "No sources were used." That is accepted for a planning document; it is not a literature review.
- **A chart is drawn only from a run that happened.** The Gantt needs the frozen schedule; the activity network needs at least one declared dependency; the resource-load histogram needs a successful levelling; the planned-completion curve needs stored finishes. If a run did not happen, or Plotly/kaleido is absent so the PNG cannot be drawn, the paper keeps its table and simply carries no chart. The four figures were added in B-264; the deck is an export of the paper and was added in B-253.
- **Periods become dates only through a declared calendar.** The schedule's early/late values and the critical path are in the declared duration unit. The dated schedule converts them to ISO dates only when the charter declares an ISO start date and only on a Monday-to-Friday calendar: one period is one working day, weekends are a gap, and no holiday, shutdown or time zone is inferred (B-262).
- **Levelling is greedy and needs a declared demand.** It runs only when every activity declares a whole demand and every assigned resource declares a positive whole capacity; a missing or over-capacity demand is named, never defaulted to one. It is the frozen serial method, not an optimiser, and capacities stay per resource while the histogram sums demand (B-263).
- **A revision preserves the recorded tables; it cannot add one.** `_rebuild_outline` reattaches each section's stored figure and strips model-echoed table rows. A table the record did not carry stays absent, and a change to scope must follow the plan's change-control route.

## Added with the project deck and the three-table feasibility study (B-253)
- **The project plan and the three-table feasibility study each get a dedicated deck.** The project deck has a title slide, the summary claim, the Schedule chart, a figure slide each for the network, the completion curve and the load histogram, and one table slide per recorded table, including the dated and levelled schedules when they ran; the feasibility deck has a title slide, the summary claim and the market, cost and returns tables. A plan that did not level or date simply has fewer slides rather than an empty one, and every deck uses only a fade; speaker notes carry the section prose. Other papers use the generic `deck.from_paper` path, which reorders the paper's own sentences and includes only figures the registry holds. A deck is an export, never a second paper.
- **The simplified feasibility study is break-even, not a full appraisal.** It computes the expected revenue, break-even volume and revenue, contribution margin and margin of safety from the declared demand, price, fixed cost and variable cost. It does not build projected statements, sensitivity tables, payback, NPV or tax; the full guide route still exists for a narrative brief and its own blocks.
- **The market table uses the declared demand as the expected volume.** No market share is inferred and no market is forecast; the paper says so. A brief that states only a market size in currency, or only a share, is a guide-route brief or a named gap, not a three-table one.
- **A subject door names its profile once.** If the student opens Home directly, the lane is chosen by the brief's own words or its WBS/table shape; a completely unlabelled narrative with no tables is not guessed into the project or feasibility lane.
- **A project title falls back to the brief's first line.** The fallback is used only when no label states a title, the line has no colon, is at most 90 characters and is not a table header; otherwise the title stays missing and is named.

## Added with the work-plan project proposal (B-254)
- **The proposal's record is its labels and its tables.** `proposal_reader.py` reads the named facts (title, problem, objectives, location, proponents, timeline, funding source, income indicators, baseline, targets) and classifies the work plan, budget and risk tables. A missing objective, activity, owner or cost is named by `proposal_plan.validate`, never filled from prose.
- **The budget total is the sum of the declared lines.** It is not a break-even, an appraisal or a forecast; the paper says the total is the declared lines. The proposal runs no core computation block and no research round, because the record is the source, so its References section says "No sources were used."
- **A narrative proposal keeps the guide route.** Only a brief with a work-plan table or a budget table takes the silent work-plan route; the full 13-section proposal schema remains the guide path. A risk's response or owner that the brief does not state stays blank in the register.
- **The download holds the paper, its workbook, its deck and the PDF.** The workbook is Overview, Work plan, Budget and Risks; the deck is the same paper's six slides and was added in B-264. The proposal still runs no core computation and no research round.

## Added with the dated schedule, the levelled schedule and the four project figures (B-262 to B-264)
- **A demand column is a declared fact, and a blank one is missing.** The reader accepts `Demand`, `Load`, `People`, `Quantity` or `Units needed` as the activity's demand. A blank cell is not zero: levelling refuses and names the activity rather than assuming one unit.
- **The core's resource-name rule is a boundary, not a paper rule.** `resource_leveling` refuses a name with a space, so the product sends `R1…` codes and keeps the brief's own names on the page. Levelling's delay and peaks are the core's stored values; the paper does not recompute them.
- **The dated calendar is weekdays from a declared start, nothing more.** One period is one working day; a Saturday or Sunday is a gap. Public holidays, shutdowns, shifts, part-time calendars and time zones are not modelled, and a plan with no ISO start date keeps its period schedule and says so.
- **The completion curve is progress, not cost.** It plots the cumulative per cent of activities finished by each period, from the stored finishes. It is not an earned-value curve, carries no budget weighting, and says so in its own note. A plan with no stored finishes has no curve.
- **The load histogram sums declared demand, and capacities stay per resource.** Summing demand across resources is a view of the levelled schedule, not a claim that one team does all the work; the paper prints capacities per resource beside it.
- **The network is activity-on-node, not activity-on-arrow.** Boxes sit in dependency layers and arrows follow the record's own predecessor edges. It draws no dummy activity, no event numbering and no duration on the arrow, so it is a dependency picture, not the AOA network a PERT textbook may show.
- **One figure per section.** The four figures occupy their own level-2 blocks, and the browser pane shows none of them; Word, the PDF and the deck carry all four.
- **A figure is drawn by one engine, and the picture is checked.** The kinds the builtin renderer owns (the Gantt, the network, the table) are never handed to Plotly, because a spec Plotly does not know is drawn as an empty axis with a title on it. The headless window is taller than the drawing it takes, so the drawing is asked for in a window with headroom and the surplus rows are cut off afterwards; a picture the crop cannot read is shipped unchanged rather than broken.
- **The citation style is read from the brief in the quiet lanes.** A student who writes "in Harvard style" in the brief gets a Harvard paper; a student who says nothing gets APA. The guide route's style select overrides the brief. A style the product cannot render is ignored, so the paper falls back to APA rather than pretending (B-267).
- **A dense chart prints no value on every point.** A chart with more than twelve points shows the shape, not a number on each bar or point; the numbers are in the table beside it and in the workbook. The completion curve carries one point per finishing period, which is the shape the finishes make.



## Added with the portfolio, growth and canvas modules (B-252)
- **GE-McKinsey's factor table is not parsed from a brief yet.** The adapter accepts structured axes (factor, weight, score per unit); when the brief holds only a portfolio table, the paper names the missing factor table rather than inventing scores.
- **The GE sensitivity test is stated, not computed.** The guideline asks how the zone changes when the top weights move; the module names the test but the first build does not run the second weighted pass.
- **BCG accepts a share-only table.** When revenue and market size are absent, the adapter passes the declared own share and competitor share to `market_share` (the method only needs the ratio). A table with revenue and market size is preferred and gives the same relative share.
- **An H test is model-proposed.** The register prints the test, the success criterion and the confidence; it does not run the experiment.
- **The canvas consistency checks are model prose.** The paper prints them, but there is no deterministic link checker that proves every segment has a revenue stream; that is the next refinement.

## Added with the quality modules and framework charts (B-255)
- **RPN and Five-S scores now come from the frozen core** (`fmea_rpn`, `five_s_score`), and `quality_reader` reads the brief's FMEA/5S/PDCA tables. PDCA measures are read but not yet charted from a pasted table, and a renamed Five-S category is a named gap rather than a guessed match.
- **The FMEA worksheet, Five-S scorecard, PDCA cycle log and RCA verification table are model-supplied.** `clean_tables` checks their shape and the paper scans them for template text; a deterministic reader for those tables is the next refinement.
- **The chart values in a model-supplied chart are shape-checked, not traced number by number.** The BCG and GE charts are safe because they plot the core's calculation rows; a model chart is refused when its shape is impossible, and the audit remains the place to challenge a value.
- **The RCA chart is a tree of the key why-chain, not a full fishbone.** The pipeline has a tree diagram and a matrix, but no fishbone kind; a fishbone layout is a renderer addition, not a data change.

## Added with the Relevance Research Agent (B-257)
- **The RRA reads what a school publishes, not what it teaches.**  A curriculum page is a
  curriculum page; it is not the teaching, the marking or the level.  The evidence records a
  url, a retrieval time, a SHA-256, a tier and a verbatim excerpt under 25 words — that is a
  citation of what the page said, and it is the most the system can honestly claim.
- **The sampling frame is a sample.**  `qa/relevance/schools.json` lists twenty-five business
  schools in the United States and Europe and the bodies to watch.  It is English-language,
  elite and Western by construction, while the product is global.  A region is recorded on
  every evidence record so the bias is visible in the data, not hidden in the design.
- **Most syllabi are not public.**  Where a school does not publish its core-course list or
  its assessment briefs, the RRA cannot find one: it does not infer the curriculum from the
  school's reputation, and a gap it cannot fill is reported as a gap.
- **The model may only propose.**  It can draft a search query, pick the passage that matters
  and draft the spec fields; the code checks every one of them.  A paraphrase in place of an
  excerpt is discarded, and a URL the search did not return is never read.  It never decides
  what a school teaches and never writes a gap spec that survives on its own.
- **Nothing is applied.**  There is no apply endpoint and no autonomous code writing.  A gap
  reaches the growth loop only through a recorded human decision, and the growth loop still
  needs a human to write the method logic and run the suite before a capability is committed.
- **A paywalled source is a pointer, not evidence.**  It is flagged and marked as such; the
  system never circumvents a paywall, and a snippet is never quoted as if the full text had
  been read.
- **The back-test measures the RRA against the owner's own list.**  Recall of 12/12 with 0
  false flags means the harness agrees with a seeded set the owner wrote; it is not proof
  against the world's curricula.  The set is a floor, not a certificate.
- **The catalogue snapshot can go stale.**  It is a read-only export of 127 capabilities, 89
  frameworks and 216 methods.  `check_drift()` says when the code has moved on; until it is
  regenerated the Mapper compares against the older snapshot.
- **The scheduled sweep is off by default.**  `BP_RELEVANCE_AUTOSTART` is 0 and
  `BP_RELEVANCE_INTERVAL` is thirty days.  The RRA runs when the owner runs it.

## Added with framework-aware research (B-258)
- **Every profile that retrieves evidence declares a research block today.** The leadership/culture/
  ethics batch completes the set: change management, logic models and theory of change route to
  people, the culture frameworks to culture, and ethical dilemma / stakeholder CSR to ethics. Four
  profiles are quote-only and have no block (ethical decision process, leader effectiveness,
  leadership development, organisational culture) because every part is the student's own. VRIO and
  the value stream map are deliberately without a block: VRIO retrieves no external evidence by
  design, and the value stream map is quote/gap only.
- **The required tiers are a product convention, not a universal rule.** PESTEL asks for an
  official or data source where the topic has one; Five Forces asks for data or research because
  industry structure is rarely published as a primary statistic; the business plan asks for
  official, data or research for market, customers and competition, and official or data for
  regulation; BCG and GE ask for data or research; the quality modules, the canvases, the people
  frameworks and the project/operations profiles require no tier because their blocks are the
  student's own. A topic whose registry has only research or press sources would surface more named
  gaps. The convention is printed in the ledger so a reader can challenge it, and it is never used
  to invent a replacement source.
- **The ledger is run-state, not plan-state.** It records what the retriever saw and why a
  candidate was refused, and it is stored on the run; it does not change the frozen plan hash
  or a citation.







## Measured limits of the Relevance Research Agent (B-259)

These were measured, not assumed.  Each one is a limit on what the RRA can
*see*, and each one makes the RRA withhold rather than over-report.

- **The search provider rate-limits.**  A full sweep — every topic against
  every school — runs into HTTP 429 and comes back with nothing.  That looks
  like a finding and is not one: the sweep would report "no framework is
  taught anywhere" from a provider that refused to answer.  The sweep now
  carries a **search budget** (`DEFAULT_SEARCH_BUDGET`, 120) and says when it
  stops.  A frame this size needs several sweeps, not one.
- **A site-restricted search returns the school's home page first** for
  almost every topic, and a home page names nothing.  The topic discovery now
  skips a URL with no content path.
- **Many course catalogues are rendered by JavaScript.**  A plain fetch sees
  only the shell — one Bocconi course page returned 248 characters where a
  browser shows the full description — so the framework the course teaches is
  not in the text the reader can see.  The reader reads **server-rendered
  text only**; a client-rendered page is a gap the RRA cannot close today.
  *Repaired in build 1.149, partly.*  The scout now reads 400,000 characters
  of the response (a 100,000-character read cut the body off, because a
  course page's header, logo and script block fill that space), the body is
  stripped to text **before** the cap, and a rendered page is kept when its
  readable text beats the fetch's — the comparison used to be against the raw
  markup, so the browser's reading was always discarded.  A plain fetch now
  finds the Business Model Canvas on the Bocconi course page that the browser
  could see.  **What is still true:** a page that only a browser can read is
  still a page the sweep may not see, because the render is bounded (12 a
  sweep) and the browser is optional.
- **A short label is not safe to text-match.**  "5S" stripped of punctuation
  is "5s", which appears by chance in almost any long page, and a two-letter
  token matches course codes.  The reader refuses a topic whose label is
  under four characters, and a short label must sit on a word boundary.
- **The 25-word excerpt is too narrow to evidence a framework.**  A
  course-catalogue page names a framework somewhere in a thousand words.  The
  reader therefore records **which topics a page names** — a derived fact,
  not a copy of the page — so the control set can see the page even when the
  excerpt misses the name.
- **The control set measures the sweep, not the world.**  Recall of 12/12 on
  the seeded set means the harness agrees with a list the owner wrote.  A
  sweep whose controls fail reports **no gaps at all**, which is the safe
  direction and also the unhelpful one: a sweep that cannot see the
  frameworks the system already has is not measuring anything, and the
  console says so in as many words.  *Measured in build 1.149:* over the
  owner's Phase 1 URL set the controls now hold at **9/12 (0.75)** and the
  measurement passes, where the same sweep held 5/12 and withheld
  everything.  BCG, ERRC and Ansoff were still not named on those pages and
  are reported as missing rather than as found.  **A curated URL list proves
  the reader can see a framework; it does not prove discovery can find one.**
  The two claims are kept apart, and `qa/relevance/curated_seed.json` says so
  in the file.

- **The search backup is slower than the search it backs up.**  The
  OpenCode leg is a headless model session with a websearch tool: it
  answers when Brave and Firecrawl both refuse, and it costs a model
  call per query.  The RRA's search budget (120 queries a sweep) is
  what keeps that bounded; a frame this size needs several sweeps.
- **The search providers answer the whole web, then the curated filter
  drops what is off-site.**  The OpenCode leg carries the site's domain
  in the prompt, but a page it returns from another host is still
  discarded, so a narrow frame narrows the answers.
- **The search chain can be down, and it is down sometimes.**  On 2026-11-10
  all three legs failed at once: Brave `HTTP 429`, Firecrawl `HTTP 429` (a
  24-hour cooldown), and the OpenCode Go gateway returned *"Unexpected server
  error"* for **any** prompt — including `Reply with exactly: PING` with no
  websearch tool — so the backup was not a fallback but a second outage.  A
  refusal is not a finding, and the sweep says which provider refused rather
  than reporting "nothing found".  The discovery stage cannot run while the
  chain is down; the curated seed lets a sweep run without it.
