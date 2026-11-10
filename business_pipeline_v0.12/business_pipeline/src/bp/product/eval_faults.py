"""Fault injection for the repair loop (product layer, standard library only).

The repair loop is only worth measuring when the failure it repairs is real.
This module seeds **known faults** into a copy of the case store, replays
them, and checks that the pipeline classifies each one the way the cause
rules say it must:

===============  ==========  ==================================================
fault            scope       what it proves
===============  ==========  ==================================================
broken_inputs    invalid     the case's **own figures** are refused at intake
                             and never reach the ledger as a defect.
tampered_        fail        a wrong recorded expectation is a **pipeline**
expectation                  problem, not an invalid fixture.
missing_phrase   fail        a paper that lost a required phrase is caught.
bad_corpus_      pass        a corpus that answers nothing produces a RAG
query                       score of *not measured*, never a green.
===============  ==========  ==================================================

**The owner's cases are never touched.**  The faults are seeded into a copy of
the case store, and the run points `BP_CASE_ROOT` at that copy and `BP_OPS_LOG`
at a sandbox log, so neither the stored cases nor the live error list is
written to.  The module checks that afterwards and says so.

Nothing here repairs anything.  The point is to measure whether the loop
*sees* a fault and *names* it correctly.
"""

import json
import os
import shutil
import tempfile

from . import case_invariants
from . import case_runner
from . import case_store

#: The faults this module can seed, with the scope each one must produce.
FAULTS = (
    {"name": "broken_inputs", "scope": "invalid",
     "note": "the case's own figures do not satisfy the method's own identity"},
    {"name": "tampered_expectation", "scope": "fail",
     "note": "the recorded expectation no longer matches the frozen method"},
    {"name": "missing_phrase", "scope": "fail",
     "note": "the paper no longer carries a required phrase"},
    {"name": "bad_corpus_query", "scope": "pass",
     "note": "the corpus answers nothing, so the RAG score is not measured"},
)

FAULT_NAMES = tuple(spec["name"] for spec in FAULTS)


def _spec(name):
    for spec in FAULTS:
        if spec["name"] == str(name):
            return spec
    raise ValueError("unknown fault: %r (known: %s)" % (name, ", ".join(FAULT_NAMES)))


