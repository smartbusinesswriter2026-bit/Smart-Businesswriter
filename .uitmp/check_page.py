"""Check the two assembly defects are gone from the served page."""
import io
import re

text = io.open(r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html",
               encoding="utf-8", newline="").read()

mark = re.search(r"const MARK = .{0,50}", text)
print("MARK line:", mark.group(0)[:60])
print("nested MARK statement:", "const MARK = " + chr(34) + "const MARK" in text)
print("nested img tag:", "<img src=" + chr(34) + "<img" in text)
print("hero line present:", "Every figure computed by code, never by the model." in text)
print("placeholder gone:", "To be supplied" not in text)
print("size:", len(text.encode("utf-8")), "bytes")
