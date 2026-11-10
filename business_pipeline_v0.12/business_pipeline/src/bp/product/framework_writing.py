"""The rules and formatters that make a framework analysis auditable.

Nothing here is evidence.  Every string this module prints is either a declared
label, a count, an item's recorded identity or a stored reading.  The tier,
recency and strength rules are **product conventions**, printed in the audit
note so a reader can challenge them; they are not claims the source makes.

The module is deliberately framework-agnostic.  The three Porter frameworks
declare their own drivers, sections and audit needs in
`bp.product.framework_profiles`; the rules below are shared so the same source
cannot be strong in one framework and weak in another.
"""

import datetime
import re

#: The declared scales.  One copy, so the prompt, the validator and the paper
#: cannot drift apart.
TIERS = ("A", "B", "C", "D")
RECENCY = ("current", "stale", "undated")
STRENGTH = ("Strong", "Moderate", "Weak")
RATINGS = ("Low", "Moderate", "High")
FITS = ("Strong", "Partial", "Weak", "None")
CONDITIONS = ("Advantage", "Neutral", "Disadvantage")
RISK = ("Lowest", "Moderate", "Highest")
IMPACT = ("Lowers", "Neutral", "Raises")
EVIDENCE = ("Strong", "Moderate", "Weak")
TRENDS = ("Rising", "Stable", "Falling")
CONFIDENCE = ("High", "Medium", "Low")
CLAIM_TYPES = ("F", "I", "J", "H")
CAUSAL = ("Yes", "Plausible", "No")

#: The declared scales a profile may choose.  Five Forces rates intensity;
#: Generic Strategies rates fit; the Diamond rates a condition.
SCALES = {"intensity": RATINGS, "fit": FITS, "condition": CONDITIONS,
          "risk": RISK, "impact": IMPACT, "evidence": EVIDENCE}


def scale_for(writing):
    """The declared scale of a writing module, defaulting to the intensity scale."""
    return SCALES.get(_text((writing or {}).get("scale")), RATINGS)

#: "Anything older than about three years is potentially stale."  The window is
#: declared here, not hidden in a formatter.
CURRENT_YEARS = 3

#: A database the record identifies as primary: a filing, a regulator, an
#: official statistic or audited financials.  Retrieval rarely supplies these
#: today; the rule exists so a future source is graded honestly.
_PRIMARY = frozenset({
    "sec edgar", "edgar", "company filing", "audited financials", "annual report",
    "world bank", "imf", "oecd", "eurostat", "national statistics", "regulator",
    "official statistics",
})

#: A reputable secondary index or a corpus book.
_SCHOLARLY = frozenset({
    "openalex", "crossref", "semantic scholar", "doaj", "proprietary corpus",
})

#: A weaker index: a preprint or a repository that is not peer reviewed.
_WEAK_INDEX = frozenset({"arxiv", "ssrn", "researchgate"})

#: The scale and analytical vocabulary a reading is allowed to use.  These are
#: labels, not facts about a source, so the proper-noun guard must not read them
#: as invented names.
READING_WORDS = set(
    "rating low moderate high trend rising stable falling confidence evidence driver "
    "drivers impact profitability profit margin margins cost costs price prices buyer "
    "buyers supplier suppliers rival rivals rivalry entry entrant entrants substitute "
    "substitutes competition competitive market industry firm unit analysis strong weak "
    "data source sources current stale undated fact inference judgment hypothesis increase "
    "decrease test testing validate validation experiment pilot prototype criterion "
    "assumption assumptions register risk rank priority "
    "pressure pressures value advantage disadvantage demand supply capacity growth share "
    "barrier barriers switching retention loyalty scale distribution brand regulation "
    "technology capital labour labor input inputs output outputs customer customers "
    "segment segments focus focused differentiation cost leadership".split())


class ReadingError(ValueError):
    """A proposed reading cannot be printed honestly."""


