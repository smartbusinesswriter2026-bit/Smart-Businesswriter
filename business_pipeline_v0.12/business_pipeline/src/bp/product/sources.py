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
import queue
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

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
    {"id": "corpus", "label": "Proprietary corpus", "kind": "proprietary", "access": "local",
     "regions": ["Global"], "disciplines": ["business", "economics", "management", "finance", "marketing"],
     "note": "Local page-exact evidence from the owned corpus; layer 1, searched first; fails open when down.", "enabled": True},
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

#: The topics a paper can carry.  The pipeline's subject ids are the spine;
#: the cross-cutting topics are what a brief actually names ("business ethics",
#: "culture", "health").  `keywords` are used only to infer a topic from free
#: text; a site's own `topics` list is the authority on where it belongs.
TOPICS = {
    "ethics": {"label": "Business ethics and governance",
               "keywords": ["ethic", "moral", "csr", "corporate social responsibility",
                            "integrity", "corruption", "bribery", "stakeholder theory"]},
    "culture": {"label": "Culture and cross-cultural management",
                "keywords": ["culture", "cultural", "hofstede", "globe project",
                             "cross-cultural", "values survey", "national culture"]},
    "law": {"label": "Law, regulation and policy",
            "keywords": ["law", "legal", "regulation", "regulatory", "compliance",
                         "sanction", "legislation", "court", "policy"]},
    "health": {"label": "Health and healthcare",
               "keywords": ["health", "healthcare", "hospital", "patient", "medical",
                            "pharma", "disease", "public health"]},
    "environment": {"label": "Environment and sustainability",
                    "keywords": ["environment", "climate", "emission", "carbon",
                                 "sustainability", "esg", "energy", "renewable", "green"]},
    "technology": {"label": "Technology and innovation",
                   "keywords": ["technology", "digital", "innovation", "ai", "artificial intelligence",
                                "automation", "software", "platform", "patent"]},
    "accounting": {"label": "Accounting and reporting",
                   "keywords": ["accounting", "ledger", "ifrs", "gaap", "audit",
                                "financial statement", "trial balance", "reporting"]},
    "finance": {"label": "Finance and markets",
                "keywords": ["finance", "financial", "valuation", "wacc", "capital",
                             "investment", "bank", "portfolio", "stock", "bond"]},
    "economics": {"label": "Economics and public policy",
                  "keywords": ["economics", "economic", "gdp", "inflation", "monetary",
                               "fiscal", "trade", "labour market", "labor market", "productivity"]},
    "marketing": {"label": "Marketing and customers",
                  "keywords": ["marketing", "brand", "customer", "consumer", "advertising",
                               "campaign", "segment", "pricing", "retail", "channel",
                               "market entry", "market size"]},
    "operations": {"label": "Operations and quality",
                   "keywords": ["operations", "process", "quality", "lean", "six sigma",
                                "capacity", "inventory", "production", "service"]},
    "supply_chain": {"label": "Supply chain and logistics",
                     "keywords": ["supply chain", "logistics", "procurement", "supplier",
                                  "distribution", "warehouse", "freight", "sourcing"]},
    "people": {"label": "People, work and organisation",
               "keywords": ["human resource", "hr", "employee", "workforce", "talent",
                            "leadership", "motivation", "organisational behaviour",
                            "organizational behavior", "training"]},
    "entrepreneurship": {"label": "Entrepreneurship and ventures",
                         "keywords": ["entrepreneur", "startup", "start-up", "venture",
                                      "sme", "msme", "incubator", "founder"]},
    "management": {"label": "Management and strategy",
                   "keywords": ["management", "strategy", "strategic", "competitive",
                                "governance", "change", "organisation", "organization"]},
    "project": {"label": "Project and programme management",
                "keywords": ["project", "programme", "program", "portfolio", "pmo",
                             "schedule", "milestone", "charter"]},
    "research": {"label": "Research methods and evidence",
                 "keywords": ["research", "method", "methodology", "statistics",
                              "sample", "survey", "regression", "evidence", "meta-analysis"]},
    "industry": {"label": "Industry and market structure",
                 "keywords": ["industry", "sector", "market share", "competitor",
                              "competitive intensity", "five forces", "market size"]},
    "company": {"label": "Company and filing data",
                "keywords": ["company", "firm", "annual report", "filing", "listed",
                             "subsidiary", "shareholder"]},
    "country": {"label": "Country and regional data",
                "keywords": ["country", "region", "national", "economy of", "market entry"]},
    "news": {"label": "Business press",
             "keywords": ["news", "current", "recent", "announcement", "press"]},
}

#: Pipeline subject ids are not always the topic id (`project-management`,
#: `supply-chain`).  One alias table keeps both surfaces honest.
SUBJECT_ALIASES = {"project-management": "project", "supply-chain": "supply_chain",
                   "strategy": "management", "organisation": "people",
                   "organization": "people", "project management": "project",
                   "supply chain": "supply_chain", "human resources": "people",
                   "human resource": "people"}

