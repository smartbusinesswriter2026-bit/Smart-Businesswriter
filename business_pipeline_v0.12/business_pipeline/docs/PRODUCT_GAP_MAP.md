# Product gap map (working backlog)

**Status: PROVISIONAL planning aid, not a decision.** It prioritises candidate work; nothing here is committed to build until the owner picks a direction and it becomes a B-… decision. Read it alongside `docs/DECISIONS.md` and `docs/KNOWN_LIMITATIONS.md`.

## Why this exists

The pipeline grew **method-by-method** (provider → statistics → forecasting → accounting), while the catalogue describes a **whole product** (140 records: 61 frameworks, 22 models, 50 quantitative methods, 7 theory clusters). This map is the difference between the two, ordered by leverage and risk, so gaps are addressed *before* more is built on top.

## What is already covered (baseline)

- **Model assistance** (DeepSeek/OpenAI-compatible boundary; facts/alternatives/critique under code validation), literature DOI verification, held-out evaluation scaffold.
- **Statistics**: descriptive, Pearson/Spearman, OLS + HC3 (diagnostics), Welch t-test + Mann-Whitney, one-way ANOVA + Kruskal-Wallis, chi-square; effect sizes + intervals throughout.
- **Forecasting**: linear trend with prediction intervals and an out-of-sample holdout (linear only).
- **Accounting (Stage 8)**: declarative engagement → ledger kernel → schedules (depreciation/amortization/accruals) → cash flow (two routes) → closing + retained-earnings rollforward → reconciliation → statement exports, with the account-mapping checkpoint.
- **Templates**: SWOT, Five Forces, and `case_decision` (2–5 alternatives compared by NPV).

## The four gaps, with tier/verification notes

Priorities: **P0** = gatekeeper (unblocks other work) · **P1** = high leverage, low risk · **P2** = breadth.

### A. Gatekeepers (P0)

