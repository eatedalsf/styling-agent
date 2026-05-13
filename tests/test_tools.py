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
    get_user_wardrobe,
    save_user_item,
    USER_DATA_PATH,
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

    def test_past_date_uses_seasonal_fallback(self):
        """Past dates can't have a forecast — fallback honestly."""
        from weather_tool import get_weather_for_date
        from datetime import date as _d, timedelta as _td
        past = (_d.today() - _td(days=30)).isoformat()
        r = get_weather_for_date(past, _today=_d.today())
        self.assertTrue(r.get("success"))
        self.assertEqual(r.get("source"), "seasonal-fallback")
        self.assertEqual(r["weather"].get("fallback_reason"), "past-date")
        self.assertFalse(r.get("in_range"))

    def test_date_beyond_window_uses_seasonal_fallback(self):
        """Dates more than 15 days out are beyond Open-Meteo's free
        forecast window — honest seasonal fallback."""
        from weather_tool import get_weather_for_date
        from datetime import date as _d, timedelta as _td
        far = (_d.today() + _td(days=90)).isoformat()
        r = get_weather_for_date(far, _today=_d.today())
        self.assertTrue(r.get("success"))
        self.assertEqual(r.get("source"), "seasonal-fallback")
        self.assertEqual(r["weather"].get("fallback_reason"),
                         "beyond-forecast-window")
        # Layer advice mentions the fallback honestly.
        self.assertIn("Seasonal estimate", r["weather"]["layer_advice"])

    def test_unparseable_date_falls_back_to_now(self):
        """Garbage input shouldn't crash — fall back to current weather."""
        from weather_tool import get_weather_for_date
        r = get_weather_for_date("not-a-date")
        self.assertTrue(r.get("success"))
        # Either live or api-error-fallback — both are acceptable.
        self.assertIn(r.get("source"), ("live", "seasonal-fallback"))

    def test_seasonal_fallback_varies_by_month(self):
        """A January date should be cold; a July date should be warm."""
        from weather_tool import get_weather_for_date
        from datetime import date as _d
        # Both far enough out to be guaranteed seasonal fallback.
        jan = "2099-01-15"; jul = "2099-07-15"
        r_jan = get_weather_for_date(jan, _today=_d.today())
        r_jul = get_weather_for_date(jul, _today=_d.today())
        self.assertLess(r_jan["weather"]["temp_f"], r_jul["weather"]["temp_f"])
        # Conditions reflect the season too.
        self.assertIn(r_jan["weather"]["condition"],
                      ("Mixed Conditions", "Partly Cloudy"))

    def test_multiple_future_events_dont_all_share_today_weather(self):
        """Regression for the reported bug: each future event must get
        its OWN weather object. We use two far-out dates so both
        deterministically go through the seasonal fallback in
        different months — they should differ in temperature."""
        from weather_tool import get_weather_for_date
        from datetime import date as _d
        winter = get_weather_for_date("2099-01-15", _today=_d.today())
        summer = get_weather_for_date("2099-07-15", _today=_d.today())
        # Two different target_date values, two different weather dicts.
        self.assertEqual(winter["target_date"], "2099-01-15")
        self.assertEqual(summer["target_date"], "2099-07-15")
        self.assertNotEqual(winter["weather"]["temp_f"],
                            summer["weather"]["temp_f"])

    def test_seasonal_fallback_has_honest_label_in_layer_advice(self):
        """The reasoning trail and UI must be able to see that this
        is NOT a live forecast. Source field + fallback_reason both
        carry that signal."""
        from weather_tool import get_weather_for_date
        from datetime import date as _d
        r = get_weather_for_date("2099-08-15", _today=_d.today())
        self.assertEqual(r["source"], "seasonal-fallback")
        self.assertEqual(r["weather"]["fallback_reason"],
                         "beyond-forecast-window")
        # The layer_advice string itself flags the fallback so users
        # who only see that line still know it's not live.
        self.assertIn("Seasonal estimate", r["weather"]["layer_advice"])

    def test_agent_run_stamps_weather_source(self):
        """End-to-end: run_agent must put a `_source` on the weather
        object so the Planner UI can label live vs forecast vs seasonal."""
        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="casual")
        w = r.get("weather") or {}
        self.assertIn("_source", w)
        self.assertIn(w["_source"], ("live", "forecast", "seasonal-fallback"))


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