#: Words that mark a vetted-web page as a press release, vendor page, blog or
#: opinion piece.  The page is still vetted; its **tier** is weak, not its use.
_WEAK_WEB = re.compile(
    r"\b(press release|newsroom|prnewswire|businesswire|globenewswire|blog|"
    r"opinion|commentary|sponsored|advertorial)\b", re.I)
_WEAK_URL = re.compile(r"/(press|newsroom|blog|opinion|sponsored)/", re.I)


def _text(value):
    return str(value or "").strip()


def _database(item):
    return _text((item or {}).get("database") or (item or {}).get("source")).lower()


def tier_for(item):
    """The evidence tier of one source: A, B, C or D.

    A missing or unknown database is **C**, never A.  A source with no database
    and no title is **D**.  The rule is a convention; the audit note says so.
    """
    if not isinstance(item, dict):
        return "D"
    kind = _text(item.get("source_kind")).lower()
    if kind in ("filing", "regulator", "official", "statistic", "audited"):
        return "A"
    database = _database(item)
    title = _text(item.get("title"))
    url = _text(item.get("url"))
    if database in _PRIMARY:
        return "A"
    if database == "vetted web":
        if _WEAK_WEB.search(title) or _WEAK_WEB.search(url) or _WEAK_URL.search(url):
            return "C"
        return "B"
    if database in _SCHOLARLY:
        return "B"
    if database in _WEAK_INDEX or database == "orientation web":
        return "C"
    if database:
        return "C"
    return "C" if title else "D"


def recency_for(item, now=None):
    """Whether the evidence is current, stale or undated.

    ``current`` is the last three years inclusive; anything older is ``stale``;
    a missing or unreadable year is ``undated``.  The clock is read once at run
    time and recorded in the audit.
    """
    if not isinstance(item, dict):
        return "undated"
    try:
        year = int(item.get("year"))
    except (TypeError, ValueError):
        return "undated"
    if year <= 0:
        return "undated"
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return "current" if year >= now.year - CURRENT_YEARS else "stale"


def strength_for(tier, recency, quantified=False):
    """How much weight one claim can bear under the declared rule.

    Strong needs a current A/B source **and** a quantified figure.  A claim
    without quantification is capped at Moderate; stale evidence is capped at
    Moderate; a C, D or undated source is Weak.  This is a rule, not a reading of
    the source.
    """
    if tier not in TIERS:
        tier = "D"
    if recency not in RECENCY:
        recency = "undated"
    if tier in ("C", "D") or recency == "undated":
        return "Weak"
    if recency == "stale":
        return "Moderate"
    return "Strong" if quantified else "Moderate"


def has_figure(text):
    """Whether a claim carries a number the audit can call quantified.

    A bare year is not a figure: "the market grew" and "the market grew 4% in
    2024" are different claims, and only the second is quantified.  A year is
    stripped before the test so a date cannot earn a Strong rating.
    """
    value = _text(text)
    if not value:
        return False
    value = re.sub(r"\b(?:19|20)\d{2}\b", " ", value)
    return bool(re.search(r"\d", value))


def metadata_for(source):
    """The audit metadata one retrieved source contributes to its item."""
    source = source if isinstance(source, dict) else {}
    return {"year": source.get("year"), "database": source.get("database"),
            "url": source.get("url"), "doi": source.get("doi"),
            "tier": tier_for(source), "recency": recency_for(source)}


def assign_source_ids(blocks):
    """Give every sourced item a stable ``S1``, ``S2`` ... in first appearance.

    The same source keeps one id across dimensions; a student item, a background
    paragraph and an assumption get none, because they are not sources.  The
    mapping is returned so the audit can print it.
    """
    mapping = {}
    for block in blocks or []:
        for item in (block or {}).get("items") or []:
            if _text(item.get("provenance")) != "sourced":
                continue
            source = _text(item.get("source"))
            if not source:
                continue
            if source not in mapping:
                mapping[source] = "S%d" % (len(mapping) + 1)
            item["source_id"] = mapping[source]
    return mapping


