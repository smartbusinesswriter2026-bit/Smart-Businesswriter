p = "src/bp/product/statements.py"
lines = open(p, encoding="utf-8").read().splitlines()
# Find the classify function
for i, l in enumerate(lines):
    if l.strip() == 'def classify(text):':
        # Insert after the docstring (which is the next line)
        insert_at = i + 2  # after def and docstring
        new_lines = [
            '    # A trial balance carries Dr/Cr markers.  If the text has them, it is a trial balance',
            '    # regardless of what the cue patterns say (account names like "Depreciation expense"',
            '    # can match adjustment cues).',
            '    import re as _re',
            '    if _re.search(r"\\d[\\d,]*(?:\\.\\d+)?\\s*(?:Dr|Cr)\\.?(?=\\s|$|[;,.])", text, _re.I):',
            '        return "trial_balance", "Dr/Cr markers", text[:60]',
        ]
        lines = lines[:insert_at] + new_lines + lines[insert_at:]
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("patched at line", insert_at + 1)
        break
else:
    print("classify not found")
