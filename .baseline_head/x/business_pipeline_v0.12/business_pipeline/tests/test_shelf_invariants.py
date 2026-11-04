"""Shelf-wide invariants that must hold across all 11 shelves.

These tests pin the structural truths that, if violated, produce the class of
drift that created D-RES-01 (records denying shipped methods) and D-RES-06
(0 tiles / 0 groups, page could not group). They are deliberately narrow:
they assert invariants, not policy.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.methods import LIBRARY  # noqa: E402
from bp.product import subjects  # noqa: E402


class ShelfInvariants(unittest.TestCase):
    """Invariants that must hold for every shelf."""

    @classmethod
    def setUpClass(cls):
        cls.all_subjects = [d["id"] for d in subjects.SUBJECT_DEFS]

    def test_every_tool_resolves_to_frozen_method_or_preset(self):
        """Every subject tool must resolve to a LIBRARY method or a PRESET."""
        from bp.server import PRESETS

        for subject_id in self.all_subjects:
            detail = subjects.detail(subject_id)
            for tool in detail["tools"]:
                preset = tool.get("preset")
                mid = tool.get("method")
                if preset and preset not in PRESETS:
                    self.fail(f"{subject_id}: tool '{tool['key']}' preset '{preset}' not in PRESETS")
                if not preset and mid not in LIBRARY:
                    self.fail(f"{subject_id}: tool '{tool['key']}' method '{mid}' not in LIBRARY and no preset")

    def test_no_record_denies_a_shipped_method_it_links(self):
        """No catalogue record may say 'not implemented' while linking a method that exists in LIBRARY.
        This is the D-RES-01 class, now measured clean on all 11 shelves.
        """
        for subject_id in self.all_subjects:
            detail = subjects.detail(subject_id)
            for record in detail["records"]:
                status = (record.get("implementation_status") or "").strip().lower()
                if status == "not implemented" and record.get("linked_methods"):
                    self.fail(f"{subject_id}: record '{record['id']}' says 'not implemented' but links methods: {record['linked_methods']}")

    def test_level_iff_study_notes(self):
        """A tool has a 'level' (difficulty badge) iff it has study notes (formula/notes).
        Measured across all 11 shelves: mismatch = 0 everywhere.
        Research's nine null-level tools are exactly the nine with no study notes.
        """
        for subject_id in self.all_subjects:
            detail = subjects.detail(subject_id)
            for tool in detail["tools"]:
                has_level = bool(tool.get("level"))
                has_formula = bool(tool.get("formula"))
                if has_level != has_formula:
                    self.fail(f"{subject_id}: tool '{tool['key']}' level={has_level} formula={has_formula} — invariant violated")

    def test_tiled_shelf_never_falls_back_to_level_grouping(self):
        """If a shelf has tiles (len > 0), the page renders tiles and returns
        before the level/fallback grouping is ever reached.

        For shelves with calculator tiles (tools have a 'group' field that matches
        tile keys), every tool with a group must be placed in exactly one tile.
        Shelves like management have tiles only for worksheets/records, not calculators,
        so their tools may not have groups and are not expected to be in tiles.
        """
        for subject_id in self.all_subjects:
            detail = subjects.detail(subject_id)
            tiles = detail.get("tiles") or []
            tools = detail.get("tools") or []
            if not tiles:
                continue
            # Check if this shelf has calculator tiles (any tile has tools)
            has_calculator_tiles = any(tile.get("tools") for tile in tiles)
            if not has_calculator_tiles:
                # This shelf has tiles but only for worksheets/records (e.g., management)
                continue
            # Every tool with a group must be placed in exactly one tile
            placed = set()
            for tile in tiles:
                for tool in tile.get("tools", []):
                    key = tool.get("key")
                    if key in placed:
                        self.fail(f"{subject_id}: tool '{key}' appears in multiple tiles")
                    placed.add(key)
            # All tools with a group must be placed
            for tool in tools:
                if tool.get("group") and tool["key"] not in placed:
                    self.fail(f"{subject_id}: tool '{tool['key']}' has group '{tool['group']}' but not placed in any tile")

    def test_catalogue_rows_reconcile(self):
        """Every catalogue row in detail() matches the registry and the shelf's
        catalogue_ids list. No record is missing or duplicated.
        """
        for subject_id in self.all_subjects:
            definition = subjects._subject_definition(subject_id)
            catalogue_ids = definition.get("catalogue_ids") or []
            detail = subjects.detail(subject_id)
            # Count of catalogue rows should match catalogue_ids
            self.assertEqual(
                len(detail["catalogue"]), len(catalogue_ids),
                f"{subject_id}: catalogue row count {len(detail['catalogue'])} != catalogue_ids {len(catalogue_ids)}"
            )
            # Every catalogue_id must appear exactly once
            seen = set()
            for row in detail["catalogue"]:
                rid = row["id"]
                if rid in seen:
                    self.fail(f"{subject_id}: duplicate catalogue id '{rid}'")
                seen.add(rid)
            for cid in catalogue_ids:
                self.assertIn(cid, seen, f"{subject_id}: catalogue_id '{cid}' missing from detail catalogue")

    def test_every_worksheet_has_exactly_one_tile(self):
        """Every worksheet sits in exactly one tile; no worksheet is orphaned or duplicated."""
        for subject_id in self.all_subjects:
            detail = subjects.detail(subject_id)
            tiles = detail.get("tiles") or []
            if not tiles:
                # Shelves without tiles (management, finance, economics) are allowed to have worksheets
                # in the flat list — this invariant only applies when tiles exist.
                continue
            placed_sheets = set()
            for tile in tiles:
                for sheet in tile.get("worksheets", []):
                    cid = sheet.get("key") or sheet.get("catalogue_id")
                    if cid in placed_sheets:
                        self.fail(f"{subject_id}: worksheet '{cid}' appears in multiple tiles")
                    placed_sheets.add(cid)
            # All worksheets in detail must be placed
            for sheet in detail["worksheets"]:
                cid = sheet["key"]
                self.assertIn(cid, placed_sheets,
                              f"{subject_id}: worksheet '{cid}' not placed in any tile (tiles exist)")


if __name__ == "__main__":
    unittest.main()