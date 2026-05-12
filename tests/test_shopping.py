"""
Tests for shopping_tool.py — favorite stores, wishlist, and the
store-aware augmentation the agent pulls into Step 6.

Each test class snapshots favorite_stores.json + wishlist.json so the
suite is idempotent and never pollutes the demo state.

Run with:
    python -m unittest tests.test_shopping
"""

import json
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shopping_tool import (  # noqa: E402
    STORES_PATH, WISHLIST_PATH,
    get_favorite_stores, add_favorite_store, remove_favorite_store,
    get_wishlist, add_wishlist_item, remove_wishlist_item,
    store_aware_suggestions, gap_is_on_wishlist,
    VALID_PRIORITIES,
)


class _ShoppingSnapshotMixin:
    """Snapshot + restore both data files across a test class."""

    @classmethod
    def setUpClass(cls):
        cls._stores_original = None
        cls._wishlist_original = None
        if os.path.exists(STORES_PATH):
            with open(STORES_PATH, "r", encoding="utf-8") as f:
                cls._stores_original = f.read()
        if os.path.exists(WISHLIST_PATH):
            with open(WISHLIST_PATH, "r", encoding="utf-8") as f:
                cls._wishlist_original = f.read()

    @classmethod
    def tearDownClass(cls):
        for path, original in (
            (STORES_PATH,   cls._stores_original),
            (WISHLIST_PATH, cls._wishlist_original),
        ):
            if original is not None:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(original)
            else:
                if os.path.exists(path):
                    os.remove(path)

    def setUp(self):
        # Reset both files to a clean empty state before every test.
        with open(STORES_PATH, "w", encoding="utf-8") as f:
            json.dump({"stores": []}, f)
        with open(WISHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"items": []}, f)


# ─────────────────────────────────────────────
# FAVORITE STORES
# ─────────────────────────────────────────────

class TestFavoriteStores(_ShoppingSnapshotMixin, unittest.TestCase):

    def test_empty_on_fresh_install(self):
        r = get_favorite_stores()
        self.assertTrue(r["success"])
        self.assertEqual(r["stores"], [])

    def test_add_store_basic(self):
        r = add_favorite_store("COS")
        self.assertTrue(r["success"])
        self.assertEqual(r["store"]["name"], "COS")
        self.assertIsNone(r["store"]["url"])
        stores = get_favorite_stores()["stores"]
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["name"], "COS")

    def test_add_store_with_url_and_notes(self):
        r = add_favorite_store("Aritzia", url="https://aritzia.com", notes="Wardrobe staples")
        self.assertTrue(r["success"])
        self.assertEqual(r["store"]["url"], "https://aritzia.com")
        self.assertEqual(r["store"]["notes"], "Wardrobe staples")

    def test_add_store_dedupes_case_insensitive(self):
        add_favorite_store("COS")
        r = add_favorite_store("cos")
        self.assertFalse(r["success"])
        self.assertIn("already a favorite", r["error"])

    def test_add_store_rejects_empty_name(self):
        r = add_favorite_store("   ")
        self.assertFalse(r["success"])
        self.assertIn("required", r["error"].lower())

    def test_remove_store(self):
        add_favorite_store("Mejuri")
        r = remove_favorite_store("Mejuri")
        self.assertTrue(r["success"])
        self.assertEqual(get_favorite_stores()["stores"], [])

    def test_remove_store_not_found(self):
        r = remove_favorite_store("DoesntExist")
        self.assertFalse(r["success"])
        self.assertIn("not in favorites", r["error"])

    def test_malformed_stores_file_falls_back(self):
        with open(STORES_PATH, "w", encoding="utf-8") as f:
            f.write("{ not json")
        r = get_favorite_stores()
        self.assertTrue(r["success"])
        self.assertEqual(r["stores"], [])
        self.assertIn("unreadable", (r.get("error") or "").lower())


# ─────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────

class TestWishlist(_ShoppingSnapshotMixin, unittest.TestCase):

    def test_empty_on_fresh_install(self):
        r = get_wishlist()
        self.assertTrue(r["success"])
        self.assertEqual(r["items"], [])

    def test_add_item_basic(self):
        r = add_wishlist_item({"name": "Cream linen blazer"})
        self.assertTrue(r["success"])
        self.assertEqual(r["item"]["name"], "Cream linen blazer")
        self.assertEqual(r["item"]["id"], "W001")
        self.assertEqual(r["item"]["priority"], "medium")
        self.assertIn("added_date", r["item"])

    def test_add_item_with_full_fields(self):
        r = add_wishlist_item({
            "name":            "Tailored navy coat",
            "category":        "outerwear",
            "preferred_store": "COS",
            "tags":            ["work", "Travel"],
            "priority":        "HIGH",
            "notes":           "For client trips",
            "source_url":      "https://example.com/x",
            "linked_gap":      "outerwear",
        })
        self.assertTrue(r["success"])
        item = r["item"]
        self.assertEqual(item["category"], "outerwear")
        self.assertEqual(item["preferred_store"], "COS")
        self.assertEqual(item["tags"], ["work", "travel"])  # lowercased
        self.assertEqual(item["priority"], "high")
        self.assertEqual(item["linked_gap"], "outerwear")

    def test_invalid_priority_falls_back_to_medium(self):
        r = add_wishlist_item({"name": "X", "priority": "URGENT"})
        self.assertTrue(r["success"])
        self.assertEqual(r["item"]["priority"], "medium")

    def test_id_auto_increments(self):
        add_wishlist_item({"name": "A"})
        add_wishlist_item({"name": "B"})
        add_wishlist_item({"name": "C"})
        ids = [it["id"] for it in get_wishlist()["items"]]
        self.assertEqual(ids, ["W001", "W002", "W003"])

    def test_add_item_rejects_empty_name(self):
        r = add_wishlist_item({"name": "  "})
        self.assertFalse(r["success"])
        self.assertIn("required", r["error"].lower())

    def test_remove_wishlist_item(self):
        add_wishlist_item({"name": "A"})
        r = remove_wishlist_item("W001")
        self.assertTrue(r["success"])
        self.assertEqual(get_wishlist()["items"], [])

    def test_remove_wishlist_item_not_found(self):
        r = remove_wishlist_item("W999")
        self.assertFalse(r["success"])

    def test_malformed_wishlist_file_falls_back(self):
        with open(WISHLIST_PATH, "w", encoding="utf-8") as f:
            f.write("{ broken")
        r = get_wishlist()
        self.assertTrue(r["success"])
        self.assertEqual(r["items"], [])


