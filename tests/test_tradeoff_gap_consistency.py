"""
Tradeoff / gap / scoring consistency tests.

A reviewer captured nine distinct mismatches across the Today /
Planner / Routine surfaces. This file is the regression-protection
layer for the fixes that landed in response. Each test pins one of
the contracts a future change must not break.

Tests rely on importing run_agent and the helpers directly — they
do not exercise the Streamlit UI. Every assertion targets the
result dict the UI reads, so a UI refactor cannot silently
re-introduce drift.
"""

from __future__ import annotations
import os
import sys
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _build_wardrobe(items):
    """Wrap a flat list of items into the filter_items_by_occasion
    result shape used by `styling_agent.run_agent`."""
    clothing = [i for i in items if i.get("type") in
                ("top", "bottom", "dress", "outerwear", "activewear",
                 "skirt", "pants")]
    shoes = [i for i in items if i.get("type") == "shoes"]
    accessories = [i for i in items if i.get("type") in
                   ("accessory", "scarf")]
    return {
        "success": True,
        "clothing": clothing,
        "shoes": shoes,
        "accessories": accessories,
        "error": None,
    }


def _patch_owner(profile: dict):
    """Patch the owner-profile getters so run_agent sees `profile`."""
    return mock.patch("styling_agent.get_owner_profile",
                      return_value={"success": True, "profile": profile})


def _patch_fit_profile(profile: dict):
    """Patch get_fit_profile (overlay) so the full profile is used."""
    return mock.patch("fit_tool.get_fit_profile",
                      return_value={"success": True, "profile": profile,
                                    "error": None})


def _patch_weather(temp_f: int = 72):
    """Patch the weather lookup at its import-site in styling_agent.
    The agent unpacks `weather_result["weather"]` and reads several
    keys downstream; the shape here mirrors what weather_tool.get_weather
    actually emits."""
    return mock.patch(
        "styling_agent.get_weather",
        return_value={
            "success": True,
            "source": "test",
            "in_range": True,
            "target_date": "2026-05-14",
            "weather": {
                "city": "Test",
                "temp_f": temp_f,
                "feels_like_f": temp_f,
                "condition": "Clear",
                "wind_mph": 0.0,
                "precip_chance_pct": 0,
                "layer_advice": "no extra layer needed",
                "temp_high_f": temp_f,
                "temp_low_f": temp_f,
                "fallback_reason": None,
            },
        },
    )


def _patch_history():
    return mock.patch("history_tool.get_history",
                      return_value={"success": True, "history": {}, "error": None})


def _run_with(items, profile, occasion="casual", temp=72):
    """Run the agent against a controlled wardrobe + profile."""
    import styling_agent
    with _patch_owner(profile), \
         _patch_fit_profile(profile), \
         _patch_weather(temp), \
         _patch_history(), \
         mock.patch("styling_agent.filter_items_by_occasion",
                    return_value=_build_wardrobe(items)):
        return styling_agent.run_agent(mode="everyday",
                                        everyday_request=occasion)


# ────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────

class TestReasoningGapConsistency(unittest.TestCase):
    """Fix 1: 'reveals a wardrobe gap' must NOT appear in reasoning
    when result['gaps'] is empty.

    Earlier behavior emitted that line on every tradeoff, even
    low-severity ones that never made it to result['gaps']. The
    contract now is: that exact phrasing is only used for tradeoffs
    whose item TYPE was promoted to a qualified gap.
    """

    def test_no_unpromoted_wardrobe_gap_claim(self):
        # A single low-severity tradeoff (preferred-fit "fitted"
        # against a smart_casual item is in-bucket, no tradeoff;
        # we deliberately set a single-dim low tradeoff path by
        # not setting modesty/balance).
        items = [
            {"id": "T1", "name": "Soft Tee",
             "type": "top", "color": "cream",
             "formality": "casual",
             "tags": ["casual"]},
            {"id": "B1", "name": "Denim Jeans",
             "type": "bottom", "color": "indigo",
             "formality": "casual",
             "tags": ["casual"]},
            {"id": "S1", "name": "White Sneakers",
             "type": "shoes", "color": "white",
             "formality": "casual",
             "tags": ["sneakers"]},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "body_shape": "pear",
                   "preferred_fit": "relaxed",   # matches casual → no fit tradeoff
                   "modesty_preference": ""}
        result = _run_with(items, profile, occasion="casual")
        joined = "\n".join(result.get("reasoning", []))
        gaps = result.get("gaps", [])
        if not gaps:
            self.assertNotIn(
                "reveals a wardrobe gap", joined,
                "Reasoning claimed a wardrobe gap when result['gaps'] "
                "was empty."
            )


