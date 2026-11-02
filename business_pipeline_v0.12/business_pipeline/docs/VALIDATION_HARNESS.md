# Validation harness — subject-by-subject paper validation

**Kind:** living, design-lane (B-080). **Owner of this file:** design owner.
**Status:** *proposed*. Nothing is built yet. Sections 1–3 and 5–9 are the design of record; §11 is the build order.
**Rule:** update this file when a rule changes status (§5, §6.2), when the subject crosswalk changes (§7), when an evidence pack changes (§8), when a layer ships (§11), or when the owner records a decision (§12). **Never rewrite a past change-log entry** — append to §13.
**Read with:** [`HOME.md`](HOME.md) → [`CONTRIBUTORS.md`](CONTRIBUTORS.md) → this file → [`CONDUCTOR_MANUAL.md`](CONDUCTOR_MANUAL.md).

---

## 1. The problem

The pipeline exposes a large surface and the owner is one person. Validating it today means one feature at a time: open the app, find the feature, fill it, generate the paper, open the `.docx`, and read it against the same eight rules every time.

The measured surface (2026-11-02, build 1.56, 2553 tests):

| Unit | Count | Producing path |
|---|---:|---|
| Framework-completion papers (one per profile) | 76 | `completion.complete()` → `completion.draft_bytes()` |
| Capability papers (computed sections) | 126 | `chat.run_capability()` → `chat.docx_bytes()` |
| Conductor framework papers | 9 | `chat.start()` → … → `chat.docx_bytes()` |
| Paper profiles (business plan, feasibility, FOR, marketing plan, proposal) | 5 | conductor, `profile=` |
| Compute-tool deliverables (xlsx/docx/pdf/md) | 148 | `POST /api/sessions` → confirm → `deliverables.write_export()` |

**364 distinct validation targets.** Worksheets are *entry points* onto framework profiles, not extra units: 86 subject→worksheet links resolve to 55 distinct worksheets, and every one of the 76 profiles already has a worksheet binding.

At ten minutes a target that is roughly **60 hours** of repetitive reading to re-check rules that never change.

## 2. What already exists (reuse, do not rebuild)

This is the reason the harness is cheap. Most of it is already written.

| Asset | Where | What it gives |
|---|---|---|
| Deterministic paper builder | `scripts/build_conductor_samples.py` | proves a paper can be built unattended and byte-identically twice |
| Frozen evidence fixture | `scripts/sample_evidence.py` | 9 citable records to mock retrieval with |
| Structural checks | `bp.product.paper.check`, `paper.META`, `paper.missing` | heading jumps, meta text, missing Conclusion/References, export gate |
| Recompute guard | `chat._recompute_guard` | re-runs every recorded computation from its own declared inputs |
| Claim ceiling check | `verify.overclaims` | sentences asserting more than a frozen method licenses |
| Completion gap gate | `completion.missing` | the dimensions that still block a paper |
| Reading verifier | `bp.product.verify` | exact-quote, unit and licence checks |
| Preset inputs | `src/bp/server.py` `PRESETS` (144) | **125 of 126 capabilities are seedable from an existing preset** |
| Subject index | `bp.product.subjects` | 11 subjects, their worksheets, tools and catalogue ids |
| Paper store | `bp.product.paper_store` | stores generated papers — but caps its index at 200 rows |

**The papers are already being produced.** `documents/` held **1,781 generated `.docx` papers** on 2026-11-02, produced by the test suite across 10-29 → 11-02. The production side of the harness is therefore not a new capability; it is a **new organisation** of an existing capability. Two gaps explain why the owner cannot use them today:

1. `paper_store.py:84` writes `rows[:200]`, so 1,581 generated papers have no durable index.
2. Nothing groups them by subject, and nothing judges them.

## 3. What the harness is

A command that, for one subject, produces **a complete paper for every feature in that subject**, judges each paper against a registered rule set, and writes one report the owner reads instead of 30 papers.

It is a **report**, not a gate. It never changes what the product allows a student to export.

## 4. Architecture

```
┌─ Layer 1  PRODUCE ────────────────────────────────────────────────┐
│ walk the registries → drive the REAL product path → a .docx       │
│ frozen retrieval fixtures; frozen core called through its API     │
│ out: validation_out/<subject>/<feature>__<style>.docx            │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Layer 2  JUDGE ──────────────────────────────────────────────────┐
│ run the rule registry (§5) against each produced paper            │
│ out: findings [{rule, severity, detail, where}]                   │
└───────────────────────────────────────────────────────────────────┘
                              ↓
┌─ Layer 3  ROLL UP ────────────────────────────────────────────────┐
│ per-subject report + one static INDEX.html                        │
│ the owner opens one screen per subject                            │
└───────────────────────────────────────────────────────────────────┘
```