def _blob(items, unit):
    """Every string a reading may reuse: the items and the declared unit."""
    parts = []
    for item in items or []:
        if isinstance(item, dict):
            for key in ("text", "citation", "title", "source"):
                parts.append(_text(item.get(key)))
    if isinstance(unit, dict):
        for key in ("value", "market", "industry", "country", "firm"):
            parts.append(_text(unit.get(key)))
    return " ".join(part for part in parts if part)


def _invented(text, blob, allowed_names=None):
    """What a reading introduced that the items do not carry: number/name/link."""
    if re.search(r"https?://|www\.|doi:|\bet al\.", text, re.I):
        return "link"
    known = set(re.findall(r"\d[\d,.]*", blob))
    for number in re.findall(r"\d[\d,.]*", text):
        if number not in known:
            return "number"
    lower = blob.lower()
    allowed = {str(word).lower() for word in (allowed_names or set())}
    for match in re.finditer(r"\b[A-Z][a-z]{2,}\b", text):
        prefix = text[:match.start()].rstrip()
        if not prefix or prefix[-1] in ".!?:":
            continue
        word = match.group(0).lower()
        if word not in lower and word not in allowed and word not in READING_WORDS:
            return "name"
    return ""


def _short(value, limit=180):
    text = _text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def scope_lines(profile, result):
    """The scope statement: the unit, the geography and the time frame.

    Every part is read from the record: the declared unit, the country or region
    the run used, and the dates the accepted evidence carries.  A part the record
    does not hold is said to be unstated, never invented.
    """
    unit = (result or {}).get("unit") or {}
    field = _text(unit.get("field"))
    lines = []
    if field == "firm":
        lines.append("The unit of analysis is the firm or business unit, %s, in the market, %s."
                     % (_text(unit.get("firm")) or "named in the brief",
                        _text(unit.get("market")) or "named in the brief"))
    elif field == "country_industry":
        lines.append("The unit of analysis is the industry, %s, in the country or region, %s."
                     % (_text(unit.get("industry")) or "named in the brief",
                        _text(unit.get("country")) or "named in the brief"))
    else:
        lines.append("The unit of analysis is the industry: %s. The analysis is of the industry's "
                     "structure, not of one company's performance."
                     % (_text(unit.get("value")) or "named in the brief"))
    country = _text((result or {}).get("country"))
    if country:
        lines.append("The geographic scope is %s, as named in the brief." % country)
    else:
        lines.append("The brief names no single country; the accepted evidence is not confined to one.")
    years = []
    for block in (result or {}).get("blocks") or []:
        for item in block.get("items") or []:
            try:
                year = int(item.get("year"))
            except (TypeError, ValueError):
                continue
            if year > 0:
                years.append(year)
    if years:
        lines.append("The brief states no period; the accepted evidence is dated %d to %d."
                     % (min(years), max(years)))
    else:
        lines.append("The brief states no period and the accepted evidence carries no date.")
    return lines


def table(columns, rows, note=""):
    """A section table: the declared columns and printable rows."""
    return {"columns": [_text(column) for column in columns],
            "rows": [[_text(cell) for cell in row] for row in rows],
            "note": _text(note)}


def clean_tables(value, limit=4):
    """The model's declared tables, cleaned to the shape a section can print.

    A table is the module's own worksheet (a verification audit, an FMEA
    worksheet, a cycle log, a scorecard).  It is not evidence by itself: the
    cells are scanned for template text and every row must fill the declared
    columns.  A malformed table is dropped rather than printed half-built.
    """
    if not isinstance(value, list):
        return []
    out = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        heading = _text(entry.get("heading"))
        columns = [_text(column) for column in entry.get("columns") or [] if _text(column)]
        if not heading or len(columns) < 2:
            continue
        rows = []
        for row in entry.get("rows") or []:
            if not isinstance(row, list) or len(row) != len(columns):
                continue
            rows.append([_text(cell) for cell in row])
        if rows:
            out.append({"heading": heading, "columns": columns, "rows": rows[:40]})
        if len(out) >= limit:
            break
    return out


def _has_evidence(block):
    """Whether a block carries evidence, as opposed to labelled background only."""
    return any(_text(item.get("provenance")) in ("sourced", "student")
               for item in (block or {}).get("items") or [])


