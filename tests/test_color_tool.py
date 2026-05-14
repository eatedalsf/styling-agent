"""
Tests for color_tool — specifically the color_tier_for helper that
acts as the single source of truth for "is this color flattering for
this skin tone?". Both color_tool.score_outfit_colors AND
styling_agent._evaluate_tradeoffs call it; if it drifts, the Today
page would show contradictory color signals on the same item.
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from color_tool import color_tier_for, score_outfit_colors  # noqa: E402


class TestColorTierFor(unittest.TestCase):
    """Pin the four-way classification for warm-olive (the user's
    profile) — these are the cases that produced contradictory
    tradeoffs in the screenshot."""

    def test_gold_is_best_for_warm_olive(self):
        # color_rules.json: "gold" is in best_colors for warm olive
        self.assertEqual(color_tier_for("gold", "warm olive"), "best")

    def test_white_gold_compound_matches_gold_best(self):
        # The Pearl Stud Earrings case: substring match should pick
        # up "gold" inside "white/gold" and tier as best.
        self.assertEqual(color_tier_for("white/gold", "warm olive"), "best")

    def test_black_is_good_for_warm_olive(self):
        # color_rules.json: "black" is in good_colors for warm olive.
        # The Black Structured Handbag case — should NOT produce a
        # tradeoff (good, not avoid).
        self.assertEqual(color_tier_for("black", "warm olive"), "good")

    def test_lavender_is_avoid_for_warm_olive(self):
        # color_rules.json: "lavender" is in avoid_colors. The only
        # tier that should fire a tradeoff.
        self.assertEqual(color_tier_for("lavender", "warm olive"), "avoid")

    def test_unknown_color_is_neutral(self):
        # Color absent from all three lists for the skin tone.
        self.assertEqual(color_tier_for("emerald", "warm olive"), "neutral")

    def test_empty_inputs_return_neutral(self):
        self.assertEqual(color_tier_for("", "warm olive"), "neutral")
        self.assertEqual(color_tier_for("gold", ""), "neutral")
        self.assertEqual(color_tier_for("", ""), "neutral")


class TestScoreOutfitColorsUsesTierHelper(unittest.TestCase):
    """score_outfit_colors must classify items identically to
    color_tier_for so the Step 7 score and the per-item tradeoff
    text agree on the same color."""

    def test_score_and_tier_agree_on_warm_olive_outfit(self):
        items = [
            {"name": "Gold Earrings",   "color": "gold"},     # best
            {"name": "Black Handbag",   "color": "black"},    # good
            {"name": "Lavender Scarf",  "color": "lavender"}, # avoid
            {"name": "Emerald Brooch",  "color": "emerald"},  # neutral
        ]
        result = score_outfit_colors(items, "warm olive")
        joined = " | ".join(result.get("notes", []) + result.get("flags", []))
        # best → ✓ excellent
        self.assertIn("Gold Earrings", joined)
        self.assertIn("excellent", joined.lower())
        # good → ✓ works well
        self.assertIn("Black Handbag", joined)
        self.assertIn("works well", joined.lower())
        # avoid → ⚠ less flattering
        self.assertIn("Lavender Scarf", joined)
        self.assertIn("less flattering", joined.lower())
        # neutral → no mention
        # (Emerald Brooch may appear in notes only if it landed there,
        # but it should NOT appear in flags.)
        for flag in result.get("flags", []):
            self.assertNotIn("Emerald", flag)


if __name__ == "__main__":
    unittest.main(verbosity=2)
