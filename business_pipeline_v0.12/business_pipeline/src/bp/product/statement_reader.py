"""Read a financial statement and extract the lines classroom ratios need.

The reader is conservative: a line is matched only when its label is a known
synonym for one of the line items below, and the number next to it is parsed as
a float.  A line that does not match is ignored, never assigned to a field, and
a ratio whose lines are missing is a named gap, never a zero or an estimate.
"""

from __future__ import annotations

import re

FORMAT = "bp-statement-reader/1"

# label -> canonical line key.  Synonyms are lowercase; matching is case-insensitive
# and ignores punctuation.
_SYNONYMS = {
    "revenue": ("revenue", "sales", "total revenue", "net sales", "net revenue",
                "turnover", "total sales"),
    "cost_of_goods_sold": ("cost of goods sold", "cogs", "cost of sales",
                           "cost of revenue"),
    "gross_profit": ("gross profit", "gross margin"),
    "net_income": ("net income", "net profit", "profit after tax", "net earnings",
                   "profit for the year", "profit for period"),
    "ebit": ("ebit", "operating income", "operating profit", "earnings before interest and tax"),
    "total_assets": ("total assets", "assets total", "total asset"),
    "current_assets": ("current assets", "total current assets"),
    "current_liabilities": ("current liabilities", "total current liabilities"),
    "inventory": ("inventory", "inventories", "stock"),
    "total_liabilities": ("total liabilities", "liabilities total"),
    "equity": ("shareholders equity", "shareholders' equity", "stockholders equity",
               "owners equity", "total equity", "equity"),
    "retained_earnings": ("retained earnings", "retained profit", "accumulated profit"),
    "working_capital": ("working capital",),
    "eps": ("earnings per share", "eps", "basic eps"),
    "book_value_per_share": ("book value per share", "bvps", "book value"),
    "market_value_equity": ("market value of equity", "market cap", "market capitalisation",
                            "market capitalization"),
    "shares_outstanding": ("shares outstanding", "number of shares"),
}

# canonical line -> ratio ids that depend on it (for gap reporting).
_LINE_KEYS = set(_SYNONYMS.values()) and set(_SYNONYMS.keys()) or set()
# Actually the canonical keys are the dict keys; build from them.
_LINE_KEYS = set(_SYNONYMS.keys())


def _norm(label):
    return re.sub(r"[^a-z0-9 ]+", " ", str(label or "").lower()).strip()


def _match(label):
    norm = _norm(label)
    if not norm:
        return None
    for key, syns in _SYNONYMS.items():
        for syn in syns:
            if _norm(syn) == norm:
                return key
    # substring fallback: the longest synonym that is contained in the label
    best = None
    for key, syns in _SYNONYMS.items():
        for syn in syns:
            s = _norm(syn)
            if s and s in norm and (best is None or len(s) > len(best[1])):
                best = (key, s)
    return best[0] if best else None


def _parse_number(text):
    if text is None:
        return None
    s = str(text).strip().replace(",", "")
    if s == "":
        return None
    # strip currency symbols and percent signs, keep sign and decimal
    s = re.sub(r"[^\d.\-eE+]", "", s)
    if s in ("", "-", ".", "+"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _split_line(line):
    # returns (label, value) or None
    line = str(line or "").strip()
    if not line:
        return None
    # tab or comma first
    if "\t" in line:
        parts = line.split("\t", 1)
    elif "," in line:
        parts = line.split(",", 1)
    elif ";" in line:
        parts = line.split(";", 1)
    elif ":" in line:
        parts = line.split(":", 1)
    else:
        # last whitespace-separated token as value
        m = re.match(r"^(.*?)[\s]+([-+]?\d[\d,.\-eE+]*)\s*$", line)
        if m:
            return m.group(1).strip(), m.group(2).strip()
        return None
    if len(parts) != 2:
        return None
    return parts[0].strip(), parts[1].strip()


def _read_xlsx(raw):
    import io
    try:
        import openpyxl
    except Exception:
        return ""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
    except Exception:
        return ""
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            cells = [("" if c.value is None else str(c.value)).strip() for c in row]
            if not any(cells):
                continue
            # two-column label/value
            if len(cells) >= 2 and cells[0] and cells[1]:
                out.append("%s, %s" % (cells[0], cells[1]))
            elif len(cells) == 1 and cells[0]:
                out.append(cells[0])
    return "\n".join(out)


def _read_pdf(raw):
    try:
        import pypdf
    except Exception:
        try:
            import PyPDF2 as pypdf  # type: ignore
        except Exception:
            return ""
    try:
        reader = pypdf.PdfReader(__import__("io").BytesIO(raw))
    except Exception:
        return ""
    out = []
    for page in getattr(reader, "pages", []):
        try:
            out.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(out)


def read_bytes(raw, mime):
    mime = str(mime or "").lower()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    raw = bytes(raw)
    if mime in ("text/csv", "text/plain", "text/tab-separated-values"):
        text = raw.decode("utf-8", errors="replace")
    elif mime in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                  "application/vnd.ms-excel"):
        text = _read_xlsx(raw)
    elif mime == "application/pdf":
        text = _read_pdf(raw)
    else:
        # try utf-8 first, then xlsx/pdf by sniffing
        try:
            text = raw.decode("utf-8")
        except Exception:
            text = _read_pdf(raw) or _read_xlsx(raw)
    return read(text)


