"""Retrieve evidence for one framework dimension (product layer).

One engine, two callers: the worksheet completion (`bp.product.completion`) and
the conductor's research (`bp.product.chat`).  Given the same framework, the
same brief, the same unit and the same region they return the same ranked
evidence, so the content a student sees cannot depend on which surface they
happen to use.  The framework supplies the words (cues, query phrases, which
source registry); this module supplies the search, the gate, the ranking and the
citation-ready item.  It writes no prose and no fact of its own.

The gate is deliberately stricter than "the abstract mentioned the word": a
candidate must carry a dimension cue in its title, and, when the framework's unit
of analysis is a country, it must carry the country too.  Everything that fails
is dropped and counted, never returned as if it were evidence.
"""

import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from . import sources as source_finder

#: The academic databases every dimension is searched in.
DATABASES = ["openalex", "semanticscholar", "doaj"]

#: How many accepted items one dimension may carry.  The manual documents
#: "one to three sourced items", and a fourth adds length without adding evidence.
MAX_ITEMS = 3

#: A candidate below this relevance score is dropped.
SCORE_FLOOR = 3


def clean(value, limit=400):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def first_sentence(source, sentences=1, limit=700):
    """The opening sentence(s) of an abstract, with HTML entities repaired."""
    text = clean(source.get("abstract") or source.get("description"), 1200)
    if not text:
        return ""
    text = (text.replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&")
            .replace("&#39;", "'").replace("&nbsp;", " "))
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        sentence = sentence.strip()
        if not sentence or "***" in sentence:
            continue
        kept.append(sentence)
        if len(kept) >= max(1, int(sentences)):
            break
    return " ".join(kept)[:limit]


#: Regions the source finder knows about.
REGIONS = ["Global", "US", "Europe", "Middle East", "China"]

#: Every sovereign state, because a student may write about any of them.  A short
#: list would recognise Iran and miss Morocco, which reads as a refusal of a
#: correct brief.  One letter case, one source: the chat and the worksheet both
#: call `country()`.
NAMES = (
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda",
    "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso",
    "Burundi", "Cabo Verde", "Cambodia", "Cameroon", "Canada", "Central African Republic",
    "Chad", "Chile", "China", "Colombia", "Comoros", "Congo", "Costa Rica", "Croatia", "Cuba",
    "Cyprus", "Czechia", "Democratic Republic of the Congo", "Denmark", "Djibouti", "Dominica",
    "Dominican Republic", "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea",
    "Estonia", "Eswatini", "Ethiopia", "Fiji", "Finland", "France", "Gabon", "Gambia", "Georgia",
    "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya",
    "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho",
    "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg", "Madagascar", "Malawi",
    "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
    "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco",
    "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand",
    "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway", "Oman",
    "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa",
    "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles",
    "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia",
    "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname",
    "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
    "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan",
    "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States",
    "Uruguay", "Uzbekistan", "Vanuatu", "Vatican City", "Venezuela", "Vietnam", "Yemen",
    "Zambia", "Zimbabwe",
)