#: Sites whose domain was already in the registry before topics existed.
#: `vetted_sites` merges these into the site dict, so the long list above does
#: not have to be rewritten.
SITE_TOPICS = {
    "sec": ["finance", "accounting", "company", "law"],
    "fed": ["economics", "finance", "country"],
    "fred": ["economics", "finance", "country"],
    "bls": ["economics", "people", "country"],
    "bea": ["economics", "country"],
    "census": ["economics", "people", "country"],
    "ustr": ["economics", "law", "country"],
    "ftc": ["law", "management"],
    "gao": ["law", "economics", "management"],
    "cbo": ["economics", "law", "country"],
    "ecb": ["economics", "finance", "country"],
    "eurostat": ["economics", "country", "people"],
    "oecd": ["economics", "finance", "management", "environment", "health", "country"],
    "eib": ["finance", "economics", "environment"],
    "ebrd": ["finance", "economics", "country"],
    "bis": ["finance", "economics", "law"],
    "wto": ["economics", "law", "country"],
    "ons": ["economics", "country", "people"],
    "destatis": ["economics", "country"],
    "insee": ["economics", "country"],
    "worldbank": ["economics", "country", "environment", "health", "management"],
    "imf": ["economics", "finance", "country"],
    "un": ["country", "law", "environment", "people"],
    "unctad": ["economics", "country", "law"],
    "gcc": ["country", "law", "economics"],
    "amf": ["finance", "economics", "country"],
    "uae-stat": ["country", "economics"],
    "saudi-stat": ["country", "economics"],
    "qatar-stat": ["country", "economics"],
    "israel-cbs": ["country", "economics"],
    "turkey-tuik": ["country", "economics"],
    "china-nbs": ["country", "economics"],
    "china-customs": ["country", "economics", "law"],
    "pboc": ["finance", "economics", "country"],
    "china-mof": ["economics", "law", "country"],
    "ndrc": ["economics", "law", "environment", "country"],
    "gov-cn": ["law", "country", "economics"],
    "sse": ["company", "finance"],
    "szse": ["company", "finance"],
    "hkex": ["company", "finance", "law"],
    "reuters": ["news", "company", "finance", "economics", "management"],
    "ft": ["news", "company", "finance", "economics", "management"],
    "bloomberg": ["news", "company", "finance", "economics"],
    "wsj": ["news", "company", "finance", "economics"],
    "economist": ["news", "economics", "management", "country"],
    "scmp": ["news", "company", "country", "economics"],
    "caixin": ["news", "finance", "company", "country"],
    "arabnews": ["news", "company", "country"],
    "thenational": ["news", "company", "country"],
    "congress": ["law"], "federalregister": ["law"], "ecfr": ["law"],
    "ofac": ["law", "finance"], "law-cornell": ["law"],
    "supremecourt": ["law"], "uscourts": ["law"], "legislation-uk": ["law"],
    "supremecourt-uk": ["law"], "eurlex": ["law"], "eu-sanctions": ["law"],
    "curia": ["law"], "wipo": ["law", "technology"], "uncitral": ["law"],
    "icj": ["law"], "icsid": ["law", "finance"], "npc": ["law", "country"],
    "china-court": ["law"], "saudi-laws": ["law"], "uae-laws": ["law"],
    "iran-cbi": ["economics", "finance", "country"],
    "iran-sci": ["economics", "country"], "iran-un": ["country", "people"],
    "imf-data": ["economics", "finance", "country"],
    "worldbank-data": ["economics", "country", "environment"],
    "oecd-library": ["economics", "management", "environment", "health"],
    "ilo": ["people", "law", "country"],
    "unesco": ["culture", "people", "country"],
    "undp": ["country", "people", "environment"],
    "hdr": ["country", "people", "research"],
    "who": ["health", "country"],
    "pew": ["culture", "people", "marketing", "research"],
    "wvs": ["culture", "people", "country", "research"],
    "arabbarometer": ["culture", "people", "country", "research"],
    "un-data": ["country", "economics", "people"],
}

