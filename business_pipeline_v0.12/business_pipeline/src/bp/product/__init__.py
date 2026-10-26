"""Product layer for the frozen core (B-080, design owner).

This package is **additive**: it sits on top of the frozen deterministic
backend (`docs/BACKEND_CONTRACT.md`) and never modifies it.  Rules that bind
every module here:

* standard library only - no third-party import, no runtime dependency;
* the frozen core is never imported: the product layer works on the JSON
  documents the core already produces (`session.to_dict()`, the delivery
  `report` + `appendix`, the `reperform` bundle) and treats them as opaque;
* no business number is computed, rounded, re-derived or adjusted here.  The
  product layer stores, lists, copies and renders what was recorded.  Where a
  field was not recorded it says "not recorded" - it never invents one;
* every file the product layer writes is new; no frozen module, test, fixture
  or factual document is edited to make a product feature work.

Sub-modules:

* `cases` - the local durable case store (one JSON bundle per case);
* `api` - additive route dispatch for the case store (no server edit);
* `subjects` - the subject index and the Calculator's launcher groups;
* `disclosure` - the AI-use disclosure rendered from the recorded metadata;
* `export` - a self-contained HTML export of a stored bundle.
"""

PRODUCT_LAYER = "bp-product/1"

__all__ = ["PRODUCT_LAYER"]
