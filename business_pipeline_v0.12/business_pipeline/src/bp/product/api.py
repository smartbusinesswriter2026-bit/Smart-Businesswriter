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
    POST   /api/cases/match                      -> 200 worksheet suggestions for a case description
    GET    /api/cases/sources/databases          -> 200 the business database registry
    GET    /api/cases/sources/sites?region=<r>   -> 200 the curated official-site registry
    POST   /api/cases/sources/search             -> 200 merged academic results (with per-database errors)
    POST   /api/cases/sources/web                -> 200 curated web results, or the directory when no key is set
    POST   /api/cases/worksheets/draft           -> 200 drafted worksheet inputs from retrieved sources
    POST   /api/cases/worksheets/report          -> 200 a sourced report and its Word (.docx) bytes
    GET    /api/cases/chat                       -> 200 the stored PESTEL chat cases
    POST   /api/cases/chat                       -> 201 a new guided PESTEL case
    GET    /api/cases/chat/{id}                  -> 200 one chat state
    POST   /api/cases/chat/{id}/answer           -> 200 the next question, or the plan
    POST   /api/cases/chat/{id}/plan             -> 200 the confirmed plan
    POST   /api/cases/chat/{id}/research         -> 200 per-dimension evidence and gaps
    POST   /api/cases/chat/{id}/draft            -> 200 the drafted PESTEL section
    POST   /api/cases/chat/{id}/export           -> 200 the drafted section as Word bytes
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

import base64
import hashlib
import os

from . import cases as case_store
from . import chat as chat_conductor
from . import chat_store
from . import charts as chart_renderer
from . import compare as comparator
from . import diagrams as diagram_renderer
from . import export as case_export
from . import ops
from . import signoff as signoff_store
from . import spreadsheets
from . import docx as docx_export
from . import credits
from . import deliverables
from . import drafting
from . import sources as source_finder
from . import subjects as subject_index
from . import versions as version_store
from . import writing

CASE_ROUTE = "/api/cases"