# ─────────────────────────────────────────────
# STORE-AWARE SUGGESTIONS
# ─────────────────────────────────────────────

class TestStoreAwareSuggestions(_ShoppingSnapshotMixin, unittest.TestCase):

    def test_no_favorites_returns_base_unchanged(self):
        base = ["A blazer", "A coat"]
        out = store_aware_suggestions(base)
        self.assertEqual(out, base)

    def test_one_favorite_adds_singular_phrasing(self):
        add_favorite_store("COS")
        out = store_aware_suggestions(["A blazer"])
        self.assertEqual(len(out), 2)
        self.assertIn("COS", out[-1])
        self.assertIn("favorite store", out[-1])

    def test_two_favorites_use_or(self):
        add_favorite_store("COS")
        add_favorite_store("Aritzia")
        out = store_aware_suggestions(["A blazer"])
        self.assertIn("COS or Aritzia", out[-1])

    def test_many_favorites_join_with_commas(self):
        for s in ("COS", "Aritzia", "Mejuri"):
            add_favorite_store(s)
        out = store_aware_suggestions(["A blazer"])
        last = out[-1]
        self.assertIn("COS", last)
        self.assertIn("Aritzia", last)
        self.assertIn("Mejuri", last)

    def test_does_not_mutate_input_list(self):
        base = ["X"]
        add_favorite_store("COS")
        out = store_aware_suggestions(base)
        # input list should be untouched
        self.assertEqual(base, ["X"])
        self.assertEqual(len(out), 2)


# ─────────────────────────────────────────────
# GAP → WISHLIST LINKING
# ─────────────────────────────────────────────

class TestGapLinking(_ShoppingSnapshotMixin, unittest.TestCase):

    def test_gap_not_on_wishlist_initially(self):
        self.assertFalse(gap_is_on_wishlist("outerwear"))

    def test_save_with_linked_gap_then_detected(self):
        add_wishlist_item({"name": "A coat", "linked_gap": "outerwear"})
        self.assertTrue(gap_is_on_wishlist("outerwear"))
        self.assertFalse(gap_is_on_wishlist("dress"))

    def test_category_alone_counts_as_linked(self):
        add_wishlist_item({"name": "A dress", "category": "dress"})
        self.assertTrue(gap_is_on_wishlist("dress"))

    def test_case_insensitive_match(self):
        add_wishlist_item({"name": "A coat", "linked_gap": "OUTERWEAR"})
        self.assertTrue(gap_is_on_wishlist("outerwear"))


# ─────────────────────────────────────────────
# AGENT INTEGRATION — Step 6 picks up favorites
# ─────────────────────────────────────────────

def _cold_weather_mock():
    """Return a deterministic 50°F weather payload so Step 5's
    outerwear-gap path always fires for these tests, regardless of
    what live Open-Meteo says on this machine today."""
    return {
        "success": True,
        "error":   None,
        "weather": {
            "city": "Test City", "temp_f": 50, "feels_like_f": 47,
            "condition": "Partly Cloudy", "wind_mph": 6,
            "precip_chance_pct": 10, "layer_advice": "A light jacket is recommended.",
        },
    }


class TestAgentShoppingIntegration(_ShoppingSnapshotMixin, unittest.TestCase):
    """
    The agent's outerwear-gap path only fires below 60°F. We mock the
    weather tool to a fixed cold value so these tests are deterministic
    regardless of what the live API returns today.
    """

    def test_baseline_gap_has_no_favorites_line(self):
        with mock.patch("styling_agent.get_weather", return_value=_cold_weather_mock()):
            from styling_agent import run_agent
            r = run_agent(mode="everyday", everyday_request="gym")
        self.assertIn("outerwear", r["gaps"])
        last_lines = " | ".join(r["shopping_suggestions"]).lower()
        # No favorites set → no "favorite store" line should appear.
        self.assertNotIn("favorite store", last_lines)

    def test_saved_favorites_appear_in_gap_suggestions(self):
        add_favorite_store("COS")
        add_favorite_store("Aritzia")
        with mock.patch("styling_agent.get_weather", return_value=_cold_weather_mock()):
            from styling_agent import run_agent
            r = run_agent(mode="everyday", everyday_request="gym")
        self.assertIn("outerwear", r["gaps"])
        last_lines = " | ".join(r["shopping_suggestions"]).lower()
        self.assertIn("cos", last_lines)
        self.assertIn("aritzia", last_lines)
        self.assertIn("favorite store", last_lines)

    def test_agent_baseline_outfit_still_works(self):
        # Sanity: shopping integration doesn't affect non-gap runs.
        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="work")
        self.assertIsNone(r.get("error"))
        self.assertGreater(len(r["recommendation"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
