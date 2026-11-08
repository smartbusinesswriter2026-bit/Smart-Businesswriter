"""Read a method's declared figures from a pasted problem, deterministically.

Accounting has had this reader for a while: a student pastes the problem and the
tile fills the figures it can prove, names the ones it cannot, and never invents
one.  Finance and economics asked the student to retype figures the problem
already stated, so the same problem had two different qualities of handling
depending on the shelf it landed on.  This module gives every shelf one reader.

The rules are the accounting rules:

* a figure is read only when the field's own name (the schema's ``desc`` label, the
  key written as words, or a registered synonym for the key) is immediately
  followed by a number;
* a number with no label is never assigned to a field;
* a required field that was not read is returned as a *named gap*, never filled
  with a guess;
* a percentage is divided by 100 only when the text carries a ``%`` and the field
  is a rate — the method's own schema says which fields those are;
* the module computes nothing.  It returns strings for the page or for a method's
  own input contract, and the frozen core does the arithmetic.

The reader is deliberately conservative.  Reading nothing and naming six gaps is a
correct answer; reading a plausible number into the wrong field is not.
"""

from __future__ import annotations

import re

from . import financial_computations as fc

FORMAT = "bp-problem-reader/1"

#: Names a student uses for a field that are not the field's own label.  Kept small
#: and specific: a synonym earns its place only when it is how the problem is worded.
SYNONYMS = {
    "rate": ("discount rate", "required return", "hurdle rate", "cost of capital",
             "interest rate", "discount", "rate of return", "rate"),
    "discount_rate": ("discount rate", "required return", "hurdle rate", "cost of capital",
                      "rate of return", "discount rate per period", "rate"),
    "cost_of_capital": ("cost of capital", "wacc", "weighted average cost of capital"),
    "cashflows": ("cash flows", "cashflow", "cash flow", "net cash flows"),
    "cash_flow": ("cash flow", "annual cash flow", "net cash flow"),
    "initial_investment": ("initial investment", "initial outlay", "capital outlay",
                           "investment", "initial cost"),
    "investment": ("investment", "initial investment", "capital", "outlay"),
    "salvage_value": ("salvage value", "residual value", "terminal value"),
    "useful_life": ("useful life", "life", "years", "number of years"),
    "price": ("price", "selling price", "unit price"),
    "quantity": ("quantity", "units", "volume"),
    "fixed_cost": ("fixed cost", "fixed costs", "total fixed cost"),
    "variable_cost": ("variable cost", "variable cost per unit", "unit variable cost"),
    "contribution_margin": ("contribution margin", "unit contribution"),
    "tax_rate": ("tax rate", "corporate tax rate", "rate of tax"),
    "growth_rate": ("growth rate", "rate of growth"),
    "inflation_rate": ("inflation rate", "rate of inflation", "inflation"),
    "yield": ("yield", "yield to maturity", "ytm"),
    "coupon_rate": ("coupon rate", "coupon"),
    "face_value": ("face value", "par value", "nominal value"),
    "maturity": ("maturity", "years to maturity", "term"),
    "principal": ("principal", "loan amount", "amount borrowed"),
    "pv": ("present value", "pv"),
    "fv": ("future value", "fv"),
    "npv": ("net present value", "npv"),
    "irr": ("internal rate of return", "irr"),
    "beta": ("beta",),
    "risk_free_rate": ("risk free rate", "risk-free rate", "rf"),
    "market_return": ("market return", "expected market return"),
}

#: A field whose schema desc says one of these is a rate: a ``%`` figure is divided
#: by 100 before it is handed over.
_RATE_WORDS = ("rate", "yield", "return", "percent", "wacc", "irr", "inflation", "growth")


class ReaderError(ValueError):
    """The request cannot be read; the message is what the page shows."""


def _clean_label(text):
    """The readable part of a schema desc: "discount rate per period, e.g. 0.10"."""
    label = str(text or "").strip()
    for marker in (", e.g.", " e.g.", ", for example", " (e.g."):
        if marker in label:
            label = label.split(marker, 1)[0].strip()
    for marker in (", default", " (optional)", "(optional)"):
        if marker in label:
            label = label.split(marker, 1)[0].strip()
    return label.rstrip(".,;")


def _key_words(key):
    return str(key or "").replace("_", " ").strip()


def _aliases(key, spec):
    """The names a student may use for one field, longest first."""
    out = []
    label = _clean_label((spec or {}).get("desc"))
    if label:
        out.append(label)
    words = _key_words(key)
    if words and words not in out:
        out.append(words)
    for alias in SYNONYMS.get(str(key), ()):
        if alias not in out:
            out.append(alias)
    return sorted(out, key=len, reverse=True)