**Layer 1 — Produce.** For each profile: `completion.complete()` with retrieval mocked to the subject's evidence pack, then `completion.draft_bytes()`. For each capability: the conductor path (`chat.start` → answer → `confirm_plan` → `run_capability` → `research` → `draft` → `docx_bytes`) with the capability's preset inputs. For each compute tool: `SessionManager.create` → `confirm` → `deliverables.write_export`.

Both paper paths were exercised end-to-end, unattended, in memory, on 2026-11-02: Kano → a 22,105-byte `.docx`; conductor PESTEL + NPV → an 18,784-byte `.docx` with the export gate returning `missing: []` and a correct H1/H2 outline.

**Layer 2 — Judge.** Pure code. No model, no network, no credits. Every rule in §5 that has a code backing reuses the product's own function, so the harness cannot drift from the product's behaviour.

**Layer 3 — Roll up.** A per-subject markdown report and a static `INDEX.html`. No server needed.

## 5. The rule registry

The harness judges papers against this registry. It is seeded from [`CONDUCTOR_MANUAL.md`](CONDUCTOR_MANUAL.md) §4 (the eight non-negotiables) and §8 (the coherence expectations and the three guards).

**Severity vocabulary for the harness verdict:**

| Status | Meaning |
|---|---|
| `enforced` | the product's own gate already blocks this; a finding is a real defect |
| `advisory` | reported, but does not fail the subject; the owner reads it when curious |
| `relaxed` | counted and stored, but not reported by default (§6) |
| `retired` | removed from the harness; the rule id stays in the table with a reason |
| `proposed` | not implemented yet |

| id | Rule | Source | Backing code today | Status |
|---|---|---|---|---|
| V-01 | No invented evidence: every external claim traces to a retrieved source | manual §4.1 | `verify`, `literature`, `writing` — no paper-level resolution check | `proposed` |
| V-02 | Gaps are named, never filled; only a **substantive** gap is printed (metadata gaps are `NULL`, not printed) | manual §4.2 | `completion.missing`, named-gap wording in `completion.py` | `proposed` |
| V-03 | Student inputs stay student inputs | manual §4.3 | none | `proposed` |
| V-04 | No silent framework substitution; a substitution is declared and recorded | manual §4.4 | `chat` records it; `guard.subject_fit` | `proposed` |
| V-05 | Computations come from the frozen core | manual §4.5 | `chat._recompute_guard` | `enforced` |
| V-06 | A paper never contains instructions, placeholders or template text | manual §4.6 | `paper.META` + `paper.check` (`meta_text`) | `enforced` |
| V-07 | Export is blocked when the paper is incomplete (409 with the missing list) | manual §4.7 | `paper.missing` | `enforced` |
| V-08 | The model does not research; it edits prose only after the deterministic draft | manual §4.8 | `chat.research` gate, `drafting` | `enforced` |
| V-09 | No heading level jump; no level-2 heading before a level-1 | manual §8 | `paper.check` (`heading_jump`, `heading_before_h1`) | `enforced` |
| V-10 | The paper has a Conclusion | manual §8 | `paper.check` (`missing_conclusion`) | `enforced` |
| V-11 | The paper has a reference list | manual §8 | `paper.check` (`missing_references`) | `enforced` |
| V-12 | Every dimension has a sourced item **or** a named gap | manual §8 | unit-tested only (`test_four_cells_each_carry_a_sourced_item_or_a_named_gap`) | `proposed` |
| V-13 | Every reference is cited in the body | manual §8 | none | `proposed` |
| V-14 | The Introduction states the decision and the thesis | manual §8 | none (a judgement) | `proposed` |
| V-15 | The Conclusion answers the thesis and introduces no new evidence | manual §8 | none (a judgement) | `proposed` |
| V-16 | The Discussion integrates the frameworks instead of repeating them | manual §8 | none (a judgement) | `proposed` |
| V-17 | No sentence asserts more than a frozen method licenses | manual §8 | `verify.overclaims` | `enforced` |
| V-18 | Combined papers name the origin of each mapped item | manual §8 | none | `proposed` |
| V-19 | The word count is inside the requested band | manual §7.10 | `chat.draft` reports `met_target` | `proposed` |
| V-20 | No placeholder student name; the byline reaches the title page | manual §4.6 | partial | `proposed` |

