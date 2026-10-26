# Stage 5 completion report (first increment)
**Status: PARTIAL.** The method contract, registry behaviour and one new method (descriptive statistics) are done and tested. The wider library (correlation, regression, forecasting, more scenarios) is not built.

## Sources used
Manual v0.3 (the supplied .md rendering; the .docx was not in the upload): 2 (P1-P10), 4, 5.1-5.8, 6, 7, 9B.1-9B.4, 14 (statistics validation), 16-18, App. A and B. Stage 5 Brief v0.1. Catalogue v0.2 (confirms descriptive statistics, NPV, break-even as candidates; nothing from it implemented as a framework).

## Audit and baseline
Repository: Stage 0-2 slice (v0.2). Baseline `python -m unittest discover -s tests`: 28 tests, OK, before any Stage 5 change.
Existing methods: NPV, break-even (T1, tested, single output).

## Gap register (implementation vs v0.3)
| Gap | Action |
|---|---|
| Spec lacked Appendix A fields (decision_context, checks, data_manifest, user_values, framework) | Added; checks are frozen into the spec |
| Artifact lacked env_hash, method version, run id, timestamp (App. B) | Added |
| Method had no contract (schema, defaults, limits, review status) | Added; `describe()` and `/api/methods` discover without executing |
| Inputs not schema-validated; bad input crashed or was coerced | Validated first, actionable errors, floats rejected, JSON floats parsed as Decimal |
| Single-output only | Multi-output methods supported (one artifact per output) |
| Missing-value codes (5.1, 9B) | Implemented for descriptive statistics; codes never read as values |
| T1 label with no named reviewer (5.3) | Label kept, review status disclosed ("expert review pending") and logged as B-005 |
| 5.4 sandbox, pinned env, no network | NOT done. env_hash is a placeholder for the real pinned-environment hash |
| 9B.3 pre-declared fallbacks, effect sizes, intervals, multiplicity | Not needed for descriptive; required before any inferential method |
| 9B.5 golden sets from NIST/SPSS | Hand-verified fixtures only; NIST/SPSS references not generated [OPEN] |

## What was built
- Method contract on every method (version, category, status, review status, intended and unsupported use, input schema, defaults register entries, assumptions, limitations, planned checks).
- Descriptive statistics for one numeric variable: n, missing count, mean, median, min, max, sample variance and SD. Defaults are in the ambiguity register. Small-sample wording and synthetic-data labelling are applied by code.
- Verification: independent float implementation (statistics module) vs the Decimal implementation; shift, scale and permutation (metamorphic) checks; missing entries never valued; order-statistic bounds. Names are frozen before execution.

## Tests
`python -m unittest discover -s tests`: 44 tests, OK (28 baseline + 16 new). Covers golden cases (5), manual-14 statistics traps (user-missing code, small sample), invalid inputs, wrongly implemented methods blocked (population SD, codes-as-values, offset mean), repair with tests frozen, discovery not executing, end-to-end via the API.
Not tested: any browser rendering of the UI; concurrency; large datasets; a real sandbox.

## Exit gate (Brief s8)
1. Priority method end-to-end in the repo: yes (NPV, break-even, plus descriptive statistics).
2. Numbers only from artifacts with type and provenance metadata: yes. Provenance tags in the spec are user-declared, not verified.
3. Frozen tests and specs enforced, failures logged, mandatory failures block: yes.
4. Tier and status accurate: partly. T1 is kept with disclosed pending review; owner decision B-005.
5. Honest reporting: this document.
6. Docs updated: DECISIONS, KNOWN_LIMITATIONS, CHANGELOG, this report.

## Next step
Owner decisions below, then correlation (with the 9B.3 machinery: declared assumption checks, fallback as a logged amendment, interval and effect size), then regression with diagnostics.

---
# Increment 2: correlation with pre-declared fallback (2026-10-20)
**Status: PARTIAL (library still incomplete).** Added Pearson and Spearman correlation, the first inferential methods, with the v0.3 9B.3 machinery.

## What was built
- **Pearson** (primary) and **Spearman** (fallback): r or rho, r-squared (Pearson), confidence interval, two-sided p-value, n pairs, n excluded, confidence level and alpha. Effect size is the coefficient; its wording comes from declared thresholds.
- **Pre-declared assumption check:** a normality screen (skewness and excess kurtosis limits) runs before results. The check, its limits and the fallback are written into the frozen spec. On failure the run switches to Spearman as a **logged amendment**, disclosed in the report and appendix, never silently.
- **Wording:** claim ceiling "associational". Reports state significance and practical importance separately, a small-sample caution, and that no causal claim is made. Causal verbs are blocked.
- **Data problems block with a reason:** unpaired lengths, a constant variable, fewer than four complete pairs, perfect correlation (interval undefined).
- **Missing data:** pairs with a blank, null or declared missing code are excluded and counted.

