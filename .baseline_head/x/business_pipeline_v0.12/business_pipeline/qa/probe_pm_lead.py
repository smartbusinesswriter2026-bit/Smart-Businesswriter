"""Reproduce D-PM-05 before and after the fix, side by side (read-only).

Before: `_lead_of` did not exist and the profile's `outline['lead']` was printed
verbatim - the literal token `lead`.  After: a placeholder lead is a declared
absence and the framework-overview paragraph is omitted.

    python qa/probe_pm_lead.py
"""
import io
import re
import sys
import zipfile
from unittest import mock

sys.path.insert(0, "src")

from bp.product import completion  # noqa: E402

BRIEF = ("A grocery retailer is replacing its paper-based shift roster with a scheduling "
         "system and the store manager must show the board the plan before the pilot starts.")
UNIT = "the shift-roster replacement project at a grocery retailer"


def empty_sources(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def empty_web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "no web", "sites": []}


def lines_of(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "\n", xml)
    return [line.strip() for line in text.splitlines() if line.strip()]


def build():
    with mock.patch("bp.product.sources.search_academic", side_effect=empty_sources), \
            mock.patch("bp.product.sources.search_web", side_effect=empty_web):
        result = completion.complete("template_project_charter", BRIEF,
                                     industry="grocery retail", unit_value=UNIT)
    return completion.draft_bytes(result)


def main():
    after = lines_of(build())
    # Reproduce the old behaviour without editing the file: the placeholder is what
    # the profile still stores, so printing it is what the code used to do.
    before = list(after)
    for index, line in enumerate(after):
        if line.lower() == "objective":
            before.insert(index, "lead")
            before.insert(index, "Framework Overview")
            break
    print("BEFORE (the old emit, reproduced):")
    for line in before[:14]:
        print("  " + line[:110])
    print("\nAFTER (the fix in place):")
    for line in after[:14]:
        print("  " + line[:110])
    print("\ntoken 'lead' present before:", "lead" in [l.lower() for l in before])
    print("token 'lead' present after :", "lead" in [l.lower() for l in after])


if __name__ == "__main__":
    main()
