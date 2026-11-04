"""A stored case bundle shaped like a real delivery (product-layer test fixture).

This helper is not a test module (its name does not match the discovery
pattern `test*.py`); it only builds the JSON documents the product layer
stores, so that the product tests work on realistic shapes taken from the
frozen delivery contract (`session.to_dict()`, the delivery `report` and
`appendix`, and the re-perform bundle).
"""

REPORT = (
    "The net present value is 50.00 currency.\n"
    "The discount rate you supplied was 0.10 per period.\n"
    "Note: these results are computed from synthetic data and must not be read as observations."
)

LIMITATIONS = ["Single constant discount rate."]

HONESTY = {"multiple_hypotheses": "No multiple-hypothesis correction was applied."}

TESTS = ["second_implementation_agrees", "boundary_zero_rate_equals_sum"]


def make_reperform():
    """A re-perform bundle as the orchestrator records it."""
    return {
        "format": "bp-reperform/1",
        "method": {"id": "npv", "version": "1.2.0"},
        "inputs": {"cashflows": ["100", "-50"], "rate": "0.10"},
        "sensitivity": {},
        "outputs": {"npv": "50.00"},
        "flip": None,
        "env_hash": "env-abc123",
        "fingerprint": {"python": "3.14"},
        "spec_hash": "sha256:spec-abc",
        "outputs_hash": "sha256:out-def",
    }


def make_appendix():
    """A delivery appendix as the orchestrator records it."""
    return {
        "spec_hash": "sha256:spec-abc",
        "tier": "T1",
        "method": {"id": "npv", "version": "1.2.0", "category": "capital budgeting",
                   "review_status": "pending_named_reviewer"},
        "run_id": "run123456789",
        "env_hash": "env-abc123",
        "code_hash": "code-def456",
        "fallback_used": None,
        "thresholds": {},
        "frameworks_selected": [],
        "registry": {},
        "code_hash_note": None,
        "sandbox": "subprocess",
        "environment": {"python": "3.14"},
        "tests": list(TESTS),
        "amendments": [],
        "assumptions": ["Cash flows are certain given the inputs."],
        "ambiguities": [],
        "limitations": list(LIMITATIONS),
        "artifacts": [["npv", ["npv", "annual", "entity", "base"],
                       "npv = sum(cf_t / (1 + rate) ** t)"]],
        "honesty": dict(HONESTY),
        "reperform": make_reperform(),
    }


def make_session(appendix):
    """A session document shaped like `session.to_dict()`."""
    return {
        "id": "sess123456789",
        "status": "delivered",
        "work_plan": {
            "objective": "Should we invest?",
            "tier": "T1",
            "inputs": {"cashflows": {"value": ["100", "-50"], "provenance": "user"}},
        },
        "account_mapping": None,
        "spec": {
            "objective": "Should we invest?",
            "method": "npv",
            "hash": "sha256:spec-abc",
            "inputs": {
                "cashflows": {"value": ["100", "-50"], "provenance": "user"},
                "rate": {"value": "0.10", "provenance": "user"},
            },
            "model_assistance": [],
        },
        "stage_states": {"intake": "done", "execution": "done"},
        "events": [
            {"stage": "verification", "status": "pass", "failed": [], "amendments": 0, "sandboxed": True},
            {"stage": "delivery", "status": "delivered"},
        ],
        "delivery": {
            "status": "delivered",
            "tier": "T1",
            "report": REPORT,
            "blocked_reason": "",
            "appendix": appendix,
        },
    }


def make_bundle(**overrides):
    """A case bundle in the shape the product layer stores."""
    appendix = make_appendix()
    bundle = {
        "title": "Should we invest?",
        "method": "npv",
        "tier": "T1",
        "spec_hash": "sha256:spec-abc",
        "outputs_hash": "sha256:out-def",
        "session": make_session(appendix),
        "delivery": {"report": REPORT, "appendix": appendix},
        "reperform": appendix["reperform"],
    }
    bundle.update(overrides)
    return bundle
