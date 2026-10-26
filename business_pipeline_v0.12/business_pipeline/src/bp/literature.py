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
        return {"title": data.get("title"), "authors": tuple(a.get("author", {}).get("display_name") for a in data.get("authorships", []) if isinstance(a, dict) and (a.get("author") or {}).get("display_name")),
                "year": str(data["publication_year"]) if data.get("publication_year") is not None else None, "container": src.get("display_name"),
                "retrieved_at": self._clock(), "response_hash": digest(raw)}

def _norm(s): return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

def verify_reference(title, doi=None, source=None, log=None):
    """Return a Reference. status is 'verified' only when a DOI is provided, it resolves against `source`, and the
    normalized title matches exactly (PROVISIONAL rule pending the manuals). Anything else is 'unverified_user_supplied'.
    A resolved retrieval always carries its audit fields (retrieved_at, response_hash), even when the title then fails to
    match; a reference that never reached a source carries neither. When `log` is a path, every resolved retrieval is
    appended to that retrieval log first; if the log cannot be written the call FAILS (fail-closed) rather than
    returning an unaudited result."""
    if not isinstance(title, str) or not title.strip(): raise SourceError("title is required")
    ref = Reference(title=title.strip(), doi=(doi.strip() if isinstance(doi, str) and doi.strip() else None))
    if not ref.doi: return ref
    source = source or CrossrefSource()
    rec = source.resolve(ref.doi)
    if rec is None: return ref                                                  # DOI did not resolve; stays unverified
    ref.source, ref.resolved_title = source.name, (rec.get("title").strip() if rec.get("title") else None)
    ref.authors, ref.year, ref.container = tuple(rec.get("authors") or ()), rec.get("year"), rec.get("container")
    ref.retrieved_at, ref.response_hash = rec.get("retrieved_at"), rec.get("response_hash")
    if _norm(rec.get("title")) == _norm(title):
        ref.status, ref.title = "verified", (rec.get("title") or title).strip()  # canonicalize to the source title
    if log: _append_log(log, _log_record(title.strip(), ref))
    return ref

# ---------- durable retrieval log (B-058; REW manual section 9) ----------
# Every retrieval that reaches a source is appended to a newline-delimited JSON log, together with the audit
# fields, so a citation can be re-checked later and a fabricated audit trail is not possible. The log is
# append-only and local; it is not a shared cache and it does not replace the source.
LOG_FORMAT = "bp-retrieval-log/1"

def default_log_path(): return os.environ.get("BP_RETRIEVAL_LOG") or "retrieval_log.jsonl"

def _log_record(supplied_title, ref):
    return {"format": LOG_FORMAT, "logged_at": utcnow(), "source": ref.source, "doi": ref.doi,
            "status": ref.status, "title_supplied": supplied_title, "title_resolved": ref.resolved_title,
            "authors": list(ref.authors), "year": ref.year, "container": ref.container,
            "retrieved_at": ref.retrieved_at, "response_hash": ref.response_hash}

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

def reverify(entry, source=None):
    """Re-check a logged retrieval against the source now. States: hash_match (same bytes as logged),
    hash_differs (the source served different bytes since) or unresolvable_now (the DOI no longer resolves)."""
    if not entry.get("doi"): return {"doi": None, "state": "no_doi_logged"}
    source = source or CrossrefSource()
    rec = source.resolve(entry["doi"])
    if rec is None: return {"doi": entry["doi"], "state": "unresolvable_now", "logged_hash": entry.get("response_hash"), "logged_at": entry.get("retrieved_at")}
    same = rec.get("response_hash") == entry.get("response_hash")
    return {"doi": entry["doi"], "state": "hash_match" if same else "hash_differs", "logged_hash": entry.get("response_hash"),
            "current_hash": rec.get("response_hash"), "logged_at": entry.get("retrieved_at"), "current_retrieved_at": rec.get("retrieved_at"),
            "title_still_matches": _norm(rec.get("title")) == _norm(entry.get("title_resolved"))}

# ---------- citation formatting (PROVISIONAL layout; REW Q9 still open) ----------
# No institutional citation style has been ratified. Rather than pretend to implement APA/Harvard/MLA, the
# only style is a DECLARED provisional author-date layout, and every formatted citation says so.
CITATION_STYLES = ("provisional",)
CITATION_NOTICE = ("PROVISIONAL citation layout (author-date, title, container, DOI). No institutional citation style has been "
                   "ratified (REW Q9), so this is not an endorsed APA, Harvard or MLA format; author names are printed exactly "
                   "as the source returned them, with no name re-parsing.")

def format_citation(ref, style="provisional"):
    """Format a Reference for display. Never upgrades an unverified reference: the text is prefixed and `verified` is False."""
    if style not in CITATION_STYLES: raise SourceError("unknown citation style; available: " + ", ".join(CITATION_STYLES))
    if ref.status != "verified":
        text = "[unverified user-supplied: not checked against a source] " + (ref.title or "").strip()
        if ref.doi: text += f" (DOI given: {ref.doi}; not confirmed)"
        note = ("The DOI resolved to a different title, so the citation stays unverified." if ref.resolved_title else None)
        return {"style": style, "text": text, "status": ref.status, "verified": False, "notice": CITATION_NOTICE, "note": note}
    authors = "; ".join(ref.authors) if ref.authors else "[no author]"
    year = ref.year or "[n.d.]"
    text = f"{authors} ({year}). {ref.title}. " + (f"{ref.container}. " if ref.container else "")
    text += f"https://doi.org/{ref.doi}" if ref.doi else ""
    return {"style": style, "text": text.strip(), "status": ref.status, "verified": True, "notice": CITATION_NOTICE, "note": None}

