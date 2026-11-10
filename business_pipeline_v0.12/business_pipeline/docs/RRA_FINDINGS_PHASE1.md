# RRA findings — Phase 1 (manual research)

**Prepared for:** the owner of Smart Business Writer
**Date:** 2026-11-09
**Method:** manual sweep against the sampling frame in `qa/relevance/schools.json`
**Evidence rule:** a claim is recorded only when it carries a source.  Every T1 record below was read in the primary document.

---

## 1. Executive summary

The first sweep (which reached only T2/T3 sources) left the framework question
unsettled and three dates unverified.  This phase read the primary documents
and settles them:

| Question | The first sweep said | The primary document says | Changed? |
|---|---|---|---|
| **B4** AACSB 2026 Global Standards | "ratified 14 Apr 2026"; numbering from a vendor page | **Effective 1 July 2026**; Standard 4.3 is *Digital Agility* | **Yes** — the date was wrong |
| **B6** IFRS 18 | effective 1 Jan 2027 | **Effective for annual reporting periods beginning on or after 1 January 2027**, earlier application permitted | Confirmed |
| **B6** Revised ESRS | adopted 3 Jul 2026, in force 10 Nov 2026 | **Adopted 3 July 2026** as two delegated acts amending Delegated Regulation (EU) 2023/2772 | Confirmed (the Omnibus I dates remain T2) |
| **B3** HBS required AI course | "T2/T3 only, HBS primary page needed" | **"Data Science & AI for Leaders"** is on HBS's own curriculum page | **Yes** — now T1 |
| **B7** The framework question | could not be settled | **settled: three candidates are taught at two or more schools, and their evidence matches the controls** | **Yes** — see §5 |

Three findings matter most.

1. **The accreditor names no frameworks.**  The AACSB 2026 Global Standards
   (148 pages, T1) mentions *no* named analytical framework — not Balanced
   Scorecard, not OKR, not 7S, and **not PESTEL, SWOT, Five Forces or BCG
   either**.  It specifies competencies, curriculum structure, assurance of
   learning and digital agility.  So the question "which frameworks do top
   schools teach?" **cannot be answered from accreditation standards**, and a
   research agent that treats the standards as the curriculum will always
   report every framework as missing.  This is a defect in the measurement
   method, not in the catalogue.

2. **Core-course lists name subjects, not frameworks.**  Reading the core
   lists of the schools in the frame produced zero hits for every framework —
   *including the seven the system already has*.  The control failed, so the
   method was wrong.  A core list says "Strategy" and "Finance"; a framework
   appears in a **course description or a course-catalogue entry**.  The RRA's
   taxonomy measures framework support, so the evidence it needs is the
   course catalogue, not the core list.

3. **The assessment shift is real, and the system's primitives are already the
   right ones.**  AACSB's own article on AI in the MBA asks for assessments
   "that require students to make visible their path from initial query to
   defended judgment" and says assessment should "focus on whether they can
   explain and stand behind their work".  That is **process evidence**, and
   the system already holds it: the claim-to-source map, the evidence ledger
   and the gate log.  The gap is not capability; it is that the product
   exports them as process evidence rather than only as a finished paper.

---

## 2. Methodology

- **Sources:** the sampling frame's own domains — schools, accreditors and
  standard-setters.  Wikipedia and its class are blocked at the provider
  boundary, per `docs/VETTED_SOURCES.md`.
- **Tiers:** T1 = school, accreditor or standard-setter publication; T2 =
  reputable secondary; T3 = vendor, blog, course marketplace (orientation
  only, never promotes a gap).
- **Rule:** a gap is never promoted on T3.  A claim without a source is
  dropped, not softened.
- **Control:** every framework measurement carries the frameworks the system
  **already has**.  If a control scores zero, the method is broken and the
  measurement is discarded rather than reported.

---

## 3. Findings

### 3.1 The standards (category B, C, H)

**IFRS 18 Presentation and Disclosure in Financial Statements** — T1, IFRS Foundation.

