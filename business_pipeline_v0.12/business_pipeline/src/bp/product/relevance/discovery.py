"""RRA Stage S1b — URL discovery.

Finds the pages the RRA should read: curriculum pages, core-course lists,
assessment briefs, AI-use policies, standards pages.

The search is deterministic and site-filtered (the vetted `sources.search_web`
with the RRA allowlist as the site list).  The model is used only to rank the
candidates and to propose a query when the search returns nothing — it never
invents a URL that was not returned by the search.
"""
import json
import os
from pathlib import Path

from . import model as _model
from .s1_scout import _is_allowed, _domain_of

#: What the RRA looks for, per school or body.
QUERY_TEMPLATES = [
    "{name} MBA curriculum core courses",
    "{name} MBA assessment format thesis dissertation capstone",
    "{name} assessment policy generative AI business school",
]

#: A framework is evidenced in a **course catalogue**, not in a core-course
#: list: a core list names subjects ("Strategy", "Finance") and a framework
#: appears in the course that teaches it.  Phase 1 proved the difference — the
#: core lists produced zero hits for every framework, including the controls.
CATALOGUE_TEMPLATES = [
    "{name} course catalogue",
    "{name} course descriptions catalogue",
    "{name} courses list syllabus",
    "{name} programme course list",
]

BODY_QUERIES = {
    "AACSB": ["AACSB global standards 2026 assurance of learning"],
    "GMAC": ["GMAC future of graduate management education report"],
    "IFRS Foundation (IASB and ISSB)": ["IFRS standards amendments issued"],
    "FASB": ["FASB accounting standards updates issued"],
    "EFRAG and the European Commission": ["ESRS sustainability reporting standards revisions"],
    "EFMD (EQUIS)": ["EFMD EQUIS accreditation standards"],
    "AMBA and BGA": ["AMBA accreditation standards MBA"],
    "CFA Institute": ["CFA Institute curriculum and standards"],
    "PMI": ["PMI standards project management"],
    "CIPD": ["CIPD standards professional development"],
}


def _repo_root():
    return Path(__file__).resolve().parents[4]


def _allowlist_sites(allowlist, domains=None):
    """Turn the allowlist into the site list the vetted search understands.

    The search adapter reads `domain`, `label`, `region` and `tier`, where
    `tier` is one of official / data / research / news — **not** the evidence
    tier (T1/T2/T3), which is decided separately by the reader.  When
    `domains` is given, only those hosts are searched, so one school's pages
    are looked for on that school's own site.
    """
    wanted = None
    if domains is not None:
        wanted = {str(d).lower().strip().lstrip(".") for d in domains if d}
    sites = []
    for entry in (allowlist or {}).get("allowed", []) or []:
        domain = str(entry.get("domain", "")).strip()
        if not domain:
            continue
        if wanted is not None:
            host = domain.lower().strip()
            # The registry may name a subdomain (gsb.stanford.edu) where the
            # allowlist names the host (stanford.edu).  Either may be the
            # parent of the other.
            match = False
            for want in wanted:
                if (host == want or host.endswith("." + want)
                        or want.endswith("." + host)):
                    match = True
                    break
            if not match:
                continue
        kind = str(entry.get("type", "research"))
        search_tier = {
            "school": "official",
            "accreditor": "official",
            "standard-setter": "official",
            "regulator": "official",
            "research": "research",
            "trade-press": "news",
        }.get(kind, "research")
        sites.append({
            "id": domain,
            "domain": domain,
            "label": entry.get("label") or domain,
            "name": entry.get("label") or domain,
            "region": entry.get("region", "Global"),
            "tier": search_tier,
            "evidence_tier": entry.get("tier", "T3"),
            "type": kind,
        })
    return sites


def _school_domain(name, school_list, allowlist):
    """The domain a school's pages live on, from the registries."""
    for region, items in ((school_list or {}).get("regions", {}) or {}).items():
        for item in (items or []):
            if item.get("name") == name and item.get("domain"):
                return item["domain"]
    for entry in ((allowlist or {}).get("allowed", []) or []):
        label = str(entry.get("label") or "")
        if label and label.lower() == str(name).lower() and entry.get("domain"):
            return entry["domain"]
    return ""


#: How many model "try a different query" calls one sweep may spend.
#: The model fallback is a *proposal*, not a requirement: when a site's search
#: returns nothing, one better query may find the page — but asking the model
#: once per school in the frame turned a three-minute sweep into a
#: twenty-minute one, for a handful of extra URLs.  The budget is spent on the
#: first schools that need it and reported either way.
DEFAULT_QUERY_FALLBACK_BUDGET = 8

