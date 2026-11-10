# RRA handoff — where the growth loop stands, and what is left

**Written 2026-11-10 by MCode, mid-build.** This is the file to read first
when you pick the Relevance Research Agent up again.

The RRA (Relevance Research Agent) is the outward-looking half of the growth
loop. The repair loop detects breakage; the RRA asks whether the product
still matches what business schools teach, assess and expect, and what is at
risk of becoming obsolete. Its findings become **capability gaps**, which
wait for the owner's decision and are then scaffolded by the growth loop.

---

## 1. The headline

**The measurement now holds.** A sweep over a verified URL set reads the
frameworks and clears the control set:

```
CONTROLS: 9/12 ratio=0.75 passed=True
verdict: the measurement held
held: PESTEL, SWOT, Five Forces, Business Model Canvas (framework)
      Break-even, Net Present Value, Ratio analysis (capability)
      Vetted web source registry, Proprietary PDF corpus (retrieval)
missing: BCG, ERRC, Ansoff — "not found in any evidence excerpt"
candidates=18 survivors=18 strict_pass=18 withheld=0
measurement_held: True
```

Before this build the same sweep held **5/12 (0.4167)** and withheld
everything. The controls were right to withhold — the read path was broken.

**What has NOT been done:** no sweep has been run with the model stages on,
no gap has been approved, and nothing has been scaffolded. Those steps need
credits and the owner's decision.

---

## 2. Why it was failing — five faults, all fixed

The RRA read **353 pages** across its history and recorded **zero** framework
names. Not one control could see a framework. The cause was not the
measurement; it was the read path between the network and the reader.

### 2.1 The fetch was cut too short (fixed)

`src/bp/product/relevance/s1_scout.py` read the response to **100,000
characters**. A course-catalogue page's header, logo and script block fill
that space, so the body was cut off. Measured on the Bocconi strategy page:

| fetch cap | raw | readable text | framework found |
|---|---|---|---|
| 100,000 | 100,000 | 1,809 chars (nav chrome) | none |
| 400,000 | 185,569 | 8,730 chars | **Business Model Canvas** |

The owner's own Phase 1 probe read **400,000** characters and read the
frameworks. That number is now `FETCH_CAP_CHARS`.

### 2.2 The User-Agent was refused (fixed)

`SmartBusinessWriter-RRA/1.0 (research; respects robots.txt)` drew a **403**
from `www.hbs.edu`, which answers a browser. The agent still names itself:

```
Mozilla/5.0 (compatible; SmartBusinessWriter-RRA/1.0; research)
```

Same page, same moment: product UA → `HTTP 403`; new UA → `HTTP 200`, and
the page names `Value Chain` and `Balanced Scorecard`.

### 2.3 The render was thrown away (fixed)

The scout compared the **rendered text** with the **raw markup** of the
fetch. Markup is always longer, so the browser's reading was discarded as
"no longer than the fetch" — the very page the browser had read for us. The
comparison is now between the two **readable** texts.

### 2.4 The body was capped before it was stripped (fixed)

The cap was applied to raw markup, so the reader received the head of the
document: a logo's `<path d="M36.88...">` data and a menu. Excerpts in the
evidence store literally read `<path d="M36.8828 55.5364C36...">`. The text
is now stripped **first** and capped **after**, so `MAX_TEXT_CHARS` counts
readable characters.

### 2.5 Two labels could not be matched (fixed)

The taxonomy names a framework as the product knows it — "Porter's Five
Forces", "Ansoff Growth Matrix" — but a course page writes the short name.
`_label_forms` tried the label, the parenthetical-stripped head and the
possessive-dropped variant; the acronym fallback only fires when the **first
word** is all-caps, which "Porter's" and "Ansoff" are not. So a page saying
*"Five Forces analysis"* recorded **no mention**.

Fixed **in the data**, not in the code: a taxonomy topic may now declare
`aliases`, and `_named_topics` consults them. Added for
`framework_five_forces`, `framework_ansoff`, `framework_kotter` and
`framework_three_horizons`.

### 2.6 Also added: a bot check is not the page

Some sites answer with a JavaScript challenge and a `202`. Storing that as
the page's text would put words in the evidence store that the school never
wrote. `_detect_challenge` now names such a page as unreadable.

---

## 3. Files changed in this build

| file | change |
|---|---|
| `src/bp/product/relevance/s1_scout.py` | fetch cap 100K→400K; browser-compatible UA; readable-length render comparison; strip-then-cap; render a failed fetch; `_detect_challenge` |
| `src/bp/product/relevance/s2_reader.py` | `_named_topics` consults a topic's `aliases` |
| `qa/relevance/taxonomy.json` | `aliases` on four framework topics |
| `qa/relevance/curated_seed.json` | **new** — verified URL set (see §5) |
| `tests/test_relevance_readpath.py` | **new** — 15 tests pinning each fault |

---

## 4. What is left, in order

### Step 1 — a sweep with the model stages on

The sweep that proved the read path ran with `use_model=False`: it used the
deterministic path only, so **no model call was made and no credit was
spent**. The full sweep needs the three model stages (discovery query,
passage extraction, spec drafting) on `deepseek-v4-pro` via the OpenCode Go
gateway.

```powershell
cd D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline
$env:PYTHONPATH="src"
# The admin console has the button: Monitor -> Relevance -> Discover pages / sweep.
```