| Gap | Why it matters | Tier / verification note |
|---|---|---|
| **Retrieval + citation layer** — standards, company filings, tax, literature | The manual makes retrieval mandatory before trusting any drifting rule ([manual §15, line 520](docs/sources/business_pipeline_v0_3.md#L520)); it unblocks framework citation, tax (B-052), the research workflow (REW), and valuation multiples | A *boundary*, not a computation: hash-audited, fail-closed, labels of `retrieved + cited` vs `declared by you (not verified)`, never a silent memory citation. The literature slice exists (B-040); the response hash/date audit is not built yet |
| **Ingestion** — PDF/scan/Excel/SPSS → structured, reusing the quote/provenance discipline | Most of the 140 catalogue items are data-hungry; the system today only eats hand-typed JSON. Manual open question ([§16, line 552](docs/sources/business_pipeline_v0_3.md#L552)) | Structured files → T1; OCR/PDF → unverified text → T2 + label + human confirm |
| **Decision dependencies** | Reviewers to promote T2→T1 (B-005), the ledger-engine choice (B-032), ratification of the living research manual (B-053, register R1–R11) | Owner decisions, not build; they gate promotion and any jurisdiction-dependent work |

### B. Statistics completion (manual 9B.2/9B.3) — P1

The manual's own growth order ([§9B.2, lines 345–359](docs/sources/business_pipeline_v0_3.md#L345)) minus what exists:

| Gap | Tier / verification note |
|---|---|
| Paired and one-sample t-tests | T1 — reuses the Welch/Mann-Whitney machinery and golden-fixture pattern |
| Factorial ANOVA, ANCOVA, repeated measures, post-hoc tests | T1 (one-way already there); post-hoc needs a declared multiple-comparison correction |
| Logistic regression | T1 — diagnostics analogous to the OLS/HC3 pair |
| Reliability (Cronbach's α) and factor analysis | T1, but factor analysis needs declared extraction/rotation defaults ([§9B.4](docs/sources/business_pipeline_v0_3.md#L377)) |
| Clustering (segmentation) | T2 initially — many algorithms, no single "right" answer; needs a labelled evaluation set |
| **Cross-cutting (9B.3)**: multiple-comparison correction, power/precision statements, missing-data mechanisms + imputation, survey weights / clustered-data detection | Upgrades to existing methods, not new ones; currently only listwise deletion and a "one test, no correction" note exist ([§9B.3, lines 369–375](docs/sources/business_pipeline_v0_3.md#L369)) |
| Time series beyond linear trend (seasonality, backtesting, break detection) | Highest stats risk — sits under the §8 regime-change controls |

### C. Finance & valuation (sits on the finished ledger) — P1

| Gap | Tier / verification note |
|---|---|
| **Financial statement ratio analysis** (liquidity, profitability, solvency, efficiency) computed from the statements | T1 — pure arithmetic on ledger/statement artifacts; the natural next step after Stage 8 |
| DCF valuation + WACC | T2 — WACC and growth are assumptions, never invented weights; grows `case_decision` |
| Unit economics (unit margin, LTV/CAC), multi-product break-even | T1/T2 |
| Cost-benefit / cost-effectiveness / SROI | T2 — valuation assumptions, expert review pending |

### D. Catalogue breadth — marketing, operations, risk, people (P2)

Most of these start as **T4 structure-only** evidence templates (organise the owner's evidence, compute nothing), promotable to T2 once the underlying quant from section C exists. The open decision on which templates come next is B-028 (PESTEL, VRIO, Value Chain, BMC, MCDA).

- **Marketing/customer**: STP, 4Ps/7Ps, Kano, RFM, cohort/churn/LTV, market sizing (TAM/SAM/SOM), pricing & demand.
- **Operations/supply chain**: EOQ + safety stock, queueing/capacity, theory of constraints, SPC/OEE, CPM/PERT, linear/integer optimization.
- **Risk/decision**: decision trees + expected value, Monte Carlo, scenario/stress, FMEA/Bow-tie, ISO 31000/COSO.
- **People/org**: Kotter, Lewin, ADKAR, 9-box, OKR/BSC — registry only today.

### E. Non-computational product gaps (manual §15B, §16)

These are requirements the manual already flags as [OPEN](docs/sources/business_pipeline_v0_3.md#L522), not methods:

- Multi-period comparatives, restated prior periods, report versioning with diffs.
- Academic-integrity / AI-use **disclosure-ready export** and a **reviewer sign-off workflow** ([line 544](docs/sources/business_pipeline_v0_3.md#L544)).
- Case workspace: retention/privacy, returning users, shared source caching ([§5.9](docs/sources/business_pipeline_v0_3.md#L185)).
- **Model version pinning + drift gate** ([line 528](docs/sources/business_pipeline_v0_3.md#L528)); security/hostile content + privacy-law review ([line 526](docs/sources/business_pipeline_v0_3.md#L526)); budgets/observability.
- **Research & Evidence Workflow (REW, formerly Stage 7)** — the living manual exists (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`, B-053) with proposed stages R0–R8, but no stage is built and R1–R11 await owner ratification; only the literature retrieval boundary (B-040) is real.

## Recommended order

1. **Ratify the living research manual (R1–R11)** — free, unblocks the REW track and turns proposals into a build spec; the alternative (original Smart Researcher manuals) is still welcome and would be reconciled against it.
2. **Retrieval + citation (P0)** — the highest-leverage single item; it unlocks tax, REW, framework citation and valuation, and is the one thing the manual treats as non-negotiable.
3. **Statement ratio analysis (P1/C)** — crisp, low-risk value on the ledger output we just finished.
4. **9B.3 honesty upgrades (P1/B)** — power, multiple-comparison, missing-data mechanisms and weights, so existing statistics stop under-reporting before more statistics are added.
5. **Ingestion (P0/A)** in parallel with the above.
6. **Breadth (P2)** only after reviewers are named (B-005) and templates are chosen (B-028), so promotion and scope decisions are made once.

## Owner asks to un-block this

- Name **expert reviewers** (B-005) — needed to promote anything T2→T1.
- Pick the **next framework templates** (B-028) for section D.
- Decide the **ledger engine** (B-032) before tax/valuation sit on the ledger for real.
- **Ratify the living research manual** R1–R11 (B-053), or supply the original Smart Researcher manuals and it will be reconciled against them.