def summary_table(profile, blocks):
    """The module's one-line-per-part summary, built from the readings."""
    writing = (profile or {}).get("writing") or {}
    columns = writing.get("summary_columns") or ["Part", "Rating", "Trend", "Confidence",
                                                 "One-line rationale"]
    rows = []
    for block in blocks or []:
        reading = block.get("reading") or {}
        if reading.get("status") == "dropped":
            rating = trend = confidence = "Not rated"
            reason = "The student dropped the proposed reading."
        elif reading.get("status") == "absent" or not reading.get("rating"):
            if _has_evidence(block):
                rating = trend = confidence = "Not rated"
                reason = "No rating was proposed for this part."
            else:
                rating = trend = confidence = "Not rated"
                reason = "Insufficient evidence: " + _short(block.get("gap") or "no citable evidence", 100)
        else:
            rating = _text(reading.get("rating"))
            trend = _text(reading.get("trend"))
            confidence = _text(reading.get("confidence"))
            reason = _short(reading.get("rationale") or reading.get("so_what"), 110)
        rows.append([_text(block.get("label") or block.get("key")), rating, trend, confidence, reason])
    return table(columns, rows)


def reading_paragraph(block):
    """The rating's own paragraph: drivers, trend, impact, confidence and so what.

    This is printed beside the model's prose so a rating can never appear without
    the parts the guideline requires.  Every part is stored on the block; nothing
    is inferred here.
    """
    reading = block.get("reading") or {}
    if reading.get("status") == "dropped":
        return ""
    if not reading or reading.get("status") == "absent" or not reading.get("rating"):
        # No rating is not a paragraph: the summary table says "Not rated", and
        # the audit says why.  The dimension keeps its own evidence-led prose,
        # so a draft is not preceded by a sentence about the model's absence.
        return ""
    items = block.get("items") or []
    drivers = []
    for driver in reading.get("drivers") or []:
        evidence = driver.get("evidence")
        if evidence is None:
            drivers.append("%s (judgment)" % _text(driver.get("driver")))
        else:
            item = items[evidence] if 0 <= evidence < len(items) else {}
            source = _text(item.get("source_id")) or _text(item.get("citation")) or "the accepted item"
            drivers.append("%s (evidence %s, %s)" % (_text(driver.get("driver")), source,
                                                     _text(driver.get("type")).lower()))
    text = ("%s: %s. Drivers: %s. Trend: %s - %s. Profitability impact: %s. "
            "Confidence: %s - %s. So what: %s."
            % (_text(reading.get("rating_label")) or "Rating",
               _text(reading.get("rating")), "; ".join(drivers) or "none recorded",
               _text(reading.get("trend")), _text(reading.get("trend_reason")),
               _text(reading.get("profitability_impact")), _text(reading.get("confidence")),
               _text(reading.get("confidence_reason")), _text(reading.get("so_what"))))
    status = _text(reading.get("status"))
    if status == "proposed":
        text += " The reading is proposed and has not been confirmed by the student."
    elif status == "overridden":
        text += " The student overrode the proposed value."
    elif status == "confirmed":
        text += " The student confirmed the reading."
    return text


def reading_status_line(blocks):
    """How far the student has confirmed the readings; printed with the audit."""
    counts = {"proposed": 0, "confirmed": 0, "overridden": 0, "dropped": 0, "absent": 0}
    for block in blocks or []:
        status = _text((block.get("reading") or {}).get("status"))
        if status in counts:
            counts[status] += 1
    if not any(counts.values()):
        return ""
    return ("Readings: %d proposed, %d confirmed, %d overridden, %d dropped, %d absent. "
            "A proposal is the system's judgment until the student decides."
            % (counts["proposed"], counts["confirmed"], counts["overridden"],
               counts["dropped"], counts["absent"]))


