"""Attack-test suite: controls must pass; bypasses are expected failures until a gate fixes them."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cases  # noqa: E402
import harness  # noqa: E402


def makeTest(case):
    def test(self):
        ok, msg = harness.check(case)
        self.assertTrue(ok, f"{case['id']}: {msg}")
    return test


class GateControls(unittest.TestCase):
    pass


class GateAttacks(unittest.TestCase):
    pass


for _c in cases.CONTROLS:
    setattr(GateControls, "test_" + _c["id"].replace("-", "_"), makeTest(_c))

for _c in cases.ATTACKS:
    # Known bypass in v0.4.0: expected failure. Unexpected success fails the run, so a fixed gate must drop the mark.
    setattr(GateAttacks, "test_" + _c["id"].replace("-", "_"), unittest.expectedFailure(makeTest(_c)))


class CaseTableTests(unittest.TestCase):
    def test_at_least_25_attack_cases(self):
        self.assertGreaterEqual(len(cases.ATTACKS), 25)

    def test_ids_are_unique(self):
        ids = [c["id"] for c in cases.CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_expectation_is_a_known_decision(self):
        for c in cases.CASES:
            self.assertIn(c["expect"], ("allow", "deny", "ask"), c["id"])


if __name__ == "__main__":
    unittest.main()
