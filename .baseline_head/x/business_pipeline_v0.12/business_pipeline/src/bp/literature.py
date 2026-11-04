"""Research & Evidence Workflow (REW, formerly Build Charter Stage 7) literature-source boundary (decision B-040, PROVISIONAL first slice).

Owner plan: an API-based literature database (public scholarly APIs) while the proprietary database is under construction.
This module only RESOLVES and VERIFIES references; it does not implement the workflow stages. Those are defined as proposals in
docs/RESEARCH_EVIDENCE_WORKFLOW.md (living manual, B-053; owner ratification register R1-R11).

Same rules as the model boundary (llm.py): standard library only, no keys committed, network in the server process,
remote responses treated as untrusted data, fail-closed. Verification rules here are PROVISIONAL placeholders that the
manuals will replace; until then a citation is "verified" only when its DOI resolves AND the title matches exactly.

Retrieval audit (B-054, manual section 9 / Q10): every retrieval that reaches a source records the SHA-256 of the exact
response bytes received and a UTC retrieval timestamp. A reference that never reached a source (no DOI, unresolvable DOI)
records neither, fail-closed. The hash is of the raw bytes, not of a re-serialised object, so it pins what was actually
served at that moment; it is not a promise that the source's metadata is correct."""
import hashlib, json, os, re, urllib.request, urllib.error
from datetime import datetime, timezone
from urllib.parse import quote
from dataclasses import dataclass, field