def forward_lines(blocks):
    """The forward look from the stored trends, or the honest absence of one.

    A trend is a reading, not a forecast.  This paragraph says which stored trend
    would move a rating and why; it never invents a technology, policy or market
    shift the items do not carry.
    """
    lines = []
    for block in blocks or []:
        reading = block.get("reading") or {}
        if not reading.get("trend") or reading.get("status") == "absent":
            continue
        lines.append("%s: the stored trend is %s, because %s. A change in that condition would "
                     "move the rating, and the forward look is limited to that condition."
                     % (_text(block.get("label") or block.get("key")), _text(reading.get("trend")),
                        _text(reading.get("trend_reason"))))
    if not lines:
        return ["No forward-looking shift is claimed: the accepted items describe conditions at "
                "the time of the source, not a trend across time."]
    return lines[:4]


def _rows_for_block(block):
    """Every material claim one block supports, with its source and its weight."""
    rows = []
    label = _text(block.get("label") or block.get("key"))
    reading = block.get("reading") or {}
    drivers_by_evidence = {}
    for driver in reading.get("drivers") or []:
        if driver.get("evidence") is not None:
            drivers_by_evidence.setdefault(driver["evidence"], driver)
    for index, item in enumerate(block.get("items") or []):
        if _text(item.get("provenance")) != "sourced":
            continue
        tier = _text(item.get("tier")) or "D"
        recency = _text(item.get("recency")) or "undated"
        quantified = has_figure(item.get("text"))
        strength = strength_for(tier, recency, quantified)
        notes = []
        if recency == "stale":
            notes.append("stale")
        if recency == "undated":
            notes.append("undated")
        if tier in ("C", "D"):
            notes.append("weak or unclassified source")
        driver = drivers_by_evidence.get(index) or {}
        if _text(driver.get("bias")) not in ("", "not classified"):
            notes.append("bias: " + _text(driver.get("bias")))
        if strength != "Strong" and not quantified and tier in ("A", "B") and recency == "current":
            notes.append("no quantified figure; capped at Moderate")
        rows.append({
            "claim": _short(item.get("text"), 180),
            "dimension": label,
            "source_id": _text(item.get("source_id")),
            "tier": tier, "recency": recency, "type": "F", "strength": strength,
            "causal": _text((drivers_by_evidence.get(index) or {}).get("causal")) or "-",
            "notes": "; ".join(notes) or "",
        })
    for driver in reading.get("drivers") or []:
        kind = _text(driver.get("type")).upper()
        evidence = driver.get("evidence")
        if kind == "H":
            item = (block.get("items") or [])[evidence] if (
                evidence is not None and 0 <= evidence < len(block.get("items") or [])) else {}
            rows.append({
                "claim": _short(driver.get("driver"), 180), "dimension": label,
                "source_id": _text(item.get("source_id")) or "-",
                "tier": _text(item.get("tier")) or "-",
                "recency": _text(item.get("recency")) or "-",
                "type": "H", "strength": "-",
                "causal": _text(driver.get("causal")) or "-",
                "notes": "hypothesis; test: " + (_text(driver.get("test")) or "not stated"),
            })
        elif evidence is None or kind == "J":
            rows.append({
                "claim": _short(driver.get("driver"), 180), "dimension": label,
                "source_id": "-", "tier": "-", "recency": "-", "type": "J", "strength": "-",
                "causal": _text(driver.get("causal")) or "-",
                "notes": "judgment driver; not evidence",
            })
    return rows


#: The assumption register's default columns.  A module may declare its own.
REGISTER_COLUMNS = ("Assumption", "Block", "Why it matters", "Evidence so far",
                    "Test", "Confidence")


