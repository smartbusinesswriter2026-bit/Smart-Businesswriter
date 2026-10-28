"""Replay a saved case: re-hash its plan, re-run its figures, re-read its claims.

    python -m bp.product.replay case.json

A case file is the JSON a case returns from `/api/cases/chat` (or a saved copy of
it).  Replay answers three questions and prints the answers:

1. does the frozen plan still hash to the value it was recorded with?
2. does the brief still hash to the brief the plan was frozen against?
3. does every recorded computation still reproduce from its declared inputs, and
   is the paper's own prose free of claims no frozen method licenses?

Replay reports drift; it never repairs it.  A case that has drifted exits non-zero
and names the reason, which is what a reviewer, an appeals process or a marker
needs in order to trust the paper.
"""

import json
import sys

from .. import methods
from . import api, chat, verify


def _run(method_id, inputs):
    """The same validated call the server attaches to the conductor."""
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


def attach():
    """Attach the frozen core, exactly as `bp.server` does at start-up."""
    api.attach_compute(lambda values: methods.breakeven(values))
    api.attach_methods(_run, methods.describe)


def _draft_sections(state):
    draft = state.get("draft") or {}
    outline = draft.get("outline")
    if outline:
        return [{"heading": item.get("heading"), "lines": item.get("lines") or []}
                for item in outline]
    return [{"heading": item[0], "lines": item[1]} for item in draft.get("sections") or []
            if isinstance(item, (list, tuple)) and len(item) == 2]


def report(state):
    """What replay can prove about one case, as data."""
    attach()
    record = state.get("plan_record") or {}
    plan = chat.replay_check(state)
    recorded_brief = record.get("brief_hash")
    current_brief = verify.brief_hash(state.get("brief"))
    figures = chat._recompute_guard(state) if record else []
    claims = chat._claim_scan(_draft_sections(state)) if state.get("draft") else []
    brief = {"recorded": recorded_brief, "current": current_brief,
             "match": bool(recorded_brief) and recorded_brief == current_brief}
    return {
        "ok": bool(plan.get("match")) and brief["match"] and not figures and not claims,
        "plan": plan,
        "brief": brief,
        "recompute": figures,
        "claims": claims,
        "catalogue_version": record.get("catalogue_version"),
        "models": list(record.get("models") or []),
    }


def replay_file(path):
    """Read one case file and report on it."""
    with open(path, encoding="utf-8") as handle:
        state = json.load(handle)
    if not isinstance(state, dict):
        raise ValueError("a case file must contain a JSON object")
    return report(state)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m bp.product.replay <case.json>", file=sys.stderr)
        return 2
    try:
        result = replay_file(argv[0])
    except (OSError, ValueError) as error:
        print("replay failed: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    if result["ok"]:
        return 0
    if not result["plan"].get("match"):
        print("the frozen plan does not replay: " + str(result["plan"].get("reason")
                                                       or "its hash changed"), file=sys.stderr)
    if not result["brief"]["match"]:
        print("the brief is not the one the plan was frozen against", file=sys.stderr)
    for problem in result["recompute"]:
        print("figure drift: " + problem, file=sys.stderr)
    for problem in result["claims"]:
        print("claim: " + problem, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
