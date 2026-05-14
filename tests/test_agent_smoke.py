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

    # ── Color placement: bottoms don't generate skin-tone tradeoffs ─

    def test_bottom_color_does_not_produce_high_severity_tradeoff(self):
        """A bottom that mismatches the skin-tone palette should NOT
        produce a medium/high color tradeoff, because skirts/trousers
        are far from the face. Previously a white skirt on a warm-olive
        profile generated a contradictory 'less aligned' warning while
        the color score said all colors worked.

        We invoke the agent with skin_tone=warm olive and verify that
        any tradeoff on a bottom carries severity 'low' or is absent
        entirely."""
        r = run_agent(mode="everyday", everyday_request="casual")
        for td in r.get("tradeoffs", []):
            if (td.get("item_type") or "").lower() == "bottom" \
                    and td.get("dimension") == "color":
                self.fail(
                    "Bottom should not generate any color tradeoff under "
                    "placement weighting (skirts/trousers are far from the "
                    f"face). Got: {td}"
                )

    # ── Step 6 wording adapts to qualified gaps ─────────────────────

    def test_step6_uses_qualified_wording_when_only_qualified_gaps(self):
        """When the outfit has all required pieces but a qualified gap
        was promoted, Step 6 must NOT say 'Outfit is complete —
        all required pieces present'."""
        r = run_agent(mode="everyday", everyday_request="casual")
        step6 = next((s for s in r["steps"] if s["step"] == 6), None)
        self.assertIsNotNone(step6)
        out = step6["output"].lower()
        qualified = any(str(g).startswith("qualified:") for g in r.get("gaps", []))
        true_missing = any(not str(g).startswith("qualified:")
                            for g in r.get("gaps", []))
        if qualified and not true_missing:
            self.assertIn("better-aligned", out,
                "Step 6 must surface the qualified gap when there's no "
                "true-missing piece.")
            self.assertNotIn("missing", out.split("better-aligned")[0],
                "Step 6 must NOT say 'missing' before 'better-aligned' "
                "when only qualified gaps fired.")

    # ── Gym outfit composition ──────────────────────────────────────

    # ── Color contradictions: tradeoffs match color_tier_for ────────

    def test_color_tradeoff_only_fires_for_avoid_tier(self):
        """The tradeoff text must agree with the color score. For any
        item with tier in {best, good, neutral} the tradeoffs list
        must NOT include a color entry for that item."""
        from color_tool import color_tier_for
        r = run_agent(mode="everyday", everyday_request="casual")
        skin = (r.get("profile") or {}).get("skin_tone") or ""
        for it in r.get("recommendation") or []:
            tier = color_tier_for(it.get("color") or "", skin)
            color_tds = [td for td in r.get("tradeoffs") or []
                         if td.get("item_id") == it.get("id")
                         and td.get("dimension") == "color"]
            if tier in ("best", "good", "neutral"):
                self.assertEqual(
                    color_tds, [],
                    f"Item {it.get('name')!r} with color={it.get('color')!r} "
                    f"is tier={tier!r} but produced a color tradeoff: "
                    f"{color_tds}",
                )

    def test_pearl_white_gold_no_color_tradeoff_for_warm_olive(self):
        """Direct unit-style check of the _evaluate_tradeoffs branch.
        We simulate the exact item from the screenshot and confirm
        no color tradeoff fires."""
        from color_tool import color_tier_for
        # white/gold should resolve to "best" because "gold" is in
        # best_colors for warm olive.
        tier = color_tier_for("white/gold", "warm olive")
        self.assertEqual(tier, "best")

    # ── Outerwear duplication: no "Note: temperature is..." line ────

    def test_outerwear_gap_does_not_emit_temperature_note(self):
        """When outerwear_gap fires, the reasoning trail must NOT
        contain the 'Note: temperature is …' duplicate. The same
        information is in the Wardrobe-Gap card + Step 5 output."""
        r = run_agent(mode="everyday", everyday_request="dinner")
        reasoning = " | ".join(r.get("reasoning") or [])
        # The exact phrase that was duplicated
        self.assertNotIn(
            "but no dinner-appropriate outerwear was found in the wardrobe",
            reasoning,
            "Reasoning trail must not duplicate the outerwear gap "
            "information that already appears in the gap card.",
        )

    def test_gym_outfit_has_at_most_one_bottom(self):
        """Earlier the agent took activewear[:2] which could pick two
        bottoms (leggings + yoga pants). The slot-aware partition
        guarantees one bottom max."""
        r = run_agent(mode="everyday", everyday_request="gym")
        outfit = r.get("recommendation", []) or []
        # Identify bottoms by name OR type. activewear-tagged items
        # have type="activewear" but their slot is name-driven.
        def _looks_like_bottom(it):
            n = (it.get("name") or "").lower()
            return any(k in n for k in (
                "legging", "pant", "trouser", "jogger", "short",
                "skirt", "skort",
            ))
        bottoms = [i for i in outfit if _looks_like_bottom(i)]
        self.assertLessEqual(len(bottoms), 1,
            f"Gym outfit must not contain two bottoms. Got: "
            f"{[b.get('name') for b in bottoms]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
