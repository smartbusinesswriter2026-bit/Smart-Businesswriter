# Parked work — the frontier-model queue

**Status: PARKED by owner instruction (2026-10-21).** These are computation items deliberately not built yet. They are listed so no incoming model mistakes them for gaps nobody noticed, and so the work can resume without re-deriving the plan.

**Un-park rule.** Start an item from this file **only** after the owner explicitly says the DeepSeek Pro credits are available (or explicitly reassigns the item to another capable model). "The owner said continue" does not un-park this queue; the trigger is the owner granting the frontier-model budget. When un-parked, each item follows the normal discipline in [`CONTRIBUTORS.md`](CONTRIBUTORS.md) §3: implementation, independent second route, wrong-implementation traps, offline goldens, `Method(...)` contract, sandbox case, preset, a `B-xxx` decision for any convention chosen, tests, docs, one commit.

**Why these five.** Each remaining statistics item needs one of: (a) a distributions routine the standard library does not have, (b) a contested modelling convention that must be declared and defended, or (c) a labelled evaluation set that does not exist yet. The earlier, cheaper items were completed and are **not** parked: `paired_t`, `one_sample_t`, `two_way_anova` (balanced), `posthoc_pairwise`, `logistic_regression`, `reliability_alpha` all shipped (B-067, B-070, B-074).

**Offline oracles already installed for these items** (fixture generation only — never imported by `src/`): scikit-learn (clustering), `factor_analyzer` (factor analysis), statsmodels (`AnovaRM` for repeated measures), scipy (`studentized_range`, `dunnett` for the range procedures).

## The queue, in un-park order

| # | Item | Tier | Why it is parked | Oracle | Output that would be accepted |
|---|---|---|---|---|---|
| 1 | **Tukey HSD / Dunnett / Games-Howell** range procedures | T1 | Needs the studentized-range distribution `q(p, k, df)` and, for Dunnett, the multivariate-t probability; neither is in the standard library. Implementing them means numerical integration that must itself be verified, and the design must declare equal-vs-unequal n, one- vs two-sided, and the family definition for the existing `posthoc_pairwise` correction | `scipy.stats.studentized_range`, `scipy.stats.dunnett` | `tukey_hsd`, `dunnett_test`, `games_howell` as T1 methods: pairwise differences with simultaneous CIs and adjusted p-values; five frozen checks each (independent integration route, p ∈ (0,1), CI width monotone in confidence, wrong-impl trap, balanced-case agreement with the existing Welch+Holm path) |
| 2 | **Unbalanced two-way ANOVA, ANCOVA, three-way** | T1 | The sums-of-squares convention is contested: Type II vs Type III (and Type I ordering) changes every F and p on unbalanced data, and the product currently refuses unbalanced designs rather than pick one silently (B-070). This needs an owner-visible declared convention, not a code default | Hand-computed Type III via statsmodels/`car` offline | Extend `two_way_anova` to unbalanced data behind a declared SS type, plus `ancova`; goldens for both conventions (they differ), refusal when a convention is not declared, the balanced case must reproduce the current B-070 numbers exactly |
| 3 | **k-means clustering (segmentation)** | T2 | No single correct segmentation: K, seeding, convergence tolerance and the evaluation criterion are conventions. Needs a labelled evaluation set and a declared K-selection rule, and is T2 by the gap map | `sklearn.cluster.KMeans` | `kmeans_cluster` T2: deterministic seeded k-means++ with declared iterations/tolerance, within-cluster SS, silhouette, cluster profiles; five frozen checks (independent assignment step, point-order invariance, objective non-increasing, silhouette permutation-invariance, refusals for K > n / empty clusters); every claim ceiling T2 |
| 4 | **Exploratory factor analysis** | T1/T2 | Extraction (principal axis vs principal components), rotation (varimax/oblimin) and factor-count rules are all conventions the manual requires to be declared ([§9B.4](sources/business_pipeline_v0_3.md#L377)). Rotation convergence and sign/order conventions need care | `factor_analyzer` | `factor_analysis` with declared extraction/rotation/factor-count defaults, loadings, communalities, variance explained, KMO/Bartlett reported as diagnostics only; five frozen checks (reproduced-correlation error bound, rotation preserves communalities, loading sign/order canonicalisation, KMO against oracle, refusal on singular/singular-adjacent matrices) |
| 5 | **Repeated-measures ANOVA (incl. sphericity handling)** | T1 | Needs a within-subject design convention, listwise deletion disclosure, and a sphericity decision (report ε and a Greenhouse-Geisser corrected p, or refuse). The incomplete-gamma function for the corrected p is standard-library implementable but must be verified independently | `statsmodels.stats.anova.AnovaRM` | `repeated_measures_anova`: within-subject F, partial η², Mauchly/ε and a declared correction; five frozen checks (second route, F = MS_effect/MS_error identity, ε ∈ (0,1], corrected p ≥ uncorrected p, refusal for unbalanced subject lists) |
| 6 | **Non-linear time series** — seasonality, backtesting, break detection | T2 | The manual flags this as the highest statistical risk because it sits under the §8 regime-change controls ([§9B.2](sources/business_pipeline_v0_3.md#L345)). Decomposition model (additive vs multiplicative), holdout scheme and break-test threshold are all conventions that must be declared before any number is produced | statsmodels (seasonal_decompose, ARIMA, CUSUM/Chow) | Declared-model forecasting family: seasonality decomposition, rolling-origin backtest with declared metrics, break detection with a declared critical-value source. Explicitly **not** an "ARIMA because it fits" feature: the convention is chosen and stated first |

## Also waiting, but *not* frontier-model work

These are listed here only so a reader does not park them by mistake — they are blocked on owner decisions or on external sources, and their homes are [`HANDOFF.md`](HANDOFF.md) §4/§5 and [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md):

- **Imputation / complex-design inference** — needs an owner-declared model (recommended default: none; keep the extreme-case bounds only). Not a difficulty problem.
- **Standards / filings / tax retrieval** — needs the owner to name sources, jurisdictions and licensing (B-052 deferred).
- **PDF/scan/OCR/SPSS ingestion** — explicitly refused by design (B-065); would need a declared extraction step plus human confirmation of unverified text.
- **Breadth templates** — gated on B-028 (next templates) and B-005 (reviewers for any promotion).
- **REW stages R0–R8** — gated on ratifying R1–R10.

## When the queue resumes

1. Owner grants frontier-model budget and names the items (or says "the queue").
2. Take them in the table order above unless the owner reorders; one item per commit.
3. For items 1, 2 and 5 the **first** artefact is the decision entry that fixes the convention (distribution/SS type/sphericity rule), reviewed before code.
4. Update the gap map rows, `KNOWN_LIMITATIONS.md`, `CHANGELOG.md` and `WORKLOG.md` in the same commit; remove the item from this file and note where it went.
