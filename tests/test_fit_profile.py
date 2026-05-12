"""
Tests for fit_tool.py + the fit-alignment reasoning notes in the agent
+ the body-positive language contract.

Run with:
    python -m unittest tests.test_fit_profile
"""

import os
import sys
import json
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fit_tool import (  # noqa: E402
    PROFILE_PATH,
    get_fit_profile,
    save_fit_profile,
    fit_alignment_note,
    FORBIDDEN_TOKENS,
    check_value_for_forbidden_language,
    check_reasoning_for_forbidden_language,
)


class _ProfileSnapshotMixin:
    """
    Snapshot / restore both user_profile.json AND wear_history.json across
    each test class. We touch wear_history because TestAgentFitIntegration
    runs the agent against the seed wardrobe, and stale wear-history state
    (from a prior dev exploration via the Streamlit "Wear this outfit"
    button) would steer Step 5 to different items — breaking assertions
    that look for specific reasoning notes tied to particular pieces.
    """

    @classmethod
    def setUpClass(cls):
        cls._original = None
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                cls._original = f.read()
        # Snapshot wear history too.
        try:
            from history_tool import HISTORY_PATH
            cls._history_path = HISTORY_PATH
            cls._history_original = None
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                    cls._history_original = f.read()
        except ImportError:
            cls._history_path = None
            cls._history_original = None

    @classmethod
    def tearDownClass(cls):
        if cls._original is not None:
            with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                f.write(cls._original)
        else:
            if os.path.exists(PROFILE_PATH):
                os.remove(PROFILE_PATH)
        if cls._history_path and cls._history_original is not None:
            with open(cls._history_path, "w", encoding="utf-8") as f:
                f.write(cls._history_original)

    def setUp(self):
        # Reset overlay to all-empty so tests are deterministic.
        with open(PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "modesty_preference": None,
                "comfort_needs":      [],
                "style_goals":        [],
                "highlight_features": [],
                "balance_areas":      [],
            }, f)
        # Reset wear history too — this is the test-hardening fix.
        # See note in setUpClass for context.
        if self._history_path:
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump({"history": {}}, f)


# ─────────────────────────────────────────────
# get_fit_profile: seed + overlay merge
# ─────────────────────────────────────────────

class TestGetFitProfile(_ProfileSnapshotMixin, unittest.TestCase):

    def test_seed_owner_loaded(self):
        r = get_fit_profile()
        self.assertTrue(r["success"])
        p = r["profile"]
        # The seed wardrobe.json owner is Eatedal with warm-olive skin tone.
        self.assertEqual(p["name"], "Eatedal")
        self.assertEqual(p["skin_tone"], "warm olive")
        self.assertEqual(p["body_shape"], "hourglass")

    def test_empty_overlay_does_not_override_seed(self):
        p = get_fit_profile()["profile"]
        # All overlay-only fields fall through to defaults when empty.
        self.assertIsNone(p["modesty_preference"])
        self.assertEqual(p["comfort_needs"], [])
        self.assertEqual(p["style_goals"], [])

    def test_overlay_overrides_seed(self):
        save_fit_profile({"modesty_preference": "moderate",
                          "comfort_needs": ["soft fabrics"]})
        p = get_fit_profile()["profile"]
        self.assertEqual(p["modesty_preference"], "moderate")
        self.assertEqual(p["comfort_needs"], ["soft fabrics"])
        # Seed fields untouched.
        self.assertEqual(p["name"], "Eatedal")

    def test_partial_save_keeps_other_fields(self):
        save_fit_profile({"style_goals": ["elevated", "modernized"]})
        save_fit_profile({"highlight_features": ["shoulders"]})
        p = get_fit_profile()["profile"]
        self.assertEqual(p["style_goals"], ["elevated", "modernized"])
        self.assertEqual(p["highlight_features"], ["shoulders"])

    def test_unknown_field_ignored(self):
        # Should silently drop unrecognized keys.
        r = save_fit_profile({"this_is_not_a_real_field": "xyz"})
        self.assertTrue(r["success"])


# ─────────────────────────────────────────────
# Body-positive language contract
# ─────────────────────────────────────────────