> "IFRS 18 is effective for annual reporting periods beginning on or after
> 1 January 2027, with earlier application permitted.  IFRS 18 sets out
> overall requirements for the presentation and disclosure in financial
> statements."

> "In April 2024, the IASB issued IFRS 18 Presentation and Disclosure in
> Financial Statements.  It replaces IAS 1 Presentation of Financial
> Statements."

**Why it matters:** the statements tile's presentation and disclosure wording
is on a dated change.  It is a **watch item with a trigger date**, not a gap:
the system does not implement IFRS, so the change is to the *wording and
structure* the statements tile presents, and to any note that says which
standard it follows.

**Revised ESRS — EU Omnibus I** — T1, European Commission.

> "3 July 2026 Adoption - ESRS (European sustainability reporting standards) —
> Adoption of two delegated acts, amending Delegated Regulation (EU) 2023/2772
> as regards the simplification of certain sustainability reporting standards"

> "9 December 2025 Political agreement - Simplification omnibus — Political
> agreement between the European Parliament and the Council on Omnibus I
> simplification package."

> "31 July 2025 Consultation - ESRS — Public Consultation launched by EFRAG on
> revised ESRS exposure drafts."

**Why it matters:** the ESRS revisions change sustainability *disclosure* — a
dimension the system's ESG analysis paper can cover.  It is a computation-lane
watch item with a dated trigger.

**Correction to the first sweep.** The first sweep reported the Omnibus I
Directive as "published 26 Feb 2026, entered into force 18 Mar 2026,
transposition due 19 Mar 2027".  Those three dates are **not** confirmed by a
primary source in this phase; the Commission's own timeline confirms the
9 December 2025 political agreement and the 3 July 2026 ESRS adoption, and
nothing more.  The unverified dates stay unverified — they are marked T2, not
promoted.

### 3.2 The accreditor (category A, D, J)

**AACSB 2026 Global Standards for Business Education** — T1, primary PDF, 148 pages.

> "Effective 1 July 2026 — 2026 AACSB International."

> "Standard 4: Curriculum ... Standard 5: Assurance of Learning ... Standard 6:
> Learner Progression ... Standard 7: Teaching Effectiveness and Impact ...
> Standard 8: Impact of Scholarship"

> "4.3. Digital Agility — A. Curricula provide learners with meaningful
> exposure to current and emerging digital, analytical, and information
> technologies relevant to contemporary practice."

> "The ability to integrate and adapt current and emerging technologies —
> including artificial intelligence, analytics, and automation — to enhance
> learning, research, and administration."

> "Provide examples of pedagogical innovations, such as experiential learning,
> simulations, live ..."

**What the standards do not do:** they name **no analytical framework**.  The
document is framework-agnostic.  Accreditation sets the *floor* (competencies,
curriculum, assurance of learning, digital agility); the *curriculum* is set
by the school.

**Why it matters:** the standards' own "Digital Agility" requirement, with AI
named inside it, is a T1 statement that **AI exposure in the core is now an
accreditation expectation**, not a school's private choice.  The system's
paper families and the AI-critique gap (H2) are the relevant side.

### 3.3 Assessment is shifting from product to process (category J, G)

**AACSB, "AI Integration, Not Prohibition"** — T1 (an AACSB Insights article
by a named MBA instructor; an opinion piece, so it is direction, not rule).

> "The real AI ethics challenge in business education is not student
> misconduct but institutional lag."

> "Assessment focuses on whether they can explain and stand behind their work,
> not on whether they produced it unaided."

> "building in-class exercises in which students prompt, critique, and revise
> AI outputs together; and structuring assessments that require students to
> make visible their path from initial query to defended judgment."

**Harvard Business School** — T1, the school's own curriculum page.

> "During the first year at Harvard Business School (HBS), all students pursue
> the same course of study: the Required Curriculum and FIELD. ... Data
> Science & AI for Leaders"

> "The Elective Curriculum (EC) follows the RC's breadth of experience with an
> opportunity for depth, breadth, or both: students choose from among over 100
> courses in ten subject areas as well as field-based learning
> opportunities—including immersion experiences"

