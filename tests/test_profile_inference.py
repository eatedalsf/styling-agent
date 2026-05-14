"""
Tests for profile_inference — the measurement → styling-suggestion engine.

The module's contract (per skills/wearly-styling-agent/fit-silhouette-rules.md §R8):
  * suggestions are preference-based, never prescriptive
  * suggestions cite fit#R8 by rule slug
  * user-confirmed profile fields are never overwritten silently
  * body-positive vocabulary only (no hide / fix / minimize / correct / flaw / slimming)
  * style_goals and comfort_needs are NEVER inferred from measurements
  * apply_suggestions() returns empty when nothing is checked

These tests pin those behaviors so the rule is enforceable in CI.
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


from profile_inference import (
    apply_suggestions,
    suggest_profile_from_measurements,
)
from fit_tool import (
    FORBIDDEN_TOKENS,
    check_reasoning_for_forbidden_language,
    check_value_for_forbidden_language,
)
import rule_refs


# ─────────────────────────────────────────────────────────────────────
# Fixtures — measurement sets that map to known shape categories per
# fit_tool.predict_body_shape heuristic boundaries.
# ─────────────────────────────────────────────────────────────────────

# Hourglass: |bust - hips| ≤ 2 AND waist_def ≥ 8.
HOURGLASS_M = {"bust": 36.0, "waist": 27.0, "hips": 36.0}

# Pear: hips - bust ≥ 2, waist < hips.
PEAR_M = {"bust": 34.0, "waist": 28.0, "hips": 40.0}

# Inverted triangle: bust - hips ≥ 2, waist < bust.
INVERTED_M = {"bust": 40.0, "waist": 30.0, "hips": 34.0}

# Apple-ish proportions: fit_tool currently classifies this as rectangle
# (since predict_body_shape doesn't have an "apple" branch); we use it
# here to verify rectangle-bucket suggestions are still grounded.
APPLE_LIKE_M = {"bust": 36.0, "waist": 34.0, "hips": 36.0}


# ─────────────────────────────────────────────────────────────────────


class TestShapeMapping(unittest.TestCase):
    """Each documented shape must produce suggestions that match the R8
    table verbatim, with fit#R8 cited."""

    def test_hourglass_maps_to_documented_suggestions(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        self.assertTrue(out["available"])
        s = out["suggestions"]
        self.assertEqual(s["body_shape"]["value"], "hourglass")
        self.assertEqual(s["body_shape"]["rule_ref"], "fit#R8")
        # R8 hourglass row: highlight waist + neckline.
        self.assertEqual(set(s["highlight_features"]["values"]),
                         {"waist", "neckline"})
        # R8 hourglass row: already balanced, so no balance_areas suggestion.
        self.assertNotIn("balance_areas", s)
        # R8 hourglass row: tailored / fitted / structured.
        self.assertEqual(s["preferred_fit"]["value"], "tailored")

    def test_pear_maps_to_documented_suggestions(self):
        out = suggest_profile_from_measurements(PEAR_M, {})
        s = out["suggestions"]
        self.assertEqual(s["body_shape"]["value"], "pear")
        self.assertEqual(set(s["highlight_features"]["values"]),
                         {"neckline", "shoulders"})
        # Pear balances hips via upper-body interest — surfaced as "hips"
        # in the balance_areas suggestion (the *intent* is upper-body
        # emphasis, but the field stores the area being balanced).
        self.assertEqual(s["balance_areas"]["values"], ["hips"])
        self.assertEqual(s["preferred_fit"]["value"], "structured")

    def test_inverted_triangle_maps_to_documented_suggestions(self):
        out = suggest_profile_from_measurements(INVERTED_M, {})
        s = out["suggestions"]
        self.assertEqual(s["body_shape"]["value"], "inverted triangle")
        self.assertEqual(set(s["highlight_features"]["values"]),
                         {"waist", "hips", "legs"})
        self.assertEqual(s["balance_areas"]["values"], ["shoulders"])
        self.assertEqual(s["preferred_fit"]["value"], "fluid")

    def test_apple_like_measurements_route_to_rectangle_bucket(self):
        """fit_tool.predict_body_shape currently buckets these into
        'rectangle'; the suggestions for that bucket are still valid
        and grounded in R8."""
        out = suggest_profile_from_measurements(APPLE_LIKE_M, {})
        s = out["suggestions"]
        # The shape category may be "rectangle" given the bust/hip
        # similarity and small waist_def, but the suggestions are still
        # documented in R8.
        self.assertIn(s["body_shape"]["value"], {"rectangle", "athletic"})
        if s["body_shape"]["value"] == "rectangle":
            self.assertEqual(s["balance_areas"]["values"], ["waist"])


class TestRuleCitations(unittest.TestCase):
    """Every suggestion must cite fit#R8, and fit#R8 must be a known slug."""

    def test_every_suggestion_carries_rule_ref(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        for fkey, sug in out["suggestions"].items():
            with self.subTest(field=fkey):
                self.assertIn("rule_ref", sug)
                self.assertEqual(sug["rule_ref"], "fit#R8")

    def test_fitR8_is_registered_in_rule_refs(self):
        self.assertTrue(rule_refs.is_valid_slug("fit#R8"))
        cite = rule_refs.cite("fit#R8")
        self.assertIn("fit-silhouette-rules", cite)
        self.assertIn("R8", cite)


class TestUserChoicesPreserved(unittest.TestCase):
    """Suggestions surface user-locked badges and never auto-overwrite."""

    def test_user_locked_body_shape_is_flagged_not_overwritten(self):
        profile = {
            "body_shape": "apple",
            "_body_shape_source": "user",
            "preferred_fit": "relaxed",
            "highlight_features": ["legs"],
        }
        out = suggest_profile_from_measurements(HOURGLASS_M, profile)
        bs = out["suggestions"]["body_shape"]
        self.assertTrue(bs["user_locked"])
        self.assertEqual(bs["current"], "apple")
        # The suggested value is still shown so the user can compare.
        self.assertEqual(bs["value"], "hourglass")

        pf = out["suggestions"]["preferred_fit"]
        self.assertTrue(pf["user_locked"])
        self.assertEqual(pf["current"], "relaxed")

        hf = out["suggestions"]["highlight_features"]
        self.assertTrue(hf["user_locked"])
        self.assertEqual(hf["current"], ["legs"])

    def test_apply_suggestions_returns_empty_when_nothing_checked(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        updates = apply_suggestions({}, out, fields_to_apply=[])
        self.assertEqual(updates, {})

        updates_none = apply_suggestions({}, out, fields_to_apply=None)
        self.assertEqual(updates_none, {})

    def test_apply_suggestions_only_applies_checked_fields(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        updates = apply_suggestions({}, out, fields_to_apply=["body_shape"])
        self.assertEqual(updates, {"body_shape": "hourglass"})
        self.assertNotIn("highlight_features", updates)
        self.assertNotIn("preferred_fit", updates)

    def test_apply_suggestions_unions_highlight_with_existing(self):
        """Highlight / balance lists are unioned, never replaced — the
        user's existing choices survive an Apply."""
        profile = {"highlight_features": ["legs"]}
        out = suggest_profile_from_measurements(HOURGLASS_M, profile)
        updates = apply_suggestions(
            profile, out, fields_to_apply=["highlight_features"],
        )
        # legs (existing) preserved; waist + neckline (suggested) added.
        self.assertIn("legs",     updates["highlight_features"])
        self.assertIn("waist",    updates["highlight_features"])
        self.assertIn("neckline", updates["highlight_features"])


class TestBodyPositiveLanguage(unittest.TestCase):
    """fit#R1 contract: no forbidden tokens in any suggestion copy."""

    def test_suggestion_reasons_are_body_positive(self):
        for fixture_name, m in [
            ("hourglass", HOURGLASS_M),
            ("pear",      PEAR_M),
            ("inverted",  INVERTED_M),
            ("apple-like", APPLE_LIKE_M),
        ]:
            out = suggest_profile_from_measurements(m, {})
            # Collect every string the inference produces.
            blobs = list(out.get("notes", []))
            for sug in out.get("suggestions", {}).values():
                for k in ("reason", "value"):
                    v = sug.get(k)
                    if isinstance(v, str):
                        blobs.append(v)
                vs = sug.get("values") or []
                blobs.extend(vs)
            offenders = check_reasoning_for_forbidden_language(blobs)
            self.assertEqual(
                offenders, set(),
                f"Forbidden language in {fixture_name} suggestions: {offenders}",
            )

    def test_suggested_values_pass_save_screen(self):
        """save_fit_profile uses check_value_for_forbidden_language on
        every value. The values we produce must pass that screen."""
        out = suggest_profile_from_measurements(PEAR_M, {})
        updates = apply_suggestions(
            {}, out,
            fields_to_apply=list(out["suggestions"].keys()),
        )
        for k, v in updates.items():
            offenders = check_value_for_forbidden_language(v)
            self.assertEqual(
                offenders, set(),
                f"Value for {k!r} contains forbidden language: {offenders}",
            )


class TestUnsupportedFields(unittest.TestCase):
    """style_goals and comfort_needs are never inferred — R8 is explicit."""

    def test_style_goals_not_inferred(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        self.assertNotIn("style_goals", out["suggestions"])
        # And the user is told why.
        joined = " ".join(out.get("notes", [])).lower()
        self.assertIn("style goals", joined)

    def test_comfort_needs_not_inferred(self):
        out = suggest_profile_from_measurements(PEAR_M, {})
        self.assertNotIn("comfort_needs", out["suggestions"])


class TestInsufficientMeasurements(unittest.TestCase):
    """Missing bust / waist / hips → no suggestions, no crash."""

    def test_empty_measurements_returns_unavailable(self):
        out = suggest_profile_from_measurements({}, {})
        self.assertFalse(out["available"])
        self.assertEqual(out["suggestions"], {})
        self.assertIn("bust",  out["missing"])
        self.assertIn("waist", out["missing"])
        self.assertIn("hips",  out["missing"])

    def test_only_height_returns_unavailable(self):
        out = suggest_profile_from_measurements({"height": 65.0}, {})
        self.assertFalse(out["available"])

    def test_none_measurements_does_not_crash(self):
        out = suggest_profile_from_measurements(None, None)
        self.assertFalse(out["available"])
        self.assertEqual(out["suggestions"], {})


class TestResetFitProfileTestData(unittest.TestCase):
    """The scoped reset wipes ONLY fit-profile fields. Wardrobe, wishlist,
    calendar, routine, wear history, and favorite stores live in other
    files and must NEVER be touched."""

    def setUp(self):
        import fit_tool
        self._original_path = fit_tool.PROFILE_PATH
        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        self._tmp.close()
        fit_tool.PROFILE_PATH = self._tmp.name
        # Seed with a mix of fields that should and should NOT be wiped.
        fit_tool.save_fit_profile({
            "name":               "Test User",          # KEEP
            "skin_tone":          "warm olive",          # KEEP
            "style_preferences":  ["classic"],          # KEEP
            "modesty_preference": "moderate",           # KEEP
            "comfort_needs":      ["soft fabrics"],     # KEEP
            "style_goals":        ["elevated"],         # KEEP
            "preferred_fit":      "tailored",           # WIPE
            "highlight_features": ["waist"],            # WIPE
            "balance_areas":      ["hips"],             # WIPE
            "measurements":       {"bust": 36.0,
                                    "waist": 27.0,
                                    "hips":  36.0},     # WIPE
        })

    def tearDown(self):
        import fit_tool, os
        fit_tool.PROFILE_PATH = self._original_path
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_reset_clears_fit_fields_and_keeps_user_expression(self):
        from fit_tool import reset_fit_profile_test_data, _load_overlay
        before = _load_overlay()
        # Sanity — fit fields populated before reset.
        self.assertTrue(before.get("measurements"))
        self.assertTrue(before.get("highlight_features"))
        self.assertTrue(before.get("balance_areas"))
        self.assertTrue(before.get("preferred_fit"))

        r = reset_fit_profile_test_data()
        self.assertTrue(r["success"], msg=r.get("error"))

        after = _load_overlay()
        # WIPED — value must be empty/None.
        self.assertFalse(after.get("measurements"),
                         msg=f"measurements not cleared: {after.get('measurements')!r}")
        self.assertFalse(after.get("preferred_fit"))
        self.assertFalse(after.get("highlight_features"))
        self.assertFalse(after.get("balance_areas"))
        self.assertFalse(after.get("body_shape"))
        self.assertFalse(after.get("_body_shape_source"))
        # KEPT — user-expression fields untouched.
        self.assertEqual(after.get("name"),               "Test User")
        self.assertEqual(after.get("skin_tone"),          "warm olive")
        self.assertEqual(after.get("style_preferences"),  ["classic"])
        self.assertEqual(after.get("modesty_preference"), "moderate")
        self.assertEqual(after.get("comfort_needs"),      ["soft fabrics"])
        self.assertEqual(after.get("style_goals"),        ["elevated"])


class TestPreferredFitConfidence(unittest.TestCase):
    """The preferred-fit suggestion labels confidence honestly. Shape-
    table picks are 'medium'; waist-only heuristics are 'weak'."""

    def test_shape_driven_fit_is_medium(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        self.assertEqual(out["suggestions"]["preferred_fit"]["confidence"],
                         "medium")

    def test_reason_string_mentions_silhouette(self):
        out = suggest_profile_from_measurements(HOURGLASS_M, {})
        reason = out["suggestions"]["preferred_fit"]["reason"].lower()
        # The reason must explain WHY — at minimum mention the shape.
        self.assertTrue(
            "hourglass" in reason or "silhouette" in reason or "proportion" in reason,
            f"Preferred-fit reason should explain its basis: {reason!r}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