def utcnow(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def digest(raw): return hashlib.sha256(raw).hexdigest()

class SourceError(Exception): pass

@dataclass
class Reference:
    title: str                                            # user-supplied (canonicalized when verified)
    doi: str | None = None
    authors: tuple = ()
    year: str | None = None
    container: str | None = None
    resolved_title: str | None = None                     # title returned by the source, when the DOI resolved
    status: str = "unverified_user_supplied"              # unverified_user_supplied | verified
    source: str | None = None
    retrieved_at: str | None = None                       # UTC timestamp of the retrieval that resolved the DOI
    response_hash: str | None = None                      # SHA-256 of the exact response bytes received
    # bibliographic fields used by the ratified citation styles (mapped only where the source supplies them)
    authors_structured: tuple = ()                        # ((family, given), ...) when the source supplies both parts
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    publisher: str | None = None
    reference_type: str | None = None                     # source-declared type, e.g. journal-article / book

class Source:
    name = "base"
    def __init__(self, clock=None): self._clock = clock or utcnow
    def resolve(self, doi) -> dict | None: raise NotImplementedError

def _title(msg): return (msg.get("title") or [None])[0]

def _crossref_authors(msg):
    out = []
    for a in msg.get("author", []) or []:
        if isinstance(a, dict):
            n = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if n: out.append(n)
    return out

def _crossref_structured(msg):
    out = []
    for a in msg.get("author", []) or []:
        if isinstance(a, dict) and (a.get("family") or a.get("given")):
            out.append((str(a.get("family") or "").strip(), str(a.get("given") or "").strip()))
    return tuple(out)

def _str_or_none(v):
    if v is None: return None
    s = str(v).strip()
    return s or None

class CrossrefSource(Source):
    """Crossref REST API (no key required for basic metadata). Smoke-tested live against one DOI on 2026-10-21; coverage not yet evaluated."""
    name = "crossref"
    URL = "https://api.crossref.org/works/{doi}"
    def __init__(self, mailto=None, timeout=30, opener=None, clock=None):
        super().__init__(clock); self.mailto = mailto or os.environ.get("BP_CROSSREF_MAILTO"); self.timeout = timeout; self._open = opener
    def resolve(self, doi):
        url = self.URL.format(doi=quote(doi, safe=""))
        req = urllib.request.Request(url, headers={"User-Agent": f"SMART-BUSINESSWRITER/0.29 (mailto:{self.mailto or 'unset'})"})
        try:
            with (self._open or urllib.request.urlopen)(req, timeout=self.timeout) as r: raw = r.read()
            data = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            raise SourceError(f"crossref returned HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e: raise SourceError(f"could not reach crossref: {type(e).__name__}")
        except ValueError: raise SourceError("crossref returned a response that is not JSON")
        msg = data.get("message") if isinstance(data, dict) else None
        if not isinstance(msg, dict): raise SourceError("unexpected crossref response shape")
        year = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        return {"title": _title(msg), "authors": tuple(_crossref_authors(msg)), "year": str(year) if year is not None else None,
                "container": (msg.get("container-title") or [None])[0],
                "authors_structured": _crossref_structured(msg),
                "volume": _str_or_none(msg.get("volume")), "issue": _str_or_none(msg.get("issue")),
                "pages": _str_or_none(msg.get("page")), "publisher": _str_or_none(msg.get("publisher")),
                "reference_type": _str_or_none(msg.get("type")),
                "retrieved_at": self._clock(), "response_hash": digest(raw)}

class OpenAlexSource(Source):
    """OpenAlex (free, no key). Smoke-tested live against one DOI on 2026-10-21; coverage not yet evaluated."""
    name = "openalex"
    URL = "https://api.openalex.org/works/doi:{doi}"
    def __init__(self, timeout=30, opener=None, clock=None):
        super().__init__(clock); self.timeout = timeout; self._open = opener
    def resolve(self, doi):
        url = self.URL.format(doi=doi)
        req = urllib.request.Request(url, headers={"User-Agent": "SMART-BUSINESSWRITER/0.29"})
        try:
            with (self._open or urllib.request.urlopen)(req, timeout=self.timeout) as r: raw = r.read()
            data = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            raise SourceError(f"openalex returned HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e: raise SourceError(f"could not reach openalex: {type(e).__name__}")
        except ValueError: raise SourceError("openalex returned a response that is not JSON")
        if not isinstance(data, dict): raise SourceError("unexpected openalex response shape")
        src = (data.get("primary_location") or {}).get("source") or {}
        biblio = data.get("biblio") or {}
        first, last = _str_or_none(biblio.get("first_page")), _str_or_none(biblio.get("last_page"))
        pages = None
        if first and last and first != last: pages = f"{first}-{last}"
        elif first: pages = first
        oa_type = _str_or_none(data.get("type"))
        ref_type = {"article": "journal-article", "book": "book", "preprint": "posted-content", "review": "journal-article"}.get((oa_type or "").lower(), oa_type)
        return {"title": data.get("title"), "authors": tuple(a.get("author", {}).get("display_name") for a in data.get("authorships", []) if isinstance(a, dict) and (a.get("author") or {}).get("display_name")),
                "year": str(data["publication_year"]) if data.get("publication_year") is not None else None, "container": src.get("display_name"),
                "authors_structured": (),
                "volume": _str_or_none(biblio.get("volume")), "issue": _str_or_none(biblio.get("issue")),
                "pages": pages, "publisher": _str_or_none(src.get("host_organization_name")), "reference_type": ref_type,
                "retrieved_at": self._clock(), "response_hash": digest(raw)}

def _norm(s): return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

# Source priority and failover policy (B-064): Crossref first, OpenAlex second. A source error at one is not
# silently swallowed — the attempt is recorded and the next source is tried; if every source errors the call
# fails closed rather than calling the DOI "unverified".
def default_sources(): return (CrossrefSource(), OpenAlexSource())

def _resolve_with_failover(doi, sources):
    """Try each source in order. Returns (winning source or None, record or None, attempts)."""
    attempts = []
    for s in sources:
        try: rec = s.resolve(doi)
        except SourceError as e:
            attempts.append({"source": s.name, "outcome": "error", "detail": str(e)}); continue
        if rec is None:
            attempts.append({"source": s.name, "outcome": "not_found"}); continue
        attempts.append({"source": s.name, "outcome": "resolved"})
        return s, rec, attempts
    return None, None, attempts

def verify_reference(title, doi=None, source=None, sources=None, log=None):
    """Return a Reference. status is 'verified' only when a DOI is provided, it resolves against a source, and the
    normalized title matches exactly (PROVISIONAL rule pending the manuals). Anything else is 'unverified_user_supplied'.
    A resolved retrieval always carries its audit fields (retrieved_at, response_hash), even when the title then fails to
    match; a reference that never reached a source carries neither. `source` pins one source; `sources` tries a list in
    order with failover (B-064) and records every attempt. When `log` is a path, every resolved retrieval is appended to
    that retrieval log first; if the log cannot be written the call FAILS (fail-closed) rather than returning an
    unaudited result."""
    if not isinstance(title, str) or not title.strip(): raise SourceError("title is required")
    ref = Reference(title=title.strip(), doi=(doi.strip() if isinstance(doi, str) and doi.strip() else None))
    if not ref.doi: return ref
    attempts = []
    if sources:
        source, rec, attempts = _resolve_with_failover(ref.doi, tuple(sources))
        if rec is None and attempts and all(a["outcome"] == "error" for a in attempts):
            raise SourceError("every retrieval source failed: " + "; ".join(f"{a['source']}: {a['detail']}" for a in attempts))
    else:
        source = source or CrossrefSource()
        rec = source.resolve(ref.doi)
    if rec is None: return ref                                                  # DOI did not resolve; stays unverified
    ref.source, ref.resolved_title = source.name, (rec.get("title").strip() if rec.get("title") else None)
    ref.authors, ref.year, ref.container = tuple(rec.get("authors") or ()), rec.get("year"), rec.get("container")
    ref.authors_structured = tuple(rec.get("authors_structured") or ())
    ref.volume, ref.issue, ref.pages = rec.get("volume"), rec.get("issue"), rec.get("pages")
    ref.publisher, ref.reference_type = rec.get("publisher"), rec.get("reference_type")
    ref.retrieved_at, ref.response_hash = rec.get("retrieved_at"), rec.get("response_hash")
    if _norm(rec.get("title")) == _norm(title):
        ref.status, ref.title = "verified", (rec.get("title") or title).strip()  # canonicalize to the source title
    if log: _append_log(log, _log_record(title.strip(), ref, attempts))
    return ref

# ---------- durable retrieval log (B-058; REW manual section 9) ----------
# Every retrieval that reaches a source is appended to a newline-delimited JSON log, together with the audit
# fields, so a citation can be re-checked later and a fabricated audit trail is not possible. The log is
# append-only and local; it is not a shared cache and it does not replace the source.
LOG_FORMAT = "bp-retrieval-log/1"

def default_log_path(): return os.environ.get("BP_RETRIEVAL_LOG") or "retrieval_log.jsonl"

def _log_record(supplied_title, ref, attempts=None):
    return {"format": LOG_FORMAT, "logged_at": utcnow(), "source": ref.source, "doi": ref.doi,
            "status": ref.status, "title_supplied": supplied_title, "title_resolved": ref.resolved_title,
            "authors": list(ref.authors), "year": ref.year, "container": ref.container,
            "retrieved_at": ref.retrieved_at, "response_hash": ref.response_hash,
            "attempts": list(attempts or [])}

def _append_log(path, rec):
    """Append one record as a single line and flush to disk. Any failure raises: an unlogged retrieval is refused."""
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush(); os.fsync(f.fileno())
    except (OSError, TypeError, ValueError) as e:
        raise SourceError(f"could not record the retrieval audit in {path!r}: {type(e).__name__}")

def read_log(path=None, limit=50):
    """Return up to `limit` most recent entries (oldest first). A missing log is empty; a corrupt log raises."""
    path = path or default_log_path()
    try:
        with open(path, encoding="utf-8") as f: lines = f.read().splitlines()
    except FileNotFoundError: return []
    except OSError as e: raise SourceError(f"could not read the retrieval log {path!r}: {type(e).__name__}")
    out = []
    for n, line in enumerate(lines, 1):
        if not line.strip(): continue
        try: rec = json.loads(line)
        except ValueError: raise SourceError(f"retrieval log {path!r} is corrupt at line {n}")
        if not isinstance(rec, dict) or rec.get("format") != LOG_FORMAT: raise SourceError(f"retrieval log {path!r} has an unknown record format at line {n}")
        out.append(rec)
    return out[-limit:] if limit else out

def reverify(entry, source=None, sources=None):
    """Re-check a logged retrieval against the source now. States: hash_match (same bytes as logged),
    hash_differs (the source served different bytes since) or unresolvable_now (the DOI no longer resolves).
    With `sources`, the same failover order as verification is used."""
    if not entry.get("doi"): return {"doi": None, "state": "no_doi_logged"}
    attempts = []
    if sources:
        source, rec, attempts = _resolve_with_failover(entry["doi"], tuple(sources))
        if rec is None and attempts and all(a["outcome"] == "error" for a in attempts):
            raise SourceError("every retrieval source failed: " + "; ".join(f"{a['source']}: {a['detail']}" for a in attempts))
    else:
        source = source or CrossrefSource(); rec = source.resolve(entry["doi"])
    if rec is None: return {"doi": entry["doi"], "state": "unresolvable_now", "logged_hash": entry.get("response_hash"), "logged_at": entry.get("retrieved_at"), "attempts": attempts}
    same = rec.get("response_hash") == entry.get("response_hash")
    return {"doi": entry["doi"], "state": "hash_match" if same else "hash_differs", "logged_hash": entry.get("response_hash"),
            "current_hash": rec.get("response_hash"), "logged_at": entry.get("retrieved_at"), "current_retrieved_at": rec.get("retrieved_at"),
            "checked_with": source.name, "attempts": attempts,
            "title_still_matches": _norm(rec.get("title")) == _norm(entry.get("title_resolved"))}

def drift_check(path=None, limit=20, sources=None):
    """Re-verify the most recent logged retrievals and summarize what changed (B-064). This is a manual sweep:
    it performs network calls, reports hash_match / hash_differs / unresolvable_now / unreachable per entry, and
    never rewrites the log."""
    entries = read_log(path, limit)
    srcs = tuple(sources) if sources else default_sources()
    results = []
    for e in entries:
        if not e.get("doi"):
            results.append({"doi": None, "state": "no_doi_logged", "title_supplied": e.get("title_supplied")}); continue
        try: r = reverify(e, sources=srcs)
        except SourceError as ex:
            r = {"doi": e["doi"], "state": "unreachable", "detail": str(ex), "title_supplied": e.get("title_supplied")}
        r["title_supplied"] = e.get("title_supplied"); results.append(r)
    summary = {"checked": len(results),
               "hash_match": sum(1 for r in results if r["state"] == "hash_match"),
               "hash_differs": [r["doi"] for r in results if r["state"] == "hash_differs"],
               "unresolvable_now": [r["doi"] for r in results if r["state"] == "unresolvable_now"],
               "unreachable": [r["doi"] for r in results if r["state"] == "unreachable"],
               "notice": "Manual drift sweep over the local retrieval log. A hash_match means the source served identical bytes; hash_differs means it changed since it was logged and the citation must be re-checked by a person; the log is never rewritten."}
    return {**summary, "results": results}


# ---------- citation formatting: APA 7 and Harvard (Cite Them Right) — ratified by the owner (B-059) ----------
# The owner ratified two styles. What is formatted is the metadata the source actually returned: authors are
# inverted only when the source supplies family and given names; titles are printed as returned (no sentence-case
# rewriting); plain text has no italics. Those limits are declared in CITATION_NOTICES rather than papered over.
CITATION_STYLES = ("apa", "harvard")
CITATION_NOTICES = {
    "apa": ("APA 7 (author-date), rendered in plain text: italics are not representable, titles are printed as the source returned "
            "them, and author names are inverted only when the source supplies family and given names."),
    "harvard": ("Harvard (Cite Them Right), rendered in plain text: italics are not representable, titles are printed as the source "
                "returns them, and author names are inverted only when the source supplies family and given names."),
}
_ARTICLE_TYPES = {"journal-article", "proceedings-article", "posted-content", "article"}
_BOOK_TYPES = {"book", "monograph", "edited-book", "reference-book"}

def _initials(given):
    return " ".join(f"{p[0]}." for p in re.split(r"[\s\-]+", (given or "").strip()) if p)

def _en_dash(pages):
    return re.sub(r"^(\d+)-(\d+)$", r"\1–\2", (pages or "").strip())

def _author_names(ref, style):
    """Return (text, note). Note is non-None only when the source could not provide invertible names."""
    if ref.authors_structured:
        pairs = [(f.strip(), _initials(g)) for f, g in ref.authors_structured]
        names = [f"{fam}, {ini}".strip().rstrip(",") if ini else fam for fam, ini in pairs]
        if len(names) > 20: names = names[:19] + ["..."] + names[-1:]
        if len(names) == 1: return (names[0], None)
        if style == "apa": return (", ".join(names[:-1]) + ", & " + names[-1], None)
        return (", ".join(names[:-1]) + " and " + names[-1], None)
    if ref.authors:
        if len(ref.authors) == 1: joined = ref.authors[0]
        elif style == "apa": joined = ", ".join(ref.authors[:-1]) + ", & " + ref.authors[-1]
        else: joined = ", ".join(ref.authors[:-1]) + " and " + ref.authors[-1]
        return (joined, "Author names were not inverted for this source (it returned display names only); check the author formatting before use.")
    return ("[no author]", None)

def _year_text(ref): return ref.year or "[n.d.]"

def _article_text(ref, names, style):
    vol, iss, pages, year, doi = ref.volume, ref.issue, _en_dash(ref.pages), _year_text(ref), ref.doi
    if style == "apa":
        loc = ""
        if vol: loc += f", {vol}" + (f"({iss})" if iss else "")
        if pages: loc += f", {pages}"
        text = f"{names} ({year}). {ref.title}."
        if ref.container: text += f" {ref.container}{loc}."
        elif loc: text += f"{loc}."
        if doi: text += f" https://doi.org/{doi}"
        return text
    src = ref.container or ""
    vol_iss = (vol or "") + (f"({iss})" if vol and iss else (iss or ""))
    bits = ", ".join(x for x in (vol_iss, f"pp. {pages}" if pages else "") if x)
    text = f"{names} ({year}) '{ref.title}'"
    if src: text += f", {src}"
    if bits: text += f", {bits}"
    text += "."
    if doi: text += f" doi: {doi}."
    return text

def _book_text(ref, names, style):
    year = _year_text(ref)
    if style == "apa":
        parts = [f"{names} ({year}).", f"{ref.title}."]
        if ref.publisher: parts.append(f"{ref.publisher}.")
        if ref.doi: parts.append(f"https://doi.org/{ref.doi}")
        return " ".join(parts)
    text = f"{names} ({year}) {ref.title}."
    if ref.publisher: text += f" {ref.publisher}."
    if ref.doi: text += f" doi: {ref.doi}."
    return text

def format_citation(ref, style="apa"):
    """Format a Reference for display in a RATIFIED style (apa or harvard). An unverified reference is never
    formatted as if checked: the text is prefixed and `verified` is False whatever the requested style."""
    if style not in CITATION_STYLES: raise SourceError("unknown citation style; available: " + ", ".join(CITATION_STYLES))
    notice, note = CITATION_NOTICES[style], None
    if ref.status != "verified":
        text = "[unverified user-supplied: not checked against a source] " + (ref.title or "").strip()
        if ref.doi: text += f" (DOI given: {ref.doi}; not confirmed)"
        if ref.resolved_title: note = "The DOI resolved to a different title, so the citation stays unverified."
        return {"style": style, "text": text, "status": ref.status, "verified": False, "notice": notice, "note": note}
    names, name_note = _author_names(ref, style)
    if name_note: note = name_note
    kind = (ref.reference_type or "").lower()
    if kind in _ARTICLE_TYPES or (not kind and ref.container):
        return {"style": style, "text": _article_text(ref, names, style), "status": ref.status, "verified": True, "notice": notice, "note": note, "layout": "journal-article"}
    if kind in _BOOK_TYPES:
        return {"style": style, "text": _book_text(ref, names, style), "status": ref.status, "verified": True, "notice": notice, "note": note, "layout": "book"}
    text = _book_text(ref, names, style)
    return {"style": style, "text": text, "status": ref.status, "verified": True, "notice": notice,
            "note": ((note + " ") if note else "") + f"Generic layout: only journal articles and books are fully styled (source type: {ref.reference_type or 'not supplied'}).", "layout": "other"}

if __name__ == "__main__":
    import sys as _sys
    _a = _sys.argv[1:]
    if not _a or _a[0] != "drift":
        print("usage: python -m bp.literature drift [log_path] [limit]"); raise SystemExit(2)
    _limit = int(_a[2]) if len(_a) > 2 else 20
    print(json.dumps(drift_check(_a[1] if len(_a) > 1 else None, _limit), indent=2, ensure_ascii=False))

