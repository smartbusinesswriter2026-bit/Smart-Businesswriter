"""Trace the retrieval gate for one framework block, with the real query."""

import os
import sys
from unittest import mock

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
sys.path.insert(0, os.path.join(os.getcwd(), "tests"))

import bp.product.framework_profiles as fp  # noqa: E402
import bp.product.retrieval as retrieval  # noqa: E402
import test_theory_of_change_completion as toc_test  # noqa: E402
import test_lewin_completion as lewin_test  # noqa: E402


def trace(template, mod, industry, brief):
    profile = fp.PROFILES[template]
    gate = retrieval.gate_of(profile.get("gate"))
    print("=" * 70)
    print(template, "| gate:", {k: v for k, v in gate.items() if k != "blocked"})
    print("  sites:", profile.get("sites"), "providers:", profile.get("providers"))
    for b in profile["blocks"]:
        for q in (b.get("queries") or [])[:1]:
            query = "%s %s" % (industry, q)
            item = {
                "title": "Grocery retail " + query[:70],
                "abstract": "Evidence on the growth option named in the query. A second sentence follows it.",
                "doi": "10.1/" + str(abs(hash(query)) % 1000000),
                "database": "OpenAlex", "year": 2024,
            }
            cue_words = {w for w in retrieval.clean(b.get("cues"), 400).split() if w}
            context_set = set(retrieval.context_of(profile, b) if hasattr(retrieval, "context_of") else [])
            # emulate the engine: context = industry words
            context_set = set(retrieval.clean(industry, 200).lower().split())
            seen = retrieval.relevance(item, cue_words, context_set, gate.get("geography", "Global"))
            score = retrieval._accept(item, cue_words, context_set, gate.get("geography", "Global"), gate)
            print("  %-14s query=%r" % (b["key"], query))
            print("       cues=%r" % b.get("cues"))
            print("       seen=%s" % {k: v for k, v in seen.items()})
            print("       accepted=%s" % score)


def main():
    trace("template_theory_of_change", toc_test, toc_test.INDUSTRY, toc_test.BRIEF)
    trace("template_lewin", lewin_test, lewin_test.INDUSTRY, lewin_test.BRIEF)


if __name__ == "__main__":
    main()
