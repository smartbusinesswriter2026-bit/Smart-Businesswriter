"""Health: what is wrong with the pipeline, named (product layer, stdlib only).

`/api/health` reports the **server**: the build, the case store, the request
log.  That is not the **pipeline**.  A pipeline can be perfectly up while its
corpus is down, its cases are failing, its repair loop is idle, and its own
test suite is red.  This module reads the signals that already exist and says
which of them are wrong.

**The shape is a list, not a score.**  Each check returns its own verdict, and
the overall bit is the conjunction of the checks that matter.  A percentage of
checks that pass is a metric that invites turning off the checks you cannot
pass; a list is read.

**A missing signal is never a green.**  A check that cannot be run returns
``ok=False`` with a reason.  Two kinds of "not ok" are kept apart:

* ``severity="required"`` - the signal is missing or wrong, and the overall
  bit is affected;
* ``severity="advisory"`` - the signal is informational (the model is off, the
  relevance sweep has never run, the test suite has never been run here).  It
  is reported plainly, and it does not degrade a pipeline that is otherwise
  sound.

**Nothing here acts.**  This module reads.  It never starts a loop, never
repairs anything, and never applies a gap.  The switches on the Loops tab
decide what runs.

**Every check is a function of its inputs**, so a test can call it with a
prepared signal instead of a running server.  `health()` is the only function
that reaches for the real world.
"""

import json
import os
from datetime import datetime, timezone

from .. import build as build_info

FORMAT = "bp-pipeline-health/1"

#: The checks, in the order the panel prints them.
CHECKS = (
    "server", "case_store", "case_pass_rate", "regressions", "corpus",
    "repair_loop", "causes", "eval_baseline", "test_suite", "relevance",
    "model_assistance", "switches",
)

#: The checks whose verdict the overall bit depends on **when they have a
#: signal**.  The rest are reported and explained, but a pipeline that is
#: otherwise sound is not degraded by a switch the owner turned off.
#:
#: The verdict is taken from each row's own ``severity``, not from this list:
#: a check that has never been measured is advisory (the pipeline is not
#: broken by a measurement nobody took), while a check that was measured and
#: is now stale is required (the measurement says nothing about this build).
REQUIRED = ("case_store", "case_pass_rate", "regressions", "corpus",
            "repair_loop", "causes", "eval_baseline", "test_suite")

#: The pipeline-failure budget.  The same number the eval program counts
#: against: pipeline failures only, never an invalid fixture.
FAIL_BUDGET = 2


def _now():
    return datetime.now(timezone.utc).isoformat()


def _check(name, ok, reason="", severity="required", **extra):
    """One named check."""
    row = {"name": name, "ok": bool(ok), "severity": severity,
           "reason": str(reason or ""), "checked_at": _now()}
    row.update(extra)
    return row


def _degraded(name, reason, **extra):
    return _check(name, False, reason, "required", **extra)


def _advisory(name, reason, **extra):
    return _check(name, False, reason, "advisory", **extra)


# ── H1 server ─────────────────────────────────────────────────────────────
def check_server(extra=None):
    """The server answered.  It is ok by the fact that this ran."""
    extra = extra or {}
    model = bool(extra.get("model_assistance"))
    return _check("server", True, "the server answered", "advisory",
                  build=str(getattr(build_info, "VERSION", "") or ""),
                  model_assistance=model,
                  sandbox=str(extra.get("sandbox") or ""))


# ── H2 case store ─────────────────────────────────────────────────────────
def check_case_store(summary=None):
    """Is the stored case library readable?"""
    if summary is None:
        from . import case_store
        try:
            summary = case_store.summary()
        except Exception as error:
            return _degraded("case_store", "the case store could not be read: %s"
                             % str(error)[:160])
    total = summary.get("total")
    if total is None:
        return _degraded("case_store", "the case store returned no count")
    if int(total) <= 0:
        return _degraded("case_store", "the case store holds no cases")
    return _check("case_store", True, "%d stored cases" % int(total), "required",
                  cases=int(total), tiles=sum(int(row.get("tiles") or 0)
                                              for row in summary.get("by_subject") or []))