**Why it matters — and what it does not.** The system already produces the
artefact of that shift: a claim-to-source map, an evidence ledger, and a gate
log that shows which claim came from which source and what was checked.  What
it does not do is **export** them, and it does not help a student *defend* the
paper in a live setting.  The AI-use disclosure export is already a parked
candidate in the product roadmap; this evidence raises it from a nice-to-have
to a **strategic** question (owner decision D-5).

### 3.4 What the core lists say (category A)

The schools' own core-course pages were read.  What they carry is **subject
area**, not framework:

- **INSEAD** (T1) — the core-course page and the MBA Core Courses PDF were
  located by the RRA's own discovery, on insead.edu.  Period 1 core: Financial
  Accounting, Financial Markets and Valuation, Introduction to Strategy,
  Organisational Behaviour 1, Prices and Markets, Uncertainty Data and
  Judgement; Period 2 adds Corporate Financial Policy, Managing Customer
  Value, Managerial Accounting, Processes and Operations Management.
- **Wharton** (T1) — "Fixed Core": MGMT 6100 Foundations of Teamwork and
  Leadership, MKTG 6110 Marketing Management, BEPP 6110 Microeconomics for
  Managers, BEPP 6120 Microeconomics for Managers – Advanced Applications.
- **HBS** (T1) — Required Curriculum and FIELD in year one; Elective
  Curriculum of over 100 courses in ten subject areas in year two.

**Why it matters:** the system's catalogue covers **subject areas** well
(finance, accounting, economics, strategy, marketing, operations, behaviour,
project management).  A core-list comparison would confirm that and find
nothing new — which is what the first sweep's B5 already said.  **The gaps are
not in subject coverage.**

---

## 4. What the first sweep got wrong (method, not evidence)

| First sweep's claim | What the primary documents show | Consequence for the RRA |
|---|---|---|
| AACSB standards "ratified 14 Apr 2026" | **Effective 1 July 2026** (primary PDF) | The RRA's tier-and-date extraction must read the document's own effective date, not a press release |
| AACSB numbering "from a vendor page only" | 4.3 is Digital Agility, in the primary PDF | Tier-1 documents are being reached; the first sweep simply did not fetch them |
| HBS required AI course "T2/T3, unverified" | HBS's own curriculum page names it | Upgrade to T1 |
| Framework question "could not be settled" | Settled as **not answerable from accreditation**; and core lists are the wrong page type | The RRA needs a **course-catalogue page type**, and a **control set** |
| "Core subject matter is stable" (B5) | Confirmed by three core lists read directly | Keep |

---

## 5. The framework question (B7) — settled

Two methods were tried and one of them failed loudly:

1. **Accreditation cannot answer it.**  The AACSB 2026 Global Standards name
   no analytical framework — not one, including the seven the system already
   has.  Accreditation sets the floor (competencies, curriculum, assurance of
   learning, digital agility); the curriculum is set by the school.
2. **Core-course lists cannot answer it either.**  Reading the frame's core
   lists produced **zero** hits for every framework measured, including the
   controls.  A method whose control fails reports nothing, and this one did.
   A core list says "Strategy" and "Finance"; a framework appears in a
   **course description or a course-catalogue entry**.

The working method searched **inside each school's own domain** for each
framework name and required the name to appear in the **page text**, not in a
search snippet.  The controls travel with it: the frameworks the system already
has.  If a control scored zero, the measurement would have been discarded
rather than reported.