**Current baseline, 2026-11-02.** The full suite is **2553 tests → 84 failures + 12 errors (96 problems) in 623 s**. The framework-completion slice alone is 566 tests → 55 failures + 7 errors. The dominant failure classes are already the paper rules:

- `test_four_cells_each_carry_a_sourced_item_or_a_named_gap` (~11 frameworks) — this is **V-12**
- `test_the_model_prompt_speaks_<X>_and_keeps_the_safety_rules` (~13 frameworks)
- `test_outline_headings_are_present_and_title_cased` (~5) — this is **V-09/V-10/V-11**
- value-chain block-key naming mismatch (`firm_infrastructure` vs `inbound`)
- `firm_infrastructure` produced zero sourced items

The unit tests detect these by asserting on internals. **The harness detects the same defects by asserting on the finished `.docx`, for all 364 targets instead of the 43 that happen to have a fixture.**

### 5.1 What the harness finds — and finds better than a manual pass

The evidence for this is the current test suite. On 2026-11-02 the framework-completion slice ran **566 tests with 62 failures or errors**. Every one of the 62 asserts a property of the produced artefact that a machine can check:

| Class | n | What it asserts |
|---|---:|---|
| Model prompt contract drift | 23 | the instruction given to the model still names the framework and keeps the safety rules |
| V-12 — a cell has an item or a named gap | 19 | no cell is empty; one source cannot fill two cells |
| V-09/V-10/V-11 — outline and headings | 8 | the headings are present, title-cased and in the declared order |
| Block-key naming mismatch | 3 | the implementation and the profile name the same block keys |
| V-04 — refusal contracts | 3 | a brief without an industry is refused with an actionable reason |
| V-02/V-07 — the export gate | 1 | an empty cell does not block the paper |
| V-20 — the byline | 1 | the byline reaches the title page |
| V-01 — a cell filled without a source | 1 | a no-source run names a gap instead of writing background |
| Unit of analysis | 1 | the industry, not the firm, is the unit |

**Not one of them needs a human to decide whether the paper is any good.** That is the whole observation: a manual test of a feature is, mechanically, a set of assertions about the artefact — and every one of those assertions is expressible in code.

### 5.2 What only a human can find

| Error | Why no rule catches it |
|---|---|
| The evidence is real but **off-topic** for the dimension it sits under | needs a reader who knows what the dimension means |
| The paper is **correct and bland** — it answers and says nothing | a quality judgement, not a property |
| The **thesis is wrong** for the case, or the Discussion integrates badly | subject knowledge |
| The evidence is **too thin** for the claim, though a source is attached | domain judgement |
| The **numbers are unrealistic** for the business | business judgement |
| The prose is **templated in tone** without containing literal template text | reading |
| "Would this get a B?" | grading |

### 5.3 What neither finds

- a defect that only appears with **live retrieval** — the harness uses frozen fixtures by design (§8)
- a **UI** defect, such as a button that 422s — `scripts/ui_smoke.py` covers one path only
- anything that only appears **under load or concurrency**
- a **model-quality** problem in the Full paper, which is non-deterministic by nature

### 5.4 The residual — and the honest answer to "is it the same as testing by hand"

The harness can only enforce rules that are **written down**. A paper can pass all twenty rules and still be a bad paper, because "bad" includes things no rule encodes.

So the harness is **not a replacement for reading. It is a replacement for checking.** A manual pass produces two things — "this feature is broken" and "this paper is good". The harness produces the first, exhaustively and reliably, and produces nothing for the second.

The asymmetry is what makes it worth doing: a manual pass over 364 targets is **fatigue-bound**. Nobody checks the eighth rule of the twenty on paper 200. The harness checks all of them, on every run, with no fatigue — and the proof that manual passes miss things is that **96 tests are failing right now**, and the notebook records that **131 of 158 catalogue records have neither a worksheet template nor a linked method**.

**The workflow this implies.** The harness runs first and produces the failure list. The owner then reads **the failures plus a random sample of the passes** — the failures because they must be fixed, the sample because a green run is not evidence of a good paper. If the harness reports 14 failures out of 364, the reading is 14 papers and a sample, not 364.

