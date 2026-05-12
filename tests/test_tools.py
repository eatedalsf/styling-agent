"""
Tool-level smoke tests. Exercises each tool's success path plus at
least one fallback path where applicable.

Run with:
    python -m unittest tests.test_tools
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from calendar_tool import get_upcoming_events  # noqa: E402
from weather_tool import get_weather  # noqa: E402
from wardrobe_tool import (  # noqa: E402
    get_wardrobe,
    get_owner_profile,
    filter_items_by_occasion,
    check_gaps,
)
from color_tool import get_color_rules, score_outfit_colors  # noqa: E402


class TestCalendarTool(unittest.TestCase):
    def test_get_upcoming_events_success(self):
        r = get_upcoming_events(days_ahead=14)
        self.assertTrue(r.get("success"))
        self.assertIsInstance(r.get("events"), list)

    def test_zero_day_window(self):
        # 0-day window may legitimately return zero events but should
        # not error out.
        r = get_upcoming_events(days_ahead=0)
        self.assertTrue(r.get("success"))


class TestWeatherTool(unittest.TestCase):
    def test_returns_weather_dict(self):
        # Live or fallback — either way we must get a usable weather dict.
        r = get_weather()
        self.assertTrue(r.get("success"))
        w = r.get("weather")
        self.assertIsInstance(w, dict)
        for key in ("city", "temp_f", "condition", "layer_advice"):
            self.assertIn(key, w)


class TestWardrobeTool(unittest.TestCase):
    def test_get_wardrobe_loads(self):
        r = get_wardrobe()
        self.assertTrue(r.get("success"))
        wardrobe = r.get("wardrobe")
        self.assertIsInstance(wardrobe, dict)
        for key in ("clothing", "shoes", "accessories", "owner"):
            self.assertIn(key, wardrobe)

    def test_owner_profile_has_required_fields(self):
        r = get_owner_profile()
        self.assertTrue(r.get("success"))
        profile = r.get("profile")
        for key in ("name", "body_shape", "skin_tone", "style_preferences"):
            self.assertIn(key, profile)

    def test_filter_returns_pools(self):
        r = filter_items_by_occasion("work", "fall")
        self.assertTrue(r.get("success"))
        for key in ("clothing", "shoes", "accessories"):
            self.assertIsInstance(r.get(key), list)

    def test_check_gaps_detects_missing(self):
        # Empty outfit should report all required pieces missing.
        gaps = check_gaps([], ["top", "bottom"])
        self.assertEqual(set(gaps), {"top", "bottom"})

    def test_check_gaps_complete(self):
        outfit = [{"type": "top"}, {"type": "bottom"}]
        gaps = check_gaps(outfit, ["top", "bottom"])
        self.assertEqual(gaps, [])


class TestColorTool(unittest.TestCase):
    def test_known_skin_tone_returns_rules(self):
        r = get_color_rules("warm olive")
        self.assertTrue(r.get("success"))
        rules = r.get("rules")
        self.assertIn("best_colors", rules)
        self.assertIn("good_colors", rules)
        self.assertIn("avoid_colors", rules)

    def test_unknown_skin_tone_fallback(self):
        r = get_color_rules("unknown-tone-xyz")
        self.assertTrue(r.get("success"))
        rules = r.get("rules")
        # Fallback rules should still expose the same keys.
        self.assertIn("best_colors", rules)

    def test_score_outfit_colors_range(self):
        items = [
            {"name": "Camel Coat", "color": "camel"},
            {"name": "Cool Grey Tank", "color": "cool grey"},
        ]
        r = score_outfit_colors(items, "warm olive")
        self.assertIn("score", r)
        self.assertGreaterEqual(r["score"], 0)
        self.assertLessEqual(r["score"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