# ── H3 case pass rate ─────────────────────────────────────────────────────
def check_case_pass_rate(errors=None, budget=FAIL_BUDGET):
    """How many open tile-case failures are **pipeline** defects?

    The count is by cause, not by wording: an invalid fixture (the case's own
    figures do not add up) is the case's problem and is never counted against
    the pipeline, exactly as the eval program counts it.
    """
    if errors is None:
        from . import ops_log
        try:
            errors = ops_log.list_errors(limit=1000, status="open")
        except Exception as error:
            return _degraded("case_pass_rate", "the error log could not be read: %s"
                             % str(error)[:160])
    from . import causes
    pipeline, invalid = [], []
    for row in errors or []:
        if not row.get("case_id"):
            continue
        scope = causes.classify_cause(row.get("error") or "",
                                       row.get("problem"))["scope"]
        if scope == causes.PIPELINE:
            pipeline.append(row)
        else:
            invalid.append(row)
    count = len(pipeline)
    if count > int(budget):
        return _degraded("case_pass_rate",
                         "%d pipeline failure(s) open; the budget is %d"
                         % (count, int(budget)),
                         failures=count, invalid=len(invalid), budget=int(budget),
                         cases=[row.get("case_id") for row in pipeline[:10]])
    return _check("case_pass_rate", True,
                  "%d pipeline failure(s) open (budget %d)" % (count, int(budget)),
                  "required", failures=count, invalid=len(invalid),
                  budget=int(budget),
                  cases=[row.get("case_id") for row in pipeline[:10]])


# ── H4 regressions ────────────────────────────────────────────────────────
def check_regressions(run_id=None, regressions=None):
    """A case that passed before and fails now is a blocker."""
    if regressions is None:
        from . import eval_runner
        try:
            if run_id is None:
                runs = eval_runner.runs(limit=20, direction="direction1")
                run_id = runs[0].get("run_id") if runs else None
            if not run_id:
                return _degraded("regressions", "no Direction 1 run to compare against")
            regressions = eval_runner.regressions(run_id)
        except Exception as error:
            return _degraded("regressions", "the runs could not be read: %s"
                             % str(error)[:160])
    if regressions:
        return _degraded("regressions",
                         "%d case(s) passed before and fail now" % len(regressions),
                         regressions=[row.get("case_id") for row in regressions[:10]])
    return _check("regressions", True, "no regressions", "required",
                  count=len(regressions or []))


# ── H5 corpus ─────────────────────────────────────────────────────────────
def check_corpus(probe=None):
    """Is the proprietary corpus index reachable?

    The corpus adapter **fails open**, so a down index looks exactly like a
    tile with no evidence.  This check asks the index itself.  A down corpus
    degrades the pipeline even when everything else is green, because the
    retrieval is then *not measured* rather than empty.
    """
    if probe is None:
        from . import eval_runner
        probe = eval_runner.corpus_available
    try:
        up = bool(probe())
    except Exception as error:
        return _degraded("corpus", "the corpus index could not be asked: %s"
                         % str(error)[:160])
    if not up:
        return _degraded("corpus",
                         "the corpus index is not reachable, so retrieval is not measured")
    return _check("corpus", True, "the corpus index answered", "required")


# ── H6 repair loop ────────────────────────────────────────────────────────
def _switch_rows(switches):
    """The switches as a list of rows, whether they arrive as a list or a map."""
    if isinstance(switches, dict):
        rows = []
        for key, value in switches.items():
            row = dict(value or {})
            row.setdefault("key", key)
            rows.append(row)
        return rows
    return list(switches or [])


def _switch_state(switches, key):
    """One switch's row, or an empty dict."""
    for row in _switch_rows(switches):
        if row.get("key") == key:
            return row
    return {}


