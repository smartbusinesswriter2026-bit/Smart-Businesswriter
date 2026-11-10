# Scaffold: general/Test

PROVISIONAL - generated scaffold, not wired into the running system

## The gap

Test

## What the pipeline already knows

Known mistakes to avoid (from qa/errors/error_registry.jsonl):
- No prior lesson matched this subject/tile; treat it as new.
Causes still open: pipeline.parser_shape (recurring, 1 recurrence(s)); pipeline.unknown (unfixed, 0 recurrence(s))

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
