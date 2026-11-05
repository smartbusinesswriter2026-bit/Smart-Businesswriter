# Append heal() function to statements.py
heal_func = '''

def heal(proposal_rule, held_out_texts, origin="self_heal"):
    """Apply a proposed RULES entry, validate against held-out set, keep or revert.

    `proposal_rule` is a tuple matching the RULES schema:
        (pattern, type, section, line, role, activity, contra)
    `held_out_texts` is a list of problem texts that must still solve after the change.

    Returns (success: bool, reason: str, passed: int, tested: int).
    """
    import os
    from . import tier1_tables as _t1
    from . import statement_library as _slib

    # Snapshot current rules for revert
    before = list(_t1.RULES)

    # Apply the proposal
    _t1.append_rule(proposal_rule)
    after = list(_t1.RULES)

    # Validate against held-out set
    tested = 0
    passed = 0
    failures = []
    for text in held_out_texts:
        tested += 1
        try:
            rec = solve(text)
            if rec.get("solved"):
                passed += 1
            else:
                failures.append(text[:60] + " -> not solved")
        except Exception as e:
            failures.append(text[:60] + " -> " + str(e)[:80])

    auto_heal = os.environ.get("BP_SELF_HEAL", "").strip() in ("1", "true", "yes")
    if passed == tested and tested > 0:
        # All held-out problems still pass — keep the change
        _slib.log_heal("rule", proposal_rule, "applied",
                       "All %d held-out problems still pass." % tested,
                       tested=tested, passed=passed)
        return True, "All %d held-out problems still pass." % tested, passed, tested
    else:
        # Regression detected — revert
        # Restore the rules list
        _t1.RULES = before
        _t1._rules_cache = before
        # Persist the reverted state
        try:
            _t1._save([list(r) for r in before], {})
        except Exception:
            pass
        reason = "Regression: %d/%d passed. %s" % (passed, tested, "; ".join(failures[:3]))
        _slib.log_heal("rule", proposal_rule, "rejected", reason,
                       tested=tested, passed=passed)
        return False, reason, passed, tested
'''

# Append to statements.py
src = open("src/bp/product/statements.py").read()
if "def heal(" not in src:
    src = src + "\n" + heal_func
    open("src/bp/product/statements.py", "w").write(src)
    print("appended heal()")
else:
    print("already present")
