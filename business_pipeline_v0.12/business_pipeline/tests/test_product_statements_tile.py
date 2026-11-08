"""The accounting shelf after the statements tile landed (B-204).

Adding a tile list flips a subject page from groups to tiles, and a tool that is in no tile then
disappears from the page.  These tests make that mechanical: every accounting tool must land in
exactly one tile, every group the shelf already used must still have a tile, and the statements tile
must be a service (it runs no frozen preset) and present in the served UI.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import subjects  # noqa: E402


class AccountingTileTest(unittest.TestCase):
    def setUp(self):
        self.detail = subjects.detail("accounting")
        self.tiles = self.detail["tiles"]

    def test_every_accounting_tool_lands_in_exactly_one_tile(self):
        placed = [tool["key"] for tile in self.tiles for tool in tile["tools"]]
        listed = [tool["key"] for tool in self.detail["tools"]]
        self.assertEqual(sorted(placed), sorted(listed),
                         "a tool is in no tile (it would vanish from the page) or in two")
        self.assertEqual(len(placed), len(set(placed)))

    def test_every_group_the_shelf_used_has_a_tile(self):
        groups = sorted({tool["group"] for tool in self.detail["tools"] if tool["group"]})
        keys = [tile["key"] for tile in self.tiles]
        self.assertEqual([group for group in groups if group not in keys], [],
                         "a calculator group has no tile, so its tools move or vanish")

    def test_the_statements_tile_is_first_and_is_a_service(self):
        first = self.tiles[0]
        self.assertEqual(first["key"], "statements")
        self.assertEqual(first["service"], "statements")
        self.assertEqual((first["tools"], first["worksheets"], first["records"]), ([], [], []))

    def test_the_shelf_still_offers_its_calculators(self):
        self.assertEqual(len(self.detail["tools"]), 18)
        # Two service tiles (statements, business plan) and seven calculator groups.
        self.assertEqual(len(self.tiles), 9)

    def test_the_served_ui_carries_the_tile_and_its_hook(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            page = stream.read()
        self.assertIn('data-statements-open', page)
        self.assertIn('id="statements-tile"', page)
        self.assertIn("/api/cases/statements", page)

    def test_the_tile_has_its_own_address(self):
        """The tile is reachable by name: its own address opens it, so it is never hunted for.

        The address is presentation: the design owner may name it, so the test pins the
        *contract* (the tile has an address, the router opens it, the opener is exposed) and not
        one spelling of that address.
        """
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            page = stream.read()
        self.assertRegex(page, r'href="#/[a-z-]*statements"',
                         "the tile link must carry the address")
        self.assertRegex(page, r'head === "[a-z-]*statements"',
                         "the router must open the tile from that address")
        self.assertIn("window.openStatementsTile = open;", page,
                      "the tile must expose the opener the router calls")

    def test_no_other_subject_gained_a_statements_tile(self):
        for subject in ("finance", "economics", "management", "operations", "marketing", "people"):
            keys = [tile["key"] for tile in subjects.detail(subject)["tiles"]]
            self.assertNotIn("statements", keys, subject + " gained a statements tile")


if __name__ == "__main__":
    unittest.main()
