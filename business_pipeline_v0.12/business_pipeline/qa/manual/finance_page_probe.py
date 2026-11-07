"""Browser probe for the Finance subject page after the Rates and FX fold.

    python qa/manual/finance_page_probe.py --url http://127.0.0.1:8021

It drives a real browser (Chromium over the DevTools Protocol, no third-party
packages) and proves the four things the Finance page must hold after the
2026-11-07 increment:

  1. the page's own script parses - no syntax error, no uncaught exception;
  2. the buttons are wired - the handler functions exist and a click on
     "All subjects" really moves the view;
  3. the Student guide and the Finance shelf summary are gone;
  4. the Rates and FX panel is a disclosure that starts closed and opens when
     its header is clicked.

It needs a server already running (`scripts/serve.py`) and a Chromium binary
with a DevTools endpoint. If no endpoint is available it prints SKIP and exits
0, so it can never turn a green suite red just because a browser is missing.
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from tile_close_browser_test import CDP  # noqa: E402  (path set above)


ERROR_TRAP = (
    "window.__errs=[];"
    "window.addEventListener('error',function(e){"
    "window.__errs.push(String(e.message||e.error));});"
)

# The app's own functions: if the inline script failed to parse, none of them exist.
FUNCTIONS = ("(function(){return { show: typeof show,"
             " renderSubject: typeof renderSubject,"
             " bindRatesPanel: typeof bindRatesPanel,"
             " shelfSummary: typeof shelfSummary };})()")

# What the Finance page must show and must not show.
PAGE_STATE = (
    "(function(){var out=document.querySelector('#subjectout');"
    "var text=out?(out.textContent||''):'';"
    "var panel=out?out.querySelector('details.marketpanel'):null;"
    "var guide=out?out.querySelector('details.guide.studentguide'):null;"
    "return { subjectOpen: !document.querySelector('#panel-subject').hidden,"
    "  heading: ((out?out.querySelector('h2'):null)||{}).textContent||'',"
    "  hasGuide: !!guide,"
    "  hasSummary: text.indexOf('Corporate finance, valuation')>=0,"
    "  hasRatesPanel: !!panel,"
    "  ratesOpen: panel ? panel.open : null,"
    "  errs: window.__errs || [] };})()"
)

BACK_CLICK = ("(function(){var b=document.querySelector('#subjectback');"
              "if(!b) return 0; b.click(); return 1;})()")

AFTER_BACK = ("(function(){return { subjectsOpen: !document.querySelector('#panel-subjects').hidden,"
             "  subjectOpen: !document.querySelector('#panel-subject').hidden,"
             "  hash: location.hash };})()")

OPEN_RATES = ("(function(){var p=document.querySelector('#subjectout details.marketpanel');"
              "if(!p) return 0; p.querySelector('summary').click(); return 1;})()")

AFTER_OPEN = ("(function(){var p=document.querySelector('#subjectout details.marketpanel');"
              "return { open: p?p.open:null,"
              "  hasFxSelect: !!(p&&p.querySelector('#fxbase')),"
              "  hasRatesOut: !!(p&&p.querySelector('#ratesout')) };})()")



def run(browser, base):
    failures = []

    def check(name, ok, detail=""):
        print(("PASS  " if ok else "FAIL  ") + name
              + (("   -> " + str(detail)) if (detail and not ok) else ""))
        if not ok:
            failures.append(name)

    def wait(expression, timeout=25):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if browser.js(expression):
                    return True
            except RuntimeError:
                pass
            time.sleep(0.25)
        return False

    browser.js("location.hash = '#/subject/finance'; 1")
    ready = wait("(function(){var p=document.querySelector('#panel-subject');"
                 "return p && !p.hidden && document.querySelector('#subjectout h2') ? 1 : 0;})()")
    check("the Finance page renders", ready)

    errs = browser.js("window.__errs || []") or []
    check("the page raises no uncaught error", not errs, errs)

    functions = browser.js(FUNCTIONS) or {}
    check("the app script parses (show/renderSubject are defined)",
          functions.get("show") == "function"
          and functions.get("renderSubject") == "function", functions)

    state = browser.js(PAGE_STATE) or {}
    check("the Student guide is gone", not state.get("hasGuide"), state)
    check("the Finance shelf summary is gone", not state.get("hasSummary"), state)
    check("the Rates and FX panel is a disclosure", bool(state.get("hasRatesPanel")), state)
    check("the Rates and FX panel starts closed", state.get("ratesOpen") is False, state)

    # The buttons: a click on "All subjects" must move the view.
    clicked = browser.js(BACK_CLICK)
    time.sleep(0.5)
    after = browser.js(AFTER_BACK) or {}
    check("the All subjects button is clickable",
          bool(clicked) and after.get("subjectsOpen") and not after.get("subjectOpen"), after)

    # Back to Finance, then unfold the panel by clicking its header.
    browser.js("location.hash = '#/subject/finance'; 1")
    wait("(function(){var p=document.querySelector('#panel-subject');"
         "return p && !p.hidden && document.querySelector('#subjectout details.marketpanel') ? 1 : 0;})()")
    browser.js(OPEN_RATES)
    time.sleep(0.5)
    opened = browser.js(AFTER_OPEN) or {}
    check("the Rates and FX header opens the panel",
          opened.get("open") is True, opened)
    check("the opened panel still carries its controls",
          opened.get("hasFxSelect") and opened.get("hasRatesOut"), opened)

    print("\n%d failures" % len(failures))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Probe the Finance subject page")
    parser.add_argument("--url", default="http://127.0.0.1:8021", help="the running workbench")
    parser.add_argument("--port", type=int, default=9333, help="the Chromium DevTools port")
    args = parser.parse_args()
    try:
        browser = CDP(args.port)
    except Exception as error:  # no browser is a SKIP, never a failure
        print("SKIP  no DevTools endpoint on port %d (%s). Start one with:" % (args.port, error))
        print("      chrome --headless=new --no-sandbox --remote-debugging-port=%d about:blank" % args.port)
        return 0
    browser.call("Page.enable")
    browser.call("Runtime.enable")
    try:
        browser.call("Network.enable")
        browser.call("Network.clearBrowserCache")
        browser.call("Network.setCacheDisabled", cacheDisabled=True)
    except RuntimeError:
        pass
    try:
        browser.call("Page.addScriptToEvaluateOnNewDocument", source=ERROR_TRAP)
    except RuntimeError:
        pass
    base = args.url.rstrip("/")
    browser.call("Page.navigate", url=base + "/")
    time.sleep(1.0)
    failures = run(browser, base)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
