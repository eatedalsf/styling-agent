"""
Tests for demo_wardrobe.py — the curated 48-item demo loader.

Verifies:
  - load_demo_wardrobe adds every item from demo_wardrobe.json.
  - Running it twice is a no-op (dedup by stable DM-* IDs).
  - User-added items (UC###/US###/UA###) are NEVER touched.
  - Filter pipeline sees demo items so the agent can use them.
  - unload_demo_wardrobe removes every DM-* item and leaves user items.
  - Generated card PNGs are real PNG files.

Every test snapshots user_wardrobe.json and the wardrobe_images/
directory at setUpClass and restores at tearDownClass so the
developer's own closet is never affected.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _wardrobe_images_dir() -> str:
    return os.path.join(_ROOT, "wardrobe_images")


class TestDemoWardrobe(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from wardrobe_tool import USER_DATA_PATH
        cls.USER_DATA_PATH = USER_DATA_PATH
        cls._backup = None
        if os.path.exists(USER_DATA_PATH):
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                cls._backup = f.read()
        # Snapshot any DM-* images currently on disk so we can restore.
        cls._img_dir = _wardrobe_images_dir()
        cls._dm_images_before = set()
        if os.path.isdir(cls._img_dir):
            cls._dm_images_before = {
                f for f in os.listdir(cls._img_dir) if f.startswith("DM-")
            }

    @classmethod
    def tearDownClass(cls):
        # Restore user_wardrobe.json
        if cls._backup is not None:
            with open(cls.USER_DATA_PATH, "w", encoding="utf-8") as f:
                f.write(cls._backup)
        else:
            if os.path.exists(cls.USER_DATA_PATH):
                os.remove(cls.USER_DATA_PATH)
        # Clean up any DM-* images we created.
        if os.path.isdir(cls._img_dir):
            for f in os.listdir(cls._img_dir):
                if f.startswith("DM-") and f not in cls._dm_images_before:
                    try:
                        os.remove(os.path.join(cls._img_dir, f))
                    except OSError:
                        pass

    def setUp(self):
        # Per-test: blank the user wardrobe so tests are independent.
        with open(self.USER_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"_comment": "blanked by test setUp",
                 "clothing": [], "shoes": [], "accessories": []},
                f,
            )
        # Drop cached modules so demo_wardrobe rebinds USER_DATA_PATH.
        for m in ("demo_wardrobe", "wardrobe_tool"):
            sys.modules.pop(m, None)

    # ── Loader behavior ──────────────────────────────────────────

    def test_load_adds_all_items_from_seed(self):
        from demo_wardrobe import load_demo_wardrobe
        r = load_demo_wardrobe()
        self.assertIsNone(r["error"])
        # Demo JSON ships ~48 items; assert at minimum 30 to allow
        # the dataset to grow without breaking the test.
        self.assertGreaterEqual(len(r["added"]), 30)
        self.assertEqual(len(r["skipped"]), 0)
        self.assertEqual(r["total_after"], len(r["added"]))

    def test_second_load_skips_everything(self):
        """Running the loader twice is a no-op — dedup by id."""
        from demo_wardrobe import load_demo_wardrobe
        r1 = load_demo_wardrobe()
        r2 = load_demo_wardrobe()
        self.assertEqual(len(r2["added"]), 0)
        self.assertEqual(len(r2["skipped"]), len(r1["added"]))

    def test_user_items_are_preserved(self):
        """A user-added UC### item must survive a demo load."""
        # Pre-populate the user overlay with a real user item.
        with open(self.USER_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"clothing": [{"id": "UC777", "type": "top",
                                "name": "My Real Blouse", "color": "cream",
                                "formality": "smart_casual",
                                "season": ["all"], "tags": ["work"]}],
                 "shoes": [], "accessories": []},
                f,
            )
        from demo_wardrobe import load_demo_wardrobe, unload_demo_wardrobe
        load_demo_wardrobe()
        # User item still there?
        with open(self.USER_DATA_PATH) as f:
            overlay = json.load(f)
        ids = [it.get("id") for it in overlay.get("clothing", [])]
        self.assertIn("UC777", ids)

        # Unload — user item still there.
        unload_demo_wardrobe()
        with open(self.USER_DATA_PATH) as f:
            overlay = json.load(f)
        ids = [it.get("id") for it in overlay.get("clothing", [])]
        self.assertIn("UC777", ids)
        # And every DM-* gone.
        dm_left = [i for i in ids if str(i).startswith("DM-")]
        self.assertEqual(dm_left, [])

    def test_unload_removes_only_dm_items(self):
        from demo_wardrobe import (
            load_demo_wardrobe, unload_demo_wardrobe, is_demo_loaded,
        )
        load_demo_wardrobe()
        self.assertTrue(is_demo_loaded())
        u = unload_demo_wardrobe()
        self.assertIsNone(u["error"])
        self.assertGreater(len(u["removed"]), 0)
        self.assertFalse(is_demo_loaded())

    def test_card_images_are_real_pngs(self):
        """Sample a generated DM-* image and verify the PNG magic header."""
        from demo_wardrobe import load_demo_wardrobe
        r = load_demo_wardrobe()
        self.assertGreater(len(r["added"]), 0)
        # The DM-T001 ivory blouse is the first record in the seed.
        sample = os.path.join(_wardrobe_images_dir(), "DM-T001.png")
        self.assertTrue(os.path.exists(sample), f"missing {sample}")
        with open(sample, "rb") as f:
            head = f.read(8)
        # PNG magic bytes.
        self.assertEqual(head, b"\x89PNG\r\n\x1a\n")

    # ── Integration with the agent's candidate pool ──────────────

    def test_demo_items_reach_agent_filter_pool(self):
        """Loaded demo items must be visible to filter_items_by_occasion."""
        from demo_wardrobe import load_demo_wardrobe
        load_demo_wardrobe()
        from wardrobe_tool import filter_items_by_occasion
        for occ in ("work", "casual", "dinner"):
            res = filter_items_by_occasion(occ, "spring")
            demo_count = sum(
                1 for i in res["clothing"]
                if (i.get("id") or "").startswith("DM-")
            )
            self.assertGreater(
                demo_count, 0,
                f"Expected demo items in the {occ!r} candidate pool, found 0.",
            )

    def test_demo_items_eligible_for_outfit(self):
        """run_agent should be ABLE to pick a demo item (not guaranteed
        to — depends on scoring — but at least one occasion should
        surface one in the recommendation)."""
        from demo_wardrobe import load_demo_wardrobe
        load_demo_wardrobe()
        from styling_agent import run_agent
        found_demo = False
        for req in ("work", "casual", "dinner", "formal"):
            r = run_agent(mode="everyday", everyday_request=req)
            if any((it.get("id") or "").startswith("DM-")
                    for it in (r.get("recommendation") or [])):
                found_demo = True
                break
        self.assertTrue(
            found_demo,
            "After load, at least one occasion should pick a DM-* item "
            "into the recommendation.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