#: Short forms, demonyms and the capitals a brief is likely to name instead of the
#: country.  A brief that says "in Nairobi" is a brief about Kenya.
ALIASES = {
    "United States": ("usa", "u.s.", "u.s.a.", "us", "america", "american",
                      "united states of america"),
    "United Kingdom": ("uk", "u.k.", "britain", "british", "great britain", "england",
                       "scotland", "wales", "northern ireland", "london"),
    "United Arab Emirates": ("uae", "u.a.e.", "emirates", "dubai", "abu dhabi", "sharjah"),
    "Saudi Arabia": ("saudi", "ksa", "riyadh", "jeddah"),
    "China": ("prc", "chinese", "beijing", "shanghai", "shenzhen"),
    "Czechia": ("czech republic", "prague"),
    "Ivory Coast": ("cote d'ivoire", "côte d'ivoire", "abidjan"),
    "Democratic Republic of the Congo": ("drc", "dr congo", "kinshasa"),
    "Congo": ("republic of the congo", "brazzaville"),
    "Myanmar": ("burma", "yangon"),
    "Netherlands": ("holland", "dutch", "amsterdam"),
    "South Korea": ("korea", "republic of korea", "seoul"),
    "North Korea": ("dprk", "pyongyang"),
    "Russia": ("russian federation", "moscow"),
    "Vietnam": ("viet nam", "hanoi", "ho chi minh city", "saigon"),
    "Morocco": ("moroccan", "rabat", "casablanca"),
    "Kenya": ("kenyan", "nairobi", "mombasa"),
    "Nigeria": ("nigerian", "lagos", "abuja"),
    "Egypt": ("egyptian", "cairo"),
    "Turkey": ("turkish", "turkiye", "türkiye", "istanbul", "ankara"),
    "Germany": ("german", "berlin", "munich", "frankfurt"),
    "France": ("french", "paris"),
    "India": ("indian", "mumbai", "delhi", "bangalore", "bengaluru"),
    "Iran": ("iranian", "tehran"),
    "Israel": ("israeli", "tel aviv", "jerusalem"),
    "Japan": ("japanese", "tokyo", "osaka"),
    "Brazil": ("brazilian", "sao paulo", "são paulo", "rio de janeiro"),
    "Mexico": ("mexican", "mexico city"),
    "Spain": ("spanish", "madrid", "barcelona"),
    "Italy": ("italian", "rome", "milan"),
    "Canada": ("canadian", "toronto", "ontario", "quebec", "vancouver"),
    "Australia": ("australian", "sydney", "melbourne"),
    "Indonesia": ("indonesian", "jakarta"),
    "Malaysia": ("malaysian", "kuala lumpur"),
    "Pakistan": ("pakistani", "karachi", "lahore", "islamabad"),
    "Bangladesh": ("bangladeshi", "dhaka"),
    "Sri Lanka": ("sri lankan", "colombo"),
    "Philippines": ("philippine", "filipino", "manila"),
    "Thailand": ("thai", "bangkok"),
    "Qatar": ("qatari", "doha"),
    "Kuwait": ("kuwaiti", "kuwait city"),
    "Oman": ("omani", "muscat"),
    "Bahrain": ("bahraini", "manama"),
    "Jordan": ("jordanian", "amman"),
    "Lebanon": ("lebanese", "beirut"),
    "Iraq": ("iraqi", "baghdad"),
    "Syria": ("syrian", "damascus"),
    "Yemen": ("yemeni", "sanaa"),
    "Poland": ("polish", "warsaw"),
    "Portugal": ("portuguese", "lisbon"),
    "Greece": ("greek", "athens"),
    "Ireland": ("irish", "dublin"),
    "Sweden": ("swedish", "stockholm"),
    "Norway": ("norwegian", "oslo"),
    "Denmark": ("danish", "copenhagen"),
    "Finland": ("finnish", "helsinki"),
    "Belgium": ("belgian", "brussels"),
    "Switzerland": ("swiss", "zurich", "geneva"),
    "Austria": ("austrian", "vienna"),
    "Hungary": ("hungarian", "budapest"),
    "Romania": ("romanian", "bucharest"),
    "Ukraine": ("ukrainian", "kyiv", "kiev"),
    "Peru": ("peruvian", "lima"),
    "Chile": ("chilean", "santiago"),
    "Colombia": ("colombian", "bogota", "bogotá"),
    "Argentina": ("argentinian", "argentine", "buenos aires"),
    "South Africa": ("south african", "johannesburg", "cape town", "pretoria"),
    "Ethiopia": ("ethiopian", "addis ababa"),
    "Ghana": ("ghanaian", "accra"),
    "Tanzania": ("tanzanian", "dar es salaam"),
    "Uganda": ("ugandan", "kampala"),
    "New Zealand": ("new zealander", "auckland", "wellington"),
}

