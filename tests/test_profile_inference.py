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


class TestEndToEndInferenceFlow(unittest.TestCase):
    """
    Integration test: measurements → suggest → apply → save →
    run_agent → reasoning includes [fit-silhouette-rules#R8].

    This pins the contract that the inferred styling fields actually
    flow through the recommendation engine and surface in the
    user-visible reasoning with the correct rule citation. Without
    this test, a regression in fit_alignment_notes or save_fit_profile
    could silently break the citation chain.
    """

    BUCKETS = {
        "fuller midsection": {"bust": 36.0, "waist": 34.0, "hips": 36.0},
        "pear":              {"bust": 34.0, "waist": 28.0, "hips": 40.0},
        "hourglass":         {"bust": 36.0, "waist": 27.0, "hips": 36.0},
        "inverted-triangle": {"bust": 40.0, "waist": 30.0, "hips": 34.0},
    }

    def setUp(self):
        import fit_tool
        import tempfile
        self._original_path = fit_tool.PROFILE_PATH
        self._tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        self._tmp.close()
        fit_tool.PROFILE_PATH = self._tmp.name

    def tearDown(self):
        import fit_tool, os
        fit_tool.PROFILE_PATH = self._original_path
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def _run_pipeline(self, measurements: dict) -> dict:
        """Walk the full pipeline; return the final reasoning + profile."""
        import fit_tool
        import profile_inference
        import styling_agent

        fit_tool.reset_fit_profile_test_data()
        suggested = profile_inference.suggest_profile_from_measurements(
            measurements, {})
        updates = profile_inference.apply_suggestions(
            {}, suggested, list(suggested["suggestions"].keys()))
        save_res = fit_tool.save_fit_profile(
            {"measurements": measurements, **updates})
        self.assertTrue(save_res["success"], msg=save_res.get("error"))

        agent_out = styling_agent.run_agent(
            mode="everyday", everyday_request="work")
        reasoning = (agent_out.get("reasoning_trail")
                     or agent_out.get("reasoning") or [])
        if isinstance(reasoning, str):
            reasoning = [reasoning]
        return {
            "suggested":   suggested,
            "updates":     updates,
            "profile":     fit_tool.get_fit_profile()["profile"],
            "reasoning":   reasoning,
            "agent_out":   agent_out,
        }

    def test_full_pipeline_for_every_bucket(self):
        """For each of four shape buckets, the pipeline must:
        - produce at least preferred_fit + body_shape + highlight_features
        - persist those values verbatim
        - emit at least one reasoning line citing fit#R8 with capital R"""
        for label, meas in self.BUCKETS.items():
            with self.subTest(bucket=label):
                out = self._run_pipeline(meas)
                p = out["profile"]

                self.assertTrue(p.get("body_shape"),
                                f"{label}: body_shape was not saved")
                self.assertTrue(p.get("preferred_fit"),
                                f"{label}: preferred_fit was not saved")
                self.assertTrue(p.get("highlight_features"),
                                f"{label}: highlight_features was not saved")

                flat = "\n".join(str(l) for l in out["reasoning"])
                # Citation tag must keep capital R — earlier .capitalize()
                # corrupted it to lowercase r.
                self.assertIn(
                    "[fit-silhouette-rules#R8]", flat,
                    f"{label}: fit#R8 citation missing or lowercased "
                    f"in reasoning.\nReasoning:\n{flat}",
                )

    def test_preferred_fit_note_fires_for_every_fit_value(self):
        """Earlier the alignment note only fired for preferred_fit='tailored';
        structured / fluid / relaxed silently dropped through. This test
        pins that every fit value applied via Analyze surfaces a note."""
        seen_fits = set()
        for label, meas in self.BUCKETS.items():
            with self.subTest(bucket=label):
                out = self._run_pipeline(meas)
                pf = out["profile"].get("preferred_fit", "")
                seen_fits.add(pf)
                flat = "\n".join(str(l) for l in out["reasoning"]).lower()
                self.assertIn(
                    f"preferred {pf}", flat,
                    f"{label}: 'aligns with your preferred {pf} fit' note "
                    "missing — fit was applied but never cited.",
                )
        # Across the four buckets we should have exercised at least
        # three distinct fit values (the buckets land on tailored,
        # structured, structured, fluid → 3 distinct values).
        self.assertGreaterEqual(len(seen_fits), 3,
                                 f"Only exercised: {seen_fits}")


