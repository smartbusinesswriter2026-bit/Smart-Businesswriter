"""Cross-structure tie registry — the post-render assertion layer.

A tie is a *declared* relationship between two field paths in the rendered structures.
The registry evaluates ties and reports a status; it never repairs a figure.  Default
authority is ``none``: a failed hard tie blocks the structure it protects.

Structures
----------
S1 consolidation worksheet (the primary statements' consolidated view)
S2 statement of other comprehensive income
S3 earnings-per-share note
S4 segment note
S5 deferred tax note
S6 lease maturity table
S7 pension reconciliation
S8 statement of changes in equity / restatement column

Field path grammar ``S{n}.{row}.{field}`` resolves to a scalar.  A row path may also be
``S{n}.ROWS[*].{field}``, which resolves to a vector of one value per row; vectors combine
element-wise and collapse with ``SUM``.  Expressions support ``+ - * /``, parentheses,
unary minus, ``abs()``, ``min()``, ``max()`` and ``SUM()``.

Status
------
PASS                  residual within tolerance
PARAM                 one or both sides are not supplied by the case (tie-pending)
AMBIGUOUS_TAX_BASIS   a pre-tax / net-of-tax boundary is crossed without a transform
FAIL_SOFT             residual exceeds a soft tolerance (warn and emit)
FAIL_HARD             residual exceeds a hard tolerance (block the structure)

Why the tax-basis check is explicit
-----------------------------------
A missing tax basis is the largest source of false positives, so it is *declared per tie*
and *declared per field* — never inferred from a field's name.  A tie that crosses the
boundary must declare both sides; a structure may tag a field ``"undeclared"`` when the
case did not say whether the figure is pre- or post-tax, and any tie touching that field
raises ``AMBIGUOUS_TAX_BASIS`` instead of guessing.
"""
import re
from decimal import Decimal, InvalidOperation

MONETARY_HARD = Decimal("0.01")
MONETARY_PRESENTED = Decimal("1.00")
RATIO = Decimal("0.0001")
COUNT = 0

#: The phase in which each structure becomes available (spec section 4).
STRUCTURE_PHASE = {"S1": 2, "S2": 2, "S3": 3, "S4": 3, "S5": 2, "S6": 1, "S7": 1, "S8": 1}
STRUCTURE_NAME = {
    "S1": "consolidation worksheet",
    "S2": "OCI statement",
    "S3": "EPS note",
    "S4": "segment note",
    "S5": "deferred tax note",
    "S6": "lease maturity table",
    "S7": "pension reconciliation",
    "S8": "restatement column",
}
#: Structures whose output is the student's answer: a failed tie here is not "withhold the
#: structure", it is "the statements are wrong".
PROTECTED = ("S1",)
#: Declared plugs: the only fields allowed to absorb a residual without a tie.
PLUGS = [{"structure": "S1", "field": "CTA.balancing", "reason": "translation balancing figure"}]


# ---------------------------------------------------------------------------
# Expression evaluation
# ---------------------------------------------------------------------------
class ExprError(ValueError):
    """The expression is not well formed, or names a field the structures do not carry."""


