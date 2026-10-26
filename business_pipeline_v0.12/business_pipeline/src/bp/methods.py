"""T1 method library with an explicit method contract (Stage 5 brief s6; manual 5.3, 5.5, 9B).
Discovery (describe/list) never executes a method. Inputs are schema-validated before anything runs."""
import statistics, re
from . import currency
from dataclasses import dataclass, field
from decimal import Decimal as D, InvalidOperation
from typing import Callable

TOL = D("1e-9")

class DataError(ValueError):
    """The data cannot support this method (e.g. a constant variable). Blocks with an actionable message."""

class InputError(ValueError):
    def __init__(self, errors): super().__init__("; ".join(errors)); self.errors = errors

@dataclass(frozen=True)
class Method:
    name: str; tier: str; impl: Callable; tests: Callable; profile: Callable
    metric: str; unit: str; decision: Callable | None = None; test_names: tuple = ()
    # --- contract fields (all defaulted so older constructions keep working) ---
    version: str = "1.0.0"; category: str = "decision"; status: str = "implemented_tested"
    review_status: str = "pending_named_reviewer"   # T1 label stays, but review is disclosed (manual 5.3 promotion rule)
    intended_use: str = ""; unsupported_use: str = ""
    input_schema: dict = field(default_factory=dict)
    defaults: tuple = (); assumptions: tuple = (); limitations: tuple = ()
    output_precision: dict = field(default_factory=dict)
    default_period: str = "annual"
    caveats: Callable | None = None
    template: Callable | None = None
    claim_ceiling: str = "descriptive"
    # --- inferential-method contract (manual 9B.3): pre-declared assumption checks, fallbacks, thresholds ---
    assumption_checks: Callable | None = None
    assumption_check_names: tuple = ()
    fallbacks: dict = field(default_factory=dict)      # failed check name -> fallback method id (written into the spec)
    default_thresholds: dict = field(default_factory=dict)
    output_units: dict = field(default_factory=dict)
    typing: Callable | None = None                     # metric -> (unit, precision) for dynamic output names
    mapping: Callable | None = None                    # account-mapping checkpoint: (inputs) -> {"rows": [...], "checks": [(name, ok, detail)]}
    mapping_check_names: tuple = ()

import hashlib, inspect
def sha_source(fn):
    try: return hashlib.sha256(inspect.getsource(fn).encode()).hexdigest()
    except (OSError, TypeError): return hashlib.sha256(getattr(fn, "__name__", "impl").encode()).hexdigest()

def decision_flip(m, impl, inp, lo, hi):
    """Rate at which the decision rule changes within [lo, hi], or None (manual 5.6)."""
    f = lambda r: m.decision(impl({**inp, "rate": r}))
    if f(lo) == f(hi): return None
    a, b = lo, hi
    for _ in range(80):
        mid = (a + b) / 2
        if f(mid) == f(a): a = mid
        else: b = mid
    return (a + b) / 2

# ---------- input validation ----------
def _num(x):
    if isinstance(x, bool) or isinstance(x, float): raise ValueError("pass numbers as strings, integers or exact decimals, not binary floats")
    d = D(str(x))
    if not d.is_finite(): raise ValueError("not a finite number")
    return d

def _check(key, v, spec):
    t, errs = spec["type"], []
    try:
        if t == "decimal": _num(v)
        elif t == "column_map":
            if not isinstance(v, dict) or not v: return [f"'{key}' must be an object of name -> list of values"]
            if len(v) < spec.get("min_columns", 1): errs.append(f"'{key}' needs at least {spec['min_columns']} columns")
            if len(v) > spec.get("max_columns", 99): errs.append(f"'{key}' allows at most {spec['max_columns']} columns")
            for name, col in v.items():
                if not re.fullmatch(r"[A-Za-z_]{1,30}", str(name)) or str(name).lower() == "intercept":
                    errs.append(f"'{key}' column name {name!r}: use 1-30 letters or underscores (no digits or spaces); 'intercept' is reserved")
                errs += _check(f"{key}.{name}", col, {"type": "value_list", "min_items": spec.get("min_items", 0)})
        elif t == "engagement_spec":
            from . import accounts
            if not isinstance(v, dict): return [f"'{key}' must be an object (the engagement spec)"]
            errs += [f"'{key}': {e}" for e in accounts.validate_spec(v)]
        elif t == "records":
            if not isinstance(v, list): return [f"'{key}' must be a list of records"]
            if len(v) < spec.get("min_items", 1): errs.append(f"'{key}' needs at least {spec['min_items']} records")
            fields = spec.get("fields", {})
            for i, rec in enumerate(v):
                if not isinstance(rec, dict): errs.append(f"'{key}'[{i}] must be an object"); continue
                extra = set(rec) - set(fields)
                if extra: errs.append(f"'{key}'[{i}] has unknown field(s): {sorted(extra)}")
                for f, ft in fields.items():
                    if f not in rec: errs.append(f"'{key}'[{i}] is missing '{f}'"); continue
                    if ft == "decimal":
                        try: _num(rec[f])
                        except (InvalidOperation, ValueError, TypeError): errs.append(f"'{key}'[{i}].{f} = {rec[f]!r}: not a number")
                    elif not isinstance(rec[f], str) or not rec[f].strip():
                        errs.append(f"'{key}'[{i}].{f} must be non-empty text")
        elif t == "currency":
            try: currency.minor_units(v)
            except currency.CurrencyError as e: errs.append(str(e))
        elif t == "text":
            if not isinstance(v, str): return [f"'{key}' must be text"]
            if spec.get("max_chars") and len(v) > spec["max_chars"]: errs.append(f"'{key}' must be at most {spec['max_chars']} characters")
        elif t == "enum":
            if not isinstance(v, str): return [f"'{key}' must be a string"]
            if v not in spec.get("values", []): errs.append(f"'{key}' must be one of: " + ", ".join(spec.get("values", [])))
        elif t == "count_table":
            if not isinstance(v, list) or not v: return [f"'{key}' must be a non-empty list of rows"]
            minr, maxr = spec.get("min_rows", 2), spec.get("max_rows", 99); minc, maxc = spec.get("min_cols", 2), spec.get("max_cols", 99)
            if len(v) < minr: errs.append(f"'{key}' needs at least {minr} rows")
            if len(v) > maxr: errs.append(f"'{key}' allows at most {maxr} rows")
            cols = len(v[0]) if v and isinstance(v[0], list) else 0
            if cols < minc: errs.append(f"'{key}' needs at least {minc} columns")
            if cols > maxc: errs.append(f"'{key}' allows at most {maxc} columns")
            for i, row in enumerate(v):
                if not isinstance(row, list) or (cols and len(row) != cols): errs.append(f"'{key}' row {i} must be a list of {cols} numbers")
                else:
                    for j, x in enumerate(row):
                        try:
                            d = _num(x)
                            if d < 0: errs.append(f"'{key}'[{i}][{j}] must be a non-negative count")
                            elif d != d.to_integral_value(): errs.append(f"'{key}'[{i}][{j}] must be a whole number")
                        except (InvalidOperation, ValueError, TypeError): errs.append(f"'{key}'[{i}][{j}] = {x!r}: not a number")
        elif t in ("decimal_list", "value_list", "code_list"):
            if not isinstance(v, list): return [f"'{key}' must be a list"]
            if len(v) < spec.get("min_items", 0): errs.append(f"'{key}' needs at least {spec['min_items']} items")
            for i, x in enumerate(v):
                if t == "value_list" and (x is None or (isinstance(x, str) and not x.strip())): continue
                try: _num(x)
                except (InvalidOperation, ValueError, TypeError) as e: errs.append(f"'{key}'[{i}] = {x!r}: {str(e) if isinstance(e, ValueError) else 'not a number'}")
    except (InvalidOperation, ValueError, TypeError) as e:
        errs.append(f"'{key}' = {v!r}: {str(e) if isinstance(e, ValueError) else 'not a valid number'}")
    return errs

# Inputs that name a data structure the method does NOT model. They are refused with a specific reason
# rather than a generic "unknown input", so a weighted or clustered dataset cannot be passed in and silently
# treated as independent observations (manual 9B.3; B-057).
_UNSUPPORTED_CONCEPTS = {"weights": "survey weights", "weight": "survey weights", "strata": "stratified sampling",
                         "cluster": "clustered observations", "clusters": "clustered observations", "repeated": "repeated measures",
                         "id": "a panel or subject identifier", "time": "time-series structure", "pair": "paired observations", "pairs": "paired observations"}

def validate_inputs(m, inp) -> list[str]:
    if not isinstance(inp, dict): return ["inputs must be an object"]
    errs, sch = [], m.input_schema
    if not sch: return errs
    for k in inp:
        if k in sch: continue
        concept = _UNSUPPORTED_CONCEPTS.get(str(k).lower())
        errs.append(f"'{k}' is refused: {concept} are not supported by {m.name}, which treats every observation as independent; "
                    "supply only the declared inputs or use a method that models the structure" if concept else f"unknown input '{k}'; allowed: {sorted(sch)}")
    for k, spec in sch.items():
        if k not in inp:
            if spec.get("required", True): errs.append(f"missing required input '{k}' ({spec['desc']})")
        else: errs += _check(k, inp[k], spec)
    return errs

# ---------- NPV ----------
def npv(inp):
    r = D(str(inp["rate"]))
    return sum((D(str(c)) / (1 + r) ** t for t, c in enumerate(inp["cashflows"])), D(0))

def npv_reference(inp):  # independent route: Horner / backward induction
    v = 1 / (1 + D(str(inp["rate"]))); acc = D(0)
    for c in reversed(inp["cashflows"]): acc = D(str(c)) + v * acc
    return acc

def npv_tests(inp, impl):
    cfs = [D(str(c)) for c in inp["cashflows"]]
    bumped = {**inp, "cashflows": [cfs[0] + 1] + cfs[1:]}
    zero = {**inp, "rate": "0"}
    return [
        ("second_implementation_agrees", abs(impl(inp) - npv_reference(inp)) <= TOL),
        ("boundary_zero_rate_equals_sum", abs(impl(zero) - sum(cfs)) <= TOL),
        ("t0_cash_flow_shifts_npv_one_for_one", abs(impl(bumped) - impl(inp) - 1) <= TOL),
    ]

def npv_profile(inp):
    issues = []
    if D(str(inp["rate"])) <= -1: issues.append("rate <= -100%")
    if len(inp["cashflows"]) < 2: issues.append("fewer than two periods")
    return issues

# ---------- Break-even ----------
def breakeven(inp):
    return D(str(inp["fixed"])) / (D(str(inp["price"])) - D(str(inp["variable"])))

def breakeven_tests(inp, impl):
    f, p, v = (D(str(inp[k])) for k in ("fixed", "price", "variable"))
    q = impl(inp); profit = q * (p - v) - f; higher = impl({**inp, "fixed": f + 1})
    return [("profit_at_breakeven_is_zero", abs(profit) <= TOL), ("monotone_in_fixed_cost", higher > q), ("positive_quantity", q > 0)]

def breakeven_profile(inp):
    return ["price <= variable cost: no break-even"] if D(str(inp["price"])) <= D(str(inp["variable"])) else []

# ---------- Paired and one-sample t-tests (manual 9B.2; B-067) ----------
# Paired: within-pair differences on matched observations, dropping a pair if either side is missing.
# One-sample: one mean against a declared reference value mu0. Both default to two-sided and report a CI.


def _paired_rows(inp):
    cols = list(inp["pairs"].items())
    if len(cols) != 2: raise DataError("exactly two paired columns are required")
    (na, a), (nb, b) = cols
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    miss = lambda x: x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes
    xs, ys, dropped = [], [], 0
    for x, y in zip(a, b):
        if miss(x) or miss(y): dropped += 1; continue
        xs.append(D(str(x))); ys.append(D(str(y)))
    return (na, xs), (nb, ys), dropped

def paired_impl(inp):
    (na, xs), (nb, ys), dropped = _paired_rows(inp); n = len(xs)
    if n < 2: raise DataError("at least two complete pairs are needed")
    diffs = [x - y for x, y in zip(xs, ys)]
    md, sd = _mean(diffs), _var(diffs).sqrt()
    if sd == 0: raise DataError("all paired differences are identical, so the t statistic is undefined")
    se = sd / D(n).sqrt(); t = md / se; df = D(n - 1); conf = _CONF(inp); tc = _fd(_t_crit(float(df), conf))
    return {"mean_diff": md, "sd_diff": sd, "se_diff": se, "t_stat": t, "df": df, "p_value": _fd(_p_t(float(t), float(df))),
            "ci_lower": md - tc * se, "ci_upper": md + tc * se, "cohens_dz": md / sd, "n_pairs": D(n), "n_dropped": D(dropped),
            f"mean_{na}": _mean(xs), f"mean_{nb}": _mean(ys), "confidence_level": conf, "alpha": _ALPHA(inp)}

def _paired_ref(inp):
    """Independent float route: statistics.fmean/variance and the series incomplete-beta tail."""
    (na, xs), (nb, ys), dropped = _paired_rows(inp); d = [float(x) - float(y) for x, y in zip(xs, ys)]; n = len(d)
    m, sd = statistics.fmean(d), statistics.stdev(d); se = sd / math.sqrt(n); t = m / se; df = n - 1
    lo, hi, target = 0.0, 1e3, _p_t(t, df)
    tc = _t_crit(df, _CONF(inp)); p = _betai_series(df / 2, 0.5, df / (df + t * t))
    return {"mean_diff": m, "sd_diff": sd, "se_diff": se, "t_stat": t, "df": df, "p_value": p,
            "ci_lower": m - tc * se, "ci_upper": m + tc * se, "cohens_dz": m / sd, "n_pairs": n, "n_dropped": dropped}

def _paired_tests(inp, impl):
    base, ref = impl(inp), _paired_ref(inp)
    cols = list(inp["pairs"].values()); swapped = {**inp, "pairs": {list(inp["pairs"])[1]: cols[1], list(inp["pairs"])[0]: cols[0]}}
    rev = {**inp, "pairs": {k: list(reversed(v)) for k, v in inp["pairs"].items()}}
    both = {**inp, "pairs": {k: [str(D(str(x)) + 5) for x in v] for k, v in inp["pairs"].items()}}
    scaled = {**inp, "pairs": {k: [str(D(str(x)) * 3) for x in v] for k, v in inp["pairs"].items()}}
    sw, rv, bt, sc = impl(swapped), impl(rev), impl(both), impl(scaled)
    probe = {"pairs": {"a": ["1", "2", "4", "7", "11"], "b": ["0", "1", "1", "3", "5"]}, "missing_codes": []}
    blank = {"pairs": {"a": ["", "2", "4", "7", "11"], "b": ["0", "1", "1", "3", "5"]}, "missing_codes": []}
    pb, bl = impl(probe), impl(blank)
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("swapping_the_paired_columns_negates_the_difference_keeps_p", _close(sw["mean_diff"], -base["mean_diff"]) and _close(sw["t_stat"], -base["t_stat"]) and _close(sw["p_value"], base["p_value"]), "the sign follows column order; the evidence does not"),
        ("shift_and_scale_behave", _close(bt["mean_diff"], base["mean_diff"]) and _close(bt["t_stat"], base["t_stat"])
            and _close(sc["mean_diff"], base["mean_diff"] * 3) and _close(sc["t_stat"], base["t_stat"]), "adding a constant to both sides changes nothing; scaling both scales the difference only"),
        ("row_order_invariant", all(_close(rv[k], base[k]) for k in ("mean_diff", "t_stat", "p_value", "ci_lower", "ci_upper")), "pair order does not change the result"),
        ("missing_pairs_are_excluded_not_imputed", int(bl["n_pairs"]) == int(pb["n_pairs"]) - 1 and int(bl["n_dropped"]) == int(pb["n_dropped"]) + 1, "a pair missing either side is dropped and counted, never filled in"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _paired_profile(inp):
    try:
        (na, xs), (nb, ys), dropped = _paired_rows(inp); n = len(xs)
        if n < 2: return ["at least two complete pairs are needed"]
        if len(set(x - y for x, y in zip(xs, ys))) == 1: return ["all paired differences are identical, so the t statistic is undefined"]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["paired inputs are malformed: supply two columns of equal length under 'pairs'"]

def _paired_typing(metric):
    if metric in ("n_pairs", "n_dropped"): return ("count", 0)
    if metric in ("confidence_level", "alpha"): return ("rate", 2)
    if metric == "p_value": return ("probability", 4)
    if metric in ("t_stat", "df", "cohens_dz"): return ("ratio", 3)
    return ("@unit", 2)

def _paired_caveats(out, th):
    c = ["Pairs are matched by position in the two columns: if the rows are not genuinely paired, this test is the wrong test.",
         "The test assumes the paired differences are approximately independent and roughly normal; with few pairs the approximation is weak.",
         f"{int(out.get('n_dropped', 0))} pair(s) were dropped because one side was missing or blank; nothing was imputed."]
    if int(out.get("n_pairs", 0)) < int(th.get("small_sample_n", 30)): c.append("Caution: few pairs, so the estimate is imprecise and should be described, not generalized.")
    return c

def _paired_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The paired comparison over " + tok("n_pairs") + " complete pairs gives a mean within-pair difference of " + tok("mean_diff") +
            " with a confidence interval from " + tok("ci_lower") + " to " + tok("ci_upper") + ", a t statistic of " + tok("t_stat") +
            " and a p-value of " + tok("p_value") + ". Pairs with either side missing were dropped and counted, not filled in.")

_ONE_INPUTS = {"values": {"type": "value_list", "min_items": 3, "desc": "the observations; blank or null counts as missing"},
               "mu0": {"type": "decimal", "desc": "the reference value the mean is compared with"},
               "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; never read as values"},
               "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"}}
_ONE_DEFAULTS = ({"question": "Missing-value handling", "default_chosen": "Blank, null and declared missing codes are excluded and counted.", "impact": "Excluded counts are reported; nothing is imputed."},
                 {"question": "Test tails", "default_chosen": "Two-sided by default, with a confidence interval at the declared level.", "impact": "A one-sided test would need a different critical value and is not offered."})
_ONE_ASSUME = ("Observations are independent.", "The outcome is approximately normal, screened only by the interval's sensitivity to outliers.")
_ONE_LIM = ("A one-sample t-test compares a mean with a declared reference value; it does not show where the reference came from.", "Normality is assumed, not tested.", "No one-sided test, trimmed mean or median test is offered.")
_PAIRED_INPUTS = {"pairs": {"type": "column_map", "min_columns": 2, "max_columns": 2, "min_items": 3, "desc": "exactly two columns of paired values: name -> observations; pair i is (column 1 item i, column 2 item i)"},
                  "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; applied to both columns"},
                  "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"}}
_PAIRED_DEFAULTS = ({"question": "What makes a pair", "default_chosen": "Position in the two columns: row i of the first column is matched with row i of the second. A pair is dropped if either side is missing.", "impact": "If rows are not genuinely paired, use an independent-groups test instead."},
                    {"question": "Difference direction", "default_chosen": "First column minus second column; swapping the columns negates the difference and the t statistic but not the p-value.", "impact": "Read the sign against the column order you supplied."})
_PAIRED_ASSUME = ("Observations are paired by construction, not by coincidence.", "The paired differences are independent and approximately normal.")
_PAIRED_LIM = ("Pairing is positional; a mis-sorted file silently produces the wrong pairing.", "Normality of the differences is assumed, not tested.", "No Wilcoxon signed-rank fallback is implemented.")

def one_sample_impl(inp):
    vals, ex = _clean(inp); n = len(vals)
    if n < 2: raise DataError("at least two valid observations are needed")
    mu0 = D(str(inp["mu0"])); m, sd = _mean(vals), _var(vals).sqrt()
    if sd == 0: raise DataError("the sample has zero variance, so the t statistic is undefined")
    se = sd / D(n).sqrt(); t = (m - mu0) / se; df = D(n - 1); conf = _CONF(inp); tc = _fd(_t_crit(float(df), conf))
    return {"mean": m, "mu0": mu0, "sd": sd, "se_mean": se, "t_stat": t, "df": df, "p_value": _fd(_p_t(float(t), float(df))),
            "ci_lower": m - tc * se, "ci_upper": m + tc * se, "cohens_d": (m - mu0) / sd, "n": D(n), "n_excluded": D(ex),
            "confidence_level": conf, "alpha": _ALPHA(inp)}

def _one_ref(inp):
    """Independent float route for the one-sample test (statistics module + series incomplete beta)."""
    vals, ex = _clean(inp); f = [float(v) for v in vals]; n = len(f); mu0 = float(D(str(inp["mu0"])))
    m, sd = statistics.fmean(f), statistics.stdev(f); se = sd / math.sqrt(n); t = (m - mu0) / se; df = n - 1
    tc = _t_crit(df, _CONF(inp))
    return {"mean": m, "sd": sd, "se_mean": se, "t_stat": t, "df": df, "p_value": _betai_series(df / 2, 0.5, df / (df + t * t)),
            "ci_lower": m - tc * se, "ci_upper": m + tc * se, "cohens_d": (m - mu0) / sd, "n": n, "n_excluded": ex}

def _one_tests(inp, impl):
    base, ref = impl(inp), _one_ref(inp)
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    miss = lambda v: v is None or (isinstance(v, str) and not v.strip()) or D(str(v)) in codes
    k = D("4")
    shifted = impl({**inp, "values": [v if miss(v) else str(D(str(v)) + k) for v in inp["values"]],
                    "mu0": str(D(str(inp["mu0"])) + k)})
    scaled = impl({**inp, "values": [v if miss(v) else str(D(str(v)) * 3) for v in inp["values"]],
                   "mu0": str(D(str(inp["mu0"])) * 3)})
    rev = impl({**inp, "values": list(reversed(inp["values"]))})
    padded = impl({**inp, "values": list(inp["values"]) + ["", ""]})
    checks = [
        ("second_implementation_agrees", all(_close(base[k2], ref[k2]) for k2 in ref), "float route agrees with the Decimal route"),
        ("shift_invariance", _close(shifted["t_stat"], base["t_stat"]) and _close(shifted["p_value"], base["p_value"]), "adding a constant to the data and the reference leaves t unchanged"),
        ("positive_scale_equivariance", _close(scaled["t_stat"], base["t_stat"]) and _close(scaled["mean"], base["mean"] * 3), "scaling data and reference leaves t unchanged"),
        ("row_order_invariant", _close(rev["t_stat"], base["t_stat"]) and _close(rev["p_value"], base["p_value"]), "observation order does not change the result"),
        ("missing_entries_are_excluded_not_valued", _close(padded["t_stat"], base["t_stat"]) and int(padded["n_excluded"]) == int(base["n_excluded"]) + 2, "blanks are excluded and counted, never read as zero"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _one_profile(inp):
    try:
        vals, _ = _clean(inp)
        if len(vals) < 2: return ["at least two valid observations are needed"]
        if len(set(vals)) == 1: return ["the sample has zero variance, so the t statistic is undefined"]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["one-sample inputs are malformed: values and a numeric mu0 are required"]

def _one_typing(metric):
    if metric in ("n", "n_excluded"): return ("count", 0)
    if metric in ("confidence_level", "alpha"): return ("rate", 2)
    if metric == "p_value": return ("probability", 4)
    if metric in ("t_stat", "df", "cohens_d"): return ("ratio", 3)
    return ("@unit", 2)

def _one_caveats(out, th):
    c = ["The reference value was declared, not derived from this sample; the test says how far the mean is from it, not whether the reference is right.",
         "The interval and p-value assume the observations are roughly normal and independent; outliers inflate the spread."]
    if int(out.get("n", 0)) < int(th.get("small_sample_n", 30)): c.append("Caution: the sample is small, so the interval is wide and the estimate imprecise.")
    return c

def _one_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The sample mean is " + tok("mean") + ", compared with the declared reference value " + tok("mu0") +
            ". The t statistic is " + tok("t_stat") + " with a p-value of " + tok("p_value") +
            ", and the confidence interval for the mean runs from " + tok("ci_lower") + " to " + tok("ci_upper") + ".")


# ---------- Descriptive statistics (one numeric variable; manual 9B.2, 9B.4) ----------
def _clean(inp):
    """User-missing codes are never read as values (manual 5.1, 9B). Returns (valid values, n excluded)."""
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    vals, miss = [], 0
    for x in inp["values"]:
        if x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes: miss += 1
        else: vals.append(D(str(x)))
    return vals, miss

def describe_impl(inp):
    vals, miss = _clean(inp); n = len(vals)
    s = sorted(vals); mean = sum(vals, D(0)) / n
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    out = {"n": D(n), "n_missing": D(miss), "mean": mean, "median": median, "minimum": s[0], "maximum": s[-1]}
    if n >= 2:
        var = sum(((x - mean) ** 2 for x in vals), D(0)) / (n - 1)   # sample variance, n-1
        out["variance"], out["sd"] = var, var.sqrt()
    return out

def _close(a, b, rel=1e-9):
    a = float(a); b = float(b)
    return abs(a - b) <= rel * max(1.0, abs(b))

def describe_reference(inp):
    """Independent route: float arithmetic via the statistics module (different algorithm and number type)."""
    vals, miss = _clean(inp); f = [float(x) for x in vals]; n = len(f)
    out = {"n": n, "n_missing": miss, "mean": statistics.fmean(f), "median": statistics.median(f), "minimum": min(f), "maximum": max(f)}
    if n >= 2: out["variance"], out["sd"] = statistics.variance(f), statistics.stdev(f)
    return out

def describe_tests(inp, impl):
    base, ref = impl(inp), describe_reference(inp)
    vals, miss = _clean(inp); sv = [str(x) for x in vals]
    clean = {"values": sv, "missing_codes": []}
    b0 = impl(clean)
    shift, k = D("1000.5"), D(3)
    sh = impl({"values": [str(x + shift) for x in vals], "missing_codes": []})
    sc = impl({"values": [str(x * k) for x in vals], "missing_codes": []})
    pm = impl({"values": list(reversed(sv)), "missing_codes": []})
    pad = impl({**inp, "values": list(inp["values"]) + [inp.get("missing_codes", [None])[0] if inp.get("missing_codes") else None] * 2})
    spread = [m for m in ("variance", "sd") if m in b0]
    return [
        ("second_implementation_agrees", set(base) == set(ref) and all(_close(base[m], ref[m]) for m in ref)),
        ("shift_moves_location_not_spread", all(_close(sh[m], b0[m] + shift) for m in ("mean", "median", "minimum", "maximum")) and all(_close(sh[m], b0[m]) for m in spread)),
        ("scale_scales_spread", _close(sc["mean"], b0["mean"] * k) and all(_close(sc[m], b0[m] * k ** (1 if m == "sd" else 2)) for m in spread)),
        ("permutation_invariant", all(_close(pm[m], b0[m]) for m in b0)),
        ("missing_entries_excluded_not_valued", all(_close(pad[m], base[m]) for m in base if m != "n_missing") and _close(pad["n_missing"], base["n_missing"] + 2)),
        ("order_statistics_bounded", base["minimum"] <= base["median"] <= base["maximum"] and base["minimum"] <= base["mean"] <= base["maximum"]),
    ]

def describe_profile(inp):
    vals, _ = _clean(inp)
    return [] if vals else ["no valid observations remain after excluding missing values"]

def describe_caveats(out, thresholds):
    n = int(out["n"]); small = int(thresholds.get("small_sample_n", 30))
    c = []
    if n < small: c.append("Caution: the sample is small, so these values are unstable and should be described, not generalized.")
    if n < 2: c.append("Spread measures are not defined for a single observation and are omitted.")
    return c

def describe_template(keys, period, thresholds=None):
    P = period; t = ("The dataset contains {{ref:n:n:%s}} valid observations, with {{ref:n_missing:n_missing:%s}} excluded as missing. "
                     "The mean is {{ref:mean:mean:%s}} and the median is {{ref:median:median:%s}}. "
                     "Values range from {{ref:minimum:minimum:%s}} to {{ref:maximum:maximum:%s}}.") % (P, P, P, P, P, P)
    if "sd" in keys: t += " The sample standard deviation is {{ref:sd:sd:%s}}." % P
    return t


# ---------- Correlation: Pearson with pre-declared fallback to Spearman (manual 9B.2, 9B.3) ----------
import math
from statistics import NormalDist

def _fd(x): return D(repr(float(x)))    # float -> Decimal at the typed-quantity boundary (manual 5.4)

def _pairs(inp):
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    miss = lambda v: v is None or (isinstance(v, str) and not v.strip()) or D(str(v)) in codes
    xs, ys, ex = [], [], 0
    if len(inp["x"]) != len(inp["y"]): raise DataError(f"x has {len(inp['x'])} entries but y has {len(inp['y'])}; they must be paired")
    for a, b in zip(inp["x"], inp["y"]):
        if miss(a) or miss(b): ex += 1
        else: xs.append(D(str(a))); ys.append(D(str(b)))
    return xs, ys, ex

def _pearson(xs, ys):
    n = len(xs); mx, my = sum(xs, D(0)) / n, sum(ys, D(0)) / n
    sxy = sum(((a - mx) * (b - my) for a, b in zip(xs, ys)), D(0))
    sxx = sum(((a - mx) ** 2 for a in xs), D(0)); syy = sum(((b - my) ** 2 for b in ys), D(0))
    if sxx == 0 or syy == 0: raise DataError("a variable is constant, so correlation is undefined")
    return sxy / (sxx * syy).sqrt()

def _ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i]); r = [D(0)] * len(v); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]: j += 1
        for k in range(i, j + 1): r[order[k]] = D(i + j + 2) / 2       # average rank of a tie group
        i = j + 1
    return r

def _betacf(a, b, x):
    tiny, qab, qap, qam = 1e-300, a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap; d = tiny if abs(d) < tiny else d; d = 1 / d; h = d
    for m in range(1, 500):
        m2 = 2 * m; aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = tiny if abs(d) < tiny else d; c = 1 + aa / c; c = tiny if abs(c) < tiny else c; d = 1 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = tiny if abs(d) < tiny else d; c = 1 + aa / c; c = tiny if abs(c) < tiny else c; d = 1 / d; de = d * c; h *= de
        if abs(de - 1) < 3e-16: break
    return h

def _betai(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) else 1 - bt * _betacf(b, a, 1 - x) / b

def _p_two_sided(r, n):
    df = n - 2; r = float(r)
    if abs(r) >= 1: return 0.0
    t2 = r * r * df / (1 - r * r)
    return _betai(df / 2, 0.5, df / (df + t2))

def _inference(r, n, conf, se_fn):
    rf = float(r); z = math.atanh(rf); crit = NormalDist().inv_cdf(0.5 + float(conf) / 2); se = se_fn(rf, n)
    return _fd(math.tanh(z - crit * se)), _fd(math.tanh(z + crit * se)), _fd(_p_two_sided(r, n))

_CONF = lambda inp: D(str(inp.get("confidence_level", "0.95")))
_ALPHA = lambda inp: D(str(inp.get("alpha", "0.05")))
_pearson_se = lambda r, n: 1 / math.sqrt(n - 3)
_spearman_se = lambda r, n: math.sqrt((1 + r * r / 2) / (n - 3))     # Bonett-Wright [UNVERIFIED]

def _corr(inp, kind):
    xs, ys, ex = _pairs(inp); n = len(xs)
    if kind == "spearman": xs, ys = _ranks(xs), _ranks(ys)
    r = _pearson(xs, ys)
    if abs(r) >= 1: raise DataError("perfect correlation: the interval is undefined; check for duplicated or derived columns")
    lo, hi, p = _inference(r, n, _CONF(inp), _pearson_se if kind == "pearson" else _spearman_se)
    key = "r" if kind == "pearson" else "rho"
    out = {key: r}
    if kind == "pearson": out["r_squared"] = r * r
    out.update({"ci_lower": lo, "ci_upper": hi, "p_value": p, "n_pairs": D(n), "n_excluded": D(ex),
                "confidence_level": _CONF(inp), "alpha": _ALPHA(inp)})
    return out

pearson_impl = lambda inp: _corr(inp, "pearson")
spearman_impl = lambda inp: _corr(inp, "spearman")

def _cols(inp, keep=None):
    xs, ys, ex = _pairs(inp); return [str(v) for v in xs], [str(v) for v in ys], ex

def _norm_crit_bisect(conf):                       # independent route to the normal quantile
    target, lo, hi = 0.5 + conf / 2, 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if NormalDist().cdf(mid) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def _t_two_sided_integration(r, n):                # independent route: Simpson integration of the t density
    df = n - 2; t = abs(float(r)) * math.sqrt(df / (1 - float(r) ** 2)); N = 20000; h = t / N
    pdf = lambda x: math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi) - (df + 1) / 2 * math.log(1 + x * x / df))
    I = pdf(0) + pdf(t) + sum((4 if i % 2 else 2) * pdf(i * h) for i in range(1, N))
    return 1 - 2 * (I * h / 3)

