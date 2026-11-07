"""Normalise the documentation files to CRLF, keeping their content.

The build 1.102 documentation update was applied by a script whose inserted text
carried LF line endings; these files are CRLF throughout, and a mixed file is a
file a diff reads badly.  This restores the one form the tree uses.
"""
import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(BASE, "docs")
NAMES = ("CHANGELOG.md", "WORKLOG.md", "DECISIONS.md", "HOME.md", "HANDOFF.md", "CONTRIBUTORS.md")

for name in NAMES:
    path = os.path.join(DOCS, name)
    with io.open(path, encoding="utf-8", newline="") as stream:
        text = stream.read()
    fixed = text.replace("\r\n", "\n").replace("\n", "\r\n")
    if fixed != text:
        with io.open(path, "w", encoding="utf-8", newline="") as stream:
            stream.write(fixed)
        print("normalised " + name)
    else:
        print("already CRLF: " + name)
