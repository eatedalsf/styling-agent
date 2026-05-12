"""
Tests for history_tool.py + the wear-history tie-breaker in the agent.

Each test class snapshot-and-restores wear_history.json so the suite
stays idempotent and never pollutes the real demo data.

Run with:
    python -m unittest tests.test_wear_history
"""

import os
import sys
import json
import unittest
from datetime import date, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from history_tool import (  # noqa: E402
    HISTORY_PATH,
    get_history,
    record_wear,
    get_freshness,
    days_since_last_worn,
    reset_history,
)


class _HistorySnapshotMixin:
    """Snapshot / restore wear_history.json around tests."""

    @classmethod
    def setUpClass(cls):
        cls._original = None
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                cls._original = f.read()

    @classmethod
    def tearDownClass(cls):
        if cls._original is not None:
            with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                f.write(cls._original)
        else:
            if os.path.exists(HISTORY_PATH):
                os.remove(HISTORY_PATH)

    def setUp(self):
        reset_history()


# ─────────────────────────────────────────────
# get_history / record_wear
# ─────────────────────────────────────────────

class TestRecordWear(_HistorySnapshotMixin, unittest.TestCase):

    def test_empty_history_on_fresh_install(self):
        r = get_history()
        self.assertTrue(r["success"])
        self.assertEqual(r["history"], {})

    def test_record_single_item(self):
        r = record_wear(["C001"], event_name="Team Meeting")
        self.assertTrue(r["success"])
        self.assertEqual(r["recorded_count"], 1)
        h = get_history()["history"]
        self.assertIn("C001", h)
        self.assertEqual(h["C001"]["worn_count"], 1)
        self.assertEqual(h["C001"]["last_event"], "Team Meeting")
        self.assertEqual(h["C001"]["last_worn_date"], date.today().isoformat())

    def test_record_multiple_items_at_once(self):
        record_wear(["C001", "C006", "S001"], event_name="Dinner")
        h = get_history()["history"]
        for iid in ("C001", "C006", "S001"):
            self.assertIn(iid, h)
            self.assertEqual(h[iid]["worn_count"], 1)

    def test_record_increments_count(self):
        record_wear(["C001"])
        record_wear(["C001"])
        record_wear(["C001"])
        h = get_history()["history"]
        self.assertEqual(h["C001"]["worn_count"], 3)

    def test_record_with_explicit_date(self):
        record_wear(["C001"], when="2026-01-15")
        h = get_history()["history"]
        self.assertEqual(h["C001"]["last_worn_date"], "2026-01-15")

    def test_record_empty_list_does_nothing(self):
        r = record_wear([])
        self.assertTrue(r["success"])
        self.assertEqual(r["recorded_count"], 0)
        self.assertEqual(get_history()["history"], {})

    def test_record_drops_falsy_ids(self):
        r = record_wear([None, "", "C001"])
        self.assertEqual(r["recorded_count"], 1)
        h = get_history()["history"]
        self.assertEqual(list(h.keys()), ["C001"])

    def test_malformed_history_falls_back_to_empty(self):
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json")
        r = get_history()
        self.assertTrue(r["success"])
        self.assertEqual(r["history"], {})
        self.assertIn("unreadable", (r.get("error") or "").lower())


# ─────────────────────────────────────────────
# get_freshness math
# ─────────────────────────────────────────────