#: How many **searches** one sweep may make.  The search provider
#: rate-limits: a sweep that asks every question of every school runs into
#: HTTP 429 and returns nothing, which looks like a finding and is not one.
#: The sweep stops at its budget and says so.
DEFAULT_SEARCH_BUDGET = 120

#: The order the RRA searches in.  Brave and Firecrawl are cheap and fast;
#: `opengo` is the owner's backup — the OpenCode Go gateway running DeepSeek
#: V4.1 Flash with its websearch tool — and it answers when the other two
#: rate-limit.  Override with BP_RELEVANCE_SEARCH_ORDER.
DEFAULT_SEARCH_ORDER = "brave,firecrawl,opengo"


def search_provider_order():
    """The providers the RRA searches in, in order.

    The order comes from the owner's **switches** (`ops_switches`): a
    provider that is switched off leaves the chain.
    """
    try:
        from .. import ops_switches as _switches
        order = _switches.search_order()
        if order:
            return list(order)
    except Exception:
        pass
    return [name.strip().lower() for name in DEFAULT_SEARCH_ORDER.split(",") if name.strip()]


def _use_opengo():
    """May the RRA use the OpenCode Go websearch as its search backup?"""
    return os.environ.get("BP_RELEVANCE_USE_OPENGO", "1") != "0"


def _opengo_timeout():
    """How long the headless OpenCode session may take."""
    try:
        return int(os.environ.get("BP_RELEVANCE_OPENGO_TIMEOUT", "60"))
    except (TypeError, ValueError):
        return 60


def _opengo_model():
    """The model the headless OpenCode session runs.

    The RRA's discovery model by default: the search is a research task, not
    prose, and the discovery stage is where the model proposes a query.
    """
    return (os.environ.get("BP_RELEVANCE_DISCOVERY_MODEL")
            or os.environ.get("BP_RELEVANCE_MODEL")
            or os.environ.get("BP_LLM_MODEL") or "")


class _Budget(object):
    """A small counter the discovery passes share.

    It bounds two things: the model "try another query" calls, and the
    **searches** themselves.  The search provider rate-limits — a sweep that
    asks every question of every school runs into HTTP 429 and comes back with
    nothing, which looks like a finding and is not one.  A sweep that stops
    at its budget says so.
    """

    def __init__(self, limit, query_limit=None):
        self.limit = limit
        self.query_limit = query_limit
        self.used = 0
        self.queries = 0
        self.query_stopped = False

    def take(self):
        if self.limit is None or self.used >= self.limit:
            return False
        self.used += 1
        return True

    def take_query(self):
        """Is there a search left in the budget?"""
        if self.query_limit is None:
            self.queries += 1
            return True
        if self.queries >= self.query_limit:
            self.query_stopped = True
            return False
        self.queries += 1
        return True


def ensure_web_credentials():
    """Load the search credentials the RRA needs, from the product's own .env.

    The paper's web layer expects its credentials exported; the RRA runs in
    its own lane and needs them too.  The loader reads a fixed allowlist,
    never overrides a value that is already set and never prints one.

    Returns the names it loaded (never the values).
    """
    try:
        from .. import source_env as _source_env
        report = _source_env.load_web_credentials()
        return list(report.get("loaded") or [])
    except Exception:
        return []


