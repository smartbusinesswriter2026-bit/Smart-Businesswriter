"""Remove the duplicated scaffold document from the top of web/index.html.

Commit 977c1cc pasted a scaffold <!doctype html> ... <!-- Content goes here -->
block in front of the real document.  The browser then parsed the real
<head> as body content, so the four icon links never became the document
head and the favicon was lost.
"""

import io
import os

PAGE = os.path.join(
    r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline\web",
    "index.html",
)

data = io.open(PAGE, "rb").read()

marker = b"<!doctype html>"
first = data.index(marker)
second = data.index(marker, first + 1)
scaffold = data[:second]

print("scaffold bytes: %d" % len(scaffold))
print(repr(scaffold.decode("utf-8")))

# The scaffold must be the empty placeholder document, not real content.
assert b"<!-- Content goes here -->" in scaffold, "not the scaffold block"
assert b"<script" not in scaffold, "scaffold contains a script"
assert b"<style" not in scaffold, "scaffold contains a style block"
assert data.count(marker) == 2, "expected exactly two doctypes"
assert scaffold.count(b"<html") == 1 and scaffold.count(b"</html>") == 1

io.open(PAGE, "wb").write(data[second:])

after = io.open(PAGE, "rb").read()
print("doctype count now: %d" % after.count(marker))
print("head count now: %d" % after.count(b"<head>"))
print("icon links now: %d" % (
    after.count(b'rel="icon"') + after.count(b'rel="apple-touch-icon"')))
print("bytes: %d -> %d" % (len(data), len(after)))