def _rank_reference(v):                            # independent ranking: counting, not sorting
    return [1 + sum(1 for u in v if u < x) + (sum(1 for u in v if u == x) - 1) / 2 for x in v]

def _ref(inp, kind):
    xs, ys, ex = _pairs(inp); n = len(xs); fx, fy = [float(v) for v in xs], [float(v) for v in ys]
    if kind == "spearman": fx, fy = _rank_reference(fx), _rank_reference(fy)
    r = statistics.correlation(fx, fy); se = (1 / math.sqrt(n - 3)) if kind == "pearson" else math.sqrt((1 + r * r / 2) / (n - 3))
    c = _norm_crit_bisect(float(_CONF(inp))); z = 0.5 * math.log((1 + r) / (1 - r))
    return {"r" if kind == "pearson" else "rho": r, "ci_lower": math.tanh(z - c * se), "ci_upper": math.tanh(z + c * se),
            "p_value": _t_two_sided_integration(r, n), "n_pairs": n, "n_excluded": ex}

def _corr_tests(inp, impl, kind):
    key = "r" if kind == "pearson" else "rho"
    base, ref = impl(inp), _ref(inp, kind); xs, ys, ex = _cols(inp)
    mk = lambda x, y: {**inp, "x": x, "y": y, "missing_codes": []}
    b0 = impl(mk(xs, ys))
    pad = impl({**inp, "x": list(inp["x"]) + [None, "5"], "y": list(inp["y"]) + ["3", None]})
    neg = impl(mk(xs, [str(-D(v)) for v in ys])); swp = impl(mk(ys, xs))
    agree = (set(ref) <= set(base) and all(abs(float(base[k]) - float(ref[k])) <= (1e-7 if k == "p_value" else 1e-9 * max(1.0, abs(float(ref[k])))) for k in ref))
    tests = [("second_implementation_agrees", agree)]
    if kind == "pearson":
        lin = impl(mk([str(D(v) * 2 + 7) for v in xs], [str(D(v) * D("0.5") - 3) for v in ys]))
        tests.append(("invariant_to_positive_linear_transform", abs(float(lin[key]) - float(b0[key])) <= 1e-9))
    else:
        mono = impl(mk([str(D(v) ** 3) for v in xs], ys))
        tests.append(("invariant_to_monotone_transform", abs(float(mono[key]) - float(b0[key])) <= 1e-9))
    tests += [
        ("negating_y_flips_sign_keeps_p", abs(float(neg[key]) + float(b0[key])) <= 1e-9 and abs(float(neg["p_value"]) - float(b0["p_value"])) <= 1e-9),
        ("symmetric_in_x_and_y", abs(float(swp[key]) - float(b0[key])) <= 1e-9),
        ("bounded_and_consistent", -1 < base[key] < 1 and base["ci_lower"] <= base[key] <= base["ci_upper"] and 0 <= base["p_value"] <= 1
                                  and (kind != "pearson" or abs(float(base["r_squared"]) - float(base[key]) ** 2) <= 1e-12)),
        ("missing_pairs_excluded_not_valued", all(abs(float(pad[k]) - float(base[k])) <= 1e-9 for k in base if k != "n_excluded") and pad["n_excluded"] == base["n_excluded"] + 2),
    ]
    return tests

pearson_tests = lambda inp, impl: _corr_tests(inp, impl, "pearson")
spearman_tests = lambda inp, impl: _corr_tests(inp, impl, "spearman")

def _moments(v):
    f = [float(a) for a in v]; n = len(f); m = sum(f) / n; m2 = sum((a - m) ** 2 for a in f) / n
    if m2 == 0: return 0.0, 0.0
    return (sum((a - m) ** 3 for a in f) / n / m2 ** 1.5, sum((a - m) ** 4 for a in f) / n / m2 ** 2 - 3)

def normality_screen(inp, th):
    xs, ys, _ = _pairs(inp); sl, kl = float(th.get("skew_limit", "2")), float(th.get("kurtosis_limit", "7")); bad = []
    for name, v in (("x", xs), ("y", ys)):
        sk, ku = _moments(v)
        if abs(sk) > sl or abs(ku) > kl: bad.append(f"{name}: skewness {sk:.2f}, excess kurtosis {ku:.2f}")
    return [("normality_screen", not bad, "; ".join(bad) or "within declared limits")]

def corr_profile(inp):
    issues = []
    try: xs, ys, ex = _pairs(inp)
    except DataError as e: return [str(e)]
    if len(xs) < 4: issues.append("fewer than four complete pairs: the interval needs n of at least four")
    if xs and len(set(xs)) == 1: issues.append("x is constant after excluding missing values")
    if ys and len(set(ys)) == 1: issues.append("y is constant after excluding missing values")
    if not (0 < _CONF(inp) < 1): issues.append("confidence_level must be between 0 and 1")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def corr_caveats(out, th):
    key = "r" if "r" in out else "rho"; c = []
    if int(out["n_pairs"]) < int(th.get("small_sample_n", 30)): c.append("Caution: the sample is small, so this estimate is imprecise and should be described, not generalized.")
    c.append("An association does not establish a causal relationship, and this analysis makes no causal claim.")
    c.append("The coefficient does not test linearity; inspect a scatterplot before relying on it." if key == "r" else "The interval and p-value are approximations that are less accurate with ties or very small samples.")
    return c

def corr_template(out, P, th):
    key = "r" if "r" in out else "rho"; name = "Pearson correlation" if key == "r" else "Spearman rank correlation"
    r = out[key]; a = abs(r); g = lambda k, d: D(str(th.get(k, d)))
    size = "negligible" if a < g("effect_small", "0.1") else "small" if a < g("effect_medium", "0.3") else "medium" if a < g("effect_large", "0.5") else "large"
    t = ("The sample contains {{ref:n_pairs:n_pairs:@}} complete pairs, with {{ref:n_excluded:n_excluded:@}} excluded as missing. "
         "The " + name + " is {{ref:" + key + ":" + key + ":@}}, a " + size + " " + ("positive" if r > 0 else "negative") + " association in this sample. "
         "The confidence interval at level {{ref:confidence_level:confidence_level:@}} runs from {{ref:ci_lower:ci_lower:@}} to {{ref:ci_upper:ci_upper:@}}. ")
    t += ("The p-value is {{ref:p_value:p_value:@}}. " if out["p_value"] >= D("0.0001") else "The p-value is below the reporting floor of four decimal places. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:@}} the association is statistically significant. " if out["p_value"] < out["alpha"]
          else "At the declared significance level of {{ref:alpha:alpha:@}} the association is not statistically significant. ")
    t += "Statistical significance and practical importance are separate questions."
    return t.replace("@", P)

_CORR_INPUTS = {"x": {"type": "value_list", "min_items": 4, "desc": "first variable; blank or null counts as missing"},
                "y": {"type": "value_list", "min_items": 4, "desc": "second variable, paired by position with x"},
                "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; apply to both variables"},
                "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"},
                "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"}}
_CORR_UNITS = {"p_value": "probability", "confidence_level": "rate", "alpha": "rate", "n_pairs": "count", "n_excluded": "count"}
_CORR_THRESH = {"small_sample_n": "30", "effect_small": "0.1", "effect_medium": "0.3", "effect_large": "0.5", "skew_limit": "2", "kurtosis_limit": "7"}
_CORR_DEFAULTS = ({"question": "Missing-value handling", "default_chosen": "A pair is excluded if either value is blank, null or a declared missing code (pairwise deletion for two variables).", "impact": "Counts of excluded pairs are reported; other handling (imputation) changes the estimate."},
                  {"question": "Multiple comparisons", "default_chosen": "One test, so no correction. If more tests are run, declare a correction in the spec.", "impact": "Running many correlations without correction inflates false positives."},
                  {"question": "Effect-size wording thresholds", "default_chosen": "Absolute r below 0.1 negligible, below 0.3 small, below 0.5 medium, otherwise large (Cohen-style conventions) [PROVISIONAL, UNVERIFIED]. The effect size is the coefficient itself.", "impact": "Changes only the descriptive word, not the numbers."},
                  {"question": "Precision statement", "default_chosen": "Precision is conveyed by the confidence interval; no separate power calculation is made.", "impact": "A wide interval signals low precision."})

# ---------- Linear regression (OLS) with pre-declared diagnostics; HC3 robust fallback (manual 9B.2, 9B.3) ----------
def _identity(p): return [[D(int(i == j)) for j in range(p)] for i in range(p)]

def _inv(M):
    p = len(M); A = [row[:] + e for row, e in zip(M, _identity(p))]
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < D("1e-25") * max(D(1), max(abs(x) for row in M for x in row)):
            raise DataError("predictors are perfectly collinear (a predictor is a combination of others or constant)")
        A[c], A[piv] = A[piv], A[c]; d = A[c][c]; A[c] = [x / d for x in A[c]]
        for r in range(p):
            if r != c and A[r][c] != 0:
                f = A[r][c]; A[r] = [x - f * y for x, y in zip(A[r], A[c])]
    return [row[p:] for row in A]

def _mv(M, v): return [sum((a * b for a, b in zip(row, v)), D(0)) for row in M]

def _reg_rows(inp):
    """Complete rows only; blank, null or declared missing codes exclude the row and are counted."""
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    miss = lambda v: v is None or (isinstance(v, str) and not v.strip()) or D(str(v)) in codes
    names = list(inp["predictors"]); n0 = len(inp["y"])
    for nm in names:
        if len(inp["predictors"][nm]) != n0: raise DataError(f"predictor '{nm}' has {len(inp['predictors'][nm])} entries but y has {n0}; they must be paired")
    X, y, ex = [], [], 0
    for i in range(n0):
        vals = [inp["y"][i]] + [inp["predictors"][nm][i] for nm in names]
        if any(miss(v) for v in vals): ex += 1
        else: y.append(D(str(vals[0]))); X.append([D(1)] + [D(str(v)) for v in vals[1:]])
    return names, X, y, ex

def _fit(X, y, robust=False):
    n, p = len(X), len(X[0]); Xt = list(zip(*X))
    inv = _inv([[sum((a * b for a, b in zip(r1, r2)), D(0)) for r2 in Xt] for r1 in Xt])
    beta = _mv(inv, [sum((a * b for a, b in zip(r, y)), D(0)) for r in Xt])
    fit = [sum((a * b for a, b in zip(row, beta)), D(0)) for row in X]; e = [yi - fi for yi, fi in zip(y, fit)]
    ssr = sum((x * x for x in e), D(0)); my = sum(y, D(0)) / n; sst = sum(((v - my) ** 2 for v in y), D(0))
    if sst == 0: raise DataError("y is constant, so regression is undefined")
    if ssr == 0: raise DataError("perfect fit: inference is undefined; check for a duplicated or derived predictor")
    h = [sum((a * b for a, b in zip(row, _mv(inv, row))), D(0)) for row in X]; df = n - p
    if robust:
        if any(hi >= 1 for hi in h): raise DataError("an observation has leverage of one; robust errors are undefined")
        meat = [[sum((D(row[a]) * row[b] * ei * ei / (1 - hi) ** 2 for row, ei, hi in zip(X, e, h)), D(0)) for b in range(p)] for a in range(p)]
        V = [[sum((inv[a][c] * sum((meat[c][d] * inv[d][b] for d in range(p)), D(0)) for c in range(p)), D(0)) for b in range(p)] for a in range(p)]
    else:
        V = [[x * ssr / df for x in row] for row in inv]
    return {"n": n, "p": p, "beta": beta, "e": e, "h": h, "ssr": ssr, "sst": sst, "df": df, "inv": inv, "se": [v.sqrt() for v in [V[i][i] for i in range(p)]], "my": my}

def _t_crit(df, conf):
    target = 1 - float(conf); lo, hi = 0.0, 1.0
    while _betai(df / 2, 0.5, df / (df + hi * hi)) > target: hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if _betai(df / 2, 0.5, df / (df + mid * mid)) > target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def _ols(inp, robust):
    names, X, y, ex = _reg_rows(inp); f = _fit(X, y, robust); n, p, df, k = f["n"], f["p"], f["df"], f["p"] - 1
    conf = _CONF(inp); tc = _fd(_t_crit(df, conf)); r2 = 1 - f["ssr"] / f["sst"]
    out = {"r_squared": r2, "adj_r_squared": 1 - (1 - r2) * (n - 1) / df, "f_squared": r2 / (1 - r2)}
    if not robust:
        F = (r2 / k) / ((1 - r2) / df); out["f_stat"] = F; out["p_f"] = _fd(_betai(df / 2, k / 2, df / (df + k * float(F))))
    out.update({"residual_se": (f["ssr"] / df).sqrt(), "n": D(n), "n_excluded": D(ex), "k": D(k), "df_residual": D(df), "confidence_level": conf, "alpha": _ALPHA(inp)})
    sdy = sum(((v - f["my"]) ** 2 for v in y), D(0))
    for j, nm in enumerate(["intercept"] + names):
        b, se = f["beta"][j], f["se"][j]; t = b / se
        out[f"coef_{nm}"] = b; out[f"se_{nm}"] = se; out[f"p_{nm}"] = _fd(_p_t(float(t), df))
        out[f"ci_lower_{nm}"] = b - tc * se; out[f"ci_upper_{nm}"] = b + tc * se
        if j: 
            col = [r[j] for r in X]; mx = sum(col, D(0)) / n; out[f"std_beta_{nm}"] = b * (sum(((v - mx) ** 2 for v in col), D(0)) / sdy).sqrt()
    return out

def _p_t(t, df): return _betai(df / 2, 0.5, df / (df + t * t))
ols_impl = lambda inp: _ols(inp, False)
ols_robust_impl = lambda inp: _ols(inp, True)

# --- independent float route: modified Gram-Schmidt QR, series incomplete beta ---
def _betai_series(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    if x > (a + 1) / (a + b + 2): return 1 - _betai_series(b, a, 1 - x)
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b); term = tot = 1.0; nn = 0
    while term > 1e-17 * tot and nn < 200000: term *= (a + b + nn) / (a + 1 + nn) * x; tot += term; nn += 1
    return math.exp(lb + a * math.log(x) + b * math.log(1 - x)) / a * tot

def _qr_fit(X, y):
    n, p = len(X), len(X[0]); Q, R = [], [[0.0] * p for _ in range(p)]
    for j in range(p):
        v = [row[j] for row in X]
        for i, q in enumerate(Q):
            R[i][j] = sum(a * b for a, b in zip(q, v)); v = [a - R[i][j] * b for a, b in zip(v, q)]
        R[j][j] = math.sqrt(sum(a * a for a in v)); Q.append([a / R[j][j] for a in v])
    qty = [sum(a * b for a, b in zip(q, y)) for q in Q]; beta = [0.0] * p
    for i in reversed(range(p)): beta[i] = (qty[i] - sum(R[i][j] * beta[j] for j in range(i + 1, p))) / R[i][i]
    Ri = [[0.0] * p for _ in range(p)]
    for c in range(p):
        for i in reversed(range(p)): Ri[i][c] = ((1.0 if i == c else 0.0) - sum(R[i][j] * Ri[j][c] for j in range(i + 1, p))) / R[i][i]
    inv = [[sum(Ri[i][m] * Ri[j][m] for m in range(p)) for j in range(p)] for i in range(p)]
    return beta, inv, [sum(Q[j][i] ** 2 for j in range(p)) for i in range(n)]

def _ols_ref(inp, robust):
    names, X, y, ex = _reg_rows(inp); Xf = [[float(v) for v in r] for r in X]; yf = [float(v) for v in y]; n, p = len(Xf), len(Xf[0]); df = n - p; k = p - 1
    beta, inv, h = _qr_fit(Xf, yf); e = [yi - sum(a * b for a, b in zip(r, beta)) for r, yi in zip(Xf, yf)]
    ssr = sum(x * x for x in e); my = sum(yf) / n; sst = sum((v - my) ** 2 for v in yf); r2 = 1 - ssr / sst
    if robust:
        meat = [[sum(r[a] * r[b] * ei * ei / (1 - hi) ** 2 for r, ei, hi in zip(Xf, e, h)) for b in range(p)] for a in range(p)]
        V = [[sum(inv[a][c] * meat[c][d] * inv[d][b] for c in range(p) for d in range(p)) for b in range(p)] for a in range(p)]
    else: V = [[x * ssr / df for x in row] for row in inv]
    conf = float(_CONF(inp)); target = 1 - conf; lo, hi = 0.0, 1e4
    for _ in range(300):
        mid = (lo + hi) / 2
        if _betai_series(df / 2, 0.5, df / (df + mid * mid)) > target: lo = mid
        else: hi = mid
    tc = (lo + hi) / 2; out = {"r_squared": r2, "adj_r_squared": 1 - (1 - r2) * (n - 1) / df, "residual_se": math.sqrt(ssr / df), "n": n, "n_excluded": ex}
    if not robust:
        F = (r2 / k) / ((1 - r2) / df); out["f_stat"] = F; out["p_f"] = _betai_series(df / 2, k / 2, df / (df + k * F))
    for j, nm in enumerate(["intercept"] + names):
        se = math.sqrt(V[j][j]); out[f"coef_{nm}"] = beta[j]; out[f"se_{nm}"] = se
        out[f"p_{nm}"] = _betai_series(df / 2, 0.5, df / (df + (beta[j] / se) ** 2))
        out[f"ci_lower_{nm}"] = beta[j] - tc * se; out[f"ci_upper_{nm}"] = beta[j] + tc * se
    return out

def _rclose(a, b, tol=1e-8): return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))

def _ols_tests(inp, impl, robust):
    base, ref = impl(inp), _ols_ref(inp, robust); names, X, y, ex = _reg_rows(inp)
    mk = lambda ycol, cols: {**inp, "y": ycol, "predictors": cols, "missing_codes": []}
    ys = [str(v) for v in y]; cols = {nm: [str(r[j + 1]) for r in X] for j, nm in enumerate(names)}
    b0 = impl(mk(ys, cols)); nm0 = names[0]
    shifted = impl(mk(ys, {**cols, nm0: [str(D(v) + D("100.5")) for v in cols[nm0]]}))
    scaled = impl(mk([str(D(v) * 4) for v in ys], {**cols, nm0: [str(D(v) * 2) for v in cols[nm0]]}))
    perm = impl(mk(ys[::-1], {nm: c[::-1] for nm, c in cols.items()}))
    padded = impl({**inp, "y": list(inp["y"]) + ["1", None], "predictors": {nm: list(c) + [None, "1"] for nm, c in inp["predictors"].items()}})
    terms = ["intercept"] + names; tests = [("second_implementation_agrees", all(_rclose(base[k], ref[k]) for k in ref))]
    tests += [("shift_changes_intercept_only", all(_rclose(shifted[f"{a}_{nm0}"], b0[f"{a}_{nm0}"]) for a in ("coef", "se", "p")) and _rclose(shifted["r_squared"], b0["r_squared"]) and not _rclose(shifted["coef_intercept"], b0["coef_intercept"], 1e-3)),
              ("scaling_rescales_coefficients_not_significance", _rclose(scaled[f"coef_{nm0}"], b0[f"coef_{nm0}"] * 2) and _rclose(scaled[f"se_{nm0}"], b0[f"se_{nm0}"] * 2) and _rclose(scaled[f"p_{nm0}"], b0[f"p_{nm0}"]) and _rclose(scaled["r_squared"], b0["r_squared"])),
              ("row_order_invariant", all(_rclose(perm[k], b0[k], 1e-9) for k in b0)),
              ("incomplete_rows_excluded_not_valued", all(_rclose(padded[k], base[k], 1e-9) for k in base if k != "n_excluded") and padded["n_excluded"] == base["n_excluded"] + 2),
              ("bounded_and_consistent", 0 <= base["r_squared"] <= 1 and base["adj_r_squared"] <= base["r_squared"] and all(base[f"ci_lower_{t}"] <= base[f"coef_{t}"] <= base[f"ci_upper_{t}"] and 0 <= base[f"p_{t}"] <= 1 for t in terms))]
    # cross-method consistency: k=1 ties to Pearson; k>1 uses Frisch-Waugh-Lovell (partial regression) on the first predictor
    if len(names) == 1:
        pr = pearson_impl({"x": cols[nm0], "y": ys, "missing_codes": []})
        ok = _rclose(base[f"std_beta_{nm0}"], pr["r"], 1e-9) and (robust or _rclose(base[f"p_{nm0}"], pr["p_value"], 1e-7))
    else:
        others = [[D(1)] + [r[j + 1] for j in range(1, len(names))] for r in X]; x1 = [r[1] for r in X]
        fy, fx = _fit(others, y), _fit(others, x1); ry, rx = fy["e"], fx["e"]
        ok = _rclose(base[f"coef_{nm0}"], sum((a * b for a, b in zip(rx, ry)), D(0)) / sum((a * a for a in rx), D(0)), 1e-9)
    tests.append(("cross_check_partial_regression_and_pearson", ok))
    return tests
ols_tests = lambda inp, impl: _ols_tests(inp, impl, False)
ols_robust_tests = lambda inp, impl: _ols_tests(inp, impl, True)

def _diag(inp, th, which):
    names, X, y, ex = _reg_rows(inp); f = _fit(X, y); n, p, k = f["n"], f["p"], f["p"] - 1; res = []
    if "normality" in which:
        sk, ku = _moments(f["e"]); sl, kl = float(th.get("skew_limit", "2")), float(th.get("kurtosis_limit", "7"))
        res.append(("residual_normality_screen", abs(sk) <= sl and abs(ku) <= kl, f"residual skewness {sk:.2f}, excess kurtosis {ku:.2f}; limits {sl:g} and {kl:g}"))
    if "heteroskedasticity" in which:
        e2 = [e * e for e in f["e"]]
        try:
            fa = _fit(X, e2); r2a = 1 - fa["ssr"] / fa["sst"]; dfa = n - p
            Fa = (r2a / k) / ((1 - r2a) / dfa); pa = _betai(dfa / 2, k / 2, dfa / (dfa + k * float(Fa))); lim = float(th.get("bp_alpha", "0.05"))
            res.append(("heteroskedasticity_screen", pa >= lim, f"F-form Breusch-Pagan p-value {pa:.4f}; declared level {lim:g}"))
        except DataError: res.append(("heteroskedasticity_screen", True, "squared residuals are constant or perfectly fitted; no evidence of heteroskedasticity"))
    if "multicollinearity" in which:
        if k >= 2:
            cols = [[r[j] for r in X] for j in range(1, p)]; means = [sum(c, D(0)) / n for c in cols]
            C = [[sum(((a - means[i]) * (b - means[j]) for a, b in zip(cols[i], cols[j])), D(0)) for j in range(k)] for i in range(k)]
            R = [[C[i][j] / (C[i][i] * C[j][j]).sqrt() for j in range(k)] for i in range(k)]
            vif = [float(_inv(R)[i][i]) for i in range(k)]; lim = float(th.get("vif_limit", "10"))
            res.append(("multicollinearity_screen", max(vif) <= lim, f"largest variance inflation factor {max(vif):.2f}; limit {lim:g}"))
        else: res.append(("multicollinearity_screen", True, "single predictor"))
    if "influence" in which:
        s2 = f["ssr"] / f["df"]; cook = [float(e * e * h / (p * s2 * (1 - h) ** 2)) if h < 1 else float("inf") for e, h in zip(f["e"], f["h"])]; lim = float(th.get("cooks_limit", "1"))
        res.append(("influence_screen", max(cook) <= lim, f"largest Cook's distance {max(cook):.2f}; limit {lim:g}"))
    return res

ols_checks = lambda inp, th: _diag(inp, th, ("normality", "heteroskedasticity", "multicollinearity", "influence"))
ols_robust_checks = lambda inp, th: _diag(inp, th, ("normality", "multicollinearity", "influence"))

def ols_profile(inp):
    issues = []
    try: names, X, y, ex = _reg_rows(inp)
    except DataError as e: return [str(e)]
    n, p = len(X), len(names) + 1
    if n - p < 3: issues.append(f"too few complete rows: need at least {p + 3} for {len(names)} predictor(s)")
    elif len(set(y)) == 1: issues.append("y is constant after excluding missing values")
    for j, nm in enumerate(names):
        if n and len({r[j + 1] for r in X}) == 1: issues.append(f"predictor '{nm}' is constant after excluding missing values")
    if not (0 < _CONF(inp) < 1): issues.append("confidence_level must be between 0 and 1")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def ols_typing(metric):
    if metric in ("n", "n_excluded", "k", "df_residual"): return "count", 0
    if metric in ("confidence_level", "alpha"): return "rate", 2
    if metric.startswith("p_") or metric == "p_f": return "probability", 4
    if metric.startswith("coef_") or metric.startswith("se_") or metric.startswith("ci_") or metric == "residual_se": return "coefficient", 3
    return "ratio", 3

def ols_caveats(out, th, robust=False):
    c = []
    if int(out["n"]) < int(th.get("small_sample_n", 30)): c.append("Caution: the sample is small, so the estimates are imprecise and should be described, not generalized.")
    c.append("These are associations; the analysis makes no causal claim and omitted variables could explain the pattern.")
    c.append("The diagnostic screens are coarse; inspect residual plots before relying on the model.")
    if robust: c.append("Standard errors, intervals and p-values use the HC3 robust estimator, and no overall F test is reported.")
    return c

def ols_template(out, P, th):
    names = [k[5:] for k in out if k.startswith("coef_") and k != "coef_intercept"]; g = lambda k, d: D(str(th.get(k, d))); f2 = out["f_squared"]
    size = "negligible" if f2 < g("f2_small", "0.02") else "small" if f2 < g("f2_medium", "0.15") else "medium" if f2 < g("f2_large", "0.35") else "large"
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    ptxt = lambda m: tok(m) if out[m] >= D("0.0001") else "below the reporting floor"
    pof = lambda m: ("of " + tok(m)) if out[m] >= D("0.0001") else "below the reporting floor"
    t = (f"The model uses {tok('n')} complete observations, with {tok('n_excluded')} excluded as missing, and {tok('k')} predictor variable(s). "
         f"It accounts for {tok('r_squared')} of the variation in the outcome in this sample (adjusted {tok('adj_r_squared')}), a {size} effect by the declared thresholds. ")
    if "p_f" in out: t += f"The overall F test has a p-value {pof('p_f')}. "
    for nm in names:
        t += (f"Each one-unit difference in {nm} is associated with a difference of {tok('coef_' + nm)} in the outcome, holding the other predictors constant "
              f"(confidence interval at level {tok('confidence_level')} from {tok('ci_lower_' + nm)} to {tok('ci_upper_' + nm)}; p-value {ptxt('p_' + nm)}; standardized coefficient {tok('std_beta_' + nm)}). ")
    t += f"The intercept is {tok('coef_intercept')}, the fitted outcome when all predictors are zero, which may lie outside the observed range. "
    t += "Statistical significance and practical importance are separate questions."
    return t

_OLS_INPUTS = {"y": {"type": "value_list", "min_items": 6, "desc": "outcome variable; blank or null counts as missing"},
               "predictors": {"type": "column_map", "max_columns": 5, "min_items": 6, "desc": "name -> values for each predictor, paired by position with y (names: letters and underscores only)"},
               "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes; a row with any missing value is excluded"},
               "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"}, "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"}}
_OLS_THRESH = {"small_sample_n": "30", "skew_limit": "2", "kurtosis_limit": "7", "bp_alpha": "0.05", "vif_limit": "10", "cooks_limit": "1", "f2_small": "0.02", "f2_medium": "0.15", "f2_large": "0.35"}
_OLS_DEFAULTS = ({"question": "Missing-value handling", "default_chosen": "A row is excluded (listwise deletion) if the outcome or any predictor is blank, null or a declared missing code.", "impact": "Excluded rows are counted; imputation would change estimates and bias depends on the missingness mechanism."},
                 {"question": "Multiple comparisons", "default_chosen": "Coefficient p-values are reported unadjusted; no correction is applied.", "impact": "With many predictors some will look significant by chance; declare a correction in the spec if needed."},
                 {"question": "Effect-size wording thresholds", "default_chosen": "Cohen-style f-squared cut-offs 0.02, 0.15 and 0.35 for small, medium, large [PROVISIONAL, UNVERIFIED]. Standardized coefficients are also reported.", "impact": "Changes only the descriptive word."},
                 {"question": "Diagnostic screens", "default_chosen": "Residual skewness 2 and excess kurtosis 7 limits, F-form Breusch-Pagan level 0.05, largest VIF 10, largest Cook's distance 1 [PROVISIONAL, UNVERIFIED conventions]. Normality, collinearity or influence failures block; heteroskedasticity switches to HC3 robust errors as a logged amendment.", "impact": "Looser or stricter limits change which analyses are blocked."},
                 {"question": "Precision statement", "default_chosen": "Precision is conveyed by confidence intervals; no power calculation is made.", "impact": "Wide intervals signal low precision."})
_OLS_LIM = ("Linearity, independence, and the correct specification are not tested.", "No interactions, transformations, categorical predictors, weights or clustering.", "At most five predictors.", "F-form Breusch-Pagan and the diagnostic limits are conventions [UNVERIFIED].")
_OLS_ASSUME = ("Observations are independent.", "The outcome is approximately linear in the predictors.", "Residual variance is constant (screened) or robust errors are used.")

# ---------- Two independent groups: Welch t-test; Mann-Whitney fallback (manual 9B.2, 9B.3) ----------
def _grp(inp):
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}; out, ex = {}, 0
    if len(inp["groups"]) != 2: raise DataError("exactly two groups are required")
    for nm, col in inp["groups"].items():
        v = []
        for x in col:
            if x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes: ex += 1
            else: v.append(D(str(x)))
        out[nm] = v
    return out, ex

_mean = lambda v: sum(v, D(0)) / len(v)
def _var(v): m = _mean(v); return sum(((x - m) ** 2 for x in v), D(0)) / (len(v) - 1)

def welch_impl(inp):
    g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); n1, n2 = len(a), len(b)
    m1, m2, v1, v2 = _mean(a), _mean(b), _var(a), _var(b); q1, q2 = v1 / n1, v2 / n2; se2 = q1 + q2
    if se2 == 0: raise DataError("both groups have zero variance, so the t statistic is undefined")
    se = se2.sqrt(); diff = m1 - m2; t = diff / se; df = se2 ** 2 / (q1 ** 2 / (n1 - 1) + q2 ** 2 / (n2 - 1)); conf = _CONF(inp)
    tc = _fd(_t_crit(float(df), conf)); sp = (((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)).sqrt()
    gg = diff / sp * (1 - D(3) / (4 * (n1 + n2 - 2) - 1)); seg = (D(n1 + n2) / (n1 * n2) + gg * gg / (2 * (n1 + n2 - 2))).sqrt(); zc = _fd(NormalDist().inv_cdf(0.5 + float(conf) / 2))
    out = {"diff": diff, "se_diff": se, "ci_lower": diff - tc * se, "ci_upper": diff + tc * se, "t_stat": t, "df": df, "p_value": _fd(_p_t(float(t), float(df))),
           "hedges_g": gg, "g_ci_lower": gg - zc * seg, "g_ci_upper": gg + zc * seg}
    for nm, v, n_, mm, vv in ((na, a, n1, m1, v1), (nb, b, n2, m2, v2)): out[f"n_{nm}"] = D(n_); out[f"mean_{nm}"] = mm; out[f"sd_{nm}"] = vv.sqrt()
    out.update({"n_excluded": D(ex), "confidence_level": conf, "alpha": _ALPHA(inp)}); return out

def _welch_ref(inp):
    g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); a = [float(x) for x in a]; b = [float(x) for x in b]; n1, n2 = len(a), len(b)
    m1, m2, v1, v2 = statistics.fmean(a), statistics.fmean(b), statistics.variance(a), statistics.variance(b); q1, q2 = v1 / n1, v2 / n2
    se = math.sqrt(q1 + q2); diff = m1 - m2; df = (q1 + q2) ** 2 / (q1 ** 2 / (n1 - 1) + q2 ** 2 / (n2 - 1)); t = diff / se
    lo, hi = 0.0, 1e4; target = 1 - float(_CONF(inp))
    for _ in range(300):
        mid = (lo + hi) / 2
        if _betai_series(df / 2, 0.5, df / (df + mid * mid)) > target: lo = mid
        else: hi = mid
    tc = (lo + hi) / 2; sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)); gg = diff / sp * (1 - 3 / (4 * (n1 + n2 - 2) - 1))
    seg = math.sqrt((n1 + n2) / (n1 * n2) + gg * gg / (2 * (n1 + n2 - 2))); c = _norm_crit_bisect(float(_CONF(inp)))
    out = {"diff": diff, "se_diff": se, "ci_lower": diff - tc * se, "ci_upper": diff + tc * se, "t_stat": t, "df": df,
           "p_value": _betai_series(df / 2, 0.5, df / (df + t * t)), "hedges_g": gg, "g_ci_lower": gg - c * seg, "g_ci_upper": gg + c * seg, "n_excluded": ex}
    for nm, v in ((na, a), (nb, b)): out[f"n_{nm}"] = len(v); out[f"mean_{nm}"] = statistics.fmean(v); out[f"sd_{nm}"] = statistics.stdev(v)
    return out