COUNTRIES = [(name, (name.lower(),) + ALIASES.get(name, ())) for name in NAMES]

#: Only the five regions the source finder understands; anything else is Global,
#: which searches without a regional filter rather than pretending to a region.
REGION_OF = {
    "United States": "US", "China": "China",
    "Iran": "Middle East", "Iraq": "Middle East", "Israel": "Middle East", "Jordan": "Middle East",
    "Kuwait": "Middle East", "Lebanon": "Middle East", "Oman": "Middle East", "Qatar": "Middle East",
    "Saudi Arabia": "Middle East", "Syria": "Middle East", "Yemen": "Middle East",
    "United Arab Emirates": "Middle East", "Bahrain": "Middle East", "Turkey": "Middle East",
    "Egypt": "Middle East", "Palestine": "Middle East", "Cyprus": "Middle East",
    "Albania": "Europe", "Andorra": "Europe", "Austria": "Europe", "Belarus": "Europe",
    "Belgium": "Europe", "Bosnia and Herzegovina": "Europe", "Bulgaria": "Europe",
    "Croatia": "Europe", "Czechia": "Europe", "Denmark": "Europe", "Estonia": "Europe",
    "Finland": "Europe", "France": "Europe", "Germany": "Europe", "Greece": "Europe",
    "Hungary": "Europe", "Iceland": "Europe", "Ireland": "Europe", "Italy": "Europe",
    "Kosovo": "Europe", "Latvia": "Europe", "Liechtenstein": "Europe", "Lithuania": "Europe",
    "Luxembourg": "Europe", "Malta": "Europe", "Moldova": "Europe", "Monaco": "Europe",
    "Montenegro": "Europe", "Netherlands": "Europe", "North Macedonia": "Europe",
    "Norway": "Europe", "Poland": "Europe", "Portugal": "Europe", "Romania": "Europe",
    "Russia": "Europe", "San Marino": "Europe", "Serbia": "Europe", "Slovakia": "Europe",
    "Slovenia": "Europe", "Spain": "Europe", "Sweden": "Europe", "Switzerland": "Europe",
    "Ukraine": "Europe", "United Kingdom": "Europe", "Vatican City": "Europe",
}

GEO_WORDS = {
    "US": {"united states", "u.s.", "america", "american", "federal", "washington"},
    "Europe": {"europe", "european", "eu", "eurozone", "uk", "britain", "germany", "france",
               "italy", "spain", "netherlands", "poland", "portugal", "greece", "ireland",
               "sweden", "norway", "denmark", "finland", "belgium", "switzerland", "austria",
               "czechia", "romania", "hungary", "ukraine"},
    "Middle East": {"middle east", "gulf", "gcc", "saudi", "saudi arabia", "uae", "emirates",
                    "qatar", "kuwait", "bahrain", "oman", "israel", "turkey", "egypt", "jordan",
                    "lebanon", "iraq", "iran", "syria", "yemen", "palestine"},
    "China": {"china", "chinese", "prc", "beijing", "shanghai", "shenzhen"},
}

STOP = set(
    "a an the and or of to in on for with by at from as is are was were be been it its this that these those "
    "we our us you your i my me they their them not no do does did can could should would will may might have "
    "has had how what when where which who why if then than so such about into over under between among after "
    "before during each per via also more most much many some any other another own same very".split())

GENERIC_TOPIC = {"market", "markets", "business", "company", "firm", "firms", "entry", "enter",
                 "product", "products", "service", "services", "industry", "global", "international"}

#: Clinical and consumer-behaviour vocabulary that fills external-environment
#: blocks with papers about something else entirely.  The health exception keeps a
#: health-sector brief from losing its own evidence.
BLOCKED = ("biosensor", "patients", "clinical", "depressive", "anxiety", "athletes",
           "food contaminant", "intervention", "childhood", "therapy", "asylum", "migrants",
           "eco-friendly", "eco friendly", "marketed effectively", "recycling", "green marketing")


