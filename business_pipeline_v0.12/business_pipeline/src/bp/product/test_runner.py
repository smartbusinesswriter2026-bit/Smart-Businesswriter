"""Automated test runner for the admin monitor (product layer, stdlib only).

Runs pytest suites and returns structured results. Uses subprocess to invoke
pytest so it works with the existing test infrastructure without importing
test modules into the server process.

Suites cover all pipeline domains: computations, frameworks, prose, paper,
accounting, economics, finance, statistics, marketing, management, operations,
project, entrepreneurship, people, research, supply_chain, plus meta suites.

Results are stored under state/test_results/ as JSONL.
"""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import ops as ops_mod

# Suite -> list of test file globs (relative to repo root)
SUITES = {
    # ── Core ──
    "computations": [
        "tests/test_methods.py",
        "tests/test_schedule_routes.py",
        "tests/test_statement_plan.py",
        "tests/test_financial_computations.py",
    ],
    "frameworks": [
        "tests/test_completion.py",
        "tests/test_conductor_frameworks.py",
        "tests/test_pestel_completion.py",
        "tests/test_framework_profiles.py",
        "tests/test_leadership_culture_ethics.py",
        "tests/test_word_count_length.py",
    ],
    "prose": [
        "tests/test_prose.py",
        "tests/test_plan_verifier.py",
        "tests/test_plan_corpus.py",
        "tests/test_writing.py",
    ],
    "paper": [
        "tests/test_chat.py",
        "tests/test_business_plan_profile.py",
        "tests/test_capability_papers.py",
        "tests/test_paper_documents.py",
        "tests/test_project_plan.py",
    ],
    # ── Accounting ──
    "accounting": [
        "tests/test_accounts.py",
        "tests/test_accounting_operations.py",
        "tests/test_accounting_pipeline_integration.py",
        "tests/test_accounting_sandbox_parity.py",
        "tests/test_articulation.py",
        "tests/test_bad_debt.py",
        "tests/test_balance_sheet_sections.py",
        "tests/test_cashflow.py",
        "tests/test_closing.py",
        "tests/test_deferrals.py",
        "tests/test_depreciation_methods.py",
        "tests/test_disposal.py",
        "tests/test_double_counting.py",
        "tests/test_equity_statement.py",
        "tests/test_input_proportions.py",
        "tests/test_je_validation.py",
        "tests/test_journal_view.py",
        "tests/test_ledger.py",
        "tests/test_line_tax.py",
        "tests/test_oci.py",
        "tests/test_purchases.py",
        "tests/test_ratio.py",
        "tests/test_reconcile.py",
        "tests/test_reconcile2.py",
        "tests/test_revaluation.py",
        "tests/test_reversals.py",
        "tests/test_schedules.py",
        "tests/test_schedule_golden.py",
        "tests/test_schedule_routes.py",
        "tests/test_statements_render_contract.py",
        "tests/test_t_account_ledger.py",
        "tests/test_trial_balance_check.py",
    ],
    # ── Economics ──
    "economics": [
        "tests/test_economics.py",
        "tests/test_economics_remaining.py",
        "tests/test_macroeconomics.py",
        "tests/test_money.py",
        "tests/test_national_income.py",
    ],
    # ── Finance ──
    "finance": [
        "tests/test_appraisal.py",
        "tests/test_currency.py",
        "tests/test_finance_additions.py",
        "tests/test_investment.py",
        "tests/test_portfolio_performance.py",
        "tests/test_portfolio_valuation.py",
        "tests/test_valuation.py",
    ],
    # ── Statistics ──
    "statistics": [
        "tests/test_anova.py",
        "tests/test_chisquare.py",
        "tests/test_correlation.py",
        "tests/test_factorial_posthoc.py",
        "tests/test_forecast.py",
        "tests/test_inference_more.py",
        "tests/test_logit_reliability.py",
        "tests/test_missing.py",
        "tests/test_multicomp.py",
        "tests/test_power.py",
        "tests/test_regression.py",
        "tests/test_weighted.py",
    ],
    # ── Marketing ──
    "marketing": [
        "tests/test_attribution_completion.py",
        "tests/test_digital_mix_completion.py",
        "tests/test_email_crm_completion.py",
        "tests/test_funnel_completion.py",
        "tests/test_marketing_additions.py",
        "tests/test_marketing_automation_completion.py",
        "tests/test_marketing_plan_completion.py",
        "tests/test_marketing_worksheets.py",
        "tests/test_paid_media_plan_completion.py",
        "tests/test_rfm_completion.py",
        "tests/test_seo_content_completion.py",
        "tests/test_social_media_completion.py",
        "tests/test_stp_completion.py",
        "tests/test_stp_evidence_completion.py",
        "tests/test_tam_completion.py",
    ],
    # ── Management ──
    "management": [
        "tests/test_adkar_completion.py",
        "tests/test_aida_completion.py",
        "tests/test_bcg_completion.py",
        "tests/test_brand_equity_completion.py",
        "tests/test_burke_litwin_completion.py",
        "tests/test_change_organization_completion.py",
        "tests/test_cro_completion.py",
        "tests/test_customer_journey_completion.py",
        "tests/test_generic_strategies_completion.py",
        "tests/test_kano_completion.py",
        "tests/test_lewin_completion.py",
        "tests/test_logic_model_completion.py",
        "tests/test_mckinsey_7s_completion.py",
        "tests/test_mintzberg_completion.py",
        "tests/test_pdsa_completion.py",
        "tests/test_porters_diamond_completion.py",
        "tests/test_raci_completion.py",
        "tests/test_servqual_completion.py",
        "tests/test_strategic_positioning_completion.py",
        "tests/test_theory_of_change_completion.py",
        "tests/test_utaut_completion.py",
    ],
    # ── Operations ──
    "operations": [
        "tests/test_operations_frameworks.py",
        "tests/test_project_worksheets.py",
    ],
    # ── Project Management ──
    "project": [
        "tests/test_project_batch_a.py",
        "tests/test_project_batch_b.py",
        "tests/test_project_batch_c.py",
        "tests/test_project_batch_d.py",
        "tests/test_project_worksheets.py",
    ],
    # ── Entrepreneurship ──
    "entrepreneurship": [
        "tests/test_entrepreneurship.py",
        "tests/test_entrepreneurship_planning.py",
    ],
    # ── People ──
    "people": [
        "tests/test_people_frameworks.py",
    ],
    # ── Research ──
    "research": [
        "tests/test_assist.py",
        "tests/test_literature.py",
        "tests/test_literature_api.py",
        "tests/test_literature_failover.py",
        "tests/test_literature_log.py",
        "tests/test_matrix_assist.py",
        "tests/test_matrix_chat.py",
        "tests/test_matrix_completion.py",
        "tests/test_matrix_figure.py",
        "tests/test_measurement_plan_completion.py",
        "tests/test_registry.py",
        "tests/test_sources.py",
        "tests/test_sources_file.py",
    ],
    # ── Supply Chain ──
    "supply_chain": [
        "tests/test_subject_supply_chain_acceptance.py",
    ],
    # ── Meta / Product ──
    "meta": [
        "tests/test_product_api.py",
        "tests/test_product_boundary.py",
        "tests/test_product_cases.py",
        "tests/test_product_ops.py",
        "tests/test_product_paper_batch.py",
        "tests/test_product_routes.py",
        "tests/test_product_server.py",
        "tests/test_product_subjects.py",
        "tests/test_product_statements.py",
        "tests/test_product_statements_api.py",
        "tests/test_product_statements_tile.py",
        "tests/test_docs_sync.py",
        "tests/test_frozen_contract.py",
        "tests/test_catalogue_truth.py",
        "tests/test_shelf_invariants.py",
        "tests/test_worksheet_reachability.py",
        "tests/test_worksheet_export.py",
    ],
    # ── Hallucination ──
    "hallucination": [
        "tests/test_prose.py",
        "tests/test_plan_verifier.py",
    ],
    # ── Regression (harvested golden fixes) ──
    "regression": [
        "tests/test_problem_norm_regression.py",
    ],
    # ── All (run everything) ──
    "all": None,  # special: runs all test files
}


