"""An independent verifier for the repair loop.

A replay that passes proves the solver could reproduce an answer; it does not
prove the answer is right.  When the same model generates and judges, a wrong
answer can pass its own check (the homogeneous-loop failure MASS describes).

This module splits the roles for 2-3 calls: the solver answers, this verifier —
a **different model** that sees only the problem and the answer — judges.  Tiers
run in cost order (free, cheap, last resort) and the loop stops when two answers
agree.
"""

#: The verifier ladder, deliberately different models from the solver.
VERIFIER_MODELS = ("beam-free", "minimax-flash", "deepseek-v4-pro")


def verifier_models():
    """The configured tier models, in cost order, skipping empty entries."""
    import os
    return tuple(model for model in (
        os.environ.get("BP_VERIFY_MODEL_TIER1", VERIFIER_MODELS[0]),
        os.environ.get("BP_VERIFY_MODEL_TIER2", VERIFIER_MODELS[1]),
        os.environ.get("BP_VERIFY_MODEL_TIER3", VERIFIER_MODELS[2]),
    ) if model)


def result_summary(result):
    """What the verifier sees: the answer, never the solver's reasoning."""
    computed = (result or {}).get("computation") or {}
    if computed:
        return "; ".join("%s = %s" % (str(name).replace("_", " "), value)
                         for name, value in list(computed.items())[:24])
    return str((result or {}).get("answer") or (result or {}).get("status") or "")[:1500]


def ask(model, problem, summary):
    """One verdict from one model: True, False, or None when it cannot answer."""
    from .. import llm
    system = ("You are an independent verifier. You see only the problem and the answer. "
              "Do not re-solve it and do not trust the answer because it is stated. "
              "Decide whether the answer is a correct and complete response to the problem. "
              "Reply with one word (PASS or FAIL), then a short reason.")
    user = ("Problem:\n" + str(problem)[:2000] +
            "\n\nAnswer (the computed result):\n" + str(summary)[:2000])
    try:
        provider = llm.OpenCodeProvider(model)
        text = provider.complete(system, user, 200)
    except Exception:
        return None
    words = str(text or "").strip().lower().split()
    if not words:
        return None
    if words[0].strip(".,:;") == "pass":
        return True
    if words[0].strip(".,:;") == "fail":
        return False
    return None


def verify_fix(problem, result):
    """Ask the ladder; the majority of the answers that came back wins.

    `ok is None` means no verifier answered: the solver's answer stands, but it
    is an unverified instance, not a durable fix.
    """
    if not problem:
        return {"ok": None, "model": "", "reason": "no problem to verify"}
    summary = result_summary(result)
    votes = []
    for model in verifier_models():
        verdict = ask(model, problem, summary)
        if verdict is None:
            continue
        votes.append((model, verdict))
        if len(votes) >= 2 and votes[0][1] == votes[1][1]:
            break
    if not votes:
        return {"ok": None, "model": "", "reason": "no verifier model answered"}
    passes = sum(1 for _model, verdict in votes if verdict)
    ok = passes * 2 > len(votes)
    return {"ok": ok,
            "model": ",".join(model for model, _verdict in votes),
            "reason": ("%d of %d verifier(s) said the answer is correct" % (passes, len(votes))
                       if ok else
                       "%d of %d verifier(s) rejected the answer" % (len(votes) - passes, len(votes)))}