def _is_rate(key, spec):
    text = (str(key) + " " + str((spec or {}).get("desc") or "")).lower()
    return any(word in text for word in _RATE_WORDS)


def _head(alias):
    words = re.sub(r"[^a-z0-9]+", " ", str(alias).lower()).strip().split()
    return r"\b" + r"\s+".join(re.escape(word) for word in words) + r"\b"


def _scalar_pattern(aliases):
    head = "(?:" + "|".join(_head(alias) for alias in aliases) + ")"
    return head + r"\s*(?:of|is|was|were|are|at|:|=|equals?)?\s*\$?(-?[\d,]+(?:\.\d+)?)(\s*%)?"


def _list_pattern(aliases):
    head = "(?:" + "|".join(_head(alias) for alias in aliases) + ")"
    number = r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    return head + r"\s*(?:of|is|was|are|:|=)?\s*\$?(" + number + r"(?:\s*[,;]\s*" + number + r")+)"


def _decimal(raw, percent, is_rate):
    """The string a method can take: a rate in percent becomes a decimal."""
    text = str(raw).replace(",", "")
    if percent and is_rate:
        try:
            value = float(text) / 100.0
            return ("%.10f" % value).rstrip("0").rstrip(".")
        except ValueError:
            return text
    return text


def read(method_id, schema, instruction, provided=None):
    """Read ``schema``'s fields from ``instruction``.

    Returns ``{"format", "method", "inputs", "read", "missing", "unread_numbers"}``:

    * ``inputs`` — every figure the reader could prove, as strings;
    * ``read`` — the field names it filled and where they came from;
    * ``missing`` — the required fields it could not prove, by their readable label;
    * ``unread_numbers`` — counts of numbers in the text that no field claimed.  It is
      reported so the page can say "four figures were not used", never so a figure can
      be assigned to fill a gap.

    ``provided`` are the figures the student typed; they win over the text and are
    never re-read.
    """
    schema = schema if isinstance(schema, dict) else {}
    if not schema:
        raise ReaderError("This method declares no figures to read.")
    text = str(instruction or "")
    provided = {str(k): str(v) for k, v in (provided or {}).items() if v not in (None, "")}

    inputs, read_fields = {}, []
    for key in provided:
        inputs[key] = provided[key]
        read_fields.append({"field": key, "source": "typed"})

    for key, spec in schema.items():
        if key in inputs:
            continue
        spec = spec if isinstance(spec, dict) else {}
        aliases = _aliases(key, spec)
        if not aliases:
            continue
        is_rate = _is_rate(key, spec)
        if str(spec.get("type") or "") in ("decimal_list", "value_list"):
            match = re.search(_list_pattern(aliases), text, re.I)
            if match:
                block = re.sub(r"(?<=\d),(?=\d{3}\b)", "", match.group(1))
                parts = [p.strip() for p in re.split(r"[,;]", block) if p.strip()]
                inputs[key] = ", ".join(_decimal(p, False, is_rate) for p in parts)
                read_fields.append({"field": key, "source": "text"})
                continue
            # a list may also be written as one figure per label: "year 1 ... year 2 ..."
            continue
        match = re.search(_scalar_pattern(aliases), text, re.I)
        if match:
            inputs[key] = _decimal(match.group(1), bool(match.group(2)), is_rate)
            read_fields.append({"field": key, "source": "text"})

    missing = []
    for key, spec in schema.items():
        spec = spec if isinstance(spec, dict) else {}
        if spec.get("required", True) is False:
            continue
        if key not in inputs:
            missing.append(_clean_label(spec.get("desc")) or _key_words(key))

    claimed = set()
    for entry in read_fields:
        claimed.add(entry["field"])
    unread = _unread_count(text, schema, inputs)
    return {"format": FORMAT, "method": str(method_id or ""), "inputs": inputs,
            "read": read_fields, "missing": missing, "unread_numbers": unread}


def _number_tokens(text):
    return re.findall(r"-?[\d,]+(?:\.\d+)?", str(text or ""))


def _unread_count(text, schema, inputs):
    """How many numbers in the text no field claimed.  Reported, never filled."""
    tokens = _number_tokens(text)
    if not tokens:
        return 0
    wanted = 0
    for value in inputs.values():
        for part in str(value).split(","):
            wanted += 1 if str(part).strip() else 0
    return max(0, len(tokens) - wanted)


__all__ = ["FORMAT", "SYNONYMS", "ReaderError", "read"]