## Verification
Independent second routes: statistics.correlation (float) for the coefficient; numerical integration of the t density for the p-value; a bisection for the normal quantile; a counting-based ranker for Spearman. Properties: positive linear transform invariance (Pearson), monotone transform invariance (Spearman), sign flip, x/y symmetry, bounds, missing pairs not valued. Golden fixtures were generated offline with scipy 1.17.1 (manual 9B.5, reference generation is offline) plus hand-checked cases (r = 6/sqrt(60); rho = 0.9). Scipy is not needed to run the tests.

## Tests
`python -m unittest discover -s tests`: **65 tests, OK** (44 before this increment). Includes five deliberately wrong Pearson implementations and a Spearman ranking bug, all blocked.
Not tested: Spearman interval accuracy against an independent reference; behaviour on large samples; real survey data; the UI in a browser.

## Open items
- Skew limit 2, kurtosis limit 7, effect cut-offs 0.1/0.3/0.5, small-sample 30: placeholders from memory [UNVERIFIED], declared in the spec so they are visible and overridable.
- Spearman interval (Bonett-Wright) is [UNVERIFIED]; scipy gives no interval to compare.
- Linearity, independence, clustering and weights are not checked (limitations are shown in the plan).
- Power is not computed; precision is conveyed by the interval only.
- Variable names are not shown in generated text (digit and injection guard); the report says "the two variables".

---
# Increment 3: linear regression with diagnostics (2026-10-20)
**Status: PARTIAL (library still incomplete).** OLS (up to five numeric predictors) and an HC3 robust fallback.

