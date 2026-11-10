"""RRA Stage S1 — Scout.

Fetches pages from allowlisted domains.  Respects robots.txt and terms of
service.  Flags paywalls (never bypasses).  Stores hash + timestamp; does
not store full page copies (D-8: hash + short excerpt only).

Returns a list of raw snapshot dicts: {url, domain, fetched_at, sha256,
status_code, paywalled, text_excerpt, error}.
"""
import hashlib
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .schemas import _is_blocked_domain, BLOCKED_DOMAINS

_USER_AGENT = ("Mozilla/5.0 (compatible; SmartBusinessWriter-RRA/1.0; research)")
_TIMEOUT = 15

#: How much of the response is read.  A page is usually larger than 100 KB of
#: markup, and the cut falls in the middle of the body: the header, the logo
#: and the script block fill the first 100,000 characters, so a 100 KB read
#: returned the chrome and lost the course description.  The owner's own
#: Phase 1 probe read 400 KB and read the frameworks; this is that number.
FETCH_CAP_CHARS = 400000

#: How much of a fetched page is kept for reading.  The full body is never
#: stored: only the hash and a short excerpt reach the evidence store.
#:
#: This counts **readable characters**, not raw markup.  A cap applied to the
#: raw HTML cuts the page at a fixed byte offset, and a page whose first
#: 20,000 characters are a logo, a script block and a navigation bar loses
#: its body entirely — the reader then sees a few hundred characters of
#: chrome and no course description.  The text is stripped first and capped
#: after, so the reader is given the words.
MAX_TEXT_CHARS = 20000


def _domain_of(url):
    parsed = urllib.parse.urlparse(str(url or ""))
    host = parsed.hostname or ""
    return host.lower()


def _is_allowed(domain, allowlist):
    """Check if a domain is on the allowlist.  Blocked domains are always rejected."""
    domain = str(domain or "").lower()
    if _is_blocked_domain(domain):
        return False, "blocked domain"
    if not allowlist or not isinstance(allowlist, dict):
        return False, "no allowlist provided"
    for entry in (allowlist.get("allowed") or []):
        allowed_domain = str(entry.get("domain", "")).lower()
        if domain == allowed_domain or domain.endswith("." + allowed_domain):
            return True, entry.get("tier", "T3")
    return False, "domain not on allowlist"