class TestWardrobeBuilder(unittest.TestCase):
    """
    Wardrobe Builder overlay tests. Each test saves a fresh copy of the
    user file, runs its assertions, and restores the file at teardown
    so the suite stays idempotent and never pollutes the demo data.
    """

    @classmethod
    def setUpClass(cls):
        # Snapshot the existing user_wardrobe.json so we can restore it.
        cls._original = None
        if os.path.exists(USER_DATA_PATH):
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                cls._original = f.read()

    @classmethod
    def tearDownClass(cls):
        if cls._original is not None:
            with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
                f.write(cls._original)
        else:
            # File didn't exist before; remove anything we created.
            if os.path.exists(USER_DATA_PATH):
                os.remove(USER_DATA_PATH)

    def setUp(self):
        # Reset overlay to empty between tests.
        import json as _json
        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            _json.dump({"clothing": [], "shoes": [], "accessories": []}, f)

    def test_get_user_wardrobe_empty(self):
        r = get_user_wardrobe()
        self.assertTrue(r.get("success"))
        ow = r.get("user_wardrobe")
        self.assertEqual(ow["clothing"], [])
        self.assertEqual(ow["shoes"], [])
        self.assertEqual(ow["accessories"], [])

    def test_save_user_item_top_assigns_id(self):
        r = save_user_item("top", {
            "name": "Test Cream Blouse",
            "color": "cream",
            "formality": "smart_casual",
            "season": ["spring", "summer"],
            "tags": ["work", "dinner"],
        })
        self.assertTrue(r.get("success"), msg=r.get("error"))
        item = r["item"]
        self.assertEqual(item["id"], "UC001")
        self.assertEqual(item["type"], "top")
        self.assertEqual(item["availability"], "available")
        self.assertEqual(item["source"], "user")

    def test_save_user_item_id_increments_per_section(self):
        save_user_item("top",       {"name": "A1", "color": "white"})
        save_user_item("bottom",    {"name": "B1", "color": "black"})
        save_user_item("shoes",     {"name": "Shoe1", "color": "tan"})
        save_user_item("accessory", {"name": "Acc1", "color": "gold"})
        save_user_item("dress",     {"name": "D1",  "color": "burgundy"})

        ow = get_user_wardrobe()["user_wardrobe"]
        clothing_ids = [i["id"] for i in ow["clothing"]]
        self.assertEqual(clothing_ids, ["UC001", "UC002", "UC003"])
        self.assertEqual([i["id"] for i in ow["shoes"]],       ["US001"])
        self.assertEqual([i["id"] for i in ow["accessories"]], ["UA001"])

    def test_save_user_item_rejects_unknown_category(self):
        r = save_user_item("nonsense_category", {"name": "X", "color": "x"})
        self.assertFalse(r.get("success"))
        self.assertIn("Unknown category", r.get("error", ""))

    def test_save_user_item_rejects_missing_name(self):
        r = save_user_item("top", {"name": "", "color": "white"})
        self.assertFalse(r.get("success"))
        self.assertIn("name", r.get("error", "").lower())

    def test_save_user_item_rejects_missing_color(self):
        r = save_user_item("top", {"name": "Blouse", "color": ""})
        self.assertFalse(r.get("success"))
        self.assertIn("color", r.get("error", "").lower())

    def test_added_item_visible_in_merged_wardrobe(self):
        save_user_item("top", {
            "name": "Test Item For Merge",
            "color": "cream",
            "tags": ["work"],
            "season": ["all"],
        })
        merged = get_wardrobe()
        self.assertTrue(merged.get("success"))
        names = [i["name"] for i in merged["wardrobe"]["clothing"]]
        self.assertIn("Test Item For Merge", names)

    def test_added_item_eligible_in_occasion_filter(self):
        save_user_item("top", {
            "name": "Test Work Top",
            "color": "ivory",
            "tags": ["work"],
            "season": ["fall", "spring", "all"],
            "formality": "business",
        })
        pool = filter_items_by_occasion("work", "fall")
        names = [i["name"] for i in pool["clothing"]]
        self.assertIn("Test Work Top", names)

    def test_unavailable_item_excluded_from_filter(self):
        save_user_item("top", {
            "name": "Test In Laundry",
            "color": "white",
            "tags": ["work"],
            "season": ["all"],
            "availability": "in laundry",
        })
        pool = filter_items_by_occasion("work", "fall")
        names = [i["name"] for i in pool["clothing"]]
        self.assertNotIn("Test In Laundry", names,
                         "Unavailable items should be filtered out of the candidate pool.")

    def test_malformed_overlay_falls_back_gracefully(self):
        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json")
        r = get_user_wardrobe()
        self.assertTrue(r.get("success"))
        self.assertEqual(r["user_wardrobe"]["clothing"], [])
        self.assertIn("unreadable", (r.get("error") or "").lower())


