"""Additive case-store routes (product layer, standard library only).

A **pure dispatcher**: it parses a method and a path, calls the case/version/
comparison/sign-off modules, and returns a status code and a payload.  It does
not touch the frozen server, does not compute anything, and never reinterprets
a stored bundle.

The computation owner wired the `/api/cases` prefix into `src/bp/server.py`
(done: B-085), so routes added here are reachable without another core edit.

Routes:

    GET    /api/cases                            -> 200 {"cases": [summary, ...]}
    GET    /api/cases?subject=<id>               -> 200 {"cases": [summary, ...]}
    GET    /api/cases/subjects                   -> 200 subject gallery
    GET    /api/cases/subjects/{id}              -> 200 subject page
    GET    /api/cases/calculator                 -> 200 Calculator tool groups
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
from . import charts as chart_renderer
from . import compare as comparator
from . import diagrams as diagram_renderer
from . import export as case_export
from . import ops
from . import signoff as signoff_store
from . import spreadsheets
from . import docx as docx_export
from . import credits
from . import subjects as subject_index
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
            summaries = case_store.list_cases()
            subject_id = query.get("subject")
            if subject_id:
                if not subject_index.exists(subject_id):
                    return _error("unknown subject %r" % subject_id)
                summaries = subject_index.filter_cases(summaries, subject_id)
            return 200, {"cases": summaries}
        if verb == "POST":
            try:
                case_id = case_store.save(body if isinstance(body, dict) else {})
            except ValueError as error:
                return _error(error)
            return 201, case_store.load(case_id)
        return 405, {"error": "method %s is not allowed on %s" % (verb, CASE_ROUTE)}

    # -- subject index and Calculator (product data, no computation) ---------
    if segments == ["subjects"]:
        if verb != "GET":
            return 405, {"error": "method %s is not allowed on subjects" % verb}
        return 200, subject_index.catalogue()
    if len(segments) == 2 and segments[0] == "subjects":
        if verb != "GET":
            return 405, {"error": "method %s is not allowed on a subject" % verb}
        try:
            return 200, subject_index.detail(segments[1])
        except subject_index.SubjectNotFound as error:
            return 404, {"error": str(error)}
    if segments == ["calculator"]:
        if verb != "GET":
            return 405, {"error": "method %s is not allowed on the calculator" % verb}
        return 200, subject_index.calculator_groups()

    case_id = segments[0]
    tail = segments[1:]

    # -- maintenance surface (backup / restore / list backups) ---------------
    if not tail and segments[0] in ("backup", "restore", "backups"):
        action = segments[0]
        if action == "backups" and verb == "GET":
            return 200, {"backups": ops.list_backups()}
        if action == "backup" and verb == "POST":
            try:
                destination = body.get("destination") if isinstance(body, dict) else None
                return 201, ops.backup(destination)
            except (OSError, ValueError) as error:
                return _error(error)
        if action == "restore" and verb == "POST":
            if not isinstance(body, dict) or not body.get("archive"):
                return 422, {"error": "restore needs an 'archive' path"}
            try:
                return 200, ops.restore(body["archive"], overwrite=body.get("overwrite") is True)
            except (OSError, ValueError) as error:
                return _error(error)
        return 405, {"error": "method %s is not allowed on %s" % (verb, route)}

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

    # -- rendering and exports (Phase 2c) ------------------------------------
    if tail == ["render"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on render" % verb}
        if not isinstance(body, dict):
            return 422, {"error": "a chart or diagram spec object is required"}
        try:
            case_id_doc = version_store.latest(case_id) if version_store._existing_versions(case_id) else {"bundle": case_store.load(case_id)}
        except (case_store.CaseNotFound, version_store.VersionError) as error:
            return 404, {"error": str(error)}
        except ValueError as error:
            return _error(error)
        bundle = case_id_doc["bundle"]
        try:
            if body.get("chart") is not None:
                return 200, {"svg": chart_renderer.render_svg(bundle, body["chart"])}
            if body.get("diagram") is not None:
                return 200, {"svg": diagram_renderer.render_svg(body["diagram"])}
        except (chart_renderer.ChartError, diagram_renderer.DiagramError) as error:
            return _error(error)
        return 422, {"error": "render needs a 'chart' or a 'diagram' spec"}

    if tail == ["export"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on export" % verb}
        if not isinstance(body, dict) or not body.get("kind"):
            return 422, {"error": "export needs a 'kind' (csv, spreadsheetml, html) and a 'destination' path"}
        if not isinstance(body.get("destination"), str) or not body["destination"].strip():
            return 422, {"error": "export needs a 'destination' path"}
        try:
            document = version_store.latest(case_id) if version_store._existing_versions(case_id) else {"bundle": case_store.load(case_id)}
            bundle = document["bundle"]
        except (case_store.CaseNotFound, version_store.VersionError) as error:
            return 404, {"error": str(error)}
        except ValueError as error:
            return _error(error)
        try:
            kind = body["kind"]
            destination = body["destination"]
            if kind not in ("csv", "spreadsheetml", "html", "docx"):
                return 422, {"error": "unknown export kind %r (csv, spreadsheetml, html, docx)" % kind}
            # price it first: the UI shows this before the student commits, and nothing renders when the
            # wallet cannot pay
            quote = credits.quote(case_id, kind)
            if body.get("quote_only"):
                return 200, {"kind": kind, "quote": quote}
            if quote["cost"] > quote["balance"]:
                return 402, {"error": "%s costs %d credit(s); the balance is %d"
                                      % (kind, quote["cost"], quote["balance"]), "quote": quote}
            if kind == "csv":
                result = {"kind": kind, "path": spreadsheets.export_csv(bundle, destination)}
            elif kind == "spreadsheetml":
                result = dict(kind=kind, **spreadsheets.export_spreadsheetml(bundle, destination, sha=True))
            elif kind == "docx":
                result = dict(kind=kind, **docx_export.export_docx(bundle, destination))
            else:
                result = {"kind": kind, "path": case_export.export_html(
                    bundle, destination, charts=body.get("charts"), diagrams=body.get("diagrams"))}
            # charge only after the file exists: a failed export costs nothing. An idempotency key
            # supplied by the caller makes a retry free; without one, each export is a new export.
            result["credits"] = credits.charge(case_id, kind, idem=body.get("idempotency_key"))
            return 200, result
        except credits.InsufficientCredits as error:
            return 402, {"error": str(error)}
        except (OSError, ValueError, chart_renderer.ChartError, diagram_renderer.DiagramError) as error:
            return _error(error)

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