def country(text):
    """The country named in a brief, or an empty string."""
    lower = (text or "").lower()
    for name, aliases in COUNTRIES:
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", lower):
                return name
    return ""


def region(name):
    """The source-finder region a country belongs to."""
    return REGION_OF.get(name or "", "Global")


def geo_words(geography):
    return set(GEO_WORDS.get(geography or "", set()))


def topic_words(text, limit=10):
    return [word for word in re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower())
            if len(word) >= 3 and word not in STOP][:limit]


def specific_words(words):
    """Topic words without the ones that say nothing about this case."""
    out = set()
    for word in set(words) - GENERIC_TOPIC:
        out.add(word)
        if word.endswith("ian") and len(word) > 4:
            out.add(word[:-3])
    return out


def context_words(text, limit=4):
    """The words that identify the unit of analysis: a country, an industry, a topic."""
    seen, out = set(), []
    for word in re.findall(r"[a-z][a-z0-9']+", (text or "").lower()):
        if len(word) < 3 or word in STOP or word in seen:
            continue
        seen.add(word)
        out.append(word)
    return out[:limit]


def build_query(phrase, context="", geography="Global", fallback=""):
    """The one query shape both callers use: the unit, then the words, then the region.

    The unit comes first so a country-qualified brief always searches its own
    country first (the chat's recorded plan asserts this).
    """
    words = phrase or fallback
    parts = [context, words]
    if geography and geography not in ("Global", ""):
        parts.append(geography)
    return clean(" ".join(part for part in parts if part), 300)


def _recency(item):
    try:
        year = int(item.get("year") or 0)
    except (TypeError, ValueError):
        year = 0
    current = datetime.datetime.now(datetime.timezone.utc).year
    if not year:
        return 0
    return 2 if year >= current - 2 else (1 if year >= current - 5 else 0)


def _source_weight(item):
    if item.get("tier") in ("official", "data"):
        return 3
    if item.get("database") in ("OpenAlex", "Semantic Scholar", "DOAJ", "Crossref",
                                "Proprietary corpus"):
        return 2
    return 1