def check_repair_loop(status=None, ledger=None, switches=None):
    """Is the repair loop doing its job when there is work for it?

    An open pipeline cause with an idle loop is not ok.  A loop that is
    **switched off** is a reason, not a failure: the owner turned it off.
    """
    if status is None:
        from . import autoresearch
        try:
            status = autoresearch.status()
        except Exception as error:
            return _degraded("repair_loop", "the repair loop's status could not be read: %s"
                             % str(error)[:160])
    if ledger is None:
        from . import cause_ledger
        try:
            ledger = cause_ledger.summary()
        except Exception:
            ledger = {}
    totals = (ledger or {}).get("summary") or {}
    open_causes = int(totals.get("unfixed", 0)) + int(totals.get("recurring", 0))
    running = bool((status or {}).get("running"))
    if switches is None:
        from . import ops_switches
        try:
            switches = ops_switches.all_switches()
        except Exception:
            switches = {}
    repair = _switch_state(switches, "loop.repair")
    enabled = bool(repair.get("enabled"))
    if open_causes and not running:
        if not enabled:
            return _check("repair_loop", True,
                          "the repair loop is switched off and %d cause(s) wait" % open_causes,
                          "advisory", running=running, enabled=False, open_causes=open_causes)
        return _degraded("repair_loop",
                         "%d cause(s) wait and the repair loop is idle" % open_causes,
                         running=running, enabled=True, open_causes=open_causes)
    return _check("repair_loop", True,
                  "the repair loop is running" if running else "nothing waits for the repair loop",
                  "required", running=running, enabled=enabled,
                  open_causes=open_causes)


# ── H7 causes ─────────────────────────────────────────────────────────────
def check_causes(ledger=None):
    """Is any cause coming back?"""
    if ledger is None:
        from . import cause_ledger
        try:
            ledger = cause_ledger.summary()
        except Exception as error:
            return _degraded("causes", "the cause ledger could not be read: %s"
                             % str(error)[:160])
    totals = (ledger or {}).get("summary") or {}
    recurring = int(totals.get("recurring", 0))
    if recurring:
        names = [row.get("cause") for row in (ledger or {}).get("causes") or []
                 if row.get("status") == "recurring"]
        return _degraded("causes", "%d cause(s) came back after a fix" % recurring,
                         recurring=recurring, causes=names[:10],
                         fixed=int(totals.get("fixed", 0)),
                         fixed_pct=totals.get("fixed_pct"))
    return _check("causes", True, "no cause is recurring", "required",
                  recurring=0, fixed=int(totals.get("fixed", 0)),
                  fixed_pct=totals.get("fixed_pct"),
                  causes=int(totals.get("causes", 0)))


# ── H8 eval baseline ──────────────────────────────────────────────────────
def tree_build_date():
    """The date of the tree's own newest build, from the changelog.

    This is the file the project already uses to say when the build changed.
    It is read rather than shelling out to git, so the check works in a
    deployment with no git.
    """
    from . import ops as ops_mod
    path = ops_mod.repo_root() / "docs" / "CHANGELOG.md"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("- ") and " (" in line:
                    stamp = line.split("(", 1)[1].split(")", 1)[0].strip()
                    return stamp
    except OSError:
        pass
    return ""


