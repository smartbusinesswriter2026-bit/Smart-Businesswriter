import sys, json, os, unittest
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp import server

FIX = json.load(open(os.path.join("tests", "fixtures", "frozen_contract.json"), encoding="utf-8"))


class FrozenCore(unittest.TestCase):
    """The core deterministic backend is FROZEN (B-079). A failure here means the public contract changed.

    Do not edit the fixture to make this green. An unfreeze needs the owner's approval, a B-decision, and a
    written reason why the core behaviour must change; the computation owner reviews it (B-066/B-080).
    Product-backend features belong outside this contract (see docs/BACKEND_CONTRACT.md).
    """

    def test_method_contracts_are_frozen(self):
        actual = {mid: {"tier": m.tier, "metric": m.metric, "unit": m.unit, "test_names": list(m.test_names),
                        "claim_ceiling": m.claim_ceiling, "category": m.category,
                        "inputs": sorted(m.input_schema)}
                  for mid, m in sorted(LIBRARY.items())}
        self.assertEqual(actual, FIX["methods"], "the method contract changed; the core deterministic backend is frozen (B-079)")

    def test_presets_are_frozen(self):
        self.assertEqual(sorted(server.PRESETS), FIX["presets"], "the preset surface changed; the core deterministic backend is frozen (B-079)")

    def test_api_route_surface_is_frozen(self):
        src = open(os.path.join("src", "bp", "server.py"), encoding="utf-8").read()
        missing = [r for r in FIX["routes"] if r not in src]
        self.assertEqual(missing, [], "an API route disappeared or moved; the core deterministic backend is frozen (B-079)")
        self.assertEqual(len(FIX["routes"]), 12)


if __name__ == "__main__":
    unittest.main()
