# DECISIONS — People & Organization Strategy & Design Worksheets

## 2026-11-02 — Project initialized (from scratch)

### D-01: Subject scope
Subject = **People and Organization**. Shelf = **Strategy and Design**.
Range = organizational theorists **Lewin → Mintzberg** inclusive.

### D-02: Theorist selection
Three worksheets authored:
- **Lewin** — Force Field Analysis, 3-Step Change Model (Unfreeze → Change → Refreeze)
- **Galbraith** — Star Model of Organizational Design, Information Processing
- **Mintzberg** — Five Organizational Configurations (Simple Structure, Machine Bureaucracy, Professional Bureaucracy, Divisionalized Form, Adhocracy)

No intermediate theorist worksheets were created because no worksheets existed anywhere in the Lewin→Mintzberg range (verified empirically — empty subject shelf).

### D-03: Before briefing + CHG mapping
Each worksheet carries exactly one `before` briefing. CHG items assigned:
- CHG-03/04/05/06/07/08/13 → strategy_design chain (one per worksheet transition + synthesis)
- CHG-02/09/10 → People shelf consistency
- CHG-15 → wiring onto People strategy_design tile

### D-04: Guard test invariant
Every People worksheet MUST carry a `before` briefing. Enforced by `tests/guard-test.mjs`.

### D-05: Wiring approach
CHG-15 is wired onto the People strategy_design tile via the CATALOGUE slice. Reachability + drift confirmed by `wiring/chg-15-probe.mjs`.
