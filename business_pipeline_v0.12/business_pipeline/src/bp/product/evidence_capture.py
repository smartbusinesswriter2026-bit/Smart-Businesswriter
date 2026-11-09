"""Optional screenshot capture for the Portfolio Lab evidence slot.

This is a best-effort convenience, never a guarantee.  It uses Playwright when
the optional package and its browser are installed; when they are not, the
caller gets a named gap and the student can still attach their own screenshot.
Nothing here blocks a snapshot.
"""

import re

# Only public quote pages are captured.  A caller cannot point the headless
# browser at an internal address: the host must be on this list and the scheme
# must be https.
ALLOWED_HOSTS = {
    "finance.yahoo.com",
    "www.google.com",
    "google.com",
    "www.marketwatch.com",
    "stockanalysis.com",
    "www.stockanalysis.com",
    "www.nasdaq.com",
    "www.bloomberg.com",
}

_SYMBOL_RE = re.compile(r"[A-Z0-9.\-]{1,12}")


class EvidenceCaptureUnavailable(Exception):
    """The capture could not be made; the message is shown to the student."""


def quote_url(symbol):
    symbol = str(symbol or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError("the symbol must be 1-12 letters, digits, dots or hyphens")
    return "https://finance.yahoo.com/quote/" + symbol


def _allowed(url):
    from urllib.parse import urlparse
    parsed = urlparse(str(url or ""))
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS


def capture(url, timeout_ms=20000):
    """Return (png_bytes, "image/png") for one public quote page.

    Raises EvidenceCaptureUnavailable with a plain-language reason when the
    optional browser is missing or the page cannot be read.
    """
    if not _allowed(url):
        raise ValueError("only https quote pages on the approved hosts can be captured")
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        raise EvidenceCaptureUnavailable(
            "Automatic screenshots are not available on this machine. "
            "Open the source page and attach your own screenshot instead.")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900},
                                        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                    "Chrome/124.0 Safari/537.36"))
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(2500)
                png = page.screenshot(full_page=False)
            finally:
                browser.close()
    except Exception as error:
        raise EvidenceCaptureUnavailable(
            "The quote page could not be captured right now (%s). "
            "Open the source page and attach your own screenshot instead."
            % str(error)[:160])
    if not isinstance(png, (bytes, bytearray)) or not bytes(png).startswith(b"\x89PNG"):
        raise EvidenceCaptureUnavailable(
            "The capture did not produce an image. Attach your own screenshot instead.")
    return bytes(png), "image/png"