def assumption_register(blocks, columns=None):
    """Every hypothesis the record holds, with its test and confidence.

    A register row is built only from a stored H driver: the assumption, the
    block, the reading's rationale, the evidence it cites (or "not evidenced"),
    the test the model named and the confidence.  A block with no H driver adds
    no row; a run with no H driver has no register.
    """
    columns = [str(column) for column in (columns or REGISTER_COLUMNS)]
    rows = []
    for block in blocks or []:
        reading = block.get("reading") or {}
        label = _text(block.get("label") or block.get("key"))
        for driver in reading.get("drivers") or []:
            if _text(driver.get("type")).upper() != "H":
                continue
            evidence = driver.get("evidence")
            item = (block.get("items") or [])[evidence] if (
                evidence is not None and 0 <= evidence < len(block.get("items") or [])) else {}
            evidence_text = (_text(item.get("source_id")) or _text(item.get("citation"))
                             or "accepted item") if item else "not evidenced"
            values = {
                "Assumption": _text(driver.get("driver")),
                "Block": label,
                "Why it matters": _text(reading.get("rationale") or reading.get("so_what")),
                "Evidence so far": evidence_text,
                "Test": _text(driver.get("test")) or "not stated",
                "Confidence": _text(reading.get("confidence")) or "not stated",
            }
            rows.append([values.get(column, "") for column in columns])
    return table(columns, rows)


def audit(profile, result, outcome_evidenced=False):
    """The evidence audit: every claim, the checks, the gaps and the verdict.

    The checks are computed from the record, not asserted.  The verdict is a
    declared rule, and the reason names the checks that produced it.
    """
    writing = (profile or {}).get("writing") or {}
    blocks = (result or {}).get("blocks") or []
    rows = []
    for block in blocks:
        rows.extend(_rows_for_block(block))
    rows = rows[:40]
    sources = {row["source_id"] for row in rows if row["source_id"] and row["source_id"] != "-"}
    # A block filled only with the framework's own labelled background is a gap
    # for the audit: background is not evidence, and a paper that called it
    # evidence would overstate the record (found on a live run).
    gaps = [_text(block.get("label") or block.get("key"))
            for block in blocks if not _has_evidence(block)]
    quantified = any(row["type"] == "F" and has_figure(row["claim"]) for row in rows)
    bias = [row for row in rows if "bias:" in (row.get("notes") or "")]
    contradictions = []
    for block in blocks:
        for note in (block.get("reading") or {}).get("contradictions") or []:
            contradictions.append({"dimension": _text(block.get("label") or block.get("key")),
                                   "note": _text(note)})
    areas = sorted({_text(driver.get("area")) for block in blocks
                    for driver in (block.get("reading") or {}).get("drivers") or []
                    if _text(driver.get("area"))})
    module = _text(writing.get("module"))
    coverage = None
    if module == "generic_strategies":
        coverage = {"areas": areas, "required": 3, "pass": len(areas) >= 3}
    determinants = []
    if module == "porters_diamond":
        for block in blocks:
            tiers = {_text(item.get("tier")) for item in block.get("items") or []
                     if _text(item.get("provenance")) == "sourced"}
            determinants.append({"label": _text(block.get("label") or block.get("key")),
                                 "tier_a_or_b": bool(tiers & {"A", "B"}),
                                 "outcome": bool(block.get("items"))})
    triangulation = {"sources": len(sources), "pass": len(sources) >= 2}
    if not rows:
        verdict = "Weakly supported"
        reason = "No sourced claim was recorded, so the analysis has no evidence to audit."
    elif module == "porters_diamond" and not outcome_evidenced:
        verdict = "Weakly supported"
        reason = ("No competitiveness outcome evidence was recorded, so the analysis is an "
                  "explanatory hypothesis rather than a demonstrated outcome.")
    elif triangulation["pass"] and not gaps and (coverage is None or coverage["pass"]):
        verdict = "Well-supported"
        reason = ("The claims rest on at least two independent sources, no part is an unqualified "
                  "gap, and the coverage check passes.")
    else:
        verdict = "Partially supported"
        missing = []
        if not triangulation["pass"]:
            missing.append("fewer than two independent sources")
        if gaps:
            missing.append("a part with no citable evidence")
        if coverage is not None and not coverage["pass"]:
            missing.append("fewer than three value-chain areas")
        reason = "The analysis is supported only in part: " + "; ".join(missing) + "."
    return {"rows": rows, "sources": sorted(sources), "gaps": gaps,
            "quantified": quantified, "bias": bias, "contradictions": contradictions,
            "areas": areas, "coverage": coverage,
            "determinants": determinants, "triangulation": triangulation,
            "verdict": verdict, "verdict_reason": reason,
            "columns": writing.get("audit_columns") or []}


