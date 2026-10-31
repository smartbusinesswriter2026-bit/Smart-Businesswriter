"""Escape the pipes inside the appended decision row and normalise the line endings."""
path = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\DECISIONS.md"

with open(path, "r", encoding="utf-8", newline="") as handle:
    text = handle.read()

text = text.replace("\r\n", "\n")
if not text.endswith("\n"):
    text += "\n"

needle = "BUSINESS | ACCOUNTING | ECONOMICS | FINANCE"
if needle in text:
    text = text.replace(needle, "BUSINESS \\| ACCOUNTING \\| ECONOMICS \\| FINANCE")
    print("escaped")
else:
    print("tagline not found in the file")

with open(path, "w", encoding="utf-8", newline="") as handle:
    handle.write(text)

with open(path, "rb") as handle:
    data = handle.read()
print("CR:", data.count(b"\r"), "LF:", data.count(b"\n"))
print("last row:", data.decode("utf-8").strip().split("\n")[-1][:120])