def _search(query, sites, limit=8, budget=None):
    """Run the vetted search.  Returns (results, error).

    **The provider chain.**  The search provider rate-limits — Brave and
    Firecrawl both answer HTTP 429 once a sweep has asked enough — and a
    sweep that keeps asking comes back with nothing, which looks like a
    finding and is not one.  The RRA therefore names its own order and lets
    the product's `sources.search_web` fall through it:

        brave -> firecrawl -> opengo (DeepSeek V4.1 Flash through OpenCode Go)

    The `opengo` leg is the owner's backup: the OpenCode Go gateway running
    DeepSeek V4.1 Flash with its websearch tool.  It is enabled **for the
    RRA's own calls only** (`BP_RELEVANCE_USE_OPENGO`, on by default), so the
    product's own web layer keeps its own cost switches untouched.

    The search budget is charged here, because a provider that refuses is not
    the same as a provider that answers.
    """
    if budget is not None and not budget.take_query():
        return [], "the search budget for this sweep is spent"
    try:
        from .. import sources as _sources
    except Exception as error:
        return [], "search module unavailable: %s" % str(error)[:160]

    order = search_provider_order()
    saved = os.environ.get("BP_OPENGO_WEBSEARCH")
    saved_timeout = os.environ.get("BP_OPENGO_TIMEOUT")
    saved_model = os.environ.get("BP_LLM_MODEL")
    try:
        if "opengo" in order and _use_opengo():
            os.environ["BP_OPENGO_WEBSEARCH"] = "1"
            # The websearch tool needs longer than the paper path allows: it
            # is a headless model session that must finish its tool call.
            os.environ.setdefault("BP_OPENGO_TIMEOUT", str(_opengo_timeout()))
            model = _opengo_model()
            if model:
                os.environ["BP_LLM_MODEL"] = model
        payload = _sources.search_web(query, limit=limit, sites=sites,
                                      providers=order or None, fast=False)
    except Exception as error:
        return [], "search failed: %s" % str(error)[:160]
    finally:
        for name, value in (("BP_OPENGO_WEBSEARCH", saved),
                            ("BP_OPENGO_TIMEOUT", saved_timeout),
                            ("BP_LLM_MODEL", saved_model)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    results = payload.get("results") or []
    if not results:
        attempts = payload.get("attempts") or []
        detail = "; ".join("%s: %s" % (a.get("provider"), a.get("error") or a.get("skipped"))
                           for a in attempts if isinstance(a, dict))
        return [], ("no result from %s" % order if not detail
                    else "no result from %s (%s)" % (order, detail))
    return results, ""


def _allowed_results(results, allowlist):
    """Keep only results whose domain is on the allowlist and not blocked."""
    kept = []
    for item in results or []:
        url = item.get("url", "")
        domain = _domain_of(url)
        ok, _reason = _is_allowed(domain, allowlist)
        if ok and url not in [k.get("url") for k in kept]:
            kept.append(item)
    return kept


def discover_for_school(name, allowlist=None, limit=6, use_model=True, school_list=None,
                        budget=None):
    """Discover URLs for one school or body.  Returns (urls, notes).

    The search is filtered to that school's own domain, so the results are the
    school's own pages rather than a general web answer about it.  When the
    search returns nothing the model may propose one better query — never a
    URL — and only while the sweep's fallback budget lasts.
    """
    allowlist = allowlist if allowlist is not None else {}
    domain = _school_domain(name, school_list, allowlist)
    sites = _allowlist_sites(allowlist, domains=[domain] if domain else None)
    if not sites:
        return [], ["no allowlisted domain for %s — nothing may be searched" % name]

    urls = []
    notes = []
    queries = BODY_QUERIES.get(name) or [t.format(name=name) for t in QUERY_TEMPLATES]

    for query in queries:
        results, err = _search(query, sites, limit=limit, budget=budget)
        if err:
            notes.append("search error for %r: %s" % (query, err))
            continue
        allowed = _allowed_results(results, allowlist)
        for item in allowed:
            url = item.get("url", "")
            if url and url not in urls:
                urls.append(url)
        if not allowed and results:
            notes.append("%r: %d result(s) but none on the allowlist" % (query, len(results)))

    if not urls and use_model:
        if budget is None or budget.take():
            # The model may propose a query, never a URL.
            proposal = _propose_query(name, notes)
            if proposal:
                notes.append("model proposed query %r" % proposal)
                results, err = _search(proposal, sites, limit=limit)
                if not err:
                    for item in _allowed_results(results, allowlist):
                        url = item.get("url", "")
                        if url and url not in urls:
                            urls.append(url)
        else:
            notes.append("no query fallback left for %s" % name)

    return urls[:limit * 2], notes


def _propose_query(name, notes):
    """Ask the model for one better search query.  Returns a query string or ''."""
    system = (
        "You write one web search query for a research agent. "
        "Rules: name the institution, name what is wanted (curriculum, core courses, "
        "assessment policy, standards), use no site: operator, no quotes, no punctuation "
        "that is not a word. Answer with the query text only. "
        "If you cannot suggest anything better, answer with an empty string."
    )
    user = "Institution: %s\nSearch problems so far:\n%s\nQuery:" % (
        name, "\n".join(notes[:5]) or "(the search returned nothing)")
    text, _record, err = _model.call(system, user, task="relevance-discovery-query")
    if err:
        return ""
    candidate = " ".join(str(text or "").split())[:160].strip()
    if not candidate or len(candidate) < 8:
        return ""
    if candidate.lower().startswith("query:"):
        candidate = candidate[6:].strip()
    return candidate


def discover_urls(school_list, allowlist=None, limit=6, use_model=True, progress=None,
                  fallback_budget=None, budget=None):
    """Discover URLs for every school and body in the sampling frame.

    Returns (urls, notes, per_school).  `progress` is an optional callable
    called with (name, count) so a long run can report itself.
    `fallback_budget` bounds how many model "try another query" calls the
    sweep may spend; `budget` is an existing budget to share with a second
    pass (the catalogue pass runs after this one).
    """
    urls = []
    notes = []
    per_school = []
    seen = set()
    if budget is None:
        budget = _Budget(DEFAULT_QUERY_FALLBACK_BUDGET
                         if fallback_budget is None else fallback_budget)

    ensure_web_credentials()

    entries = []
    regions = (school_list or {}).get("regions", {}) or {}
    for region, items in regions.items():
        for item in (items or []):
            name = item.get("name", "")
            if name:
                entries.append(name)
    for body in (school_list or {}).get("bodies_to_watch", []) or []:
        if isinstance(body, dict):
            name = body.get("name", "")
        else:
            name = str(body)
        if name:
            entries.append(name)

    for name in entries:
        found, found_notes = discover_for_school(name, allowlist=allowlist,
                                                 limit=limit, use_model=use_model,
                                                 school_list=school_list,
                                                 budget=budget)
        new = [u for u in found if u not in seen]
        for u in new:
            seen.add(u)
            urls.append(u)
        per_school.append({"name": name, "urls": new, "count": len(new)})
        notes.extend(found_notes)
        if progress is not None:
            try:
                progress(name, len(new))
            except Exception:
                pass

    return urls, notes, per_school


def discover_catalogues(school_list, allowlist=None, limit=4, use_model=True, progress=None,
                        fallback_budget=None, budget=None):
    """Find each school's **course catalogue** pages.

    These are the pages that name a framework in the course that teaches it.
    The core-course list is a different page type and cannot answer the
    framework question; Phase 1 measured that (zero hits for every framework,
    including the controls).
    """
    urls = []
    notes = []
    per_school = []
    seen = set()
    if budget is None:
        budget = _Budget(DEFAULT_QUERY_FALLBACK_BUDGET
                         if fallback_budget is None else fallback_budget)

    ensure_web_credentials()

    entries = []
    for region, items in ((school_list or {}).get("regions", {}) or {}).items():
        for item in (items or []):
            name = item.get("name", "")
            if name:
                entries.append(name)
    for body in (school_list or {}).get("bodies_to_watch", []) or []:
        if isinstance(body, dict):
            name = body.get("name", "")
        else:
            name = str(body)
        if name:
            entries.append(name)

    for name in entries:
        found, found_notes = _discover(name, allowlist, limit, use_model,
                                       school_list, CATALOGUE_TEMPLATES, budget)
        new = [u for u in found if u not in seen]
        for u in new:
            seen.add(u)
            urls.append(u)
        per_school.append({"name": name, "urls": new, "count": len(new)})
        notes.extend(found_notes)
        if progress is not None:
            try:
                progress(name, len(new))
            except Exception:
                pass

    return urls, notes, per_school


def _discover(name, allowlist, limit, use_model, school_list, templates, budget=None):
    """Run one discovery pass with a given query template set."""
    allowlist = allowlist if allowlist is not None else {}
    domain = _school_domain(name, school_list, allowlist)
    sites = _allowlist_sites(allowlist, domains=[domain] if domain else None)
    if not sites:
        return [], ["no allowlisted domain for %s — nothing may be searched" % name]

    urls = []
    notes = []
    queries = BODY_QUERIES.get(name) or [t.format(name=name) for t in templates]

    for query in queries:
        results, err = _search(query, sites, limit=limit, budget=budget)
        if err:
            notes.append("search error for %r: %s" % (query, err))
            continue
        allowed = _allowed_results(results, allowlist)
        for item in allowed:
            url = item.get("url", "")
            if url and url not in urls:
                urls.append(url)
        if not allowed and results:
            notes.append("%r: %d result(s) but none on the allowlist" % (query, len(results)))

    if not urls and use_model:
        if budget is None or budget.take():
            proposal = _propose_query(name, notes)
            if proposal:
                notes.append("model proposed query %r" % proposal)
                results, err = _search(proposal, sites, limit=limit)
                if not err:
                    for item in _allowed_results(results, allowlist):
                        url = item.get("url", "")
                        if url and url not in urls:
                            urls.append(url)
        else:
            notes.append("no query fallback left for %s" % name)

    return urls[:limit * 2], notes


def discover_for_topic(topic_label, school, allowlist=None, school_list=None,
                       limit=4, use_model=True, budget=None):
    """Find the pages of one school that name one topic.

    The Phase 1 research asked, per school and per framework, the question
    that works: *does this school publish a page that names this framework?*
    A generic "curriculum core courses" search finds the core-course list,
    which names **subjects**; only a search carrying the framework's own name
    finds the course that teaches it.  The RRA learned this the hard way: a
    sweep that searched generically read 347 pages from 66 hosts and its
    controls found none of the frameworks the system already has.

    Returns (urls, notes).
    """
    allowlist = allowlist if allowlist is not None else {}
    name = topic_label.get("label", "") if isinstance(topic_label, dict) else str(topic_label)
    school_name = school.get("name", "") if isinstance(school, dict) else str(school)
    domain = school.get("domain", "") if isinstance(school, dict) else ""
    if not domain:
        domain = _school_domain(school_name, school_list, allowlist)
    sites = _allowlist_sites(allowlist, domains=[domain] if domain else None)
    if not sites:
        return [], ["no allowlisted domain for %s" % school_name]

    # The bare topic name reads better in a query than the full label
    # ("OKR (Objectives and Key Results)").
    query_name = name.split("(")[0].strip() or name
    queries = ["%s %s course" % (school_name, query_name),
               "%s %s" % (school_name, query_name)]

    urls = []
    notes = []
    for query in queries:
        results, err = _search(query, sites, limit=limit, budget=budget)
        if err:
            notes.append("search error for %r: %s" % (query, err))
            continue
        for item in _allowed_results(results, allowlist):
            url = item.get("url", "")
            if not url or url in urls:
                continue
            # A site-restricted query returns the school's **home page** first
            # for almost every topic, and a home page names nothing.  Only a
            # page with a path can carry a course description.
            if not _has_content_path(url):
                continue
            urls.append(url)
    return urls[:limit * 2], notes


def _has_content_path(url):
    """Does a URL have a path that could carry content?"""
    from urllib.parse import urlparse
    path = urlparse(str(url or "")).path or ""
    path = path.strip("/")
    if not path:
        return False
    if path in ("index.html", "index.htm", "index.php"):
        return False
    return True


def discover_topics(school_list, taxonomy, allowlist=None, limit=3, use_model=True,
                    progress=None, max_schools=None, budget=None):
    """Find, for each framework topic, the pages of each school that name it.

    Returns (urls, notes, per_topic).  This is the question the Phase 1
    research asked and the one that works.
    """
    urls = []
    notes = []
    per_topic = []
    seen = set()

    ensure_web_credentials()

    schools = []
    for region, items in ((school_list or {}).get("regions", {}) or {}).items():
        for item in (items or []):
            if item.get("domain"):
                schools.append({"name": item.get("name", ""),
                                "domain": item.get("domain", ""),
                                "region": region})
    if max_schools:
        schools = schools[:max_schools]

    topics = []
    for topic in (taxonomy.get("topics", []) if isinstance(taxonomy, dict) else []):
        if topic.get("evidence_page") == "course_catalogue":
            topics.append(topic)

    for topic in topics:
        found_topic = []
        for school in schools:
            found, found_notes = discover_for_topic(
                topic, school, allowlist=allowlist, school_list=school_list,
                limit=limit, use_model=use_model, budget=budget)
            for url in found:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
                    found_topic.append(url)
            notes.extend(found_notes)
        per_topic.append({"topic": topic.get("label", ""),
                          "topic_id": topic.get("id", ""),
                          "urls": found_topic, "count": len(found_topic)})
        if progress is not None:
            try:
                progress(topic.get("label", ""), len(found_topic))
            except Exception:
                pass

    return urls, notes, per_topic


def save_discovered(path=None, urls=None, notes=None, per_school=None):
    """Write the discovered URLs to qa/relevance/discovered_urls.json."""
    target = Path(path) if path else (_repo_root() / "qa" / "relevance" / "discovered_urls.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": "bp-relevance-discovered/1",
        "urls": list(urls or []),
        "notes": list(notes or []),
        "per_school": list(per_school or []),
    }
    try:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return target, ""
    except OSError as error:
        return None, str(error)


def load_discovered(path=None):
    """Load previously discovered URLs.  Returns a list (empty when none)."""
    target = Path(path) if path else (_repo_root() / "qa" / "relevance" / "discovered_urls.json")
    if not target.is_file():
        return []
    try:
        with open(target, encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("urls") or []
    except (OSError, json.JSONDecodeError):
        return []
