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
import shutil
from pathlib import Path

#: The product's own credential file.
PROJECT_ENV = Path(__file__).resolve().parents[3] / "Backend" / ".env"

ALLOWED = {
    "BRAVE_API_KEY": "BP_BRAVE_API_KEY",
    "FIRECRAWL_API_KEY": "BP_FIRECRAWL_API_KEY",
    "DEEPSEEK_API_KEY": "BP_DEEPSEEK_API_KEY",
    "OPENCODE_API_KEY": "BP_OPENGO_API_KEY",
    "OPENCODE_GO_MODEL": "BP_LLM_MODEL",
    "LLM_MODEL_TIER2": "BP_LLM_MODEL_TIER2",
    "LLM_MODEL_TIER3": "BP_LLM_MODEL_TIER3",
    "LLM_PROVIDER": "BP_LLM_PROVIDER",
    "LLM_BASE_URL": "BP_LLM_BASE_URL",
    "COUNCIL_MODEL": "BP_COUNCIL_MODEL",
    "PROSE_MODEL": "BP_PROSE_MODEL",
    "OPENGO_SEARCH_URL": "BP_OPENGO_SEARCH_URL",
    "OPENGO_WEBSEARCH": "BP_OPENGO_WEBSEARCH",
    "OPENGO_RESEARCH": "BP_OPENGO_RESEARCH",
    "OPENGO_TIMEOUT": "BP_OPENGO_TIMEOUT",
    "SEMANTIC_SCHOLAR_API_KEY": "BP_SEMANTIC_SCHOLAR_KEY",
    "OPENALEX_API_KEY": "BP_OPENALEX_API_KEY",
    "OPENALEX_EMAIL": "BP_OPENALEX_EMAIL",
    "CROSSREF_MAILTO": "BP_CROSSREF_MAILTO",
    "FIRECRAWL_KEYLESS": "BP_FIRECRAWL_KEYLESS",
    # Payments. The client id is public (the browser SDK loads it); the secret never leaves the server.
    "PAYPAL_CLIENT_ID": "BP_PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET": "BP_PAYPAL_CLIENT_SECRET",
    "PAYPAL_ENV": "BP_PAYPAL_ENV",
    # The Business Bundle hand-off to the other product: its address and the shared secret
    # both products carry. The secret is server-side only.
    "WRITE_SMARTER_URL": "BP_WRITE_SMARTER_URL",
    "BUNDLE_HANDOFF_SECRET": "BP_BUNDLE_HANDOFF_SECRET",
    # Market data: one institutional Alpha Vantage key shared by every student (free tier today).
    "ALPHAVANTAGE_API_KEY": "BP_ALPHAVANTAGE_KEY",
    # Second market-data provider: one institutional Massive key.
    "MASSIVE_API_KEY": "BP_MASSIVE_API_KEY",
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
            "deepseek": bool(os.environ.get("BP_DEEPSEEK_API_KEY")),
            "opengo": bool(shutil.which("opencode")) and os.environ.get("BP_OPENGO_WEBSEARCH", "0") == "1",
            "opengo_key": bool(os.environ.get("BP_OPENGO_API_KEY")),
            "model": os.environ.get("BP_LLM_MODEL", "beam-free"),
            "prose_model": os.environ.get("BP_PROSE_MODEL") or os.environ.get("BP_LLM_MODEL", "beam-free"),
            "semantic_scholar": bool(os.environ.get("BP_SEMANTIC_SCHOLAR_KEY")),
            "firecrawl_keyless": os.environ.get("BP_FIRECRAWL_KEYLESS", "1") != "0",
            "alpha_vantage": bool(os.environ.get("BP_ALPHAVANTAGE_KEY")),
            "massive": bool(os.environ.get("BP_MASSIVE_API_KEY"))}


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


def load_selected(names, path=None):
    """Load only the named entries from the first existing credential file.

    The launcher loads the whole allowlist at startup; a module that needs one credential and may be
    reached from a server started another way (``python -m bp.server``) uses this so the names it
    depends on are resolved without touching anything else. Values are never returned.
    """
    wanted = [name for name in names if name in ALLOWED]
    candidates = [path] if path else ([os.environ["BP_SOURCE_ENV"]] if os.environ.get("BP_SOURCE_ENV") else []) + list(DEFAULT_PATHS)
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            values = _parse(candidate)
            loaded = []
            for name in wanted:
                value = values.get(name)
                if value and not os.environ.get(ALLOWED[name]):
                    os.environ[ALLOWED[name]] = value
                    loaded.append(ALLOWED[name])
            return {"path": candidate, "loaded": loaded}
    return {"path": None, "loaded": []}