**One design rule follows from this.** The harness must never emit a verdict like "bad". It emits `V-12 failed at H2 Consideration` — a named rule and a location — so that every finding can be argued with. The authority stays with the reader.

## 6. Relaxing a rule that is counterproductive

This is the part the harness exists to make safe. Some paper rules fire on nearly every paper; a rule that always fires teaches the reader to ignore it.

### 6.1 The principle: relax the alarm, never the guarantee

The harness's verdict is a **report**. The product's own gates — `paper.check`, `paper.missing`, `completion.missing`, `verify.overclaims`, the 409 — are the **guarantee**. Downgrading a rule in the harness changes what the owner is shown; it does **not** change what a student may export.

- ✅ The harness stops reporting V-12 as a failure for a given subject and says why.
- ❌ The harness weakens `paper.check` so a paper with an unfilled gap exports.

If a change should alter what the product asserts, it is a **computation-lane change** (`CONTRIBUTORS.md` §1A/§1B) and must be requested in `WORKLOG.md` with a `[design]` tag for the owner, not made here.

### 6.2 The procedure for changing a rule's status

1. **State** the rule id, the current status, the proposed status, and the evidence: how many papers fired it, and whether an inspected finding turned out to be a real defect.
2. **Record** it in §6.3 with a date and the deciding authority.
3. **Update** the status column in §5.
4. **Never delete** a rule from §5. Mark it `retired` with the reason. A later model must be able to see that the rule existed and why it went.
5. **Never relax** V-01, V-03, V-05, V-06, V-07 or V-08 as harness rules. Those are the product's guarantees; `CONTRIBUTORS.md` §1 rule 3 forbids weakening a check. The harness may report them more or less prominently, but it may not stop reporting them.

### 6.3 Rule change log

| Date | Rule | From | To | Evidence | Authority |
|---|---|---|---|---|---|
| 2026-11-02 | — | — | — | registry created from the manual; no rule changed | design owner (proposal) |

### 6.4 The noise policy

Each rule carries two counters in `manifest.json`: how many papers it fired on, and how many of those findings were confirmed as real on inspection. A rule with a **confirmed-defect rate under ~10 %** over a full run is a candidate for `advisory` or `relaxed`. A rule that fires on **every** paper is noise by definition and must be demoted, not left to cry wolf. Demoting is a finding about the *harness*, not about the product.

### 6.5 Rules that are likely to be counterproductive

Recorded now so a later model does not have to rediscover them. These are **expectations**, not decisions.

| Rule | Why it may be counterproductive | Default stance |
|---|---|---|
| V-12 every dimension has a sourced item or a named gap | For a *probe* profile the paper may legitimately carry general background with no citation in some dimensions; requiring a named gap in every cell produces noise papers | measure first |
| V-13 every reference cited in the body | Some retrieval results are used as background without an in-text citation | advisory |
| V-14 Introduction states the thesis | Not machine-checkable without a judgement | advisory, never `enforced` |
| V-15 Conclusion answers the thesis | Same | advisory |
| V-16 Discussion integrates rather than repeats | Same; closest to a style rule | advisory |
| V-19 word count inside the band | The band is a target, and short papers are legitimate | advisory |
| V-03 student inputs stay student inputs | Needs a way to tell student text from generated text that does not already exist | proposed, low priority |

## 7. The subject crosswalk

**This is the one thing that must be decided before Layer 3 can exist.** There is no single subject taxonomy in the codebase:

| Registry | Subject vocabulary |
|---|---|
| Subject pages (`subjects.SUBJECT_DEFS`) | accounting, finance, economics, management, project-management, entrepreneurship, operations, supply-chain, marketing, people, research (11) |
| Framework profiles (`framework_profiles.PROFILES`) | management, operations, people, strategy, project-management, change, marketing (7) — `pestel` and `five_forces` carry **no** subject |
| Capabilities (`capabilities.ENTRIES`) | **empty for all 126** — the `subject` key exists in the row and is simply never filled |
| Catalogue records (`subjects.CATALOGUE`) | **empty for all 158** |

`strategy` and `change` match no shelf; six shelves own no profile; 126 capabilities own nothing. A crosswalk is unavoidable.

**Recommendation (default, not yet ratified):** the harness owns its own mapping file, `scripts/validation/subject_map.json`, and does **not** edit `src/bp/**`. That keeps the whole harness inside the design-owner lane (B-080) and touches no frozen module and no test. Proposed entries:

