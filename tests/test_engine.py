import json
import unittest
from pathlib import Path

from collector.engine import burden, classify


class EngineTests(unittest.TestCase):
    def test_thresholds(self):
        rule = {"direction":"higher_is_worse","amber":10,"red":20}
        self.assertEqual(classify(9, rule, True)[0], "G")
        self.assertEqual(classify(10, rule, True)[0], "A")
        self.assertEqual(classify(20, rule, True)[0], "R")
        self.assertEqual(classify(None, rule, False)[0], "B")

    def test_b_excluded_but_coverage_visible(self):
        result = burden([{"status":"R"},{"status":"G"},{"status":"B"}])
        self.assertEqual(result["score"], 50.0)
        self.assertEqual(result["coverage"], 66.7)

    def test_reference_never_enters_history(self):
        snapshots = [
            {"kind":"reference_snapshot","as_of":"2026-10-14"},
            {"kind":"live_observation","as_of":"2026-10-15"},
        ]
        history = [row for row in snapshots if row.get("kind") == "live_observation"]
        self.assertEqual([row["as_of"] for row in history], ["2026-10-15"])

    def test_all_22_indicators_are_automatic_and_documented(self):
        path = Path(__file__).parents[1] / "config" / "indicators.json"
        indicators = json.loads(path.read_text(encoding="utf-8"))["indicators"]
        self.assertEqual(len(indicators), 22)
        self.assertEqual(len({item["id"] for item in indicators}), 22)
        self.assertTrue(all(item["mode"] == "automatic" for item in indicators))
        self.assertTrue(all(item.get("proxy") and item.get("limitation") for item in indicators))


if __name__ == "__main__":
    unittest.main()

