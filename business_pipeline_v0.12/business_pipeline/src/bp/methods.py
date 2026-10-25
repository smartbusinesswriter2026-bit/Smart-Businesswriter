"""T1 method library with an explicit method contract (Stage 5 brief s6; manual 5.3, 5.5, 9B).
Discovery (describe/list) never executes a method. Inputs are schema-validated before anything runs."""
import statistics, re
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

def validate_inputs(m, inp) -> list[str]:
    if not isinstance(inp, dict): return ["inputs must be an object"]
    errs, sch = [], m.input_schema
    if not sch: return errs
    errs += [f"unknown input '{k}'; allowed: {sorted(sch)}" for k in inp if k not in sch]
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