class TestFreshnessMath(_HistorySnapshotMixin, unittest.TestCase):

    def test_never_worn_is_max_freshness(self):
        self.assertEqual(get_freshness("never_seen_id"), 1.0)

    def test_empty_id_is_max_freshness(self):
        self.assertEqual(get_freshness(""), 1.0)

    def test_recently_worn_loses_freshness(self):
        record_wear(["C001"])  # default `when` is today
        f = get_freshness("C001")
        self.assertLess(f, 1.0)
        self.assertGreaterEqual(f, 0.4)

    def test_floor_is_0_40(self):
        # Wear it 20 times today. Frequency penalty caps at 4 → -0.25.
        # Recency penalty fires → another -0.25. Total: 0.5. Floor: 0.4.
        for _ in range(20):
            record_wear(["C001"])
        self.assertGreaterEqual(get_freshness("C001"), 0.4)
        self.assertLessEqual(get_freshness("C001"), 0.5)

    def test_long_ago_recency_penalty_lifts(self):
        # Worn once 30 days ago — only the frequency penalty applies.
        long_ago = (date.today() - timedelta(days=30)).isoformat()
        record_wear(["C001"], when=long_ago)
        f = get_freshness("C001")
        # Expected: 1.0 - 0.25 * (1/4) = 0.9375
        self.assertAlmostEqual(f, 0.9375, places=3)

    def test_days_since_last_worn(self):
        when = (date.today() - timedelta(days=7)).isoformat()
        record_wear(["C001"], when=when)
        self.assertEqual(days_since_last_worn("C001"), 7)
        self.assertIsNone(days_since_last_worn("never_seen_id"))


# ─────────────────────────────────────────────
# Agent integration: the tie-breaker visibly affects outfit + reasoning
# ─────────────────────────────────────────────

class TestAgentFreshnessTieBreaker(_HistorySnapshotMixin, unittest.TestCase):

    def test_baseline_outfit_with_no_history(self):
        # Sanity: agent runs and includes White Button-Down Blouse as the top
        # (it's the first work-tagged top in the wardrobe seed file).
        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="work")
        self.assertIsNone(r.get("error"))
        names = [i["name"] for i in r["recommendation"]]
        self.assertIn("White Button-Down Blouse", names)

    def test_recently_worn_top_yields_to_fresher_alternative(self):
        # White Button-Down (C001) is the default work top. If we mark it
        # worn 3 times today, its freshness drops below the Black Fitted
        # Turtleneck (C002) which is ALSO work-tagged. The agent should
        # pick a different top.
        record_wear(["C001"], when=date.today().isoformat())
        record_wear(["C001"], when=date.today().isoformat())
        record_wear(["C001"], when=date.today().isoformat())

        from styling_agent import run_agent
        # Use everyday "work" with a season the C002 turtleneck covers (fall/winter).
        # We can't control season directly, but the agent reads weather. Most days
        # this maps to fall or spring; the work-tagged tops other than C001 are
        # C002 (fall/winter), C003 (Terracotta Silk — spring/fall — also work?
        # actually only dinner/casual/evening), and C005 (blush wrap — work/dinner).
        r = run_agent(mode="everyday", everyday_request="work")
        chosen_top_ids = [i["id"] for i in r["recommendation"] if i.get("type") == "top"]
        self.assertNotEqual(chosen_top_ids[:1], ["C001"],
                            "Agent should pick a fresher top, not the just-worn one.")

    def test_reasoning_trail_surfaces_freshness_note(self):
        # Wear C006 (Black Tailored Trousers) repeatedly today. The agent
        # picks it anyway because nothing else is work-tagged + season-fit,
        # AND surfaces a "you've worn this recently" note.
        for _ in range(4):
            record_wear(["C006"])

        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="work")
        combined = " | ".join(r.get("reasoning", []))
        # When there's no alternative, the recently-worn item is still chosen
        # and the trail must explain why it's there despite being recent.
        ids = [i["id"] for i in r["recommendation"]]
        if "C006" in ids:
            self.assertIn("worn", combined.lower())
            self.assertIn("Black Tailored Trousers", combined)

    def test_long_unworn_note_surfaces(self):
        # Mark an item worn 60 days ago. When the agent picks it back up,
        # the reasoning trail should surface "haven't worn ... in N days".
        long_ago = (date.today() - timedelta(days=60)).isoformat()
        record_wear(["C006"], when=long_ago)

        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="work")
        combined = " | ".join(r.get("reasoning", []))
        ids = [i["id"] for i in r["recommendation"]]
        if "C006" in ids:
            self.assertIn("haven't worn", combined.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
