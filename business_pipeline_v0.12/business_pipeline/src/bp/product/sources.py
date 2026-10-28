"""Source finder shared by every subject (product layer, standard library only).

The researcher in Write Smarter selects databases for a general academic audience.
This module keeps only the sources that answer business questions, and adds a
curated list of official sites for the regions the product serves: the United
States, Europe, the Middle East and China.

Rules:
* nothing here invents a source or a number; every result carries the database,
  URL/DOI, retrieval time and a transparent credibility signal;
* a database that fails is reported, not hidden, and never blocks the others;
* web search runs only over a curated domain list, and only when a search key is
  configured. Without a key the directory is returned instead.
"""

import copy
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

TIMEOUT = 12
USER_AGENT = "SmartBusinessWriter/1.0 (mailto:%s)" % (
    os.environ.get("BP_CROSSREF_MAILTO") or os.environ.get("BP_OPENALEX_EMAIL") or "research@example.com")

#: Academic databases that carry business, management, economics, finance and
#: marketing research.  Medical and engineering indexes are deliberately absent:
#: they were the bulk of the general researcher and add noise here.
DATABASES = [
    {"id": "openalex", "label": "OpenAlex", "kind": "academic", "access": "free",
     "regions": ["Global"], "disciplines": ["business", "economics", "management", "finance", "marketing"],
     "note": "Broad scholarly index; free, no key required.", "enabled": True},
    {"id": "crossref", "label": "Crossref", "kind": "metadata", "access": "free",
     "regions": ["Global"], "disciplines": ["business", "economics", "management", "finance"],
     "note": "DOI metadata; used to verify a citation and fill authors, year and venue.", "enabled": True},
    {"id": "semanticscholar", "label": "Semantic Scholar", "kind": "academic", "access": "free (key optional)",
     "regions": ["Global"], "disciplines": ["business", "economics", "management", "marketing"],
     "note": "Citation graph and abstracts; strong on working papers and conference papers.", "enabled": True},
    {"id": "doaj", "label": "DOAJ", "kind": "academic", "access": "free",
     "regions": ["Global"], "disciplines": ["business", "economics", "management", "finance"],
     "note": "Open-access journals only; every result has a free full text.", "enabled": True},
    # Present but off by default: paid or not business-specific.
    {"id": "scopus", "label": "Scopus", "kind": "academic", "access": "subscription",
     "regions": ["Global"], "disciplines": ["business", "economics", "management"],
     "note": "Strong business journal coverage, but a subscription key is required.", "enabled": False},
    {"id": "arxiv", "label": "arXiv (econ)", "kind": "preprint", "access": "free",
     "regions": ["Global"], "disciplines": ["economics", "finance"],
     "note": "Economics and finance preprints only; not peer reviewed.", "enabled": False},
    {"id": "pubmed", "label": "PubMed / PMC", "kind": "academic", "access": "free",
     "regions": ["Global"], "disciplines": ["medicine"],
     "note": "Excluded from business shelves: medical literature is not the question here.", "enabled": False},
]

