src = open("src/bp/statement_extract.py", encoding="utf-8").read()
old = 'raise ExtractionError("the model returned nothing")'
new = 'raise ExtractionError("the model did not return a readable journal. Try restating as a trial balance (one account per line) or as labelled figures (Data: ... Required: ...).")'
assert old in src, "old1 not found"
src = src.replace(old, new, 1)

old2 = 'raise ExtractionError("the model did not return JSON")'
new2 = 'raise ExtractionError("the model response was not in the expected format. Try restating as a trial balance (one account per line) or as labelled figures (Data: ... Required: ...).")'
assert old2 in src, "old2 not found"
src = src.replace(old2, new2, 1)

open("src/bp/statement_extract.py", "w", encoding="utf-8").write(src)
print("patched")
