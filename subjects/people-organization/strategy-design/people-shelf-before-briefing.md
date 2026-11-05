# Before Briefing: People Shelf Consistency

**Subject:** People and Organization  
**Shelf:** Strategy and Design  
**Scope:** All People worksheets (Lewin, Galbraith, Mintzberg)  
**CHG references:** CHG-02, CHG-09, CHG-10 (People shelf consistency)  
**Purpose:** Ensure every People worksheet on the Strategy and Design shelf meets consistency standards. Read this before any People worksheet.

---

## Why this briefing exists

CHG-02, CHG-09, and CHG-10 require that every worksheet on the People shelf is consistent: same structure, same metadata, same self-assessment format, same reference style, and every worksheet carries a `before` briefing. This briefing is the consistency gate.

## CHG-02 — Shelf consistency: structural standard

Every People worksheet must have:

| Element | Required? | Where verified |
|---------|-----------|----------------|
| Worksheet ID (PPL-STR-XXX-###) | Yes | Header block |
| Subject + Shelf declaration | Yes | Header block |
| Theorist name + framework | Yes | Header block |
| Before briefing referenced | Yes | Header block |
| Overview section | Yes | Section 1 |
| Learning objectives table | Yes | Section 2 |
| Core exercise sections | Yes | Sections 3–5 |
| Self-assessment checklist | Yes | Penultimate section |
| References | Yes | Final section |

## CHG-09 — Shelf consistency: before-briefing presence

**Guard rule:** No People worksheet may be used without its paired `before-briefing.md` in the same directory. This is enforced by `tests/guard-test.mjs`.

## CHG-10 — Shelf consistency: cross-worksheet alignment

All People worksheets on this shelf must:

- Use identical front-matter field names
- Use identical section numbering (1 = Overview, 2 = Objectives, ...)
- Use identical self-assessment checkbox format (`- [ ]`)
- Reference the same subject shelf ("People and Organization → Strategy and Design")

## Consistency checklist (run before any worksheet)

- [ ] Worksheet ID follows PPL-STR-XXX-### pattern
- [ ] `before-briefing.md` exists in same directory
- [ ] Header block matches all other People worksheets
- [ ] Section structure matches all other People worksheets
- [ ] Self-assessment uses `- [ ]` checkboxes
- [ ] References section present
- [ ] CHG references listed in header

---

**End of People shelf consistency briefing.** Apply to every People worksheet on this shelf.