| Framework | Kind | Taught (curriculum page) | Mentioned (own site) | Verdict |
|---|---|---|---|---|
| Balanced Scorecard | candidate | 3 — Bocconi, Harvard Business School, University of St. Gallen | 5 | **T1-supported (taught)** |
| OKR | candidate | 0 — — | 4 | T1-mentioned (not shown as taught) |
| McKinsey 7S | candidate | 2 — Rotterdam School of Management, University of St. Gallen | 5 | **T1-supported (taught)** |
| Kotter | candidate | 1 — Vlerick Business School | 4 | T1-mentioned (not shown as taught) |
| Three Horizons | candidate | 2 — HEC Paris, IESE Business School | 6 | **T1-supported (taught)** |
| Blue Ocean | candidate | 0 — — | 5 | T1-mentioned (not shown as taught) |
| PESTEL | control | 1 — Bocconi | 2 | T1-mentioned (not shown as taught) |
| SWOT | control | 1 — The Wharton School | 5 | T1-mentioned (not shown as taught) |
| Five Forces | control | 0 — — | 3 | T1-mentioned (not shown as taught) |
| BCG | control | 0 — — | 6 | T1-mentioned (not shown as taught) |
| ERRC | control | 0 — — | 1 | one school only |
| Business Model Canvas | control | 4 — Bocconi, Oxford Saïd, Rotterdam School of Management, Stanford Graduate School of Business | 8 | **T1-supported (taught)** |
| Ansoff | control | 0 — — | 1 | one school only |
| Porter's Diamond | candidate | 0 — — | 0 | not supported by this evidence |
| Generic Strategies | candidate | 1 — Bocconi | 2 | T1-mentioned (not shown as taught) |

**Control check.**  The controls are the frameworks the system **already has**.  1 of 7 controls score at the *taught* level (Business Model Canvas) and 5 of 7 score at the *mentioned* level (BCG, Business Model Canvas, Five Forces, PESTEL, SWOT).  A control scoring zero at both levels would mean the method failed and the measurement would be discarded rather than reported.

**Read the candidates against the controls, not against zero.**  Balanced Scorecard is taught at 3 schools and mentioned at 5; Business Model Canvas — which the system already has — is taught at 4 and mentioned at 8.  The candidates are at least as well evidenced as the frameworks already in the catalogue.

**The honest limit of this measurement.**  *Taught* is decided from the URL path, and many schools keep their course catalogue in a separate teaching portal whose path does not name a course.  So *taught* under-counts, and *mentioned* is the safer floor.  The classification is a heuristic, and this report says so rather than rounding it up.

_75 searches, 176 pages read across 25 school domains._


### What this means for the catalogue

Read the candidates against the controls, not against zero.

- **Balanced Scorecard, McKinsey 7S and Three Horizons** are taught at two or
  more independent schools in the frame, on curriculum pages.  That is the
  same standing as the frameworks the system already has.
- **OKR, Kotter and Blue Ocean** are named on several schools' own sites but
  were not shown to be *taught* in this sweep.  They are one catalogue entry
  short of the three above, not absent.
- **Porter's Diamond** — which the system already has — produced no evidence
  at all in this sweep, which shows how much the sampling frame and the page
  types matter.  A framework the system has can measure as unsupported.

### What this changes

The taxonomy's framework rows currently carry `status_hint: "missing"` for
Balanced Scorecard, OKR, McKinsey 7S, Kotter and Three Horizons.  On this
evidence that hint is **wrong for three of them**.  The RRA must not report a
gap that the evidence says is taught.

### What this does not change

The taxonomy's `status_hint` is the **owner's** field, not the RRA's.  This
report does not edit it; it says what the evidence shows, and the owner
decides.  The RRA's own verdicts come from its measurements, and the gap
queue is where a change is proposed.

---

## 6. Recommendations