#: Curated official and research sites, by region.  `tier` is for presentation:
#: official (government / regulator / multilateral), data (statistics or exchange),
#: research (academic or think tank), news (business press).
VETTED_SITES = [
    # United States
    {"id": "sec", "label": "U.S. SEC EDGAR", "domain": "sec.gov", "region": "US", "tier": "official", "use": "company filings"},
    {"id": "fed", "label": "Federal Reserve", "domain": "federalreserve.gov", "region": "US", "tier": "official", "use": "monetary policy and data"},
    {"id": "fred", "label": "FRED (St. Louis Fed)", "domain": "fred.stlouisfed.org", "region": "US", "tier": "data", "use": "economic time series"},
    {"id": "bls", "label": "U.S. Bureau of Labor Statistics", "domain": "bls.gov", "region": "US", "tier": "data", "use": "labour and prices"},
    {"id": "bea", "label": "U.S. Bureau of Economic Analysis", "domain": "bea.gov", "region": "US", "tier": "data", "use": "GDP and trade"},
    {"id": "census", "label": "U.S. Census Bureau", "domain": "census.gov", "region": "US", "tier": "data", "use": "population and business statistics"},
    {"id": "ustr", "label": "U.S. Trade Representative", "domain": "ustr.gov", "region": "US", "tier": "official", "use": "trade policy"},
    {"id": "ftc", "label": "U.S. Federal Trade Commission", "domain": "ftc.gov", "region": "US", "tier": "official", "use": "competition and consumer policy"},
    {"id": "gao", "label": "U.S. GAO", "domain": "gao.gov", "region": "US", "tier": "official", "use": "public-sector audits"},
    {"id": "cbo", "label": "U.S. Congressional Budget Office", "domain": "cbo.gov", "region": "US", "tier": "official", "use": "fiscal projections"},
    # Europe
    {"id": "ecb", "label": "European Central Bank", "domain": "ecb.europa.eu", "region": "Europe", "tier": "official", "use": "monetary policy and banking"},
    {"id": "eurostat", "label": "European Commission / Eurostat", "domain": "ec.europa.eu", "region": "Europe", "tier": "data", "use": "EU policy and statistics"},
    {"id": "oecd", "label": "OECD", "domain": "oecd.org", "region": "Europe", "tier": "official", "use": "economic and social data"},
    {"id": "eib", "label": "European Investment Bank", "domain": "eib.org", "region": "Europe", "tier": "official", "use": "investment and finance"},
    {"id": "ebrd", "label": "EBRD", "domain": "ebrd.com", "region": "Europe", "tier": "official", "use": "transition economies"},
    {"id": "bis", "label": "Bank for International Settlements", "domain": "bis.org", "region": "Europe", "tier": "official", "use": "banking and financial stability"},
    {"id": "wto", "label": "World Trade Organization", "domain": "wto.org", "region": "Europe", "tier": "official", "use": "trade rules and statistics"},
    {"id": "ons", "label": "UK Office for National Statistics", "domain": "ons.gov.uk", "region": "Europe", "tier": "data", "use": "UK statistics"},
    {"id": "destatis", "label": "Destatis (Germany)", "domain": "destatis.de", "region": "Europe", "tier": "data", "use": "German statistics"},
    {"id": "insee", "label": "INSEE (France)", "domain": "insee.fr", "region": "Europe", "tier": "data", "use": "French statistics"},
    # Middle East
    {"id": "worldbank", "label": "World Bank", "domain": "worldbank.org", "region": "Global", "tier": "official", "use": "development and country data"},
    {"id": "imf", "label": "International Monetary Fund", "domain": "imf.org", "region": "Global", "tier": "official", "use": "macro and financial data"},
    {"id": "un", "label": "United Nations", "domain": "un.org", "region": "Global", "tier": "official", "use": "development and policy"},
    {"id": "unctad", "label": "UNCTAD", "domain": "unctad.org", "region": "Global", "tier": "official", "use": "trade and investment"},
    {"id": "gcc", "label": "Gulf Cooperation Council", "domain": "gcc-sg.org", "region": "Middle East", "tier": "official", "use": "GCC policy"},
    {"id": "amf", "label": "Arab Monetary Fund", "domain": "amf.org.ae", "region": "Middle East", "tier": "official", "use": "Arab financial data"},
    {"id": "uae-stat", "label": "UAE Federal Competitiveness and Statistics Centre", "domain": "fcsc.gov.ae", "region": "Middle East", "tier": "data", "use": "UAE statistics"},
    {"id": "saudi-stat", "label": "Saudi General Authority for Statistics", "domain": "stats.gov.sa", "region": "Middle East", "tier": "data", "use": "Saudi statistics"},
    {"id": "qatar-stat", "label": "Qatar Planning and Statistics Authority", "domain": "psa.gov.qa", "region": "Middle East", "tier": "data", "use": "Qatar statistics"},
    {"id": "israel-cbs", "label": "Israel Central Bureau of Statistics", "domain": "cbs.gov.il", "region": "Middle East", "tier": "data", "use": "Israeli statistics"},
    {"id": "turkey-tuik", "label": "TÜİK (Turkey)", "domain": "tuik.gov.tr", "region": "Middle East", "tier": "data", "use": "Turkish statistics"},
    # China
    {"id": "china-nbs", "label": "China National Bureau of Statistics", "domain": "stats.gov.cn", "region": "China", "tier": "data", "use": "Chinese statistics"},
    {"id": "china-customs", "label": "China Customs", "domain": "customs.gov.cn", "region": "China", "tier": "official", "use": "trade data"},
    {"id": "pboc", "label": "People's Bank of China", "domain": "pboc.gov.cn", "region": "China", "tier": "official", "use": "monetary policy"},
    {"id": "china-mof", "label": "China Ministry of Finance", "domain": "mof.gov.cn", "region": "China", "tier": "official", "use": "fiscal policy"},
    {"id": "ndrc", "label": "China NDRC", "domain": "ndrc.gov.cn", "region": "China", "tier": "official", "use": "industrial policy"},
    {"id": "gov-cn", "label": "The State Council of China", "domain": "gov.cn", "region": "China", "tier": "official", "use": "policy and releases"},
    {"id": "sse", "label": "Shanghai Stock Exchange", "domain": "sse.com.cn", "region": "China", "tier": "data", "use": "listed companies"},
    {"id": "szse", "label": "Shenzhen Stock Exchange", "domain": "szse.cn", "region": "China", "tier": "data", "use": "listed companies"},
    {"id": "hkex", "label": "Hong Kong Exchanges", "domain": "hkex.com.hk", "region": "China", "tier": "data", "use": "filings and market data"},
    # Vetted business press (tier news; paywalls are marked by the publisher)
    {"id": "reuters", "label": "Reuters Business", "domain": "reuters.com", "region": "Global", "tier": "news", "use": "business news"},
    {"id": "ft", "label": "Financial Times", "domain": "ft.com", "region": "Global", "tier": "news", "use": "business news"},
    {"id": "bloomberg", "label": "Bloomberg", "domain": "bloomberg.com", "region": "Global", "tier": "news", "use": "markets and companies"},
    {"id": "wsj", "label": "Wall Street Journal", "domain": "wsj.com", "region": "Global", "tier": "news", "use": "business news"},
    {"id": "economist", "label": "The Economist", "domain": "economist.com", "region": "Global", "tier": "news", "use": "analysis"},
    {"id": "scmp", "label": "South China Morning Post", "domain": "scmp.com", "region": "China", "tier": "news", "use": "China business"},
    {"id": "caixin", "label": "Caixin Global", "domain": "caixinglobal.com", "region": "China", "tier": "news", "use": "China finance"},
    {"id": "arabnews", "label": "Arab News", "domain": "arabnews.com", "region": "Middle East", "tier": "news", "use": "Middle East business"},
    {"id": "thenational", "label": "The National (UAE)", "domain": "thenationalnews.com", "region": "Middle East", "tier": "news", "use": "Gulf business"},
    # Legal primary sources: legislation, courts, regulators and international law.
    {"id": "congress", "label": "U.S. Congress (Congress.gov)", "domain": "congress.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "US legislation and bills"},
    {"id": "federalregister", "label": "U.S. Federal Register", "domain": "federalregister.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "US rules and notices"},
    {"id": "ecfr", "label": "U.S. eCFR", "domain": "ecfr.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "US Code of Federal Regulations"},
    {"id": "ofac", "label": "U.S. Treasury OFAC", "domain": "treasury.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "sanctions lists and guidance"},
    {"id": "law-cornell", "label": "Cornell LII", "domain": "law.cornell.edu", "region": "US", "tier": "research", "category": "legal", "academic_fit": "research", "use": "US legal reference"},
    {"id": "supremecourt", "label": "U.S. Supreme Court", "domain": "supremecourt.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "US case law"},
    {"id": "uscourts", "label": "U.S. Courts", "domain": "uscourts.gov", "region": "US", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "US federal courts"},
    {"id": "legislation-uk", "label": "legislation.gov.uk", "domain": "legislation.gov.uk", "region": "Europe", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "UK legislation"},
    {"id": "supremecourt-uk", "label": "UK Supreme Court", "domain": "supremecourt.uk", "region": "Europe", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "UK case law"},
    {"id": "eurlex", "label": "EUR-Lex", "domain": "eur-lex.europa.eu", "region": "Europe", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "EU law and treaties"},
    {"id": "eu-sanctions", "label": "EU Council sanctions", "domain": "consilium.europa.eu", "region": "Europe", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "EU restrictive measures"},
    {"id": "curia", "label": "Court of Justice of the EU", "domain": "curia.europa.eu", "region": "Europe", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "EU case law"},
    {"id": "wipo", "label": "WIPO Lex", "domain": "wipo.int", "region": "Global", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "intellectual property law"},
    {"id": "uncitral", "label": "UNCITRAL", "domain": "uncitral.un.org", "region": "Global", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "international trade law"},
    {"id": "icj", "label": "International Court of Justice", "domain": "icj-cij.org", "region": "Global", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "international law"},
    {"id": "icsid", "label": "ICSID", "domain": "icsid.worldbank.org", "region": "Global", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "investment arbitration"},
    {"id": "npc", "label": "China National People's Congress", "domain": "npc.gov.cn", "region": "China", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "Chinese legislation"},
    {"id": "china-court", "label": "Supreme People's Court of China", "domain": "court.gov.cn", "region": "China", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "Chinese case law"},
    {"id": "saudi-laws", "label": "Saudi Bureau of Experts", "domain": "boe.gov.sa", "region": "Middle East", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "Saudi legislation"},
    {"id": "uae-laws", "label": "UAE Legislation", "domain": "uaelegislation.gov.ae", "region": "Middle East", "tier": "official", "category": "legal", "academic_fit": "primary", "use": "UAE legislation"},
    {"id": "iran-cbi", "label": "Central Bank of Iran", "domain": "cbi.ir", "region": "Middle East", "tier": "data", "category": "economic", "academic_fit": "primary", "use": "official monetary data (state source)"},
    {"id": "iran-sci", "label": "Statistical Center of Iran", "domain": "amar.org.ir", "region": "Middle East", "tier": "data", "category": "economic", "academic_fit": "primary", "use": "official statistics (state source)"},
    {"id": "iran-un", "label": "United Nations in Iran", "domain": "iran.un.org", "region": "Middle East", "tier": "official", "category": "social", "academic_fit": "primary", "use": "UN country data and programmes"},
    # Economic data portals and research.
    {"id": "imf-data", "label": "IMF Data", "domain": "data.imf.org", "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary", "use": "macro and financial data"},
    {"id": "worldbank-data", "label": "World Bank Data", "domain": "data.worldbank.org", "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary", "use": "development data"},
    {"id": "oecd-library", "label": "OECD iLibrary", "domain": "oecd-ilibrary.org", "region": "Europe", "tier": "research", "category": "economic", "academic_fit": "research", "use": "OECD reports and data"},
    # Social data and research.
    {"id": "ilo", "label": "International Labour Organization", "domain": "ilo.org", "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary", "use": "labour and social policy"},
    {"id": "unesco", "label": "UNESCO", "domain": "unesco.org", "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary", "use": "education, culture and society"},
    {"id": "undp", "label": "UNDP", "domain": "undp.org", "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary", "use": "development and society"},
    {"id": "hdr", "label": "Human Development Reports", "domain": "hdr.undp.org", "region": "Global", "tier": "data", "category": "social", "academic_fit": "primary", "use": "human development indicators"},
    {"id": "who", "label": "World Health Organization", "domain": "who.int", "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary", "use": "health and social determinants"},
    {"id": "pew", "label": "Pew Research Center", "domain": "pewresearch.org", "region": "US", "tier": "research", "category": "social", "academic_fit": "research", "use": "survey research"},
    {"id": "wvs", "label": "World Values Survey", "domain": "worldvaluessurvey.org", "region": "Global", "tier": "research", "category": "social", "academic_fit": "research", "use": "cross-national values data"},
    {"id": "arabbarometer", "label": "Arab Barometer", "domain": "arabbarometer.org", "region": "Middle East", "tier": "research", "category": "social", "academic_fit": "research", "use": "Middle East survey data"},
    {"id": "un-data", "label": "UN Data", "domain": "data.un.org", "region": "Global", "tier": "data", "category": "social", "academic_fit": "primary", "use": "UN statistics"},
]

REGIONS = ["Global", "US", "Europe", "Middle East", "China"]
CATEGORIES = ["legal", "economic", "social", "company", "news"]

#: Category for the registry entries written before the category field existed.
SITE_CATEGORY = {
    "sec": "company", "sse": "company", "szse": "company", "hkex": "company",
    "ftc": "legal", "gao": "legal",
    "un": "social",
    "reuters": "news", "ft": "news", "bloomberg": "news", "wsj": "news",
    "economist": "news", "scmp": "news", "caixin": "news", "arabnews": "news", "thenational": "news",
}


def databases(enabled_only=False):
    return [dict(item) for item in DATABASES if item["enabled"] or not enabled_only]


def vetted_sites(region=None, tier=None, category=None, academic_fit=None):
    sites = []
    for site in VETTED_SITES:
        item = dict(site)
        item.setdefault("category", SITE_CATEGORY.get(item["id"], "economic"))
        item.setdefault("academic_fit", "background" if item["tier"] == "news"
                        else "research" if item["tier"] == "research" else "primary")
        sites.append(item)
    if region and region != "Global":
        sites = [site for site in sites if site["region"] in (region, "Global")]
    if tier:
        sites = [site for site in sites if site["tier"] == tier]
    if category:
        sites = [site for site in sites if site["category"] == category]
    if academic_fit:
        sites = [site for site in sites if site["academic_fit"] == academic_fit]
    return sites


def _get_json(url, headers=None, timeout=TIMEOUT):
    """One GET returning JSON.  Patched in tests so no test touches the network."""
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _text(value, limit=600):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _abstract_from_inverted(index):
    if not isinstance(index, dict):
        return ""
    words = []
    for word, positions in index.items():
        for position in positions or []:
            words.append((position, word))
    words.sort()
    return " ".join(word for _, word in words)[:1200]


def _credibility(item):
    """Transparent signals, not a claim of quality.  Capped at 100."""
    score = 20
    if item.get("doi"):
        score += 30
    if len(item.get("abstract") or "") >= 80:
        score += 20
    if item.get("year") and int(item["year"]) >= datetime.now(timezone.utc).year - 10:
        score += 15
    if item.get("venue"):
        score += 10
    if item.get("url"):
        score += 5
    return min(100, score)


def _item(title, authors="", year=None, abstract="", doi=None, url=None, venue="", database="", kind="academic",
          authors_list=None, volume="", issue="", pages="", publisher="", item_type="journalArticle"):
    title = _text(title, 400)
    names = [_text(name, 160) for name in (authors_list or []) if _text(name, 160)]
    return {
        "title": title or "Untitled",
        "authors": _text(authors, 300),
        "authors_list": names,
        "year": int(year) if year and str(year).isdigit() else None,
        "venue": _text(venue, 200),
        "volume": _text(volume, 40), "issue": _text(issue, 40), "pages": _text(pages, 40),
        "publisher": _text(publisher, 160), "item_type": item_type,
        "doi": (doi or "").strip().lower() or None,
        "url": url or (("https://doi.org/" + doi.strip()) if doi else None),
        "abstract": _text(abstract, 1200),
        "database": database,
        "kind": kind,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _openalex(query, limit, year_from):
    params = {"search": query, "per-page": str(limit), "sort": "relevance_score:desc"}
    if year_from:
        params["filter"] = "publication_year:%d-" % int(year_from)
    data = _get_json("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
    out = []
    for work in data.get("results", []):
        doi = (work.get("doi") or "").replace("https://doi.org/", "")
        authorships = work.get("authorships") or []
        names = [(a.get("author") or {}).get("display_name", "") for a in authorships[:20]]
        names = [name for name in names if name]
        biblio = work.get("biblio") or {}
        pages = ""
        if biblio.get("first_page") and biblio.get("last_page"):
            pages = "%s-%s" % (biblio["first_page"], biblio["last_page"])
        elif biblio.get("first_page"):
            pages = biblio["first_page"]
        location = (work.get("primary_location") or {}).get("source") or {}
        out.append(_item(
            work.get("title"), ", ".join(names[:5]), work.get("publication_year"),
            _abstract_from_inverted(work.get("abstract_inverted_index")), doi,
            ("https://doi.org/" + doi) if doi else None, location.get("display_name"), "OpenAlex",
            authors_list=names, volume=biblio.get("volume", ""), issue=biblio.get("issue", ""), pages=pages,
            publisher=location.get("host_organization_name", ""), item_type=work.get("type", "article")))
    return out


def _crossref(query, limit, year_from):
    params = {"query": query, "rows": str(min(limit, 25)), "sort": "relevance", "order": "desc",
              "select": "title,author,published,DOI,abstract,container-title,volume,issue,page,publisher"}
    if year_from:
        params["filter"] = "from-pub-date:%d" % int(year_from)
    data = _get_json("https://api.crossref.org/works?" + urllib.parse.urlencode(params),
                     headers={"User-Agent": USER_AGENT}, timeout=6)
    out = []
    for work in (data.get("message") or {}).get("items", []):
        date = (work.get("published") or {}).get("date-parts") or [[None]]
        year = date[0][0] if date and date[0] else None
        names = [" ".join(filter(None, [a.get("given"), a.get("family")]))
                 for a in (work.get("author") or [])[:20]]
        names = [name for name in names if name]
        title = work.get("title") or []
        container = work.get("container-title") or []
        out.append(_item(title[0] if isinstance(title, list) and title else title,
                         ", ".join(names[:5]), year, _text(work.get("abstract"), 1200), work.get("DOI"),
                         None, container[0] if isinstance(container, list) and container else "", "Crossref",
                         authors_list=names, volume=work.get("volume", ""), issue=work.get("issue", ""),
                         pages=work.get("page", ""), publisher=work.get("publisher", ""),
                         item_type=work.get("type", "journal-article")))
    return out


def _semanticscholar(query, limit, year_from):
    params = {"query": query, "limit": str(min(limit, 25)),
              "fields": "title,authors,year,abstract,externalIds,journal,publicationVenue,openAccessPdf"}
    if year_from:
        params["year"] = "%d-" % int(year_from)
    headers = {}
    if os.environ.get("BP_SEMANTIC_SCHOLAR_KEY"):
        headers["x-api-key"] = os.environ["BP_SEMANTIC_SCHOLAR_KEY"]
    data = _get_json("https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params),
                     headers=headers)
    out = []
    for paper in data.get("data", []):
        doi = (paper.get("externalIds") or {}).get("DOI")
        names = [a.get("name", "") for a in (paper.get("authors") or [])[:20]]
        names = [name for name in names if name]
        journal = paper.get("journal") or {}
        out.append(_item(paper.get("title"), ", ".join(names[:5]), paper.get("year"), paper.get("abstract"),
                         doi, None, journal.get("name") or (paper.get("publicationVenue") or {}).get("name", ""),
                         "Semantic Scholar", authors_list=names, volume=journal.get("volume", ""),
                         pages=journal.get("pages", ""), item_type="journalArticle"))
    return out


def _doaj(query, limit, year_from):
    expression = query if not year_from else "%s AND bibjson.year:[%d TO %d]" % (
        query, int(year_from), datetime.now(timezone.utc).year)
    url = "https://doaj.org/api/search/articles/%s?pageSize=%s&page=1" % (
        urllib.parse.quote(expression, safe=""), min(limit, 50))
    data = _get_json(url)
    out = []
    for result in data.get("results", []):
        bib = result.get("bibjson") or {}
        doi = next((i.get("id") for i in bib.get("identifier") or [] if i.get("type") == "doi"), None)
        names = [a.get("name", "") for a in (bib.get("author") or [])[:20]]
        names = [name for name in names if name]
        journal = bib.get("journal") or {}
        pages = ""
        if bib.get("start_page") and bib.get("end_page"):
            pages = "%s-%s" % (bib["start_page"], bib["end_page"])
        out.append(_item(bib.get("title"), ", ".join(names[:5]), bib.get("year"), bib.get("abstract"), doi,
                         (next((l.get("url") for l in bib.get("link") or [] if l.get("type") == "fulltext"), None)),
                         journal.get("title", ""), "DOAJ", authors_list=names, volume=journal.get("volume", ""),
                         issue=journal.get("number", ""), pages=pages, publisher=journal.get("publisher", ""),
                         item_type="journalArticle"))
    return out


ADAPTERS = {"openalex": _openalex, "crossref": _crossref, "semanticscholar": _semanticscholar,
            "doaj": _doaj}

#: At most this many outbound source requests at once, across every dimension.
_NETWORK = threading.Semaphore(int(os.environ.get("BP_SOURCE_CONCURRENCY", "8")))
_CACHE = {}
_CACHE_LOCK = threading.Lock()


def _cache_ttl():
    try:
        return max(0.0, float(os.environ.get("BP_SOURCE_CACHE_TTL", "600")))
    except (TypeError, ValueError):
        return 600.0


def _cache_get(key):
    if _cache_ttl() <= 0:
        return None
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if not entry:
            return None
        stored, value = entry
        if time.time() - stored > _cache_ttl():
            _CACHE.pop(key, None)
            return None
    return copy.deepcopy(value)


def _cache_put(key, value):
    if _cache_ttl() <= 0:
        return
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), copy.deepcopy(value))


def clear_cache():
    """Drop every cached academic and web search (used by tests and a reset)."""
    with _CACHE_LOCK:
        _CACHE.clear()


def search_academic(query, databases=None, limit=20, year_from=None):
    """Search the selected academic databases and return one merged, deduped list.

    The selected databases are queried concurrently, under a bounded network
    semaphore, so one slow index cannot add its latency to every other index.
    Identical searches are cached briefly; `cached` says whether a result came
    from that cache.  Each response carries per-database `timings` in seconds.
    """
    text = (query or "").strip()
    if not text:
        return {"query": text, "results": [], "errors": [], "databases": [], "retrieved_at": None}
    wanted = [d for d in DATABASES if d["enabled"] and (not databases or d["id"] in databases)]
    cache_key = ("academic", text, tuple(d["id"] for d in wanted), limit, year_from)
    cached = _cache_get(cache_key)
    if cached is not None:
        cached["cached"] = True
        return cached
    results, errors, skipped, timings = [], [], [], {}

    def run(database):
        adapter = ADAPTERS.get(database["id"])
        if not adapter:
            return database["id"], [], {"database": database["id"], "reason": "no adapter in this build"}, 0.0
        started = time.perf_counter()
        try:
            with _NETWORK:
                items = adapter(text, limit, year_from)
            return database["id"], items, None, time.perf_counter() - started
        except Exception as error:       # one database must never block the others
            return database["id"], [], {"database": database["id"], "error": str(error)[:200]}, time.perf_counter() - started

    if wanted:
        with ThreadPoolExecutor(max_workers=min(len(wanted), 4)) as pool:
            batches = list(pool.map(run, wanted))
    else:
        batches = []
    for database_id, items, failure, seconds in batches:
        timings[database_id] = round(seconds, 2)
        results.extend(items)
        if failure and "error" in failure:
            errors.append(failure)
        elif failure:
            skipped.append(failure)
    deduped = {}
    for item in results:
        key = item["doi"] or re.sub(r"[^a-z0-9]+", "", item["title"].lower())[:90]
        if key and key not in deduped:
            item["credibility"] = _credibility(item)
            deduped[key] = item
    merged = sorted(deduped.values(), key=lambda item: (-item["credibility"], -(item.get("year") or 0)))
    payload = {"query": text, "results": merged[:limit], "errors": errors, "skipped": skipped,
               "databases": [d["id"] for d in wanted], "timings": timings, "cached": False,
               "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _cache_put(cache_key, payload)
    return copy.deepcopy(payload)


_FIRECRAWL_COOLDOWN = {"until": 0.0, "error": None}


def _post_json(url, payload, headers=None, timeout=TIMEOUT):
    """One POST returning JSON.  Patched in tests so no test touches the network."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _web_item(result, sites):
    url = result.get("url") or ""
    host = urllib.parse.urlparse(url).hostname or ""
    host = host[4:] if host.startswith("www.") else host
    site = next((s for s in sites if host == s["domain"] or host.endswith("." + s["domain"])), None)
    if not site:
        return None
    return {"title": _text(result.get("title"), 300), "url": url,
            "description": _text(result.get("description") or result.get("snippet"), 500),
            "site": site["label"], "domain": host, "region": site["region"], "tier": site["tier"]}


def _brave_web(text, sites, limit):
    key = os.environ.get("BP_BRAVE_API_KEY")
    if not key:
        return [], {"provider": "brave", "skipped": "BP_BRAVE_API_KEY is not set"}
    domains = [site["domain"] for site in sites if site["tier"] in ("official", "data", "research")][:5]
    search = text + (" (" + " OR ".join("site:" + d for d in domains) + ")" if domains else "")
    params = {"q": search, "count": str(min(limit, 20)), "text_decorations": "false", "safesearch": "moderate"}
    try:
        data = _get_json("https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(params),
                         headers={"X-Subscription-Token": key}, timeout=8)
    except Exception as error:
        return [], {"provider": "brave", "error": str(error)[:160]}
    out = [item for item in (_web_item(result, sites) for result in (data.get("web") or {}).get("results", [])) if item]
    return out, {"provider": "brave", "n": len(out)}


def _firecrawl_timeout():
    try:
        return max(3.0, float(os.environ.get("BP_FIRECRAWL_TIMEOUT", "8")))
    except (TypeError, ValueError):
        return 8.0


def _firecrawl_web(text, sites, limit):
    key = os.environ.get("BP_FIRECRAWL_API_KEY")
    keyless = os.environ.get("BP_FIRECRAWL_KEYLESS", "1") != "0"
    if not key and not keyless:
        return [], {"provider": "firecrawl", "skipped": "BP_FIRECRAWL_API_KEY is not set"}
    if time.time() < _FIRECRAWL_COOLDOWN["until"]:
        return [], {"provider": "firecrawl", "skipped": "cooldown", "error": _FIRECRAWL_COOLDOWN["error"]}
    domains = sorted({site["domain"].split("/")[0] for site in sites})[:20]
    payload = {"query": text, "limit": min(max(limit, 1), 10), "includeDomains": domains}
    headers = {"Authorization": "Bearer " + key} if key else {}
    try:
        data = _post_json("https://api.firecrawl.dev/v2/search", payload, headers=headers,
                          timeout=_firecrawl_timeout())
    except urllib.error.HTTPError as error:
        if error.code == 429:
            _FIRECRAWL_COOLDOWN.update({"until": time.time() + 86400,
                                        "error": "firecrawl rate-limited (24h cooldown)"})
        return [], {"provider": "firecrawl", "error": "HTTP %s" % error.code}
    except Exception as error:
        return [], {"provider": "firecrawl", "error": str(error)[:160]}
    rows = ((data.get("data") or {}).get("web") or [])
    out = [item for item in (_web_item(result, sites) for result in rows) if item]
    return out, {"provider": "firecrawl", "n": len(out)}


def search_web(query, region="Global", limit=10, category=None):
    """Search the curated domains: Brave first, Firecrawl as the fallback.

    Nothing outside the curated list can leave this function.  If neither
    provider returns a curated result, the directory is returned with a reason.
    """
    text = (query or "").strip()
    if not text:
        return {"query": text, "results": [], "notice": "A search query is required.", "sites": []}
    sites = vetted_sites(region, category=category)
    key = ("web", text, region, limit, category)
    cached = _cache_get(key)
    if cached is not None:
        cached["cached"] = True
        return cached
    attempts, results = [], []
    brave, brave_attempt = _brave_web(text, sites, limit)
    attempts.append(brave_attempt)
    results.extend(brave)
    seen = {item["url"] for item in results}
    # Fallback only when Brave returned nothing: a thin Brave answer is still an
    # answer, and a second provider would only add latency.
    if not results:
        firecrawl, firecrawl_attempt = _firecrawl_web(text, sites, limit)
        attempts.append(firecrawl_attempt)
        for item in firecrawl:
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)
    results = results[:max(1, limit)]
    providers = [item.get("provider") for item in attempts
                 if item.get("n") and item.get("provider") in ("brave", "firecrawl")]
    provider = "+".join(dict.fromkeys(providers)) if providers else None
    notice = None
    if not results:
        notice = ("No curated web result came back. Brave and Firecrawl were both unavailable or empty; "
                  "the vetted-site directory is below.")
    payload = {"query": text, "results": results, "sites": sites, "provider": provider,
               "attempts": attempts, "notice": notice, "cached": False}
    _cache_put(key, payload)
    return copy.deepcopy(payload)


def web_status():
    """Which web providers are usable, without exposing any key."""
    keyless = os.environ.get("BP_FIRECRAWL_KEYLESS", "1") != "0"
    return {"primary": "brave", "fallback": "firecrawl",
            "brave": bool(os.environ.get("BP_BRAVE_API_KEY")),
            "firecrawl": bool(os.environ.get("BP_FIRECRAWL_API_KEY")) or keyless,
            "firecrawl_keyless": keyless}