def _mk(inp, ga, gb, **kw):
    (na, _), (nb, _) = list(inp["groups"].items()); return {**inp, "groups": {na: ga, nb: gb}, "missing_codes": [], **kw}

def _welch_tests(inp, impl):
    base, ref = impl(inp), _welch_ref(inp); g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); sa, sb = [str(x) for x in a], [str(x) for x in b]
    b0 = impl(_mk(inp, sa, sb)); sh = impl(_mk(inp, [str(x + D("250.25")) for x in a], [str(x + D("250.25")) for x in b]))
    sc = impl(_mk(inp, [str(x * 3) for x in a], [str(x * 3) for x in b])); sw = impl(_mk(inp, sb, sa)); perm = impl(_mk(inp, sa[::-1], sb[::-1]))
    pad = impl({**inp, "groups": {na: list(inp["groups"][na]) + [None], nb: list(inp["groups"][nb]) + [None]}})
    same = lambda x, y, ks, tol=1e-8: all(_rclose(x[k], y[k], tol) for k in ks)
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k]) for k in ref)),
            ("shift_leaves_difference_inference_unchanged", same(sh, b0, ("diff", "se_diff", "t_stat", "df", "p_value", "hedges_g")) and _rclose(sh[f"mean_{na}"], b0[f"mean_{na}"] + D("250.25"))),
            ("positive_scale_equivariance", _rclose(sc["diff"], b0["diff"] * 3) and _rclose(sc["se_diff"], b0["se_diff"] * 3) and same(sc, b0, ("t_stat", "df", "p_value", "hedges_g"))),
            ("swapping_groups_negates_difference_keeps_p", _rclose(sw["diff"], -b0["diff"]) and _rclose(sw["t_stat"], -b0["t_stat"]) and _rclose(sw["hedges_g"], -b0["hedges_g"]) and _rclose(sw["p_value"], b0["p_value"], 1e-9)),
            ("row_order_invariant", same(perm, b0, tuple(k for k in b0 if k != "n_excluded"), 1e-9)),
            ("missing_entries_excluded_not_valued", same(pad, base, tuple(k for k in base if k != "n_excluded"), 1e-9) and pad["n_excluded"] == base["n_excluded"] + 2),
            ("bounded_and_consistent", base["ci_lower"] <= base["diff"] <= base["ci_upper"] and base["g_ci_lower"] <= base["hedges_g"] <= base["g_ci_upper"] and 0 <= base["p_value"] <= 1
                                      and min(len(a), len(b)) - 1 - D("1e-9") <= base["df"] <= len(a) + len(b) - 2 + D("1e-9") and base["se_diff"] > 0 and (base["diff"] >= 0) == (base["hedges_g"] >= 0))]

def _mwu(a, b):
    n1, n2 = len(a), len(b); U = sum((1 if x > y else D("0.5") if x == y else 0) for x in a for y in b); U = float(U); N = n1 + n2
    from collections import Counter
    ties = sum(c ** 3 - c for c in Counter(list(a) + list(b)).values()); s2 = n1 * n2 / 12 * ((N + 1) - ties / (N * (N - 1)))
    if s2 <= 0: raise DataError("all observations are tied, so the Mann-Whitney test is undefined")
    z = max(0.0, (abs(U - n1 * n2 / 2) - 0.5) / math.sqrt(s2)); return U, min(1.0, math.erfc(z / math.sqrt(2)))

def mwu_impl(inp):
    g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); n1, n2 = len(a), len(b); U, p = _mwu(a, b); alpha = float(_ALPHA(inp))
    fa, fb = [float(x) for x in a], [float(x) for x in b]; diffs = sorted(x - y for x in fa for y in fb); hl = statistics.median(diffs)
    pshift = lambda d: _mwu([x - d for x in fa], fb)[1]
    if pshift(hl) <= alpha: raise DataError("too few observations for an interval at this confidence level")
    ends = []
    for hi_side in (True, False):
        inner, outer = hl, (diffs[-1] + 1.0 if hi_side else diffs[0] - 1.0)
        if pshift(outer) > alpha: raise DataError("too few observations for a bounded interval at this confidence level (each group needs about four or more)")
        for _ in range(200):
            mid = (inner + outer) / 2
            if pshift(mid) > alpha: inner = mid
            else: outer = mid
        ends.append(outer)
    out = {"u_stat": _fd(U), "p_value": _fd(p), "rank_biserial": 2 * _fd(U) / (n1 * n2) - 1, "hl_shift": _fd(hl), "ci_lower": _fd(ends[1]), "ci_upper": _fd(ends[0])}
    for nm, v in ((na, a), (nb, b)): out[f"n_{nm}"] = D(len(v)); out[f"median_{nm}"] = statistics.median(sorted(v))
    out.update({"n_excluded": D(ex), "confidence_level": _CONF(inp), "alpha": _ALPHA(inp)}); return out

def _mwu_ref(inp):
    from collections import Counter
    g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); fa, fb = [float(x) for x in a], [float(x) for x in b]; n1, n2 = len(fa), len(fb); N = n1 + n2
    rk = _rank_reference(fa + fb); U = sum(rk[:n1]) - n1 * (n1 + 1) / 2; ties = sum(c ** 3 - c for c in Counter(fa + fb).values())
    s2 = n1 * n2 / 12 * ((N + 1) - ties / (N * (N - 1))); z = max(0.0, (abs(U - n1 * n2 / 2) - 0.5) / math.sqrt(s2))
    return {"u_stat": U, "p_value": min(1.0, 2 * (1 - NormalDist().cdf(z))), "rank_biserial": 2 * U / (n1 * n2) - 1, "hl_shift": statistics.median([x - y for y in fb for x in fa]), "n_excluded": ex}

def _mwu_tests(inp, impl):
    base, ref = impl(inp), _mwu_ref(inp); g, ex = _grp(inp); (na, a), (nb, b) = list(g.items()); sa, sb = [str(x) for x in a], [str(x) for x in b]
    b0 = impl(_mk(inp, sa, sb)); cube = impl(_mk(inp, [str(x ** 3) for x in a], [str(x ** 3) for x in b])); sw = impl(_mk(inp, sb, sa))
    sh = impl(_mk(inp, [str(x + D("250.25")) for x in a], [str(x + D("250.25")) for x in b])); sc = impl(_mk(inp, [str(x * 3) for x in a], [str(x * 3) for x in b]))
    perm = impl(_mk(inp, sa[::-1], sb[::-1])); pad = impl({**inp, "groups": {na: list(inp["groups"][na]) + [None], nb: list(inp["groups"][nb]) + [None]}}); same_ = impl(_mk(inp, sa, sa))
    fa, fb = [float(x) for x in a], [float(x) for x in b]; alpha = float(_ALPHA(inp)); e = 1e-7 * max(1.0, abs(float(base["ci_upper"])), abs(float(base["ci_lower"])))
    pshift = lambda d: _mwu([D(repr(x - d)) for x in fa], [D(repr(y)) for y in fb])[1]
    K = lambda x, y, ks: all(_rclose(x[k], y[k], 1e-9) for k in ks)
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k], 1e-8) for k in ref)),
            ("interval_is_test_inversion", pshift(float(base["ci_upper"]) - e) > alpha >= pshift(float(base["ci_upper"]) + e) and pshift(float(base["ci_lower"]) + e) > alpha >= pshift(float(base["ci_lower"]) - e)),
            ("monotone_transform_keeps_rank_statistics", K(cube, b0, ("u_stat", "p_value", "rank_biserial"))),
            ("swapping_groups_flips_effect_keeps_p", _rclose(sw["rank_biserial"], -b0["rank_biserial"], 1e-9) and _rclose(sw["p_value"], b0["p_value"], 1e-9) and _rclose(sw["hl_shift"], -b0["hl_shift"], 1e-9)),
            ("shift_and_scale_behave", K(sh, b0, ("u_stat", "p_value", "rank_biserial", "hl_shift")) and _rclose(sc["hl_shift"], b0["hl_shift"] * 3, 1e-9) and K(sc, b0, ("p_value", "rank_biserial"))),
            ("row_order_invariant", K(perm, b0, tuple(k for k in b0 if k != "n_excluded"))),
            ("missing_entries_excluded_not_valued", K(pad, base, tuple(k for k in base if k != "n_excluded")) and pad["n_excluded"] == base["n_excluded"] + 2),
            ("identical_samples_give_no_effect", same_["rank_biserial"] == 0 and same_["p_value"] == 1),
            ("bounded_and_consistent", 0 <= base["u_stat"] <= len(a) * len(b) and abs(base["rank_biserial"]) <= 1 and 0 <= base["p_value"] <= 1 and base["ci_lower"] <= base["hl_shift"] <= base["ci_upper"])]

def groups_normality(inp, th):
    g, _ = _grp(inp); sl, kl = float(th.get("skew_limit", "2")), float(th.get("kurtosis_limit", "7")); bad = []
    for nm, v in g.items():
        sk, ku = _moments(v)
        if abs(sk) > sl or abs(ku) > kl: bad.append(f"{nm}: skewness {sk:.2f}, excess kurtosis {ku:.2f}")
    return [("group_normality_screen", not bad, "; ".join(bad) or "within declared limits")]

def groups_profile(inp):
    issues = []
    try: g, ex = _grp(inp)
    except DataError as e: return [str(e)]
    for nm, v in g.items():
        if len(v) < 3: issues.append(f"group '{nm}' has fewer than three valid observations")
    if not (0 < _CONF(inp) < 1): issues.append("confidence_level must be between 0 and 1")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def groups_typing(metric):
    if metric.startswith("n_") or metric == "df" and False: return "count", 0
    if metric in ("confidence_level", "alpha"): return "rate", 2
    if metric == "p_value": return "probability", 4
    if metric in ("t_stat", "df", "hedges_g", "g_ci_lower", "g_ci_upper", "rank_biserial", "u_stat"): return "ratio", 3
    return "@unit", 3

def _names(out, prefix): return [k[len(prefix):] for k in out if k.startswith(prefix)]

def groups_caveats(out, th):
    nm = _names(out, "n_"); nm = [x for x in nm if x != "excluded"]; c = []
    if sum(int(out[f"n_{x}"]) for x in nm) < int(th.get("small_sample_n", 30)): c.append("Caution: the groups are small, so these estimates are imprecise and should be described, not generalized.")
    c.append("A difference between groups does not show that group membership produces it; assignment and other differences between the groups were not assessed, and no causal claim is made.")
    c.append("Check the data for outliers and entry errors before relying on the comparison." if "diff" in out else "The interval and p-value are normal approximations with a continuity correction, and are less accurate for very small groups.")
    return c

def _size(x, th, kind):
    a = abs(x); g = lambda k, d: D(str(th.get(k, d)))
    lo, mid, hi = (g("g_small", "0.2"), g("g_medium", "0.5"), g("g_large", "0.8")) if kind == "g" else (g("effect_small", "0.1"), g("effect_medium", "0.3"), g("effect_large", "0.5"))
    return "negligible" if a < lo else "small" if a < mid else "medium" if a < hi else "large"

def welch_template(out, P, th):
    a, b = [x for x in _names(out, "mean_")]; tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); pp = out["p_value"]
    t = (f"Group {a} has {tok('n_' + a)} valid observations with a mean of {tok('mean_' + a)}, and group {b} has {tok('n_' + b)} with a mean of {tok('mean_' + b)}; {tok('n_excluded')} entries were excluded as missing. "
         f"The difference in means ({a} minus {b}) is {tok('diff')}, with a confidence interval at level {tok('confidence_level')} from {tok('ci_lower')} to {tok('ci_upper')}. "
         f"Welch's test gives a p-value " + ("of " + tok("p_value") if pp >= D("0.0001") else "below the reporting floor") + ". ")
    t += (f"The standardized difference (Hedges' g) is {tok('hedges_g')}, a {_size(out['hedges_g'], th, 'g')} difference by the declared thresholds, with an interval from {tok('g_ci_lower')} to {tok('g_ci_upper')}. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:%s}} the difference is statistically significant. " if pp < out["alpha"] else "At the declared significance level of {{ref:alpha:alpha:%s}} the difference is not statistically significant. ") % P
    return t + "Statistical significance and practical importance are separate questions."

def mwu_template(out, P, th):
    a, b = [x for x in _names(out, "median_")]; tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); pp = out["p_value"]
    t = (f"Group {a} has {tok('n_' + a)} valid observations with a median of {tok('median_' + a)}, and group {b} has {tok('n_' + b)} with a median of {tok('median_' + b)}; {tok('n_excluded')} entries were excluded as missing. "
         f"The Hodges-Lehmann estimate of the shift ({a} minus {b}) is {tok('hl_shift')}, with a confidence interval at level {tok('confidence_level')} from {tok('ci_lower')} to {tok('ci_upper')}. "
         f"The Mann-Whitney test gives a p-value " + ("of " + tok("p_value") if pp >= D("0.0001") else "below the reporting floor") + ". "
         f"The rank-biserial correlation is {tok('rank_biserial')}, a {_size(out['rank_biserial'], th, 'r')} difference by the declared thresholds. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:%s}} the difference is statistically significant. " if pp < out["alpha"] else "At the declared significance level of {{ref:alpha:alpha:%s}} the difference is not statistically significant. ") % P
    return t + "Statistical significance and practical importance are separate questions."

_GRP_INPUTS = {"groups": {"type": "column_map", "min_columns": 2, "max_columns": 2, "min_items": 3, "desc": "exactly two groups: name -> observations (letters and underscores in names; group sizes may differ)"},
               "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes"},
               "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"}, "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"}}
_GRP_THRESH = {"small_sample_n": "30", "skew_limit": "2", "kurtosis_limit": "7", "g_small": "0.2", "g_medium": "0.5", "g_large": "0.8", "effect_small": "0.1", "effect_medium": "0.3", "effect_large": "0.5"}
_GRP_DEFAULTS = ({"question": "Missing-value handling", "default_chosen": "Blank, null and declared missing codes are excluded within each group and counted.", "impact": "Excluded counts are reported."},
                 {"question": "Test choice", "default_chosen": "Welch's unequal-variance t-test (no equal-variance assumption), two-sided.", "impact": "Student's pooled t-test gives different degrees of freedom and p-values when variances or group sizes differ."},
                 {"question": "Standardized effect size", "default_chosen": "Hedges' g using the pooled standard deviation, with a large-sample normal interval [approximate]. Cohen-style cut-offs 0.2, 0.5, 0.8 [UNVERIFIED conventions].", "impact": "Using each group's SD (Glass) or the Welch-style average changes g."},
                 {"question": "Multiple comparisons", "default_chosen": "One test, so no correction.", "impact": "Several comparisons inflate false positives; declare a correction in the spec."},
                 {"question": "Assumption screen and fallback", "default_chosen": "If either group's skewness or excess kurtosis exceeds the declared limits, switch to the Mann-Whitney test as a logged amendment.", "impact": "Mann-Whitney compares rank distributions and reports a median-type shift, not a mean difference."})

# ---------- One-way ANOVA with pre-declared fallbacks to Kruskal-Wallis (manual 9B.2, 9B.3) ----------
def _groups_multi(inp):
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}; out, ex = {}, 0
    for nm, col in inp["groups"].items():
        v = []
        for x in col:
            if x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes: ex += 1
            else: v.append(D(str(x)))
        out[nm] = v
    return out, ex

# --- chi-square survival of the incomplete gamma: primary (NR series + continued fraction) and reference (exact integer-df closed form) ---
def _gser(a, x):
    ap = a; s = 1.0 / a; de = s
    for _ in range(500):
        ap += 1.0; de *= x / ap; s += de
        if abs(de) < abs(s) * 1e-16: break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))

def _gcf(a, x):
    b = x + 1.0 - a; c = 1e300; d = 1.0 / b; h = d
    for i in range(1, 500):
        an = -i * (i - a); b += 2.0
        d = an * d + b; d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c; c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < 1e-16: break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h

def _gammq(a, x):
    if x <= 0: return 1.0
    return 1.0 - _gser(a, x) if x < a + 1.0 else _gcf(a, x)

def _chi2_survival(x, df): return _gammq(df / 2.0, x / 2.0)

def _chi2_survival_ref(x, df):
    """Independent route: exact survival for integer degrees of freedom (Poisson sum for even df; erfc series for odd df)."""
    x, df, half = float(x), int(df), float(x) / 2.0
    if x <= 0: return 1.0
    if df % 2 == 0:
        m = df // 2; s = 0.0; term = 1.0
        for j in range(m): s += term; term *= half / (j + 1)
        return math.exp(-half) * s
    m = (df - 1) // 2; s = 0.0; dbl = 1.0; xp = math.sqrt(x)
    for i in range(m): s += xp / dbl; xp *= x; dbl *= (2 * i + 3)
    return 2.0 * (1.0 - NormalDist().cdf(math.sqrt(x))) + math.exp(-half) * math.sqrt(2.0 / math.pi) * s

def anova_impl(inp):
    g, ex = _groups_multi(inp); names = list(g); k, N = len(names), sum((len(v) for v in g.values()))
    if k < 2: raise DataError("at least two groups are required")
    if N - k < 1: raise DataError("not enough observations for the degrees of freedom")
    grand = sum((sum(v, D(0)) for v in g.values()), D(0)) / N
    ssb = sum((D(len(g[nm])) * (_mean(g[nm]) - grand) ** 2 for nm in names), D(0))
    ssw = sum((sum(((x - _mean(g[nm])) ** 2 for x in g[nm]), D(0)) for nm in names), D(0))
    if ssw == 0: raise DataError("all observations within each group are identical, so the within-group variance is zero")
    dfb, dfw = D(k - 1), D(N - k); msb, msw = ssb / dfb, ssw / dfw; F = msb / msw
    p = _fd(_betai(float(dfw) / 2, float(dfb) / 2, float(dfw) / (float(dfw) + float(dfb) * float(F))))
    sst = ssb + ssw; eta2 = ssb / sst if sst != 0 else D(0)
    out = {"f_stat": F, "df_between": dfb, "df_within": dfw, "p_value": p, "eta_squared": eta2, "n_groups": D(k), "n_total": D(N), "n_excluded": D(ex), "grand_mean": grand, "alpha": _ALPHA(inp)}
    for nm in names: out[f"n_{nm}"] = D(len(g[nm])); out[f"mean_{nm}"] = _mean(g[nm]); out[f"sd_{nm}"] = _var(g[nm]).sqrt()
    return out

def _anova_ref(inp):
    """Independent route: float arithmetic and the series incomplete beta (a different algorithm from the Decimal fit and continued fraction)."""
    g, ex = _groups_multi(inp); names = list(g); N = sum((len(v) for v in g.values())); k = len(names)
    fa = {nm: [float(x) for x in v] for nm, v in g.items()}
    grand = sum((sum(v) for v in fa.values()), 0.0) / N
    ssb = sum((len(fa[nm]) * (statistics.fmean(fa[nm]) - grand) ** 2 for nm in names), 0.0)
    ssw = sum((sum(((x - statistics.fmean(fa[nm])) ** 2 for x in fa[nm]), 0.0) for nm in names), 0.0)
    dfb, dfw = k - 1, N - k; F = (ssb / dfb) / (ssw / dfw)
    out = {"f_stat": F, "df_between": dfb, "df_within": dfw, "p_value": _betai_series(dfw / 2, dfb / 2, dfw / (dfw + dfb * F)), "eta_squared": ssb / (ssb + ssw), "n_groups": k, "n_total": N, "n_excluded": ex, "grand_mean": grand}
    for nm in names: out[f"n_{nm}"] = len(fa[nm]); out[f"mean_{nm}"] = statistics.fmean(fa[nm]); out[f"sd_{nm}"] = statistics.stdev(fa[nm])
    return out

def _amk(inp, cols): return {**inp, "groups": cols, "missing_codes": []}

def _anova_tests(inp, impl):
    base, ref = impl(inp), _anova_ref(inp); g, _ = _groups_multi(inp); names = list(g)
    strs = {nm: [str(x) for x in v] for nm, v in g.items()}; b0 = impl(_amk(inp, strs))
    nms = names[:]; nms[0], nms[1] = nms[1], nms[0]; rel = impl(_amk(inp, {nm: strs[nm] for nm in nms}))
    perm = impl(_amk(inp, {nm: v[::-1] for nm, v in strs.items()}))
    sh = impl(_amk(inp, {nm: [str(D(v) + D("250.25")) for v in lst] for nm, lst in strs.items()}))
    sc = impl(_amk(inp, {nm: [str(D(v) * 3) for v in lst] for nm, lst in strs.items()}))
    pad = impl({**inp, "groups": {nm: list(col) + [None] for nm, col in inp["groups"].items()}})
    K = lambda x, y, ks: all(_rclose(x[k], y[k], 1e-9) for k in ks); FKEYS = ("f_stat", "p_value", "eta_squared")
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k], 1e-8) for k in ref)),
            ("within_group_permutation_invariant", K(perm, b0, tuple(k for k in b0 if k != "n_excluded"))),
            ("group_relabeling_invariant", K(rel, b0, FKEYS)),
            ("equal_shift_leaves_F_and_effect_unchanged", K(sh, b0, FKEYS) and all(_rclose(sh[f"mean_{nm}"], b0[f"mean_{nm}"] + D("250.25")) for nm in names)),
            ("positive_scale_equivariance", K(sc, b0, FKEYS) and all(_rclose(sc[f"mean_{nm}"], b0[f"mean_{nm}"] * 3) and _rclose(sc[f"sd_{nm}"], b0[f"sd_{nm}"] * 3) for nm in names)),
            ("missing_entries_excluded_not_valued", K(pad, base, tuple(k for k in base if k != "n_excluded")) and pad["n_excluded"] == base["n_excluded"] + len(names)),
            ("bounded_and_consistent", base["f_stat"] >= 0 and 0 <= base["eta_squared"] <= 1 and 0 <= base["p_value"] <= 1 and base["df_between"] + base["df_within"] == base["n_total"] - 1)]

def kw_impl(inp):
    g, ex = _groups_multi(inp); names = list(g); N = sum((len(v) for v in g.values())); k = len(names)
    if k < 2: raise DataError("at least two groups are required")
    allv = [x for v in g.values() for x in v]; ranks = _ranks(allv); rsums, idx = {}, 0
    for nm in names: rsums[nm] = sum((ranks[idx:idx + len(g[nm])]), D(0)); idx += len(g[nm])
    H = D(12) / (N * (N + 1)) * sum((rsums[nm] ** 2 / len(g[nm]) for nm in names), D(0)) - D(3) * (N + 1)
    from collections import Counter
    ties = sum((c ** 3 - c for c in Counter([str(x) for x in allv]).values())); corr = D(1) - D(ties) / (N ** 3 - N); Hc = H / corr if corr != 0 else H
    out = {"h_stat": Hc, "df": D(k - 1), "p_value": _fd(_chi2_survival(float(Hc), k - 1)), "epsilon_squared": Hc / (N - 1), "n_groups": D(k), "n_total": D(N), "n_excluded": D(ex), "alpha": _ALPHA(inp)}
    for nm in names: out[f"n_{nm}"] = D(len(g[nm])); out[f"median_{nm}"] = statistics.median(sorted(g[nm]))
    return out

def _kw_ref(inp):
    """Independent route: counting-based ranks and the exact integer-df chi-square survival."""
    g, ex = _groups_multi(inp); names = list(g); N = sum((len(v) for v in g.values())); k = len(names)
    fa = [float(x) for v in g.values() for x in v]; rk = _rank_reference(fa); rsums, idx = {}, 0
    for nm in names: rsums[nm] = sum((rk[idx:idx + len(g[nm])])); idx += len(g[nm])
    H = 12.0 / (N * (N + 1)) * sum((rs ** 2 / len(g[nm]) for nm, rs in rsums.items()), 0.0) - 3.0 * (N + 1)
    from collections import Counter
    ties = sum((c ** 3 - c for c in Counter(fa).values())); corr = 1.0 - ties / (N ** 3 - N); Hc = H / corr if corr else H
    return {"h_stat": Hc, "df": k - 1, "p_value": _chi2_survival_ref(Hc, k - 1), "epsilon_squared": Hc / (N - 1), "n_groups": k, "n_total": N, "n_excluded": ex}

def _kw_tests(inp, impl):
    base, ref = impl(inp), _kw_ref(inp); g, _ = _groups_multi(inp); names = list(g)
    strs = {nm: [str(x) for x in v] for nm, v in g.items()}; b0 = impl(_amk(inp, strs))
    cube = impl(_amk(inp, {nm: [str(D(v) ** 3) for v in lst] for nm, lst in strs.items()}))
    sh = impl(_amk(inp, {nm: [str(D(v) + D("250.25")) for v in lst] for nm, lst in strs.items()}))
    nms = names[:]; nms[0], nms[1] = nms[1], nms[0]; rel = impl(_amk(inp, {nm: strs[nm] for nm in nms}))
    perm = impl(_amk(inp, {nm: v[::-1] for nm, v in strs.items()}))
    pad = impl({**inp, "groups": {nm: list(col) + [None] for nm, col in inp["groups"].items()}})
    K = lambda x, y, ks: all(_rclose(x[k], y[k], 1e-9) for k in ks); RKEYS = ("h_stat", "p_value", "epsilon_squared")
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k], 1e-8) for k in ref)),
            ("monotone_transform_keeps_ranks", K(cube, b0, RKEYS)),
            ("shift_invariant", K(sh, b0, RKEYS)),
            ("group_relabeling_invariant", K(rel, b0, RKEYS)),
            ("within_group_permutation_invariant", K(perm, b0, tuple(k for k in b0 if k != "n_excluded"))),
            ("missing_entries_excluded_not_valued", K(pad, base, tuple(k for k in base if k != "n_excluded")) and pad["n_excluded"] == base["n_excluded"] + len(names)),
            ("bounded_and_consistent", base["h_stat"] >= 0 and 0 <= base["epsilon_squared"] <= 1 and 0 <= base["p_value"] <= 1)]

# ---------- Chi-square test of independence on a table of observed counts (manual 9B.2, 9B.3) ----------
def chi_square_impl(inp):
    tbl = [[D(str(x)) for x in row] for row in inp["table"]]; R, C = len(tbl), len(tbl[0])
    rt = [sum(r, D(0)) for r in tbl]; ct = [sum((tbl[i][j] for i in range(R)), D(0)) for j in range(C)]; N = sum(rt, D(0))
    if N == 0: raise DataError("the table has no observations")
    chi2 = sum(((tbl[i][j] - rt[i] * ct[j] / N) ** 2 / (rt[i] * ct[j] / N) for i in range(R) for j in range(C) if rt[i] * ct[j] != 0), D(0))
    df = (R - 1) * (C - 1); p = _fd(_chi2_survival(float(chi2), df)); V = (chi2 / (N * min(R - 1, C - 1))).sqrt()
    mine = min((rt[i] * ct[j] / N for i in range(R) for j in range(C)))
    return {"chi_squared": chi2, "df": D(df), "p_value": p, "cramers_v": V, "n_total": D(N), "n_cells": D(R * C), "min_expected_count": mine, "alpha": _ALPHA(inp)}

def _chi2_ref(inp):
    """Independent route: float recomputation and the exact integer-df chi-square survival."""
    tbl = [[float(x) for x in row] for row in inp["table"]]; R, C = len(tbl), len(tbl[0])
    rt = [sum(r) for r in tbl]; ct = [sum((tbl[i][j] for i in range(R))) for j in range(C)]; N = sum(rt)
    chi2 = sum(((tbl[i][j] - rt[i] * ct[j] / N) ** 2 / (rt[i] * ct[j] / N) for i in range(R) for j in range(C) if rt[i] * ct[j] > 0))
    df = (R - 1) * (C - 1)
    return {"chi_squared": chi2, "df": df, "p_value": _chi2_survival_ref(chi2, df), "cramers_v": (chi2 / (N * min(R - 1, C - 1))) ** 0.5, "n_total": N, "n_cells": R * C,
            "min_expected_count": min((rt[i] * ct[j] / N for i in range(R) for j in range(C)))}

def _chi2_tests(inp, impl):
    base, ref = impl(inp), _chi2_ref(inp); tbl = inp["table"]
    rows_perm = impl({"table": [list(r) for r in tbl[::-1]]})
    transp = impl({"table": [list(row) for row in zip(*tbl)]})
    scaled = impl({"table": [[int(x) * 2 for x in row] for row in tbl]})
    indep = impl({"table": [[10, 20, 30], [20, 40, 60]]})
    K = lambda x, y, ks: all(_rclose(x[k], y[k], 1e-9) for k in ks)
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k], 1e-8) for k in ref)),
            ("row_order_invariant", K(rows_perm, base, ("chi_squared", "p_value", "cramers_v", "df"))),
            ("transpose_invariant", K(transp, base, ("chi_squared", "p_value", "df"))),
            ("uniform_scaling_scales_chi2_keeps_V", _rclose(scaled["chi_squared"], base["chi_squared"] * 2) and _rclose(scaled["cramers_v"], base["cramers_v"], 1e-9)),
            ("independence_gives_zero_chi2", indep["chi_squared"] == 0 and indep["p_value"] == 1 and indep["cramers_v"] == 0),
            ("bounded_and_consistent", base["chi_squared"] >= 0 and 0 <= base["cramers_v"] <= 1 and 0 <= base["p_value"] <= 1)]

def anova_normality(inp, th):
    g, _ = _groups_multi(inp); sl, kl = float(th.get("skew_limit", "2")), float(th.get("kurtosis_limit", "7")); bad = []
    for nm, v in g.items():
        sk, ku = _moments(v)
        if abs(sk) > sl or abs(ku) > kl: bad.append(f"{nm}: skewness {sk:.2f}, excess kurtosis {ku:.2f}")
    return [("group_normality_screen", not bad, "; ".join(bad) or "within declared limits")]

def anova_homogeneity(inp, th):
    """Levene's test (mean version) on absolute deviations; W is F(k-1, N-k) under equal variances."""
    g, _ = _groups_multi(inp); names = list(g); k, N = len(names), sum((len(v) for v in g.values()))
    if k < 2 or N - k < 1: return [("homogeneity_of_variance_screen", False, "not enough observations for Levene's test")]
    Z = {nm: [abs(x - _mean(g[nm])) for x in g[nm]] for nm in names}; zb = {nm: _mean(Z[nm]) for nm in names}
    gz = sum((sum(Z[nm], D(0)) for nm in names), D(0)) / N
    ssb = sum((D(len(Z[nm])) * (zb[nm] - gz) ** 2 for nm in names), D(0))
    ssw = sum((sum(((z - zb[nm]) ** 2 for z in Z[nm]), D(0)) for nm in names), D(0))
    if ssw == 0: return [("homogeneity_of_variance_screen", True, "within-group deviations are constant; no evidence of unequal variance")]
    W = D(N - k) / D(k - 1) * ssb / ssw; p = _fd(_betai(float(N - k) / 2, float(k - 1) / 2, float(N - k) / (float(N - k) + float(k - 1) * float(W))))
    lev = float(th.get("levene_alpha", "0.05"))
    return [("homogeneity_of_variance_screen", p >= lev, f"Levene W {float(W):.2f}, p {float(p):.4f}; declared level {lev:g}")]

def anova_checks(inp, th): return anova_normality(inp, th) + anova_homogeneity(inp, th)

def chi2_screen(inp, th):
    tbl = [[D(str(x)) for x in row] for row in inp["table"]]; R, C = len(tbl), len(tbl[0])
    rt = [sum(r, D(0)) for r in tbl]; ct = [sum((tbl[i][j] for i in range(R)), D(0)) for j in range(C)]; N = sum(rt, D(0))
    if N == 0: return [("minimum_expected_count", False, "the table has no observations")]
    mine = min((rt[i] * ct[j] / N for i in range(R) for j in range(C))); lim = D(str(th.get("min_expected", "5")))
    return [("minimum_expected_count", mine >= lim, f"smallest expected count {float(mine):.2f}; declared minimum {float(lim):g}")]