#: Topic-specific sites added after the first registry.  A site may carry more
#: than one topic; the selection is a ranking, not a hard filter, so a data
#: source that belongs to no exact topic can still appear below the matches.
#: `access` is honest: a paywalled source is still a vetted source, but it is
#: ranked below a free one and its snippet is orientation, not citable text.
TOPIC_SITES = [
    # Business ethics and philosophy
    {"id": "sep", "label": "Stanford Encyclopedia of Philosophy", "domain": "plato.stanford.edu",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["ethics", "management", "law"],
     "use": "philosophical foundations of ethics and stakeholder theory"},
    {"id": "iep", "label": "Internet Encyclopedia of Philosophy", "domain": "iep.utm.edu",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["ethics", "management"],
     "use": "peer-reviewed philosophy reference"},
    {"id": "markkula", "label": "Markkula Center for Applied Ethics", "domain": "scu.edu",
     "region": "US", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["ethics", "management"],
     "use": "applied business and organisational ethics"},
    {"id": "ibe", "label": "Institute of Business Ethics", "domain": "ibe.org.uk",
     "region": "Europe", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["ethics", "management"],
     "use": "business ethics research and guidance"},
    {"id": "transparency", "label": "Transparency International", "domain": "transparency.org",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["ethics", "law", "management", "country"],
     "use": "corruption and integrity indexes"},
    {"id": "unglobalcompact", "label": "UN Global Compact", "domain": "unglobalcompact.org",
     "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["ethics", "environment", "management"],
     "use": "corporate responsibility principles"},
    {"id": "carnegiecouncil", "label": "Carnegie Council for Ethics in International Affairs",
     "domain": "carnegiecouncil.org", "region": "Global", "tier": "research",
     "category": "social", "academic_fit": "research", "access": "free",
     "topics": ["ethics", "law"], "use": "ethics and international affairs"},
    # Culture and cross-cultural management
    {"id": "hofstede", "label": "Geert Hofstede", "domain": "geerthofstede.com",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["culture", "people", "management"],
     "use": "the six dimensions of national culture"},
    {"id": "hofstede-insights", "label": "Hofstede Insights / The Culture Factor",
     "domain": "hofstede-insights.com", "region": "Global", "tier": "research",
     "category": "social", "academic_fit": "research", "access": "mixed",
     "topics": ["culture", "people", "management"],
     "use": "country culture profiles and comparisons"},
    {"id": "globe", "label": "GLOBE Project", "domain": "globeproject.com",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["culture", "people", "management"],
     "use": "GLOBE cultural dimensions and leadership"},
    {"id": "afrobarometer", "label": "Afrobarometer", "domain": "afrobarometer.org",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["culture", "people", "country", "research"],
     "use": "African public opinion data"},
    {"id": "latinobarometro", "label": "Latinobarometro", "domain": "latinobarometro.org",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["culture", "people", "country", "research"],
     "use": "Latin American public opinion data"},
    # Management, strategy and the practice literature
    {"id": "hbr", "label": "Harvard Business Review", "domain": "hbr.org",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["management", "marketing", "people", "technology"],
     "use": "practice literature and management ideas"},
    {"id": "sloanreview", "label": "MIT Sloan Management Review", "domain": "sloanreview.mit.edu",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "mixed", "topics": ["management", "technology", "people"],
     "use": "management research for practice"},
    {"id": "mckinsey", "label": "McKinsey Insights", "domain": "mckinsey.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "operations", "marketing", "technology"],
     "use": "industry and strategy analysis"},
    {"id": "bcg", "label": "BCG Insights", "domain": "bcg.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "technology", "operations"],
     "use": "strategy and industry analysis"},
    {"id": "bain", "label": "Bain Insights", "domain": "bain.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "marketing", "operations"],
     "use": "strategy and customer analysis"},
    {"id": "deloitte", "label": "Deloitte Insights", "domain": "deloitte.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "finance", "operations", "technology"],
     "use": "industry and functional research"},
    {"id": "pwc", "label": "PwC Research", "domain": "pwc.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "finance", "accounting", "people"],
     "use": "industry, tax and governance research"},
    {"id": "accenture", "label": "Accenture Research", "domain": "accenture.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "technology", "operations"],
     "use": "technology and operating-model research"},
    {"id": "strategy-business", "label": "Strategy+Business", "domain": "strategy-business.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "free", "topics": ["management", "people"],
     "use": "strategy and leadership analysis"},
    {"id": "gartner", "label": "Gartner", "domain": "gartner.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["technology", "management", "operations", "marketing"],
     "use": "technology and market research"},
    {"id": "forrester", "label": "Forrester", "domain": "forrester.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["technology", "management", "marketing"],
     "use": "technology and customer research"},
    # Marketing and customer data
    {"id": "ama", "label": "American Marketing Association", "domain": "ama.org",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["marketing"], "use": "marketing practice and definitions"},
    {"id": "marketingweek", "label": "Marketing Week", "domain": "marketingweek.com",
     "region": "Europe", "tier": "news", "category": "economic", "academic_fit": "background",
     "access": "mixed", "topics": ["marketing"], "use": "marketing practice and campaigns"},
    {"id": "warc", "label": "WARC", "domain": "warc.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["marketing"], "use": "advertising and media effectiveness"},
    {"id": "emarketer", "label": "eMarketer", "domain": "emarketer.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["marketing", "technology"], "use": "digital marketing data"},
    {"id": "nielsen", "label": "Nielsen", "domain": "nielsen.com",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary",
     "access": "mixed", "topics": ["marketing", "industry"], "use": "consumer and media measurement"},
    {"id": "kantar", "label": "Kantar", "domain": "kantar.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "primary",
     "access": "mixed", "topics": ["marketing", "culture"], "use": "brand, media and consumer research"},
    {"id": "statista", "label": "Statista", "domain": "statista.com",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "background",
     "access": "mixed", "topics": ["marketing", "industry", "company", "economics"],
     "use": "market and consumer statistics"},
    {"id": "ibisworld", "label": "IBISWorld", "domain": "ibisworld.com",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["industry", "management", "strategy"],
     "use": "industry reports and market structure"},
    {"id": "euromonitor", "label": "Euromonitor", "domain": "euromonitor.com",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["industry", "marketing", "economics"],
     "use": "consumer markets and industry data"},
    {"id": "mintel", "label": "Mintel", "domain": "mintel.com",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "background",
     "access": "paywalled", "topics": ["marketing", "industry"], "use": "consumer and market research"},
    # Finance, accounting and company filings
    {"id": "fasb", "label": "FASB", "domain": "fasb.org",
     "region": "US", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["accounting", "finance"],
     "use": "US GAAP standards and projects"},
    {"id": "ifrs", "label": "IFRS Foundation / IASB", "domain": "ifrs.org",
     "region": "Global", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["accounting", "finance", "environment"],
     "use": "IFRS and ISSB standards"},
    {"id": "aicpa", "label": "AICPA", "domain": "aicpa.org",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["accounting", "finance"], "use": "accounting profession and audit"},
    {"id": "cfainstitute", "label": "CFA Institute", "domain": "cfainstitute.org",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["finance", "accounting"], "use": "investment and ethics research"},
    {"id": "annualreports", "label": "AnnualReports.com", "domain": "annualreports.com",
     "region": "Global", "tier": "data", "category": "company", "academic_fit": "primary",
     "access": "free", "topics": ["company", "finance", "accounting"],
     "use": "listed-company annual reports"},
    {"id": "companieshouse", "label": "UK Companies House", "domain": "companieshouse.gov.uk",
     "region": "Europe", "tier": "official", "category": "company", "academic_fit": "primary",
     "access": "free", "topics": ["company", "finance", "law"],
     "use": "UK company filings"},
    # Economics and think tanks
    {"id": "nber", "label": "NBER", "domain": "nber.org",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["economics", "finance", "research"],
     "use": "working papers and economic research"},
    {"id": "cepr", "label": "CEPR", "domain": "cepr.org",
     "region": "Europe", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["economics", "research"], "use": "economic policy research"},
    {"id": "voxeu", "label": "VoxEU", "domain": "voxeu.org",
     "region": "Europe", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["economics", "research"], "use": "economic policy commentary"},
    {"id": "brookings", "label": "Brookings Institution", "domain": "brookings.edu",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["economics", "law", "management", "country"],
     "use": "policy and economic research"},
    {"id": "piie", "label": "Peterson Institute for International Economics", "domain": "piie.com",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["economics", "law", "country"],
     "use": "trade and international economics"},
    {"id": "bruegel", "label": "Bruegel", "domain": "bruegel.org",
     "region": "Europe", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["economics", "country"], "use": "European economic policy"},
    {"id": "ourworldindata", "label": "Our World in Data", "domain": "ourworldindata.org",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["economics", "health", "environment", "country", "research"],
     "use": "long-run country and development data"},
    {"id": "gapminder", "label": "Gapminder", "domain": "gapminder.org",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["economics", "country", "research"],
     "use": "country development data"},
    {"id": "icpsr", "label": "ICPSR (University of Michigan)", "domain": "icpsr.umich.edu",
     "region": "Global", "tier": "data", "category": "social", "academic_fit": "research",
     "access": "mixed", "topics": ["research", "people", "economics", "country"],
     "use": "social-science data archive"},
    {"id": "datagov", "label": "Data.gov", "domain": "data.gov",
     "region": "US", "tier": "data", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["country", "economics", "research"],
     "use": "US open government data"},
    {"id": "unstats", "label": "UN Statistics Division", "domain": "unstats.un.org",
     "region": "Global", "tier": "data", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["country", "economics", "people"],
     "use": "cross-national official statistics"},
    # Operations and supply chain
    {"id": "ascm", "label": "ASCM (APICS)", "domain": "ascm.org",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["supply_chain", "operations"],
     "use": "supply-chain standards and research"},
    {"id": "cscmp", "label": "CSCMP", "domain": "cscmp.org",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["supply_chain", "operations"],
     "use": "logistics and supply-chain research"},
    {"id": "ism", "label": "Institute for Supply Management", "domain": "ism.ws",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["supply_chain", "operations"],
     "use": "purchasing and supply management"},
    {"id": "mitctl", "label": "MIT Center for Transportation and Logistics", "domain": "ctl.mit.edu",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["supply_chain", "operations", "research"],
     "use": "logistics and supply-chain research"},
    {"id": "lpi", "label": "World Bank Logistics Performance Index", "domain": "lpi.worldbank.org",
     "region": "Global", "tier": "data", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["supply_chain", "operations", "country"],
     "use": "country logistics performance"},
    # People and organisation
    {"id": "shrm", "label": "SHRM", "domain": "shrm.org",
     "region": "US", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "mixed", "topics": ["people", "management"], "use": "HR practice and research"},
    {"id": "cipd", "label": "CIPD", "domain": "cipd.org",
     "region": "Europe", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "mixed", "topics": ["people", "management"], "use": "people profession research"},
    {"id": "gallup", "label": "Gallup", "domain": "gallup.com",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "mixed", "topics": ["people", "research", "marketing"],
     "use": "workplace and public-opinion research"},
    # Entrepreneurship
    {"id": "kauffman", "label": "Kauffman Foundation", "domain": "kauffman.org",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["entrepreneurship", "research"],
     "use": "entrepreneurship research"},
    {"id": "cbinsights", "label": "CB Insights", "domain": "cbinsights.com",
     "region": "Global", "tier": "data", "category": "company", "academic_fit": "background",
     "access": "mixed", "topics": ["entrepreneurship", "technology", "company", "industry"],
     "use": "startup and venture data"},
    {"id": "crunchbase", "label": "Crunchbase", "domain": "crunchbase.com",
     "region": "Global", "tier": "data", "category": "company", "academic_fit": "background",
     "access": "mixed", "topics": ["entrepreneurship", "technology", "company"],
     "use": "startup funding and company data"},
    {"id": "pitchbook", "label": "PitchBook", "domain": "pitchbook.com",
     "region": "Global", "tier": "data", "category": "company", "academic_fit": "background",
     "access": "paywalled", "topics": ["entrepreneurship", "finance", "company"],
     "use": "private-market and venture data"},
    {"id": "startupgenome", "label": "Startup Genome", "domain": "startupgenome.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["entrepreneurship", "technology", "country"],
     "use": "startup ecosystems"},
    # Technology and innovation
    {"id": "uspto", "label": "USPTO", "domain": "uspto.gov",
     "region": "US", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["technology", "law", "research"],
     "use": "patents and trademarks"},
    {"id": "epo", "label": "European Patent Office", "domain": "epo.org",
     "region": "Europe", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["technology", "law", "research"],
     "use": "patents and innovation data"},
    {"id": "nist", "label": "NIST", "domain": "nist.gov",
     "region": "US", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "free", "topics": ["technology", "operations", "research"],
     "use": "standards and measurement"},
    {"id": "technologyreview", "label": "MIT Technology Review", "domain": "technologyreview.com",
     "region": "Global", "tier": "news", "category": "economic", "academic_fit": "background",
     "access": "mixed", "topics": ["technology", "management", "research"],
     "use": "technology analysis"},
    {"id": "stanfordhai", "label": "Stanford HAI", "domain": "hai.stanford.edu",
     "region": "US", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "free", "topics": ["technology", "research", "management"],
     "use": "AI policy and research"},
    # Environment and sustainability
    {"id": "ipcc", "label": "IPCC", "domain": "ipcc.ch",
     "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["environment", "research", "country"],
     "use": "climate science assessments"},
    {"id": "unep", "label": "UN Environment Programme", "domain": "unep.org",
     "region": "Global", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["environment", "country"], "use": "environmental policy and data"},
    {"id": "iea", "label": "International Energy Agency", "domain": "iea.org",
     "region": "Global", "tier": "official", "category": "economic", "academic_fit": "primary",
     "access": "mixed", "topics": ["environment", "economics", "country"],
     "use": "energy data and policy"},
    {"id": "epa", "label": "US EPA", "domain": "epa.gov",
     "region": "US", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["environment", "health", "law"],
     "use": "US environmental regulation and data"},
    {"id": "wri", "label": "World Resources Institute", "domain": "wri.org",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "research",
     "access": "free", "topics": ["environment", "country", "research"],
     "use": "environment and development research"},
    {"id": "cdp", "label": "CDP", "domain": "cdp.net",
     "region": "Global", "tier": "data", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["environment", "finance", "company"],
     "use": "corporate climate disclosure"},
    {"id": "gri", "label": "Global Reporting Initiative", "domain": "globalreporting.org",
     "region": "Global", "tier": "research", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["environment", "accounting", "company"],
     "use": "sustainability reporting standards"},
    # Health
    {"id": "cdc", "label": "US CDC", "domain": "cdc.gov",
     "region": "US", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["health", "research"],
     "use": "public health data and guidance"},
    {"id": "nih", "label": "US National Institutes of Health", "domain": "nih.gov",
     "region": "US", "tier": "official", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["health", "research"], "use": "biomedical and health research"},
    {"id": "ihme", "label": "Institute for Health Metrics and Evaluation", "domain": "healthdata.org",
     "region": "Global", "tier": "data", "category": "social", "academic_fit": "primary",
     "access": "free", "topics": ["health", "country", "research"],
     "use": "global health burden data"},
    # Law and governance
    {"id": "unodc", "label": "UN Office on Drugs and Crime", "domain": "unodc.org",
     "region": "Global", "tier": "official", "category": "legal", "academic_fit": "primary",
     "access": "free", "topics": ["law", "ethics", "management"],
     "use": "corruption, crime and justice data"},
    {"id": "worldjustice", "label": "World Justice Project", "domain": "worldjusticeproject.org",
     "region": "Global", "tier": "research", "category": "legal", "academic_fit": "research",
     "access": "free", "topics": ["law", "country", "management"],
     "use": "rule-of-law index"},
    # Project and programme management
    {"id": "pmi", "label": "Project Management Institute", "domain": "pmi.org",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["project", "management"],
     "use": "project management standards and research"},
    {"id": "ipma", "label": "IPMA", "domain": "ipma.world",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "research",
     "access": "mixed", "topics": ["project", "management"],
     "use": "project management competence"},
    {"id": "axelos", "label": "AXELOS", "domain": "axelos.com",
     "region": "Global", "tier": "research", "category": "economic", "academic_fit": "background",
     "access": "mixed", "topics": ["project", "management", "technology"],
     "use": "PRINCE2 and ITIL practice"},
]


#: Canonical sources come first within a topic.  The number is not a
#: credibility claim; it is the order a researcher would try them: the primary
#: standards body before a regional bank, the encyclopedia before a consultancy.
SITE_PRIORITY = {
    "sep": 10, "iep": 9, "markkula": 8, "ibe": 8, "transparency": 8,
    "unglobalcompact": 7, "carnegiecouncil": 7,
    "hofstede": 10, "globe": 10, "hofstede-insights": 8, "afrobarometer": 8,
    "latinobarometro": 8, "worldvaluessurvey": 8, "unesco": 8, "pewresearch": 7,
    "sec": 10, "fasb": 10, "ifrs": 10, "cfainstitute": 8, "aicpa": 8,
    "annualreports": 7, "companieshouse": 8, "federalreserve": 9, "ecb": 9,
    "imf": 8, "worldbank": 8, "oecd": 7, "bis": 7,
    "congress": 9, "eurlex": 9, "curia": 8, "supremecourt": 8, "legislation-uk": 8,
    "who": 10, "cdc": 10, "nih": 9, "ihme": 8,
    "ipcc": 10, "unep": 9, "iea": 9, "epa": 9, "wri": 8, "cdp": 8, "gri": 8,
    "nber": 8, "cepr": 7, "voxeu": 7, "brookings": 7, "piie": 7, "bruegel": 7,
    "ourworldindata": 7, "gapminder": 6,
    "hbr": 8, "sloanreview": 7, "mckinsey": 7, "bcg": 7, "bain": 7,
    "deloitte": 6, "pwc": 6, "accenture": 6, "gartner": 7, "forrester": 7,
    "ama": 9, "nielsen": 8, "kantar": 8, "statista": 7, "ibisworld": 8,
    "euromonitor": 8, "mintel": 8, "warc": 7, "emarketer": 7,
    "ascm": 9, "cscmp": 9, "ism": 8, "mitctl": 9, "lpi": 8,
    "shrm": 9, "cipd": 8, "gallup": 7,
    "kauffman": 9, "cbinsights": 8, "crunchbase": 8, "pitchbook": 7, "startupgenome": 7,
    "uspto": 9, "epo": 9, "nist": 8, "technologyreview": 7, "stanfordhai": 8,
    "unodc": 8, "worldjustice": 8,
    "pmi": 9, "ipma": 8, "axelos": 7,
}


#: Existing news sites whose access was not recorded in the first registry.
SITE_ACCESS = {
    "reuters": "mixed", "ft": "paywalled", "bloomberg": "paywalled",
    "wsj": "paywalled", "economist": "paywalled", "scmp": "mixed",
    "caixin": "mixed", "arabnews": "free", "thenational": "mixed",
}


def _all_sites():
    """The full registry with defaults filled, one dict per site."""
    for site in list(VETTED_SITES) + list(TOPIC_SITES):
        item = dict(site)
        item.setdefault("topics", list(SITE_TOPICS.get(item["id"], [])))
        item.setdefault("access", SITE_ACCESS.get(item["id"], "free"))
        item.setdefault("category", SITE_CATEGORY.get(item["id"], "economic"))
        item.setdefault("priority", SITE_PRIORITY.get(item["id"], 0))
        item.setdefault("academic_fit", "background" if item["tier"] == "news"
                        else "research" if item["tier"] == "research" else "primary")
        yield item


#: A few strong cues per topic, used only where the dimension is generic
#: (`none` framework, key `evidence`).  They do not loosen a named dimension:
#: a PESTEL legal block still requires legal evidence, not ethics vocabulary.
TOPIC_CUES = {
    "ethics": ["ethic", "moral", "stakeholder", "integrity", "corruption", "csr"],
    "culture": ["culture", "cultural", "hofstede", "values", "cross-cultural"],
    "finance": ["finance", "financial", "valuation", "investment", "capital"],
    "accounting": ["accounting", "audit", "ifrs", "gaap", "reporting"],
    "marketing": ["marketing", "customer", "consumer", "brand", "retail"],
    "operations": ["operations", "process", "quality", "capacity", "inventory"],
    "supply_chain": ["supply", "logistics", "procurement", "supplier", "distribution"],
    "people": ["employee", "workforce", "leadership", "motivation", "training"],
    "entrepreneurship": ["entrepreneur", "startup", "venture", "sme", "founder"],
    "technology": ["technology", "digital", "innovation", "patent", "automation"],
    "environment": ["environment", "climate", "carbon", "sustainability", "emission"],
    "health": ["health", "healthcare", "patient", "medical", "hospital"],
    "law": ["law", "legal", "regulation", "compliance", "court"],
    "economics": ["economics", "economic", "gdp", "inflation", "trade"],
    "project": ["project", "programme", "pmo", "schedule", "milestone"],
    "industry": ["industry", "sector", "market", "competitor", "competition"],
    "company": ["company", "firm", "annual", "filing", "shareholder"],
    "country": ["country", "national", "region"],
    "research": ["research", "method", "statistics", "survey", "evidence"],
    "management": ["management", "strategy", "competitive", "governance", "change"],
    "news": ["news", "announcement", "press"],
}


def topic_cues(topic):
    """The strong cues of a topic, or an empty set for an unknown one."""
    key = SUBJECT_ALIASES.get(str(topic or "").lower().strip(), str(topic or "").lower().strip())
    if key not in TOPIC_CUES:
        key = topic_for_text(topic) or ""
    return set(TOPIC_CUES.get(key, []))


def topic_label(topic):
    """The readable label of a topic, or an empty string."""
    key = SUBJECT_ALIASES.get(str(topic or "").lower().strip(), str(topic or "").lower().strip())
    if key not in TOPICS:
        key = topic_for_text(topic) or ""
    row = TOPICS.get(key) or {}
    return row.get("label") or ""


def _keyword_hit(keyword, value):
    """A short token (`ai`, `hr`, `esg`) must be a whole word, not a substring.

    The first pass matched `ai` inside `chain`, so a supply-chain brief was
    classified as technology.  Longer phrases stay substring matches.
    """
    if len(keyword) <= 3:
        return re.search(r"\b%s\b" % re.escape(keyword), value) is not None
    return keyword in value


def topic_for_text(text):
    """The best topic for a brief or query, or None.

    The first topic with the most keyword hits wins.  The map is deliberately
    small and explicit: an unknown brief returns None and the caller falls back
    to the whole registry, never to a guessed subject.
    """
    value = str(text or "").lower()
    if not value:
        return None
    key = SUBJECT_ALIASES.get(value.strip(), value.strip())
    if key in TOPICS:
        return key
    best, best_hits = None, 0
    for topic, row in TOPICS.items():
        hits = sum(1 for keyword in row["keywords"] if _keyword_hit(keyword, value))
        if hits > best_hits:
            best, best_hits = topic, hits
    return best


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


def sites_for(topic=None, region=None, category=None, limit=15):
    """The vetted sites most relevant to a topic, best first.

    A topic is a pipeline subject id (`marketing`, `finance`) or a free-text
    brief (`business ethics`, `national culture`).  Sites that carry the topic
    are ranked first, then free before paywalled, then official/data over
    research over news.  The list is capped because a web search over fifty
    domains is slower and no more precise than one over fifteen.
    """
    wanted = set()
    value = str(topic or "").strip()
    if value:
        key = SUBJECT_ALIASES.get(value.lower(), value.lower())
        if key in TOPICS:
            wanted.add(key)
        else:
            inferred = topic_for_text(value)
            if inferred:
                wanted.add(inferred)

    def score(item):
        item_topics = item.get("topics") or []
        overlap = len(set(item_topics) & wanted)
        value = 40 + 5 * overlap if overlap else 0
        if item_topics and item_topics[0] in wanted:
            value += 6          # the site's own primary topic, not a side tag
        value += {"official": 6, "data": 6, "research": 5, "news": 2}.get(item["tier"], 1)
        value += {"free": 6, "mixed": 3, "paywalled": 0}.get(item.get("access", "free"), 0)
        value += int(item.get("priority") or 0)
        if region and region != "Global":
            if item["region"] == region:
                value += 4
            elif item["region"] == "Global":
                value += 1
        if category and item["category"] == category:
            value += 3
        return value

    sites = list(_all_sites())
    if region and region != "Global":
        sites = [site for site in sites if site["region"] in (region, "Global")]
    if wanted:
        matched = [site for site in sites if set(site.get("topics") or []) & wanted]
        # A well-covered topic is the list.  A thin one keeps the core data
        # sources below the matches so the paper still has country and market
        # evidence to fall back on.
        if len(matched) >= 5:
            sites = matched
    sites.sort(key=lambda item: (-score(item), item["domain"]))
    seen, out = set(), []
    for item in sites:
        domain = item["domain"].lower()
        if domain in seen:
            continue
        seen.add(domain)
        out.append(item)
        if len(out) >= max(1, int(limit)):
            break
    return out


def vetted_sites(region=None, tier=None, category=None, academic_fit=None,
                 topic=None, limit=15):
    """The vetted-site registry, optionally ranked for a topic.

    Without a topic the whole registry is returned and the old filters apply
    exactly as before.  With a topic the list is the ranked topic selection;
    category is a ranking signal there, not a hard filter, because an ethics
    source legitimately sits under `social` even when the block is economic.
    """
    if topic:
        sites = sites_for(topic, region=region, category=category, limit=limit)
    else:
        sites = list(_all_sites())
        if region and region != "Global":
            sites = [site for site in sites if site["region"] in (region, "Global")]
        if category:
            sites = [site for site in sites if site["category"] == category]
    if tier:
        sites = [site for site in sites if site["tier"] == tier]
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
    if item.get("database") == "Proprietary corpus":
        score += 25   # a curated corpus page earns a DOI's worth of signal
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
    # OpenAlex grants the polite pool (and avoids shared-IP 429s) only when the
    # request carries a contact address.
    params = {"search": query, "per-page": str(limit), "sort": "relevance_score:desc",
              "mailto": os.environ.get("BP_OPENALEX_EMAIL") or "research@example.com"}
    if os.environ.get("BP_OPENALEX_API_KEY"):
        params["api_key"] = os.environ["BP_OPENALEX_API_KEY"]
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


# ── the proprietary corpus adapter ──────────────────────────────────────────

#: Meilisearch connection details.  Stdlib urllib only — no Meilisearch SDK.
CORPUS_MEILI_URL = os.environ.get("CORPUS_MEILI_URL", "http://127.0.0.1:7700").rstrip("/")
CORPUS_MEILI_KEY = os.environ.get("CORPUS_MEILI_KEY", "")
CORPUS_INDEX = os.environ.get("CORPUS_INDEX", "pages")


def _corpus(query, limit, year_from):
    """The proprietary corpus: page-exact evidence from the local index.

    Fails open.  A corpus outage is a notice, never a failed run: an empty
    list means the live layers answer alone.
    """
    body = json.dumps({"q": query, "limit": limit}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if CORPUS_MEILI_KEY:
        headers["Authorization"] = "Bearer " + CORPUS_MEILI_KEY
    request = urllib.request.Request(
        "%s/indexes/%s/search" % (CORPUS_MEILI_URL, CORPUS_INDEX),
        data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=2.0) as response:
            hits = json.loads(response.read().decode("utf-8")).get("hits", [])
    except Exception:
        return []
    items = []
    for hit in hits:
        # A missing year is a metadata gap, not proof that the source is old.
        # Filtering it out here silently emptied the corpus whenever a period
        # was set: the page index carries no year for most books, so every
        # corpus hit was dropped before the relevance gate ever saw it.
        if year_from and hit.get("year") and (hit.get("year") or 0) < year_from:
            continue
        authors = [name.strip() for name in (hit.get("authors") or "").split(";") if name.strip()]
        item = _item(
            title=hit.get("title") or "",
            authors="; ".join(authors),
            authors_list=authors,
            year=hit.get("year"),
            abstract=hit.get("text") or "",       # the page text lives here
            doi=hit.get("doi"),
            url=hit.get("url"),
            venue=hit.get("venue") or "",
            database="Proprietary corpus",
            kind="proprietary",
            volume=hit.get("volume") or "",
            issue=hit.get("issue") or "",
            pages=hit.get("printed_page") or "",
            publisher=hit.get("publisher") or "",
            item_type="book" if hit.get("source_kind") == "book" else "journalArticle")
        # The unique page key.  Both dedup sites must prefer it (trap 2).
        item["corpus_key"] = "corpus:%s:%d" % (hit.get("doc_id"), hit.get("pdf_page"))
        item["doc_id"] = hit.get("doc_id")
        item["source_kind"] = hit.get("source_kind")
        item["pdf_page"] = hit.get("pdf_page")
        item["subject"] = hit.get("subject")
        items.append(item)
    return items


ADAPTERS = {"openalex": _openalex, "crossref": _crossref, "semanticscholar": _semanticscholar,
            "doaj": _doaj, "corpus": _corpus}

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


QUERY_STOP = set("a an the and or of to in on for with by at from as is are was were be been it its this that these those "
                  "study studies paper article analysis research evidence review case effect effects impact impacts role "
                  "using based toward towards new global".split())
MEDICAL = {"cancer", "clinical", "patient", "patients", "disease", "depression", "anxiety", "biosensor",
           "transplant", "therapy", "medical", "health", "childhood", "intervention", "trial"}


def _stem(word):
    word = word.lower()
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("s"):
        return word[:-1]
    return word


def _query_terms(query, limit=8):
    words = [_stem(word) for word in re.findall(r"[a-z][a-z0-9'-]+", (query or "").lower())]
    out = []
    for word in words:
        if len(word) < 3 or word in QUERY_STOP or word in out:
            continue
        out.append(word)
    return out[:limit]


def _query_match(query, item):
    terms = _query_terms(query)
    if not terms:
        return True
    title = (item.get("title") or "").lower()
    text = title + " " + (item.get("abstract") or item.get("description") or "").lower()
    words = {_stem(word) for word in re.findall(r"[a-z][a-z0-9'-]+", text)}
    hits = len(set(terms) & words)
    required = 2 if len(terms) >= 3 else 1
    if hits < required:
        return False
    query_words = {_stem(word) for word in re.findall(r"[a-z][a-z0-9'-]+", (query or "").lower())}
    if any(word in text for word in MEDICAL) and not (query_words & MEDICAL):
        return False
    return True


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
    results = [item for item in results if _query_match(text, item)]
    deduped = {}
    for item in results:
        # Trap 2: a corpus page carries a unique corpus_key, so two pages of the
        # same book do not collapse into one.  Fall back to DOI, then title.
        key = item.get("corpus_key") or item["doi"] or re.sub(r"[^a-z0-9]+", "", item["title"].lower())[:90]
        if key and key not in deduped:
            # Trap 4: never overwrite a credibility the adapter already set.
            # A corpus page has a stable identifier and earns its own score.
            item.setdefault("credibility", _credibility(item))
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
    date = _text(result.get("date"), 40)
    year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
    title = _text(result.get("title"), 300)
    title = re.sub(r"^(?:Table Data|Title|Data)\s*[-:|]\s*", "", title, flags=re.I).strip()
    title = title.split(" | ")[0].strip()
    description = _text(result.get("description") or result.get("snippet") or result.get("summary"), 500)
    # Scraped pages carry their own furniture ("Table Data -", "Title | ...",
    # "Date Range | ..."); it is not evidence and must not reach a citation.
    description = re.split(r"\s*(?:Title|Date Range|Table Data)\s*\|", description)[0].strip()
    description = re.sub(r"(?:\.\.\.|\u2026)+\s*$", "", description).strip()
    return {"title": title, "url": url, "description": description,
            "site": site["label"], "domain": host, "region": site["region"], "tier": site["tier"],
            "year": year, "authority": result.get("authority"),
            "search_score": result.get("rerank_score")}


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


def _site_query(text, sites, max_domains=4):
    domains = [site["domain"] for site in sites if site["tier"] in ("official", "data", "research")]
    for count in range(min(max_domains, len(domains)), 0, -1):
        query = text + " (" + " OR ".join("site:" + domain for domain in domains[:count]) + ")"
        if len(query) <= 128:
            return query
    return text


def _opencode_exe():
    found = shutil.which("opencode")
    if not found:
        return None
    path = Path(found)
    candidate = path.parent / "node_modules" / "opencode-ai" / "bin" / "opencode.exe"
    return str(candidate) if candidate.exists() else found


def _parse_opencode_results(stdout, sites, limit):
    out, seen = [], set()
    for line in (stdout or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get("part") or {}
        if event.get("type") != "tool_use" or part.get("tool") != "websearch":
            continue
        output = (part.get("state") or {}).get("output") or ""
        for block in re.split(r"\n\s*---\s*\n", output):
            title = re.search(r"^Title:\s*(.+)$", block, re.M)
            url = re.search(r"^URL:\s*(https?://\S+)", block, re.M)
            if not url:
                continue
            highlight = re.search(r"Highlights:\s*(.*)", block, re.S)
            item = _web_item({"title": title.group(1).strip() if title else "",
                              "url": url.group(1).strip(),
                              "summary": highlight.group(1).strip() if highlight else ""}, sites)
            if item and item["url"] not in seen:
                seen.add(item["url"])
                out.append(item)
    return out[:max(1, limit)]


def _opengo_web(text, sites, limit):
    """Run a headless OpenCode session and use its websearch tool.

    No OpenCode window is needed: `opencode run` starts its own headless
    server, uses the configured websearch provider, and exits.  The model is
    DeepSeek V4.1 Flash unless BP_LLM_MODEL overrides it.
    """
    if os.environ.get("BP_OPENGO_WEBSEARCH", "0") != "1":
        return [], {"provider": "opengo", "skipped": "BP_OPENGO_WEBSEARCH is not 1"}
    executable = _opencode_exe()
    if not executable:
        return [], {"provider": "opengo", "skipped": "opencode is not on PATH"}
    model = os.environ.get("BP_LLM_MODEL", "beam-free")
    count = min(max(limit * 3, 5), 10)
    prompt = ("Use the websearch tool with the query: %s. Return the top %d results. "
              "Do not answer from memory. Do not add commentary." % (text, count))
    try:
        timeout = max(10, int(os.environ.get("BP_OPENGO_TIMEOUT", "12")))
    except (TypeError, ValueError):
        timeout = 12
    try:
        process = subprocess.Popen(
            [executable, "run", "-m", "opencode-go/" + model, "--format", "json", "--auto", prompt],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            cwd=str(Path(__file__).resolve().parents[5]))
    except Exception as error:
        return [], {"provider": "opengo", "error": str(error)[:160]}
    lines = []
    lines_queue = queue.Queue()

    def read_lines():
        for line in process.stdout:
            lines_queue.put(line)
        lines_queue.put(None)

    threading.Thread(target=read_lines, daemon=True).start()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            line = lines_queue.get(timeout=0.5)
        except queue.Empty:
            if process.poll() is not None:
                break
            continue
        if line is None:
            break
        lines.append(line)
        if '"tool_use"' in line and '"websearch"' in line:
            break
    try:
        process.terminate()
        process.wait(timeout=3)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass
    out = _parse_opencode_results("".join(lines), sites, limit * 3)
    if not out:
        return [], {"provider": "opengo", "n": 0, "model": model,
                    "error": "no curated websearch result"}
    return out, {"provider": "opengo", "n": len(out), "model": model}


def _deepseek_web(text, sites, limit):
    """DeepSeek Search API ($0.75 per 1,000 successful searches)."""
    key = os.environ.get("BP_DEEPSEEK_API_KEY")
    if not key:
        return [], {"provider": "deepseek", "skipped": "BP_DEEPSEEK_API_KEY is not set"}
    payload = {"query": _site_query(text, sites), "count": min(max(limit * 3, 5), 20),
               "need_content": False}
    try:
        data = _post_json("https://api.deepseek.com/v1/tools/search", payload,
                          headers={"Authorization": "Bearer " + key}, timeout=12)
    except urllib.error.HTTPError as error:
        return [], {"provider": "deepseek", "error": "HTTP %s" % error.code}
    except Exception as error:
        return [], {"provider": "deepseek", "error": str(error)[:160]}
    rows = data.get("results") or []
    out = [item for item in (_web_item(result, sites) for result in rows if isinstance(result, dict)) if item]
    return out, {"provider": "deepseek", "n": len(out), "billable": bool(rows)}


INDUSTRY_SITES = [
    {"domain": "mckinsey.com", "label": "McKinsey", "tier": "research", "region": "Global"},
    {"domain": "hbr.org", "label": "Harvard Business Review", "tier": "research", "region": "Global"},
    {"domain": "statista.com", "label": "Statista", "tier": "data", "region": "Global"},
    {"domain": "reuters.com", "label": "Reuters", "tier": "news", "region": "Global"},
    {"domain": "ft.com", "label": "Financial Times", "tier": "news", "region": "Global"},
    {"domain": "economist.com", "label": "The Economist", "tier": "news", "region": "Global"},
    {"domain": "gartner.com", "label": "Gartner", "tier": "research", "region": "Global"},
    {"domain": "idc.com", "label": "IDC", "tier": "data", "region": "Global"},
    {"domain": "counterpointresearch.com", "label": "Counterpoint Research", "tier": "data", "region": "Global"},
    {"domain": "canalys.com", "label": "Canalys", "tier": "data", "region": "Global"},
    {"domain": "gsmaintelligence.com", "label": "GSMA Intelligence", "tier": "data", "region": "Global"},
    {"domain": "oecd.org", "label": "OECD", "tier": "official", "region": "Global"},
    {"domain": "worldbank.org", "label": "World Bank", "tier": "official", "region": "Global"},
]


def search_web(query, region="Global", limit=10, category=None, fast=False, sites=None,
               providers=None, topic=None):
    """Search curated domains: OpenGo, DeepSeek, Brave, Firecrawl.

    `fast` skips the headless OpenGo agent for multi-dimension research, where
    its 13-15 s model latency would stall the pass; DeepSeek Search is then first.
    `sites` overrides the vetted registry (framework research uses INDUSTRY_SITES)
    and `providers` fixes the order, because a general engine returns better
    industry articles than a site-filtered one.
    """
    text = (query or "").strip()
    if not text:
        return {"query": text, "results": [], "notice": "A search query is required.", "sites": []}
    custom = sites is not None
    site_list = sites if custom else vetted_sites(region, category=category, topic=topic)
    filter_sites = sites if custom else vetted_sites(category=category, topic=topic)
    # Two custom site lists must not share a cached answer, so the directory is
    # part of the key rather than only the word "custom".  The topic is part of
    # it too: the same words with a different priority list are a different search.
    directory = tuple((site.get("domain") or site.get("id") or str(site))
                      if isinstance(site, dict) else str(site) for site in site_list)
    key = ("web", text, region, limit, category, topic, "custom" if custom else "", directory)
    cached = _cache_get(key)
    if cached is not None:
        cached["cached"] = True
        return cached
    attempts, results = [], []
    seen = set()
    order = (("opengo", _opengo_web), ("deepseek", _deepseek_web),
             ("brave", _brave_web), ("firecrawl", _firecrawl_web))
    if providers:
        lookup = dict(order)
        order = tuple((name, lookup[name]) for name in providers if name in lookup)
    elif fast:
        order = order[1:]
    for _name, provider in order:
        found, attempt = provider(text, filter_sites, limit)
        attempts.append(attempt)
        for item in found:
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)
        if results:
            break
    results = results[:max(1, limit)]
    providers = [item.get("provider") for item in attempts if item.get("n")]
    provider = "+".join(dict.fromkeys(providers)) if providers else None
    notice = None
    if not results:
        notice = ("No curated web result came back. OpenGo, DeepSeek, Brave and Firecrawl were "
                  "unavailable or empty; the vetted-site directory is below.")
    payload = {"query": text, "results": results, "sites": site_list, "provider": provider,
               "attempts": attempts, "notice": notice, "cached": False}
    _cache_put(key, payload)
    return copy.deepcopy(payload)


def web_status():
    """Which web providers are usable, without exposing any key."""
    keyless = os.environ.get("BP_FIRECRAWL_KEYLESS", "1") != "0"
    return {"order": ["opengo", "deepseek", "brave", "firecrawl"],
            "opengo": bool(shutil.which("opencode")) and os.environ.get("BP_OPENGO_WEBSEARCH", "0") == "1",
            "opengo_research": os.environ.get("BP_OPENGO_RESEARCH", "0") == "1",
            "deepseek": bool(os.environ.get("BP_DEEPSEEK_API_KEY")),
            "brave": bool(os.environ.get("BP_BRAVE_API_KEY")),
            "firecrawl": bool(os.environ.get("BP_FIRECRAWL_API_KEY")) or keyless,
            "firecrawl_keyless": keyless}
