p = "src/bp/product/statements.py"
text = open(p, encoding="utf-8").read()
old = '''    try:
        kind, _cue, _sentence_text = classify(text)
    except StatementError:
        return False
    return kind == "trial_balance"
'''
new = '''    # A trial balance carries Dr/Cr markers on its lines.  If the text has them, it is a trial
    # balance regardless of what classify() says (classify can be fooled by account names like
    # "Depreciation expense" that match adjustment cues).
    import re as _re
    if _re.search(r"\\d[\\d,]*(?:\\.\\d+)?\\s*(?:Dr|Cr)\\.?(?=\\s|$|[;,.])", text, _re.I):
        return True
    try:
        kind, _cue, _sentence_text = classify(text)
    except StatementError:
        return False
    return kind == "trial_balance"
'''
assert old in text, "old not found"
text = text.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(text)
print("patched")