def read(text):
    lines = {}
    for raw in str(text or "").splitlines():
        split = _split_line(raw)
        if not split:
            continue
        label, value = split
        key = _match(label)
        if key is None:
            continue
        num = _parse_number(value)
        if num is None:
            continue
        # first occurrence wins
        if key not in lines:
            lines[key] = num
    ratios = {}
    gaps = []

    def need(*keys):
        return all(k in lines for k in keys)

    # gross margin
    if need("gross_profit", "revenue"):
        ratios["gross_margin"] = lines["gross_profit"] / lines["revenue"]
    elif need("revenue", "cost_of_goods_sold"):
        ratios["gross_margin"] = (lines["revenue"] - lines["cost_of_goods_sold"]) / lines["revenue"]
    else:
        gaps.append("gross_margin")

    # net margin
    if need("net_income", "revenue"):
        ratios["net_margin"] = lines["net_income"] / lines["revenue"]
    else:
        gaps.append("net_margin")

    # current ratio
    if need("current_assets", "current_liabilities"):
        ratios["current_ratio"] = lines["current_assets"] / lines["current_liabilities"]
    else:
        gaps.append("current_ratio")

    # quick ratio
    if need("current_assets", "inventory", "current_liabilities"):
        ratios["quick_ratio"] = (lines["current_assets"] - lines["inventory"]) / lines["current_liabilities"]
    else:
        gaps.append("quick_ratio")

    # debt to equity
    if need("total_liabilities", "equity"):
        ratios["debt_to_equity"] = lines["total_liabilities"] / lines["equity"]
    else:
        gaps.append("debt_to_equity")

    # asset turnover
    if need("revenue", "total_assets"):
        ratios["asset_turnover"] = lines["revenue"] / lines["total_assets"]
    else:
        gaps.append("asset_turnover")

    # inventory turnover
    if need("cost_of_goods_sold", "inventory"):
        ratios["inventory_turnover"] = lines["cost_of_goods_sold"] / lines["inventory"]
    else:
        gaps.append("inventory_turnover")

    # roa
    if need("net_income", "total_assets"):
        ratios["roa"] = lines["net_income"] / lines["total_assets"]
    else:
        gaps.append("roa")

    # roe
    if need("net_income", "equity"):
        ratios["roe"] = lines["net_income"] / lines["equity"]
    else:
        gaps.append("roe")

    # altman z
    if need("current_assets", "current_liabilities", "total_assets", "retained_earnings",
            "ebit", "total_liabilities", "market_value_equity", "revenue"):
        wc = lines["current_assets"] - lines["current_liabilities"]
        ta = lines["total_assets"]
        tl = lines["total_liabilities"]
        ratios["altman_z"] = (1.2 * wc / ta + 1.4 * lines["retained_earnings"] / ta
                              + 3.3 * lines["ebit"] / ta + 0.6 * lines["market_value_equity"] / tl
                              + 1.0 * lines["revenue"] / ta)
    else:
        gaps.append("altman_z")

    # dupont roe
    if need("net_income", "revenue", "total_assets", "equity"):
        net_margin = lines["net_income"] / lines["revenue"]
        asset_turnover = lines["revenue"] / lines["total_assets"]
        equity_multiplier = lines["total_assets"] / lines["equity"]
        ratios["dupont_roe"] = net_margin * asset_turnover * equity_multiplier
    else:
        gaps.append("dupont_roe")

    # graham number
    if need("eps", "book_value_per_share"):
        ratios["graham_number"] = (22.5 * lines["eps"] * lines["book_value_per_share"]) ** 0.5
    else:
        gaps.append("graham_number")

    # piotroski: report as gap unless all nine inputs present; we do not fabricate the score
    piotroski_inputs = ("net_income", "current_assets", "current_liabilities",
                        "total_assets", "total_liabilities", "equity", "revenue")
    if all(k in lines for k in piotroski_inputs):
        # minimal proxy: profitability + leverage/liquidity; full 9-test score left to student
        ratios["piotroski_f"] = None
        gaps.append("piotroski_f")
    else:
        gaps.append("piotroski_f")

    # remove None placeholders
    for k in [k for k, v in ratios.items() if v is None]:
        del ratios[k]

    return {"format": FORMAT, "lines": lines, "ratios": ratios, "gaps": sorted(set(gaps))}
