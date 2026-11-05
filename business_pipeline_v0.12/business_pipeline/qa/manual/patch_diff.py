p = "src/bp/product/statements.py"
text = open(p).read()

# 1. Init tier1_gaps
old_init = "    reading, rows, source, rejected, same_model = None, [], \"parser\", [], False\n    parser_error = None\n"
new_init = ("    reading, rows, source, rejected, same_model = None, [], \"parser\", [], False\n"
            "    parser_error = None\n"
            "    tier1_gaps = []\n")
assert old_init in text, "init"
text = text.replace(old_init, new_init, 1)

# 2. >3 missing case
old_fail2 = ("            parser_error = StatementError(\"deterministic reader missed most of the problem\")\n"
             "            reading = None\n            rows = []\n")
new_fail2 = ("            if isinstance(reading, dict):\n"
             "                tier1_gaps = (reading.get(\"missing\") or []) + (reading.get(\"unplaceable\") or [])\n"
             "            parser_error = StatementError(\"deterministic reader missed most of the problem\")\n"
             "            reading = None\n            rows = []\n")
assert old_fail2 in text, "fail2"
text = text.replace(old_fail2, new_fail2, 1)

# 3. StatementRefused and StatementError
old_fail3 = ("    except StatementRefused as error:\n"
             "        parser_error = error\n"
             "        reading = None\n"
             "    except StatementError as error:\n"
             "        parser_error = error\n"
             "        reading = None\n")
new_fail3 = ("    except StatementRefused as error:\n"
             "        if isinstance(reading, dict):\n"
             "            tier1_gaps = (reading.get(\"missing\") or []) + (reading.get(\"unplaceable\") or [])\n"
             "        parser_error = error\n"
             "        reading = None\n"
             "    except StatementError as error:\n"
             "        if isinstance(reading, dict):\n"
             "            tier1_gaps = (reading.get(\"missing\") or []) + (reading.get(\"unplaceable\") or [])\n"
             "        parser_error = error\n"
             "        reading = None\n")
assert old_fail3 in text, "fail3"
text = text.replace(old_fail3, new_fail3, 1)

# 4. Pass tier1_gaps to _solve_narrative
old_call = "                    return _solve_narrative(attempt_text, currency=currency, framework=framework,\n                                            ratios=ratios, statements=requested)\n"
new_call = ("                    return _solve_narrative(attempt_text, currency=currency, framework=framework,\n"
            "                                            ratios=ratios, statements=requested,\n"
            "                                            tier1_gaps=tier1_gaps)\n")
assert old_call in text, "call"
text = text.replace(old_call, new_call, 1)

# 5. Signature
old_sig = "def _solve_narrative(text, currency=None, framework=None, ratios=None, statements=None):"
new_sig = "def _solve_narrative(text, currency=None, framework=None, ratios=None, statements=None, tier1_gaps=None):"
assert old_sig in text, "sig"
text = text.replace(old_sig, new_sig, 1)

# 6. Store tier1_gaps in record (last occurrence)
old_ratios = '        "ratios": None,\n    }\n    return verify.freeze(record)\n'
idx = text.rfind(old_ratios)
assert idx != -1, "ratios"
new_ratios = ('        "ratios": None,\n'
              '        "tier1_gaps": tier1_gaps or [],\n'
              '    }\n    return verify.freeze(record)\n')
text = text[:idx] + new_ratios + text[idx + len(old_ratios):]

open(p, "w").write(text)
print("done")
