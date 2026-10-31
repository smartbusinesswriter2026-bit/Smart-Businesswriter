"""Diagnose why one block in each framework loses its source.

Reuses each test module's own mock so the result matches what the suite sees.
"""

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))

import bp.product.completion as completion  # noqa: E402
import bp.product.framework_profiles as fp  # noqa: E402
import bp.product.retrieval as retrieval  # noqa: E402

MODULES = [
    ("template_vrio", "test_vrio_completion"),
    ("template_lewin", "test_lewin_completion"),
    ("template_pdsa", "test_pdsa_completion"),
    ("template_theory_of_change", "test_theory_of_change_completion"),
]


def main():
    for template, modname in MODULES:
        mod = __import__(modname)
        profile = fp.PROFILES[template]
        brief = getattr(mod, "BRIEF", None)
        industry = getattr(mod, "INDUSTRY", None)
        print("=" * 78)
        print("%s   %s" % (template, profile.get("label")))
        with mock.patch("bp.product.sources.search_academic", side_effect=mod.academic), \
             mock.patch("bp.product.sources.search_web", side_effect=mod.web):
            try:
                result = completion.complete(template, brief, industry=industry)
            except Exception as error:
                print("  complete() raised: %s: %s" % (type(error).__name__, error))
                continue
        for block, prof_block in zip(result["blocks"], profile["blocks"]):
            items = block.get("items") or []
            prov = ",".join(i.get("provenance", "?") for i in items)
            print("  %-22s items=%d [%s]" % (block.get("key"), len(items), prov))
            if not items or any(i.get("provenance") == "background" for i in items):
                print("      cues  : %r" % prof_block.get("cues"))
                print("      query : %r" % (prof_block.get("queries") or [None])[0])
                # What does the candidate title actually tokenise to?
                cue_words = {w for w in (prof_block.get("cues") or "").split() if w}
                query = (prof_block.get("queries") or [""])[0]
                title = ("Grocery retail " + query[:70]).lower()
                raw = set(retrieval.re.findall(r"[a-z][a-z0-9'-]+", title))
                parts = set()
                for w in raw:
                    if "-" in w:
                        parts.update(x for x in w.split("-") if x)
                print("      title_tokens : %s" % sorted(raw))
                print("      title_parts  : %s" % sorted(parts))
                print("      cue_words    : %s" % sorted(cue_words))
                print("      hits(raw)    : %s" % sorted(cue_words & raw))
                print("      hits(split)  : %s" % sorted(cue_words & (raw | parts)))


if __name__ == "__main__":
    main()