def audit_lines(profile, result, report=None, outcome_evidenced=False):
    """The prose beside the audit table: the checks, the gaps and the verdict."""
    report = report or audit(profile, result, outcome_evidenced=outcome_evidenced)
    lines = [
        ("The table records every material claim, its source, the source's tier and recency, "
         "whether it is a fact, inference or judgment, and the strength the product's convention "
         "allows."),
        ("Triangulation: %d independent source(s) support the analysis; two are needed for a "
         "strong conclusion." % report["triangulation"]["sources"]),
        ("Quantification: a quantified figure is %s; a claim without one is capped at Moderate "
         "strength." % ("present" if report["quantified"] else "absent")),
        ("Bias: %s." % ("; ".join(_short(row["claim"], 60) for row in report["bias"])
                        if report["bias"] else
                        "no source is classified as firm or interested-party material")),
        ("Contradictions: %s." % ("; ".join(item["note"] for item in report["contradictions"])
                                  if report["contradictions"] else "none recorded")),
        ("Gaps: %s." % ("; ".join(report["gaps"]) if report["gaps"] else "none recorded")),
        ("Overall verdict: %s. %s" % (report["verdict"], report["verdict_reason"])),
    ]
    coverage = report.get("coverage")
    if coverage is not None:
        lines.insert(2, ("Coverage: evidence comes from %d value-chain area(s) (%s); the guideline "
                         "asks for at least three."
                         % (len(coverage["areas"]), ", ".join(coverage["areas"]) or "none recorded")))
    if report.get("determinants"):
        weak = [row["label"] for row in report["determinants"] if not row["tier_a_or_b"]]
        lines.insert(2, ("Determinant coverage: %s."
                         % ("every determinant has a Tier A or B source" if not weak
                            else "no Tier A or B source for " + "; ".join(weak))))
        lines.insert(3, ("Outcome evidence: %s."
                         % ("recorded" if outcome_evidenced
                            else "not recorded; the analysis is an explanatory hypothesis")))
    status_line = reading_status_line((result or {}).get("blocks") or [])
    if status_line:
        lines.append(status_line)
    conventions = _text(((profile or {}).get("writing") or {}).get("conventions"))
    if conventions:
        lines.append(conventions)
    return lines


def reading_directive(scale, label="Rating"):
    """The instruction one section call needs to return a reading beside its prose."""
    return (" Also return \"reading\": an object with %s (%s), drivers (a list; each driver has "
            "driver, evidence (the zero-based item number, or null for a judgment), type "
            "(F for fact, I for inference, J for judgment, H for a hypothesis) and, where the "
            "payload supplies an `areas` list, one `area` from that list; an H driver must also "
            "carry `test`, the cheapest test that would confirm or reject it), trend (Rising, "
            "Stable or Falling), "
            "trend_reason, profitability_impact, confidence (High, Medium or Low), confidence_reason, "
            "so_what, rationale and contradictions (an optional list of short sentences naming "
            "evidence that conflicts with the reading). The %s is a judgment about this part, not a "
            "fact about a source. Use only the items; do not add a number, name, source or citation. "
            "Return the paragraphs and the reading in one JSON object: "
            "{\"paragraphs\":[\"...\"], \"reading\":{...}}."
            % (label, ", ".join(scale), label.lower()))


