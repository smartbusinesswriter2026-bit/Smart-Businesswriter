import os
p = "src/bp/schedule_math.py"
s = open(p, encoding="utf-8").read()
# The file was written with every newline/quote/backslash escaped. Undo that.
s2 = s.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
open(p, "w", encoding="utf-8", newline="").write(s2)
print("lines:", s2.count("\n") + 1)
print("first 3:", s2.splitlines()[:3])