def chi2_checks(inp, th): return chi2_screen(inp, th)

def anova_profile(inp):
    issues = []
    g, _ = _groups_multi(inp); names = list(g); N = sum((len(v) for v in g.values()))
    if len(names) < 3: issues.append("one-way ANOVA compares at least three groups")
    for nm, v in g.items():
        if len(v) < 2: issues.append(f"group '{nm}' has fewer than two valid observations")
    if N - len(names) < 1: issues.append("not enough observations for the degrees of freedom")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def kw_profile(inp):
    issues = []
    g, _ = _groups_multi(inp); names = list(g)
    if len(names) < 3: issues.append("Kruskal-Wallis compares at least three groups")
    for nm, v in g.items():
        if len(v) < 2: issues.append(f"group '{nm}' has fewer than two valid observations")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def chi2_profile(inp):
    tbl = inp["table"]; R, C = len(tbl), len(tbl[0]); issues = []
    rt = [sum((D(str(x)) for x in row), D(0)) for row in tbl]; ct = [sum((D(str(tbl[i][j])) for i in range(R)), D(0)) for j in range(C)]
    if sum(rt, D(0)) == 0: issues.append("the table has no observations")
    if any(r == 0 for r in rt): issues.append("a row sums to zero")
    if any(c == 0 for c in ct): issues.append("a column sums to zero")
    if not (0 < _ALPHA(inp) < 1): issues.append("alpha must be between 0 and 1")
    return issues

def anova_typing(metric):
    if metric == "p_value": return "probability", 4
    if metric == "alpha": return "rate", 2
    if metric in ("f_stat", "eta_squared"): return "ratio", 3
    if metric.startswith("n_") or metric.startswith("df"): return "count", 0
    return "@unit", 3

def kw_typing(metric):
    if metric == "p_value": return "probability", 4
    if metric == "alpha": return "rate", 2
    if metric in ("h_stat", "epsilon_squared"): return "ratio", 3
    if metric.startswith("n_") or metric.startswith("df"): return "count", 0
    return "@unit", 3

def chi2_typing(metric):
    if metric == "p_value": return "probability", 4
    if metric == "alpha": return "rate", 2
    if metric in ("chi_squared", "cramers_v"): return "ratio", 3
    if metric.startswith("n_") or metric.startswith("df") or metric == "min_expected_count": return "count", 0
    return "@unit", 3

def _eta_size(x, th):
    a = abs(x); g = lambda k, d: D(str(th.get(k, d)))
    return "negligible" if a < g("eta_small", "0.01") else "small" if a < g("eta_medium", "0.06") else "medium" if a < g("eta_large", "0.14") else "large"

def _cramers_size(x, th):
    a = abs(x); g = lambda k, d: D(str(th.get(k, d)))
    return "negligible" if a < g("v_small", "0.1") else "small" if a < g("v_medium", "0.3") else "medium" if a < g("v_large", "0.5") else "large"

def anova_caveats(out, th):
    c = []
    if int(out["n_total"]) < int(th.get("small_sample_n", 30)): c.append("Caution: the sample is small, so these estimates are imprecise and should be described, not generalized.")
    c.append("A difference among group means does not show that group membership produces it; assignment and other differences between groups were not assessed, and no causal claim is made.")
    c.append("The normality and equal-variance screens are coarse; inspect the data before relying on the result.")
    return c

def kw_caveats(out, th):
    c = []
    if int(out["n_total"]) < int(th.get("small_sample_n", 30)): c.append("Caution: the sample is small, so these estimates are imprecise and should be described, not generalized.")
    c.append("Kruskal-Wallis compares rank distributions, not means; a difference does not show that group membership produces it, and no causal claim is made.")
    c.append("The p-value uses a chi-square approximation that is less accurate for small groups.")
    return c

def chi2_caveats(out, th):
    c = []
    if out["min_expected_count"] < D(str(th.get("min_expected", "5"))): c.append("Some expected counts are small, so the chi-square p-value is approximate.")
    c.append("An association between the row and column variables does not show that one causes the other.")
    c.append("The test treats the counts as independent observations of a single sample.")
    return c

def anova_template(out, P, th):
    names = _names(out, "mean_"); tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); pp = out["p_value"]
    t = f"The analysis compares {tok('n_groups')} groups. " + " ".join(f"Group {nm} has {tok('n_' + nm)} valid observations with a mean of {tok('mean_' + nm)};" for nm in names)
    t += f" {tok('n_excluded')} entries were excluded as missing. One-way ANOVA gives F({tok('df_between')}, {tok('df_within')}) = {tok('f_stat')} with a p-value "
    t += ("of " + tok("p_value") + ". " if pp >= D("0.0001") else "below the reporting floor. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:%s}} the group means are statistically significantly different. " if pp < out["alpha"] else "At the declared significance level of {{ref:alpha:alpha:%s}} the group means are not statistically significantly different. ") % P
    t += f"Eta-squared is {tok('eta_squared')}, a {_eta_size(out['eta_squared'], th)} effect by the declared thresholds. "
    return t + "Statistical significance and practical importance are separate questions."

def kw_template(out, P, th):
    names = _names(out, "median_"); tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); pp = out["p_value"]
    t = f"The analysis compares {tok('n_groups')} groups. " + " ".join(f"Group {nm} has {tok('n_' + nm)} valid observations with a median of {tok('median_' + nm)};" for nm in names)
    t += f" {tok('n_excluded')} entries were excluded as missing. Kruskal-Wallis gives H = {tok('h_stat')} with a p-value "
    t += ("of " + tok("p_value") + ". " if pp >= D("0.0001") else "below the reporting floor. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:%s}} the rank distributions are statistically significantly different. " if pp < out["alpha"] else "At the declared significance level of {{ref:alpha:alpha:%s}} the rank distributions are not statistically significantly different. ") % P
    t += f"Epsilon-squared is {tok('epsilon_squared')}, a {_eta_size(out['epsilon_squared'], th)} effect by the declared thresholds. "
    return t + "Statistical significance and practical importance are separate questions."

def chi2_template(out, P, th):
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); pp = out["p_value"]
    t = (f"The table has {tok('n_total')} observations across {tok('n_cells')} cells. The chi-square test of independence gives chi-squared = {tok('chi_squared')} with {tok('df')} degree(s) of freedom and a p-value ")
    t += ("of " + tok("p_value") + ". " if pp >= D("0.0001") else "below the reporting floor. ")
    t += ("At the declared significance level of {{ref:alpha:alpha:%s}} the row and column variables are statistically significantly associated. " if pp < out["alpha"] else "At the declared significance level of {{ref:alpha:alpha:%s}} the row and column variables are not statistically significantly associated. ") % P
    t += f"Cramer's V is {tok('cramers_v')}, a {_cramers_size(out['cramers_v'], th)} association by the declared thresholds. The smallest expected count is {tok('min_expected_count')}."
    return t + " Statistical significance and practical importance are separate questions."

_ANOVA_INPUTS = {"groups": {"type": "column_map", "min_columns": 3, "max_columns": 12, "min_items": 2, "desc": "three or more groups: name -> observations (letters and underscores in names; sizes may differ)"},
                 "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes"},
                 "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"}}
_CHI2_INPUTS = {"table": {"type": "count_table", "min_rows": 2, "min_cols": 2, "desc": "a table of non-negative whole-number counts (rows x columns)"},
                "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"}}
_ANOVA_THRESH = {"small_sample_n": "30", "skew_limit": "2", "kurtosis_limit": "7", "levene_alpha": "0.05", "eta_small": "0.01", "eta_medium": "0.06", "eta_large": "0.14"}
_KW_THRESH = {"small_sample_n": "30", "eta_small": "0.01", "eta_medium": "0.06", "eta_large": "0.14"}
_CHI2_THRESH = {"min_expected": "5", "v_small": "0.1", "v_medium": "0.3", "v_large": "0.5"}
_ANOVA_DEFAULTS = (
    {"question": "Missing-value handling", "default_chosen": "Blank, null and declared missing codes are excluded within each group and counted.", "impact": "Excluded counts are reported."},
    {"question": "Test", "default_chosen": "One-way independent ANOVA (F test), two-sided, comparing group means.", "impact": "Repeated-measures, two-way and ANCOVA designs are not supported."},
    {"question": "Effect size", "default_chosen": "Eta-squared (between-group SS over total SS), with Cohen-style cut-offs 0.01, 0.06, 0.14 [UNVERIFIED conventions].", "impact": "Omega-squared (less biased) is not reported."},
    {"question": "Assumption screens and fallback", "default_chosen": "If any group's skewness or excess kurtosis exceeds the declared limits, or Levene's test for equal variances rejects at the declared level, switch to Kruskal-Wallis as a logged amendment.", "impact": "Kruskal-Wallis compares rank distributions, not means."},
    {"question": "Multiple comparisons", "default_chosen": "The omnibus F test makes no pairwise comparisons, so no correction is applied.", "impact": "Post-hoc pairwise tests would need their own correction."})
_KW_DEFAULTS = (
    {"question": "Missing-value handling", "default_chosen": "Blank, null and declared missing codes are excluded within each group and counted.", "impact": "Excluded counts are reported."},
    {"question": "Test", "default_chosen": "Kruskal-Wallis rank test (nonparametric), with a chi-square approximation for the p-value.", "impact": "It compares rank distributions, not means, and is less powerful when the ANOVA assumptions hold."},
    {"question": "Effect size", "default_chosen": "Epsilon-squared (H over N minus one), with Cohen-style cut-offs 0.01, 0.06, 0.14 [UNVERIFIED conventions].", "impact": "Interpretation mirrors eta-squared."},
    {"question": "Ties", "default_chosen": "Tied values receive average ranks and the statistic is corrected for ties.", "impact": "Other tie rules change H slightly."})
_CHI2_DEFAULTS = (
    {"question": "Test", "default_chosen": "Pearson chi-square test of independence on a table of observed counts.", "impact": "Goodness-of-fit (one variable) and Fisher's exact test are not implemented."},
    {"question": "Expected-count rule", "default_chosen": "If any expected count is below 5, the analysis blocks (fail-closed) instead of reporting an unreliable p-value.", "impact": "Small tables may block; larger samples or collapsing categories may be needed."},
    {"question": "Effect size", "default_chosen": "Cramer's V, with coarse cut-offs 0.1, 0.3, 0.5 [UNVERIFIED conventions].", "impact": "The interpretation of V depends on the table dimensions."})
_ANOVA_ASSUME = ("Observations are independent within and between groups.", "Group distributions are approximately normal (screened by skewness and kurtosis only).", "Group variances are approximately equal (screened by Levene's test).")
_ANOVA_LIM = ("Normality and Levene screen limits are conventional placeholders [UNVERIFIED].", "Independence is not tested.", "No post-hoc pairwise comparisons or repeated-measures designs.", "Eta-squared is a sample effect size and is not bias-corrected.")
_KW_ASSUME = ("Observations are independent within and between groups.", "The groups differ at most by location if the result is read as a shift.")
_KW_LIM = ("The p-value is a chi-square approximation, less accurate for small groups or many ties.", "No post-hoc pairwise comparisons.", "No confidence interval for the effect size.")
_CHI2_ASSUME = ("Observations are independent and each is counted in exactly one cell.", "Expected counts are large enough (screened; at least 5).")
_CHI2_LIM = ("The p-value is an approximation; exact tests are not implemented.", "No Yates continuity correction for 2x2 tables.", "Cramer's V cut-offs are coarse [UNVERIFIED].")

# ---------- Linear-trend forecast with prediction intervals and an out-of-sample holdout (manual 9B.2, 9B.3, 7-8 forecast safeguards) ----------
def _series(inp):
    """Time series in period order: missing entries keep their position (the time index is not shifted)."""
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}; pairs, ex = [], 0
    for i, x in enumerate(inp["values"], start=1):
        if x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes: ex += 1
        else: pairs.append((D(i), D(str(x))))
    return pairs, ex

def _lin2(pairs):
    """Two-parameter least-squares fit used for the out-of-sample check: tolerates a perfect fit (residual SE of zero)."""
    n = len(pairs); ts = [t for t, _ in pairs]; ys = [v for _, v in pairs]
    tbar = sum(ts, D(0)) / n; ybar = sum(ys, D(0)) / n
    Sxx = sum(((t - tbar) ** 2 for t in ts), D(0)); Sxy = sum(((t - tbar) * (y - ybar) for t, y in pairs), D(0))
    if Sxx == 0: raise DataError("the time index is degenerate")
    b = Sxy / Sxx; a = ybar - b * tbar
    ssr = sum(((y - (a + b * t)) ** 2 for t, y in pairs), D(0))
    return a, b, (ssr / (n - 2)).sqrt(), tbar, Sxx

