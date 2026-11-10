"""Relevance Research Agent (RRA) — product layer, stdlib only.

External sensing capability: curriculum/assessment benchmarking, standards
watch, coverage mapping, gap specs, obsolescence watchlist.  Design lane
(additive product backend).  No writes to src/bp/**; no frozen-core edits.

See CLAUDE_RESEARCH_MANUAL.md §4 and the RRA integration spec sheet.
"""
from .schemas import (
    EvidenceRecord, CoverageRow, GapSpec, WatchItem,
    TIER_T1, TIER_T2, TIER_T3,
    ACCESS_OPEN, ACCESS_PAYWALLED,
    STATUS_COVERED, STATUS_PARTIAL, STATUS_MISSING, STATUS_PARKED, STATUS_AT_RISK,
    GAP_STATUS_OPEN, GAP_STATUS_APPROVED, GAP_STATUS_REJECTED, GAP_STATUS_DEFERRED,
    PRIORITY_P0, PRIORITY_P1, PRIORITY_P2,
    EFFORT_S, EFFORT_M, EFFORT_L,
    CATEGORY_LABELS,
)
from .storage import (
    state_dir, runs_path, evidence_path, gaps_path, watchlist_path,
    append_run, append_evidence, append_gap, append_watchitem, append_coverage,
    read_runs, read_evidence, read_gaps, read_watchlist, read_coverage,
    read_latest_gap, read_latest_gaps, read_latest_evidence,
)
from .runner import run_sweep
from .s0_scope import build_run_plan, load_school_list, load_allowlist, load_taxonomy, load_backtest
from .s7_gate import record_decision, pending_decisions, decision_summary
from .catalogue_snapshot import build_catalogue_snapshot, write_catalogue_snapshot, load_catalogue_snapshot, check_drift
from . import config as relevance_config
from . import model as relevance_model
from . import discovery as relevance_discovery
from . import controls as relevance_controls
from . import backtest as relevance_backtest

__all__ = [
    "EvidenceRecord", "CoverageRow", "GapSpec", "WatchItem",
    "TIER_T1", "TIER_T2", "TIER_T3",
    "ACCESS_OPEN", "ACCESS_PAYWALLED",
    "STATUS_COVERED", "STATUS_PARTIAL", "STATUS_MISSING", "STATUS_PARKED", "STATUS_AT_RISK",
    "GAP_STATUS_OPEN", "GAP_STATUS_APPROVED", "GAP_STATUS_REJECTED", "GAP_STATUS_DEFERRED",
    "PRIORITY_P0", "PRIORITY_P1", "PRIORITY_P2",
    "EFFORT_S", "EFFORT_M", "EFFORT_L",
    "CATEGORY_LABELS",
    "state_dir", "runs_path", "evidence_path", "gaps_path", "watchlist_path",
    "append_run", "append_evidence", "append_gap", "append_watchitem", "append_coverage",
    "read_runs", "read_evidence", "read_gaps", "read_watchlist", "read_coverage",
    "read_latest_gap", "read_latest_gaps", "read_latest_evidence",
    "run_sweep",
    "build_run_plan", "load_school_list", "load_allowlist", "load_taxonomy", "load_backtest",
    "record_decision", "pending_decisions", "decision_summary",
    "build_catalogue_snapshot", "write_catalogue_snapshot", "load_catalogue_snapshot", "check_drift",
    "relevance_config", "relevance_model", "relevance_discovery",
    "relevance_controls", "relevance_backtest",
]