## What was built
- **OLS** (`ols`): coefficients, standard errors, p-values and confidence intervals for the intercept and each predictor; R-squared, adjusted R-squared, f-squared effect size, standardized coefficients, residual SE, F test.
- **Four pre-declared diagnostics, run before results, thresholds frozen in the spec:** residual normality (skewness, kurtosis), heteroskedasticity (F-form Breusch-Pagan), multicollinearity (largest VIF), influence (largest Cook's distance).
- **Fail-closed rule:** heteroskedasticity switches to `ols_robust` (HC3 standard errors) as a logged amendment, disclosed in the report. Normality, multicollinearity and influence failures **block**, and the message names the check and the measured value. No fallback was declared for them.
- **Wording:** associational only. Reports use "associated with a difference of ... holding the other predictors constant", state that no causal claim is made, and name the omitted-variable risk. Causal verbs are blocked.
- **Predictor names** appear in the report. They are limited to letters and underscores (no digits, spaces or markup) so they cannot carry numbers or injected text; "intercept" is reserved.
- Negative non-currency numbers now print with a minus sign (parentheses stay for currency, per manual 9.5).

## Verification
Independent second route: modified Gram-Schmidt QR in floats with a series-based incomplete beta (different algorithms from the Decimal normal-equations fit and continued-fraction beta). Properties: predictor shift changes the intercept only; rescaling rescales coefficients but not significance; row-order invariance; incomplete rows not valued; bounds and consistency; a cross-check (simple regression equals Pearson; multiple regression matches a partial-regression calculation). Golden fixtures were generated offline with numpy 2.4 and scipy 1.17 and agree to about 1e-14. A hand-checked case (slope 0.6, intercept 2.2, R-squared 0.6) is exact.

## Tests
`python -m unittest discover -s tests`: **87 tests, OK** (65 before this increment). Includes eight deliberately wrong OLS versions and a robust version that returns classical errors; all blocked. Trap data: heteroskedastic (fallback), collinear, influential point, skewed residuals (each blocked or switched as designed).
Not tested: large samples; rank-deficient edge cases beyond exact collinearity; the UI in a browser; any real student dataset.

## Open items
- Every diagnostic limit (2, 7, 0.05, 10, 1) and the f-squared cut-offs (0.02, 0.15, 0.35) are conventions from memory [UNVERIFIED], declared and overridable. The F-form Breusch-Pagan is also unverified against a published reference.
- Blocking on normality, collinearity and influence is my reading of fail-closed (P8); it may over-block student data. Owner decision B-013.
- No categorical predictors, interactions, transformations, weights, clustering, or time series. No power calculation. HC3 intervals use t critical values (approximate in small samples).

---
# Increment 4: two-group comparison (2026-10-21)
**Status: PARTIAL (library still incomplete).** Welch t-test with a pre-declared Mann-Whitney fallback.

## What was built
- **Welch t-test** (`welch_t`): means, SDs and n per group, difference in means with interval, t, Welch degrees of freedom, two-sided p-value, Hedges' g with a large-sample interval. Group sizes may differ; exactly two groups, named with letters and underscores.
- **Pre-declared screen:** each group's skewness and excess kurtosis against declared limits. A failure switches to **Mann-Whitney** (`mann_whitney`) as a logged, disclosed amendment, with the fallback and its tests frozen in the spec first.
- **Mann-Whitney:** U, tie- and continuity-corrected asymptotic p-value, rank-biserial correlation, Hodges-Lehmann shift with an interval obtained by inverting the test. It needs roughly four or more observations per group for a bounded interval; smaller groups block with that reason.
- Wording: associational ceiling; the report says group differences do not show that group membership produces them, and makes no causal claim.

## Verification
Independent second routes: float arithmetic with the statistics module and a series-based incomplete beta for Welch; rank-sum U with a counting ranker and the normal CDF for Mann-Whitney. Properties: shift, scale, group swap, row order, missing entries, monotone transforms, identical samples, bounds, and a check that the interval endpoints are where the test's p-value crosses alpha. Golden fixtures generated offline with numpy 2.4 and scipy 1.17 agree to about 1e-15; hand-checked: Welch t = -3/sqrt(2.5), df = 6.25/1.0625; U = 20 and rank-biserial 0.6.

## Tests
`python -m unittest discover -s tests`: **106 tests, OK** (87 before). Includes seven deliberately wrong Welch versions (Student pooled t instead of Welch, small SE, one-sided p, uncorrected g, sign flip, missing codes read as values, a magnitude-dependent bug) and four wrong Mann-Whitney versions; all blocked.
**Defect found and fixed during this increment:** the frozen consistency check wrongly rejected valid data because Welch degrees of freedom can equal the upper bound to within rounding; I added a 1e-9 tolerance. This was a verifier-side tolerance bug in the build, not a change made at runtime.

## Open items
- Skew/kurtosis limits, Cohen-style cut-offs (g 0.2/0.5/0.8; rank-biserial reuses 0.1/0.3/0.5) are conventions from memory [UNVERIFIED], declared and overridable.
- The Hodges-Lehmann interval method, and the large-sample Hedges' g interval, are not checked against a published reference [UNVERIFIED]. scipy provides neither.
- No paired designs, more than two groups, proportions, or exact small-sample tests.

---
# Increment 5: sandbox, pinned environment and re-performance (2026-10-21)
**Status: PARTIAL.** Meets manual 5.4 for vetted T1 code on Linux; not a container.

## What was built
- **Sandboxed execution** (`sandbox.py`, `sandbox_child.py`): assumption checks, verification, execution and decision-flip run in a separate Python process (`-S -s`, minimal environment, `PYTHONHASHSEED=0`, fixed seed). The child blocks network and name resolution, process spawning, and writes outside its temporary work directory. A timeout kills runaway processes. A memory cap applies on POSIX. Any sandbox failure **blocks** delivery (fail closed).
- **Pinned environment** (`envpin.py`): the environment hash now covers the interpreter, platform and a hash of the bp source files themselves, recorded on every artifact. It lists no third-party packages because none are used.
- **Re-performance** (`reperform.py`, manual P9): every delivery includes a bundle (method, version, inputs, outputs, environment). `python -m bp.reperform bundle.json` re-runs it in a fresh sandbox and reports exact, within-tolerance or mismatched outputs, and any environment difference. The workbench has a download button for the bundle.
- The server runs with the sandbox ON by default (`--no-sandbox` for development only). The appendix states how each run executed.

## Tests
`python -m unittest discover -s tests`: **125 tests, OK** (106 before). Sandbox tests: escape probes (network, DNS, a real local listener, writes outside the work directory, os.system, subprocess) all blocked, writes inside allowed; timeout kill; policy report; sandbox outputs identical to in-process for all nine methods; identical results across separate processes; identical reports with and without the sandbox; fallbacks and blocks through the sandbox; unavailable or timed-out sandbox blocks; tampered outputs, tampered inputs and unknown methods detected by re-performance; command-line tool exit codes; full HTTP flow with the sandbox.
**Not tested:** Windows, macOS, memory-limit enforcement, any hostile code beyond the listed probes, the UI download button in a browser.

## What this does not claim
It is process isolation plus policy guards for **our own vetted code**. It is not a security boundary: model-written code (T2/T3) must wait for an OS-level container (for example Docker with no network, a read-only filesystem and resource limits). That decision, and the Windows deployment path, need the owner.

---
# Increment 6: ANOVA, Kruskal-Wallis and chi-square (2026-10-21)
**Status: PARTIAL (library still incomplete).** Owner-requested: one-way ANOVA with a pre-declared Kruskal-Wallis fallback, and a chi-square test of independence.

## What was built
- **One-way ANOVA** (`anova`, three or more groups): F statistic, between/within degrees of freedom, two-sided p-value, eta-squared effect size, grand mean, and per-group n, mean and SD. Missing entries are excluded and counted.
- **Pre-declared screens and fallback:** per-group skewness/kurtosis against declared limits and Levene's test (mean version) for equal variances at a declared level. Either failure switches to **Kruskal-Wallis** (`kruskal_wallis`) as a logged, disclosed amendment; both checks and the fallback are frozen in the spec.
- **Kruskal-Wallis:** average ranks for ties, tie-corrected H, chi-square-approximation p-value, epsilon-squared effect size, per-group n and median.
- **Chi-square test of independence** (`chi_square`) on a table of non-negative whole counts: chi-squared, df, p-value, Cramer's V, smallest expected count. A screen requires every expected count to be at least the declared floor (5); if not, the analysis **blocks fail-closed** (no fallback declared, per the B-013 pattern). Zero row/column totals and empty tables block.
- Wording: associational ceiling everywhere; the reports state that group differences / association do not show causation.

## Verification
Independent second routes: float recomputation with the series incomplete beta for the F p-value; counting-based ranks plus an exact integer-degree-of-freedom closed form (Poisson sum for even df, erfc series for odd df) for the chi-square survival, against the primary incomplete-gamma (NR series + continued fraction) route. Properties: within-group permutation, group relabeling, equal shift, positive scale, monotone transforms, missing exclusion, transpose and row-order invariance, uniform count scaling, independence giving chi-squared zero, and bounds. Golden fixtures generated offline with scipy 1.18.1 (f_oneway, kruskal, chi2_contingency); the two chi-square survival routes agree with scipy to about 4e-15. Deliberately wrong implementations (one-sided p, wrong df, inverted eta-squared, squared F, uncorrected p, doubled H, negative epsilon, V without the square root, wrong df) are all blocked.

## Tests
`python -m unittest discover -s tests`: **307 tests, OK** (278 before this increment; 29 new, plus the sandbox parity set extended to the three new methods).
Not tested: post-hoc pairwise tests, repeated-measures or factorial designs, Fisher's exact or Yates corrections, very large tables, real survey data.

## Open items
- All conventions are placeholders [UNVERIFIED], declared and overridable: skew/kurtosis limits 2/7, Levene level 0.05, eta/epsilon cut-offs 0.01/0.06/0.14, Cramer's V cut-offs 0.1/0.3/0.5, expected-count floor 5 (B-042).
- Blocking on small expected counts is fail-closed (P8); a Fisher-exact fallback for small tables is future work.
- No post-hoc tests, no Welch ANOVA (equal-variance failures fall back to Kruskal-Wallis instead), no goodness-of-fit chi-square.

---
# Increment 7: linear-trend forecasting with an out-of-sample check (2026-10-21)
**Status: PARTIAL (library still incomplete).** Owner-requested forecasting increment.

## What was built
- **`trend_forecast`**: fits a linear trend in time (t = 1..n) by least squares and forecasts a user-chosen horizon (1-12 periods, default 3) with classical prediction intervals at the declared confidence level. Outputs: intercept, slope, R-squared, residual SE, slope p-value, per-period forecasts and intervals, and fit/missing counts.
- **Out-of-sample check, disclosed not gating:** the last m periods (m = max(1, min(3, n/4))) are held out, the trend is refit on the rest, and the mean absolute error and the fraction of held-out values inside the prediction intervals are reported as artifacts and in the report.
- **Missing values keep their position in time** and are excluded from the fit (never filled in). Constant series and fewer than six valid observations block. A perfect fit blocks for the main trend (inference undefined) but the holdout tolerates it (its intervals degenerate to the fitted line).
- Claim ceiling: **predictive** (no causal or intervention wording); the report states that the forecast projects the past pattern forward, assumes the trend continues, and gets less reliable further ahead.

## Verification
Independent second route: float QR fit with the series incomplete beta for the p-value and critical value. Properties: shift moves the intercept and forecasts but not the slope or p-value; positive scale equivariance; bounds; and an independent float recomputation of the holdout error and coverage. Golden fixtures generated offline with numpy 2.5.3 + scipy 1.18.1 (linregress, t.ppf); the implementation agrees to about 4e-15. Deliberately wrong implementations (flat forecast, narrowed interval, negative MAE, coverage above one, flipped slope) are blocked.

## Tests
`python -m unittest discover -s tests`: **320 tests, OK** (307 before; 13 new). Sandbox parity set extended to the new method.
Not tested: seasonal or non-linear series, multiple series, long horizons, real business data.

## Open items
- The holdout-size rule (a quarter of the series, capped at 3), the minimum series length (6) and the horizon cap (12) are placeholders (B-043).
- No seasonality, cycles, external drivers or structural-break handling; no exponential smoothing or ARIMA.
- Prediction intervals assume independent, roughly normal errors around the trend.