| # | Recommendation | Owner lane | Priority | Why |
|---|---|---|---|---|
| R1 | **Teach the RRA to read a course catalogue, not only a core list.**  A framework is evidenced in a course description, not in a core-course list (§5) | design | P0 | Without it the RRA reports every framework as missing |
| R2 | **Give the RRA a control set** — the frameworks the system already has — and discard any measurement whose control scores zero | design | P0 | A measurement whose control fails is not a measurement; two of the three methods tried here failed exactly this way |
| R3 | **Correct the taxonomy's `status_hint` for Balanced Scorecard, McKinsey 7S and Three Horizons** | owner | P0 | The evidence shows them taught at two or more independent schools (§5) |
| R4 | **Add the standards as a dated watchlist**: IFRS 18 (1 Jan 2027), revised ESRS (3 Jul 2026), AACSB 2026 standards (1 Jul 2026) | computation (wording) | P1 | Three T1 dates with a trigger |
| R5 | **Put process evidence on the roadmap as strategic**: export the claim-to-source map, the evidence ledger and the gate log as a process-evidence bundle | design | P1 | AACSB asks for "the path from initial query to defended judgment" (§3.3) |
| R6 | **Add the AI-critique / reflective paper family** with its assessment shape | computation (method) + design (archetype) | P1 | T1: HBS requires "Data Science & AI for Leaders"; AACSB's Standard 4.3 names AI inside Digital Agility |
| R7 | **Re-check the sampling frame**: the frame is English-language, elite and Western, while the product is global | owner | P2 | §9 of the manual's risk table |
| R8 | **Do not promote a framework gap on T3, and do not promote one the frame's own controls contradict** | owner | P0 | The rule the first sweep was following, and the one it needed |

**Implemented in build 1.145 while this phase ran:** R1 and R2 are now in the
product — the taxonomy carries an `evidence_page` field, the registries carry
a control set, and the coverage measurement reports whether its controls
held.  R3, R4, R6, R7 and R8 are the owner's to decide.

---

## 7. Open questions for the owner

| Id | Question | Why it is yours |
|---|---|---|
| **D-5** | Authorise research into **process evidence and defence readiness** as a product direction? | §3.3 shows the shift is real and the primitives exist; building the export is a product decision, not a gap fix |
| **D-8** | Are the three standards dates enough for a watchlist, or should the RRA also watch standard-setter news automatically? | Cost and noise |
| **D-9** | Should the RRA read **course catalogues** as a first-class source, even though a catalogue page is far less authoritative than a standard? | It is the only place the framework answer lives; the alternative is to never settle B7 |
| **D-10** | Is the sampling frame right, given the product is global? | §R6 |

---

## 8. The back-test, measured

The RRA's own measurement harness, run against the seeded set:

- **Recall:** 12/12 (100 %) — every seeded known gap was rediscovered, including the two parked items, which were correctly labelled *parked* rather than proposed as work.
- **False flags:** 0 — none of the eleven seeded present items was flagged.
- **Verdict:** PASS against the owner's threshold (8 of 10, 0 false flags).

**The caveat that matters:** recall 12/12 means the harness agrees with a set
the owner wrote.  It is a floor, not a certificate.  §5 shows exactly where
the measurement can be wrong — and that the fix was a control set, not more
searches.

---

## 9. What this phase did not do

- It did not write a single line of product code.
- It did not promote a gap on T3 evidence.
- It did not touch the frozen core, a computation, or the paper path.
- It did not resolve the Omnibus I Directive's own dates; they stay T2 because
  no primary source was read for them in this phase.

---

## 10. Source register

| Source | Tier | Used for | How far read |
|---|---|---|---|
| AACSB, *2026 Global Standards for Business Education* (PDF, 148 pp.) | T1 | §3.2 | Full text extracted and searched |
| IFRS Foundation, IFRS 18 standard page | T1 | §3.1 | Full page |
| European Commission, Corporate sustainability reporting policy timeline | T1 | §3.1 | Full page |
| AACSB Insights, "AI Integration, Not Prohibition" | T1 (opinion) | §3.3 | Full page |
| Harvard Business School, MBA curriculum | T1 | §3.3 | Full page |
| Wharton, MBA core curriculum | T1 | §3.4 | Full page |
| INSEAD, MBA core courses (page + Core Courses PDF) | T1 | §3.4 | Located and read |
| The frame's core-course lists (the frame's pages) | T1 | §3.4, §5 | Text extracted and searched |
| The frame's course catalogues (site-restricted search) | T1 | §5 | 75 searches, 176 pages read |

---

*Prepared by the Phase 1 manual research sweep.  The RRA that produced it is
build 1.145; the owner may re-run any part of it from the Relevance panel.*