#: file extension and MIME type per export kind, for the download path
_SUFFIX = {"docx": "docx", "html": "html", "csv": "csv", "spreadsheetml": "xml", "xlsx": "xlsx"}
_MIME = {"docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         "html": "text/html; charset=utf-8", "csv": "text/csv; charset=utf-8",
         "spreadsheetml": "application/xml; charset=utf-8",
         "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


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
    if segments == ["match"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on the matcher" % verb}
        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            return _error("a case description is required")
        return 200, subject_index.match_frameworks(text)

    # -- source finder (shared by every subject) ------------------------------
    if segments and segments[0] == "sources":
        if segments == ["sources", "databases"]:
            if verb != "GET":
                return 405, {"error": "method %s is not allowed on the database registry" % verb}
            return 200, {"databases": source_finder.databases(), "regions": source_finder.REGIONS,
                         "categories": source_finder.CATEGORIES, "web": source_finder.web_status(),
                         "credentials": {"semantic_scholar": bool(os.environ.get("BP_SEMANTIC_SCHOLAR_KEY"))}}
        if segments == ["sources", "sites"]:
            if verb != "GET":
                return 405, {"error": "method %s is not allowed on the site registry" % verb}
            region = query.get("region")
            if region and region not in source_finder.REGIONS:
                return _error("unknown region %r" % region)
            category = query.get("category")
            if category and category not in source_finder.CATEGORIES:
                return _error("unknown category %r" % category)
            return 200, {"regions": source_finder.REGIONS, "categories": source_finder.CATEGORIES,
                         "sites": source_finder.vetted_sites(region, category=category)}
        if segments == ["sources", "search"]:
            if verb != "POST":
                return 405, {"error": "method %s is not allowed on source search" % verb}
            if not isinstance(body, dict):
                return _error("a search object is required")
            limit = body.get("limit", 20)
            try:
                limit = max(1, min(int(limit), 50))
            except (TypeError, ValueError):
                return _error("limit must be an integer")
            year_from = body.get("year_from")
            if year_from is not None:
                try:
                    year_from = int(year_from)
                except (TypeError, ValueError):
                    return _error("year_from must be a year")
            return 200, source_finder.search_academic(body.get("query"), body.get("databases"), limit, year_from)
        if segments == ["sources", "web"]:
            if verb != "POST":
                return 405, {"error": "method %s is not allowed on web search" % verb}
            if not isinstance(body, dict):
                return _error("a search object is required")
            region = body.get("region") or "Global"
            if region not in source_finder.REGIONS:
                return _error("unknown region %r" % region)
            category = body.get("category")
            if category and category not in source_finder.CATEGORIES:
                return _error("unknown category %r" % category)
            try:
                limit = max(1, min(int(body.get("limit", 10)), 20))
            except (TypeError, ValueError):
                return _error("limit must be an integer")
            return 200, source_finder.search_web(body.get("query"), region, limit, category)
        return 404, {"error": "unknown source route"}

    # -- the deterministic PESTEL conductor ----------------------------------
    if segments and segments[0] == "chat":
        if segments == ["chat"]:
            if verb == "GET":
                return 200, {"cases": chat_store.list_cases()}
            if verb != "POST":
                return 405, {"error": "method %s is not allowed on chat" % verb}
            if not isinstance(body, dict):
                return _error("a chat object is required")
            try:
                state = chat_conductor.start(body.get("brief"), body.get("subject") or "management",
                                             body.get("framework"))
                state = chat_store.save(state)
            except chat_conductor.ChatError as error:
                return _error(error)
            return 201, state
        chat_id = segments[1]
        try:
            state = chat_store.load(chat_id)
        except chat_store.ChatCaseNotFound as error:
            return 404, {"error": str(error)}
        except (chat_store.ChatCaseCorrupt, ValueError) as error:
            return _error(error)
        if len(segments) == 2:
            if verb == "GET":
                return 200, state
            if verb == "DELETE":
                return 200, chat_store.delete(chat_id)
            return 405, {"error": "method %s is not allowed on a chat case" % verb}
        action = segments[2]
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on a chat action" % verb}
        data = body if isinstance(body, dict) else {}
        try:
            if action == "answer":
                state = chat_conductor.answer(state, data.get("question_id"), data.get("value"))
            elif action == "plan":
                state = chat_conductor.confirm_plan(state)
            elif action == "research":
                state = chat_conductor.research(state)
            elif action == "draft":
                accepted = data.get("accepted")
                if accepted is not None and not isinstance(accepted, list):
                    return _error("accepted must be a list of evidence ids")
                state = chat_conductor.draft(state, accepted, data.get("implications"), data.get("style"))
            elif action == "export":
                draft = state.get("draft") or {}
                if not draft:
                    return _error("draft the section before exporting it")
                data_bytes = chat_conductor.docx_bytes(state)
                return 200, {"filename": writing.filename({"title": draft.get("title")}),
                             "mime": _MIME["docx"], "data": base64.b64encode(data_bytes).decode("ascii"),
                             "sha256": hashlib.sha256(data_bytes).hexdigest()}
            else:
                return 404, {"error": "unknown chat action %r" % action}
        except chat_conductor.ChatError as error:
            return _error(error)
        state = chat_store.save(state)
        return 200, state

    if segments == ["worksheets", "draft"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on worksheet drafting" % verb}
        if not isinstance(body, dict):
            return _error("a draft object is required")
        try:
            return 200, drafting.draft(body.get("template"), body.get("sources"))
        except ValueError as error:
            return _error(error)

    if segments == ["worksheets", "report"]:
        if verb != "POST":
            return 405, {"error": "method %s is not allowed on report writing" % verb}
        if not isinstance(body, dict):
            return _error("a report object is required")
        draft = body.get("draft")
        if draft is not None and not isinstance(draft, dict):
            return _error("draft must be an object")
        try:
            report = writing.compose(body.get("template"), body.get("objective"), body.get("sources"), draft,
                                     body.get("framework"), body.get("style"))
        except ValueError as error:
            return _error(error)
        data = writing.docx_bytes(report)
        return 200, {"report": report, "docx": {
            "filename": writing.filename(report), "mime": _MIME["docx"],
            "data": base64.b64encode(data).decode("ascii"),
            "sha256": hashlib.sha256(data).hexdigest()}}

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
            return 422, {"error": "export needs a 'kind' (xlsx, csv, spreadsheetml, html, docx) and a 'destination' path"}
        if not body.get("download") and not body.get("quote_only") and (
                not isinstance(body.get("destination"), str) or not body["destination"].strip()):
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
            deliverable = body.get("deliverable") or deliverables.infer(kind)
            deliverables.check_pair(deliverable, kind)          # refuses a pair that cannot carry the artefact
            if body.get("quote_only"):
                return 200, {"deliverable": deliverable, "kind": kind,
                             "quote": credits.quote(case_id, deliverable, kind)}
            quote = credits.quote(case_id, deliverable, kind)
            if quote["cost"] > quote["balance"]:
                return 402, {"error": "%s as %s costs %d credit(s); the balance is %d"
                                      % (deliverable, kind, quote["cost"], quote["balance"]), "quote": quote}
            if body.get("download"):
                # the browser has no way to fetch a server-side path, so the bytes come back with the
                # response and the page turns them into a file. The destination is chosen here.
                destination = os.path.join(str(ops.state_dir()), "exports",
                                           "%s-%s.%s" % (case_id, deliverable, _SUFFIX[kind]))
                result = deliverables.write_export(bundle, deliverable, kind, destination)
                with open(destination, "rb") as fh:
                    payload = fh.read()
                result.pop("path", None)
                result.update({"filename": os.path.basename(destination), "mime": _MIME[kind],
                               "data": base64.b64encode(payload).decode("ascii")})
                result["credits"] = credits.charge(case_id, deliverable, kind, idem=body.get("idempotency_key"))
                return 200, result
            destination = body["destination"]
            result = deliverables.write_export(bundle, deliverable, kind, destination)
            # charge only after the file exists: a failed export costs nothing. An idempotency key
            # supplied by the caller makes a retry free; without one, each export is a new export.
            result["credits"] = credits.charge(case_id, deliverable, kind, idem=body.get("idempotency_key"))
            return 200, result
        except deliverables.DeliverableError as error:
            return 422, {"error": str(error)}
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
