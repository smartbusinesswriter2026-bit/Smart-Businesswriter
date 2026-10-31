"""Repair web/index.html: the language/router block was left inside <style>.

The block that belongs at the top of the inline script (`LOCALES` through
`const RENDERERS = {}`) had been placed inside the stylesheet, so the script
threw `ReferenceError: RENDERERS is not defined` and the page fell back to its
static run-first markup.  Move it back to just after `const PANELS = [...]`.

Also remove the three top-right pills (Pricing / My account / Sign up) that
docs/UI_BRIEF.md says are removed and that build 0.66 wrongly claimed were gone.
"""
import io
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "business_pipeline_v0.12", "business_pipeline", "web", "index.html")

with io.open(PATH, encoding="utf-8", newline="") as stream:
    text = stream.read()

start_marker = "const LOCALES = {"
end_marker = "const RENDERERS = {};"
start = text.index(start_marker)
end = text.index(end_marker, start) + len(end_marker)
# consume the newline after RENDERERS so the block moves cleanly
if text[end:end + 2] == "\r\n":
    end += 2
elif text[end:end + 1] == "\n":
    end += 1
block = text[start:end]

# 1. remove it from inside <style>
text = text[:start] + text[end:]

# 2. place it after the PANELS line, before the subjects section
anchor = 'const PANELS = ["home", "subjects", "calculator", "tool", "new", "results", "cases", "case", "data", "refs", "deliver", "accounts", "frames", "assistant", "plan", "status"];'
if anchor not in text:
    sys.exit("PANELS anchor not found")
head, tail = text.split(anchor, 1)
text = head + anchor + "\r\n\r\n" + block + tail

# 3. remove the three pills the UI brief says are gone
for line in (
    '  <span class="pill" id="pricingpill">Pricing</span>\r\n',
    '  <span class="pill" id="accountpill">My account</span>\r\n',
    '  <span class="pill" id="signupbtn">Sign up</span>\r\n',
    '<span class="pill" id="pricingpill">Pricing</span>\n',
    '<span class="pill" id="accountpill">My account</span>\n',
    '<span class="pill" id="signupbtn">Sign up</span>\n',
):
    text = text.replace(line, "")

with io.open(PATH, "w", encoding="utf-8", newline="") as stream:
    stream.write(text)

print("moved %d characters of script out of the stylesheet" % len(block))
print("remaining pills:", text.count("pricingpill") + text.count("accountpill") + text.count("signupbtn"))
print("style block still closes:", "</style>" in text)
