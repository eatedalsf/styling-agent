"""
Smoke tests for the Wearly styling agent.

Uses stdlib `unittest` — no third-party dependencies required. Pytest
will discover these automatically if installed.

Run with:
    python -m unittest tests.test_agent_smoke
or:
    python -m unittest discover tests
"""

import os
import sys
import unittest

# Make the project root importable regardless of where tests run from.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from styling_agent import run_agent  # noqa: E402


class TestAgentCalendarMode(unittest.TestCase):
    """Agent should produce a valid outfit when invoked in calendar mode."""

    @classmethod
    def setUpClass(cls):
        cls.result = run_agent(mode="calendar")

    def test_no_error(self):
        self.assertIsNone(self.result.get("error"), f"Agent error: {self.result.get('error')}")

    def test_seven_steps_recorded(self):
        self.assertEqual(len(self.result["steps"]), 7,
                         "Expected exactly 7 workflow steps in the audit trail.")

    def test_recommendation_has_items(self):
        outfit = self.result.get("recommendation", [])
        self.assertGreater(len(outfit), 0, "Agent should produce at least one outfit piece.")

    def test_reasoning_trail_populated(self):
        self.assertGreater(len(self.result.get("reasoning", [])), 0,
                           "Reasoning trail should not be empty.")

    def test_event_present(self):
        self.assertIn("event", self.result)
        self.assertIsInstance(self.result["event"], dict)

    def test_weather_present(self):
        # Weather always returns a dict (live or fallback).
        self.assertIsNotNone(self.result.get("weather"))

    def test_profile_exposed(self):
        # Required by the Streamlit color card so it can show skin tone.
        profile = self.result.get("profile")
        self.assertIsInstance(profile, dict)
        self.assertIn("skin_tone", profile)


class TestAgentEverydayMode(unittest.TestCase):
    """Everyday mode should map free-text occasions onto valid outfits."""

    def test_gym_mode_runs(self):
        r = run_agent(mode="everyday", everyday_request="gym")
        self.assertIsNone(r.get("error"))
        outfit = r.get("recommendation", [])
        # Gym pool may be small, but the agent should produce activewear.
        types = {i.get("type") for i in outfit}
        self.assertTrue(
            "activewear" in types or len(outfit) > 0,
            "Gym mode should produce at least some activewear or shoes."
        )

    def test_unknown_occasion_falls_back_to_casual(self):
        r = run_agent(mode="everyday", everyday_request="completely unknown thing")
        self.assertIsNone(r.get("error"))
        self.assertEqual(r["event"]["type"], "casual",
                         "Unknown occasion should fall back to 'casual'.")


class TestRejectAndRegenerate(unittest.TestCase):
    """The reject/regenerate flow must exclude rejected items AND surface
    the user's reason in the reasoning trail (the agent-not-chatbot moment)."""

    @classmethod
    def setUpClass(cls):
        cls.baseline = run_agent(mode="calendar")
        assert cls.baseline.get("recommendation"), "Baseline outfit must exist for this test."

    def test_rejected_item_excluded_from_regen(self):
        first = self.baseline["recommendation"][0]
        first_id = first.get("id")
        self.assertIsNotNone(first_id, "Baseline first item must have an id.")
        regen = run_agent(
            mode="calendar",
            rejected_ids=[first_id],
            rejection_reasons=[{"item_id": first_id, "item_name": first["name"],
                                "reason": "Wore it recently"}],
        )
        new_ids = [i.get("id") for i in regen.get("recommendation", [])]
        self.assertNotIn(first_id, new_ids,
                         "Rejected item should not appear in the regenerated outfit.")

    def test_rejection_reason_surfaces_in_reasoning(self):
        first = self.baseline["recommendation"][0]
        first_id = first.get("id")
        regen = run_agent(
            mode="calendar",
            rejected_ids=[first_id],
            rejection_reasons=[{"item_id": first_id, "item_name": first["name"],
                                "reason": "Too formal"}],
        )
        combined = " | ".join(regen.get("reasoning", []))
        self.assertIn("Too formal", combined,
                      "Reasoning trail must surface the user's rejection reason.")
        self.assertIn(first["name"], combined,
                      "Reasoning trail must name the rejected item.")

    def test_step4_records_exclusion_count(self):
        first_id = self.baseline["recommendation"][0].get("id")
        regen = run_agent(mode="calendar", rejected_ids=[first_id])
        step4 = next((s for s in regen["steps"] if s["step"] == 4), None)
        self.assertIsNotNone(step4)
        self.assertIn("Excluded", step4["output"],
                      "Step 4 should note that rejected items were excluded.")

    # ── Profile-version invalidation contract ────────────────────────

    def test_run_agent_stamps_profile_hash(self):
        """Every agent result must carry a profile_hash so the UI can
        detect staleness when the user changes their profile."""
        r = run_agent(mode="everyday", everyday_request="casual")
        self.assertIn("profile_hash", r)
        self.assertIsInstance(r["profile_hash"], str)
        self.assertTrue(len(r["profile_hash"]) > 0)

    def test_profile_hash_matches_current_profile(self):
        """The stamped hash equals `profile_hash(current_profile)` so
        the UI comparison is straightforward."""
        from fit_tool import profile_hash, get_fit_profile
        r = run_agent(mode="everyday", everyday_request="casual")
        current_hash = profile_hash(
            get_fit_profile().get("profile", {}) or {})
        self.assertEqual(r["profile_hash"], current_hash)

    # ── Tradeoff records contract ────────────────────────────────────

    def test_result_includes_tradeoffs_key(self):
        """Even when no tradeoffs fire, the key must exist as a list
        so the UI can iterate without a KeyError."""
        r = run_agent(mode="everyday", everyday_request="casual")
        self.assertIn("tradeoffs", r)
        self.assertIsInstance(r["tradeoffs"], list)

    def test_tradeoff_records_are_well_shaped(self):
        """If any tradeoff fires, each record must carry the four keys
        the wardrobe-gap detector and reasoning surface depend on."""
        r = run_agent(mode="everyday", everyday_request="dinner")
        for td in r.get("tradeoffs", []):
            self.assertIn("dimension", td)
            self.assertIn("severity",  td)
            self.assertIn("reason",    td)
            self.assertIn("item_id",   td)
            self.assertIn(td["dimension"],
                          ("color", "fit", "balance", "modesty"))
            self.assertIn(td["severity"], ("low", "medium", "high"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
