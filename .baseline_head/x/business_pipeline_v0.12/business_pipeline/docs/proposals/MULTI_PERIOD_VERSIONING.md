# Multi-period comparatives and case versioning — proposal

**Status: PROPOSAL for the owner (computation owner, 2026-10-21). Not approved, not planned as a commitment.** It follows `docs/PRODUCT_BACKEND_PLAN.md` Phase 3 item 1 and decides *how* to deliver "compare this period with last period" and "keep an audit trail of versions". Only the owner picks A or B.

## The problem

Today one session = one frozen spec = one delivery for one period. Real use needs:

1. **Comparatives**: the same method on the same basis for several periods, shown side by side.
2. **Versioning**: the same case re-run later (new inputs, corrected data, upgraded method version) with an audit trail of what changed.

Both are presentation/comparison problems *on top of* verified deliveries, not new computations. Neither may produce a new number: every compared value must be a value that was already delivered by the frozen core for some period/version.

## Option A — product layer, no unfreeze (recommended first)

- Run each period as its **own session** exactly as today (frozen core unchanged), and store each delivery as a **case version** in the local case store (product layer): same case id, version number, immutability, `spec_hash`, `outputs_hash`, `method` id+version, `created_at`.
- A comparison renderer (product layer) loads two or more stored bundles and lays them out side by side: same metric, unit and period rows, values copied **verbatim** from each bundle.
- **Declared comparability rules** (must be explicit in the output): the methods must have the same id, the metrics must share unit and period basis, and the comparison must state which specification fields differ (inputs, thresholds, method version, currency, period). Missing periods/versions render as "not computed for this period" and are never interpolated or filled.
- Version diff shows: spec hash changed (yes/no and the differing input names), method version changed, outputs changed per artifact with the **stored** values, checks passed/failed, and the timestamps. No recomputation of any kind.
- Audit story: each period/version is an independently re-performable frozen bundle; the comparison document carries the list of bundles (ids + hashes) it was built from.

**Acceptance (if A):** case-version storage (immutability, monotonic versions, hash linkage); comparison refuses different methods or incompatible metric bases with a reason; missing periods shown as not computed; every displayed number byte-identical to its stored bundle; deterministic ordering and layout; no arithmetic in the product layer; tests for all of the above.

**Cost/risk:** product-layer only (design owner, one slice); no core change, no re-performance impact; the "single bundle" property is lost (a comparison cites N bundles instead of one).

## Option B — core multi-period delivery, needs an unfreeze (B-079)

- Extend the frozen request/spec with a declared period list; the orchestrator runs the same frozen spec per period and emits one delivery with per-period artifacts, a deterministic diff against a declared base period, and one re-performance bundle covering all periods.
- **What would have to change:** `spec.py` (period set), `orchestrator.py` (loop + primary artifact per period), `artifacts.py` (period dimension), `delivery`/appendix and `reperform.py` format, plus goldens and the frozen contract fixture; the docs-state and frozen-contract guards must be updated in the same commit. This is a genuine unfreeze and needs the owner's approval under B-079.
- **Pros:** one audit bundle, one hash, one re-performance artefact; comparisons become part of the frozen delivery rather than a product document.
- **Cons:** larger surface, re-performance format change, every existing test/golden touched; it also fixes the comparison rules inside the core, which is less flexible than a product renderer.

## Recommendation

**Option A first.** It delivers the visible feature (period comparison, version history) with zero risk to the frozen contract, and every number remains a stored frozen output. Option B can follow if the audit requirement becomes "one bundle must contain every period" — that is a decision about audit packaging, not about correctness, so it can wait until the owner has seen A working. If B is chosen instead, it needs a B-decision with the unfreeze scope above and a migration plan for the existing `bp-reperform/1` format.

## What the owner is asked

1. **A or B?** (Recommended: A.)
2. For A: how many periods are typical (2-3, a year?), and does a comparison need to survive as a saved document or is on-screen comparison enough?
3. Is the audit requirement satisfied by "a comparison cites the N frozen bundles with their hashes", or must one bundle contain all periods (that is what B buys)?

## OPEN

- Whether comparatives of *different* methods (e.g. ratio analysis 2025 vs DCF 2025) are ever meaningful — assumed out of scope: comparison is same-method, same-basis only.
- Restatement/prior-period adjustment rules (an accounting convention) are **not** covered here; a restated period is a new version with a declared reason, not an automatic adjustment.
- Retention/version pruning policy is deferred with the case-store policy (D2 already accepted, but pruning rules are not specified).