class TestAutoFillFromShape(unittest.TestCase):
    """save_fit_profile now auto-fills highlight_features, balance_areas,
    and preferred_fit from the R8 table whenever body_shape is set
    AND fit_profile_mode is in ('measurements', 'manual'). User-set
    values are never overwritten."""

    def setUp(self):
        import fit_tool, tempfile
        self._orig_path = fit_tool.PROFILE_PATH
        self._tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        self._tmp.close()
        fit_tool.PROFILE_PATH = self._tmp.name

    def tearDown(self):
        import fit_tool, os
        fit_tool.PROFILE_PATH = self._orig_path
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_manual_pear_auto_fills_dependent_fields(self):
        from fit_tool import save_fit_profile, get_fit_profile
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "pear",
                          "_body_shape_source": "user"})
        p = get_fit_profile()["profile"]
        self.assertEqual(set(p["highlight_features"]),
                         {"neckline", "shoulders"})
        self.assertEqual(p["balance_areas"], ["hips"])
        self.assertEqual(p["preferred_fit"], "structured")

    def test_measurements_pear_auto_fills_dependent_fields(self):
        from fit_tool import save_fit_profile, get_fit_profile
        save_fit_profile({"fit_profile_mode": "measurements",
                          "measurements": PEAR_M})
        p = get_fit_profile()["profile"]
        self.assertEqual(p["body_shape"], "pear")
        self.assertEqual(set(p["highlight_features"]),
                         {"neckline", "shoulders"})
        self.assertEqual(p["balance_areas"], ["hips"])
        self.assertEqual(p["preferred_fit"], "structured")

    def test_measurements_mode_overwrites_prior_body_shape(self):
        """Switching to new measurements predicting a different shape
        must overwrite the saved body_shape — this is the contradiction
        the user reported. Without this, a 'hourglass' left over from
        a prior session would stay even after entering pear-like
        bust/waist/hips."""
        from fit_tool import save_fit_profile, get_fit_profile
        # Start: hourglass from old measurements.
        save_fit_profile({"fit_profile_mode": "measurements",
                          "measurements": HOURGLASS_M})
        self.assertEqual(
            get_fit_profile()["profile"]["body_shape"], "hourglass")
        # Switch in pear measurements.
        save_fit_profile({"measurements": PEAR_M})
        p = get_fit_profile()["profile"]
        self.assertEqual(p["body_shape"], "pear",
                         "measurements mode must overwrite body_shape")

    def test_user_edited_dependent_fields_are_preserved(self):
        """The user explicitly sets highlight_features = ['legs'].
        Subsequent saves must NOT overwrite this with R8 defaults."""
        from fit_tool import save_fit_profile, get_fit_profile
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "hourglass",
                          "highlight_features": ["legs"]})
        p = get_fit_profile()["profile"]
        # User's pick wins over the R8 default of [waist, neckline].
        self.assertEqual(p["highlight_features"], ["legs"])

    def test_manual_mode_does_not_auto_fill_without_shape(self):
        """In manual mode with body_shape unset (the 'not sure'
        state), nothing should auto-fill into the overlay."""
        from fit_tool import save_fit_profile, _load_overlay
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": None})
        # Check the overlay, not the merged profile — the seed owner
        # ships preferred_fit="tailored" which would otherwise mask
        # the auto-fill behavior we're testing.
        ov = _load_overlay()
        self.assertFalse(ov.get("highlight_features"))
        self.assertFalse(ov.get("balance_areas"))
        self.assertFalse(ov.get("preferred_fit"))

    def test_skip_mode_does_not_auto_fill(self):
        from fit_tool import save_fit_profile, _load_overlay
        save_fit_profile({"fit_profile_mode": "skip"})
        # Even if a body_shape is later saved while in skip mode, the
        # R8 auto-fill must not run.
        save_fit_profile({"body_shape": "pear"})
        ov = _load_overlay()
        self.assertFalse(ov.get("highlight_features"))
        self.assertFalse(ov.get("balance_areas"))
        self.assertFalse(ov.get("preferred_fit"))


