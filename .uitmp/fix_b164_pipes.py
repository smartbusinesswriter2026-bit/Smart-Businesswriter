"""Keep the decision table intact: a pipe inside a cell would split it."""
path = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\DECISIONS.md"

with open(path, "r", encoding="utf-8", newline="") as handle:
    text = handle.read()

if "`<br>`" in text:
    text = text.replace("`<br>`", "the line break")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print("reworded the <br> mention")
else:
    print("no <br> in the file")

lines = text.replace("\r\n", "\n").strip().split("\n")
for line in lines:
    if line.startswith("| B-16"):
        print(line.split("|")[1].strip(), "-> cells:", len(line.split("|")) - 2)