def _fetch_url(url):
    """Fetch a URL.  Returns (status_code, text, error).  Respects timeout."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            status = resp.getcode()
            raw = resp.read(FETCH_CAP_CHARS)
            # try decode
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                text = raw.decode("latin-1", errors="replace")
            return status, text, ""
    except urllib.error.HTTPError as e:
        return e.code, "", "HTTP %d" % e.code
    except urllib.error.URLError as e:
        return 0, "", "URL error: %s" % str(e.reason)
    except Exception as e:
        return 0, "", "fetch error: %s" % str(e)[:200]


def _detect_paywall(text, status_code):
    """Heuristic paywall detection.  Returns True if likely paywalled."""
    if status_code in (401, 402, 403):
        return True
    low = str(text or "").lower()
    paywall_signals = [
        "subscribe to continue", "subscribe to read", "sign in to continue",
        "create an account to read", "this content is for subscribers",
        "paywall", "premium content", "members only",
    ]
    return any(sig in low for sig in paywall_signals)


def _detect_challenge(text, status_code):
    """Is this a bot-check page rather than the page the URL names?

    Some sites answer a fetch with a JavaScript challenge ("confirm you are
    human") and a 202 status.  The body is not the course catalogue, and
    storing it as the page's text would put words in the evidence store
    that the school never wrote about the framework.  Such a page is named
    as unreadable instead.
    """
    if status_code not in (202, 429, 503):
        return False
    low = str(text or "").lower()[:2000]
    signals = [
        "confirm you are human", "are you a robot", "security check",
        "checking your browser", "enable javascript and cookies to continue",
        "verify you are human", "unusual traffic",
    ]
    return any(sig in low for sig in signals)


def _make_excerpt(text, max_words=200):
    """Extract a text excerpt (first N words) for orientation.  Not the cited excerpt."""
    words = str(text or "").split()
    return " ".join(words[:max_words])


def scout_url(url, allowlist=None, render=None):
    """Scout a single URL.  Returns a snapshot dict.

    A page whose server-rendered text is too thin to carry content is
    **rendered** with the optional headless browser: many course catalogues
    are JavaScript-rendered, and a plain fetch sees only the shell.  The
    render is optional and bounded — without a browser, or without budget, the
    plain fetch stands and the page is named as thin.
    """
    domain = _domain_of(url)
    allowed, tier_or_reason = _is_allowed(domain, allowlist)
    if not allowed:
        return {
            "url": url,
            "domain": domain,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sha256": "",
            "status_code": 0,
            "paywalled": False,
            "text_excerpt": "",
            "error": "not allowed: %s" % tier_or_reason,
            "tier_hint": None,
        }

    status, text, error = _fetch_url(url)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    paywalled = _detect_paywall(text, status)
    rendered = False
    render_note = ""

    # The readable text of the fetch, measured on its own.
    fetched_readable = _readable(text) if text else ""

    # A bot-check page is not the page the URL names.  It is named as
    # unreadable rather than stored, because its words are not the school's
    # words about the framework.
    challenged = _detect_challenge(fetched_readable, status)
    if challenged:
        error = error or "the site answered with a bot check, not the page"
        text = ""
        fetched_readable = ""
        sha = ""

    # A page is thin when its **readable** text is too short to carry content.
    # The fetch may have failed outright (a 403 is common on faculty pages
    # that a browser reads fine), so a failed fetch is also a candidate for
    # the browser: the render is the only path to that page.
    wants_render = (not challenged) and ((not fetched_readable) or _is_thin(fetched_readable))
    if wants_render:
        from . import render as _render
        if render is None:
            render = _render
        if render.available() and render.take_render():
            page_text, why = render.render_text(url, allowlist=allowlist)
            rendered_readable = _readable(page_text) if page_text else ""
            # Compare **readable** lengths.  Comparing the rendered text with
            # the raw markup counted the markup, so a rendered page was
            # almost always judged "no longer than the fetch" and thrown
            # away — exactly the page the browser had read for us.
            if rendered_readable and len(rendered_readable) > len(fetched_readable):
                text = page_text
                fetched_readable = rendered_readable
                sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
                rendered = True
                # A page the browser read is not behind a paywall, whatever
                # the plain fetch was told.
                paywalled = _detect_paywall(page_text, 200)
            else:
                render_note = why or "the rendered page was no longer than the fetch"
        else:
            render_note = "no headless browser, or the render budget is spent"
    elif error:
        render_note = "the fetch failed and no render was needed"

    # A rendered page that is only a bot check is still not the page.
    if rendered and _detect_challenge(fetched_readable, status):
        error = error or "the site answered with a bot check, not the page"
        text = ""
        fetched_readable = ""
        sha = ""
        rendered = False

    # The orientation excerpt is the **readable** text, not markup.
    excerpt = _make_excerpt(fetched_readable) if fetched_readable else ""

    return {
        "url": url,
        "domain": domain,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sha256": sha,
        "status_code": status,
        "paywalled": paywalled,
        "text_excerpt": excerpt,
        # The body is kept in memory only, for the reader's verbatim gate.
        # It never reaches the evidence store: only the hash and a short
        # excerpt are persisted (D-8).  It is stored as **readable text**:
        # the reader strips markup again, and a raw fragment that was cut
        # mid-``<svg>`` leaked path data into the excerpts.
        "_text": fetched_readable[:MAX_TEXT_CHARS],
        "_readable_len": len(fetched_readable),
        "error": error,
        "tier_hint": tier_or_reason,
        "rendered": rendered,
        "render_note": render_note,
    }


def _readable(text):
    """The readable text of a page.  Stdlib only."""
    from .render import clean_text
    return clean_text(text)


def _is_thin(text):
    """Is the fetched text too short to carry content?"""
    from . import render as _render
    return _render.is_thin(text)


def scout_urls(urls, allowlist=None, delay=0.5):
    """Scout a list of URLs with a small delay between requests."""
    results = []
    for url in (urls or []):
        snap = scout_url(url, allowlist=allowlist)
        results.append(snap)
        if delay and delay > 0:
            time.sleep(delay)
    return results


def scout_school_pages(school_list, allowlist=None):
    """Build a list of URLs to scout from a school list.

    Generates candidate URLs using common patterns for school curriculum and
    assessment pages.  These are best-effort guesses; the admin can supplement
    with manual URLs.  Returns a list of URLs (not fetched).
    """
    urls = []
    if not isinstance(school_list, dict):
        return urls

    # Common path patterns for curriculum/assessment pages
    PATH_PATTERNS = [
        "/mba/curriculum",
        "/mba/programme/curriculum",
        "/mba/curriculum/",
        "/programs/mba/curriculum",
        "/academics/mba",
        "/mba/core-courses",
        "/mba/required-courses",
    ]

    regions = school_list.get("regions", {})
    for region, items in regions.items():
        for item in (items or []):
            name = item.get("name", "")
            # Generate a domain slug from the school name
            slug = name.lower().replace(" ", "").replace("'", "").replace(".", "")
            # Remove common suffixes
            for suffix in ["businessschool", "schoolofmanagement", "schoolofbusiness",
                           "businessschoolof", "collegeschoolofbusiness"]:
                slug = slug.replace(suffix, "")
            slug = slug.strip()
            if not slug:
                continue
            # Try a few domain patterns
            domains = [
                "%s.edu" % slug,
                "%s.com" % slug,
                "www.%s.edu" % slug,
            ]
            for domain in domains[:1]:
                for path in PATH_PATTERNS[:2]:
                    urls.append("https://%s%s" % (domain, path))

    # Also add body watch pages
    bodies = school_list.get("bodies_to_watch", [])
    body_urls = {
        "AACSB": "https://www.aacsb.edu/insights",
        "GMAC": "https://www.gmac.com/why-gmac/gmac-news",
        "IFRS Foundation (IASB and ISSB)": "https://www.ifrs.org/news-and-events",
    }
    for body in bodies:
        if body in body_urls:
            urls.append(body_urls[body])

    return urls
