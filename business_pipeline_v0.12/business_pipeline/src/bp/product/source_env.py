"""Load the source credentials from this project's own backend .env.

The product has its own `Backend/.env`; it no longer has to borrow another
application's file.  The loader reads a fixed allowlist of source names, maps
them to the `BP_` names the source finder uses, never prints a value and never
overrides a value that is already set in the environment.

Lookup order (the first existing file wins):

    BP_SOURCE_ENV, then <repo>/Backend/.env, then
    D:\\AA\\Backend\\.env, then D:\\AA\\AcademicSources\\Backend\\.env

The last two are the legacy locations kept only so a checkout without its own
file still works.
"""

import os
from pathlib import Path

#: The product's own credential file.
PROJECT_ENV = Path(__file__).resolve().parents[3] / "Backend" / ".env"

ALLOWED = {
    "BRAVE_API_KEY": "BP_BRAVE_API_KEY",
    "FIRECRAWL_API_KEY": "BP_FIRECRAWL_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY": "BP_SEMANTIC_SCHOLAR_KEY",
    "OPENALEX_EMAIL": "BP_OPENALEX_EMAIL",
    "CROSSREF_MAILTO": "BP_CROSSREF_MAILTO",
    "FIRECRAWL_KEYLESS": "BP_FIRECRAWL_KEYLESS",
}
DEFAULT_PATHS = (str(PROJECT_ENV), r"D:\AA\Backend\.env", r"D:\AA\AcademicSources\Backend\.env")


def _parse(path):
    values = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            for line in stream:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                name = name.strip()
                if name in ALLOWED:
                    values[name] = value.strip().strip('"').strip("'")
    except OSError:
        return {}
    return values


def _status():
    return {"brave": bool(os.environ.get("BP_BRAVE_API_KEY")),
            "firecrawl": bool(os.environ.get("BP_FIRECRAWL_API_KEY")),
            "semantic_scholar": bool(os.environ.get("BP_SEMANTIC_SCHOLAR_KEY")),
            "firecrawl_keyless": os.environ.get("BP_FIRECRAWL_KEYLESS", "1") != "0"}


def load_web_credentials(path=None):
    """Set the allowlisted source credentials when they are not already set.

    Returns a report with the path and the *names* loaded, never the values.
    """
    candidates = [path] if path else ([os.environ["BP_SOURCE_ENV"]] if os.environ.get("BP_SOURCE_ENV") else []) + list(DEFAULT_PATHS)
    chosen = None
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            chosen = candidate
            break
    if not chosen:
        return {"path": None, "loaded": [], **_status()}
    loaded = []
    for name, value in _parse(chosen).items():
        target = ALLOWED[name]
        if not value or os.environ.get(target):
            continue
        os.environ[target] = value
        loaded.append(target)
    return {"path": chosen, "loaded": loaded, **_status()}