def _age_of(stamp, now=None):
    """How old a timestamp is, in words.  "" when there is no timestamp."""
    text = str(stamp or "").strip()
    if not text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    seconds = int((reference - moment).total_seconds())
    if seconds < 0:
        return "in the future"
    if seconds < 60:
        return "%d second(s) ago" % seconds
    if seconds < 3600:
        return "%d minute(s) ago" % (seconds // 60)
    if seconds < 86400:
        return "%d hour(s) ago" % (seconds // 3600)
    return "%d day(s) ago" % (seconds // 86400)


def _stale_against_tree(signal_date, tree_date):
    """Is this signal older than the tree's own newest build?

    A measurement taken before the code changed says nothing about the code
    that is there now.  The comparison is by day: a run earlier the same day
    is still the run of this build.
    """
    if not signal_date or not tree_date:
        return False
    return str(signal_date)[:10] < str(tree_date)[:10]


def _signal(signal_date):
    """The two fields every stored signal carries: when it was taken, how old."""
    return {"signal_checked_at": str(signal_date or ""),
            "age": _age_of(signal_date)}


def check_eval_baseline(manifest=None, tree_date=None):
    """The last Direction 1 run: within budget, no regressions, and current."""
    if manifest is None:
        from . import eval_runner
        try:
            runs = eval_runner.runs(limit=5, direction="direction1")
            manifest = runs[0] if runs else None
        except Exception as error:
            return _degraded("eval_baseline", "the eval runs could not be read: %s"
                             % str(error)[:160])
    if not manifest:
        return _degraded("eval_baseline",
                         "no Direction 1 run yet; the pipeline has not been measured")
    counts = manifest.get("counts") or {}
    failures = int(counts.get("fail", 0))
    regressions = manifest.get("regressions") or []
    if failures > FAIL_BUDGET:
        return _degraded("eval_baseline",
                         "the last run had %d pipeline failure(s); the budget is %d"
                         % (failures, FAIL_BUDGET),
                         failures=failures, budget=FAIL_BUDGET,
                         run_id=manifest.get("run_id"),
                         checked_at=manifest.get("finished_at") or manifest.get("created_at"))
    if regressions:
        return _degraded("eval_baseline",
                         "the last run had %d regression(s)" % len(regressions),
                         failures=failures, budget=FAIL_BUDGET,
                         run_id=manifest.get("run_id"),
                         checked_at=manifest.get("finished_at") or manifest.get("created_at"))
    if tree_date is None:
        tree_date = tree_build_date()
    finished = str(manifest.get("finished_at") or manifest.get("created_at") or "")
    signal = _signal(finished)
    if _stale_against_tree(finished, tree_date):
        return _degraded("eval_baseline",
                         "the last run predates build %s; run it again"
                         % str(tree_date),
                         failures=failures, budget=FAIL_BUDGET,
                         run_id=manifest.get("run_id"), checked_at=finished,
                         tree_date=str(tree_date), **signal)
    return _check("eval_baseline", True,
                  "the last run had %d pipeline failure(s) and no regression" % failures,
                  "required", failures=failures, budget=FAIL_BUDGET,
                  run_id=manifest.get("run_id"), checked_at=finished,
                  tree_date=str(tree_date), **signal)


# ── H9 test suite ─────────────────────────────────────────────────────────
def check_test_suite(results=None, tree_date=None):
    """The last stored result of each suite.

    A suite that has **never been run here** is not measured, so it is
    advisory: the pipeline is not degraded by a measurement the owner has not
    taken yet.  A suite that ran and **failed** degrades the pipeline.  A
    suite that ran **before the code changed** is stale, and says nothing
    about the code that is there now.
    """
    if results is None:
        from . import test_runner
        try:
            results = test_runner.list_results(limit=50)
        except Exception as error:
            return _degraded("test_suite", "the stored results could not be read: %s"
                             % str(error)[:160])
    latest = {}
    for row in results or []:
        name = str(row.get("suite") or "")
        if not name:
            continue
        current = latest.get(name)
        # The newest result of a suite is the one that counts; the store is
        # written newest-first, but the timestamp is the truth.
        if current is None or str(row.get("ts") or "") > str(current.get("ts") or ""):
            latest[name] = row
    if not latest:
        return _advisory("test_suite", "no suite has been run here")
    failed = {name: row for name, row in latest.items() if int(row.get("failed") or 0)}
    total = sum(int(row.get("total") or 0) for row in latest.values())
    passed = sum(int(row.get("passed") or 0) for row in latest.values())
    newest = max((str(row.get("ts") or "") for row in latest.values()), default="")
    signal = _signal(newest)
    if tree_date is None:
        tree_date = tree_build_date()
    if failed:
        return _degraded("test_suite",
                         "%d of %d suite(s) failed: %s"
                         % (len(failed), len(latest), ", ".join(sorted(failed)[:5])),
                         suites=len(latest), passed=passed, total=total,
                         failing=sorted(failed)[:10], **signal)
    if _stale_against_tree(newest, tree_date):
        return _degraded("test_suite",
                         "the last suite run predates build %s; run the suites again"
                         % str(tree_date),
                         suites=len(latest), passed=passed, total=total,
                         tree_date=str(tree_date), **signal)
    return _check("test_suite", True, "%d suite(s) green" % len(latest), "required",
                  suites=len(latest), passed=passed, total=total,
                  tree_date=str(tree_date or ""), **signal)


# ── H10 relevance ─────────────────────────────────────────────────────────
def check_relevance(run=None):
    """The relevance sweep: did its controls hold?

    A sweep that has never run is not measured (advisory).  A sweep that ran
    and whose **controls failed** is a degraded measurement: it cannot be
    trusted to propose a capability gap, and the pipeline's sense of what it
    should know is stale.
    """
    if run is None:
        try:
            from .relevance import storage as _storage
            runs = _storage.read_runs(limit=5)
            run = runs[-1] if runs else None
        except Exception as error:
            return _advisory("relevance", "the relevance runs could not be read: %s"
                             % str(error)[:160])
    if not run:
        return _advisory("relevance", "the relevance sweep has never run here")
    controls = run.get("controls") or {}
    held = controls.get("held")
    total = controls.get("total")
    finished = str(run.get("finished_at") or run.get("started_at") or "")
    signal = _signal(finished)
    if run.get("status") == "running":
        return _check("relevance", True, "the relevance sweep is running", "advisory",
                      run_id=run.get("run_id"), **signal)
    if total and held is not None and int(held) < int(total) * float(controls.get("min_held") or 0.75):
        return _degraded("relevance",
                         "the last sweep's controls held %s of %s, so it cannot be trusted"
                         % (held, total),
                         run_id=run.get("run_id"), held=held, total=total, **signal)
    return _check("relevance", True, "the last sweep's controls held", "advisory",
                  run_id=run.get("run_id"), held=held, total=total, **signal)


# ── H11 model assistance ──────────────────────────────────────────────────
def check_model_assistance(extra=None):
    """Whether a model is configured.  Reported, never a failure."""
    extra = extra or {}
    on = bool(extra.get("model_assistance"))
    return _check("model_assistance", True,
                  "model assistance is on" if on else "model assistance is off",
                  "advisory", model_assistance=on)


# ── H12 switches ──────────────────────────────────────────────────────────
def check_switches(switches=None):
    """The owner's own switches.  Reported, never a failure."""
    if switches is None:
        from . import ops_switches
        try:
            switches = ops_switches.all_switches()
        except Exception as error:
            return _advisory("switches", "the switches could not be read: %s"
                             % str(error)[:160])
    rows = _switch_rows(switches)
    on = [row.get("key") for row in rows if row.get("enabled")]
    running = [row.get("key") for row in rows if row.get("running")]
    return _check("switches", True, "%d switch(es) on, %d loop(s) running"
                  % (len(on), len(running)), "advisory",
                  enabled=on, running=running,
                  total=len(rows))


# ── the whole thing ───────────────────────────────────────────────────────
def health(extra=None, sources=None):
    """The pipeline's health: a list of named checks and one overall bit.

    ``sources`` lets a caller (or a test) hand in the signals instead of
    having them read.  Every key is optional; anything not supplied is read
    for real.
    """
    sources = sources or {}
    extra = extra or sources.get("extra") or {}
    tree_date = sources.get("tree_date")
    if tree_date is None:
        tree_date = tree_build_date()
    checks = [
        check_server(extra),
        check_case_store(sources.get("case_store")),
        check_case_pass_rate(sources.get("errors")),
        check_regressions(sources.get("run_id"), sources.get("regressions")),
        check_corpus(sources.get("corpus_probe")),
        check_repair_loop(sources.get("repair_status"), sources.get("ledger"),
                          sources.get("switches")),
        check_causes(sources.get("ledger")),
        check_eval_baseline(sources.get("manifest"), tree_date),
        check_test_suite(sources.get("test_results"), tree_date),
        check_relevance(sources.get("relevance_run")),
        check_model_assistance(extra),
        check_switches(sources.get("switches")),
    ]
    # The overall bit is the conjunction of the rows that are **required**
    # and not ok.  A row's own severity decides: a check that was never
    # measured is advisory, and a check that was measured and is now stale
    # is required.
    failing = [row for row in checks if row["severity"] == "required" and not row["ok"]]
    advisory = [row for row in checks if row["severity"] != "required" and not row["ok"]]
    report = {
        "format": FORMAT,
        "overall": not failing,
        "checked_at": _now(),
        "build": str(getattr(build_info, "VERSION", "") or ""),
        "checks": checks,
        "failing": [row["name"] for row in failing],
        "advisory": [row["name"] for row in advisory],
    }
    return report


def _health_path():
    from . import ops as ops_mod
    return ops_mod.state_dir() / "health" / "health.jsonl"


#: The ops-log lane the health findings live in.  It is their own lane so the
#: panel can show them apart from the pipeline's own errors.
LANE = "pipeline-health"


def _live_issues(name):
    """The health issues for one check that are still live.

    An issue is live until it is resolved, invalidated or dismissed.  An
    **attended** issue is still live: attending it tells the repair loop to
    leave it alone, it does not close it.
    """
    from . import ops_log
    rows = ops_log.list_errors(limit=1000, lane=LANE, status="all")
    return [row for row in rows
            if row.get("gap_label") == name
            and not (row.get("resolved") or row.get("invalid") or row.get("dismissed"))]


def _find_issue(message):
    """The id of the issue carrying this exact message, or None."""
    from . import ops_log
    rows = ops_log.list_errors(limit=1000, lane=LANE, status="all")
    for row in rows:
        if str(row.get("error") or "").strip() == str(message).strip():
            return row.get("error_id")
    return None


def log_issues(report=None):
    """Log the failing checks into the ops log, once each.

    A check that fails twice in a row is **one** issue, not two: the second
    failure carries no new information and a second id would give the repair
    loop something to re-fix.  A check that recovers is marked resolved with a
    note, so the history keeps the failure and the recovery.

    The findings are **attended**, not open.  A health finding is a fact for
    the owner ("the corpus index is not reachable"), not something the
    auto-fixer can repair by replaying a case; attending it stops the repair
    loop from spending model calls on it.
    """
    if report is None:
        report = health()
    from . import ops_log
    logged, resolved, kept = [], [], []
    for row in report.get("checks") or []:
        name = row.get("name")
        live = _live_issues(name)
        if row.get("ok"):
            for issue in live:
                ops_log.mark_error_verified(
                    issue.get("error_id"),
                    "the check is ok again", cause="pipeline.health", artifact="")
                resolved.append(name)
            continue
        if row.get("severity") != "required":
            continue                      # an advisory signal is not an issue
        if live:
            kept.append(name)
            continue
        message = "health: %s - %s" % (name, row.get("reason") or "degraded")
        if not ops_log.log_error(LANE, message, gap_label=name, force=True):
            continue
        error_id = _find_issue(message)
        if error_id:
            ops_log.mark_error_attended(
                error_id, "a health finding for the owner, not a defect the loop can repair")
        logged.append(name)
    return {"logged": logged, "resolved": resolved, "kept": kept}


def health_record(report=None):
    """Write the report to the health store and return the path.

    The store is a JSONL of the reports, so a run can be compared with the
    previous one without re-running anything.  It is never rewritten and
    never pruned here.
    """
    if report is None:
        report = health()
    path = _health_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, default=str) + "\n")
    except OSError:
        return ""
    return str(path)


def history(limit=20):
    """The stored health reports, newest first."""
    path = _health_path()
    if not os.path.isfile(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    rows.reverse()
    return rows[:limit]
