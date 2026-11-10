"""Render a page with the optional headless browser, and read its text.

Many course catalogues are rendered by JavaScript.  A plain HTTP fetch sees
only the shell — one Bocconi course page returned 248 characters where the
browser shows the full description — so the framework the course teaches is
not in the text the reader can see, and the sweep concludes the framework is
taught nowhere.

This module reads the **rendered** text with the same optional browser the
Portfolio Lab already uses for screenshots.  It is optional in every sense:

- no Playwright, no browser, or no budget left -> the plain fetch stands and
  the page is named as thin;
- only an https host on the RRA's own allowlist is ever rendered;
- a per-sweep budget bounds the time, because a browser is far slower than a
  fetch and a sweep must not spend an hour in one page.
"""
import importlib.util
import re

#: A page whose cleaned text is shorter than this is probably a shell that
#: JavaScript fills in.
THIN_PAGE_CHARS = 1500

#: How many pages one sweep may render.
DEFAULT_RENDER_BUDGET = 12

#: How long one page may take to render.
DEFAULT_TIMEOUT_MS = 25000


def available():
    """Is the optional browser installed?"""
    return importlib.util.find_spec("playwright") is not None


def budget():
    """How many pages one sweep may render."""
    import os
    try:
        return max(0, int(os.environ.get("BP_RELEVANCE_RENDER_BUDGET",
                                         str(DEFAULT_RENDER_BUDGET))))
    except (TypeError, ValueError):
        return DEFAULT_RENDER_BUDGET


#: The render budget is spent, not merely read: a sweep resets it and every
#: render takes one.  A browser is far slower than a fetch, and a sweep must
#: not spend an hour in one page.
_used = {"count": 0, "limit": DEFAULT_RENDER_BUDGET}


def reset_budget():
    """Start a sweep's render budget afresh."""
    _used["count"] = 0
    _used["limit"] = budget()
    return _used["limit"]


def take_render():
    """Is there a render left in this sweep's budget?"""
    if _used["count"] >= _used["limit"]:
        return False
    _used["count"] += 1
    return True


def used():
    return _used["count"]


def _timeout_ms():
    import os
    try:
        return max(3000, int(os.environ.get("BP_RELEVANCE_RENDER_TIMEOUT",
                                            str(DEFAULT_TIMEOUT_MS))))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_MS


def _allowed(url, allowlist):
    """Only an https host on the RRA's own allowlist is ever rendered."""
    from urllib.parse import urlparse
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https":
        return False, "only https is rendered"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "the url has no host"
    from .s1_scout import _is_allowed
    ok, reason = _is_allowed(host, allowlist or {})
    return ok, reason


def render_text(url, allowlist=None, timeout_ms=None):
    """The rendered text of a page.  Returns (text, reason).

    `text` is "" when the page could not be rendered; `reason` says why.
    """
    ok, reason = _allowed(url, allowlist)
    if not ok:
        return "", reason
    if not available():
        return "", "the optional headless browser is not installed"
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return "", "the optional headless browser is not installed"
    timeout = timeout_ms or _timeout_ms()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    viewport={"width": 1280, "height": 900},
                    user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0 Safari/537.36"))
                page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                try:
                    page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass
                page.wait_for_timeout(1200)
                text = page.inner_text("body") or ""
            finally:
                browser.close()
    except Exception as error:
        return "", "the page could not be rendered (%s)" % str(error)[:160]
    return text, ""


def is_thin(text, threshold=None):
    """Is this text too short to carry a course description?

    The **cleaned** text is measured, not the raw bytes: a page that is
    twenty thousand characters of markup and two hundred characters of words
    is a shell, and that is the page the reader cannot see.
    """
    limit = threshold or THIN_PAGE_CHARS
    cleaned = clean_text(text)
    return len(cleaned) < limit


def clean_text(raw):
    """The readable text of a page.  Stdlib only."""
    from .s2_reader import _html_to_text
    return _html_to_text(raw)