class TestSuggestedFitReconciliation(unittest.TestCase):
    """When the user has chosen a preferred_fit that differs from the
    R8 _suggested_fit for their body shape, both values must be
    preserved AND the recommendation reasoning must surface the blend."""

    def setUp(self):
        import fit_tool, tempfile
        self._orig_path = fit_tool.PROFILE_PATH
        self._tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        self._tmp.close()
        fit_tool.PROFILE_PATH = self._tmp.name

    def tearDown(self):
        import fit_tool, os
        fit_tool.PROFILE_PATH = self._orig_path
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_suggested_fit_round_trips(self):
        """_suggested_fit is always set from R8 when body_shape is set in
        an active mode, independent of the user's preferred_fit."""
        from fit_tool import save_fit_profile, get_fit_profile
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "pear",
                          "_body_shape_source": "user",
                          "preferred_fit": "relaxed"})
        p = get_fit_profile()["profile"]
        # User's preferred_fit preserved
        self.assertEqual(p["preferred_fit"], "relaxed")
        # R8 suggested_fit for pear is "structured"
        self.assertEqual(p["_suggested_fit"], "structured")

    def test_user_preferred_fit_not_overwritten_by_r8(self):
        """save_fit_profile must never write preferred_fit when the user
        has already chosen one, even when the R8 mapping would suggest
        a different value."""
        from fit_tool import save_fit_profile, _load_overlay
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "pear",
                          "preferred_fit": "relaxed"})
        ov = _load_overlay()
        self.assertEqual(ov.get("preferred_fit"), "relaxed",
                         "user's preferred_fit must survive R8 auto-fill")
        # And the R8 suggestion is still recorded separately
        self.assertEqual(ov.get("_suggested_fit"), "structured")

    def test_suggested_fit_wiped_on_reset(self):
        from fit_tool import save_fit_profile, reset_fit_profile_test_data, _load_overlay
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "pear"})
        # _suggested_fit should be present
        self.assertEqual(_load_overlay().get("_suggested_fit"), "structured")
        reset_fit_profile_test_data()
        ov = _load_overlay()
        self.assertFalse(ov.get("_suggested_fit"))

    def test_blend_note_appears_when_fits_differ_and_item_supports_balance(self):
        """The reasoning trail must surface the blend when:
          - user's preferred_fit ≠ R8's _suggested_fit, AND
          - the item's silhouette is structured (blazer / fit-and-flare /
            A-line / peplum / wrap), AND
          - the item earned a balance note (it targets a balance area).
        Pear's balance_areas = ['hips']; the hip silhouette signals
        include 'a-line', so an A-line skirt fires both the balance
        note and the structured-element check.
        """
        from fit_tool import fit_alignment_notes
        profile = {
            "body_shape":         "pear",
            "preferred_fit":      "relaxed",   # user
            "_suggested_fit":     "structured", # R8
            "balance_areas":      ["hips"],
            "highlight_features": ["neckline"],
        }
        item = {
            "type":      "bottom",
            "name":      "Cream A-Line Midi Skirt",
            "tags":      ["work", "smart_casual"],
            "formality": "smart_casual",
            "color":     "cream",
            "silhouette": "a-line",
        }
        notes = fit_alignment_notes(item, profile)
        joined = "\n".join(notes).lower()
        self.assertIn("blends your preferred relaxed fit", joined,
                      msg=f"got: {notes}")
        self.assertIn("[fit-silhouette-rules#r8]", joined)

    def test_blend_note_does_not_appear_when_fits_match(self):
        """When user kept the R8-suggested fit, no blend note fires —
        there's nothing to reconcile."""
        from fit_tool import fit_alignment_notes
        profile = {
            "body_shape":         "pear",
            "preferred_fit":      "structured",
            "_suggested_fit":     "structured",
            "balance_areas":      ["hips"],
        }
        item = {
            "type":      "bottom",
            "name":      "Cream A-Line Midi Skirt",
            "silhouette":"a-line",
            "formality": "smart_casual",
        }
        notes = fit_alignment_notes(item, profile)
        joined = "\n".join(notes).lower()
        self.assertNotIn("blends your preferred", joined)


class TestFitProfileMode(unittest.TestCase):
    """The fit_profile_mode field controls which Profile UI path renders.
    It must round-trip through save_fit_profile, be wiped by
    reset_fit_profile_test_data, and gate the auto-fill of body_shape
    from measurements when the user is in 'manual' mode."""

    def setUp(self):
        import fit_tool, tempfile
        self._orig_path = fit_tool.PROFILE_PATH
        self._tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        self._tmp.close()
        fit_tool.PROFILE_PATH = self._tmp.name

    def tearDown(self):
        import fit_tool, os
        fit_tool.PROFILE_PATH = self._orig_path
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_mode_round_trips(self):
        from fit_tool import save_fit_profile, get_fit_profile
        for mode in ("measurements", "manual", "skip"):
            r = save_fit_profile({"fit_profile_mode": mode})
            self.assertTrue(r["success"], msg=r.get("error"))
            p = get_fit_profile()["profile"]
            self.assertEqual(p["fit_profile_mode"], mode)

    def test_reset_wipes_mode(self):
        from fit_tool import save_fit_profile, reset_fit_profile_test_data
        from fit_tool import _load_overlay
        save_fit_profile({"fit_profile_mode": "measurements",
                          "measurements": {"bust": 36, "waist": 27,
                                            "hips": 36}})
        r = reset_fit_profile_test_data()
        self.assertTrue(r["success"])
        overlay = _load_overlay()
        self.assertFalse(overlay.get("fit_profile_mode"))
        self.assertFalse(overlay.get("measurements"))

    def test_manual_mode_does_not_overwrite_body_shape_from_measurements(self):
        """The classic contradiction the redesign prevents: user picks
        'pear' in manual mode, then measurements happen to be saved
        (e.g. left over from a previous session); the prediction
        would say 'hourglass'. In manual mode, body_shape must stay
        'pear', not get overwritten."""
        from fit_tool import save_fit_profile, get_fit_profile
        # Pretend the user is in manual mode and picked pear.
        save_fit_profile({"fit_profile_mode": "manual",
                          "body_shape": "pear",
                          "_body_shape_source": "user"})
        # Now add measurements that predict hourglass (36/27/36).
        save_fit_profile({"measurements": HOURGLASS_M})
        p = get_fit_profile()["profile"]
        # body_shape must still be the user's pear choice.
        self.assertEqual(p["body_shape"], "pear")

    def test_measurements_mode_auto_fills_body_shape(self):
        """In measurements mode, the auto-fill must still work — that's
        the whole point of that path."""
        from fit_tool import save_fit_profile, get_fit_profile
        save_fit_profile({"fit_profile_mode": "measurements",
                          "measurements": HOURGLASS_M})
        p = get_fit_profile()["profile"]
        self.assertEqual(p["body_shape"], "hourglass")
        self.assertEqual(p["_body_shape_source"], "auto")