| Source | Maps to |
|---|---|
| profile `strategy` (9) | `management` |
| profile `change` (1) | `people` |
| profile `pestel` | `management` |
| profile `five_forces` | `management` |
| capability `slot` H1 | see the H1→shelf table below |
| catalogue records | the shelf that owns the worksheet they cite, else `research` |

**Alternative, if the owner prefers the data to be canonical:** fill the `subject` key on the 126 capability rows and the 158 catalogue rows in `src/bp/product/`. That is a declared-data change in the **computation lane** and needs the owner's instruction; the harness would then read the subject from the product rather than from its own file. Both are legitimate. The harness default is the first, because it changes no product file.

**H1 slot → shelf** (the capability catalogue's existing grouping: 16 slots, 126 capabilities, verified 2026-11-02). The proposed shelf is a default, not a decision.

| Slot | n | Capabilities in it | Proposed shelf |
|---|---:|---|---|
| Financial Feasibility | 32 | break-even, NPV, IRR, DCF, WACC, CAPM, cash runway, bonds, tax, depreciation… | finance |
| Data Analysis | 19 | OLS, ANOVA, chi-square, probit, IV, RDD, panel, power, reliability… | research |
| Economic Context | 14 | inflation, BoP, national income, HDI, PPP, unemployment, fiscal multiplier… | economics |
| Delivery Status | 10 | CPM, earned value, Monte Carlo, decision tree, resource levelling, crashing… | project-management |
| Market Structure | 9 | Cournot, Nash, market power, price discrimination, cost curves, equilibrium… | economics |
| Policy Impact | 9 | externality/Pigouvian tax, Gini, public good, social welfare, tariff, tax incidence… | economics |
| Marketing Performance | 8 | A/B test, attribution, campaign efficiency, email health, media plan, funnel, web analytics | marketing |
| Operations | 6 | capacity/OEE, inventory policy, line balancing, process control, queue | operations |
| Financial Analysis | 4 | DuPont, ratio analysis, trend analysis, working capital | accounting |
| Customer Economics | 3 | channel economics, CLV, customer profitability | marketing |
| Customer Evidence | 3 | cohort retention, purchase intent, RFM | marketing |
| Impact | 3 | cost-benefit, cost-effectiveness, SROI | economics |
| Market Assessment | 2 | market share, market sizing | marketing |
| Market Response | 2 | demand curve, price elasticity | marketing |
| Ownership | 1 | cap table round | finance |
| Pricing | 1 | pricing decision | marketing |

**Four shelves receive no capability by slot:** `supply-chain`, `entrepreneurship`, `people`, `management`. They get their frameworks from the profile/worksheet path, but their compute tools sit on the subject pages rather than in the capability catalogue. The crosswalk therefore needs a second, explicit override list for those four — the slots above are a floor, not the whole map.

**Note on `supply-chain`:** four capabilities are operations-flavoured (`inventory_policy`, `capacity_analysis`, `oee_analysis`, `queue_analysis`) and would serve `supply-chain` better than `operations`. They are listed once in the manifest and filed under both shelves, exactly as the 30 shared worksheets are.

### 7.1 Worksheets are shared between shelves

**30 of the 59 worksheets a subject page serves** sit on **two** subject pages (re-measured 2026-11-03, entrepreneurship session). One paper serves both, and it is filed in both folders. This is why "validate subject by subject" is cheaper than the raw count suggests.

| Shared worksheets | Shelves |
|---|---|
| `CHG-01` … `CHG-13` (13) | management, people |
| `OPS-01`…`OPS-08`, `OPS-10`…`OPS-12` (11) | operations, supply-chain |
| `STR-13`, `STR-15`–`STR-18` (5) | management, entrepreneurship |
| `PM-10` (1) | project-management, people |

### 7.2 A reachability gap worth recording

**Re-measured 2026-11-03 (management session): 17 of the 75 profiles are not reachable from any subject
page** — `aida`, `attribution`, `brand_equity`, `change_organization`, `cro`, `digital_mix`, `email_crm`,
`funnel`, `marketing_automation`, `rfm`, `seo_content`, `social_media`, `stp`, `stp_evidence`,
`strategic_positioning`, `tam`, `utaut`. A student reaches them only through the conductor, if at all.
The harness must still produce their papers — otherwise the report silently omits a fifth of the
framework surface. **This is a product finding, not a harness defect; it is recorded here so it is not
lost.** `test_E_mgt_043` is the live measurement: it fails if the number moves, so the next reader
re-measures instead of copying this paragraph. The 22 recorded on 2026-11-02 included `bcg`,
`ge_mckinsey`, `generic_strategies`, `porters_diamond` and a `strategy_4` that does not exist; the first
four have since been wired to subject pages.

`change_organization` is the one profile in that list with a **complete profile, a full completion test
suite and no worksheet row on any shelf** (G-mgt-02): it works when called, and no page can call it.

A further **12 profiles have a worksheet that is not marked `draftable`** (activity_system_fit, ansoff, blue_ocean_errc, customer_journey, kano, measurement_plan, paid_media_plan, scenario_planning, servqual, strategic_group_map, value_stream_map, vrio). The harness produces them anyway: the draftable flag governs the student button, not the capability to write the paper. Re-measured 2026-11-03: still 12, unchanged.

## 8. Evidence fixtures

A paper needs evidence, and **live retrieval cannot be the oracle**: it is non-deterministic, network-dependent, rate-limited, and its results change between runs. The harness therefore mocks `sources.search_academic` and `sources.search_web` with a frozen pack per subject.

- A pack is a JSON list of real, citable sources with the fields the retrieval layer returns (title, authors, year, venue, DOI/URL, abstract).
- `scripts/sample_evidence.py` already holds a 9-record pack (the Apple/Iran case) and is the starting shape.
- Dimensions with **no** supporting source must fall into a **named gap** — which is itself a valid state the paper must handle, and is exactly what V-02 measures.
- A pack is **subject data**, not product code. It belongs in `scripts/validation/evidence/<subject>.json`.
- First pass recommendation: one shared pack for all subjects, then grow it per subject as the owner reads the papers. A thin pack produces thin papers; that is honest, and the report will show it.

## 9. Model policy for the harness

**Owner instruction, 2026-11-02:** the model used for this work is **OpenCode or OpenRouter, not the DeepSeek direct API**, to reduce cost.

**What the code supports today.** `src/bp/llm.py` defines `PROVIDERS = {"anthropic", "openai", "deepseek"}`; `BP_LLM_PROVIDER` selects one, `BP_LLM_MODEL` is required and never defaulted, `BP_LLM_BASE_URL` overrides the endpoint for the OpenAI-compatible classes, and `BP_LLM_REVIEWER_MODEL` is optional. `OpenAICompatProvider.KEY_ENV = "OPENAI_API_KEY"` and `self.base_url` is the **full chat-completions URL** (`src/bp/llm.py:59,65`).

**OpenRouter therefore works with no code change:**

```powershell
$env:BP_LLM_PROVIDER="openai"
$env:BP_LLM_BASE_URL="https://openrouter.ai/api/v1/chat/completions"
$env:BP_LLM_MODEL="<openrouter model id>"
$env:OPENAI_API_KEY="<openrouter key>"
```

`[UNVERIFIED against the live service]` — `llm.py:30-31,53-54` states the providers are unit-tested with an injected opener but untested live; the owner must run a first live call.

**OpenCode is not a model provider.** It is an agent harness that talks to a provider of your choice. Two readings, both recorded:

- **(a) OpenCode drives the harness** as the agent doing the work. Then OpenCode's own provider configuration is what matters, and the pipeline's model lane stays off entirely. This is the default and the cheapest option.
- **(b) OpenCode is meant to become the pipeline's model lane.** `PROVIDERS` has no `opencode` key, so this needs a new provider class. `CONTRIBUTORS.md` §11 makes "adding a new external API or model provider" a **stop-and-ask**: it needs the owner's instruction and a B-decision. It is not a harness change.

**The harness does not need a model at all.** The judgement layer is pure code, and the papers it judges are the deterministic Draft path — `BP_LLM_PROVIDER` unset means `llm.from_env()` returns `None` (`src/bp/llm.py:118`), so the model lane is off and the Draft is the live paper. The model lane only affects the *Full* paper, which is optional enrichment. **The cost decision therefore does not block the harness.** If the owner later wants Full papers inside the harness, run them as a separate, explicitly budgeted pass with OpenRouter.

## 10. Output contract

```
validation_out/
  INDEX.html                       the review surface — 11 subject panels
  manifest.json                    the machine record of the run
  <subject-slug>/
    <feature-id>__<style>.docx     the complete paper
    <feature-id>__<style>.json     the verdict for that paper
  reports/
    <subject-slug>.md              the report the owner reads
```

`manifest.json` shape:

```json
{
  "generated_at": "2026-11-02T03:00:00+08:00",
  "git_commit": "<sha>",
  "build": "1.56",
  "subject_map_version": 1,
  "features": [
    {"subject": "marketing", "kind": "framework", "id": "template_kano",
     "label": "Kano Model", "style": "apa",
     "paper": "marketing/template_kano__apa.docx", "sha256": "...",
     "words": 812, "verdict": "fail",
     "findings": [
       {"rule": "V-12", "status": "proposed", "severity": "high",
        "detail": "Consideration carries a sourced item but no named gap",
        "where": "H2 Consideration"}
     ]}
  ],
  "summary": {"pass": 350, "fail": 14, "by_rule": {"V-12": 9, "V-06": 2}}
}
```

Per-subject report:

```markdown
## Marketing & customers — 27 features, 24 pass, 3 fail

| Feature | Kind | Verdict | Findings |
|---|---|---|---|
| Kano Model | framework | fail | V-12 Consideration: no named gap |
| Customer Lifetime Value | capability | pass | — |
| … | | | |

Papers: `validation_out/marketing/`
```

## 11. Build order

| Stage | Deliverable | Notes |
|---|---|---|
| 0 | `subject_map.json` + one shared evidence pack | decisions only, no code |
| 1 | Framework walker → 76 papers, `manifest.json`, `INDEX.html` | reuses `completion.draft_bytes`; `paper.check` verdicts only |
| 2 | Full rule engine → every `enforced`/`proposed` rule with a code backing | the §5 registry becomes live |
| 3 | Capability walker → 126 conductor papers | seeds from `PRESETS` (125 of 126 already) |
| 4 | Compute-tool walker → 148 deliverables | via `SessionManager` + `deliverables.write_export` |
| 5 | The relaxation loop | measure noise, propose downgrades, update §6.3 |

Stage 1 alone already replaces most of the owner's reading, because the framework papers are the bulk of it.

## 12. Open questions for the owner

| # | Question | Default in this document |
|---|---|---|
| 1 | Where does the crosswalk live — the harness's own file, or the product's `subject` fields? | harness's own file (§7) |
| 2 | Which slots map to which shelves? | the H1 table in §7 |
| 3 | One shared evidence pack, or one per subject from the start? | one shared, then grow per subject (§8) |
| 4 | Which style does the harness produce — APA only, or APA and Harvard? | APA, with Harvard as a second pass |
| 5 | Which length band — Short, Mid or Long? | Mid |
| 6 | Does the owner want the Full (model-written) paper in scope? | no; Draft only, for cost reasons (§9) |

## 13. Change log

| Date | Change |
|---|---|
| 2026-11-03 | §7.2 re-measured by the management session: **17** profiles are reachable from no subject page (not the 22 recorded on 2026-11-02), and 12 are still not `draftable`. The count is now asserted by `tests/test_subject_management_acceptance.py::test_E_mgt_043` so this paragraph cannot drift again. `change_organization` is named as the one unreachable profile that works when called but has no worksheet row (G-mgt-02). |
| 2026-11-02 | Document created from the owner's request to automate validation subject by subject. Measured the surface (364 targets), recorded what already exists, fixed the architecture at three layers, seeded the rule registry from `CONDUCTOR_MANUAL.md` §4/§8, recorded the rule-relaxation procedure (§6), the subject crosswalk gap (§7), the evidence-fixture plan (§8) and the owner's model instruction (OpenCode or OpenRouter, not the DeepSeek direct API, §9). Nothing built. |
| 2026-11-02 | Made discoverable: a row in `HOME.md` §1 (Read in 30 seconds), §1 (By task) and §4 (the documentation spine); a pointer in `CONDUCTOR_MANUAL.md` §12; an entry in `WORKLOG.md` tagged `[design]`; an entry in `DISCUSSION_NOTEBOOK.md`; an entry in `CHANGELOG.md`. No product file, source file or test was changed. |
| 2026-11-02 | Added §5.1–§5.4, answering the owner's question "can the harness identify errors as if I manually tested each feature?". Measured it: of the 62 failing or erroring framework-completion tests, **all 62 assert a machine-checkable property of the produced artefact**. The harness therefore replaces *checking*, not *reading*; the residual is judgement (§5.2) and live-environment behaviour (§5.3), and the workflow it implies is to read the failures plus a random sample of the passes. |