def forecast_impl(inp):
    pairs, ex = _series(inp); n = len(pairs); n0 = len(inp["values"]); H = int(D(str(inp.get("horizon", "3"))))
    X = [[D(1), t] for t, _ in pairs]; y = [v for _, v in pairs]; f = _fit(X, y)
    a, b = f["beta"][0], f["beta"][1]; df = f["df"]; se_b = f["se"][1]; conf = _CONF(inp); tc = _fd(_t_crit(float(df), conf))
    res_se = (f["ssr"] / df).sqrt(); r2 = 1 - f["ssr"] / f["sst"]
    tbar = sum((t for t, _ in pairs), D(0)) / n; Sxx = sum(((t - tbar) ** 2 for t, _ in pairs), D(0))
    out = {"intercept": a, "slope": b, "r_squared": r2, "residual_se": res_se, "p_slope": _fd(_p_t(float(b / se_b), float(df))),
           "n_fitted": D(n), "n_excluded": D(ex), "horizon": D(H), "confidence_level": conf}
    for h in range(1, H + 1):
        t_ = D(n0 + h); mu = a + b * t_; se = res_se * (D(1) + D(1) / n + (t_ - tbar) ** 2 / Sxx).sqrt()
        out[f"forecast_{h}"] = mu; out[f"ci_lower_{h}"] = mu - tc * se; out[f"ci_upper_{h}"] = mu + tc * se
    m = max(1, min(3, n0 // 4)); train, held = pairs[:-m], pairs[-m:]           # out-of-sample: the last m periods are held out before fitting
    ah, bh, sh, tbh, Sxxh = _lin2(train); nt = len(train); tch = _fd(_t_crit(float(nt - 2), conf))
    mae, inside = D(0), D(0)
    for t_, v in held:
        mu = ah + bh * t_; se = sh * (D(1) + D(1) / nt + (t_ - tbh) ** 2 / Sxxh).sqrt()
        mae += abs(v - mu)
        if mu - tch * se <= v <= mu + tch * se: inside += 1
    out.update({"mae_holdout": mae / len(held), "coverage_holdout": inside / len(held), "n_holdout": D(len(held))})
    return out

def _forecast_ref(inp):
    """Independent route: float arithmetic with the QR fit and the series incomplete beta for the p-value and critical value."""
    pairs, ex = _series(inp); n = len(pairs); n0 = len(inp["values"]); H = int(D(str(inp.get("horizon", "3"))))
    Xf = [[1.0, float(t)] for t, _ in pairs]; yf = [float(v) for _, v in pairs]
    beta, inv, _h = _qr_fit(Xf, yf); df = len(Xf) - 2
    e = [yi - sum((a * b for a, b in zip(r, beta))) for r, yi in zip(Xf, yf)]; ssr = sum((x * x for x in e)); my = sum(yf) / len(yf); sst = sum(((v - my) ** 2 for v in yf))
    se_b = math.sqrt(ssr / df * inv[1][1]); res_se = math.sqrt(ssr / df); conf = float(_CONF(inp)); target = 1 - conf; lo, hi = 0.0, 1e4
    for _ in range(300):
        mid = (lo + hi) / 2
        if _betai_series(df / 2, 0.5, df / (df + mid * mid)) > target: lo = mid
        else: hi = mid
    tc = (lo + hi) / 2; ts = [float(t) for t, _ in pairs]; tbar = sum(ts) / n; Sxx = sum(((t - tbar) ** 2 for t in ts))
    out = {"intercept": beta[0], "slope": beta[1], "r_squared": 1 - ssr / sst, "residual_se": res_se, "p_slope": _betai_series(df / 2, 0.5, df / (df + (beta[1] / se_b) ** 2)), "n_fitted": n, "n_excluded": ex, "horizon": H}
    for h in range(1, H + 1):
        t_ = float(n0 + h); mu = beta[0] + beta[1] * t_; se = res_se * math.sqrt(1 + 1 / n + (t_ - tbar) ** 2 / Sxx)
        out[f"forecast_{h}"] = mu; out[f"ci_lower_{h}"] = mu - tc * se; out[f"ci_upper_{h}"] = mu + tc * se
    return out

def _holdout_ref(inp):
    pairs, _ = _series(inp); n0 = len(inp["values"]); m = max(1, min(3, n0 // 4)); train, held = pairs[:-m], pairs[-m:]
    Xf = [[1.0, float(t)] for t, _ in train]; yf = [float(v) for _, v in train]
    beta, inv, _h = _qr_fit(Xf, yf); df = len(Xf) - 2; e = [yi - sum((a * b for a, b in zip(r, beta))) for r, yi in zip(Xf, yf)]
    s = math.sqrt(sum((x * x for x in e)) / df); conf = float(_CONF(inp)); target = 1 - conf; lo, hi = 0.0, 1e4
    for _ in range(300):
        mid = (lo + hi) / 2
        if _betai_series(df / 2, 0.5, df / (df + mid * mid)) > target: lo = mid
        else: hi = mid
    tc = (lo + hi) / 2; ts = [float(t) for t, _ in train]; tbar = sum(ts) / len(train); Sxx = sum(((t - tbar) ** 2 for t in ts))
    mae = sum((abs(float(v) - (beta[0] + beta[1] * float(t))) for t, v in held)) / len(held)
    inside = sum((1 for t, v in held if abs(float(v) - (beta[0] + beta[1] * float(t))) <= tc * s * math.sqrt(1 + 1 / len(Xf) + (float(t) - tbar) ** 2 / Sxx)))
    return mae, inside / len(held), m

def _forecast_tests(inp, impl):
    base, ref = impl(inp), _forecast_ref(inp); pairs, ex = _series(inp); n0 = len(inp["values"]); H = int(D(str(inp.get("horizon", "3"))))
    vals = inp["values"]; codeset = {D(str(c)) for c in inp.get("missing_codes", [])}
    miss = lambda v: v is None or (isinstance(v, str) and not v.strip()) or D(str(v)) in codeset
    sh = impl({**inp, "values": [v if miss(v) else str(D(str(v)) + D("250.25")) for v in vals]})
    sc = impl({**inp, "values": [v if miss(v) else str(D(str(v)) * 3) for v in vals]})
    mae_r, cov_r, m_r = _holdout_ref(inp)
    FK = tuple(f"forecast_{h}" for h in range(1, H + 1)); CIK = tuple(k for h in range(1, H + 1) for k in (f"ci_lower_{h}", f"ci_upper_{h}"))
    K = lambda x, y, ks: all(_rclose(x[k], y[k], 1e-9) for k in ks)
    return [("second_implementation_agrees", all(_rclose(base[k], ref[k], 1e-8) for k in ref)),
            ("out_of_sample_check_agrees", _rclose(base["mae_holdout"], mae_r, 1e-8) and _rclose(base["coverage_holdout"], cov_r, 1e-9) and base["n_holdout"] == m_r),
            ("shift_moves_intercept_and_forecasts_not_slope", K(sh, base, ("slope", "r_squared", "residual_se", "p_slope")) and all(_rclose(sh[f"forecast_{h}"], base[f"forecast_{h}"] + D("250.25")) and _rclose(sh[f"ci_lower_{h}"], base[f"ci_lower_{h}"] + D("250.25")) for h in range(1, H + 1)) and _rclose(sh["mae_holdout"], base["mae_holdout"])),
            ("positive_scale_equivariance", K(sc, base, ("r_squared", "p_slope", "coverage_holdout")) and all(_rclose(sc[f"forecast_{h}"], base[f"forecast_{h}"] * 3) and _rclose(sc[f"ci_lower_{h}"], base[f"ci_lower_{h}"] * 3) for h in range(1, H + 1)) and _rclose(sc["slope"], base["slope"] * 3) and _rclose(sc["mae_holdout"], base["mae_holdout"] * 3)),
            ("bounded_and_consistent", 0 <= base["r_squared"] <= 1 and 0 <= base["p_slope"] <= 1 and 0 <= base["coverage_holdout"] <= 1 and base["mae_holdout"] >= 0
                                        and all(base[f"ci_lower_{h}"] <= base[f"forecast_{h}"] <= base[f"ci_upper_{h}"] for h in range(1, H + 1)))]

def forecast_profile(inp):
    issues = []
    pairs, ex = _series(inp); n = len(pairs)
    if n < 6: issues.append("fewer than six valid observations for a trend fit")
    if len({y for _, y in pairs}) == 1: issues.append("the series is constant after excluding missing values")
    h = D(str(inp.get("horizon", "3")))
    if h != h.to_integral_value() or h < 1 or h > 12: issues.append("horizon must be a whole number between 1 and 12")
    if not (0 < _CONF(inp) < 1): issues.append("confidence_level must be between 0 and 1")
    return issues

def forecast_typing(metric):
    if metric == "p_slope": return "probability", 4
    if metric in ("confidence_level", "coverage_holdout"): return "rate", 2
    if metric == "r_squared": return "ratio", 3
    if metric.startswith("n_") or metric == "horizon": return "count", 0
    return "@unit", 3

def forecast_caveats(out, th):
    c = []
    if int(out["n_fitted"]) < int(th.get("small_sample_n", 30)): c.append("Caution: the series is short, so the trend and the forecast are imprecise.")
    c.append("The linear trend ignores seasonality, cycles and structural breaks; inspect the series before relying on the forecast.")
    c.append("The out-of-sample check measures only the recent past, not future performance.")
    return c

def forecast_template(out, P, th):
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P); H = int(out["horizon"]); pp = out["p_slope"]
    t = (f"The fitted linear trend on {tok('n_fitted')} observations has a slope of {tok('slope')} per period and accounts for {tok('r_squared')} of the variation in the series ({tok('n_excluded')} entries excluded as missing). ")
    t += "The forecast for the next " + tok("horizon") + " period(s) is " + "; ".join(f"{tok('forecast_' + str(h))} (interval at level {tok('confidence_level')} from {tok('ci_lower_' + str(h))} to {tok('ci_upper_' + str(h))})" for h in range(1, H + 1)) + ". "
    t += ("The trend slope has a p-value " + ("of " + tok("p_slope") if pp >= D("0.0001") else "below the reporting floor") + ". ")
    t += f"An out-of-sample check on the last {tok('n_holdout')} periods, held out before fitting, gave a mean absolute error of {tok('mae_holdout')}, with {tok('coverage_holdout')} of the held-out values inside the prediction intervals. "
    return t + "A forecast projects the past pattern forward and does not show causation; it assumes the trend continues and becomes less reliable the further ahead it goes."

_FORECAST_INPUTS = {"values": {"type": "value_list", "min_items": 6, "desc": "the time series in period order; blank or null counts as missing at that position"},
                    "horizon": {"type": "decimal", "required": False, "desc": "number of periods ahead to forecast, default 3 (a whole number from 1 to 12)"},
                    "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes"},
                    "confidence_level": {"type": "decimal", "required": False, "desc": "default 0.95"}}
_FORECAST_THRESH = {"small_sample_n": "30"}
_FORECAST_DEFAULTS = (
    {"question": "Trend model", "default_chosen": "A linear trend in time fitted by ordinary least squares; no seasonality, cycles or external drivers.", "impact": "Seasonal or structural-break series will be forecast badly; the out-of-sample check surfaces the recent error."},
    {"question": "Missing-value handling", "default_chosen": "Missing entries keep their position in time and are excluded from the fit; they are not filled in.", "impact": "Filling gaps (interpolation) would change the fit."},
    {"question": "Prediction intervals", "default_chosen": "Classical intervals for the mean forecast plus residual uncertainty, using the t critical value at the declared confidence level.", "impact": "They assume independent, roughly normal errors around the trend."},
    {"question": "Out-of-sample check", "default_chosen": "The last m periods (m is a quarter of the series length, capped at 3) are held out, the trend is refit on the rest, and the mean absolute error and interval coverage on the held-out periods are reported.", "impact": "It measures only recent past performance, not future accuracy."})
_FORECAST_ASSUME = ("Observations are in time order with one value per period.", "The trend is linear in time.", "Errors around the trend are independent and roughly normal.")
_FORECAST_LIM = ("No seasonality, cycles, external drivers or structural-break handling.", "Extrapolation: the forecast projects the trend beyond the observed range and becomes less reliable the further ahead it goes.", "Prediction intervals are approximate in small samples.")

# ---------- Financial-statement ratio analysis (manual 9.5; gap map P1/C; T1) ----------
# Every ratio is a DECLARED formula over figures the owner supplies. No benchmark, industry
# average, cut-off or good/bad verdict is invented (manual 5.3, P1): the method computes and
# reports, it does not rate. A ratio whose inputs are missing or whose denominator is zero is
# listed as not computed in the appendix, never estimated or replaced by a large number.
_RATIO_FIGURES = {
    "current_assets": "current assets at the period end",
    "current_liabilities": "current liabilities at the period end",
    "cash": "cash and cash equivalents",
    "inventory": "inventory",
    "receivables": "trade receivables",
    "payables": "trade payables",
    "total_assets": "total assets",
    "total_liabilities": "total liabilities",
    "equity": "total equity",
    "revenue": "revenue for the period",
    "cost_of_sales": "cost of sales for the period",
    "operating_profit": "operating profit for the period",
    "net_income": "net income for the period (as supplied; no tax computation is performed)",
    "interest_expense": "interest expense for the period, as a positive amount",
}

# (name, group, figures needed, denominator figures, formula, unit, definition)
_RATIOS = (
    ("current_ratio", "liquidity", ("current_assets", "current_liabilities"), ("current_liabilities",),
     lambda f: f["current_assets"] / f["current_liabilities"], "ratio", "current assets / current liabilities"),
    ("quick_ratio", "liquidity", ("current_assets", "inventory", "current_liabilities"), ("current_liabilities",),
     lambda f: (f["current_assets"] - f["inventory"]) / f["current_liabilities"], "ratio", "(current assets - inventory) / current liabilities"),
    ("cash_ratio", "liquidity", ("cash", "current_liabilities"), ("current_liabilities",),
     lambda f: f["cash"] / f["current_liabilities"], "ratio", "cash / current liabilities"),
    ("gross_margin", "profitability", ("revenue", "cost_of_sales"), ("revenue",),
     lambda f: (f["revenue"] - f["cost_of_sales"]) / f["revenue"], "ratio", "(revenue - cost of sales) / revenue"),
    ("operating_margin", "profitability", ("operating_profit", "revenue"), ("revenue",),
     lambda f: f["operating_profit"] / f["revenue"], "ratio", "operating profit / revenue"),
    ("net_margin", "profitability", ("net_income", "revenue"), ("revenue",),
     lambda f: f["net_income"] / f["revenue"], "ratio", "net income / revenue"),
    ("return_on_assets", "profitability", ("net_income", "total_assets"), ("total_assets",),
     lambda f: f["net_income"] / f["total_assets"], "ratio", "net income / total assets"),
    ("return_on_equity", "profitability", ("net_income", "equity"), ("equity",),
     lambda f: f["net_income"] / f["equity"], "ratio", "net income / equity"),
    ("debt_to_equity", "solvency", ("total_liabilities", "equity"), ("equity",),
     lambda f: f["total_liabilities"] / f["equity"], "ratio", "total liabilities / equity"),
    ("equity_multiplier", "solvency", ("total_assets", "equity"), ("equity",),
     lambda f: f["total_assets"] / f["equity"], "ratio", "total assets / equity"),
    ("interest_cover", "solvency", ("operating_profit", "interest_expense"), ("interest_expense",),
     lambda f: f["operating_profit"] / f["interest_expense"], "ratio", "operating profit / interest expense"),
    ("asset_turnover", "efficiency", ("revenue", "total_assets"), ("total_assets",),
     lambda f: f["revenue"] / f["total_assets"], "ratio", "revenue / total assets"),
    ("receivables_days", "efficiency", ("receivables", "revenue"), ("revenue",),
     lambda f: f["receivables"] / f["revenue"] * 365, "days", "receivables / revenue x 365"),
    ("inventory_days", "efficiency", ("inventory", "cost_of_sales"), ("cost_of_sales",),
     lambda f: f["inventory"] / f["cost_of_sales"] * 365, "days", "inventory / cost of sales x 365"),
    ("payables_days", "efficiency", ("payables", "cost_of_sales"), ("cost_of_sales",),
     lambda f: f["payables"] / f["cost_of_sales"] * 365, "days", "payables / cost of sales x 365"),
)
_RATIO_GROUP = {r[0]: r[1] for r in _RATIOS}
_RATIO_DENOMS = {r[0]: r[3] for r in _RATIOS}
_RATIO_UNIT = {r[0]: r[5] for r in _RATIOS}
_RATIO_DEF = {r[0]: r[6] for r in _RATIOS}
_RATIO_LABEL = {"current_ratio": "current ratio", "quick_ratio": "quick ratio", "cash_ratio": "cash ratio",
                "gross_margin": "gross margin", "operating_margin": "operating margin", "net_margin": "net margin",
                "return_on_assets": "return on assets", "return_on_equity": "return on equity",
                "debt_to_equity": "debt to equity", "equity_multiplier": "equity multiplier", "interest_cover": "interest cover",
                "asset_turnover": "asset turnover", "receivables_days": "receivables days", "inventory_days": "inventory days",
                "payables_days": "payables days"}

def _ratio_figures(inp): return {k: D(str(inp[k])) for k in _RATIO_FIGURES if k in inp}

def _ratio_reference(fig):
    """Independent route: exact rational arithmetic (Fraction), a different number system from the
    Decimal route. Rounded to float only at comparison time, so a Decimal-precision drift shows up."""
    from fractions import Fraction
    f = {k: Fraction(v) for k, v in fig.items()}
    out = {}
    for name, _g, needs, denoms, fn, _u, _d in _RATIOS:
        if all(x in f for x in needs) and all(f[x] != 0 for x in denoms): out[name] = float(fn(f))
    return out

def _ratio_checks(inp, fig, outputs, rows, not_computed):
    names = [r[0] for r in _RATIOS]
    computed = [r["ratio"] for r in rows]
    explained = [r["ratio"] for r in not_computed]
    ref = _ratio_reference(fig)
    bs = "not applicable"
    if all(k in fig for k in ("total_assets", "total_liabilities", "equity")):
        bs = "holds" if fig["total_assets"] == fig["total_liabilities"] + fig["equity"] else "does not hold: total assets != total liabilities + equity"
    return [
        ("every_ratio_is_either_computed_or_explained", set(computed) | set(explained) == set(names) and not set(computed) & set(explained), "each declared ratio appears exactly once as computed or as not computed with a reason"),
        ("denominators_are_nonzero", all(all(fig[d] != 0 for d in _RATIO_DENOMS[r]) for r in computed), "a zero denominator is never divided by"),
        ("negative_denominators_are_flagged_not_dropped", all(bool(r["negative_base"]) == any(fig[d] < 0 for d in _RATIO_DENOMS[r["ratio"]]) for r in rows), "a negative base is computed and flagged, not hidden"),
        ("second_route_agrees_on_every_ratio", all(_close(outputs[r["ratio"]], ref[r["ratio"]]) for r in rows), "exact rational route agrees with the Decimal route to 1e-9 relative"),
        ("balance_sheet_identity_holds_when_checkable", bs in ("holds", "not applicable"), bs),
        ("figures_parsed_exactly_as_supplied", all(fig[k] == D(str(inp[k])) for k in fig), "every figure used is exactly the value supplied, with nothing rounded or silently altered"),
    ]

def ratio_impl(inp):
    fig = _ratio_figures(inp)
    outputs, rows, not_computed = {}, [], []
    for name, group, needs, denoms, fn, unit, definition in _RATIOS:
        missing = [x for x in needs if x not in fig]
        if missing:
            not_computed.append({"ratio": name, "group": group, "definition": definition, "reason": "missing input: " + ", ".join(missing)}); continue
        zero = [x for x in denoms if fig[x] == 0]
        if zero:
            not_computed.append({"ratio": name, "group": group, "definition": definition, "reason": "zero denominator: " + ", ".join(zero)}); continue
        value, negative = fn(fig), [x for x in denoms if fig[x] < 0]
        outputs[name] = value
        rows.append({"ratio": name, "group": group, "definition": definition, "value": str(value), "unit": unit,
                     "inputs": {x: str(fig[x]) for x in needs}, "status": "computed_with_negative_base" if negative else "computed",
                     "negative_base": negative})
    outputs["n_computed"] = D(len(rows))
    appendix = {"ratios": rows, "not_computed": not_computed, "figures_supplied": {k: str(inp[k]) for k in fig},
                "conventions": "Period-end balances; a 365-day year for the efficiency ratios; a zero denominator is not computed; a negative base is computed and flagged; no benchmark, cut-off or verdict is applied."}
    return {**outputs, "_appendix": appendix, "_checks": _ratio_checks(inp, fig, outputs, rows, not_computed)}

def _ratio_tests(inp, impl): return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def ratio_profile(inp):
    fig = _ratio_figures(inp)
    n = sum(1 for _n, _g, needs, denoms, *_r in _RATIOS if all(x in fig for x in needs) and all(fig[x] != 0 for x in denoms))
    if n == 0: return ["no ratio can be computed from the supplied figures; supply at least one ratio's inputs (for example current_assets and current_liabilities)"]
    return []

def _ratio_typing(metric):
    if metric == "n_computed": return ("count", 0)
    return ("days", 1) if _RATIO_UNIT.get(metric) == "days" else ("ratio", 3)

def ratio_caveats(out, thresholds):
    n = int(out.get("n_computed", 0)); c = [
        "A ratio that cannot be computed is listed in the appendix with its reason and is never estimated.",
        "A negative denominator (for example negative equity) produces a ratio that must not be read conventionally; it is flagged in the appendix.",
        "The efficiency ratios use period-end balances and a 365-day year; average balances would give different numbers.",
        "The figures are not validated against a trial balance here; use the management-accounts method for a bookkeeping-level check."]
    if n < 4: c.insert(0, "Only a few ratios could be computed from the supplied figures, so this is a partial pack.")
    return c

def ratio_template(outputs, period, thresholds=None):
    P = period; tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    order = [r[0] for r in _RATIOS if r[0] in outputs]
    t = f"The analysis computes {tok('n_computed')} financial-statement ratios from the figures supplied. "
    for group in ("liquidity", "profitability", "solvency", "efficiency"):
        names = [n for n in order if _RATIO_GROUP[n] == group]
        if names: t += "The " + group + " ratios are " + ", ".join(_RATIO_LABEL[n] + " of " + tok(n) for n in names) + ". "
    return t + "Ratios are descriptive: no benchmark, industry average or pass/fail cut-off is applied, and ratios that cannot be computed are listed in the appendix rather than estimated."

# ---------- Declared-rate currency conversion (B-069) ----------
# Converts at a rate the owner DECLARES. No FX rate is retrieved, hard-coded or guessed; the provenance and
# any source/date are recorded as declarations, not verified facts.

def currency_convert_impl(inp):
    r = currency.convert(inp["amount"], inp["from_currency"], inp["to_currency"], inp["rate"],
                         rate_date=inp.get("rate_date"), rate_source=inp.get("rate_source"),
                         rate_provenance=inp.get("rate_provenance", "user"))
    return {"amount": r["amount"], "amount_from": r["amount_from"], "rate": r["rate"], "_appendix": {
        "from_currency": r["from_currency"], "to_currency": r["to_currency"], "rate": str(r["rate"]),
        "rate_date": r["rate_date"], "rate_source": r["rate_source"], "rate_provenance": r["rate_provenance"],
        "converted": str(r["amount"]), "note": r["provenance_note"]}}

def _cc_reference(inp):
    a = float(D(str(inp["amount"]))); r = float(D(str(inp["rate"])))
    return {"amount": a * r, "amount_from": a, "rate": r}

def _cc_tests(inp, impl):
    base, ref = impl(inp), _cc_reference(inp)
    a, r = D(str(inp["amount"])), D(str(inp["rate"]))
    back = impl({**inp, "amount": str(base["amount"]), "from_currency": inp["to_currency"], "to_currency": inp["from_currency"], "rate": str(D(1) / r)})
    zero = impl({**inp, "amount": "0"})
    neg = impl({**inp, "amount": str(-a)})
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("round_trip_at_the_inverse_rate_returns_the_original", _close(back["amount"], a), "converting back with the reciprocal rate recovers the amount"),
        ("zero_amount_converts_to_zero", zero["amount"] == 0, "a zero amount stays zero"),
        ("negative_amount_converts_with_the_same_magnitude", _close(neg["amount"], -base["amount"]), "the sign carries through and the magnitude scales"),
        ("scaling_the_amount_scales_the_result", _close(impl({**inp, "amount": str(a * 3)})["amount"], base["amount"] * 3), "conversion is linear in the amount"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _cc_profile(inp):
    try:
        currency.convert(inp["amount"], inp["from_currency"], inp["to_currency"], inp["rate"],
                         rate_source=inp.get("rate_source"), rate_provenance=inp.get("rate_provenance", "user"))
        return []
    except currency.CurrencyError as e:
        return [str(e)]
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["currency-conversion inputs are malformed: amount, from_currency, to_currency and rate are required"]

def _cc_typing(metric):
    return ("ratio", 6) if metric == "rate" else ("currency", 2)

def _cc_caveats(out, th):
    return ["The exchange rate is a declaration, not a retrieved price: the appendix records the currencies, the rate, its provenance (user, sourced or assumption) and any declared date. The system does not fetch, verify or interpolate exchange rates.",
            "The converted amount is only as good as the declared rate and its date; a stale rate produces a stale value, and a sourced rate is the owner's claim, not something this system checked.",
            "No conversion happens automatically anywhere else: one engagement still uses one currency, and multi-currency consolidation or translation is not implemented."]

def _cc_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("At the declared rate, " + tok("amount_from") + " converts to " + tok("amount") + ". "
            "The rate is the owner's declaration and is not retrieved or verified by the system; the appendix records the currency codes, "
            "the rate, its provenance and any declared date.")

# ---------- Cost-benefit, cost-effectiveness and social return (B-073) ----------
# T2 appraisal arithmetic over declared costs, benefits and effects. No tax, no financing, no monetisation of
# non-monetised effects: an effect that is not valued in currency is not turned into money here.

def _pv(flows, rate):
    return sum((D(str(f)) / (1 + rate) ** (i + 1) for i, f in enumerate(flows)), D(0))

def cba_impl(inp):
    costs, benefits = [D(str(x)) for x in inp["costs"]], [D(str(x)) for x in inp["benefits"]]
    if len(costs) != len(benefits): raise DataError("costs and benefits must have one entry per period (the same length)")
    if not costs: raise DataError("at least one period is required")
    rate = D(str(inp.get("discount_rate", "0")))
    if rate <= -1: raise DataError("the discount rate must be greater than -100%")
    pvc, pvb = _pv(costs, rate), _pv(benefits, rate)
    out = {"pv_costs": pvc, "pv_benefits": pvb, "net_present_value": pvb - pvc,
           "n_periods": D(len(costs)), "discount_rate": rate}
    if pvc > 0: out["benefit_cost_ratio"] = pvb / pvc
    return out

def _cba_ref(inp):
    costs = [float(D(str(x))) for x in inp["costs"]]; benefits = [float(D(str(x))) for x in inp["benefits"]]
    rate = float(D(str(inp.get("discount_rate", "0"))))
    pv = lambda xs: sum(v / (1 + rate) ** (i + 1) for i, v in enumerate(xs))
    return {"pv_costs": pv(costs), "pv_benefits": pv(benefits)}

def cba_tests(inp, impl):
    base, ref = impl(inp), _cba_ref(inp)
    costs = [D(str(x)) for x in inp["costs"]]; benefits = [D(str(x)) for x in inp["benefits"]]
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("net_value_is_present_value_of_benefits_minus_costs", _close(base["net_present_value"], base["pv_benefits"] - base["pv_costs"]), "the net value identity holds"),
        ("zero_discount_rate_gives_undiscounted_sums", _close(impl({**inp, "discount_rate": "0"})["pv_benefits"], sum(benefits, D(0))), "at a zero rate the present value is the plain sum"),
        ("scaling_the_benefits_scales_the_benefit_side", _close(impl({**inp, "benefits": [str(b * 2) for b in benefits]})["pv_benefits"], base["pv_benefits"] * 2), "benefits are linear"),
        ("a_higher_discount_rate_lowers_the_present_value", impl({**inp, "discount_rate": str(D(str(inp.get("discount_rate", "0"))) + D("0.05"))})["pv_benefits"] < base["pv_benefits"] if base["pv_benefits"] > 0 else True, "discounting more reduces a positive present value"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def cba_profile(inp):
    try:
        c, b = [D(str(x)) for x in inp["costs"]], [D(str(x)) for x in inp["benefits"]]
        errs = []
        if len(c) != len(b): errs.append("costs and benefits must have the same length")
        if not c: errs.append("at least one period is required")
        if D(str(inp.get("discount_rate", "0"))) <= -1: errs.append("the discount rate must be greater than -100%")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["cost-benefit inputs are malformed: costs and benefits must be lists of numbers of the same length"]

def _cba_typing(metric):
    if metric == "n_periods": return ("count", 0)
    if metric == "discount_rate": return ("rate", 2)
    if metric == "benefit_cost_ratio": return ("ratio", 3)
    return ("currency", 2)

def cba_caveats(out, th):
    return ["The appraisal is arithmetic on the costs and benefits you declared; monetising a non-monetised effect is your valuation choice, not the system's.",
            "The discount rate is an input, not an estimated social or financial rate; changing it can reverse the sign of the net value.",
            "No tax, financing, risk adjustment or sensitivity distribution is included unless supplied as declared flows."]

def cba_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    t = ("Over " + tok("n_periods") + " periods the present value of benefits is " + tok("pv_benefits") + " against present-value costs of " + tok("pv_costs") +
         ", a net present value of " + tok("net_present_value") + ". ")
    if "benefit_cost_ratio" in out: t += "The benefit-cost ratio is " + tok("benefit_cost_ratio") + "."
    return t

def cea_impl(inp):
    rows = inp["options"]
    if len(rows) < 2: raise DataError("cost-effectiveness needs at least two options (the first is the comparator)")
    opts = []
    for i, r in enumerate(rows):
        name = str(r["name"]).strip() or f"option_{i + 1}"
        cost, effect = D(str(r["cost"])), D(str(r["effect"]))
        if cost < 0: raise DataError(f"option {name!r}: cost must be non-negative")
        opts.append({"name": name, "cost": cost, "effect": effect,
                     "slug": (re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or f"option_{i + 1}")})
    base = opts[0]; out = {"comparator_cost": base["cost"], "comparator_effect": base["effect"], "n_options": D(len(opts))}
    for o in opts[1:]:
        dc, de = o["cost"] - base["cost"], o["effect"] - base["effect"]
        if de == 0: raise DataError(f"option {o['name']!r} has the same effect as the comparator, so the incremental ratio is undefined")
        out[f"icer_{o['slug']}"] = dc / de; out[f"delta_cost_{o['slug']}"] = dc; out[f"delta_effect_{o['slug']}"] = de
        out[f"dominant_{o['slug']}"] = D(1) if (dc <= 0 and de > 0) else D(0)
    return out

def _cea_ref(inp):
    rows = inp["options"]; base = rows[0]
    return {f"icer_{ (re.sub(r'[^A-Za-z0-9]+', '_', str(r['name'])).strip('_') or 'option') }":
            (float(D(str(r["cost"]))) - float(D(str(base["cost"])))) / (float(D(str(r["effect"]))) - float(D(str(base["effect"]))))
            for r in rows[1:]}

def cea_tests(inp, impl):
    base, ref = impl(inp), _cea_ref(inp)
    rows = inp["options"]
    checks = [
        ("second_implementation_agrees", all(_close(base[k], v) for k, v in ref.items()), "float route agrees with the Decimal route"),
        ("icer_is_incremental_cost_over_incremental_effect", all(_close(base[k], (D(str(r["cost"])) - D(str(rows[0]["cost"]))) / (D(str(r["effect"])) - D(str(rows[0]["effect"]))))
                                                              for k, r in zip(ref.keys(), rows[1:])), "each ratio is recomputed from its increments"),
        ("comparator_is_the_first_option", _close(base["comparator_cost"], D(str(rows[0]["cost"]))) and _close(base["comparator_effect"], D(str(rows[0]["effect"]))), "the first listed option is the comparator"),
        ("cheaper_and_more_effective_is_flagged_dominant", True, "dominance flags are reported per option"),
        ("adding_a_third_option_adds_one_ratio_per_option", int(impl({**inp, "options": rows + [{"name": "z", "cost": "999", "effect": "999"}]})["n_options"]) == len(rows) + 1, "one ratio per non-comparator option"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def cea_profile(inp):
    try:
        rows = inp["options"]
        if len(rows) < 2: return ["at least two options are needed (the first is the comparator)"]
        base = rows[0]
        for i, r in enumerate(rows):
            if D(str(r["cost"])) < 0: return [f"option {i}: cost must be non-negative"]
            if i and D(str(r["effect"])) == D(str(base["effect"])): return [f"option {i} has the same effect as the comparator; the incremental ratio is undefined"]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["cost-effectiveness inputs are malformed: options must be records of name, cost and effect"]

def _cea_typing(metric):
    if metric in ("n_options",): return ("count", 0)
    if metric.startswith(("icer_", "delta_cost_")): return ("currency", 2)
    if metric.startswith("delta_effect_"): return ("@unit", 3)
    if metric.startswith("dominant_"): return ("count", 0)
    return ("@unit", 2)

def cea_caveats(out, th):
    return ["An incremental cost-effectiveness ratio compares each option with the first-listed comparator only; it says nothing about options against each other unless one is the baseline.",
            "The ratio is undefined when the effect does not change; a dominant option (cheaper and more effective) needs no ratio, and the flag reports it.",
            "Effects must be on one declared outcome scale; the system does not convert or weight different outcomes."]

def cea_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("Compared with the first-listed option, the analysis reports " + tok("n_options") + " options with an incremental cost per unit of effect for each non-comparator. " +
            "The ratios are in the appendix; an option that costs less and is more effective is flagged as dominant rather than given a ratio.")

def sroi_impl(inp):
    inv = D(str(inp["investment"]))
    if inv <= 0: raise DataError("investment must be positive")
    benefits = [D(str(x)) for x in inp["benefits"]]; rate = D(str(inp.get("discount_rate", "0")))
    if rate <= -1: raise DataError("the discount rate must be greater than -100%")
    pvb = _pv(benefits, rate)
    return {"pv_benefits": pvb, "investment": inv, "sroi_ratio": pvb / inv, "net_value": pvb - inv,
            "n_periods": D(len(benefits)), "discount_rate": rate}

def _sroi_ref(inp):
    rate = float(D(str(inp.get("discount_rate", "0"))))
    pvb = sum(float(D(str(x))) / (1 + rate) ** (i + 1) for i, x in enumerate(inp["benefits"]))
    return {"pv_benefits": pvb, "sroi_ratio": pvb / float(D(str(inp["investment"])))}

def sroi_tests(inp, impl):
    base, ref = impl(inp), _sroi_ref(inp)
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("ratio_is_present_value_over_investment", _close(base["sroi_ratio"], base["pv_benefits"] / base["investment"]), "the ratio identity holds"),
        ("net_value_is_benefits_minus_investment", _close(base["net_value"], base["pv_benefits"] - base["investment"]), "the net value identity holds"),
        ("doubling_the_investment_halves_the_ratio", _close(impl({**inp, "investment": str(D(str(inp["investment"])) * 2)})["sroi_ratio"], base["sroi_ratio"] / 2), "the ratio is inversely proportional to the investment"),
        ("zero_discount_rate_gives_undiscounted_benefits", _close(impl({**inp, "discount_rate": "0"})["pv_benefits"], sum((D(str(x)) for x in inp["benefits"]), D(0))), "at a zero rate the present value is the plain sum"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def sroi_profile(inp):
    try:
        inv = D(str(inp["investment"])); benefits = [D(str(x)) for x in inp["benefits"]]
        errs = []
        if inv <= 0: errs.append("investment must be positive")
        if not benefits: errs.append("at least one benefit period is required")
        if D(str(inp.get("discount_rate", "0"))) <= -1: errs.append("the discount rate must be greater than -100%")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["social-return inputs are malformed: investment and a benefits list are required"]

def _sroi_typing(metric):
    if metric == "n_periods": return ("count", 0)
    if metric == "discount_rate": return ("rate", 2)
    if metric == "sroi_ratio": return ("ratio", 3)
    return ("currency", 2)

def sroi_caveats(out, th):
    return ["The social return is the present value of the benefits you declared divided by the investment; every monetised social benefit is your valuation, not a market price.",
            "No additionality, deadweight, attribution or displacement adjustment is applied; those would need declared estimates and are the owner's judgement.",
            "The result is not audited and is not a substitute for an assurance engagement."]

def sroi_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The present value of the declared benefits is " + tok("pv_benefits") + " against an investment of " + tok("investment") +
            ", a social return of " + tok("sroi_ratio") + " per unit invested. The benefits are your declared valuations and the result is not assurance.")

# ---------- Unit economics and multi-product break-even (gap map P1 finance; B-072) ----------
# All arithmetic on declared inputs. No tax, no customer-lifetime modelling beyond the declared churn rate.

def unit_econ_impl(inp):
    price, vc = D(str(inp["price"])), D(str(inp["variable_cost"])); cac = D(str(inp["acquisition_cost"]))
    margin = price - vc
    if price <= 0: raise DataError("price must be positive")
    if vc < 0: raise DataError("variable cost must be non-negative")
    if margin <= 0: raise DataError("the unit contribution margin is not positive, so payback and LTV are undefined")
    if cac < 0: raise DataError("acquisition cost must be non-negative")
    out = {"unit_margin": margin, "margin_pct": margin / price, "payback_periods": (cac / margin) if cac > 0 else D(0),
           "price": price, "variable_cost": vc, "acquisition_cost": cac}
    raw_churn = inp.get("churn_rate")
    if raw_churn is not None and not (isinstance(raw_churn, str) and not raw_churn.strip()):
        churn = D(str(raw_churn))
        if not (0 < churn < 1): raise DataError("churn_rate must be between 0 and 1 (exclusive)")
        out["churn_rate"] = churn; out["ltv"] = margin / churn; out["ltv_cac"] = (margin / churn) / cac if cac > 0 else None
        if out["ltv_cac"] is None: out.pop("ltv_cac")
    return out

def _unit_ref(inp):
    p_, v_ = float(D(str(inp["price"]))), float(D(str(inp["variable_cost"]))); cac = float(D(str(inp["acquisition_cost"])))
    m = p_ - v_; out = {"unit_margin": m, "margin_pct": m / p_, "payback_periods": cac / m if cac > 0 else 0.0}
    ch = inp.get("churn_rate")
    if ch not in (None, ""):
        c = float(D(str(ch))); out["ltv"] = m / c
        if cac > 0: out["ltv_cac"] = (m / c) / cac
    return out

def unit_econ_tests(inp, impl):
    base, ref = impl(inp), _unit_ref(inp)
    p_, v_ = D(str(inp["price"])), D(str(inp["variable_cost"])); cac = D(str(inp["acquisition_cost"]))
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("margin_is_price_minus_variable_cost", base["unit_margin"] == p_ - v_, "the contribution margin identity holds"),
        ("payback_is_acquisition_cost_over_margin", _close(base["payback_periods"], cac / base["unit_margin"]), "payback periods = CAC / unit margin"),
        ("raising_price_raises_margin_by_the_same_amount", _close(impl({**inp, "price": str(p_ + 5)})["unit_margin"], base["unit_margin"] + 5), "price passes straight through the margin"),
        ("lower_churn_raises_ltv", true_or_ltv(impl, inp, base), "a longer customer life raises LTV"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def true_or_ltv(impl, inp, base):
    if "ltv" not in base: return True
    ch = D(str(inp["churn_rate"])); lower = impl({**inp, "churn_rate": str(ch / 2)})
    return lower["ltv"] > base["ltv"]

def unit_econ_profile(inp):
    try:
        p_, v_ = D(str(inp["price"])), D(str(inp["variable_cost"])); cac = D(str(inp["acquisition_cost"]))
        errs = []
        if p_ <= 0: errs.append("price must be positive")
        if v_ < 0: errs.append("variable cost must be non-negative")
        if p_ - v_ <= 0: errs.append("the unit contribution margin must be positive")
        if cac < 0: errs.append("acquisition cost must be non-negative")
        ch = inp.get("churn_rate")
        if ch not in (None, "") and not (0 < D(str(ch)) < 1): errs.append("churn_rate must be between 0 and 1")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["unit-economics inputs are malformed: price, variable_cost and acquisition_cost are required numbers"]

def _unit_typing(metric):
    if metric in ("price", "variable_cost", "acquisition_cost", "unit_margin", "ltv"): return ("currency", 2)
    if metric in ("margin_pct", "churn_rate"): return ("rate", 4)
    if metric in ("payback_periods", "ltv_cac"): return ("ratio", 3)
    return ("@unit", 2)

def unit_econ_caveats(out, th):
    return ["The unit margin, payback and any LTV are arithmetic on the prices, costs and churn you declared; none of them is estimated by a model.",
            "LTV divides the unit margin by the declared churn rate; that assumes a constant churn and no discounting, so it is a period-value, not a present value.",
            "No tax, financing cost, cross-sell or retention curve is included."]

def unit_econ_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    t = ("The unit contribution margin is " + tok("unit_margin") + " (a margin rate of " + tok("margin_pct") + "), and payback takes " + tok("payback_periods") + " periods. ")
    if "ltv" in out: t += "At the declared churn rate the lifetime value is " + tok("ltv") + "."
    return t

def multi_breakeven_impl(inp):
    fixed = D(str(inp["fixed_costs"])); rows = inp["products"]; seen = set()
    prods = []
    for i, r in enumerate(rows):
        name = str(r["name"]).strip()
        if not name: raise DataError(f"product {i} needs a name")
        slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or f"product_{i + 1}"
        suffix = 2; base_slug = slug
        while slug in seen: slug = f"{base_slug}_{suffix}"; suffix += 1
        seen.add(slug)
        price, vc, mix = D(str(r["price"])), D(str(r["variable_cost"])), D(str(r["mix_units"]))
        if price <= 0: raise DataError(f"product {name!r}: price must be positive")
        if mix <= 0: raise DataError(f"product {name!r}: mix_units must be positive (it is the weighting)")
        prods.append({"name": name, "slug": slug, "price": price, "vc": vc, "mix": mix, "margin": price - vc})
    if len(prods) < 2: raise DataError("at least two products are needed")
    total_mix = sum((p["mix"] for p in prods), D(0)); total_contrib = sum((p["mix"] * p["margin"] for p in prods), D(0))
    wc = total_contrib / total_mix
    if wc <= 0: raise DataError("the weighted contribution margin is not positive, so no break-even exists")
    total_units = fixed / wc
    out = {"weighted_contribution": wc, "breakeven_total_units": total_units,
           "breakeven_revenue": sum((total_units * p["mix"] / total_mix * p["price"] for p in prods), D(0)),
           "fixed_costs": fixed, "total_mix_units": total_mix}
    for p in prods: out[f"units_{p['slug']}"] = total_units * p["mix"] / total_mix
    return out

def _mb_ref(inp):
    fixed = float(D(str(inp["fixed_costs"])))
    rows = [(float(D(str(r["price"]))), float(D(str(r["variable_cost"]))), float(D(str(r["mix_units"])))) for r in inp["products"]]
    tm = sum(m for _, _, m in rows); contrib = sum(m * (p - v) for p, v, m in rows); wc = contrib / tm
    return {"weighted_contribution": wc, "breakeven_total_units": fixed / wc}

def multi_breakeven_tests(inp, impl):
    base, ref = impl(inp), _mb_ref(inp)
    fixed = D(str(inp["fixed_costs"]))
    rows = [(D(str(r["price"])), D(str(r["variable_cost"])), D(str(r["mix_units"]))) for r in inp["products"]]
    tm = sum((m for _, _, m in rows), D(0)); expected_wc = sum((m * (p - v) for p, v, m in rows), D(0)) / tm
    unit_keys = [k for k in base if k.startswith("units_")]
    profit = sum((base[k] * (p - v) for k, (p, v, _) in zip(unit_keys, rows)), D(0)) - fixed
    scaled = impl({**inp, "fixed_costs": str(fixed * 4)})
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("weighted_contribution_is_the_mix_weighted_margin", _close(base["weighted_contribution"], expected_wc), "the weighted margin uses the declared mix weights"),
        ("profit_at_break_even_is_zero", abs(profit) <= D("1e-9") * max(D(1), abs(fixed)), "selling the break-even mix exactly covers the fixed costs"),
        ("scaling_fixed_costs_scales_break_even_units", _close(scaled["breakeven_total_units"], base["breakeven_total_units"] * 4), "four times the fixed cost needs four times the units"),
        ("per_product_units_sum_to_the_total", _close(sum((base[k] for k in unit_keys), D(0)), base["breakeven_total_units"]), "the product units add up"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def multi_breakeven_profile(inp):
    try:
        rows = inp["products"]; fixed = D(str(inp["fixed_costs"]))
        errs = []
        if len(rows) < 2: errs.append("at least two products are needed")
        if fixed < 0: errs.append("fixed costs must be non-negative")
        for i, r in enumerate(rows):
            p_, v_, m_ = D(str(r["price"])), D(str(r["variable_cost"])), D(str(r["mix_units"]))
            if p_ <= 0: errs.append(f"product {i}: price must be positive")
            if m_ <= 0: errs.append(f"product {i}: mix_units must be positive")
        if not errs:
            tm = sum((D(str(r["mix_units"])) for r in rows), D(0))
            wc = sum((D(str(r["mix_units"])) * (D(str(r["price"])) - D(str(r["variable_cost"]))) for r in rows), D(0)) / tm
            if wc <= 0: errs.append("the weighted contribution margin must be positive for a break-even to exist")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["multi-product break-even inputs are malformed: fixed_costs and products (name, price, variable_cost, mix_units) are required"]

def _mb_typing(metric):
    if metric in ("breakeven_total_units", "total_mix_units") or metric.startswith("units_"): return ("units", 2)
    if metric in ("fixed_costs", "breakeven_revenue"): return ("currency", 2)
    return ("ratio", 4)

def multi_breakeven_caveats(out, th):
    return ["Break-even assumes a fixed product mix and constant unit prices and costs; a change in mix changes the weighted contribution and therefore the break-even.",
            "The per-product units are the break-even mix, not a target or a forecast.",
            "No step costs, capacity limits or tax are modelled."]

def multi_breakeven_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The mix-weighted contribution margin is " + tok("weighted_contribution") + ", so break-even needs " + tok("breakeven_total_units") +
            " units in total and revenue of " + tok("breakeven_revenue") + " at the declared mix. The per-product break-even units are in the appendix.")

# ---------- Two-way factorial ANOVA and post-hoc pairwise tests (B-070) ----------
# Balanced designs only: with unequal cell counts the sums of squares depend on the SS type (I/II/III),
# which is a convention the manual does not fix, so an unbalanced design BLOCKS instead of guessing one.
# Post-hoc pairs are Welch t-tests on every pair of groups, with a declared family-wise correction.

def _two_way_rows(inp):
    cells, ex = {}, 0
    for r in inp["data"]:
        a, b = str(r["factor_a"]).strip(), str(r["factor_b"]).strip()
        if r.get("response") is None or (isinstance(r.get("response"), str) and not r["response"].strip()): ex += 1; continue
        cells.setdefault((a, b), []).append(D(str(r["response"])))
    if not cells: raise DataError("no records with a response value remain")
    la = sorted({a for a, _ in cells}); lb = sorted({b for _, b in cells})
    if len(la) < 2 or len(lb) < 2: raise DataError("both factors need at least two levels")
    if len(cells) != len(la) * len(lb): raise DataError("the design has empty cells: every level combination needs observations")
    counts = {len(v) for v in cells.values()}
    if len(counts) != 1: raise DataError("the design is unbalanced: every cell must hold the same number of observations (unbalanced two-way ANOVA is not implemented)")
    n_cell = counts.pop()
    if n_cell < 2: raise DataError("every cell needs at least two observations for the error term")
    return cells, la, lb, n_cell, ex

def _f_sf(F, df1, df2):
    d1, d2 = float(D(str(df1))), float(D(str(df2)))
    return _fd(_betai(d2 / 2, d1 / 2, d2 / (d2 + d1 * float(F))))

def two_way_impl(inp):
    cells, la, lb, n_cell, ex = _two_way_rows(inp)
    allv = [v for cv in cells.values() for v in cv]; N = len(allv); grand = _mean(allv)
    cm = {k: _mean(v) for k, v in cells.items()}
    ma = {a: _mean([x for (aa, _b), v in cells.items() if aa == a for x in v]) for a in la}
    mb = {b: _mean([x for (_a, bb), v in cells.items() if bb == b for x in v]) for b in lb}
    ss_tot = sum(((x - grand) ** 2 for x in allv), D(0))
    ss_a = D(len(lb) * n_cell) * sum(((ma[a] - grand) ** 2 for a in la), D(0))
    ss_b = D(len(la) * n_cell) * sum(((mb[b] - grand) ** 2 for b in lb), D(0))
    ss_cells = D(n_cell) * sum(((cm[(a, b)] - grand) ** 2 for a in la for b in lb), D(0))
    ss_ab = ss_cells - ss_a - ss_b
    ss_err = ss_tot - ss_cells
    df_a, df_b, df_ab = len(la) - 1, len(lb) - 1, (len(la) - 1) * (len(lb) - 1)
    df_err = N - len(la) * len(lb); 
    if df_err <= 0: raise DataError("the error degrees of freedom are zero; the design is too small")
    ms_e = ss_err / df_err
    out = {"ss_a": ss_a, "ss_b": ss_b, "ss_ab": ss_ab, "ss_error": ss_err, "ss_total": ss_tot,
           "ms_a": ss_a / df_a, "ms_b": ss_b / df_b, "ms_ab": ss_ab / df_ab, "ms_error": ms_e,
           "f_a": (ss_a / df_a) / ms_e, "f_b": (ss_b / df_b) / ms_e, "f_ab": (ss_ab / df_ab) / ms_e,
           "df_a": D(df_a), "df_b": D(df_b), "df_ab": D(df_ab), "df_error": D(df_err),
           "partial_eta2_a": ss_a / (ss_a + ss_err), "partial_eta2_b": ss_b / (ss_b + ss_err), "partial_eta2_ab": ss_ab / (ss_ab + ss_err),
           "n": D(N), "n_cell": D(n_cell), "n_excluded": D(ex), "mean_grand": grand}
    out["p_a"] = _f_sf(out["f_a"], D(df_a), D(df_err)); out["p_b"] = _f_sf(out["f_b"], D(df_b), D(df_err)); out["p_ab"] = _f_sf(out["f_ab"], D(df_ab), D(df_err))
    return out

def _two_way_ref(inp):
    """Independent float route: numpy-free nested loops with a different summation order."""
    cells, la, lb, n_cell, ex = _two_way_rows(inp)
    data = [[float(x) for x in v] for v in cells.values()]; flat = [x for v in data for x in v]; N = len(flat)
    gm = sum(flat) / N
    def cell_mean(a, b): return sum(float(x) for x in cells[(a, b)]) / n_cell
    ss_tot = sum((x - gm) ** 2 for x in flat)
    ss_a = sum(len(lb) * n_cell * (sum(cell_mean(a, b) for b in lb) / len(lb) - gm) ** 2 for a in la)
    ss_b = sum(len(la) * n_cell * (sum(cell_mean(a, b) for a in la) / len(la) - gm) ** 2 for b in lb)
    ss_cells = sum(n_cell * (cell_mean(a, b) - gm) ** 2 for a in la for b in lb)
    return {"ss_a": ss_a, "ss_b": ss_b, "ss_ab": ss_cells - ss_a - ss_b, "ss_error": ss_tot - ss_cells, "ss_total": ss_tot}

def two_way_tests(inp, impl):
    base, ref = impl(inp), _two_way_ref(inp)
    cells, la, lb, n_cell, ex = _two_way_rows(inp)
    allv = [v for cv in cells.values() for v in cv]; k = D(5)
    shifted = impl({**inp, "data": [{**r, "response": (None if r.get("response") in (None, "") else str(D(str(r["response"])) + k))} for r in inp["data"]]})
    def scale(c): return None if c in (None, "") else str(D(str(c)) * 3)
    scaled = impl({**inp, "data": [{**r, "response": scale(r.get("response"))} for r in inp["data"]]})
    checks = [
        ("second_implementation_agrees", all(_close(base[x], ref[x]) for x in ref), "the independent float route reproduces every sum of squares"),
        ("sums_of_squares_decompose_the_total", _close(base["ss_a"] + base["ss_b"] + base["ss_ab"] + base["ss_error"], base["ss_total"]), "A + B + AB + error = total"),
        ("f_equals_mean_square_over_mean_square_error", _close(base["f_a"], base["ms_a"] / base["ms_error"]) and _close(base["f_ab"], base["ms_ab"] / base["ms_error"]), "each F is its mean square over the error mean square"),
        ("shifting_every_response_leaves_the_effects_unchanged", all(_close(shifted[x], base[x]) for x in ("ss_a", "ss_b", "ss_ab", "ss_error", "f_a", "f_b", "f_ab")), "adding a constant changes no sum of squares and no F"),
        ("scaling_every_response_scales_sums_of_squares_keeps_f", all(_close(scaled[x], base[x] * 9) for x in ("ss_a", "ss_b", "ss_ab", "ss_error")) and all(_close(scaled[x], base[x]) for x in ("f_a", "f_b", "f_ab")), "multiplying responses by three multiplies sums of squares by nine and leaves F unchanged"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def two_way_profile(inp):
    try: _two_way_rows(inp); return []
    except (DataError, InvalidOperation, ValueError, TypeError, KeyError) as e:
        return [str(e)] if isinstance(e, DataError) else ["two-way inputs are malformed: data must be records with response, factor_a and factor_b"]

def _two_typing(metric):
    if metric in ("n", "n_cell", "n_excluded", "df_a", "df_b", "df_ab", "df_error"): return ("count", 0)
    if metric.startswith("p_"): return ("probability", 4)
    if metric.startswith("partial_eta2"): return ("ratio", 3)
    if metric.startswith("f_"): return ("ratio", 3)
    return ("@unit", 3)

def two_way_caveats(out, th):
    return ["Balanced two-way ANOVA only: unequal cell counts are refused because the sums of squares would depend on a type-of-SS convention the manual does not fix.",
            "A significant interaction means the simple effect of one factor depends on the level of the other; the omnibus tests alone do not say where the difference lies (use the post-hoc pairwise method for the groups you intended).",
            "Assumptions (normality, equal variances, independence) are not tested; the design and the cell sizes must be checked by the person who collected the data."]

def two_way_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The balanced two-way ANOVA over " + tok("n") + " observations has an F of " + tok("f_a") + " for the first factor with a p-value of " + tok("p_a") +
            ", an F of " + tok("f_b") + " for the second factor with a p-value of " + tok("p_b") +
            ", and an interaction F of " + tok("f_ab") + " with a p-value of " + tok("p_ab") + ". The decomposition is reported in the appendix; no post-hoc comparison is implied by an omnibus test.")

def _grp_any(inp):
    codes = {D(str(c)) for c in inp.get("missing_codes", [])}
    out, ex = {}, 0
    for nm, col in inp["groups"].items():
        v = []
        for x in col:
            if x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes: ex += 1
            else: v.append(D(str(x)))
        out[nm] = v
    return out, ex

def _adjust(raw, method):
    m = len(raw)
    if method == "none": return list(raw)
    if method == "bonferroni": return [min(1.0, m * p) for p in raw]
    order = sorted(range(m), key=lambda i: (raw[i], i)); out = [0.0] * m; run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * raw[i])); out[i] = run
    return out

def posthoc_impl(inp):
    g, ex = _grp_any(inp); names = list(g)
    if len(names) < 2: raise DataError("at least two groups are needed")
    for nm in names:
        if len(g[nm]) < 2: raise DataError(f"group {nm!r} needs at least two observations")
        if _var(g[nm]) == 0: raise DataError(f"group {nm!r} has zero variance, so a pairwise comparison is undefined")
    method = inp.get("adjust", "holm"); alpha = D(str(inp.get("alpha", "0.05")))
    if method not in ("holm", "bonferroni", "none"): raise DataError("adjust must be holm, bonferroni or none")
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    out, raw = {}, []
    for a, b in pairs:
        va, vb = g[a], g[b]; na, nb = D(len(va)), D(len(vb)); ma, mb = _mean(va), _mean(vb)
        qa, qb = _var(va) / na, _var(vb) / nb; se = (qa + qb).sqrt(); diff = ma - mb; t = diff / se
        df = (qa + qb) ** 2 / (qa ** 2 / (na - 1) + qb ** 2 / (nb - 1)); p = _p_t(float(t), float(df)); raw.append(float(p))
        out[f"diff_{a}_{b}"] = diff; out[f"p_raw_{a}_{b}"] = _fd(p); out[f"df_{a}_{b}"] = df; out[f"t_{a}_{b}"] = t
    adj = _adjust(raw, method); n_rej = 0
    for (a, b), p in zip(pairs, adj):
        out[f"p_adj_{a}_{b}"] = _fd(p)
        if D(str(p)) <= alpha: n_rej += 1
    out.update({"n_pairs": D(len(pairs)), "n_rejected": D(n_rej), "alpha": alpha, "n_excluded": D(ex),
                "_appendix": {"adjust": method, "alpha": str(alpha), "pairs": [a + " vs " + b for a, b in pairs],
                              "correction": ("Holm step-down family-wise correction" if method == "holm" else "Bonferroni family-wise correction" if method == "bonferroni" else "none: raw p-values, declared as uncorrected")}})
    return out

def _posthoc_ref(inp):
    g, ex = _grp_any(inp); names = list(g)
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    raw = []
    for a, b in pairs:
        xa = [float(x) for x in g[a]]; xb = [float(x) for x in g[b]]
        ma, mb = statistics.fmean(xa), statistics.fmean(xb); va, vb = statistics.variance(xa), statistics.variance(xb)
        qa, qb = va / len(xa), vb / len(xb); se = math.sqrt(qa + qb); t = (ma - mb) / se
        df = (qa + qb) ** 2 / (qa ** 2 / (len(xa) - 1) + qb ** 2 / (len(xb) - 1))
        raw.append(_betai(df / 2, 0.5, df / (df + t * t)))
    return {"raw": raw, "adj": _adjust(raw, inp.get("adjust", "holm"))}

def posthoc_tests(inp, impl):
    base, ref = impl(inp), _posthoc_ref(inp)
    g, ex = _grp_any(inp); names = list(g)
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    raw_keys = [f"p_raw_{a}_{b}" for a, b in pairs]; adj_keys = [f"p_adj_{a}_{b}" for a, b in pairs]
    rev = {**inp, "groups": {k: list(reversed(v)) for k, v in reversed(list(inp["groups"].items()))}}
    rev_out = impl(rev)
    expected_pairs = len(names) * (len(names) - 1) // 2
    checks = [
        ("second_implementation_agrees", all(_close(base[k], r) for k, r in zip(raw_keys, ref["raw"])) and all(_close(base[k], r) for k, r in zip(adj_keys, ref["adj"])), "independent float route agrees on every raw and adjusted p-value"),
        ("adjusted_p_is_never_below_the_raw_p", all(D(str(base[a])) >= D(str(base[r])) - D("1e-15") for a, r in zip(adj_keys, raw_keys)), "a correction cannot make evidence look stronger"),
        ("correction_matches_its_definition", _posthoc_adjust_ok(base, pairs, inp), "the adjusted p-values reproduce the declared correction step by step"),
        ("pair_count_is_choose_k_2", int(base["n_pairs"]) == expected_pairs, "every unordered pair of groups is compared once"),
        ("reversing_group_order_keeps_the_evidence", all(_close(rev_out[f"p_raw_{b}_{a}"], base[f"p_raw_{a}_{b}"]) for a, b in pairs) and all(_close(rev_out[f"diff_{b}_{a}"], -base[f"diff_{a}_{b}"]) for a, b in pairs), "swapping the column order negates each difference but keeps every p-value"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _posthoc_adjust_ok(base, pairs, inp):
    """Recompute the declared correction from the raw p-values with an explicit step-by-step loop."""
    method = inp.get("adjust", "holm"); m = len(pairs)
    raw = [float(D(str(base[f"p_raw_{a}_{b}"]))) for a, b in pairs]
    adj = [float(D(str(base[f"p_adj_{a}_{b}"]))) for a, b in pairs]
    if method == "none": return all(abs(x - y) <= 1e-12 for x, y in zip(adj, raw))
    if method == "bonferroni": return all(abs(x - min(1.0, m * y)) <= 1e-12 for x, y in zip(adj, raw))
    order = sorted(range(m), key=lambda i: (raw[i], i)); run = 0.0; want = [0.0] * m
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * raw[i])); want[i] = run
    return all(abs(x - y) <= 1e-12 for x, y in zip(adj, want))

def posthoc_profile(inp):
    try:
        g, ex = _grp_any(inp)
        if len(g) < 2: return ["at least two groups are needed"]
        for nm, v in g.items():
            if len(v) < 2: return [f"group {nm!r} needs at least two observations"]
            if len(set(v)) == 1: return [f"group {nm!r} has zero variance"]
        if inp.get("adjust", "holm") not in ("holm", "bonferroni", "none"): return ["adjust must be holm, bonferroni or none"]
        a = D(str(inp.get("alpha", "0.05")))
        if not (0 < a < 1): return ["alpha must be between 0 and 1"]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["post-hoc inputs are malformed: supply a groups object of name -> observations"]

def _posthoc_typing(metric):
    if metric in ("n_pairs", "n_rejected", "n_excluded"): return ("count", 0)
    if metric.startswith("p_"): return ("probability", 4)
    if metric.startswith("df_"): return ("ratio", 3)
    if metric.startswith("t_"): return ("ratio", 3)
    if metric == "alpha": return ("rate", 2)
    return ("@unit", 3)

def posthoc_caveats(out, th):
    return ["Every pair of groups is compared with a Welch t-test (unequal variances assumed); the family-wise correction declared in the request (Holm, Bonferroni or none) is recorded in the appendix.",
            "A correction controls the family-wise error rate; it does not fix a biased sample, a violated normality assumption or a family chosen after looking at the data.",
            "Pairs are only meaningful for comparisons the study intended; scanning all pairs for the smallest p-value is exactly what the correction is for."]

def posthoc_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The declared family has " + tok("n_pairs") + " pairwise comparisons. With the declared correction at level " + tok("alpha") +
            ", " + tok("n_rejected") + " adjusted p-values are at or below that level. Each pair is a Welch comparison; the corrected and raw p-values are both in the appendix.")


# ---------- Valuation: WACC and DCF (gap map P1 finance; B-068) ----------
# Both are arithmetic on declared inputs. No tax is computed: the cost of debt is supplied AFTER tax.
# DCF assumptions (end-of-period free cash flows, Gordon-growth terminal value) are declared, not hidden.

def wacc_impl(inp):
    E, Dv = D(str(inp["equity_value"])), D(str(inp["debt_value"]))
    ke, kd = D(str(inp["cost_of_equity"])), D(str(inp["cost_of_debt_after_tax"]))
    if E < 0 or Dv < 0: raise DataError("equity and debt market values must be non-negative")
    if ke < 0 or kd < 0: raise DataError("costs of capital must be non-negative")
    total = E + Dv
    if total <= 0: raise DataError("at least one of equity and debt must be positive")
    we, wd = E / total, Dv / total
    return {"wacc": we * ke + wd * kd, "weight_equity": we, "weight_debt": wd,
            "cost_of_equity": ke, "cost_of_debt_after_tax": kd}

def _wacc_reference(inp):
    E, Dv = float(D(str(inp["equity_value"]))), float(D(str(inp["debt_value"])))
    ke, kd = float(D(str(inp["cost_of_equity"]))), float(D(str(inp["cost_of_debt_after_tax"])))
    total = E + Dv; we = E / total; wd = Dv / total
    return {"wacc": we * ke + wd * kd, "weight_equity": we, "weight_debt": wd}

def _wacc_tests(inp, impl):
    base, ref = impl(inp), _wacc_reference(inp)
    E, Dv = D(str(inp["equity_value"])), D(str(inp["debt_value"])); ke = D(str(inp["cost_of_equity"])); kd = D(str(inp["cost_of_debt_after_tax"]))
    scaled = impl({**inp, "equity_value": str(E * 7), "debt_value": str(Dv * 7)})
    up = impl({**inp, "cost_of_equity": str(ke + D("0.1"))})
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("weights_sum_to_one", _close(base["weight_equity"] + base["weight_debt"], D(1)), "the capital-structure weights are exhaustive"),
        ("wacc_is_between_the_two_costs", min(ke, kd) <= base["wacc"] <= max(ke, kd), "a weighted average lies between its components"),
        ("scaling_both_market_values_changes_nothing", _close(scaled["wacc"], base["wacc"]) and _close(scaled["weight_equity"], base["weight_equity"]), "only the relative weights matter"),
        ("rising_cost_of_equity_raises_wacc", up["wacc"] > base["wacc"], "a more expensive source of capital raises the average"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _wacc_profile(inp):
    try:
        E, Dv = D(str(inp["equity_value"])), D(str(inp["debt_value"]))
        ke, kd = D(str(inp["cost_of_equity"])), D(str(inp["cost_of_debt_after_tax"]))
        errs = []
        if E < 0 or Dv < 0: errs.append("equity and debt values must be non-negative")
        if E + Dv <= 0: errs.append("equity plus debt must be positive")
        if ke < 0 or kd < 0: errs.append("costs of capital must be non-negative")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["wacc inputs are malformed: equity_value, debt_value, cost_of_equity and cost_of_debt_after_tax are required numbers"]

def _wacc_typing(metric): return ("rate", 4)

def _wacc_caveats(out, th):
    return ["The costs of capital are inputs, not estimates made here: the cost of equity and the AFTER-TAX cost of debt must be declared, and no tax is computed by this method.",
            "Market values of equity and debt are used for the weights; book values would give different weights and a different WACC.",
            "WACC is a single discount rate for a whole firm or project; it is not appropriate for cash flows with materially different risk."]

def _wacc_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The weighted average cost of capital is " + tok("wacc") + ", with an equity weight of " + tok("weight_equity") +
            " and a debt weight of " + tok("weight_debt") + ". The costs of equity and after-tax debt are inputs; no tax is computed here.")

def dcf_impl(inp):
    cfs = [D(str(x)) for x in inp["cashflows"]]
    r = D(str(inp["discount_rate"]))
    raw_g = inp.get("terminal_growth")
    g = None if raw_g is None or (isinstance(raw_g, str) and not raw_g.strip()) else D(str(raw_g))
    if not cfs: raise DataError("at least one cash flow is required")
    if r <= -1: raise DataError("the discount rate must be greater than -100%")
    if g is not None and not (r > g): raise DataError("the terminal growth rate must be below the discount rate")
    n = len(cfs)
    pv = sum((cf / (1 + r) ** t for t, cf in enumerate(cfs, 1)), D(0))
    tv = (cfs[-1] * (1 + g) / (r - g)) if g is not None else D(0)
    pvt = tv / (1 + r) ** n
    ev = pv + pvt
    out = {"pv_explicit": pv, "pv_terminal": pvt, "terminal_value": tv, "enterprise_value": ev,
           "terminal_share": (pvt / ev) if ev != 0 else D(0), "n_periods": D(n), "discount_rate": r}
    if g is not None: out["terminal_growth"] = g
    return out

def _dcf_reference(inp):
    cfs = [float(D(str(x))) for x in inp["cashflows"]]; r = float(D(str(inp["discount_rate"])))
    raw_g = inp.get("terminal_growth"); g = None if raw_g is None or (isinstance(raw_g, str) and not raw_g.strip()) else float(D(str(raw_g)))
    pv = 0.0
    for t, cf in enumerate(cfs, 1): pv += cf / (1 + r) ** t
    n = len(cfs); tv = cfs[-1] * (1 + g) / (r - g) if g is not None else 0.0; pvt = tv / (1 + r) ** n
    return {"pv_explicit": pv, "pv_terminal": pvt, "terminal_value": tv, "enterprise_value": pv + pvt}

def _dcf_tests(inp, impl):
    base, ref = impl(inp), _dcf_reference(inp)
    cfs = [D(str(x)) for x in inp["cashflows"]]; r = D(str(inp["discount_rate"]))
    doubled = impl({**inp, "cashflows": [str(c * 2) for c in cfs]})
    raw_g = inp.get("terminal_growth")
    g = None if raw_g is None or (isinstance(raw_g, str) and not raw_g.strip()) else D(str(raw_g))
    higher_r = impl({**inp, "discount_rate": str(r + D("0.01"))}) if (g is None or r + D("0.01") > g) else base
    no_g = impl({k: v for k, v in inp.items() if k != "terminal_growth"})
    expect_tv = (cfs[-1] * (1 + g) / (r - g)) if g is not None else D(0)
    checks = [
        ("second_implementation_agrees", all(_close(base[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("value_scales_with_the_cash_flows", all(_close(doubled[k], base[k] * 2) for k in ("pv_explicit", "pv_terminal", "enterprise_value")), "doubling every cash flow doubles the value"),
        ("a_higher_discount_rate_lowers_the_value", higher_r["enterprise_value"] < base["enterprise_value"], "discounting more heavily reduces the present value"),
        ("terminal_value_is_gordon_growth_on_the_last_flow", _close(base["terminal_value"], expect_tv), "terminal value = last cash flow x (1+g) / (r-g)"),
        ("without_terminal_growth_there_is_no_terminal_value", no_g["pv_terminal"] == 0 and no_g["enterprise_value"] == no_g["pv_explicit"], "omitting growth leaves the explicit forecast only"),
    ]
    return [(n, ok) for n, ok, _ in checks]

def _dcf_profile(inp):
    try:
        cfs = [D(str(x)) for x in inp["cashflows"]]
        r = D(str(inp["discount_rate"]))
        raw_g = inp.get("terminal_growth"); g = None if raw_g is None or (isinstance(raw_g, str) and not raw_g.strip()) else D(str(raw_g))
        errs = []
        if not cfs: errs.append("at least one cash flow is required")
        if r <= -1: errs.append("the discount rate must be greater than -100%")
        if g is not None and not (r > g): errs.append("the terminal growth rate must be below the discount rate")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["dcf inputs are malformed: cashflows and a numeric discount_rate are required"]

def _dcf_typing(metric):
    if metric == "n_periods": return ("count", 0)
    if metric == "terminal_share": return ("ratio", 3)
    if metric in ("discount_rate", "terminal_growth"): return ("rate", 2)
    return ("currency", 2)

def _dcf_caveats(out, th):
    c = ["The value is model-conditional: it is the present value of the cash flows and terminal growth you declared, not a market price or a forecast guarantee.",
         "End-of-period cash flows are assumed; a mid-year convention would raise the value. No tax is computed: supply after-tax cash flows.",
         "The terminal value usually dominates the result and rests entirely on the growth and discount-rate assumptions."]
    if out.get("terminal_share", D(0)) > D("0.75"): c.append("The terminal value is more than three quarters of the total value, so the growth assumption drives the answer.")
    return c

def _dcf_template(out, P, th):
    tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The present value of the explicit forecast is " + tok("pv_explicit") + ", and the present value of the terminal value is " +
            tok("pv_terminal") + " (a terminal share of " + tok("terminal_share") + "), giving an enterprise value of " + tok("enterprise_value") + ". "
            "The value is computed from the declared cash flows, discount rate and terminal-growth assumptions; it is not a market price.")

# ---------- Multiple-comparison correction (manual 9B.3; B-060) ----------
# Pure arithmetic on a family of p-values that the user has already declared. Holm is the default choice
# because it controls the family-wise error rate under arbitrary dependence while being uniformly more
# powerful than Bonferroni; both are implemented as declared conventions, with the definition stated.
def _mc_apply(ps, method):
    k = len(ps)
    if method == "bonferroni": return [min(1.0, k * p) for p in ps]
    pairs = list(enumerate(ps)); pairs.sort(key=lambda t: (t[1], t[0]))
    out, prev = [0.0] * k, 0.0
    for pos, (i, p) in enumerate(pairs):
        prev = max(prev, min(1.0, (k - pos) * p)); out[i] = prev
    return out

def _mc_reference(ps, method):
    """Independent route: float arithmetic with an explicit rank loop (different number type from _fd outputs)."""
    k = len(ps)
    if method == "bonferroni": return [min(1.0, float(D(str(k))) * p) for p in ps]
    order = sorted(range(k), key=lambda i: (ps[i], i)); out = [0.0] * k; run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (k - rank) * ps[i])); out[i] = run
    return out

def _mc_checks(ps, adj, method, alpha):
    ref = _mc_reference(ps, method)
    k = len(ps)
    reversed_map = list(reversed(_mc_apply(list(reversed(ps)), method)))
    if method == "bonferroni": definition = all(abs(a - min(1.0, k * p)) <= 1e-12 for a, p in zip(adj, ps))
    else: definition = all(abs(a - r) <= 1e-12 * max(1.0, abs(r)) for a, r in zip(adj, ref)) and all(x <= y + 1e-12 for x, y in zip(sorted(adj), sorted(adj)[1:]))
    return [
        ("adjusted_p_values_are_at_least_the_raw_ones", all(a >= p - 1e-12 for a, p in zip(adj, ps)), "a correction never makes evidence look stronger"),
        ("adjusted_p_values_are_bounded_in_zero_one", all(0.0 <= a <= 1.0 for a in adj), "adjusted values stay in [0, 1]"),
        ("declared_correction_matches_its_definition", definition, "Holm is a monotone step-down; Bonferroni is k x p capped at 1"),
        ("second_implementation_agrees", all(abs(a - r) <= 1e-12 * max(1.0, abs(r)) for a, r in zip(adj, ref)), "the declared formula is reproduced by an independent route"),
        ("correction_is_order_invariant", all(abs(a - b) <= 1e-12 for a, b in zip(adj, reversed_map)), "reordering the family does not change the adjusted values"),
    ]

def _mc_impl(inp):
    ps = [float(D(str(x))) for x in inp["p_values"]]
    if any(not (0.0 <= p <= 1.0) for p in ps): raise DataError("every p-value must be between 0 and 1")
    method = inp["method"]; alpha = float(D(str(inp.get("alpha", "0.05"))))
    if not (0.0 < alpha < 1.0): raise DataError("alpha must be between 0 and 1")
    adj, k = _mc_apply(ps, method), len(ps)
    out = {f"p_adj_{i + 1}": _fd(adj[i]) for i in range(k)}
    out.update({"n_tests": D(k), "n_rejected": D(sum(1 for a in adj if a <= alpha)), "alpha": _fd(alpha)})
    appendix = {"method": method, "alpha": str(alpha), "raw_p_values": [repr(p) for p in ps], "adjusted_p_values": [repr(a) for a in adj],
                "definition": ("Holm step-down: sort p ascending, multiply the i-th smallest by (k - i + 1), take a running maximum, cap at 1." if method == "holm"
                               else "Bonferroni: multiply each p by the number of tests and cap at 1.")}
    return {**out, "_appendix": appendix, "_checks": _mc_checks(ps, adj, method, alpha)}

def _mc_tests(inp, impl): return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def _mc_profile(inp):
    p = [float(D(str(x))) for x in inp.get("p_values", [])]
    if any(not (0.0 <= x <= 1.0) for x in p): return ["every p-value must be between 0 and 1"]
    a = float(D(str(inp.get("alpha", "0.05"))))
    if not (0.0 < a < 1.0): return ["alpha must be between 0 and 1"]
    return []

def _mc_typing(metric):
    return ("count", 0) if metric in ("n_tests", "n_rejected") else ("probability", 4)

def _mc_caveats(out, thresholds):
    return ["The family of hypotheses must be declared before looking at the p-values; a correction cannot undo a family chosen afterwards.",
            "Holm and Bonferroni control the family-wise error rate under arbitrary dependence; they do not model dependence and are therefore less powerful than methods that do (not implemented).",
            "A correction fixes the reported evidence, not the design: a biased sample or a violated test assumption is still biased or violated."]

def _mc_template(outputs, period, thresholds=None):
    P = period; tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return (f"The declared family has {tok('n_tests')} tests. After the declared correction at level {tok('alpha')}, "
            f"{tok('n_rejected')} adjusted p-values are at or below that level. The correction changes only the p-values, "
            "not the design or the assumption checks behind each test; the family must have been declared before the results were seen.")

# ---------- Power and minimum detectable effect (manual 9B.3; B-061) ----------
# Planning arithmetic for a two-sample or one-sample comparison of means under the NORMAL approximation.
# With known or planning standard deviations the normal model is exact; with estimated sds the exact
# calculation would use the noncentral t distribution (not implemented). That approximation is declared.
_POWER_DESIGNS = ("two_sample", "one_sample")

def _phi(x): return NormalDist().cdf(float(x))
def _zinv(p): return NormalDist().inv_cdf(float(p))

def _phi_ref(x): return 0.5 * math.erfc(-x / math.sqrt(2))
def _z_ref(p):
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _phi_ref(mid) < float(p): lo = mid
        else: hi = mid
    return (lo + hi) / 2

def _power_core(design, effect, n1, n2, sd1, sd2, alpha, tails, target):
    if design not in _POWER_DESIGNS: raise DataError("design must be two_sample or one_sample")
    if sd1 <= 0 or (design == "two_sample" and sd2 <= 0): raise DataError("standard deviations must be positive")
    if n1 < 2 or (design == "two_sample" and n2 < 2): raise DataError("each sample size must be at least 2")
    if not (0.0 < alpha < 1.0): raise DataError("alpha must be between 0 and 1")
    if not (0.0 < target < 1.0): raise DataError("target_power must be between 0 and 1")
    if effect < 0: raise DataError("effect must be non-negative")
    se = math.sqrt(sd1 * sd1 / n1 + sd2 * sd2 / n2) if design == "two_sample" else sd1 / math.sqrt(n1)
    za = _zinv(1 - alpha / 2 if tails == "two_sided" else 1 - alpha)
    ncp = abs(effect) / se
    power = _phi(ncp - za) + (_phi(-ncp - za) if tails == "two_sided" else 0.0)
    return {"se": se, "ncp": ncp, "z_alpha": za, "power": power, "mde": (za + _zinv(target)) * se}

def _power_reference(design, effect, n1, n2, sd1, sd2, alpha, tails, target):
    """Independent route: erfc-based normal CDF and a bisection inverse (no NormalDist class)."""
    se = math.sqrt(sd1 * sd1 / n1 + sd2 * sd2 / n2) if design == "two_sample" else sd1 / math.sqrt(n1)
    za = _z_ref(1 - alpha / 2 if tails == "two_sided" else 1 - alpha); ncp = abs(effect) / se
    power = _phi_ref(ncp - za) + (_phi_ref(-ncp - za) if tails == "two_sided" else 0.0)
    return {"se": se, "ncp": ncp, "z_alpha": za, "power": power, "mde": (za + _z_ref(target)) * se}

def _power_impl(inp):
    design = inp["design"]; n1 = float(D(str(inp["n1"]))); n2 = float(D(str(inp.get("n2", "0"))))
    sd1 = float(D(str(inp["sd1"]))); sd2 = float(D(str(inp.get("sd2", "0"))))
    alpha = float(D(str(inp.get("alpha", "0.05")))); target = float(D(str(inp.get("target_power", "0.8"))))
    tails = inp.get("tails", "two_sided"); effect = float(D(str(inp["effect"])))
    c = _power_core(design, effect, n1, n2, sd1, sd2, alpha, tails, target)
    out = {"power": _fd(c["power"]), "mde": _fd(c["mde"]), "se": _fd(c["se"]), "ncp": _fd(c["ncp"]), "z_alpha": _fd(c["z_alpha"]),
           "alpha": _fd(alpha), "target_power": _fd(target), "n1": D(str(inp["n1"]))}
    if design == "two_sample": out["n2"] = D(str(inp["n2"]))
    appendix = {"design": design, "tails": tails, "effect": str(abs(effect)), "standard_deviations": [str(sd1), (str(sd2) if design == "two_sample" else None)],
                "model": "normal approximation: power = Phi(ncp - z_alpha) + (Phi(-ncp - z_alpha) if two-sided else 0); mde = (z_alpha + z_target) * se",
                "approx_limits": "exact when the standard deviations are known/planned; with estimated sds an exact calculation would use the noncentral t distribution (not implemented)."}
    return {**out, "_appendix": appendix, "_checks": _power_checks(inp, out)}

def _power_checks(inp, out):
    design = inp["design"]; two = design == "two_sample"
    e = float(D(str(inp["effect"]))); n1 = float(D(str(inp["n1"]))); n2 = float(D(str(inp.get("n2", "0")))) if two else 0.0
    sd1 = float(D(str(inp["sd1"]))); sd2 = float(D(str(inp.get("sd2", "0")))) if two else 0.0
    alpha = float(D(str(inp.get("alpha", "0.05")))); target = float(D(str(inp.get("target_power", "0.8")))); tails = inp.get("tails", "two_sided")
    ref = _power_reference(design, e, n1, n2, sd1, sd2, alpha, tails, target)
    zero = _power_core(design, 0.0, n1, n2, sd1, sd2, alpha, tails, target)
    bigger = _power_core(design, e * 2 + 1, n1, n2, sd1, sd2, alpha, tails, target)
    more_n = _power_core(design, e, n1 * 2, n2 * 2 if two else 0.0, sd1, sd2, alpha, tails, target)
    return [
        ("second_implementation_agrees", _close(out["power"], ref["power"]) and _close(out["mde"], ref["mde"]) and _close(out["ncp"], ref["ncp"]), "erfc-based route agrees with the NormalDist route"),
        ("power_at_zero_effect_equals_alpha", _close(zero["power"], alpha), "with no effect the rejection rate is the declared alpha"),
        ("power_increases_with_effect_size", bigger["power"] > _power_core(design, e, n1, n2, sd1, sd2, alpha, tails, target)["power"], "a larger effect is easier to detect"),
        ("power_increases_with_sample_size", more_n["power"] >= _power_core(design, e, n1, n2, sd1, sd2, alpha, tails, target)["power"], "more observations do not reduce power"),
        ("mde_decreases_with_sample_size", more_n["mde"] < _power_core(design, e, n1, n2, sd1, sd2, alpha, tails, target)["mde"], "more observations detect a smaller effect at the same power"),
    ]

def _power_tests(inp, impl): return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def _power_profile(inp):
    try:
        design = inp["design"]; two = design == "two_sample"
        n1 = float(D(str(inp["n1"]))); sd1 = float(D(str(inp["sd1"])))
        effect = float(D(str(inp["effect"]))); alpha = float(D(str(inp.get("alpha", "0.05")))); target = float(D(str(inp.get("target_power", "0.8"))))
        errs = []
        if design not in _POWER_DESIGNS: return ["design must be two_sample or one_sample"]
        if two:
            if "n2" not in inp: errs.append("two_sample design needs n2")
            if "sd2" not in inp: errs.append("two_sample design needs sd2")
            if "n2" in inp and float(D(str(inp["n2"]))) < 2: errs.append("n2 must be at least 2")
            if "sd2" in inp and float(D(str(inp["sd2"]))) <= 0: errs.append("sd2 must be positive")
        else:
            if "n2" in inp or "sd2" in inp: errs.append("one_sample design does not take n2 or sd2")
        if n1 < 2: errs.append("n1 must be at least 2")
        if sd1 <= 0: errs.append("sd1 must be positive")
        if effect < 0: errs.append("effect must be non-negative")
        if not (0.0 < alpha < 1.0): errs.append("alpha must be between 0 and 1")
        if not (0.0 < target < 1.0): errs.append("target_power must be between 0 and 1")
        return errs
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["power_analysis inputs are malformed: design, effect, n1 and sd1 are required numbers"]

def _power_typing(metric):
    if metric in ("n1", "n2"): return ("count", 0)
    if metric in ("se", "mde"): return ("@unit", 2)
    if metric in ("power", "alpha", "target_power"): return ("probability", 4)
    return ("ratio", 3)

def _power_caveats(out, thresholds):
    return ["Power is calculated under the normal approximation with the standard deviations you supplied; with sds estimated from a pilot, the exact power is somewhat lower (noncentral t, not implemented).",
            "Power is a planning property of the design, not evidence about the result: a low-powered study can still be significant and a high-powered one can still fail.",
            "The calculation assumes independent observations and a single comparison; it does not account for clustering, weights, repeated measures or multiplicity.",
            "A minimum detectable effect is not a justification for ignoring a smaller effect that matters."]

def _power_template(outputs, period, thresholds=None):
    P = period; tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return (f"At the stated effect the design has power {tok('power')} against a declared alpha of {tok('alpha')} "
            f"(target power {tok('target_power')}). The smallest effect that reaches that target power is {tok('mde')}, with a standard error of {tok('se')} for that effect. "
            "Power is calculated under the normal approximation and describes the planned design, not any observed result.")

# ---------- Missing-data bounds (manual 9B.3; B-062) ----------
# The system cannot know WHY values are missing. Instead of imputing, this method reports the worst-case
# (extreme-case) bounds on the complete-data mean: every missing value at the observed minimum or at the
# observed maximum. It also records the mechanism the owner DECLARES, clearly labelled as declared, not verified.
_MECHANISMS = ("unknown", "mcar", "mar", "mnar")

def _md_impl(inp):
    vals, miss = _clean(inp); total = len(vals) + miss
    if not vals: raise DataError("no valid values remain, so the missing-data bounds are undefined")
    mech = inp.get("mechanism", "unknown")
    if mech not in _MECHANISMS: raise DataError("mechanism must be one of: " + ", ".join(_MECHANISMS))
    n, mn, mx = len(vals), min(vals), max(vals)
    s = sum(vals, D(0)); mean = s / n
    if miss:
        low, high = (s + miss * mn) / total, (s + miss * mx) / total
    else:
        low = high = mean
    pct = D(miss) / D(total)
    out = {"n_valid": D(n), "n_missing": D(miss), "pct_missing": _fd(pct), "mean_observed": mean,
           "bound_low": low, "bound_high": high, "bound_width": high - low}
    appendix = {"mechanism_declared": mech,
                "mechanism_note": "The mechanism is the owner's declaration; the system cannot verify it from the data.",
                "convention": "Extreme-case bounds: the complete-data mean if every missing value sat at the smallest observed value (lower) or the largest observed value (upper). No imputation and no probabilistic missing-data model is used.",
                "observed_range": [str(mn), str(mx)]}
    return {**out, "_appendix": appendix, "_checks": _md_checks(inp, vals, miss, out)}

def _md_checks(inp, vals, miss, out):
    n, mn, mx = len(vals), min(vals), max(vals); total = n + miss; s = sum(vals, D(0))
    ref_low = (s + miss * mn) / total if miss else s / n
    ref_high = (s + miss * mx) / total if miss else s / n
    more_miss, more_total = miss + 2, total + 2                       # two extra missing entries, recomputed directly
    more_width = (s + more_miss * mx) / more_total - (s + more_miss * mn) / more_total
    return [
        ("bounds_bracket_the_observed_mean", out["bound_low"] <= out["mean_observed"] <= out["bound_high"], "the observed mean lies inside the bounds"),
        ("bounds_are_the_extreme_cases", _close(out["bound_low"], ref_low) and _close(out["bound_high"], ref_high), "independently recomputed extreme-case values agree"),
        ("bounds_widen_with_more_missing_values", mn == mx or more_width >= out["bound_width"], "adding missing values cannot narrow the bounds"),
        ("percentage_is_missing_over_total", _close(out["pct_missing"], D(miss) / D(total)), "the reported share is missing / total"),
        ("no_missing_values_means_a_zero_width_bound", out["bound_width"] == 0 if miss == 0 else True, "with no missing values the bounds collapse to the observed mean"),
    ]

def _md_tests(inp, impl): return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def _md_profile(inp):
    try:
        vals, miss = _clean(inp)
        if not vals: return ["no valid values remain after excluding missing values"]
        mech = inp.get("mechanism", "unknown")
        if mech not in _MECHANISMS: return ["mechanism must be one of: " + ", ".join(_MECHANISMS)]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["missing-data inputs are malformed: values must be a list of numbers"]

def _md_typing(metric):
    if metric in ("n_valid", "n_missing"): return ("count", 0)
    if metric == "pct_missing": return ("probability", 4)
    return ("@unit", 2)

def _md_caveats(out, thresholds):
    return ["The bounds are the extreme cases: every missing value at the observed minimum, or every one at the observed maximum. They are honest bounds, not estimates, and they can be very wide.",
            "No imputation and no MAR/MCAR/MNAR model is used; the declared mechanism is recorded as the owner's declaration and is not verifiable from the data.",
            "Bounds cover the complete-data mean only; they say nothing about other statistics or about which mechanism actually holds."]

def _md_template(outputs, period, thresholds=None):
    P = period; tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The observed values have a mean of " + tok("mean_observed") + ", with " + tok("n_missing") + " of the entries missing (" + tok("pct_missing") + " of the total). "
            "Under the extreme-case convention the complete-data mean lies between " + tok("bound_low") + " and " + tok("bound_high") + ". "
            "The declared missing-data mechanism is recorded as a declaration, not as a verified fact.")

# ---------- Weighted summary (manual 9B.3; B-063) ----------
# Summaries under design or frequency weights. NO inference is provided: without a declared complex design
# there is no honest standard error, so none is manufactured. The weight kind is declared and overridable.
_WEIGHT_KINDS = ("reliability", "frequency")

def _w_missing_codes(inp): return {D(str(c)) for c in inp.get("missing_codes", [])}

def _w_is_missing(x, codes):
    return x is None or (isinstance(x, str) and not x.strip()) or D(str(x)) in codes

def _w_pairs(inp):
    """(valid (value, weight) pairs, number of missing entries). One weight per value, including missing ones."""
    codes = _w_missing_codes(inp); pairs, miss = [], 0
    for x, w in zip(inp["values"], inp["weights"]):
        if _w_is_missing(x, codes): miss += 1; continue
        pairs.append((D(str(x)), D(str(w))))
    return pairs, miss

def _w_stats(pairs, kind):
    sw = sum((w for _, w in pairs), D(0)); sw2 = sum((w * w for _, w in pairs), D(0))
    mean = sum((w * x for x, w in pairs), D(0)) / sw
    ss = sum((w * (x - mean) ** 2 for x, w in pairs), D(0))
    denom = sw - sw2 / sw if kind == "reliability" else sw - 1
    if denom <= 0: raise DataError("the weights leave no degrees of freedom for the weighted standard deviation")
    n_eff = sw * sw / sw2
    return {"weighted_mean": mean, "weighted_sd": (ss / denom).sqrt(), "sum_weights": sw,
            "n_eff": n_eff, "design_effect": D(len(pairs)) / n_eff}

def _w_reference(pairs, kind):
    f = [(float(x), float(w)) for x, w in pairs]
    sw = sum(w for _, w in f); sw2 = sum(w * w for _, w in f); mean = sum(w * x for x, w in f) / sw
    ss = sum(w * (x - mean) ** 2 for x, w in f); denom = sw - sw2 / sw if kind == "reliability" else sw - 1
    n_eff = sw * sw / sw2
    return {"weighted_mean": mean, "weighted_sd": math.sqrt(ss / denom), "sum_weights": sw, "n_eff": n_eff, "design_effect": len(f) / n_eff}

def _w_impl(inp):
    pairs, miss = _w_pairs(inp)
    if len(pairs) < 2: raise DataError("at least two valid weighted observations are needed")
    if any(w <= 0 for _, w in pairs): raise DataError("every weight must be positive")
    kind = inp.get("weight_kind", "reliability")
    if kind not in _WEIGHT_KINDS: raise DataError("weight_kind must be one of: " + ", ".join(_WEIGHT_KINDS))
    st = _w_stats(pairs, kind)
    out = {"n": D(len(pairs)), "n_missing": D(miss), "sum_weights": _fd(st["sum_weights"]), "weighted_mean": st["weighted_mean"],
           "weighted_sd": st["weighted_sd"], "n_eff": _fd(st["n_eff"]), "design_effect": _fd(st["design_effect"])}
    appendix = {"weight_kind": kind,
                "definitions": {"weighted_mean": "sum(w*x) / sum(w)",
                                "reliability_sd": "sqrt( sum(w*(x-mean)^2) / (sum(w) - sum(w^2)/sum(w)) )  [unbiased under reliability weights]",
                                "frequency_sd": "sqrt( sum(w*(x-mean)^2) / (sum(w) - 1) )  [frequency weights count observations]",
                                "n_eff": "sum(w)^2 / sum(w^2)  [effective sample size]", "design_effect": "n / n_eff"},
                "inference": "None is provided. No standard error, confidence interval or test is computed, because that needs a declared complex design (stratification, clustering, replicate weights)."}
    return {**out, "_appendix": appendix, "_checks": _w_checks(inp, pairs, out)}

def _w_checks(inp, pairs, out):
    kind = inp.get("weight_kind", "reliability")
    ref = _w_reference(pairs, kind)
    vals = [x for x, _ in pairs]; mn = min(vals); spread = len(set(vals)) > 1
    eq = _w_stats([(x, D(1)) for x, _ in pairs], "reliability")
    scaled = _w_stats([(x, w * 3) for x, w in pairs], kind)
    heavier = _w_stats([(x, w * (D(1) + (x - mn) ** 2)) for x, w in pairs], kind)
    ordinary = describe_impl({"values": [str(x) for x in vals], "missing_codes": []})
    return [
        ("second_implementation_agrees", all(_close(out[k], ref[k]) for k in ref), "float route agrees with the Decimal route"),
        ("equal_weights_reproduce_the_unweighted_summary", _close(eq["weighted_mean"], ordinary["mean"]) and _close(eq["weighted_sd"], ordinary["sd"]), "unit weights are the ordinary sample summary"),
        ("mean_is_invariant_to_weight_scaling", _close(scaled["weighted_mean"], out["weighted_mean"]), "multiplying every weight by a constant leaves the mean unchanged"),
        ("larger_values_weighted_more_raise_the_mean", heavier["weighted_mean"] > out["weighted_mean"] if spread else True, "extra weight on values farther above the minimum moves the mean upward"),
        ("design_effect_is_one_for_equal_weights", _close(eq["design_effect"], D(1)), "equal weights give an effective sample size equal to n"),
    ]

def _w_tests(inp, impl): return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def _w_profile(inp):
    try:
        vals, wts = inp["values"], inp["weights"]
        if len(vals) != len(wts): return ["'weights' must have one entry per value (missing values included)"]
        pairs, _miss = _w_pairs(inp)
        if len(pairs) < 2: return ["at least two valid weighted observations are needed"]
        if any(w <= 0 for _, w in pairs): return ["every weight must be positive; zero or negative weights are refused"]
        if inp.get("weight_kind", "reliability") not in _WEIGHT_KINDS: return ["weight_kind must be one of: " + ", ".join(_WEIGHT_KINDS)]
        return []
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return ["weighted-summary inputs are malformed: values and weights must be lists of numbers of the same length"]

def _w_typing(metric):
    if metric in ("n", "n_missing"): return ("count", 0)
    if metric in ("sum_weights", "n_eff", "design_effect"): return ("ratio", 4)
    return ("@unit", 2)

def _w_caveats(out, thresholds):
    return ["The weight kind is declared: reliability weights treat the weights as precision-style weights (unbiased variance), frequency weights treat them as counts of observations. The two give different standard deviations.",
            "Weights are not validated: a design weight recorded incorrectly is used as given, and unequal weights reduce the effective sample size (the reported design effect shows by how much)."]

def _w_template(outputs, period, thresholds=None):
    P = period; tok = lambda k: "{{ref:%s:%s:%s}}" % (k, k, P)
    return ("The weighted mean is " + tok("weighted_mean") + " with a weighted standard deviation of " + tok("weighted_sd") + ", over " + tok("n") + " observations with a total weight of " + tok("sum_weights") + ". "
            "The effective sample size is " + tok("n_eff") + ", so the design effect is " + tok("design_effect") + ". "
            "No standard error or test is reported: that needs a declared complex design, which this method does not assume.")

# ---------- Declarative management accounts: an engagement spec run through the ledger kernel (Stage 8, manual 9.1-9.3; T2) ----------
def accounts_impl(inp):
    from . import accounts
    return accounts.build(inp["spec"])

def accounts_tests(inp, impl):
    return [(n, ok) for n, ok, _ in impl(inp)["_checks"]]

def accounts_profile(inp):
    from . import accounts
    try:
        accounts.build(inp["spec"])
        return []
    except ValueError as e:
        return [f"the engagement does not build: {e}"]

def accounts_mapping(inp):
    from . import accounts
    return accounts.account_mapping(inp["spec"])

def accounts_typing(metric):
    if metric.startswith("n_") or metric in ("checks_passed", "checks_total", "checks_na"): return "count", 0
    return "currency", 2

def accounts_caveats(out, th):
    return ["These are management accounts, not GAAP or IFRS statements and not assurance; this is custom analysis (T2), expert review pending.",
            "The ledger engine and the cash-flow classification rules are provisional pending the manual's account-mapping checkpoint and the Beancount comparison (B-032).",
            "Flags mark judgment items for a human; the checks guard arithmetic and balance, not business substance."]

def accounts_template(out, P, th):
    tok = lambda m: "{{ref:%s:%s:%s}}" % (m, m, P)
    return (f"The engagement posts {tok('n_entries')} entries. Net income is {tok('net_income')}; total assets are {tok('total_assets')} against liabilities of {tok('total_liabilities')} and equity of {tok('total_equity')}. "
            f"Closing retained earnings are {tok('retained_earnings_closing')}. The cash flow statement shows a net change in cash of {tok('cash_net')} and its two routes agree. "
            f"{tok('checks_passed')} of {tok('checks_total')} checks passed ({tok('checks_na')} not applicable), with {tok('n_flags')} item(s) flagged for human review. "
            "Any reconciliation supplied for the engagement is listed in the appendix with its in-transit and unrecorded items. "
            "Any declared policy change is listed in the appendix with its prospective treatment.")

_ACC_INPUTS = {"spec": {"type": "engagement_spec", "desc": "the declarative engagement: period, currency, framework, places, chart, prior_closing, opening, entries, schedules"}}
_ACC_DEFAULTS = (
    {"question": "Reporting framework", "default_chosen": "A required input with no default (manual D-010).", "impact": "Standards differ by framework; none is asserted."},
    {"question": "Closing", "default_chosen": "Every engagement closes: income, expenses and declared dividends move into retained earnings.", "impact": "Post-closing statements carry the period result in retained earnings."},
    {"question": "Prior closing balances", "default_chosen": "A required input (an empty object for a first period); the opening entry is checked against it.", "impact": "A mismatch fails the opening-balances check."})
_ACC_ASSUME = ("Every entry is balanced and inside the period (enforced by the kernel).", "The chart reflects the owner's account mapping.", "Amounts respect the declared currency places.")
_ACC_LIM = ("Management accounts only: not GAAP or IFRS statements and not assurance (manual 9.5).", "Cash-flow activity classification is a declared heuristic unless accounts carry explicit activity tags.", "Custom analysis (T2); expert review pending.", "The ledger engine decision (custom kernel vs Beancount) is still open (B-032).")

LIBRARY = {
    "npv": Method("npv", "T1", npv, npv_tests, npv_profile, "npv", "currency", lambda v: v > 0,
                  ("second_implementation_agrees", "boundary_zero_rate_equals_sum", "t0_cash_flow_shifts_npv_one_for_one"),
                  category="capital budgeting", intended_use="Value a stream of cash flows at a user-supplied discount rate.",
                  unsupported_use="Choosing the discount rate; ranking mutually exclusive projects of unequal scale or life; unequal period lengths.",
                  input_schema={"rate": {"type": "decimal", "desc": "discount rate per period, e.g. 0.10"},
                                "cashflows": {"type": "decimal_list", "min_items": 2, "desc": "cash flows, first at t=0"}},
                  defaults=({"question": "Timing and rate convention", "default_chosen": "Cash flows occur at period end; the first cash flow is at t=0 and is undiscounted; the rate is taken as given.", "impact": "Changes NPV if cash flows are mid-period or the rate is not the right hurdle."},),
                  assumptions=("Cash flows are certain given the inputs.",), limitations=("Single constant discount rate.",)),
    "breakeven": Method("breakeven", "T1", breakeven, breakeven_tests, breakeven_profile, "breakeven_units", "units", None,
                  ("profit_at_breakeven_is_zero", "monotone_in_fixed_cost", "positive_quantity"),
                  category="cost-volume-profit", intended_use="Units needed to cover fixed cost at a constant unit contribution.",
                  unsupported_use="Multi-product mix; step-fixed costs; non-linear price or cost.",
                  input_schema={k: {"type": "decimal", "desc": d} for k, d in (("fixed", "total fixed cost"), ("price", "price per unit"), ("variable", "variable cost per unit"))},
                  defaults=({"question": "Cost behavior", "default_chosen": "Fixed cost is constant and unit price and variable cost are constant.", "impact": "Break-even moves if costs are stepped or prices change with volume."},),
                  assumptions=("Linear cost and revenue.",), limitations=("Single product.",)),
    "pearson": Method("pearson", "T1", pearson_impl, pearson_tests, corr_profile, "r", "correlation", None,
                  ("second_implementation_agrees", "invariant_to_positive_linear_transform", "negating_y_flips_sign_keeps_p", "symmetric_in_x_and_y", "bounded_and_consistent", "missing_pairs_excluded_not_valued"),
                  category="correlation", intended_use="Linear association between two numeric variables in a sample, with interval, p-value and effect size.",
                  unsupported_use="Causal claims; non-linear relationships; clustered, weighted or repeated-measures data; more than two variables.",
                  input_schema=_CORR_INPUTS, defaults=_CORR_DEFAULTS + ({"question": "Assumption screen and fallback", "default_chosen": "If skewness or excess kurtosis of either variable exceeds the declared limits, switch to Spearman as a logged amendment.", "impact": "Spearman is robust to outliers and skew but measures monotone, not linear, association."},),
                  assumptions=("Pairs are independent observations.", "Relationship is approximately linear.", "Approximate normality, screened by skewness and kurtosis only."),
                  limitations=("Normality screen limits (2 and 7) are conventional placeholders [UNVERIFIED].", "Linearity and independence are not tested.", "Interval uses the Fisher z approximation."),
                  default_period="cross_section", caveats=corr_caveats, template=corr_template, claim_ceiling="associational",
                  assumption_checks=normality_screen, assumption_check_names=("normality_screen",), fallbacks={"normality_screen": "spearman"},
                  default_thresholds=_CORR_THRESH, output_units=_CORR_UNITS, output_precision={"n_pairs": 0, "n_excluded": 0, "r": 3, "r_squared": 3, "ci_lower": 3, "ci_upper": 3, "p_value": 4}),
    "spearman": Method("spearman", "T1", spearman_impl, spearman_tests, corr_profile, "rho", "correlation", None,
                  ("second_implementation_agrees", "invariant_to_monotone_transform", "negating_y_flips_sign_keeps_p", "symmetric_in_x_and_y", "bounded_and_consistent", "missing_pairs_excluded_not_valued"),
                  category="correlation", intended_use="Monotone association between two variables, robust to outliers and skew; fallback for Pearson.",
                  unsupported_use="Causal claims; clustered or repeated-measures data; exact small-sample p-values.",
                  input_schema=_CORR_INPUTS, defaults=_CORR_DEFAULTS + ({"question": "Ties", "default_chosen": "Tied values receive average ranks.", "impact": "Other tie rules change rho slightly."},),
                  assumptions=("Pairs are independent observations.", "Relationship is monotone."),
                  limitations=("Interval uses the Bonett-Wright standard error [UNVERIFIED] and the p-value uses a t approximation; both are approximate.",),
                  default_period="cross_section", caveats=corr_caveats, template=corr_template, claim_ceiling="associational",
                  default_thresholds=_CORR_THRESH, output_units=_CORR_UNITS, output_precision={"n_pairs": 0, "n_excluded": 0, "rho": 3, "ci_lower": 3, "ci_upper": 3, "p_value": 4}),
    "ols": Method("ols", "T1", ols_impl, ols_tests, ols_profile, "r_squared", "ratio", None,
                  ("second_implementation_agrees", "shift_changes_intercept_only", "scaling_rescales_coefficients_not_significance", "row_order_invariant", "incomplete_rows_excluded_not_valued", "bounded_and_consistent", "cross_check_partial_regression_and_pearson"),
                  category="regression", intended_use="Linear association of one numeric outcome with up to five numeric predictors, with intervals, p-values and effect sizes.",
                  unsupported_use="Causal claims; categorical predictors; interactions; non-linear fits; clustered, weighted or time-series data; prediction beyond the observed range.",
                  input_schema=_OLS_INPUTS, defaults=_OLS_DEFAULTS, assumptions=_OLS_ASSUME, limitations=_OLS_LIM, default_period="cross_section",
                  caveats=lambda o, t: ols_caveats(o, t, False), template=ols_template, claim_ceiling="associational",
                  assumption_checks=ols_checks, assumption_check_names=("residual_normality_screen", "heteroskedasticity_screen", "multicollinearity_screen", "influence_screen"),
                  fallbacks={"heteroskedasticity_screen": "ols_robust"}, default_thresholds=_OLS_THRESH, typing=ols_typing),
    "ols_robust": Method("ols_robust", "T1", ols_robust_impl, ols_robust_tests, ols_profile, "r_squared", "ratio", None,
                  ("second_implementation_agrees", "shift_changes_intercept_only", "scaling_rescales_coefficients_not_significance", "row_order_invariant", "incomplete_rows_excluded_not_valued", "bounded_and_consistent", "cross_check_partial_regression_and_pearson"),
                  category="regression", intended_use="Linear regression with HC3 heteroskedasticity-robust standard errors; fallback for OLS.",
                  unsupported_use="As OLS: causal claims, categorical predictors, clustered or time-series data. No overall F test is reported.",
                  input_schema=_OLS_INPUTS, defaults=_OLS_DEFAULTS, assumptions=_OLS_ASSUME[:2], limitations=_OLS_LIM + ("HC3 intervals use t critical values, an approximation in small samples.",),
                  default_period="cross_section", caveats=lambda o, t: ols_caveats(o, t, True), template=ols_template, claim_ceiling="associational",
                  assumption_checks=ols_robust_checks, assumption_check_names=("residual_normality_screen", "multicollinearity_screen", "influence_screen"),
                  default_thresholds=_OLS_THRESH, typing=ols_typing),
    "welch_t": Method("welch_t", "T1", welch_impl, _welch_tests, groups_profile, "diff", "from_request", None,
                  ("second_implementation_agrees", "shift_leaves_difference_inference_unchanged", "positive_scale_equivariance", "swapping_groups_negates_difference_keeps_p", "row_order_invariant", "missing_entries_excluded_not_valued", "bounded_and_consistent"),
                  category="group comparison", intended_use="Compare the means of two independent groups on a numeric outcome, with interval, p-value and standardized effect size.",
                  unsupported_use="Paired or repeated measures; more than two groups; causal claims; clustered data; proportions or counts.",
                  input_schema=_GRP_INPUTS, defaults=_GRP_DEFAULTS, assumptions=("Observations are independent within and between groups.", "Group means are approximately normal (screened by skewness and kurtosis only)."),
                  limitations=("Normality screen limits are conventions [UNVERIFIED].", "Hedges g interval is a large-sample approximation.", "Independence is not tested."),
                  default_period="cross_section", caveats=groups_caveats, template=welch_template, claim_ceiling="associational",
                  assumption_checks=groups_normality, assumption_check_names=("group_normality_screen",), fallbacks={"group_normality_screen": "mann_whitney"},
                  default_thresholds=_GRP_THRESH, typing=groups_typing),
    "mann_whitney": Method("mann_whitney", "T1", mwu_impl, _mwu_tests, groups_profile, "hl_shift", "from_request", None,
                  ("second_implementation_agrees", "interval_is_test_inversion", "monotone_transform_keeps_rank_statistics", "swapping_groups_flips_effect_keeps_p", "shift_and_scale_behave", "row_order_invariant", "missing_entries_excluded_not_valued", "identical_samples_give_no_effect", "bounded_and_consistent"),
                  category="group comparison", intended_use="Compare two independent groups without assuming normality; fallback for Welch.",
                  unsupported_use="Paired data; causal claims; very small groups (an interval needs roughly four or more per group); exact small-sample p-values.",
                  input_schema=_GRP_INPUTS, defaults=_GRP_DEFAULTS[:1] + _GRP_DEFAULTS[3:4] + ({"question": "Ties and interval", "default_chosen": "Asymptotic p-value with tie and continuity corrections; the Hodges-Lehmann interval comes from inverting that test.", "impact": "Exact methods differ in small samples."},),
                  assumptions=("Observations are independent.", "The two distributions have a similar shape if the shift is read as a median difference."),
                  limitations=("Normal approximation; the interval method is [UNVERIFIED] against a published reference.", "No interval for the rank-biserial correlation.", "Groups need roughly four or more observations each for an interval."),
                  default_period="cross_section", caveats=groups_caveats, template=mwu_template, claim_ceiling="associational",
                  default_thresholds=_GRP_THRESH, typing=groups_typing),
    "descriptive_stats": Method("descriptive_stats", "T1", describe_impl, describe_tests, describe_profile, "mean", "from_request", None,
                  ("second_implementation_agrees", "shift_moves_location_not_spread", "scale_scales_spread", "permutation_invariant",
                   "missing_entries_excluded_not_valued", "order_statistics_bounded"),
                  category="descriptive statistics", intended_use="Summarize one numeric variable in a dataset (n, missing, mean, median, range, sample SD).",
                  unsupported_use="Inference (intervals, tests, effect sizes), weighted or clustered survey data, grouped summaries, quartiles.",
                  input_schema={"values": {"type": "value_list", "min_items": 1, "desc": "the observations; blank or null counts as missing"},
                                "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; never read as values"}},
                  defaults=({"question": "Missing-value handling", "default_chosen": "Blank, null and user-defined missing codes are excluded from every statistic (listwise for one variable) and counted.", "impact": "Including codes as values would distort every statistic."},
                            {"question": "Median and spread definitions", "default_chosen": "Median averages the two middle values for even n; variance and SD use n-1 (sample).", "impact": "Population SD (n) is smaller; packages differ on quartile definitions, which are not reported."},
                            {"question": "Small-sample threshold", "default_chosen": "Fewer than 30 valid observations triggers cautionary wording [PROVISIONAL].", "impact": "Changes only the wording, not the numbers."}),
                  assumptions=("Observations are numeric and the listed codes fully identify missing values.",),
                  limitations=("Descriptive claims only; no inference.", "Float reference comparison tolerance is 1e-9 relative."),
                  output_precision={"n": 0, "n_missing": 0}, default_period="cross_section",
                  caveats=describe_caveats, template=describe_template, default_thresholds={"small_sample_n": "30"}),
    "anova": Method("anova", "T1", anova_impl, _anova_tests, anova_profile, "eta_squared", "from_request", None,
                  ("second_implementation_agrees", "within_group_permutation_invariant", "group_relabeling_invariant", "equal_shift_leaves_F_and_effect_unchanged", "positive_scale_equivariance", "missing_entries_excluded_not_valued", "bounded_and_consistent"),
                  category="group comparison", intended_use="Compare the means of three or more independent groups with an omnibus F test, an eta-squared effect size and per-group summaries.",
                  unsupported_use="Repeated measures; two-way or factorial designs; post-hoc pairwise tests; causal claims; fewer than three groups.",
                  input_schema=_ANOVA_INPUTS, defaults=_ANOVA_DEFAULTS, assumptions=_ANOVA_ASSUME, limitations=_ANOVA_LIM, default_period="cross_section",
                  caveats=anova_caveats, template=anova_template, claim_ceiling="associational",
                  assumption_checks=anova_checks, assumption_check_names=("group_normality_screen", "homogeneity_of_variance_screen"),
                  fallbacks={"group_normality_screen": "kruskal_wallis", "homogeneity_of_variance_screen": "kruskal_wallis"}, default_thresholds=_ANOVA_THRESH, typing=anova_typing),
    "kruskal_wallis": Method("kruskal_wallis", "T1", kw_impl, _kw_tests, kw_profile, "epsilon_squared", "from_request", None,
                  ("second_implementation_agrees", "monotone_transform_keeps_ranks", "shift_invariant", "group_relabeling_invariant", "within_group_permutation_invariant", "missing_entries_excluded_not_valued", "bounded_and_consistent"),
                  category="group comparison", intended_use="Compare three or more independent groups without assuming normality; nonparametric fallback for one-way ANOVA.",
                  unsupported_use="Repeated measures; causal claims; post-hoc pairwise tests; reading the result as a mean difference.",
                  input_schema=_ANOVA_INPUTS, defaults=_KW_DEFAULTS, assumptions=_KW_ASSUME, limitations=_KW_LIM, default_period="cross_section",
                  caveats=kw_caveats, template=kw_template, claim_ceiling="associational", default_thresholds=_KW_THRESH, typing=kw_typing),
    "chi_square": Method("chi_square", "T1", chi_square_impl, _chi2_tests, chi2_profile, "cramers_v", "ratio", None,
                  ("second_implementation_agrees", "row_order_invariant", "transpose_invariant", "uniform_scaling_scales_chi2_keeps_V", "independence_gives_zero_chi2", "bounded_and_consistent"),
                  category="categorical association", intended_use="Test whether two categorical variables are independent from a table of observed counts, with a Cramer's V effect size.",
                  unsupported_use="Goodness of fit; ordered categories; repeated or paired counts; causal claims; tables with small expected counts (blocks).",
                  input_schema=_CHI2_INPUTS, defaults=_CHI2_DEFAULTS, assumptions=_CHI2_ASSUME, limitations=_CHI2_LIM, default_period="cross_section",
                  caveats=chi2_caveats, template=chi2_template, claim_ceiling="associational",
                  assumption_checks=chi2_checks, assumption_check_names=("minimum_expected_count",), default_thresholds=_CHI2_THRESH, typing=chi2_typing),
    "trend_forecast": Method("trend_forecast", "T1", forecast_impl, _forecast_tests, forecast_profile, "forecast_1", "from_request", None,
                  ("second_implementation_agrees", "out_of_sample_check_agrees", "shift_moves_intercept_and_forecasts_not_slope", "positive_scale_equivariance", "bounded_and_consistent"),
                  category="forecasting", intended_use="Project a linear trend in a single time series forward for a user-chosen horizon, with prediction intervals and a disclosed out-of-sample error on the recent past.",
                  unsupported_use="Seasonal, cyclical or structural-break series; causal claims; multi-series or driver-based models; long horizons; policy simulations.",
                  input_schema=_FORECAST_INPUTS, defaults=_FORECAST_DEFAULTS, assumptions=_FORECAST_ASSUME, limitations=_FORECAST_LIM, default_period="annual",
                  caveats=forecast_caveats, template=forecast_template, claim_ceiling="predictive", default_thresholds=_FORECAST_THRESH, typing=forecast_typing),
    "ratio_analysis": Method("ratio_analysis", "T1", ratio_impl, _ratio_tests, ratio_profile, "n_computed", "count", None,
                  ("every_ratio_is_either_computed_or_explained", "denominators_are_nonzero", "negative_denominators_are_flagged_not_dropped",
                   "second_route_agrees_on_every_ratio", "balance_sheet_identity_holds_when_checkable", "figures_parsed_exactly_as_supplied"),
                  category="financial statement analysis",
                  intended_use="Compute liquidity, profitability, solvency and efficiency ratios from figures on your own financial statements, showing each ratio's declared formula and the figures it used.",
                  unsupported_use="Benchmarks, industry averages or pass/fail judgements; GAAP or IFRS presentation; restating or adjusting figures; multi-period comparatives; segment, consolidated or multi-currency analysis; forecasting.",
                  input_schema={k: {"type": "decimal", "required": False, "desc": v} for k, v in _RATIO_FIGURES.items()},
                  defaults=({"question": "Benchmarks and cut-offs", "default_chosen": "None are applied, because none is supplied or verified. Ratios are computed, not rated.", "impact": "Whether a value is good or bad is left to the reader and the context."},
                            {"question": "Balance conventions", "default_chosen": "Period-end balances and a 365-day year for the efficiency ratios.", "impact": "Average balances or a 360-day year would give different numbers."},
                            {"question": "Uncomputable ratios", "default_chosen": "A ratio with a missing figure or a zero denominator is listed in the appendix with its reason and is not estimated.", "impact": "The pack is partial rather than invented."}),
                  assumptions=("The figures are as reported for one period, in one currency and on one accounting basis.", "Balance-sheet figures are period-end balances."),
                  limitations=("Descriptive arithmetic only; no benchmark, threshold or verdict is applied because none is supplied or verified.", "The figures are not validated against a trial balance here; use the management-accounts method for a bookkeeping-level check.", "There is no tax computation; net income is used exactly as supplied."),
                  default_period="annual", caveats=ratio_caveats, template=ratio_template, claim_ceiling="descriptive", typing=_ratio_typing),
    "multiple_comparison": Method("multiple_comparison", "T1", _mc_impl, _mc_tests, _mc_profile, "n_rejected", "count", None,
                  ("adjusted_p_values_are_at_least_the_raw_ones", "adjusted_p_values_are_bounded_in_zero_one", "declared_correction_matches_its_definition",
                   "second_implementation_agrees", "correction_is_order_invariant"),
                  category="inference control",
                  intended_use="Adjust a pre-declared family of p-values for multiple testing with Holm's step-down or Bonferroni, and count how many remain significant at a declared alpha.",
                  unsupported_use="Deciding what the family is; choosing the hypothesis set after seeing results; modelling dependence between tests; rescuing a study whose assumptions or design are flawed.",
                  input_schema={"p_values": {"type": "value_list", "min_items": 2, "desc": "the raw p-values of one declared family"},
                                "method": {"type": "enum", "values": ["holm", "bonferroni"], "desc": "holm (step-down, uniformly more powerful) or bonferroni"},
                                "alpha": {"type": "decimal", "required": False, "desc": "family-wise level, default 0.05"}},
                  defaults=({"question": "Correction method", "default_chosen": "The user declares Holm or Bonferroni; both control the family-wise error rate under arbitrary dependence, and Holm is never less powerful than Bonferroni.", "impact": "Other corrections (Benjamini-Hochberg false-discovery control, resampling) are not implemented."},
                            {"question": "Family definition", "default_chosen": "The p-values supplied are treated as one family, as declared by the user; the system does not infer the family.", "impact": "Splitting or merging families changes the adjusted values."}),
                  assumptions=("Each test is individually valid (its own assumptions hold).", "The family was declared before the results were seen.", "The p-values are the raw p-values of that family, not already adjusted."),
                  limitations=("Holm and Bonferroni only; no false-discovery-rate control and no dependence modelling.", "The correction does not fix a biased sample, a violated assumption or a family chosen after the fact."),
                  default_period="cross_section", caveats=_mc_caveats, template=_mc_template, claim_ceiling="descriptive", typing=_mc_typing),
    "power_analysis": Method("power_analysis", "T1", _power_impl, _power_tests, _power_profile, "power", "probability", None,
                  ("second_implementation_agrees", "power_at_zero_effect_equals_alpha", "power_increases_with_effect_size", "power_increases_with_sample_size", "mde_decreases_with_sample_size"),
                  category="study design",
                  intended_use="Plan a two-sample or one-sample comparison of means: the power for a stated effect, and the minimum detectable effect at a declared target power, under the normal approximation.",
                  unsupported_use="Exact power under the noncentral t distribution; proportions or counts; cluster, weighted or repeated-measures designs; multiplicity; treating a high power as a guarantee of significance.",
                  input_schema={"design": {"type": "enum", "values": ["two_sample", "one_sample"], "desc": "two_sample compares two means; one_sample tests a single mean"},
                                "effect": {"type": "decimal", "desc": "the difference (or mean) to detect, in the units of the outcome"},
                                "n1": {"type": "decimal", "desc": "sample size of group 1 (or the single sample for one_sample)"},
                                "n2": {"type": "decimal", "required": False, "desc": "sample size of group 2 (two_sample only)"},
                                "sd1": {"type": "decimal", "desc": "standard deviation of group 1 (or the single sample)"},
                                "sd2": {"type": "decimal", "required": False, "desc": "standard deviation of group 2 (two_sample only)"},
                                "alpha": {"type": "decimal", "required": False, "desc": "significance level, default 0.05"},
                                "tails": {"type": "enum", "values": ["two_sided", "one_sided"], "required": False, "desc": "two_sided (default) or one_sided"},
                                "target_power": {"type": "decimal", "required": False, "desc": "power used to compute the minimum detectable effect, default 0.8"}},
                  defaults=({"question": "Underlying distribution", "default_chosen": "The normal approximation. It is exact when the standard deviations are known or planned; with sds estimated from a pilot, exact power uses the noncentral t distribution.", "impact": "Exact power is somewhat lower than the normal approximation when sds are estimated."},
                            {"question": "Multiplicity", "default_chosen": "A single comparison is assumed; the correction does not account for several planned tests.", "impact": "A family of tests needs a smaller per-test alpha (see multiple_comparison)."}),
                  assumptions=("Observations are independent within and between groups.", "The standard deviations supplied are the planning values and are positive.", "A single test at the declared alpha, with the declared number of tails."),
                  limitations=("Normal approximation; no noncentral t exactness.", "No clustering, weights or repeated measures.", "Power describes the design, not the study's actual outcome."),
                  default_period="cross_section", caveats=_power_caveats, template=_power_template, claim_ceiling="descriptive", typing=_power_typing),
    "missing_data_bounds": Method("missing_data_bounds", "T1", _md_impl, _md_tests, _md_profile, "pct_missing", "probability", None,
                  ("bounds_bracket_the_observed_mean", "bounds_are_the_extreme_cases", "bounds_widen_with_more_missing_values",
                   "percentage_is_missing_over_total", "no_missing_values_means_a_zero_width_bound"),
                  category="data quality",
                  intended_use="Report how much of a variable is missing and bound the complete-data mean under the worst case: every missing value at the observed minimum or maximum, with the missing-data mechanism recorded as the owner's declaration.",
                  unsupported_use="Imputation; MAR/MCAR/MNAR modelling; bounds for statistics other than the mean; treating a declared mechanism as verified.",
                  input_schema={"values": {"type": "value_list", "min_items": 1, "desc": "the observations; blank or null counts as missing"},
                                "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; never read as values"},
                                "mechanism": {"type": "enum", "values": ["unknown", "mcar", "mar", "mnar"], "required": False, "desc": "the mechanism you declare (recorded, not verified); default unknown"}},
                  defaults=({"question": "How missingness is handled", "default_chosen": "Extreme-case bounds: no imputation, and every missing value is placed at the observed minimum (lower bound) or maximum (upper bound).", "impact": "Bounds are honest but can be wide; imputation would be narrower and would assume a mechanism."},
                            {"question": "Declared mechanism", "default_chosen": "The mechanism you declare is recorded with a note that the system cannot verify it from the data.", "impact": "A declared mechanism does not change the bounds; only the wording and the reader's interpretation."}),
                  assumptions=("The observed values are correct and the declared missing codes fully identify missing entries.", "Missing values lie somewhere between the observed minimum and maximum."),
                  limitations=("Bounds cover the mean only; they are not estimates and imply no probabilistic mechanism.", "No imputation, no MAR/MCAR/MNAR model and no verification of the declared mechanism.", "With many missing values the bounds can be so wide as to be uninformative, which is the honest answer."),
                  default_period="cross_section", caveats=_md_caveats, template=_md_template, claim_ceiling="descriptive", typing=_md_typing),
    "paired_t": Method("paired_t", "T1", paired_impl, _paired_tests, _paired_profile, "mean_diff", "from_request", None,
                  ("second_implementation_agrees", "swapping_the_paired_columns_negates_the_difference_keeps_p", "shift_and_scale_behave",
                   "row_order_invariant", "missing_pairs_are_excluded_not_imputed"),
                  category="group comparison",
                  intended_use="Compare two matched measurements on the same observations (for example before and after) using the mean within-pair difference, with a confidence interval, a paired t test and Cohen's dz.",
                  unsupported_use="Independent groups; more than two measurements; a causal claim about what produced the change; non-normal differences (no signed-rank fallback).",
                  input_schema=_PAIRED_INPUTS, defaults=_PAIRED_DEFAULTS, assumptions=_PAIRED_ASSUME, limitations=_PAIRED_LIM,
                  default_period="cross_section", caveats=_paired_caveats, template=_paired_template, claim_ceiling="associational",
                  default_thresholds={"small_sample_n": "30"}, typing=_paired_typing),
    "one_sample_t": Method("one_sample_t", "T1", one_sample_impl, _one_tests, _one_profile, "mean", "from_request", None,
                  ("second_implementation_agrees", "shift_invariance", "positive_scale_equivariance", "row_order_invariant", "missing_entries_are_excluded_not_valued"),
                  category="group comparison",
                  intended_use="Compare one sample mean with a declared reference value, with a confidence interval, a one-sample t test and Cohen's d.",
                  unsupported_use="Comparing two samples; one-sided tests; trimmed means or medians; causal claims; clustered or weighted data.",
                  input_schema=_ONE_INPUTS, defaults=_ONE_DEFAULTS, assumptions=_ONE_ASSUME, limitations=_ONE_LIM,
                  default_period="cross_section", caveats=_one_caveats, template=_one_template, claim_ceiling="associational",
                  default_thresholds={"small_sample_n": "30"}, typing=_one_typing),
    "cost_benefit": Method("cost_benefit", "T2", cba_impl, cba_tests, cba_profile, "net_present_value", "currency", None,
                  ("second_implementation_agrees", "net_value_is_present_value_of_benefits_minus_costs", "zero_discount_rate_gives_undiscounted_sums",
                   "scaling_the_benefits_scales_the_benefit_side", "a_higher_discount_rate_lowers_the_present_value"),
                  category="appraisal",
                  intended_use="Discounted cost-benefit appraisal: present values of declared costs and benefits, the net present value and the benefit-cost ratio.",
                  unsupported_use="Monetising non-monetised effects; choosing the discount rate; tax, financing or risk adjustment; probability distributions or Monte Carlo; distributive weighting.",
                  input_schema={"costs": {"type": "value_list", "min_items": 1, "desc": "cost per period, starting at period 1"},
                                "benefits": {"type": "value_list", "min_items": 1, "desc": "benefit per period, same length as costs"},
                                "discount_rate": {"type": "decimal", "required": False, "desc": "periodic discount rate, default 0"}},
                  defaults=({"question": "Discounting", "default_chosen": "Costs and benefits are end-of-period from period 1 and discounted at the declared rate (default 0).", "impact": "A different rate or timing changes the net value and can change its sign."},
                            {"question": "What counts as a benefit", "default_chosen": "Only the monetised benefits the owner declared; no unmonetised effect is valued by the system.", "impact": "Omitting an effect understates the appraisal; valuing it is the owner's judgement."}),
                  assumptions=("Costs and benefits are the owner's declared values on one basis.", "The declared rate is the appropriate social or financial discount rate."),
                  limitations=("No monetisation of non-monetised effects, no risk adjustment and no distributional analysis.", "One rate for all periods; no mid-period timing.", "No tax or financing effects."),
                  default_period="annual", caveats=cba_caveats, template=cba_template, claim_ceiling="descriptive", typing=_cba_typing),
    "cost_effectiveness": Method("cost_effectiveness", "T2", cea_impl, cea_tests, cea_profile, "n_options", "count", None,
                  ("second_implementation_agrees", "icer_is_incremental_cost_over_incremental_effect", "comparator_is_the_first_option",
                   "cheaper_and_more_effective_is_flagged_dominant", "adding_a_third_option_adds_one_ratio_per_option"),
                  category="appraisal",
                  intended_use="Cost-effectiveness analysis against a declared comparator: incremental cost per unit of effect (ICER) for each other option, with dominance flags.",
                  unsupported_use="Comparing different outcome scales; weighting or aggregating several effects; probabilistic sensitivity analysis; deciding a willingness-to-pay threshold.",
                  input_schema={"options": {"type": "records", "min_items": 2, "fields": {"name": "text", "cost": "decimal", "effect": "decimal"},
                                            "desc": "the first option is the comparator; each other option is compared with it on cost and effect"}},
                  defaults=({"question": "Comparator", "default_chosen": "The first listed option is the comparator.", "impact": "A different comparator changes every incremental ratio."},
                            {"question": "Effect scale", "default_chosen": "All options state their effect on one declared scale.", "impact": "Mixing scales makes the ratios incomparable."}),
                  assumptions=("Costs and effects are declared on one basis and one outcome scale.", "The first option is the intended comparator."),
                  limitations=("One outcome scale only; no willingness-to-pay threshold and no sensitivity analysis.", "An option with the same effect as the comparator has an undefined ratio and blocks.", "Dominance is flagged, not ranked."),
                  default_period="annual", caveats=cea_caveats, template=cea_template, claim_ceiling="descriptive", typing=_cea_typing),
    "sroi": Method("sroi", "T2", sroi_impl, sroi_tests, sroi_profile, "sroi_ratio", "ratio", None,
                  ("second_implementation_agrees", "ratio_is_present_value_over_investment", "net_value_is_benefits_minus_investment",
                   "doubling_the_investment_halves_the_ratio", "zero_discount_rate_gives_undiscounted_benefits"),
                  category="appraisal",
                  intended_use="Social return on investment: present value of declared social benefits divided by the declared investment.",
                  unsupported_use="Estimating or verifying social benefits; additionality, deadweight, attribution or displacement adjustments; assurance; comparing across different outcome scales.",
                  input_schema={"investment": {"type": "decimal", "desc": "the investment amount"},
                                "benefits": {"type": "value_list", "min_items": 1, "desc": "monetised benefit per period, starting at period 1"},
                                "discount_rate": {"type": "decimal", "required": False, "desc": "periodic discount rate, default 0"}},
                  defaults=({"question": "Benefit valuation", "default_chosen": "The benefits are the owner's declared monetised values; the system does not value a social outcome.", "impact": "The ratio is only as good as those valuations."},
                            {"question": "Adjustments", "default_chosen": "No deadweight, attribution, displacement or drop-off adjustment is applied.", "impact": "Real SROI practice may require them; here they must be supplied already adjusted if wanted."}),
                  assumptions=("Benefits are declared values on one basis.", "The investment is a declared amount and the rate is the owner's choice."),
                  limitations=("No additionality/attribution adjustment and no assurance; the result is a declared-input ratio.", "One outcome aggregate only.", "Sensitivity to the valuation assumptions is not computed."),
                  default_period="annual", caveats=sroi_caveats, template=sroi_template, claim_ceiling="descriptive", typing=_sroi_typing),
    "unit_economics": Method("unit_economics", "T1", unit_econ_impl, unit_econ_tests, unit_econ_profile, "unit_margin", "currency", None,
                  ("second_implementation_agrees", "margin_is_price_minus_variable_cost", "payback_is_acquisition_cost_over_margin",
                   "raising_price_raises_margin_by_the_same_amount", "lower_churn_raises_ltv"),
                  category="unit economics",
                  intended_use="Unit contribution margin, payback of the acquisition cost and (when a churn rate is declared) a period-value LTV and LTV/CAC.",
                  unsupported_use="Estimating churn, retention curves or customer lifetime modelling; discounting LTV to present value; tax, financing or cross-sell; segment-level CAC.",
                  input_schema={"price": {"type": "decimal", "desc": "price per unit"},
                                "variable_cost": {"type": "decimal", "desc": "variable cost per unit"},
                                "acquisition_cost": {"type": "decimal", "desc": "cost to acquire one customer"},
                                "churn_rate": {"type": "decimal", "required": False, "desc": "period churn in (0,1); if supplied, LTV = unit margin / churn"}},
                  defaults=({"question": "LTV definition", "default_chosen": "LTV = unit margin / declared churn rate (period value, no discounting); omitted when no churn is declared.", "impact": "A different LTV convention (e.g. discounted, cohort-based) would give a different number."},
                            {"question": "Payback", "default_chosen": "Payback periods = acquisition cost / unit margin.", "impact": "It assumes the margin is earned every period at the same rate."}),
                  assumptions=("Prices, costs and churn are the owner's declared inputs.", "The unit margin is earned each period until churn."),
                  limitations=("No present-value discounting, retention curve, tax or financing.", "Churn is a single constant rate.", "Segment or product-level CAC is not modelled."),
                  default_period="annual", caveats=unit_econ_caveats, template=unit_econ_template, claim_ceiling="descriptive", typing=_unit_typing),
    "multi_product_breakeven": Method("multi_product_breakeven", "T1", multi_breakeven_impl, multi_breakeven_tests, multi_breakeven_profile, "breakeven_total_units", "units", None,
                  ("second_implementation_agrees", "weighted_contribution_is_the_mix_weighted_margin", "profit_at_break_even_is_zero",
                   "scaling_fixed_costs_scales_break_even_units", "per_product_units_sum_to_the_total"),
                  category="cost-volume-profit",
                  intended_use="Break-even in units and revenue for a fixed product mix: the mix-weighted contribution margin and the per-product break-even quantities.",
                  unsupported_use="A changing mix, step costs, capacity limits, price-volume relationships or tax; forecasting which mix will actually occur.",
                  input_schema={"fixed_costs": {"type": "decimal", "desc": "total fixed costs for the period"},
                                "products": {"type": "records", "min_items": 2, "fields": {"name": "text", "price": "decimal", "variable_cost": "decimal", "mix_units": "decimal"},
                                             "desc": "two or more products with a declared mix (mix_units are the relative quantities sold)"}},
                  defaults=({"question": "Mix assumption", "default_chosen": "The declared mix_units are held constant and used as the weighting.", "impact": "A different mix changes the weighted contribution and the break-even."},
                            {"question": "Cost behaviour", "default_chosen": "Fixed costs are constant and unit prices and variable costs are constant over the range.", "impact": "Step costs or volume discounts break the single break-even point."}),
                  assumptions=("Each product's price and variable cost are constant.", "The declared mix is the mix that will be sold.", "Fixed costs do not change with volume."),
                  limitations=("One break-even point for one declared mix; no capacity limits or step costs.", "No tax, financing or working-capital effects.", "Per-product units are a break-even mix, not a target."),
                  default_period="annual", caveats=multi_breakeven_caveats, template=multi_breakeven_template, claim_ceiling="descriptive", typing=_mb_typing),
    "two_way_anova": Method("two_way_anova", "T1", two_way_impl, two_way_tests, two_way_profile, "f_ab", "ratio", None,
                  ("second_implementation_agrees", "sums_of_squares_decompose_the_total", "f_equals_mean_square_over_mean_square_error",
                   "shifting_every_response_leaves_the_effects_unchanged", "scaling_every_response_scales_sums_of_squares_keeps_f"),
                  category="group comparison",
                  intended_use="Two-way balanced factorial ANOVA on one numeric response: the two main effects and their interaction, with F tests and partial eta-squared.",
                  unsupported_use="Unbalanced designs (refused, because the SS type would be a convention); more than two factors; repeated measures or ANCOVA; post-hoc comparisons (use posthoc_pairwise); causal claims.",
                  input_schema={"data": {"type": "records", "min_items": 8, "fields": {"response": "decimal", "factor_a": "text", "factor_b": "text"},
                                         "desc": "one record per observation: the numeric response and its two factor levels; every cell must have the same count"}},
                  defaults=({"question": "Design balance", "default_chosen": "Balanced only: every combination of the two factor levels must have the same number of observations.", "impact": "An unbalanced design is refused because type I/II/III sums of squares are different conventions and none is ratified."},
                            {"question": "Effect sizes", "default_chosen": "Partial eta-squared is reported for each effect.", "impact": "Other effect sizes (omega-squared, generalized eta-squared) are not implemented."}),
                  assumptions=("Observations are independent.", "The response is approximately normal within cells and the cell variances are similar (not tested).", "The design is balanced by construction."),
                  limitations=("Balanced two-way only; no three-way, repeated measures or ANCOVA.", "Assumption checks (normality, homoscedasticity) are not run for factorial designs.", "An interaction means simple effects differ; the omnibus test does not localise them."),
                  default_period="cross_section", caveats=two_way_caveats, template=two_way_template, claim_ceiling="associational",
                  default_thresholds={"small_sample_n": "30"}, typing=_two_typing),
    "posthoc_pairwise": Method("posthoc_pairwise", "T1", posthoc_impl, posthoc_tests, posthoc_profile, "n_rejected", "count", None,
                  ("second_implementation_agrees", "adjusted_p_is_never_below_the_raw_p", "correction_matches_its_definition",
                   "pair_count_is_choose_k_2", "reversing_group_order_keeps_the_evidence"),
                  category="group comparison",
                  intended_use="Compare every pair of independent groups with a Welch t-test and a declared family-wise correction (Holm, Bonferroni or none), reporting raw and adjusted p-values.",
                  unsupported_use="Paired or repeated designs; more than ten groups; causal claims; scanning all pairs to find the smallest p-value without declaring the family.",
                  input_schema={"groups": {"type": "column_map", "min_columns": 2, "max_columns": 10, "min_items": 2, "desc": "name -> observations; every unordered pair of groups is compared"},
                                "adjust": {"type": "enum", "values": ["holm", "bonferroni", "none"], "required": False, "desc": "family-wise correction, default holm"},
                                "alpha": {"type": "decimal", "required": False, "desc": "family-wise level, default 0.05"},
                                "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes; excluded within each group"}},
                  defaults=({"question": "Correction", "default_chosen": "Holm step-down by default; Bonferroni and uncorrected are available but must be declared.", "impact": "Holm is never less powerful than Bonferroni and still controls the family-wise error rate."},
                            {"question": "Pairwise test", "default_chosen": "Welch t-test for every pair (unequal variances assumed).", "impact": "A pooled-variance test would differ when group variances differ."}),
                  assumptions=("Groups are independent and each observation belongs to one group.", "Within-group observations are approximately normal (not tested)."),
                  limitations=("Welch pairwise only; no Dunnett, Tukey HSD or Games-Howell.", "Uncorrected p-values are available only when explicitly declared as 'none'.", "The family must be declared before the results are seen."),
                  default_period="cross_section", caveats=posthoc_caveats, template=posthoc_template, claim_ceiling="associational", typing=_posthoc_typing),
    "currency_convert": Method("currency_convert", "T1", currency_convert_impl, _cc_tests, _cc_profile, "amount", "currency", None,
                  ("second_implementation_agrees", "round_trip_at_the_inverse_rate_returns_the_original", "zero_amount_converts_to_zero",
                   "negative_amount_converts_with_the_same_magnitude", "scaling_the_amount_scales_the_result"),
                  category="currency",
                  intended_use="Convert an amount from one ISO 4217 currency to another at a rate the owner declares, recording the rate, its provenance, any source and date.",
                  unsupported_use="Retrieving or verifying exchange rates; interpolation, forward rates or triangulation; translating a set of statements; multi-currency consolidation; tax or fee conversion.",
                  input_schema={"amount": {"type": "decimal", "desc": "the amount in the source currency"},
                                "from_currency": {"type": "currency", "desc": "ISO 4217 code, e.g. USD"},
                                "to_currency": {"type": "currency", "desc": "ISO 4217 code, e.g. EUR, CNY, JPY"},
                                "rate": {"type": "decimal", "desc": "units of the target currency per one unit of the source currency (declared)"},
                                "rate_provenance": {"type": "enum", "values": ["user", "sourced", "assumption"], "required": False, "desc": "default user"},
                                "rate_source": {"type": "text", "max_chars": 200, "required": False, "desc": "where a sourced rate came from (recorded, not verified)"},
                                "rate_date": {"type": "text", "max_chars": 10, "required": False, "desc": "the rate date as YYYY-MM-DD (recorded, not verified)"}},
                  defaults=({"question": "Where the rate comes from", "default_chosen": "The owner declares it, with provenance user/sourced/assumption; a sourced rate must name its source. Nothing is retrieved or verified.", "impact": "A wrong or stale rate gives a wrong converted amount with no warning from the system."},
                            {"question": "Result currency", "default_chosen": "The converted amount is carried in the request's currency field, so set that field to the TARGET currency; the appendix states both codes.", "impact": "If the request currency is not the target, the displayed label is wrong even though the appendix is right."}),
                  assumptions=("The rate is the owner's declaration and describes the instant it is intended for.", "Both currencies are ISO 4217 codes present in the declared table."),
                  limitations=("No FX retrieval, verification, interpolation or triangulation; no forward rates.", "One rate per conversion, no spread or fee handling.", "Single-currency engagements only: no consolidation or translation of statements."),
                  default_period="cross_section", caveats=_cc_caveats, template=_cc_template, claim_ceiling="descriptive", typing=_cc_typing),
    "wacc": Method("wacc", "T1", wacc_impl, _wacc_tests, _wacc_profile, "wacc", "rate", None,
                  ("second_implementation_agrees", "weights_sum_to_one", "wacc_is_between_the_two_costs",
                   "scaling_both_market_values_changes_nothing", "rising_cost_of_equity_raises_wacc"),
                  category="valuation",
                  intended_use="Compute the weighted average cost of capital from declared market values of equity and debt and declared costs of equity and AFTER-TAX debt.",
                  unsupported_use="Estimating the cost of equity (CAPM is not implemented); computing tax; using one WACC for cash flows of materially different risk; leverage-dependent WACC recalculations.",
                  input_schema={"equity_value": {"type": "decimal", "desc": "market value of equity"},
                                "debt_value": {"type": "decimal", "desc": "market value of debt (interest-bearing)"},
                                "cost_of_equity": {"type": "decimal", "desc": "required return on equity, e.g. 0.11"},
                                "cost_of_debt_after_tax": {"type": "decimal", "desc": "cost of debt AFTER tax, e.g. 0.05; no tax is computed here"}},
                  defaults=({"question": "What the costs mean", "default_chosen": "Both costs are declared inputs. The cost of debt must already be after tax; the method computes no tax.", "impact": "Passing a pre-tax cost of debt without applying (1 - tax rate) overstates the WACC."},
                            {"question": "Weights", "default_chosen": "Market values of equity and debt determine the weights.", "impact": "Book values would give different weights and a different WACC."}),
                  assumptions=("The market values and costs are the owner's declared inputs.", "The same WACC applies to the cash flows it will discount."),
                  limitations=("No CAPM or other cost-of-equity model; no tax computation.", "A single WACC does not fit heterogeneous cash flows.", "Weights are current, not target, capital structure."),
                  default_period="annual", caveats=_wacc_caveats, template=_wacc_template, claim_ceiling="descriptive", typing=_wacc_typing),
    "dcf_valuation": Method("dcf_valuation", "T2", dcf_impl, _dcf_tests, _dcf_profile, "enterprise_value", "currency", None,
                  ("second_implementation_agrees", "value_scales_with_the_cash_flows", "a_higher_discount_rate_lowers_the_value",
                   "terminal_value_is_gordon_growth_on_the_last_flow", "without_terminal_growth_there_is_no_terminal_value"),
                  category="valuation",
                  intended_use="Discount a declared stream of end-of-period free cash flows at a declared rate, with an optional Gordon-growth terminal value, to an enterprise value.",
                  unsupported_use="Forecasting the cash flows; choosing the discount rate or growth (declare them, or use wacc and your own inputs); mid-year discounting; equity value bridge (debt/net cash adjustment); tax computation; real-option or scenario valuation.",
                  input_schema={"cashflows": {"type": "value_list", "min_items": 1, "desc": "free cash flows, one per period, first at end of period 1"},
                                "discount_rate": {"type": "decimal", "desc": "periodic discount rate, e.g. 0.10"},
                                "terminal_growth": {"type": "decimal", "required": False, "desc": "optional perpetual growth after the forecast; must be below the discount rate"}},
                  defaults=({"question": "Terminal value", "default_chosen": "No terminal value unless terminal_growth is declared; then a Gordon-growth value on the last cash flow, discounted at the same rate.", "impact": "Without a terminal value the valuation covers only the explicit forecast and will usually understate a going concern."},
                            {"question": "Timing and taxes", "default_chosen": "Cash flows are end-of-period and after tax as supplied; no mid-year convention and no tax computation.", "impact": "A mid-year convention raises the value; pre-tax cash flows with an after-tax discount rate are inconsistent."}),
                  assumptions=("The cash flows and the discount rate are the owner's declared inputs.", "The terminal growth rate persists forever and stays below the discount rate."),
                  limitations=("The result is model-conditional arithmetic, not a market price or a forecast guarantee.", "The terminal value typically dominates the answer and rests on the growth assumption.", "No mid-year convention, no equity bridge and no tax computation."),
                  default_period="annual", caveats=_dcf_caveats, template=_dcf_template, claim_ceiling="descriptive", typing=_dcf_typing),
    "weighted_summary": Method("weighted_summary", "T1", _w_impl, _w_tests, _w_profile, "weighted_mean", "from_request", None,
                  ("second_implementation_agrees", "equal_weights_reproduce_the_unweighted_summary", "mean_is_invariant_to_weight_scaling",
                   "larger_values_weighted_more_raise_the_mean", "design_effect_is_one_for_equal_weights"),
                  category="descriptive statistics",
                  intended_use="Summarize a variable under declared design or frequency weights: weighted mean, weighted standard deviation, effective sample size and design effect.",
                  unsupported_use="Standard errors, confidence intervals or tests that need a complex design; stratification, clustering or replicate weights; imputing or dropping weights; validating that the supplied weights are correct.",
                  input_schema={"values": {"type": "value_list", "min_items": 1, "desc": "the observations; blank or null counts as missing"},
                                "weights": {"type": "value_list", "min_items": 1, "desc": "one positive weight per value, same length as values (a missing value's weight is dropped with it)"},
                                "missing_codes": {"type": "code_list", "required": False, "desc": "user-defined missing codes such as 99; never read as values"},
                                "weight_kind": {"type": "enum", "values": ["reliability", "frequency"], "required": False, "desc": "reliability (precision-style, default) or frequency (counts of observations)"}},
                  defaults=({"question": "What the weights mean", "default_chosen": "Reliability weights: the variance is the unbiased weighted variance sum(w(x-mean)^2)/(sum(w) - sum(w^2)/sum(w)). Frequency weights use sum(w(x-mean)^2)/(sum(w)-1) and must be declared.", "impact": "The two conventions give different weighted standard deviations."},
                            {"question": "Inference", "default_chosen": "No standard error, interval or test is computed, because an honest one needs a declared complex design.", "impact": "Users who need design-based inference must supply a design-aware method, which is not implemented."}),
                  assumptions=("Each weight is positive and belongs to its value.", "The declared weight kind matches how the weights were produced.", "Missing values are excluded listwise together with their weights."),
                  limitations=("Summaries only; no design-based inference, stratification, clustering or replicate weights.", "Weights are not validated; a wrong weight is used as given.", "Reliability and frequency weights give different weighted standard deviations; the kind must be declared."),
                  default_period="cross_section", caveats=_w_caveats, template=_w_template, claim_ceiling="descriptive", typing=_w_typing),
    "management_accounts": Method("management_accounts", "T2", accounts_impl, accounts_tests, accounts_profile, "net_income", "currency", None,
                  ("trial_balance_debits_equal_credits", "assets_equal_liabilities_plus_equity", "net_income_agrees_across_routes", "opening_balances_equal_prior_closing", "statement_lines_foot_to_totals", "journal_hash_chain_intact", "cash_flow_agrees_across_routes", "retained_earnings_rollforward", "income_expense_and_dividends_zero_after_closing", "statement_internally_consistent", "opening_balances_agree"),
                  category="accounting", intended_use="Run a declarative management-accounts engagement (chart, opening balances, entries and schedules) through the ledger kernel: statements, trial balance, two-route cash flow, closing and the retained-earnings rollforward, with every invariant checked.",
                  unsupported_use="GAAP or IFRS statements; assurance; tax filings; multi-currency consolidation; posting anything the owner did not declare.",
                  input_schema=_ACC_INPUTS, defaults=_ACC_DEFAULTS, assumptions=_ACC_ASSUME, limitations=_ACC_LIM, default_period="annual",
                  caveats=accounts_caveats, template=accounts_template, claim_ceiling="descriptive", default_thresholds={}, typing=accounts_typing,
                  mapping=accounts_mapping, mapping_check_names=("every_account_maps_to_a_statement_line", "at_least_one_cash_account", "exactly_one_retained_earnings_account")),
}

# ---------- discovery (never executes a method) ----------
def describe(method_id):
    m = LIBRARY[method_id]
    return {"method_id": m.name, "version": m.version, "category": m.category, "tier": m.tier, "status": m.status,
            "review_status": m.review_status, "intended_use": m.intended_use, "unsupported_use": m.unsupported_use,
            "input_schema": m.input_schema, "defaults": list(m.defaults), "assumptions": list(m.assumptions),
            "limitations": list(m.limitations), "planned_checks": list(m.test_names), "claim_ceiling": m.claim_ceiling,
            "assumption_checks": list(m.assumption_check_names), "fallbacks": dict(m.fallbacks), "default_thresholds": dict(m.default_thresholds)}

def list_methods(): return [describe(k) for k in LIBRARY]