class TestSuggestFromShape(unittest.TestCase):
    """The manual-mode entry point: given a body-shape string directly
    (not measurements), produce the same shape of suggestions with
    fit#R8 cited and labeled 'based-on-selection'."""

    def test_hourglass_returns_documented_suggestions(self):
        from profile_inference import suggest_profile_from_shape
        out = suggest_profile_from_shape("hourglass", {})
        self.assertTrue(out["available"])
        self.assertEqual(out["source"], "manual")
        s = out["suggestions"]
        self.assertEqual(s["body_shape"]["value"], "hourglass")
        self.assertEqual(s["body_shape"]["confidence"], "user-selected")
        self.assertEqual(set(s["highlight_features"]["values"]),
                         {"waist", "neckline"})
        self.assertEqual(s["preferred_fit"]["value"], "tailored")
        # Every suggestion cites fit#R8.
        for sug in s.values():
            self.assertEqual(sug["rule_ref"], "fit#R8")
        # Every suggestion is labeled 'based-on-selection' (or
        # 'user-selected' for body_shape).
        for fkey in ("highlight_features", "balance_areas", "preferred_fit"):
            if fkey in s:
                self.assertEqual(s[fkey]["confidence"],
                                 "based-on-selection")

    def test_pear_alias_triangle_normalizes(self):
        from profile_inference import suggest_profile_from_shape
        out = suggest_profile_from_shape("triangle", {})
        self.assertTrue(out["available"])
        self.assertEqual(out["suggestions"]["body_shape"]["value"], "pear")

    def test_apple_alias_fuller_midsection_normalizes(self):
        from profile_inference import suggest_profile_from_shape
        for alias in ("fuller midsection", "apple/fuller midsection",
                      "apple (round midsection)"):
            with self.subTest(alias=alias):
                out = suggest_profile_from_shape(alias, {})
                self.assertTrue(out["available"])
                self.assertEqual(out["suggestions"]["body_shape"]["value"],
                                 "apple")

    def test_not_sure_returns_unavailable(self):
        from profile_inference import suggest_profile_from_shape
        out = suggest_profile_from_shape("not sure", {})
        self.assertFalse(out["available"])
        self.assertEqual(out["suggestions"], {})

    def test_empty_returns_unavailable_with_prompt(self):
        from profile_inference import suggest_profile_from_shape
        out = suggest_profile_from_shape("", {})
        self.assertFalse(out["available"])
        joined = " ".join(out.get("notes", []))
        self.assertIn("Pick", joined)

    def test_body_positive_language_in_all_shapes(self):
        from profile_inference import suggest_profile_from_shape
        from fit_tool import check_reasoning_for_forbidden_language
        for shape in ("hourglass", "pear", "rectangle",
                       "inverted triangle", "apple"):
            with self.subTest(shape=shape):
                out = suggest_profile_from_shape(shape, {})
                blobs = list(out.get("notes", []))
                for sug in out.get("suggestions", {}).values():
                    for k in ("reason", "value"):
                        v = sug.get(k)
                        if isinstance(v, str):
                            blobs.append(v)
                    blobs.extend(sug.get("values") or [])
                self.assertEqual(
                    check_reasoning_for_forbidden_language(blobs), set(),
                    f"forbidden language in shape={shape}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