def validate_reading(reading, items, unit=None, allowed_names=None,
                     scale=None, label="Rating"):
    """A clean reading, or ``ReadingError`` naming the first thing wrong.

    A rating is a judgment: it must name at least one driver, and every driver
    that is a fact or an inference must point at an accepted item.  A judgment
    driver must not cite an item as if the item said it.  No reading may add a
    number, name, link or citation the items do not carry.
    """
    scale = tuple(scale or RATINGS)
    label = _text(label) or "Rating"
    if not isinstance(reading, dict):
        raise ReadingError("a reading must be an object")
    if not items:
        raise ReadingError("a rating needs at least one accepted item")
    rating = _text(reading.get("rating"))
    if rating not in scale:
        raise ReadingError(label.lower() + " must be one of: " + ", ".join(scale))
    drivers = reading.get("drivers")
    if not isinstance(drivers, list) or not drivers:
        raise ReadingError("a rating needs at least one driver")
    clean_drivers = []
    for index, driver in enumerate(drivers):
        number = index + 1
        if not isinstance(driver, dict):
            raise ReadingError("driver %d must be an object" % number)
        name = _text(driver.get("driver"))
        if not name:
            raise ReadingError("driver %d needs a name" % number)
        evidence = driver.get("evidence")
        if evidence is not None:
            try:
                evidence = int(evidence)
            except (TypeError, ValueError):
                raise ReadingError("driver %d evidence must be an item number" % number)
            if evidence < 0 or evidence >= len(items):
                raise ReadingError("driver %d evidence is outside the accepted items" % number)
        kind = _text(driver.get("type")).upper()
        if kind not in CLAIM_TYPES:
            raise ReadingError("driver %d type must be F, I or J" % number)
        if kind == "J" and evidence is not None:
            raise ReadingError("driver %d is a judgment, so it cannot cite an item as its evidence"
                               % number)
        if kind in ("F", "I") and evidence is None:
            raise ReadingError("driver %d needs evidence for a fact or an inference" % number)
        test = _text(driver.get("test"))
        if kind == "H" and not test:
            raise ReadingError("driver %d is a hypothesis and needs the test that would confirm "
                               "or reject it" % number)
        causal = _text(driver.get("causal"))
        if causal and causal not in CAUSAL:
            raise ReadingError("driver %d causal link must be Yes, Plausible or No" % number)
        clean_drivers.append({
            "driver": name, "evidence": evidence, "type": kind,
            "area": _text(driver.get("area")),
            "bias": _text(driver.get("bias")) or "not classified",
            "causal": causal or "Not assessed",
            "test": test,
        })
    trend = _text(reading.get("trend"))
    if trend not in TRENDS:
        raise ReadingError("trend must be one of: " + ", ".join(TRENDS))
    confidence = _text(reading.get("confidence"))
    if confidence not in CONFIDENCE:
        raise ReadingError("confidence must be one of: " + ", ".join(CONFIDENCE))
    contradictions = reading.get("contradictions")
    clean_contradictions = []
    if contradictions not in (None, ""):
        if not isinstance(contradictions, list):
            raise ReadingError("contradictions must be a list of short sentences")
        for item in contradictions:
            text = _text(item)
            if not text:
                continue
            problem = _invented(text, _blob(items, unit), allowed_names)
            if problem:
                raise ReadingError("a contradiction names a %s that is not in the items" % problem)
            clean_contradictions.append(text)
    out = {"rating": rating, "drivers": clean_drivers, "trend": trend,
           "confidence": confidence, "rating_scale": list(scale),
           "rating_label": label, "contradictions": clean_contradictions}
    for field in ("trend_reason", "profitability_impact", "confidence_reason",
                  "so_what", "rationale"):
        value = _text(reading.get(field))
        if not value:
            raise ReadingError(field + " is required")
        out[field] = value
    blob = _blob(items, unit)
    for field in ("trend_reason", "profitability_impact", "confidence_reason",
                  "so_what", "rationale"):
        problem = _invented(out[field], blob, allowed_names)
        if problem == "number":
            raise ReadingError(field + " names a number that is not in the items")
        if problem == "name":
            raise ReadingError(field + " names a name that is not in the items")
        if problem == "link":
            raise ReadingError(field + " carries a link or citation the items do not carry")
    for driver in out["drivers"]:
        problem = _invented(driver["driver"], blob, allowed_names)
        if problem == "number":
            raise ReadingError("a driver names a number that is not in the items")
        if problem == "name":
            raise ReadingError("a driver names a name that is not in the items")
        if problem == "link":
            raise ReadingError("a driver carries a link or citation the items do not carry")
    return out
