"""Durable store for deterministic chat cases (product layer).

One JSON document per chat case under `<case store>/chat/`.  The case holds the
brief, the answers, the plan, the sources, the evidence, the draft and the
export state; it is the first container that can later carry more than one
framework or method run.
"""

import json
import os
import uuid

from . import cases

FORMAT = "bp-chat/1"


class ChatCaseNotFound(Exception):
    pass


class ChatCaseCorrupt(Exception):
    pass


def chat_dir():
    return cases.cases_dir() / "chat"


def _path(case_id):
    checked = cases._check_id(case_id)
    root = chat_dir().resolve()
    path = (root / (checked + ".json")).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("chat case id resolves outside the store")
    return path


def save(state):
    """Store one chat state, assigning an id and timestamps when absent."""
    state = dict(state)
    if not state.get("id"):
        state["id"] = uuid.uuid4().hex[:12]
    state.setdefault("format", FORMAT)
    if not cases.ID_RE.fullmatch(state["id"]):
        raise ValueError("chat case id must be 12 lowercase hex characters")
    cases._write(_path(state["id"]), state)
    return state


def load(case_id):
    path = _path(case_id)
    if not path.exists():
        raise ChatCaseNotFound("no chat case %s" % case_id)
    try:
        with open(path, encoding="utf-8") as stream:
            state = json.load(stream)
    except (OSError, ValueError) as error:
        raise ChatCaseCorrupt("chat case %s cannot be read: %s" % (case_id, error))
    if not isinstance(state, dict) or state.get("format") != FORMAT or state.get("id") != case_id:
        raise ChatCaseCorrupt("chat case %s has the wrong shape" % case_id)
    return state


def list_cases():
    root = chat_dir()
    if not root.exists():
        return []
    out = []
    for path in sorted(root.glob("*.json")):
        try:
            state = load(path.stem)
        except (ChatCaseNotFound, ChatCaseCorrupt, ValueError):
            out.append({"id": path.stem, "corrupt": True})
            continue
        out.append({"id": state["id"], "subject": state.get("subject"), "stage": state.get("stage"),
                    "brief": state.get("brief"), "updated_at": state.get("updated_at")})
    return out


def delete(case_id):
    path = _path(case_id)
    if path.exists():
        os.unlink(path)
    return {"deleted": case_id}
