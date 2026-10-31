"""Append the B-165 decision row, keeping the file's LF endings and its table intact."""
path = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\docs\DECISIONS.md"

row = ("| B-165 | PROVISIONAL (owner instruction, 2026-10-29) | "
       "**The collapsed rail is the strip plus a column for the subject list's scrollbar.** The owner "
       "asked for the collapsed rail's width to be adjusted so the icons can be seen in full. The "
       "subject list scrolls inside the rail and a vertical scrollbar takes the scrollport's right "
       "edge, so with the strip alone (45 px) the scrollport ended at x = 30 while every glyph sits at "
       "x = 18.5 -> 37.5 - under the scrollbar's column and cut in half. The convention is now "
       "`--rail-sb:16px` and `--rail-w-collapsed:calc(var(--rail-w) + var(--rail-sb))`, applied by "
       "`body:not(.rail-open) .rail{width:var(--rail-w-collapsed)}`: the collapsed rail is 61 px in the "
       "wide layout and 60 px in the narrow one. The green strip keeps its own width (`.railaccent` is "
       "still `--rail-w`), so the open rail is untouched and the new column is the white one the labels "
       "start in. The icons do not move - `--rail-ic-pad` is unchanged and the glyph is still at "
       "18.5 -> 37.5 - and the collapsed toggle hugs the strip with its chevron walked back onto the "
       "icon column. `scripts/ui_smoke.py` carries the markers so the column cannot be silently "
       "dropped. Presentation only: no behaviour, number, claim, endpoint or frozen-core change. | "
       "A scrollbar eats the scrollport's right edge, so the icon column needs a column of its own "
       "rather than a wider strip: widening the strip alone would have moved the icons further under "
       "the scrollbar, not clear of it. |")

with open(path, "r", encoding="utf-8", newline="") as handle:
    text = handle.read().replace("\r\n", "\n")

if "| B-165 |" in text:
    print("B-165 already present; nothing appended")
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
print("last row starts:", lines[-1][:40])
print("cells in last row:", len(lines[-1].split("|")) - 2)
