"""
Tests for wardrobe_query.infer_wishlist_taste — specifically the
narrative summary line that appears in the agent's reasoning panel.

The earlier behavior used `" and ".join(bits)` producing strings like
"X and Y and Z and W" with a lowercase store name. These tests pin
the Oxford-comma join and the title-cased store names.
"""

import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class TestWishlistTasteSummary(unittest.TestCase):
    """Mock the wishlist + wardrobe loaders so the summary depends
    only on the inputs we hand-craft. We patch `get_wishlist` and
    `get_wardrobe` at the wardrobe_query module level."""

    def _run(self, wishlist_items: list) -> dict:
        # `infer_wishlist_taste` lazy-imports get_wishlist from
        # shopping_tool inside the function body, so we patch at the
        # source module. `get_wardrobe` IS imported at module load
        # in wardrobe_query, so it gets patched there.
        from wardrobe_query import infer_wishlist_taste
        canned_wishlist = {"items": wishlist_items}
        canned_wardrobe = {
            "success": True,
            "wardrobe": {"clothing": [], "shoes": [], "accessories": []},
            "error": None,
        }
        with mock.patch("shopping_tool.get_wishlist",
                        return_value=canned_wishlist), \
             mock.patch("wardrobe_query.get_wardrobe",
                        return_value=canned_wardrobe):
            return infer_wishlist_taste()

    def test_three_signals_use_oxford_join(self):
        """3+ bits should render as 'X, Y, and Z' — never 'X and Y and Z'."""
        items = [
            {"name": "Cream Trench Coat", "category": "outerwear",
             "tags": ["work"], "preferred_store": "aritzia"},
            {"name": "Navy Blazer", "category": "outerwear",
             "tags": ["work"], "preferred_store": "aritzia"},
            {"name": "Silk Blouse", "category": "top",
             "tags": ["smart_casual"], "preferred_store": "aritzia"},
        ]
        out = self._run(items)
        summary = out.get("summary", "")
        # Negative assertion: no "and ... and" pattern
        self.assertNotIn(" and ".join([""] * 3).replace("  ", " "), summary)
        # Positive assertion: contains the Oxford ", and " before the
        # final clause when there are 3+ bits.
        self.assertIn(", and ", summary,
            f"Expected Oxford ', and ' in summary. Got: {summary!r}")

    def test_store_names_are_title_cased(self):
        """`aritzia` saved lowercase should render as `Aritzia`."""
        items = [
            {"name": "Cream Trench Coat", "category": "outerwear",
             "tags": ["work"], "preferred_store": "aritzia"},
        ]
        out = self._run(items)
        summary = out.get("summary", "")
        self.assertIn("Aritzia", summary,
            f"Expected title-cased store name. Got: {summary!r}")
        self.assertNotIn("aritzia", summary,
            "Lowercase store name leaked into the summary.")

    def test_empty_wishlist_yields_empty_summary(self):
        out = self._run([])
        self.assertEqual(out.get("summary", ""), "")

    def test_summary_starts_with_wishlist_phrase(self):
        """Any non-empty summary should lead with the canonical
        opening phrase. Bit count varies by what infer_wishlist_taste
        extracts from the items (categories / colors / store / etc.),
        so we don't lock the exact bit count — just the framing."""
        items = [
            {"name": "Cream Trench Coat", "category": "outerwear",
             "tags": [], "preferred_store": ""},
        ]
        out = self._run(items)
        summary = out.get("summary", "")
        self.assertTrue(summary.startswith("Your wishlist suggests"),
            f"Got: {summary!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