class _Vector:
    """One value per row: how a ``ROWS[*]`` path behaves inside an expression."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = list(values)

    def _pair(self, other):
        if isinstance(other, _Vector):
            if len(other.values) != len(self.values):
                raise ExprError("vectors of different lengths")
            return other.values
        return [other] * len(self.values)

    def _apply(self, other, fn):
        return _Vector([fn(a, b) for a, b in zip(self.values, self._pair(other))])

    def __add__(self, other):
        return self._apply(other, lambda a, b: a + b)

    __radd__ = __add__

    def __sub__(self, other):
        return self._apply(other, lambda a, b: a - b)

    def __rsub__(self, other):
        return _Vector([b - a for a, b in zip(self.values, self._pair(other))])

    def __mul__(self, other):
        return self._apply(other, lambda a, b: a * b)

    __rmul__ = __mul__

    def __truediv__(self, other):
        def div(a, b):
            if b == 0:
                raise ExprError("division by zero")
            return a / b

        return self._apply(other, div)

    def __neg__(self):
        return _Vector([-v for v in self.values])


def _decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(1) if value else Decimal(0)
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


_PATH = re.compile(r"^S(\d+)\.([A-Za-z_]\w*)(?:\[(\*)\]|\b)(?:\.([A-Za-z_]\w*))?$")


def _resolve(path, structures):
    """Resolve a field path.  Returns Decimal, _Vector, or None when not supplied."""
    match = _PATH.match(path)
    if not match:
        return None
    sid = "S" + match.group(1)
    row_key = match.group(2)
    star = match.group(3)
    field = match.group(4)
    struct = structures.get(sid)
    if not isinstance(struct, dict):
        return None
    if star:
        rows = struct.get(row_key)
        if not isinstance(rows, list):
            return None
        return _Vector([_decimal(r.get(field)) if isinstance(r, dict) else None for r in rows])
    row = struct.get(row_key)
    if field is None:
        return _decimal(row) if not isinstance(row, (dict, list)) else None
    if isinstance(row, dict):
        return _decimal(row.get(field))
    if isinstance(row, (list, tuple)) and field.isdigit():
        index = int(field)
        return _decimal(row[index]) if index < len(row) else None
    return None


_TOKEN = re.compile(
    r"\s*(?:"
    r"(?P<number>\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    r"|(?P<path>S\d+\.[A-Za-z_]\w*(?:\[\*\](?:\.[A-Za-z_]\w*)?|\.[A-Za-z_]\w*)?)"
    r"|(?P<name>[A-Za-z_]\w*)"
    r"|(?P<op>[-+*/(),])"
    r")"
)


def _tokenize(expression):
    tokens, position = [], 0
    text = str(expression)
    while position < len(text):
        if text[position].isspace():
            position += 1
            continue
        match = _TOKEN.match(text, position)
        if not match or match.end() == position:
            raise ExprError("cannot read expression at %r" % text[position:position + 20])
        kind = match.lastgroup
        tokens.append((kind, match.group(kind)))
        position = match.end()
    return tokens


class _Parser:
    """Recursive descent over the token list: expr -> term -> factor -> primary."""

    def __init__(self, tokens, structures):
        self.tokens = tokens
        self.index = 0
        self.structures = structures

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else (None, None)

    def take(self, value=None):
        kind, token = self.peek()
        if value is not None and token != value:
            raise ExprError("expected %r, found %r" % (value, token))
        self.index += 1
        return kind, token

    def parse(self):
        value = self.expr()
        if self.index != len(self.tokens):
            raise ExprError("trailing tokens: %r" % (self.tokens[self.index:],))
        return value

    def expr(self):
        value = self.term()
        while self.peek()[1] in ("+", "-"):
            op = self.take()[1]
            right = self.term()
            if value is None or right is None:
                return None
            value = value + right if op == "+" else value - right
        return value

    def term(self):
        value = self.factor()
        while self.peek()[1] in ("*", "/"):
            op = self.take()[1]
            right = self.factor()
            if value is None or right is None:
                return None
            if op == "*":
                value = value * right
            else:
                if isinstance(right, _Vector):
                    raise ExprError("cannot divide by a vector")
                if right == 0:
                    return None
                value = value / right
        return value

    def factor(self):
        if self.peek()[1] == "-":
            self.take("-")
            value = self.factor()
            return None if value is None else -value
        if self.peek()[1] == "+":
            self.take("+")
            return self.factor()
        return self.primary()

    def primary(self):
        kind, token = self.peek()
        if token == "(":
            self.take("(")
            value = self.expr()
            self.take(")")
            return value
        if kind == "number":
            self.take()
            return Decimal(token)
        if kind == "path":
            self.take()
            return _resolve(token, self.structures)
        if kind == "name":
            self.take()
            name = token.lower()
            if self.peek()[1] != "(":
                raise ExprError("unknown name %r" % token)
            self.take("(")
            args = [self.expr()]
            while self.peek()[1] == ",":
                self.take(",")
                args.append(self.expr())
            self.take(")")
            return _call(name, args)
        raise ExprError("unexpected token %r" % (token,))


def _call(name, args):
    if name == "sum":
        if len(args) != 1:
            raise ExprError("sum() takes one argument")
        value = args[0]
        if value is None:
            return None
        if not isinstance(value, _Vector):
            return value
        total = Decimal(0)
        for item in value.values:
            if item is None:
                return None
            total += item
        return total
    if name in ("abs", "min", "max"):
        flat = []
        for arg in args:
            if isinstance(arg, _Vector):
                flat.extend(arg.values)
            else:
                flat.append(arg)
        if not flat or any(v is None for v in flat):
            return None
        if name == "abs":
            return abs(flat[0])
        return min(flat) if name == "min" else max(flat)
    raise ExprError("unknown function %r" % name)


def evaluate(expression, structures):
    """Evaluate one expression against the structures.  Returns Decimal or None.

    None means "the case does not supply this" — never zero.
    """
    if expression is None:
        return None
    text = str(expression).strip()
    if not text:
        return None
    value = _Parser(_tokenize(text), structures).parse()
    if isinstance(value, _Vector):
        raise ExprError("expression yields a vector without SUM(): %r" % text)
    return value


def fields(expression):
    """Every field path an expression names."""
    return re.findall(r"S\d+\.[A-Za-z_]\w*(?:\.\w+)?", str(expression or ""))


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------
def _tie(tid, name, lhs, relation, rhs, tol, severity, authority, phase,
         tax_basis=None, message="", on_fail=None, repair_expression=None):
    return {
        "id": tid, "name": name, "lhs": lhs, "relation": relation, "rhs": rhs,
        "tol": Decimal(str(tol)), "severity": severity, "authority": authority,
        "phase": phase, "tax_basis": tax_basis, "message": message,
        "on_fail": on_fail or ("WITHHOLD" if severity == "hard" else "WARN"),
        "repair_expression": repair_expression,
    }


TIES = [
    _tie("T01", "ni_split_closure", "S1.NI.consolidated", "eq",
         "S1.NI.parent + S1.NI.nci", "0.01", "hard", "none", 2,
         message="Consolidated net income does not equal parent + NCI attribution."),
    _tie("T02", "balance_sheet_identity", "S1.TA.consolidated", "eq",
         "S1.TL.consolidated + S1.SC.consolidated + S1.RE.consolidated + S1.NCI.consolidated",
         "0.01", "hard", "none", 2,
         message="Consolidated assets != liabilities + equity + NCI."),
    _tie("T03", "eps_numerator_to_parent_ni", "S3.NI.numerator", "eq",
         "S1.NI.parent - S3.DIV.preferred", "0.01", "hard", "none", 3,
         message="EPS numerator != consolidated NI attributable to parent less preferred dividends."),
    _tie("T04", "eps_denominator_to_share_recon", "S3.WA.shares", "exact",
         "S8.SHARES.wa_total", "0", "hard", "none", 3,
         message="EPS weighted shares != weighted shares in the share reconciliation."),
    _tie("T05", "dt_note_to_balance_sheet", "S5.CLOSING.net", "eq",
         "S1.DTL.net - S1.DTA.net", "0.01", "hard", "none", 2,
         message="Deferred tax note does not agree to the balance sheet."),
    _tie("T06", "dt_destination_sum",
         "S5.PL.total + S5.OCI.total + S5.EQUITY.total + S5.ACQ.total", "eq",
         "S5.CLOSING.net - S5.OPENING.net", "0.01", "hard", "none", 2,
         message="Deferred tax movements by destination do not sum to the closing-opening movement."),
    _tie("T07", "oci_tax_closure", "S5.OCI.total", "eq_neg",
         "S2.TAX.total", "0.01", "hard", "none", 2,
         tax_basis={"lhs": "net_of_tax", "rhs": "net_of_tax"},
         message="OCI tax per deferred tax note != OCI tax per OCI statement (sign convention)."),
    _tie("T08", "revaluation_reserve_closure", "S2.REVAL.net", "eq",
         "S1.RE.reval_component", "0.01", "hard", "none", 2,
         tax_basis={"lhs": "net_of_tax", "rhs": "net_of_tax"},
         message="Revaluation OCI != revaluation reserve movement."),
    _tie("T09", "cfh_reserve_closure", "S2.CFH.net", "eq",
         "S1.RE.cfh_component", "0.01", "hard", "none", 2,
         message="Cash-flow-hedge OCI != cash-flow-hedge reserve movement."),
    _tie("T10", "pension_oci_closure", "S2.PENSION.net", "eq",
         "S7.OCI.remeasurement", "0.01", "hard", "none", 2,
         message="Pension OCI per OCI statement != pension remeasurement per pension note."),
    _tie("T11", "funded_status_identity", "S7.FUNDED.status", "eq",
         "S7.ASSETS.closing - S7.PBO.closing", "0.01", "hard", "none", 1,
         message="Funded status != plan assets - PBO."),
    _tie("T12", "pension_balance_sheet", "S7.BS.net_liability", "eq",
         "-S7.FUNDED.status", "0.01", "hard", "none", 2,
         message="Pension net liability != -funded status."),
    _tie("T13", "segment_to_consolidated_revenue", "S4.REV.consolidated", "eq",
         "S1.REV.consolidated", "0.01", "hard", "none", 3,
         message="Segment reconciled revenue != worksheet consolidated revenue."),
    _tie("T14", "segment_reconciliation_closure",
         "S4.REV.segment_total - S4.REV.intersegment + S4.REV.unallocated", "eq",
         "S4.REV.consolidated", "0.01", "hard", "none", 3,
         message="Segment reconciliation does not close. The residual is a failure, never an 'other' bucket."),
    _tie("T15", "lease_maturity_closure", "S6.PV.total", "eq",
         "S6.UNDISC.total - S6.IMPUTED.total", "0.01", "hard", "none", 1,
         message="Lease present value != undiscounted payments - imputed interest."),
    _tie("T16", "lease_liability_to_balance_sheet", "S6.BS.liability", "eq",
         "S1.TL.lease_component", "0.01", "hard", "none", 2,
         message="Lease liability != the lease component of the balance sheet."),
    _tie("T17", "restated_opening_re", "S8.RE.opening_restated", "eq",
         "S1.RE.opening_adjusted", "0.01", "hard", "none", 3,
         message="Restated opening retained earnings != adjusted opening retained earnings."),
    _tie("T18", "restated_closing_re", "S8.RE.closing_restated", "eq",
         "S1.RE.consolidated", "0.01", "hard", "none", 3,
         message="Restated closing retained earnings != the balance sheet."),
    _tie("T19", "restatement_nets_to_zero", "S8.EQUITY.closing_restated", "eq",
         "S8.EQUITY.closing_reported", "0.01", "hard", "none", 1,
         message="Restatement changed closing equity. Only the period allocation may differ."),
    _tie("T20", "goodwill_formula", "S1.GW.consolidated", "eq",
         "S1.GW.consideration - S1.GW.nci_at_acq - S1.GW.fv_net_assets",
         "0.01", "hard", "none", 2,
         message="Goodwill != consideration + NCI at acquisition - fair value of net assets."),
    _tie("T21", "diluted_le_basic", "S3.EPS.diluted", "le",
         "S3.EPS.basic", "0.0001", "hard", "none", 3,
         message="Diluted EPS exceeds basic EPS."),
    _tie("T22", "profit_to_consolidated_ni", "S2.PROFIT.for_period", "eq",
         "S1.NI.consolidated", "0.01", "hard", "none", 2,
         message="Profit for the period in the OCI statement != revenue less expenses."),
    _tie("T23", "dt_rederivation", "S5.CLOSING.net", "eq",
         "SUM(S5.ROWS[*].cumulative_td * S5.ROWS[*].enacted_rate)", "1.00", "soft", "RHS", 2,
         message="Deferred tax note does not re-derive from its own rows.",
         repair_expression="SUM(S5.ROWS[*].cumulative_td * S5.ROWS[*].enacted_rate)"),
    _tie("T24", "segment_assets_to_consolidated",
         "S4.ASSETS.segment_total + S4.ASSETS.unallocated", "eq",
         "S1.TA.consolidated", "0.01", "hard", "none", 3,
         message="Segment assets + unallocated != consolidated total assets."),
    _tie("T25", "diluted_denominator_bridge", "S3.WA.diluted", "eq",
         "S3.WA.basic + S3.INCR.denominator_total", "0", "hard", "none", 3,
         message="Diluted weighted shares != basic + incremental shares."),
    _tie("T26", "pension_cost_component_sum", "S7.PL.net_cost", "eq",
         "SUM(S7.PL.COMPONENTS[*].amount)", "0.01", "hard", "none", 1,
         message="Net pension cost != the sum of its components."),
    _tie("T27", "correction_column_terminates", "S8.CORRECTION.cumulative", "eq",
         "0", "0.01", "hard", "none", 1,
         message="Cumulative correction does not terminate at zero in the final restated period."),
    _tie("T28", "va_le_gross_dta", "S5.VA.closing", "le",
         "S5.GROSS_DTA.closing", "0.01", "hard", "none", 2,
         message="Valuation allowance exceeds gross deferred tax assets."),
]

TIES_BY_ID = {tie["id"]: tie for tie in TIES}


def _field_tax_basis(path, structures):
    """A structure may tag a field's tax basis under ``_tax_basis``."""
    match = re.match(r"^(S\d+)\.([A-Za-z_]\w*)", path)
    if not match:
        return None
    struct = structures.get(match.group(1))
    if not isinstance(struct, dict):
        return None
    tags = struct.get("_tax_basis")
    if not isinstance(tags, dict):
        return None
    return tags.get(match.group(2))


