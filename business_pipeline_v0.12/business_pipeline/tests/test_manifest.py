import unittest
from decimal import Decimal

from bp import manifest


class ManifestTests(unittest.TestCase):
    def test_require_returns_value(self):
        m = manifest.Manifest(tax_rate=Decimal("0.25"))
        self.assertEqual(m.require("tax_rate"), Decimal("0.25"))

    def test_require_raises_on_none(self):
        m = manifest.Manifest()
        with self.assertRaises(manifest.ReviewRequired):
            m.require("inventory_system")


if __name__ == "__main__":
    unittest.main()
