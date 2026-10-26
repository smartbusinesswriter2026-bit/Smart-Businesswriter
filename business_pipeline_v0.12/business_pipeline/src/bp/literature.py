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

def verify_reference(title, doi=None, source=None):
    """Return a Reference. status is 'verified' only when a DOI is provided, it resolves against `source`, and the
    normalized title matches exactly (PROVISIONAL rule pending the manuals). Anything else is 'unverified_user_supplied'.
    A resolved retrieval always carries its audit fields (retrieved_at, response_hash), even when the title then fails to
    match; a reference that never reached a source carries neither. """
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
    return ref