def tax_basis_problem(tie, structures):
    """AMBIGUOUS_TAX_BASIS when a boundary is crossed without a declared convention."""
    basis = tie.get("tax_basis")
    if not basis:
        # No declared boundary: a field explicitly tagged undeclared still blocks the tie.
        for expression in (tie["lhs"], tie["rhs"]):
            for path in fields(expression):
                if _field_tax_basis(path, structures) == "undeclared":
                    return "AMBIGUOUS_TAX_BASIS"
        return None
    left, right = basis.get("lhs"), basis.get("rhs")
    if left and right and left != right and not basis.get("rate_transform"):
        return "AMBIGUOUS_TAX_BASIS"
    for expression in (tie["lhs"], tie["rhs"]):
        for path in fields(expression):
            if _field_tax_basis(path, structures) == "undeclared":
                return "AMBIGUOUS_TAX_BASIS"
    return None


def run_ties(structures, phase=None):
    """Evaluate every tie (or one phase).  Returns a list of result dicts."""
    results = []
    for tie in TIES:
        if phase is not None and tie["phase"] != phase:
            continue
        result = {"id": tie["id"], "name": tie["name"], "phase": tie["phase"],
                  "severity": tie["severity"], "on_fail": tie["on_fail"],
                  "lhs": tie["lhs"], "rhs": tie["rhs"],
                  "structures": sorted({p.split(".")[0] for p in
                                        fields(tie["lhs"]) + fields(tie["rhs"])})}
        ambiguous = tax_basis_problem(tie, structures)
        if ambiguous:
            result.update({"status": "AMBIGUOUS_TAX_BASIS", "lhs_val": None, "rhs_val": None,
                           "residual": None,
                           "message": tie["message"] or
                           "Tax basis is undeclared at a pre-tax / net-of-tax boundary."})
            results.append(result)
            continue
        try:
            lhs_val = evaluate(tie["lhs"], structures)
            rhs_val = evaluate(tie["rhs"], structures)
        except ExprError as error:
            result.update({"status": "PARAM", "lhs_val": None, "rhs_val": None, "residual": None,
                           "message": "expression could not be evaluated: " + str(error)})
            results.append(result)
            continue
        if lhs_val is None or rhs_val is None:
            result.update({"status": "PARAM", "lhs_val": lhs_val, "rhs_val": rhs_val,
                           "residual": None,
                           "message": "one or both sides are not supplied by the case"})
            results.append(result)
            continue
        if tie["relation"] == "eq_neg":
            residual = lhs_val + rhs_val
        elif tie["relation"] in ("eq", "exact"):
            residual = lhs_val - rhs_val
        elif tie["relation"] == "le":
            residual = lhs_val - rhs_val
        elif tie["relation"] == "ge":
            residual = rhs_val - lhs_val
        else:
            raise ValueError("unknown relation for %s: %s" % (tie["id"], tie["relation"]))
        tolerance = tie["tol"]
        if tie["relation"] == "le":
            passed = residual <= tolerance
        elif tie["relation"] == "ge":
            passed = residual >= -tolerance
        else:
            passed = abs(residual) <= tolerance
        if passed:
            status = "PASS"
        else:
            status = "FAIL_SOFT" if tie["severity"] == "soft" else "FAIL_HARD"
        result.update({"status": status, "lhs_val": str(lhs_val), "rhs_val": str(rhs_val),
                       "residual": str(residual), "message": tie["message"]})
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Meta-validation (phase 5)
# ---------------------------------------------------------------------------
def _structures_in(expression):
    return {path.split(".")[0] for path in fields(expression)}