# ─────────────────────────────────────────────
# Image understanding (Pillow-only, lazy import)
# ─────────────────────────────────────────────

class TestImageColorSuggestion(unittest.TestCase):
    """
    Verifies suggest_colors_from_image() returns sensible top suggestions
    for synthetic solid-color images. Pillow is required for these tests;
    skipped cleanly if unavailable.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image  # noqa: F401
            cls.have_pil = True
        except ImportError:
            cls.have_pil = False

    def _solid_png_bytes(self, rgb, size=(64, 64)):
        """Return PNG bytes for a solid-color image."""
        from PIL import Image
        import io
        img = Image.new("RGB", size, rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_solid_terracotta_suggests_terracotta(self):
        if not self.have_pil:
            self.skipTest("Pillow not installed")
        from wardrobe_tool import suggest_colors_from_image
        bytes_ = self._solid_png_bytes((193, 127, 90))  # #C17F5A
        r = suggest_colors_from_image(bytes_, top_n=3)
        self.assertTrue(r.get("success"))
        self.assertGreater(len(r["suggestions"]), 0)
        self.assertEqual(r["suggestions"][0]["name"], "terracotta")

    def test_solid_navy_suggests_navy(self):
        if not self.have_pil:
            self.skipTest("Pillow not installed")
        from wardrobe_tool import suggest_colors_from_image
        bytes_ = self._solid_png_bytes((31, 42, 68))  # #1F2A44
        r = suggest_colors_from_image(bytes_, top_n=3)
        self.assertTrue(r.get("success"))
        self.assertEqual(r["suggestions"][0]["name"], "navy")

    def test_solid_camel_suggests_camel(self):
        if not self.have_pil:
            self.skipTest("Pillow not installed")
        from wardrobe_tool import suggest_colors_from_image
        bytes_ = self._solid_png_bytes((184, 152, 120))  # #B89878
        r = suggest_colors_from_image(bytes_, top_n=3)
        self.assertTrue(r.get("success"))
        self.assertEqual(r["suggestions"][0]["name"], "camel")

    def test_garbage_bytes_returns_clean_error(self):
        if not self.have_pil:
            self.skipTest("Pillow not installed")
        from wardrobe_tool import suggest_colors_from_image
        r = suggest_colors_from_image(b"not an image", top_n=3)
        self.assertFalse(r.get("success"))
        self.assertIn("decode", (r.get("error") or "").lower())


class TestImageSavePipeline(unittest.TestCase):
    """End-to-end: save_user_item with image bytes writes a real PNG and
    records the image_path on the item. Image is cleaned up at teardown."""

    @classmethod
    def setUpClass(cls):
        try:
            from PIL import Image  # noqa: F401
            cls.have_pil = True
        except ImportError:
            cls.have_pil = False
        cls._original = None
        if os.path.exists(USER_DATA_PATH):
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                cls._original = f.read()

    @classmethod
    def tearDownClass(cls):
        import shutil
        from wardrobe_tool import WARDROBE_IMAGES_DIR
        if cls._original is not None:
            with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
                f.write(cls._original)
        else:
            if os.path.exists(USER_DATA_PATH):
                os.remove(USER_DATA_PATH)
        if os.path.isdir(WARDROBE_IMAGES_DIR):
            shutil.rmtree(WARDROBE_IMAGES_DIR, ignore_errors=True)

    def setUp(self):
        import json as _json
        with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
            _json.dump({"clothing": [], "shoes": [], "accessories": []}, f)

    def test_save_with_image_writes_file_and_records_path(self):
        if not self.have_pil:
            self.skipTest("Pillow not installed")
        from PIL import Image
        from wardrobe_tool import save_user_item, WARDROBE_IMAGES_DIR
        import io
        # Build a small synthetic terracotta image.
        img = Image.new("RGB", (200, 200), (193, 127, 90))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        r = save_user_item(
            "top",
            {"name": "Photo Test Top", "color": "terracotta",
             "tags": ["work"], "season": ["all"]},
            image_bytes=buf.getvalue(),
        )
        self.assertTrue(r.get("success"), msg=r.get("error"))
        item = r["item"]
        self.assertIn("image_path", item)
        self.assertTrue(item["image_path"], "image_path should be non-empty")
        full = os.path.join(os.path.dirname(WARDROBE_IMAGES_DIR), item["image_path"])
        self.assertTrue(os.path.exists(full), f"Expected image at {full}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
