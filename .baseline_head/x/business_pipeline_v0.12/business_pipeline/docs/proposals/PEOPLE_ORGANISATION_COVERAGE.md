# People & organisation — coverage report and decisions

**Status:** DRAFT for owner review. Not authority: it records what the code does
today and what the catalogue says, and it asks for decisions where the two do not
agree. It decides nothing and cites no decision id.

**Scope:** the People & organisation subject (`people`) in the subject shelf, the
`people and learning` and `change and organization` catalogue disciplines it
carries, and the seventeen People computations the candidate list names.

**How to read it:** every row is taken from the code (`bp.product.subjects`,
`bp.product.framework_profiles`, `bp.templates`, `bp.registry`, `bp.methods`) or
from the committed catalogue slice, never from memory. Where the frozen core has
no method, the row says **absent** and the unfreeze request
(`PEOPLE_COMPUTATION_UNFREEZE.md`) names what would be needed.

---

## 1. Frameworks

The People shelf had **no worksheets at all** before this build. It showed the
catalogue entries as reading material and no way to complete one. Eight
frameworks now complete from a brief.

| Id | Framework | Before | Now | Parts | Tile |
|---|---|---|---|---|---|
| PPL-03 | Job Characteristics Model | catalogue-only record | **worksheet** — `template_job_characteristics` | 5 | Resourcing |
| PPL-02 | Kirkpatrick Training Evaluation Model | catalogue-only record | **worksheet** — `template_kirkpatrick` | 4 | Development |
| PPL-01 | AMO Framework | catalogue-only record | **worksheet** — `template_amo` | 3 | Engagement and culture |
| PPL-05 | Team development review using Tuckman's stages | catalogue-only record | **worksheet** — `template_tuckman` | 5 | Development |
| PPL-04 | Nine-Box Talent Grid | catalogue-only record | **worksheet** — `template_nine_box` | 4 | Resourcing |
| CHG-01 | Kotter's 8-Step Change Model | catalogue-only record | **worksheet** — `template_kotter` | 8 | Strategy and design |
| CHG-12 | Competing Values Framework | catalogue-only record | **worksheet** — `template_competing_values` | 4 | Engagement and culture |
| CHG-11 | Organizational Design: Star/fit review | catalogue-only record | **worksheet** — `template_org_design` | 6 | Strategy and design |
| THE-02 | Maslow, Herzberg, McClelland, expectancy, equity and self-determination theory | not on the People shelf | **reading lens** — added to the shelf | – | Reading lenses |

Each of the eight is a T4 structure-and-evidence worksheet on its own canvas: a
profile in `framework_profiles.py`, a template in `templates.py`, a
`TEMPLATE_LINKS` entry in `registry.py`, a drafting schema in `drafting.py`, and
a `WORKSHEETS` entry marked draftable. Every part is a `research` block: the
pipeline retrieves what a source can support, and where nothing is found it
writes the framework's own general background paragraph as an uncited item, so a
part is never a notice, never a blank and never a gate.

## 2. Computations

Ten calculators sit on the People shelf. Seven were already there; three are new
and each one runs an existing frozen method with its own preset. No number is
computed in the product layer.

