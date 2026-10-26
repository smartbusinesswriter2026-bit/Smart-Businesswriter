"""Additive case-store routes (product layer, standard library only).

A **pure dispatcher**: it parses a method and a path, calls the case/version/
comparison/sign-off modules, and returns a status code and a payload.  It does
not touch the frozen server, does not compute anything, and never reinterprets
a stored bundle.

The computation owner wired the `/api/cases` prefix into `src/bp/server.py`
(done: B-085), so routes added here are reachable without another core edit.

Routes:

    GET    /api/cases                            -> 200 {"cases": [summary, ...]}
    POST   /api/cases                            -> 201 <the stored bundle>
    GET    /api/cases/{id}                       -> 200 <the stored bundle>
    DELETE /api/cases/{id}                       -> 200 {"deleted": id}
    GET    /api/cases/{id}/versions              -> 200 {"versions": [summary, ...]}
    POST   /api/cases/{id}/versions              -> 201 version metadata
    GET    /api/cases/{id}/versions/{n}          -> 200 version document
    GET    /api/cases/{id}/compare?versions=1,2  -> 200 comparison
    POST   /api/cases/{id}/signoff               -> 201 sign-off record
    GET    /api/cases/{id}/signoff?version=n     -> 200 {"signoffs": [...]}
"""

from . import cases as case_store
from . import compare as comparator
from . import signoff as signoff_store
from . import versions as version_store

CASE_ROUTE = "/api/cases"


def _clean_path(path):
    """The path without a query string or a trailing slash."""
    if not isinstance(path, str):
        return ""
    text = path.split("?", 1)[0].split("#", 1)[0].strip()
    if len(text) > 1 and text.endswith("/"):
        text = text.rstrip("/")
    return text


def _query(path):
    """The query string as a flat dict of first values."""
    if not isinstance(path, str) or "?" not in path:
        return {}
    try:
        from urllib.parse import parse_qs
        return {key: values[0] for key, values in parse_qs(path.split("?", 1)[1]).items() if values}
    except ValueError:
        return {}


def _segments(path):
    """The path segments after `/api/cases`, or None when the path is not that route."""
    if path == CASE_ROUTE:
        return []
    if not path.startswith(CASE_ROUTE + "/"):
        return None
    return [part for part in path[len(CASE_ROUTE) + 1:].split("/") if part]


def _error(error):
    return 422, {"error": str(error)}


def handle(method, path, body=None):
    """Dispatch one request. Returns `(status_code, payload)`."""
    verb = (method or "").upper()
    route = _clean_path(path)
    segments = _segments(route)
    query = _query(path)
    if segments is None:
        return 404, {"error": "unknown route %s" % route}

    # -- the case collection -------------------------------------------------
    if not segments:
        if verb == "GET":
            return 200, {"cases": case_store.list_cases()}
        if verb == "POST":
            try:
                case_id = case_store.save(body if isinstance(body, dict) else {})
            except ValueError as error:
                return _error(error)
            return 201, case_store.load(case_id)
        return 405, {"error": "method %s is not allowed on %s" % (verb, CASE_ROUTE)}

    case_id = segments[0]
    tail = segments[1:]
    try:
        version_store._check_id(case_id)
    except ValueError as error:
        return _error(error)

    # -- the version chain ---------------------------------------------------
    if tail == ["versions"]:
        if verb == "GET":
            try:
                return 200, {"versions": version_store.list_versions(case_id)}
            except ValueError as error:
                return _error(error)
            except version_store.VersionError as error:
                return 404, {"error": str(error)}
        if verb == "POST":
            if not isinstance(body, dict):
                return 422, {"error": "a case bundle object is required"}
            try:
                stored_id, version = version_store.append(body, case_id)
                document = version_store.get(stored_id, version)
            except (ValueError, version_store.VersionError) as error:
                return _error(error)
            return 201, {key: document[key] for key in
                         ("format", "case_id", "version", "created_at", "bundle_hash", "spec_hash",
                          "outputs_hash", "method", "method_version", "tier", "title")}
        return 405, {"error": "method %s is not allowed on versions" % verb}

    if len(tail) == 2 and tail[0] == "versions":
        if verb != "GET":
            return 405, {"error": "method %s is not allowed on a version" % verb}
        try:
            version = int(tail[1])
        except ValueError:
            return _error("version must be a positive integer")
        try:
            return 200, version_store.get(case_id, version)
        except ValueError as error:
            return _error(error)
        except version_store.VersionNotFound as error:
            return 404, {"error": str(error)}
        except version_store.VersionCorrupt as error:
            return _error(error)

    # -- comparison ----------------------------------------------------------
    if tail == ["compare"]:
        if verb != "GET":
            return 405, {"error": "method %s is not allowed on compare" % verb}
        wanted = None
        if query.get("versions"):
            try:
                wanted = [int(part) for part in query["versions"].split(",") if part.strip()]
            except ValueError:
                return _error("versions must be a comma-separated list of positive integers")
        try:
            return 200, comparator.compare(case_id, wanted)
        except ValueError as error:
            return _error(error)
        except (comparator.CompareError, version_store.VersionError) as error:
            return _error(error)

    # -- sign-off ------------------------------------------------------------
    if tail == ["signoff"]:
        if verb == "GET":
            try:
                version = int(query["version"]) if query.get("version") else None
                return 200, {"signoffs": signoff_store.list_for(case_id, version)}
            except ValueError as error:
                return _error(error)
        if verb == "POST":
            if not isinstance(body, dict):
                return 422, {"error": "a sign-off object is required"}
            try:
                version = int(body.get("version"))
            except (TypeError, ValueError):
                return 422, {"error": "version must be a positive integer"}
            try:
                return 201, signoff_store.record(case_id, version, body.get("reviewer"),
                                                role=body.get("role"), scope=body.get("scope"),
                                                decision=body.get("decision", "reviewed"))
            except ValueError as error:
                return _error(error)
            except version_store.VersionError as error:
                return 404, {"error": str(error)}
        return 405, {"error": "method %s is not allowed on signoff" % verb}

    # -- the original flat case ---------------------------------------------
    if tail:
        return 404, {"error": "unknown route %s" % route}
    if verb == "GET":
        try:
            return 200, case_store.load(case_id)
        except case_store.CaseNotFound as error:
            return 404, {"error": str(error)}
        except ValueError as error:
            return _error(error)
    if verb == "DELETE":
        try:
            if version_store._existing_versions(case_id):
                version_store.delete_case(case_id)
            else:
                case_store.delete(case_id)
        except (case_store.CaseNotFound, version_store.VersionNotFound) as error:
            return 404, {"error": str(error)}
        except ValueError as error:
            return _error(error)
        return 200, {"deleted": case_id}
    return 405, {"error": "method %s is not allowed on %s" % (verb, route)}