def _cycles(edges):
    """Strongly connected components of size > 1, plus self-loops, as sorted lists."""
    graph = {node: sorted(targets) for node, targets in edges.items()}
    index, stack, on_stack, indices, low, out = {}, [], set(), {}, {}, []
    counter = [0]

    def strongconnect(node):
        indices[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for target in graph.get(node, ()):
            if target not in indices:
                strongconnect(target)
                low[node] = min(low[node], low[target])
            elif target in on_stack:
                low[node] = min(low[node], indices[target])
        if low[node] == indices[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.discard(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1 or (len(component) == 1 and node in graph.get(node, ())):
                out.append(sorted(component))

    for node in list(graph):
        if node not in indices:
            strongconnect(node)
    return out


def meta_validate(structures):
    """M1-M5.  Returns a list of ``{check, ok, detail}`` issues (empty means clean)."""
    issues = []
    issues.extend(_m1_completeness(structures))
    issues.extend(_m2_acyclicity())
    issues.extend(_m3_phase_order())
    issues.extend(_m4_tolerance())
    issues.extend(_m5_authority())
    return issues


def _m1_completeness(structures):
    """Every field a tie names must exist in a structure that is actually present."""
    issues = []
    seen = set()
    for tie in TIES:
        for expression in (tie["lhs"], tie["rhs"]):
            for path in fields(expression):
                if (tie["id"], path) in seen:
                    continue
                seen.add((tie["id"], path))
                sid = path.split(".")[0]
                if sid not in structures:
                    continue          # the structure is absent: its ties are PARAM, not broken
                struct = structures[sid] or {}
                row = path.split(".")[1]
                if row == "ROWS":
                    if not isinstance(struct.get("ROWS"), list):
                        issues.append({"check": "M1", "ok": False,
                                       "detail": "%s names rows but %s carries no ROWS"
                                                 % (tie["id"], sid)})
                    continue
                if row not in struct:
                    issues.append({"check": "M1", "ok": False,
                                   "detail": "%s names %s, which %s does not carry"
                                             % (tie["id"], path, sid)})
    return issues


def _m2_acyclicity():
    """No tie cycle unless the cycle declares a plug."""
    edges = {}
    for tie in TIES:
        left = _structures_in(tie["lhs"])
        right = _structures_in(tie["rhs"])
        for source in right:
            for target in left:
                edges.setdefault(source, set()).add(target)
    plugged = {plug["structure"] for plug in PLUGS}
    issues = []
    for component in _cycles({node: sorted(targets) for node, targets in edges.items()}):
        if plugged & set(component):
            continue
        issues.append({"check": "M2", "ok": False,
                       "detail": "tie dependency cycle %s has no declared plug" % (component,)})
    return issues


def _m3_phase_order():
    """A tie may not run before the structures it reads exist."""
    issues = []
    for tie in TIES:
        required = max([STRUCTURE_PHASE.get(sid, 0) for sid in
                        _structures_in(tie["lhs"]) | _structures_in(tie["rhs"])] or [0])
        if tie["phase"] < required:
            issues.append({"check": "M3", "ok": False,
                           "detail": "%s runs in phase %d but reads a phase-%d structure"
                                     % (tie["id"], tie["phase"], required)})
    return issues


def _m4_tolerance():
    """A hard tie presented to the penny may not carry a loose tolerance."""
    issues = []
    for tie in TIES:
        if tie["severity"] == "hard" and tie["tol"] > MONETARY_PRESENTED:
            issues.append({"check": "M4", "ok": False,
                           "detail": "%s is hard but tolerates %s; downgrade it to soft"
                                     % (tie["id"], tie["tol"])})
    return issues


def _m5_authority():
    """Authority without a repair expression is a repair loop waiting to happen."""
    issues = []
    for tie in TIES:
        if tie["authority"] != "none" and not tie.get("repair_expression"):
            issues.append({"check": "M5", "ok": False,
                           "detail": "%s declares authority=%s with no repair expression"
                                     % (tie["id"], tie["authority"])})
    return issues


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
def summary(results):
    """Counts by status."""
    counts = {"total": len(results), "PASS": 0, "PARAM": 0, "AMBIGUOUS_TAX_BASIS": 0,
              "FAIL_SOFT": 0, "FAIL_HARD": 0}
    for result in results:
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts


def blocked(results):
    """Structures a failing hard tie forbids emitting.

    A tie blocks the structure it protects on either side.  Ties whose sides include a
    protected structure (S1: the student's own statements) are returned under
    ``protected`` — the caller decides whether that is a refusal, because a protected
    structure failing is not "withhold a note", it is "the statements are wrong".
    """
    withhold, protected = set(), []
    for result in results:
        if result["status"] != "FAIL_HARD" or result.get("on_fail") != "WITHHOLD":
            continue
        sides = set(result["structures"])
        guarded = sides & set(PROTECTED)
        if guarded:
            protected.append(result)
        else:
            withhold |= sides
    return {"structures": sorted(withhold), "protected": protected}


def validate(structures):
    """Meta-validate, then run every tie.  Returns ``(meta_issues, results, verdict)``."""
    meta = meta_validate(structures)
    results = run_ties(structures)
    verdict = {"summary": summary(results), "blocked": blocked(results),
               "meta_ok": not meta}
    return meta, results, verdict