| Tool | Frozen method | Preset | Period badge | Tier | Status |
|---|---|---|---|---|---|
| Reliability (Cronbach's alpha) | `reliability_alpha` | `alpha` | per observation | T1 | was on the shelf |
| Weighted summary | `weighted_summary` | `weighted` | per observation | T1 | was on the shelf; study notes added |
| Descriptive statistics | `descriptive_stats` | `descriptive` | per observation | T1 | was on the shelf |
| Chi-square association | `chi_square` | `chi_square` | per observation | T1 | was on the shelf |
| Power and sample size | `power_analysis` | `power` | per observation | T1 | was on the shelf |
| Pearson correlation | `pearson` | `pearson` | per observation | T1 | was on the shelf |
| Linear regression | `ols` | `ols` | per observation | T1 | was on the shelf |
| **Training ROI** | `return_on_investment` | `roi` | per period | T1 | **new** — training spend and training gain |
| **Labour market tightness** | `labour_market` | `labour` | annual | T1 | **new** — real wage, wage share, market tightness |
| **People programme cost-effectiveness** | `cost_effectiveness` | `cea` | annual | T2 | **new** — cost per unit of effect against a declared comparator |

## 3. Catalogue-only and absent

### 3a. Frameworks that are catalogued but have no worksheet

These are shown in the People tiles as something to read and cite, never as a
button that cannot work. Each row is a decision, not an oversight.

| Id | Framework | Tile | Why there is no worksheet | Decision needed |
|---|---|---|---|---|
| CHG-02 | ADKAR | Development | catalogued, no canvas | build, or leave as reading material |
| CHG-03 | Lewin's Three-Stage Model | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-04 | McKinsey 7-S | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-05 | Burke–Litwin Organizational Performance and Change Model | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-06 | Galbraith Star Model | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-07 | Theory of Change | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-08 | Logic Model | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-09 | Plan–Do–Study–Act (PDSA) | Development | catalogued, no canvas | a PDCA canvas already exists on the Operations shelf under a different record (`OPS-12`); link it here, or leave it |
| CHG-10 | DMAIC | Development | catalogued, no canvas | build, or leave as reading material |
| CHG-13 | Mintzberg Organizational Configurations | Strategy and design | catalogued, no canvas | build, or leave as reading material |
| CHG-14 | RACI responsibility matrix | Resourcing | catalogued; a matrix canvas exists on the Project Management shelf under `PM-10` | link it here, or leave it |

### 3b. Candidate frameworks that the catalogue does not hold at all

The candidate list names these for People & organisation. **None of them is a
catalogue record**, so none of them can be added without a catalogue decision
first. The shelf does not invent them.

| Candidate | Catalogue status | Nearest catalogue record | Decision needed |
|---|---|---|---|
| HR strategy and workforce planning | not catalogued | – | add a record, or drop |
| Job analysis and job design (Hackman) | catalogued | PPL-03 | built as a worksheet |
| Recruitment and selection | not catalogued | – | add a record, or drop |
| Onboarding | not catalogued | – | add a record, or drop |
| Training and development / training needs analysis | catalogued | PPL-02 | built as a worksheet |
| Performance management (appraisal) | not catalogued | – | add a record, or drop |
| 360 feedback | not catalogued | – | add a record, or drop |
| Competency model | not catalogued | – | add a record, or drop |
| Reward and job evaluation | not catalogued | – | add a record, or drop — this is why the Reward tile is empty |
| Motivation (Herzberg / Maslow) | reading lens only | THE-02 | carried as a reading lens |
| Team roles (Belbin) | not catalogued | – | add a record, or drop |
| Team development (Tuckman) | catalogued | PPL-05 | built as a worksheet |
| Leadership styles | not catalogued | – | add a record, or drop |
| Organisational culture (Schein / Competing Values) | catalogued (partly) | CHG-12 | built as a worksheet; Schein himself is not catalogued |
| Change management (Kotter) | catalogued | CHG-01 | built as a worksheet |
| Stakeholder analysis | catalogued, other shelf | `PM-15` | the RACI/stakeholder canvas lives on Project Management |
| Nine-box talent grid | catalogued | PPL-04 | built as a worksheet |
| Engagement and eNPS | not catalogued as a framework | – | add a record, or drop |
| Succession planning | not catalogued | – | add a record, or drop |
| Diversity and inclusion | not catalogued | – | add a record, or drop |
| Organisational design and span of control | catalogued (partly) | CHG-11, CHG-06 | CHG-11 built; span of control is a metric, not a framework |
| Conflict and negotiation (Thomas–Kilmann) | not catalogued | – | add a record, or drop |
| Coaching | not catalogued | – | add a record, or drop |
| Employer brand and EVP | not catalogued | – | add a record, or drop |

### 3c. Candidate computations the frozen core does not implement

Fifteen of the seventeen candidate People computations have **no** method in
`bp.methods.LIBRARY`. A similar method is not a substitute for a missing one, so
each is named as absent and carried in the unfreeze request.

| Candidate | Nearest frozen method | Verdict |
|---|---|---|
| Headcount and FTE | `descriptive_stats` (one value per person) | **absent** — no total FTE, no headcount method |
| Turnover and retention | `cohort_retention` (customer cohorts) | **absent** — that method's declared subject is customers |
| Absenteeism | – | **absent** |
| Cost per hire | `unit_economics` (customer acquisition) | **absent** |
| Time to hire | – | **absent** |
| Training cost and ROI | `return_on_investment` | **delivered** — `trainingroi`; the cost is the declared investment |
| Compa-ratio and salary range penetration | – | **absent** |
| Span of control | – | **absent** |
| Revenue per employee | `ratio_analysis` (financial statements) | **absent** — that method takes statement lines, not people |
| Labour cost as % of revenue | `ratio_analysis` | **absent** |
| Overtime % | – | **absent** |
| Benefits cost | – | **absent** |
| Workforce gap and supply | `demand_supply_equilibrium` (a market model), `capacity_analysis` | **partly delivered** — `labourtightness` reads the *market*; the organisation's own gap is **absent** |
| Nine-box distribution | – | **absent** — the grid is a worksheet; the count is not computed |
| Engagement index and eNPS | `cohort_retention`, `social_engagement` | **absent** — both are declared for other subjects |
| Diversity ratio | `gini_coefficient` (income inequality) | **absent** |
| Job evaluation points | – | **absent** |

### 3d. The Reward tile

The tile exists because the candidate list names reward and job evaluation, and
the catalogue holds **neither**. The tile is shown empty and says so in the page:
a missing capability is named, not hidden and not faked.

## 4. Verdict

| Area | Verdict | Evidence |
|---|---|---|
| People frameworks | **8 built, 1 reading lens added** | `bp.product.framework_profiles` (28 profiles), `bp.templates` (45 templates), `bp.registry.TEMPLATE_LINKS` |
| People computations | **3 added, all on frozen methods with presets** | `return_on_investment`, `labour_market`, `cost_effectiveness`; live-delivered through `/api/sessions` |
| Frameworks with no worksheet | **11 catalogued, all shown as read-and-cite** | the People tiles; none carries a dead button |
| Frameworks not in the catalogue | **15 candidates, none invented** | every candidate is named in §3b |
| Computations absent from the core | **15**, with an unfreeze request each | `PEOPLE_COMPUTATION_UNFREEZE.md` |
| The shelf's honesty | the page states the Reward tile is empty and names every metric it does not compute | `subjects.detail("people")["does_not"]` |

### Decisions the owner is asked for

1. **The Reward tile stays empty** until the catalogue gains a reward or
   job-evaluation record. Alternative: commission one record now.
2. **CHG-09 (PDSA) and CHG-14 (RACI)** already have canvases on other shelves
   under different record ids. Link them onto the People tiles, or leave People
   with a read-and-cite card.
3. **The eleven remaining change frameworks** stay reading material unless the
   owner wants canvases built for them.
4. **The fifteen absent People metrics** need the unfreeze request in
   `PEOPLE_COMPUTATION_UNFREEZE.md` before any of them can appear on the shelf.
5. **The candidate list's uncatalogued frameworks** need a catalogue decision
   before they can exist. None was added.
