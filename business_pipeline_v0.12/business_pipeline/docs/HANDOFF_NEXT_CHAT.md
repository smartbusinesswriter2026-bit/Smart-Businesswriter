# Handoff: give the remaining frameworks instruction-driven completion

Read this first. It exists because the PESTEL build took far too long, cost far too
much and repeatedly broke things it was not asked to touch. Do not repeat that.

## 1. What already works, and where

One engine, one profile per framework. Nothing is branched on a framework name in
the engine or the page.

| Part | File | What it holds |
|---|---|---|
| Profiles | `src/bp/product/framework_profiles.py` | `PROFILES` with two entries: `template_five_forces`, `template_pestel` |
| Engine | `src/bp/product/retrieval.py` | `retrieve()`, `build_query()`, `country()`, `country/region` tables (197 names), gate, ranking, de-duplication |
| Pipeline | `src/bp/product/completion.py` | `complete()`, `missing()`, `draft()`, `draft_bytes()`; the Draft and Full paper |
| Route | `src/bp/product/api.py` | `POST /api/cases/frameworks/complete`, `POST /api/cases/frameworks/report` (409 with missing labels) |
| Template payload | `src/bp/server.py` `_template_payload` | attaches the profile to `/api/templates/{id}` as `completion` |
| Page | `web/index.html` | one form: `evidenceWorksheetForm` + `bindEvidenceCompletion` + `collectEvidenceInputs` + `generateEvidencePaper`, selected by `if (t.completion)` |
| Chat | `src/bp/product/chat.py` | `_research_one` calls the same `retrieval.retrieve` with the profile's gate |

Verified on a fresh server on 2026-10-29, through the real routes:

- PESTEL, Morocco brief, country field blank → unit `Morocco`, 6/6 dimensions sourced.
- Full paper → HTTP 200, 1,950 words, 70 s, stored as `PESTEL · Full paper`.
- Five Forces, grocery/cold-chain brief → editor with ratings, Draft 1,080 words, byline on the title page.
- `template_swot` unchanged: no profile, no completion.

## 2. The one thing that is not obvious: the server must be restarted

The page is read from disk on every request, but the Python process is not. After
editing `src/`, the page looks new while every API answer is old. That cost hours.

```powershell
# restart the listener only; the supervisor reloads the code 5 s later
$p = (Get-NetTCPConnection -State Listen -LocalPort 8021).OwningProcess
Stop-Process -Id $p -Force
```

Then check it actually loaded:

```powershell
python -c "import json,urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8021/api/templates/template_pestel'))['completion']['unit'])"
```

**Port 8021 is the owner's page.** Do not serve another directory on it. Port 8031 is
a stale v0.76 copy from another checkout — ignore it, or close it if the owner asks.

## 3. Adding the next framework (the whole job)

For each worksheet that should complete, in this order:

1. Add **one dict** to `PROFILES` in `framework_profiles.py`. Copy the PESTEL shape:
   `template, key, label, title_prefix, unit{field,label,help,example,refuse},
   ratings, assumption, sites, providers, gate, blocks[], outline{}, voice{}, notes{}`.
2. **Blocks must match the template.** `templates.CANVAS_BLOCKS["<template>"]` is the
   source of truth for keys and labels; `templates.describe(id)["blocks"]` is what the
   page renders. A profile whose labels differ produces a paper with the wrong headings.
3. Every block needs `cues` (space-separated words), `queries` (one phrase, no case-specific
   nouns, no country), and a `notes` entry with `analysis`, `qualify`, `short` — plus
   `probe` when `assumption: "probe"`.
4. `outline`: `framework, context, discussion, implications, limitations, conclusion, lead`.
5. `voice`: `thesis_question, unit_noun, block_plural, lens, closing, intro_frame,
   context_frame, interaction, implication_frame, reference_heading`.
6. Add the worksheet to `WORKSHEETS` in `subjects.py` with `draftable: True` if it is not
   already there.
7. **No edits** to `completion.py`, `api.py` or `web/index.html`.
8. Tests: N blocks or named gaps, the unit refusal, empty → gap/probe, the outline
   headings, the byline, the 409. Copy `tests/test_pestel_completion.py`.
9. One APA and one Harvard sample.

Decide two things per framework, and record them:

- **Unit of analysis.** `industry` (needs `guard.five_forces_fit`) or `country`
  (a country, or the explicit word `Global`; never defaulted). A framework with no
  natural unit should not be completed.
- **Gap mode.** `assumption: "case"` lets the model propose a labelled case assumption
  (Five Forces). `assumption: "probe"` returns a named gap plus "what to look for" and
  never a model-written fact (PESTEL). Anything with country or company facts is `probe`.

Order: do the **management shelf** first — SWOT, Value Chain, Ansoff, VRIO, the canvases
already have block keys in `templates.CANVAS_BLOCKS`. Then finance, entrepreneurship,
project management. Do them **one at a time, each verified live**, not in batches.

## 4. Traps that already bit

- **Docs counts.** `tests/test_docs_sync.py` compares `docs/HOME.md`, `HANDOFF.md` and
  `CONTRIBUTORS.md` with the collected test count (now **1847**) and the build in
  `CHANGELOG.md` (now **1.47**). Adding a test means updating those numbers.
- **Never rewrite a doc with a global regex.** A `**\d+ tests pass.**` replacement
  destroyed the historical counts of nine changelog entries, and restoring from git
  deleted a **1.48 entry that another editor had written**. If you touch the changelog,
  edit one line.
- **Concurrent edits.** This tree is edited by more than one session; untracked
  `billing.py`, `paypal.py`, `test_product_billing.py` are not from this work. Run
  `git status` before and after.
- **The model is flaky.** It sometimes returns an empty reply. `completion._ask` retries
  once; `_problems` allows the framework's own labels and the declared region's words.
  Set `BP_PROSE_DUMP=1` to write the raw reply to `%TEMP%\bp_prose_dump.txt`.
- **The proper-noun guard is not decoration.** It refused "European" for a Morocco
  paper. Do not widen it to silence a failure; widen it only for the framework's own
  words.
- **Item cap is 3 per block** (`retrieval.MAX_ITEMS`), one 20 s deadline for the whole
  completion (`BP_RESEARCH_DEADLINE`), and one source cannot fill two blocks.

## 5. How to work on this without repeating the damage

- Do exactly the instruction. Ask before touching an adjacent file.
- One framework at a time. Verify it through `http://127.0.0.1:8021/`, on the real form,
  with the country/industry field, and generate both a Draft and a Full paper.
- Targeted tests (`pytest tests/test_pestel_completion.py tests/test_docs_sync.py`), not
  the whole suite on a loop.
- Do not build a throwaway server on 8021. If you need a second instance, use another
  port and say which.
- When something works, say what you ran and what it returned. When it fails, quote the
  rejection reason (`%TEMP%\bp_model_reject.log`) instead of guessing.
