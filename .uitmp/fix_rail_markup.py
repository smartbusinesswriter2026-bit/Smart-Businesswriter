"""One-off: align the static rail items with the live rail.

- drop the native `title` attributes (the rail tooltip now carries the text)
- use the subject's real name, the same one the live API returns
Each replacement must apply exactly once; the script fails loudly otherwise.
"""
import io
import sys

PATH = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web\index.html"

PAIRS = [
    (' style="--i:#FFFFFF" title="Home: the case shelf, the chat and a new analysis">',
     ' style="--i:#FFFFFF">'),
    (' style="--i:#4D9BFF" title="Accounting">', ' style="--i:#4D9BFF">'),
    (' style="--i:#3DDC84" title="Finance">', ' style="--i:#3DDC84">'),
    (' style="--i:#2BD9D9" title="Economics">', ' style="--i:#2BD9D9">'),
    (' style="--i:#B388FF" title="Management &amp; strategy">', ' style="--i:#B388FF">'),
    (' style="--i:#FFC542" title="Entrepreneurship">', ' style="--i:#FFC542">'),
    (' style="--i:#7AA7FF" title="Operations management">', ' style="--i:#7AA7FF">'),
    (' style="--i:#38E0C8" title="Supply chain &amp; logistics">', ' style="--i:#38E0C8">'),
    (' style="--i:#FF7A6B" title="Marketing &amp; customers">', ' style="--i:#FF7A6B">'),
    (' style="--i:#C3CEDA" title="People &amp; organisation">', ' style="--i:#C3CEDA">'),
    (' style="--i:#8E9BFF" title="Research &amp; statistics">', ' style="--i:#8E9BFF">'),
    ('<span class="railtext">Management</span>', '<span class="railtext">Management &amp; strategy</span>'),
    ('<span class="railtext">Operations</span>', '<span class="railtext">Operations management</span>'),
    ('<span class="railtext">Supply chain</span>', '<span class="railtext">Supply chain &amp; logistics</span>'),
    ('<span class="railtext">Marketing</span>', '<span class="railtext">Marketing &amp; customers</span>'),
    ('<span class="railtext">People</span>', '<span class="railtext">People &amp; organisation</span>'),
    ('<span class="railtext">Research</span>', '<span class="railtext">Research &amp; statistics</span>'),
]

with io.open(PATH, encoding="utf-8", newline="") as fh:
    text = fh.read()

for old, new in PAIRS:
    n = text.count(old)
    if n != 1:
        print("FAIL %d matches for %r" % (n, old))
        sys.exit(1)
    text = text.replace(old, new)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(text)
print("ok: %d replacements" % len(PAIRS))