class TestAccessoryNoFitTradeoff(unittest.TestCase):
    """Fix 2: earrings, handbags, jewelry must NOT receive
    'cut differs from preferred fit' tradeoffs."""

    def test_earrings_get_no_fit_tradeoff(self):
        items = [
            {"id": "T1", "name": "Soft Tee", "type": "top",
             "color": "cream", "formality": "casual"},
            {"id": "B1", "name": "Wide-Leg Trousers",
             "type": "bottom", "color": "navy", "formality": "casual"},
            {"id": "S1", "name": "White Sneakers", "type": "shoes",
             "color": "white", "formality": "casual",
             "tags": ["sneakers"]},
            {"id": "A1", "name": "Gold Hoop Earrings",
             "type": "accessory", "color": "gold",
             "formality": "casual"},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "preferred_fit": "structured"}
        result = _run_with(items, profile, occasion="casual")
        # Tradeoffs list must not contain a fit-dimension record
        # against the earring.
        tradeoffs = result.get("tradeoffs", [])
        earring_fit = [t for t in tradeoffs
                       if t.get("item_id") == "A1"
                       and t.get("dimension") == "fit"]
        self.assertEqual(
            [], earring_fit,
            f"Earring received fit tradeoff(s): {earring_fit}"
        )

    def test_handbag_gets_no_color_or_fit_tradeoff(self):
        items = [
            {"id": "T1", "name": "Soft Tee", "type": "top",
             "color": "cream", "formality": "casual"},
            {"id": "B1", "name": "Wide-Leg Trousers",
             "type": "bottom", "color": "navy", "formality": "casual"},
            {"id": "S1", "name": "White Sneakers", "type": "shoes",
             "color": "white", "formality": "casual"},
            # Handbag: type accessory but name contains "handbag"
            {"id": "A1", "name": "Black Leather Handbag",
             "type": "accessory", "color": "black",
             "formality": "casual"},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "preferred_fit": "structured",
                   "modesty_preference": "moderate"}
        result = _run_with(items, profile, occasion="casual")
        tradeoffs = result.get("tradeoffs", [])
        bag_tradeoffs = [t for t in tradeoffs if t.get("item_id") == "A1"]
        # Handbags should produce NO tradeoffs at all (no fit, no
        # color, no balance, no modesty).
        self.assertEqual(
            [], bag_tradeoffs,
            f"Handbag received tradeoff(s): {bag_tradeoffs}"
        )


class TestShoesUseOccasionFitNotCut(unittest.TestCase):
    """Fix 7: shoes use occasion-fit, not preferred-fit/cut."""

    def test_shoes_never_receive_fit_dimension(self):
        items = [
            {"id": "T1", "name": "Soft Tee", "type": "top",
             "color": "cream", "formality": "casual"},
            {"id": "B1", "name": "Wide-Leg Trousers",
             "type": "bottom", "color": "navy", "formality": "casual"},
            {"id": "S1", "name": "White Canvas Sneakers",
             "type": "shoes", "color": "white",
             "formality": "casual", "tags": ["sneakers", "canvas"]},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "preferred_fit": "structured"}
        result = _run_with(items, profile, occasion="casual")
        shoe_fit = [t for t in result.get("tradeoffs", [])
                    if t.get("item_id") == "S1"
                    and t.get("dimension") == "fit"]
        self.assertEqual(
            [], shoe_fit,
            f"Shoes received a fit dimension: {shoe_fit}"
        )