**Check the gateway first.** On 2026-11-10 the whole search chain was down:
Brave `HTTP 429`, Firecrawl `HTTP 429` (24 h cooldown), and the OpenCode Go
gateway returned *"Unexpected server error"* for **any** prompt — including
`Reply with exactly: PING` with no websearch tool. That is the gateway, not
the code. If the gateway is still down, the discovery stage cannot run; the
curated seed below can still run the sweep.

### Step 2 — the three controls still missing

BCG, ERRC and Ansoff were not found in the seed. They are not a bug: those
frameworks are simply not named on the pages in the seed. Either

- add pages that name them (search each school's own domain for the
  framework's name, as the owner's Phase 1 probe did), or
- accept 9/12, which **passes** the 0.75 threshold.

Do not lower the threshold to make a number look better.

### Step 3 — the owner's decision, then the scaffold

A gap that clears the gate lands in the **decision queue** in
`web/admin-sbw.html` (Monitor → Relevance). Approve / reject / defer, with
a reason and a user. **Do not approve on the owner's behalf** — the absence
of an apply endpoint is deliberate.

On approval the gate calls `ops_log.log_finding(rule="capability_gap",
source="relevance")`, the gap appears in the Validation panel, and the
growth loop (`src/bp/product/growth_loop.py`) scaffolds it on its next pass.

---

## 5. The curated seed

`qa/relevance/curated_seed.json` — 9 pages, each read on 2026-11-10, each
with the framework names found in its text. It lets a sweep run with **no
search provider and no model call**.

```powershell
cd D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline
$env:PYTHONPATH="src"
$env:BP_STATE_DIR="$env:TEMP\rra-seed-state"   # keep the real state clean
python -c "import json,os; from bp.product.relevance import runner; \
urls=[p['url'] for p in json.load(open('qa/relevance/curated_seed.json',encoding='utf-8'))['pages']]; \
r=runner.run_sweep(url_list=urls, use_model=False); \
print(r['controls']['held'],'/',r['controls']['total'],r['controls']['passed'])"
```

**One honesty note, and it matters.** A curated list proves that **the reader
can see** a framework on a course catalogue. It does **not** prove that
**discovery can find** such a page — that is the search provider's job, and
the provider was down. Report the two claims separately. Do not let a
curated sweep stand in for a discovery sweep.

---

## 6. Housekeeping done in this build

- **The runaway sweep was stopped.** A leftover `run_rra_sweep3.py` (PID
  35412) had been running since 06:43 against the dead search chain, with
  its own server on :8074. It was killed; the user's other servers (8000,
  8021, 8075) were left alone.
- **Stale run rows.** Five runs are stuck at `status=running` with no
  `finished_at` — a crashed sweep leaves its "started" row behind. They are
  historical, not a live sweep. `BP_RELEVANCE_AUTOSTART` is 0, so no sweep
  restarts itself.
- **`state/relevance/` was not written to.** Every verification ran with
  `BP_STATE_DIR` pointed at a temporary directory.

---

## 7. The honest caveats

1. **The three missing controls are real.** BCG, ERRC and Ansoff were not
   seen. The measurement passes at 0.75 with nine, but a wider sweep may
   find them — and may also find that some school does *not* teach them,
   which is a finding, not a failure.
2. **The search provider is an unresolved external dependency.** The RRA's
   discovery stage depends on a gateway that was down. This is the one thing
   this build could not fix, because it is not a code fault.
3. **The sweep that proved the read path used no model.** It proves the
   reader and the controls. It does not prove the model stages, the back-test
   against a live catalogue, or the gap specs.
4. **The framework gap set is not yet trustworthy.** 18 candidates survived
   the skeptic and passed the strict checklist, but they were produced
   without the model stages and without a discovery sweep. Treat them as
   candidates to be reviewed, not as findings.

---

## 8. Where the code lives

| what | where |
|---|---|
| the pipeline (8 stages, S0–S7) | `src/bp/product/relevance/` |
| the scout (the read path fixed here) | `src/bp/product/relevance/s1_scout.py` |
| the reader (aliases fixed here) | `src/bp/product/relevance/s2_reader.py` |
| the control set | `qa/relevance/controls.json` |
| the sampling frame | `qa/relevance/schools.json` |
| the taxonomy (owner-edited) | `qa/relevance/taxonomy.json` |
| the allowlist | `qa/relevance/allowlist.json` |
| the back-test | `qa/relevance/backtest.json` |
| the curated seed | `qa/relevance/curated_seed.json` |
| the decision queue | `web/admin-sbw.html` (Monitor → Relevance) |
| the scaffold side | `src/bp/product/growth_loop.py` |
| the Phase 1 findings | `docs/RRA_FINDINGS_PHASE1.md` |
| the owner's proven probe | `.scratch/phase1_frameworks_v3.py` and `.json` |

**The owner's Phase 1 probe is the method that worked.** It searched inside
each school's own domain for each framework name, fetched the results, and
counted a hit only when the name appeared in the **page text** — never in a
search snippet. It read 176 pages across 75 searches and found Balanced
Scorecard at 5 schools, BMC at 8, BCG at 6, McKinsey 7S at 5, Three Horizons
at 6, Kotter at 4, OKR at 4, Blue Ocean at 5, SWOT at 5, PESTEL at 2, Five
Forces at 3, Generic Strategies at 2, ERRC at 1 and Ansoff at 1. That
result set is the backlog this build is working against.
