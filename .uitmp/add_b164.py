"""Append the B-164 decision row, keeping the file's LF endings and its table intact."""
path = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\DECISIONS.md"

row = ("| B-164 | PROVISIONAL (owner instruction, 2026-10-29) | "
       "**The Home slogan loses its final period.** The owner asked for one character to be removed: "
       "the lead now reads \"Your reliable business writing assistant\" with no full stop, in both the "
       "static hero markup and the `RENDERERS.home` rebuild. Nothing else moves - the claim stays in "
       "the bold 19.8 px lead, the three proofs stay in the italic 15 px line under it with their own "
       "full stops, and the `<br>` still separates them. B-094's clause \"the slogan must not be changed\" "
       "and B-162's clause \"the slogan stays\" were the owner's own guard against unasked-for edits; "
       "the owner has now asked for this edit, so both clauses are revised by this row rather than "
       "quietly broken. Copy only: no behaviour, number, claim, endpoint or frozen-core change. | "
       "The owner wants the hero's promise to read as a phrase set against its proofs, with the weight "
       "step and the line break carrying the emphasis instead of a full stop. |")

with open(path, "r", encoding="utf-8", newline="") as handle:
    text = handle.read().replace("\r\n", "\n")

if "| B-164 |" in text:
    print("B-164 already present; nothing appended")
else:
    if not text.endswith("\n"):
        text += "\n"
    text += row + "\n"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    print("appended")

with open(path, "rb") as handle:
    data = handle.read()
print("CR:", data.count(b"\r"), "LF:", data.count(b"\n"))
lines = data.decode("utf-8").strip().split("\n")
print("last row:", lines[-1][:110])
print("pipes in last row:", lines[-1].count("|"))