class TestTopDescriptorNoMidiOrLonger(unittest.TestCase):
    """Fix 4: shopping descriptor for a TOP must never say
    'midi or longer'. That phrasing is dress/skirt vocabulary."""

    def test_top_qualified_gap_descriptor_is_category_aware(self):
        # Force a top to be picked + flagged for modesty by giving the
        # ONLY top in the wardrobe a "tank top" name with a
        # moderate-modesty user.
        items = [
            {"id": "T1", "name": "Cropped Tank Top",
             "type": "top", "color": "cream", "formality": "casual",
             "tags": ["crop", "tank top"]},
            {"id": "B1", "name": "Wide-Leg Trousers",
             "type": "bottom", "color": "navy", "formality": "casual"},
            {"id": "S1", "name": "White Sneakers", "type": "shoes",
             "color": "white", "formality": "casual"},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "preferred_fit": "relaxed",
                   "modesty_preference": "moderate"}
        result = _run_with(items, profile, occasion="casual")
        suggestions = " || ".join(result.get("shopping_suggestions", []))
        if "top" in (result.get("gaps", []) or []) or \
           "qualified:top" in (result.get("gaps", []) or []):
            self.assertNotIn(
                "midi or longer", suggestions.lower(),
                "Top descriptor used dress-vocabulary 'midi or longer'. "
                f"Suggestions: {suggestions}"
            )


class TestColorPlacementImpact(unittest.TestCase):
    """Fix 3: lower-body colors (skirt / pants / leggings / shoes)
    must NOT generate color tradeoffs on their own."""

    def test_white_skirt_no_color_tradeoff_for_warm_olive(self):
        items = [
            {"id": "T1", "name": "Camel Sweater", "type": "top",
             "color": "camel", "formality": "casual"},
            {"id": "B1", "name": "White Skirt", "type": "skirt",
             "color": "white", "formality": "casual"},
            {"id": "S1", "name": "Brown Loafers", "type": "shoes",
             "color": "brown", "formality": "casual"},
        ]
        profile = {"name": "T", "skin_tone": "warm olive"}
        result = _run_with(items, profile, occasion="casual")
        bottom_color_tradeoffs = [
            t for t in result.get("tradeoffs", [])
            if t.get("item_id") == "B1" and t.get("dimension") == "color"
        ]
        self.assertEqual(
            [], bottom_color_tradeoffs,
            f"Lower-body skirt got a color tradeoff: {bottom_color_tradeoffs}"
        )


class TestKnowledgeGraphRenameInRuntimeCopy(unittest.TestCase):
    """Fix 8: runtime app.py must use 'Reasoning Graph' (not
    'Knowledge Graph') in user-facing copy. The book's renamed
    section is the Reasoning Graph."""

    def test_app_py_no_user_facing_knowledge_graph(self):
        with open(os.path.join(_ROOT, "app.py"), "r",
                   encoding="utf-8") as f:
            body = f.read()
        # Allow developer comments and KG export internals; the user-
        # visible strings (button labels, paragraph copy, captions)
        # must say "Reasoning Graph." We check for the two specific
        # known-bad strings the audit caught.
        self.assertNotIn(
            "in-book Knowledge-Graph viewer", body,
            "app.py still references the old in-book viewer name."
        )
        self.assertNotIn(
            "Read more in the **Knowledge Graph** section", body,
            "app.py still says 'Knowledge Graph' in the cross-link copy."
        )


class TestPreferredFitChangesProfileHash(unittest.TestCase):
    """Fix 5: changing preferred_fit must change profile_hash so
    the regenerate banner fires."""

    def test_relaxed_vs_structured_produce_different_hashes(self):
        from fit_tool import profile_hash
        base = {"body_shape": "pear", "skin_tone": "warm olive",
                "modesty_preference": "moderate"}
        h_relaxed    = profile_hash({**base, "preferred_fit": "relaxed"})
        h_structured = profile_hash({**base, "preferred_fit": "structured"})
        self.assertNotEqual(
            h_relaxed, h_structured,
            "profile_hash unchanged when preferred_fit toggled."
        )