class TestForbiddenLanguage(_ProfileSnapshotMixin, unittest.TestCase):

    def test_clean_string_passes(self):
        self.assertEqual(check_value_for_forbidden_language("highlight my shoulders"), set())

    def test_corrective_verb_detected(self):
        offenders = check_value_for_forbidden_language("hide my hips")
        self.assertIn("hide", offenders)

    def test_multiple_offenders(self):
        offenders = check_value_for_forbidden_language("fix this flaw")
        self.assertIn("fix", offenders)
        self.assertIn("flaw", offenders)

    def test_list_value_scanned_recursively(self):
        offenders = check_value_for_forbidden_language(
            ["softer fabrics", "minimize my waist", "support shoulders"]
        )
        self.assertIn("minimize", offenders)

    def test_save_rejects_forbidden_input(self):
        r = save_fit_profile({"style_goals": ["hide my arms"]})
        self.assertFalse(r["success"])
        self.assertIn("body-positive", r["error"].lower())

    def test_save_accepts_clean_input(self):
        r = save_fit_profile({"style_goals": ["elevated", "feel like myself"]})
        self.assertTrue(r["success"])

    def test_reasoning_scan_passes_on_clean_trail(self):
        from styling_agent import run_agent
        result = run_agent(mode="everyday", everyday_request="work")
        offenders = check_reasoning_for_forbidden_language(result.get("reasoning", []))
        self.assertEqual(offenders, set(),
                         f"Agent reasoning trail contains forbidden language: {offenders}")

    def test_reasoning_scan_passes_with_full_profile(self):
        # Set every overlay field, then run the agent and assert clean output.
        save_fit_profile({
            "modesty_preference": "moderate",
            "comfort_needs":      ["soft fabrics"],
            "style_goals":        ["elevated", "feel like myself"],
            "highlight_features": ["shoulders", "neckline"],
            "balance_areas":      ["hips"],
        })
        from styling_agent import run_agent
        result = run_agent(mode="everyday", everyday_request="dinner")
        offenders = check_reasoning_for_forbidden_language(result.get("reasoning", []))
        self.assertEqual(offenders, set(),
                         f"Trail contains forbidden language: {offenders}")


# ─────────────────────────────────────────────
# fit_alignment_note: agent uses preferences in reasoning
# ─────────────────────────────────────────────

class TestFitAlignmentNote(unittest.TestCase):

    def test_no_profile_no_note(self):
        item = {"name": "X", "formality": "casual", "tags": ["casual"]}
        self.assertIsNone(fit_alignment_note(item, {}))

    def test_tailored_fit_alignment(self):
        item = {"name": "Black Tailored Trousers", "formality": "business",
                "tags": ["work"], "id": "C006"}
        profile = {"preferred_fit": "tailored"}
        out = fit_alignment_note(item, profile)
        self.assertIsNotNone(out)
        self.assertIn("tailored", out.lower())

    def test_style_preference_surfaces_on_versatile_pieces(self):
        item = {"name": "White Blouse", "formality": "business",
                "tags": ["work", "dinner", "versatile"], "id": "C001"}
        profile = {"style_preferences": ["classic", "elegant", "minimal"]}
        out = fit_alignment_note(item, profile)
        self.assertIsNotNone(out)
        self.assertIn("classic", out.lower())

    def test_style_goal_surfaces(self):
        item = {"name": "X", "formality": "business", "tags": ["work"], "id": "X1"}
        profile = {"style_goals": ["elevated"]}
        out = fit_alignment_note(item, profile)
        self.assertIsNotNone(out)
        self.assertIn("elevated", out.lower())


# ─────────────────────────────────────────────
# Agent integration: fit notes appear in the trail
# ─────────────────────────────────────────────

class TestAgentFitIntegration(_ProfileSnapshotMixin, unittest.TestCase):

    def test_seed_owner_style_preferences_surface_in_reasoning(self):
        # Eatedal's seed profile has classic / elegant / minimal preferences.
        # The reasoning trail should mention them on at least one versatile piece.
        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="work")
        combined = " | ".join(r.get("reasoning", []))
        self.assertIn("classic", combined.lower(),
                      "Seed style preferences should appear in the reasoning trail.")

    def test_user_style_goal_surfaces_in_reasoning(self):
        save_fit_profile({"style_goals": ["elevated"]})
        from styling_agent import run_agent
        r = run_agent(mode="everyday", everyday_request="dinner")
        combined = " | ".join(r.get("reasoning", []))
        self.assertIn("elevated", combined.lower(),
                      "User-saved style goal should appear in the reasoning trail.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
