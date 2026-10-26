"""Additive case-store routes (product layer, standard library only).

This module is a **pure dispatcher**: it parses a method and a path, calls the
case store, and returns a status code and a payload.  It does not touch the
frozen server, does not compute anything, and never reinterprets a stored
bundle - `GET` hands back exactly what was stored.

The computation owner wires it into `src/bp/server.py` after review (that
edit is the core's, not this lane's; see `docs/BACKEND_CONTRACT.md` §4-§6).

Routes:

    GET    /api/cases          -> 200 {"cases": [summary, ...]}
    POST   /api/cases          -> 201 <the stored bundle>
    GET    /api/cases/{id}     -> 200 <the stored bundle>
    DELETE /api/cases/{id}     -> 200 {"deleted": id}

`POST` expects the bundle shape documented in `cases.py`.  A body that is not
a bundle is refused with 422 and the list of what is missing.
"""

from . import cases as case_store

CASE_ROUTE = "/api/cases"


def _clean_path(path):
    """The path without a query string or a trailing slash."""
    if not isinstance(path, str):
        return ""
    text = path.split("?", 1)[0].split("#", 1)[0].strip()
    if len(text) > 1 and text.endswith("/"):
        text = text.rstrip("/")
    return text


def _case_id(path):
    """The id in `/api/cases/{id}`, or None when the path is not that route."""
    if not path.startswith(CASE_ROUTE + "/"):
        return None
    return path[len(CASE_ROUTE) + 1:]


def handle(method, path, body=None):
    """Dispatch one request. Returns `(status_code, payload)`.

    `method` is the HTTP method, `path` the request path, `body` the decoded
    JSON body (or None).  The payload is always a JSON-serialisable object.
    """
    verb = (method or "").upper()
    route = _clean_path(path)

    if route == CASE_ROUTE:
        if verb == "GET":
            return 200, {"cases": case_store.list_cases()}
        if verb == "POST":
            try:
                case_id = case_store.save(body if isinstance(body, dict) else {})
            except ValueError as error:
                return 422, {"error": str(error)}
            return 201, case_store.load(case_id)
        return 405, {"error": "method %s is not allowed on %s" % (verb, route)}

    case_id = _case_id(route)
    if case_id is not None:
        if verb == "GET":
            try:
                return 200, case_store.load(case_id)
            except case_store.CaseNotFound as error:
                return 404, {"error": str(error)}
            except ValueError as error:
                return 422, {"error": str(error)}
        if verb == "DELETE":
            try:
                case_store.delete(case_id)
            except case_store.CaseNotFound as error:
                return 404, {"error": str(error)}
            except ValueError as error:
                return 422, {"error": str(error)}
            return 200, {"deleted": case_id}
        return 405, {"error": "method %s is not allowed on %s" % (verb, route)}

    return 404, {"error": "unknown route %s" % route}