class TestPreferredFitAffectsScoring(unittest.TestCase):
    """Fix 5: preferred_fit must shift the selector, not only the
    displayed text. Given a wardrobe with one casual-formality top
    and one business-formality top, switching the user from
    relaxed-preferring to structured-preferring should change which
    top wins (or produce a documented 'no better option' tradeoff)."""

    def test_structured_preference_prefers_business_when_available(self):
        items = [
            # Two tops to compete: one casual-formality, one business
            {"id": "T_CASUAL", "name": "Soft Loose Tee",
             "type": "top", "color": "cream", "formality": "casual",
             "tags": ["loose", "relaxed"]},
            {"id": "T_BIZ",    "name": "Tailored Blouse",
             "type": "top", "color": "cream", "formality": "business",
             "tags": ["structured", "tailored"]},
            {"id": "B1", "name": "Trousers", "type": "bottom",
             "color": "navy", "formality": "business"},
            {"id": "S1", "name": "Loafers", "type": "shoes",
             "color": "brown", "formality": "business",
             "tags": ["loafer"]},
        ]
        # Run #1: relaxed user
        prof_relaxed = {"name": "T", "skin_tone": "warm olive",
                        "body_shape": "pear",
                        "preferred_fit": "relaxed"}
        r_relaxed = _run_with(items, prof_relaxed, occasion="casual")
        picked_top_relaxed = next(
            (i["id"] for i in r_relaxed.get("recommendation", [])
             if i.get("type") == "top"), None
        )
        # Run #2: structured user
        prof_structured = {**prof_relaxed, "preferred_fit": "structured"}
        r_structured = _run_with(items, prof_structured, occasion="casual")
        picked_top_structured = next(
            (i["id"] for i in r_structured.get("recommendation", [])
             if i.get("type") == "top"), None
        )

        # Both picks must be present (the test wardrobe has two tops)
        self.assertIsNotNone(picked_top_relaxed)
        self.assertIsNotNone(picked_top_structured)
        # The pick should DIFFER between the two profiles, OR the
        # reasoning should explicitly mention an opportunity for a
        # better-aligned alternative. (We accept "documented" outcome
        # because some occasions may genuinely have only one suitable
        # candidate; the agent must say so in that case.)
        if picked_top_relaxed == picked_top_structured:
            joined_structured = "\n".join(
                r_structured.get("reasoning", [])
            ).lower()
            self.assertTrue(
                ("opportunity" in joined_structured or
                 "best available" in joined_structured),
                ("Same top picked for relaxed and structured profiles "
                 "but no honest 'best available' / 'opportunity' note "
                 "in the reasoning trail.")
            )


class TestFitNotesDedup(unittest.TestCase):
    """Fix 6: identical 'aligns with your preferred X fit' lines
    should appear at most once across the reasoning trail."""

    def test_fit_note_appears_at_most_once(self):
        items = [
            {"id": "T1", "name": "Relaxed Tee", "type": "top",
             "color": "cream", "formality": "casual",
             "tags": ["relaxed"]},
            {"id": "B1", "name": "Relaxed Trousers", "type": "bottom",
             "color": "navy", "formality": "casual",
             "tags": ["relaxed"]},
            {"id": "S1", "name": "Sneakers", "type": "shoes",
             "color": "white", "formality": "casual"},
        ]
        profile = {"name": "T", "skin_tone": "warm olive",
                   "preferred_fit": "relaxed"}
        result = _run_with(items, profile, occasion="casual")
        joined_lower = "\n".join(result.get("reasoning", [])).lower()
        occurrences = joined_lower.count("aligns with your preferred relaxed fit")
        self.assertLessEqual(
            occurrences, 1,
            f"'aligns with your preferred relaxed fit' appeared "
            f"{occurrences} times; expected at most 1."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