def _stem(word):
    """A crude English stem, so a cue matches the inflection a title uses.

    The cue says "sustain"; the paper says "sustaining".  Without a stem the
    gate cannot see that the source is on the dimension, and refuses it.
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4 and word[-3] in "sxzo":
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    if word.endswith("ing") and len(word) > 5:
        base = word[:-3]
        if len(base) > 3 and base[-1] == base[-2]:
            base = base[:-1]
        elif base.endswith("z"):
            base += "e"
        return base
    if word.endswith("ed") and len(word) > 4:
        base = word[:-2]
        if len(base) > 3 and base[-1] == base[-2]:
            base = base[:-1]
        return base
    return word


def _expand(words):
    """Every form of a word the gate should see: itself, its stem, its parts.

    A hyphenated title word carries the cue it is built from: a title that says
    "costly-to-imitate" holds the cue "costly" and the cue "imitate".  The
    parts are only added when they are long enough to be a word in their own
    right, so "to" does not become a cue of its own.
    """
    out = set()
    for word in words:
        out.add(word)
        out.add(_stem(word))
        if "-" in word:
            for part in word.split("-"):
                if len(part) >= 3:
                    out.add(part)
                    out.add(_stem(part))
    return out


def _is_health_context(context_set):
    """True when the unit of analysis is a health context.

    The blocked-word list refuses clinical and consumer-behaviour papers so
    they cannot fill a block about something else.  A health-sector brief must
    keep its own evidence, so the exception covers "healthcare" and "health
    care" as well as "health".
    """
    for word in context_set or ():
        if word == "health" or word.startswith("health"):
            return True
    return False


def relevance(item, cue_words, context_set, geography="Global", limit=2000):
    """Score one candidate, or None when the gate refuses it.

    The gate is the same for every framework; the profile decides how strict the
    context rule is and whether the country must appear.
    """
    title = clean(item.get("title"), 400).lower()
    body = title + " " + clean(item.get("abstract") or item.get("description"), limit).lower()
    words = _expand(set(re.findall(r"[a-z][a-z0-9'-]+", body)))
    title_words = _expand(set(re.findall(r"[a-z][a-z0-9'-]+", title)))
    cues = _expand({word for word in (cue_words or set()) if word})
    context = _expand({word for word in (context_set or set()) if word})
    cue_hits = len(cues & words)
    title_cues = len(cues & title_words)
    context_hits = len(context & words)
    title_context = len(context & title_words)
    geo = geo_words(geography) if geography not in ("Global", "") else set()
    geo_hits = sum(1 for phrase in geo if phrase in body)
    return {"cue_hits": cue_hits, "title_cues": title_cues, "context_hits": context_hits,
            "title_context": title_context, "geo_hits": geo_hits}


def rank_item(item, score, cue_words, context_set):
    """Precision ranking: relevance, title match, specificity, source tier, recency."""
    title = clean(item.get("title"), 400).lower()
    title_words = _expand(set(re.findall(r"[a-z][a-z0-9'-]+", title)))
    cues = _expand({word for word in (cue_words or set()) if word})
    context = _expand({word for word in (context_set or set()) if word})
    return (score + 2 * len(cues & title_words) + 2 * len(context & title_words)
            + _recency(item) + _source_weight(item) + (item.get("credibility") or 0) / 100)


def gate_of(profile_gate=None):
    """The gate with its defaults, so a profile only states what differs."""
    gate = {"min_score": SCORE_FLOOR, "title_cue": True, "title_context": False,
            "require_geography": True, "blocked": BLOCKED}
    gate.update(profile_gate or {})
    return gate


def _accept(item, cue_words, context_set, geography, gate):
    """The score for an accepted candidate, or None."""
    seen = relevance(item, cue_words, context_set, geography)
    if not seen["cue_hits"]:
        return None
    # Trap 1: a full-text source (the corpus) is judged on the passage it
    # quotes, not on the book's title.  One cue hit in the body is enough, and
    # the title alone is never sufficient.  Abstract-only sources keep the
    # title rule exactly as it is (D-10 / B-168).
    full_text = item.get("database") == "Proprietary corpus"
    if not full_text and gate["title_cue"] and not seen["title_cues"] and seen["cue_hits"] < 3:
        return None
    if context_set:
        if gate["title_context"] and not seen["title_context"]:
            return None
        if not gate["title_context"] and not seen["context_hits"]:
            return None
    if gate["require_geography"] and geography not in ("Global", "") and not seen["geo_hits"]:
        return None
    title = clean(item.get("title"), 400).lower()
    blocked = gate.get("blocked") or ()
    if (any(word in title for word in blocked)
            and not _is_health_context(context_set)):
        return None
    score = (2 * seen["cue_hits"] + 2 * (1 if seen["geo_hits"] else 0) + seen["context_hits"]
             + 2 * seen["title_cues"] + 2 * seen["title_context"])
    score = rank_item(item, score, cue_words, context_set)
    if score < gate["min_score"]:
        return None
    return score


def key_of(item):
    """The identity of a source: its corpus page key when it has one, its DOI
    otherwise, its title as a last resort.  A corpus page key is unique per
    page, so two pages of the same book do not collapse into one (trap 2)."""
    corpus_key = item.get("corpus_key")
    if corpus_key:
        return corpus_key
    return (clean(item.get("doi"), 80).lower() or clean(item.get("title"), 160).lower())


def _key(item):
    return key_of(item)


#: Where the corpus admin service listens.  Fail-soft: never block a paper run.
LEARNING_LOG_URL = os.environ.get("CORPUS_LEARNING_LOG_URL",
                                  "http://127.0.0.1:7710/api/corpus/log")
#: A test run must not write its fixtures into the real corpus history.
LEARNING_LOG_ENABLED = os.environ.get("BP_LEARNING_LOG", "1") != "0"


def _log_learning(query="", subject=None, dimension=None, corpus_hits=0,
                  live_hits=0, sources=None, web_sources=None):
    """Write one retrieval to the corpus learning log.  Fail-soft: never raise.

    The pipeline writes through one HTTP route on the admin service (D-23),
    never by importing corpus_lib across the repo boundary.  A one-second
    timeout keeps a stopped container from stalling a paper run.
    """
    if not LEARNING_LOG_ENABLED:
        return
    payload = {
        "query": query or "",
        "subject": subject,
        "dimension": dimension,
        "case_id": None,
        "corpus_hits": int(corpus_hits or 0),
        "live_hits": int(live_hits or 0),
        "corpus_status": "ok",
        "sources": sources or [],
        "web_sources": web_sources or [],
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        LEARNING_LOG_URL, data=body,
        headers={"Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=1.0):
            pass
    except Exception:
        # The learning log is a signal, not evidence.  A failure here is
        # swallowed and never reaches the page.
        pass


def cue_words_of(cues):
    """The cue words of a declaration, whether it is a string or a list.

    A profile that declared ``cues`` as a list of words produced the single token
    ``"['evidence']"`` once it was coerced with ``str()``, so no title could ever match
    and the block could never carry evidence — a cell that was silently always a gap
    (D-MGT-12, found by driving the canvas profiles with a title that echoes their own
    query).  A list is a legitimate declaration; it is read here.
    """
    if isinstance(cues, (list, tuple, set)):
        words = " ".join(str(word) for word in cues)
    else:
        words = str(cues or "")
    return {word for word in clean(words, 400).split() if word}


#: Background reading.  Wikipedia is free, fast and broad enough to orient most
#: business topics; it is never cited.
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
ORIENTATION_USER_AGENT = "SmartBusinessWriter/1.0 (background reading)"
ORIENTATION_ENABLED = os.environ.get("BP_ORIENTATION", "1") != "0"


def _orientation(query, limit=3):
    """A few encyclopedia pages about the topic, or an empty list.

    This is the fast web layer: it runs only when the corpus missed, it never
    blocks a paper run, and nothing it returns is evidence.  The pipeline uses
    it to know what the topic looks like; the renderer is never given it.
    """
    if not query or not ORIENTATION_ENABLED:
        return {"results": [], "notice": None}
    params = {"action": "query", "list": "search", "srsearch": query,
              "srlimit": str(max(1, int(limit))), "format": "json", "utf8": "1",
              "srprop": "snippet"}
    request = urllib.request.Request(
        WIKIPEDIA_API + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": ORIENTATION_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        return {"results": [], "notice": "Background reading unavailable: %s" % str(error)[:120]}
    results = []
    for row in (payload.get("query") or {}).get("search") or []:
        title = clean(row.get("title"), 200)
        if not title:
            continue
        results.append({
            "title": title,
            "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
            "abstract": re.sub(r"<[^>]+>", "", row.get("snippet") or ""),
            "database": "orientation web",
            "citable": False,
            "credibility": 0,
        })
    return {"results": results, "notice": None}


def _accepted_any(found, cue_words, context_set, geography, gate, exclude):
    """True when at least one candidate clears the relevance gate."""
    seen = set()
    for item in found:
        item_key = _key(item)
        if not item_key or item_key in seen or item_key in exclude:
            continue
        seen.add(item_key)
        if _accept(item, cue_words, context_set, geography, gate) is not None:
            return True
    return False


def _web_item(item):
    """A vetted web result as a retrieval candidate."""
    return {"title": item.get("title"), "abstract": item.get("description"),
            "authors": item.get("site"), "authors_list": [item.get("site")],
            "year": item.get("year"), "venue": item.get("site"), "doi": None,
            "url": item.get("url"), "database": "vetted web",
            "tier": item.get("tier"), "credibility": 60,
            "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def retrieve(key, cues, queries, context, geography="Global", year_from=None, category=None,
             sites=None, providers=None, gate=None, exclude=None, max_items=MAX_ITEMS,
             academic_limit=4, corpus_limit=4, web_limit=3, corpus_doc_cap=3,
             corpus_doc_counts=None):
    """Retrieve, gate and rank the evidence for one dimension.

    The order is fixed and cheap first:

    1. **The owned corpus.**  It is searched alone.  When it answers the
       dimension, nothing else is called: a corpus page is citable evidence,
       and a journal-API call would only duplicate it (D-09 / B-168).
    2. **The web**, only when the corpus missed.  Vetted pages may be cited;
       general pages (Wikipedia, explainers) are background reading and are
       never cited.
    3. **The journal APIs**, last and slow, only when neither the corpus nor
       the vetted web supplied a citable source.

    Everything seen, accepted or not, is written to the corpus learning log so
    the enrichment worker can store it for a future run.

    `corpus_doc_cap` limits how many pages one corpus document may contribute
    to a single paper (Q-16).  `corpus_doc_counts` is a shared dict mapping
    doc_id to accepted count, threaded across dimensions so the cap holds
    per-paper, not per-call.
    """
    gate = gate_of(gate)
    exclude = exclude if exclude is not None else set()
    corpus_doc_counts = corpus_doc_counts if corpus_doc_counts is not None else {}
    cue_words = cue_words_of(cues)
    context_set = {word for word in context or [] if word}
    started = time.perf_counter()
    queries = [query for query in queries or [] if query]
    errors, skipped, notices = [], [], []
    academic_cached, web_cached, timings = False, False, {}
    layers = {"corpus": 0, "web": 0, "api": 0}

    # ── layer 1: the owned corpus, alone and first ──────────────────────────
    corpus_found = []
    for query in queries:
        try:
            corpus = source_finder.search_academic(query, databases=["corpus"],
                                                   limit=corpus_limit, year_from=year_from)
        except Exception as error:  # a corpus outage is a notice, never a failure
            notices.append("corpus search unavailable: %s" % str(error)[:160])
            corpus = {}
        corpus_found.extend(corpus.get("results") or [])
    layers["corpus"] = len(corpus_found)
    corpus_answer = _accepted_any(corpus_found, cue_words, context_set, geography, gate, exclude)

    if corpus_answer:
        found = corpus_found
        source_plan = "corpus"
    else:
        # ── layer 2: the web, only on a corpus miss ─────────────────────────
        web_items = []
        if queries:
            web = _web(queries[0], geography, web_limit, category, sites, providers)
            web_items = [_web_item(item) for item in web.get("results") or []]
            web_cached = bool(web.get("cached"))
            if web.get("notice"):
                notices.append(web["notice"])
        layers["web"] = len(web_items)
        web_answer = _accepted_any(web_items, cue_words, context_set, geography, gate, exclude)
        if web_answer:
            found = web_items
            source_plan = "web"
        else:
            # ── layer 3: the journal APIs, last and slow ────────────────────
            api_items = []
            for index, query in enumerate(queries):
                try:
                    academic = source_finder.search_academic(
                        query, databases=DATABASES, limit=academic_limit, year_from=year_from)
                except Exception as error:  # a database outage is reported, not hidden
                    errors.append({"database": "academic", "error": str(error)[:160]})
                    academic = {}
                api_items.extend(academic.get("results") or [])
                errors.extend(academic.get("errors") or [])
                skipped.extend(academic.get("skipped") or [])
                academic_cached = academic_cached or bool(academic.get("cached"))
                if index == 0:
                    timings = dict(academic.get("timings") or {})
            layers["api"] = len(api_items)
            found = web_items + api_items
            source_plan = "api" if api_items else "none"

    scored, seen = [], set()
    orientation = []
    orientation_seen = set()
    dropped = 0
    if source_plan != "corpus" and queries:
        # Background reading: the fast web answer to "what is this about?".
        # It never enters the evidence list and never reaches a reference.
        general = _orientation(queries[0])
        for item in general.get("results") or []:
            item_key = item.get("url") or _key(item)
            if item_key and item_key not in orientation_seen:
                orientation_seen.add(item_key)
                orientation.append(item)
        if general.get("notice"):
            notices.append(general["notice"])
    for item in found:
        item_key = _key(item)
        if not item_key or item_key in seen or item_key in exclude:
            dropped += 1
            continue
        seen.add(item_key)
        score = _accept(item, cue_words, context_set, geography, gate)
        if score is None:
            dropped += 1
            continue
        # A source that clears the relevance gate but is weakly relevant is
        # kept as background reading.  It informs the plan, it is never cited.
        if score < max(gate.get("min_score", SCORE_FLOOR) + 2, 5):
            if item_key not in orientation_seen:
                orientation_seen.add(item_key)
                orientation.append(item)
            continue
        scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    items = []
    for _score, item in scored[:max(1, int(max_items))]:
        # Q-16: one document may not supply every dimension of a paper.
        # Cap corpus pages per doc_id; live sources are not capped.
        if item.get("database") == "Proprietary corpus":
            doc_id = item.get("doc_id")
            if doc_id and corpus_doc_counts.get(doc_id, 0) >= corpus_doc_cap:
                dropped += 1
                continue
        exclude.add(_key(item))
        items.append(item)
        if item.get("database") == "Proprietary corpus":
            doc_id = item.get("doc_id")
            corpus_doc_counts[doc_id] = corpus_doc_counts.get(doc_id, 0) + 1
    # Learning hook: every source this retrieval saw is recorded, not only the
    # accepted ones.  The candidates the gate refused are exactly the works the
    # corpus does not hold, so they are the demand the enrichment worker fills.
    used_keys = {_key(item) for item in items}
    corpus_used = sum(1 for item in items
                      if item.get("corpus_key") or item.get("database") == "Proprietary corpus")
    logged = found + orientation
    _log_learning(
        query=" || ".join(queries) if queries else "",
        subject=geography if geography not in ("Global", "") else None,
        dimension=key,
        corpus_hits=corpus_used,
        live_hits=len(items) - corpus_used,
        sources=[{
            "title": item.get("title"),
            "doi": item.get("doi"),
            "url": item.get("url"),
            "venue": item.get("venue"),
            "year": item.get("year"),
            "abstract": first_sentence(item, 1, 500) or None,
            "source": item.get("database") or "unknown",
            "database": item.get("database"),
            "source_kind": item.get("source_kind"),
            "used": 1 if _key(item) in used_keys else 0,
        } for item in logged],
        web_sources=[{
            "url": item.get("url"),
            "title": item.get("title"),
            "summary": first_sentence(item, 1, 500) or item.get("abstract"),
            "domain": item.get("domain"),
        } for item in logged
            if item.get("url")
            and item.get("database") in ("vetted web", "orientation web")],
    )
    return {"key": key, "items": items, "orientation": orientation, "queries": queries,
            "dropped": dropped, "errors": errors, "skipped": skipped, "notices": notices,
            "academic_cached": academic_cached, "web_cached": web_cached,
            "database_timings": timings, "layers": layers, "source_plan": source_plan,
            "elapsed": round(time.perf_counter() - started, 2)}


def _web(query, geography, limit, category, sites, providers):
    """Search the curated web; never raise, and never hold a dimension hostage."""
    try:
        if sites:
            return source_finder.search_web(query, geography, limit, category, True,
                                            sites=sites, providers=providers) or {}
        return source_finder.search_web(query, geography, limit, category, True) or {}
    except Exception as error:
        return {"results": [], "errors": [], "notice": "Web search failed: " + str(error)[:120]}