def sandbox(root=None):
    """A copy of the case store to seed faults into.

    Returns the path of the copy.  The caller removes it.  The copy is a
    plain copy of the owner's cases: the same shape, the same names, so the
    replay is the real replay.
    """
    target = root or tempfile.mkdtemp(prefix="eval-faults-")
    source = case_store._root()
    if os.path.isdir(source):
        for name in os.listdir(source):
            src = os.path.join(source, name)
            dst = os.path.join(target, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    return target


def _numeric(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _break_inputs(case):
    """Perturb the case's own figures until its own invariants object.

    The perturbation is chosen by the method's own invariants, not guessed,
    and it has to **survive the re-recording**: the figures are changed, the
    method is run again, the expectation is recorded from the new figures,
    and only then are the invariants asked.  A break that the re-recording
    repairs is not a break - it would have replayed as a pass.

    Returns (inputs, recorded_result, problem) or (None, None, None).
    """
    method = case.get("method") or ""
    inputs = case.get("inputs") or {}
    for name, value in list(inputs.items()):
        number = _numeric(value)
        if number is None:
            continue
        for factor in (10.0, 0.1, 3.0, 2.0, 0.5, -1.0):
            trial = dict(inputs)
            trial[name] = str(number * factor)
            try:
                recorded = _run_method_for(case, trial)
            except Exception:
                continue
            problems = case_invariants.check(method, trial, recorded)
            for problem in problems:
                if str(problem).startswith("invalid input: "):
                    return trial, recorded, str(problem)
    return None, None, None


def _run_method_for(case, inputs):
    """The frozen method's own result for these figures."""
    from . import paper_batch
    _subject_row, _group, tile = paper_batch._find_tile(case.get("subject"), case.get("tile"))
    output = paper_batch._run_method(tile, inputs)
    if isinstance(output, dict):
        return {str(name): str(value) for name, value in output.items()
                if not str(name).startswith("_")}
    return {}


def inject(fault, case):
    """Seed one fault into a case.  Returns (case, expectation).

    The expectation is the scope the fault must produce.  A fault that
    cannot be seeded into this case raises ValueError with the reason, so a
    run never reports "pass" for a fault it never applied.
    """
    name = _spec(fault)["name"]
    case = json.loads(json.dumps(case or {}))     # a copy: the owner's case is untouched
    expected = case.setdefault("expected", {})

    if name == "broken_inputs":
        inputs, recorded, problem = _break_inputs(case)
        if inputs is None:
            raise ValueError("this case's method has no input identity to break")
        case["inputs"] = inputs
        # The expectation is re-recorded from the broken figures, exactly as
        # the owner's own invalid fixtures were recorded: the computation
        # agrees with the case, and only the method's own identity objects.
        # Without this the case would fail on the result as well, and a
        # failure is a different scope from an invalid input.
        if recorded:
            expected["result"] = recorded
        return case, {"scope": "invalid", "problem": problem}

    if name == "tampered_expectation":
        result = expected.get("result") or {}
        if not result:
            raise ValueError("this case records no expected result to tamper with")
        key = sorted(result)[0]
        original = result[key]
        number = _numeric(original)
        result[key] = str((number or 0) + 17.5)
        expected["result"] = result
        return case, {"scope": "fail", "tampered": key,
                      "was": str(original), "now": str(result[key])}

    if name == "missing_phrase":
        expected["contains"] = ["a phrase this paper does not carry"]
        expected.pop("contract", None)
        return case, {"scope": "fail", "phrase": "a phrase this paper does not carry"}

    if name == "bad_corpus_query":
        return case, {"scope": "pass", "corpus": "unreachable"}

    raise ValueError("unknown fault: %r" % (fault,))


def _pick_case(case_id=None, method=None):
    """The case to seed a fault into."""
    cases = case_store.load_cases()
    if case_id:
        for case in cases:
            if str(case.get("id")) == str(case_id):
                return case
        return None
    if method:
        for case in cases:
            if str(case.get("method")) == str(method):
                return case
        return None
    return cases[0] if cases else None


def run_fault(fault, case_id=None, method=None, root=None, corpus_down=False):
    """Seed one fault into a sandbox and replay it.

    Returns the outcome: the scope the pipeline gave the fault, whether that
    matched the expectation, and what the pipeline said.
    """
    spec = _spec(fault)
    source_root = case_store._root()
    original = _pick_case(case_id=case_id, method=method)
    if original is None:
        return {"fault": spec["name"], "error": "no such case", "ok": False}
    relative = os.path.relpath(original.get("_path") or "", source_root)
    seeded, expectation = inject(spec["name"], original)

    saved_root = os.environ.get("BP_CASE_ROOT")
    saved_log = os.environ.get("BP_OPS_LOG")
    saved_corpus = os.environ.get("CORPUS_MEILI_URL")
    target = sandbox(root)
    try:
        os.environ["BP_CASE_ROOT"] = target
        os.environ["BP_OPS_LOG"] = os.path.join(target, "ops_log")
        if corpus_down:
            os.environ["CORPUS_MEILI_URL"] = "http://127.0.0.1:1"
        path = os.path.join(target, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(seeded, handle, ensure_ascii=False, indent=1)
        replayed = None
        for case in case_store.load_cases():
            if str(case.get("id")) == str(original.get("id")):
                replayed = case
                break
        outcome = case_runner.run_case_object(replayed or seeded, log=True)
        scope = _scope_of(outcome)
        return {
            "fault": spec["name"],
            "expected_scope": expectation.get("scope"),
            "scope": scope,
            "ok": scope == expectation.get("scope"),
            "status": outcome.get("status"),
            "error": str(outcome.get("error") or "")[:300],
            "expectation": expectation,
        }
    finally:
        for name, value in (("BP_CASE_ROOT", saved_root), ("BP_OPS_LOG", saved_log),
                            ("CORPUS_MEILI_URL", saved_corpus)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(target, ignore_errors=True)


def _scope_of(outcome):
    """The scope the pipeline gave the outcome."""
    from . import eval_runner
    return eval_runner.scope_of((outcome or {}).get("status"))


def live_log_fingerprint():
    """A fingerprint of the live error log, so a run can prove it wrote nothing."""
    from . import ops_log
    path = ops_log._errors_path()
    try:
        with open(path, "rb") as handle:
            return (str(path), len(handle.read()))
    except OSError:
        return (str(path), 0)


def run_faults(case_id=None, method=None):
    """Seed every fault and report what the pipeline made of each one.

    The live error log is fingerprinted before and after: a fault run that
    wrote to the owner's error list has failed, whatever the faults said.
    """
    from . import eval_runner
    before = live_log_fingerprint()
    outcomes = []
    for spec in FAULTS:
        kwargs = {"case_id": case_id}
        if spec["name"] == "broken_inputs":
            kwargs = {"case_id": case_id, "method": method}
        if spec["name"] == "bad_corpus_query":
            kwargs = {"case_id": case_id, "corpus_down": True}
        try:
            outcomes.append(run_fault(spec["name"], **kwargs))
        except Exception as error:
            outcomes.append({"fault": spec["name"], "ok": False,
                             "error": str(error)[:300]})
    after = live_log_fingerprint()
    return {
        "faults": outcomes,
        "live_log_untouched": before == after,
        "live_log": before,
        "scopes": {row.get("fault"): row.get("scope") for row in outcomes},
        "expected_scopes": {spec["name"]: spec["scope"] for spec in FAULTS},
    }