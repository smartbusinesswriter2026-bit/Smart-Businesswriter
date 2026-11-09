"""Scaffold a capability the pipeline does not have yet.

The growth loop is **semi-autonomous**: this module writes a reviewable skeleton,
never a working method.  A human fills in the logic, runs the suite, and commits
it; the repair loop then protects the new case.

Every file is marked PROVISIONAL and none is imported by the running system.
The research order is local-first:

1. the error database (`error_db.growth_brief`) — have we paid for this mistake?
2. the subject's own methods, capabilities and presets;
3. the vetted source finder (curated sites), then the wider web.
"""
import json
import os
from pathlib import Path

PROVISIONAL = "PROVISIONAL - generated scaffold, not wired into the running system"


def _root(root=None):
    override = os.environ.get("BP_SCAFFOLD_ROOT")
    if root:
        return Path(root)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "qa" / "scaffolds"


def _safe(text):
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in str(text or "")).strip("-")


def _method_stub(subject, tile, instruction):
    return '''"""PROVISIONAL method stub for {subject}/{tile}.

{provisional}

Fill in `impl`.  It must be a pure function of its declared inputs: no model
call, no network, no invented figure.  Add it to the frozen core only after the
suite passes and the owner reviews it.
"""
from decimal import Decimal as D


def {func}_impl(inputs):
    """Compute the tile from the declared figures."""
    raise NotImplementedError("write the method logic for {subject}/{tile}")


def {func}_profile(inputs):
    """Validate the declared figures; return a list of problems (empty is valid)."""
    return []


def {func}_tests(inputs, impl):
    """The method's own checks: at least one identity the result must satisfy."""
    return [("the result is defined", impl(inputs) is not None)]


METHOD = {{
    "name": "{func}",
    "impl": {func}_impl,
    "profile": {func}_profile,
    "tests": {func}_tests,
    "version": "0.0.1-provisional",
    "intended_use": {instruction!r},
    "unsupported_use": "PROVISIONAL: nothing is approved yet",
}}
'''.format(subject=subject, tile=tile, func=_safe(tile).replace("-", "_") or "method",
           provisional=PROVISIONAL, instruction=str(instruction or "")[:400])


def _capability_entry(subject, tile):
    return '''# {provisional}
# Add this row to capabilities.ENTRIES only after the method is reviewed.
entry = {{
    "key": "{tile}",
    "method": "{tile}",
    "label": "{tile}",
    "slot": ["{subject}", "{tile}"],
    "cues": [r"{tile}"],
    "integration": "Framework and Declared Figures",
}}
'''.format(provisional=PROVISIONAL, subject=subject, tile=tile)


def _preset(subject, tile, instruction):
    return json.dumps({
        "format": "bp-tile-preset/1",
        "subject": subject,
        "tile": tile,
        "status": PROVISIONAL,
        "objective": str(instruction or "")[:300],
        "inputs": {},
        "note": "declare the figures the method needs; leave an input out rather than invent it",
    }, ensure_ascii=False, indent=1) + "\n"


def _test_sketch(subject, tile):
    return '''"""PROVISIONAL tests for {subject}/{tile}.

{provisional}

The human writes the real expectations.  This sketch only pins the shape so the
suite cannot be green by construction with no assertions.
"""
import unittest


class {cls}Test(unittest.TestCase):
    def test_the_method_is_defined(self):
        from bp import methods
        self.assertIn("{tile}", methods.LIBRARY)

    def test_a_declared_input_round_trips(self):
        self.skipTest("write the first real case: declare figures, run, assert the result")


if __name__ == "__main__":
    unittest.main()
'''.format(subject=subject, tile=tile, provisional=PROVISIONAL,
           cls=(_safe(tile).replace("-", "_") or "Tile").title().replace("_", ""))


def _readme(subject, tile, instruction, brief):
    return """# Scaffold: {subject}/{tile}

{provisional}

## The gap

{instruction}

## What the pipeline already knows

{brief}

## Research order (local first)

1. Search the error database for this failure class (`error_db.search`).
2. Read the subject's own methods, capabilities and presets.
3. Search the vetted source finder's curated sites (docs/VETTED_SOURCES.md).
4. Only if those are thin, search the wider web through the vetted source finder.

Never copy a figure or a citation from a source; cite it, and compute from the
student's declared figures.

## Before this becomes a capability

- [ ] a human writes the method logic
- [ ] the method has at least one identity test
- [ ] the suite passes (`python -m pytest`)
- [ ] the frozen contract passes
- [ ] the capability entry and preset are reviewed
- [ ] a case is seeded and the repair loop replays it
""".format(subject=subject, tile=tile, provisional=PROVISIONAL,
           instruction=str(instruction or "")[:800], brief=brief or "(no prior lesson)")


def generate(subject, tile, instruction="", root=None):
    """Write the scaffold for one gap.  Returns {paths, subject, tile}."""
    from . import error_db
    subject = _safe(subject) or "unknown"
    tile = _safe(tile) or "newtile"
    folder = _root(root) / subject / tile
    folder.mkdir(parents=True, exist_ok=True)
    try:
        brief = error_db.growth_brief(subject, tile, instruction, limit=5)
    except Exception:
        brief = "the error database is unavailable; research this as new"
    files = {
        "method_stub.py": _method_stub(subject, tile, instruction),
        "capability_entry.py": _capability_entry(subject, tile),
        "preset.json": _preset(subject, tile, instruction),
        "test_sketch.py": _test_sketch(subject, tile),
        "README.md": _readme(subject, tile, instruction, brief),
    }
    written = []
    for name, text in files.items():
        path = folder / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(str(path))
    return {"subject": subject, "tile": tile, "folder": str(folder), "paths": written}
