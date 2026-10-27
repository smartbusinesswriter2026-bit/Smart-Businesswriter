"""Re-performance (manual P9): rerun a delivered bundle in a fresh sandbox and compare outputs and environment."""
import json, sys
from decimal import Decimal as D
from .sandbox import SubprocessSandbox, SandboxError

def _cmp(a: str, b: str):
    if a == b: return "exact"
    try:
        x, y = D(a), D(b)
        return "within_tolerance" if abs(x - y) <= D("1e-12") * max(D(1), abs(y)) else "mismatch"
    except Exception: return "mismatch"

def reperform(bundle: dict, sandbox=None) -> dict:
    sb = sandbox or SubprocessSandbox()
    if bundle.get("template"):
        from .artifacts import sha
        try: out, meta = sb.template(bundle["method"]["id"], bundle["inputs"])
        except Exception as e: return {"verified": False, "reason": f"could not re-run: {e}", "differences": []}
        diffs = []
        if sha(out["analysis"]) != bundle["analysis_hash"]: diffs.append("analysis differs from the delivered structure")
        if any(not ok for _, ok in out["results"]): diffs.append("verification checks failed on re-run")
        return {"verified": not diffs, "all_exact": not diffs, "environment_match": meta["env_hash"] == bundle["env_hash"], "differences": diffs, "outputs": {}}
    try: results, outputs, meta = sb.verify_execute(bundle["method"]["id"], bundle["inputs"])
    except Exception as e: return {"verified": False, "reason": f"could not re-run: {e}", "differences": []}
    diffs, status = [], {}
    if outputs is None: return {"verified": False, "reason": "verification checks failed on re-run", "differences": [n for n, ok in results if not ok]}
    for k, v in bundle["outputs"].items():
        st = "missing" if k not in outputs else _cmp(v, str(outputs[k])); status[k] = st
        if st in ("mismatch", "missing"): diffs.append(f"{k}: delivered {v}, re-run {outputs.get(k)}")
    extra = [k for k in outputs if k not in bundle["outputs"]]
    if extra: diffs.append(f"re-run produced extra outputs: {extra}")
    if bundle.get("flip") is not None:
        lo, hi = bundle["sensitivity"]["rate"]; f = sb.flip(bundle["method"]["id"], bundle["inputs"], lo, hi)
        st = _cmp(bundle["flip"], str(f)) if f is not None else "mismatch"; status["flip"] = st
        if st == "mismatch": diffs.append(f"flip: delivered {bundle['flip']}, re-run {f}")
    env_diff = sorted(k for k in set(bundle["fingerprint"]) | set(meta["fingerprint"]) if bundle["fingerprint"].get(k) != meta["fingerprint"].get(k))
    # The rendered appendix (statements, T-accounts, journal) is what the reader sees, so it is verified
    # too when the bundle carries its hash. A mismatch here means the document changed while the scalars did
    # not - exactly the drift a scalar-only check cannot see.
    statements = None
    if bundle.get("statements_hash") is not None:
        from .artifacts import sha
        rerun_extra = meta.get("appendix_extra")
        if rerun_extra is None:
            statements = "missing"
            diffs.append("statements: the re-run produced no appendix to compare")
        elif sha(rerun_extra) != bundle["statements_hash"]:
            statements = "mismatch"
            diffs.append("statements: the re-run appendix differs from the delivered one")
        else:
            statements = "exact"
    return {"verified": not diffs, "outputs": status, "all_exact": all(v == "exact" for v in status.values()), "environment_match": meta["env_hash"] == bundle["env_hash"],
            "statements": statements, "environment_differences": env_diff, "differences": diffs}

if __name__ == "__main__":
    b = json.load(open(sys.argv[1], encoding="utf-8")); b = b.get("reperform", b)
    r = reperform(b); print(json.dumps(r, indent=2)); sys.exit(0 if r["verified"] else 1)