def _repo_root():
    return ops_mod.repo_root()


def _results_dir():
    d = ops_mod.state_dir() / "test_results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _results_path():
    return _results_dir() / "results.jsonl"


def _run_pytest(files):
    """Run pytest on a list of files, return (passed, failed, total, failures, duration)."""
    root = _repo_root()
    if files is None:
        # Run all tests
        cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short", "-p", "no:cacheprovider"]
    else:
        cmd = [sys.executable, "-m", "pytest"] + files + ["-q", "--tb=short", "-p", "no:cacheprovider"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    env["BP_STATEMENT_LIBRARY_DIR"] = str(root / "state" / "test_lib")
    start = datetime.datetime.now(datetime.timezone.utc)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            cwd=str(root), env=env)
    except subprocess.TimeoutExpired:
        return 0, 0, 0, ["TIMEOUT after 600s"], 600000
    duration = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds() * 1000

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    passed = 0
    failed = 0
    for line in stdout.splitlines() + stderr.splitlines():
        line = line.strip()
        m_passed = re.search(r"(\d+)\s+passed", line)
        m_failed = re.search(r"(\d+)\s+failed", line)
        m_error = re.search(r"(\d+)\s+error", line)
        if m_passed:
            passed = int(m_passed.group(1))
        if m_failed:
            failed = int(m_failed.group(1))
        if m_error:
            failed += int(m_error.group(1))

    total = passed + failed

    failures = []
    for line in stdout.splitlines():
        if "FAILED" in line:
            parts = line.split("::")
            if len(parts) >= 2:
                failures.append(parts[-1].strip()[:120])
            elif line.strip():
                failures.append(line.strip()[:120])
    if not failures and failed > 0:
        for line in (stdout + stderr).splitlines()[-10:]:
            if line.strip():
                failures.append(line.strip()[:120])

    return passed, failed, total, failures[:20], round(duration, 1)


def run_suite(suite_name):
    """Run one suite, store result, return dict."""
    if suite_name not in SUITES:
        return {"suite": suite_name, "error": "unknown suite", "passed": 0, "failed": 0, "total": 0, "failures": []}

    files = SUITES[suite_name]
    root = _repo_root()

    if files is not None:
        existing = [f for f in files if (root / f).is_file()]
        if not existing:
            return {"suite": suite_name, "error": "no test files found", "passed": 0, "failed": 0, "total": 0, "failures": []}
    else:
        existing = None

    passed, failed, total, failures, duration = _run_pytest(existing)
    result = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "suite": suite_name,
        "passed": passed,
        "failed": failed,
        "total": total,
        "failures": failures,
        "duration_ms": duration,
        "files": existing if existing else ["tests/ (all)"],
    }
    try:
        path = _results_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass
    return result


def list_results(limit=20):
    """Return recent test results, newest first."""
    path = _results_path()
    if not path.is_file():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
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


def suites():
    """Return the list of available suites."""
    return list(SUITES.keys())