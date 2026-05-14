"""
profile_inference.py — measurement-grounded styling-profile suggestions.

This module takes a user's body measurements (bust / waist / hips and
related fields) and surfaces a small set of *preference-based* styling
suggestions: predicted body shape, areas the user *may* choose to
highlight, areas they *may* choose to balance, and a preferred fit
hint. Every suggestion is tied to a documented rule citation (see
`fit-silhouette-rules.md` R8) so the reasoning is traceable.

What this module does NOT do:
  - It does not invent styling advice. Every suggested value maps to
    the table in fit-silhouette-rules.md §R8.
  - It does not auto-apply anything. The caller (the Profile UI)
    must render the suggestions, get explicit user confirmation, and
    only then merge them into the saved profile.
  - It does not infer style_goals or comfort_needs from measurements.
    Those are personal expression and only the user can set them.
  - It never frames a body feature as a flaw. All copy uses the
    body-positive vocabulary required by fit#R1, and is screened by
    `fit_tool.check_value_for_forbidden_language` at write time.

Public API:

    from profile_inference import suggest_profile_from_measurements

    out = suggest_profile_from_measurements(measurements, current_profile)
    # out is a dict shaped like:
    # {
    #   "available":   bool,           # True iff at least one suggestion fired
    #   "missing":     [str, ...],     # measurement field names that would unlock more suggestions
    #   "suggestions": {
    #       "body_shape":         {"value": str, "confidence": str, "reason": str,
    #                              "rule_ref": "fit#R8", "user_locked": bool},
    #       "highlight_features": {"values": [str, ...], "confidence": "...",
    #                              "rule_ref": "fit#R8", "reason": "..."},
    #       "balance_areas":      {...},
    #       "preferred_fit":      {...},
    #   },
    #   "notes": [str, ...],           # framing copy ready to render in UI
    # }

Body-positive language contract:
  - "balance" means "bring into visual proportion", never "minimize".
  - "highlight" is always opt-in — the user chooses to draw attention.
  - The word "fix", "hide", "minimize", "correct", "flaw" never appear.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────
# CANONICAL MAPPING TABLE — must match fit-silhouette-rules.md §R8.
# Changing values here without updating the rule pack will break the
# documentation-integrity test.
# ─────────────────────────────────────────────────────────────────────

# Each entry: shape → (highlight_features, balance_areas, preferred_fit_options).
# Empty lists mean "no specific suggestion for this field at this shape;
# leave to user".
_SHAPE_TABLE: Dict[str, Dict[str, List[str]]] = {
    "hourglass": {
        "highlight":  ["waist", "neckline"],
        "balance":    [],                           # already balanced
        "fit":        ["tailored", "fitted", "structured"],
    },
    "pear": {
        "highlight":  ["neckline", "shoulders"],
        "balance":    ["hips"],                     # via upper-body interest
        "fit":        ["structured"],               # upper structured, lower fluid
    },
    "apple": {
        "highlight":  ["neckline", "legs", "collarbone"],
        "balance":    ["waist"],                    # midsection proportion
        "fit":        ["relaxed", "fluid"],
    },
    "rectangle": {
        "highlight":  ["collarbone", "waist", "neckline"],
        "balance":    ["waist"],                    # via waist-defining cuts
        "fit":        ["structured", "tailored"],
    },
    "inverted triangle": {
        "highlight":  ["waist", "hips", "legs"],
        "balance":    ["shoulders"],                # via lower-body interest
        "fit":        ["fluid"],                    # upper fluid, lower structured
    },
    "athletic": {
        "highlight":  [],                           # user choice
        "balance":    [],
        "fit":        [],
    },
}

# Confidence label per shape. Mirrors the structure of
# fit_tool.predict_body_shape so callers see the same word in both
# panels. Hourglass / pear / inverted triangle get "high" when the
# ratios are textbook; the inference will surface "medium" when the
# user has overridden the predicted shape but kept measurements.
_DEFAULT_CONFIDENCE = "medium"

# Weak-heuristic preferred-fit derived from waist definition.
# fit-silhouette-rules.md §R8 explicitly labels this a weak heuristic.
_WAIST_DEF_TAILORED_THRESHOLD_IN = 8.0
_WAIST_DEF_RELAXED_THRESHOLD_IN  = 4.0

# Rule citation slug for every suggestion this module returns. Kept as
# a module-level constant so callers don't have to remember it; if R8
# is ever renumbered, only this line changes.
_RULE_SLUG = "fit#R8"


# ─────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────

def suggest_profile_from_measurements(
    measurements: Optional[Dict[str, Any]],
    current_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build preference-based styling suggestions from user measurements.

    Parameters
    ----------
    measurements : dict | None
        Measurement values keyed by `fit_tool.MEASUREMENT_FIELDS` (bust,
        waist, hips, etc.), all in inches. Missing fields are fine —
        the function returns whatever subset of suggestions the
        provided fields can support.
    current_profile : dict | None
        The user's already-saved profile. Used for *display* only:
        suggestions are flagged ``user_locked=True`` when the user has
        confirmed a value for that field already, so the UI can show
        the suggestion alongside (but does not silently overwrite).

    Returns
    -------
    dict
        See module docstring for the shape. Always returns a dict —
        empty ``suggestions`` if measurements are insufficient, in
        which case ``available`` is False and ``missing`` lists the
        measurements that would unlock more inference.
    """
    measurements = measurements or {}
    current_profile = current_profile or {}

    out: Dict[str, Any] = {
        "available":   False,
        "missing":     [],
        "suggestions": {},
        "notes":       [],
    }

    # 1. Body-shape prediction — reuse the existing fit_tool function so
    #    there's only one source of truth for the heuristic.
    try:
        from fit_tool import predict_body_shape
    except Exception:
        # Defensive: profile_inference must never crash the Profile UI.
        return out

    shape_pred = predict_body_shape(measurements)
    if not shape_pred:
        # Need at least bust + waist + hips. Tell the caller what to ask for.
        present = {k for k, v in measurements.items()
                   if isinstance(v, (int, float)) and v > 0}
        for need in ("bust", "waist", "hips"):
            if need not in present:
                out["missing"].append(need)
        out["notes"].append(
            "Share bust, waist, and hip measurements to unlock "
            "preference-based styling suggestions. Every suggestion "
            "is optional — you can edit or skip any of them."
        )
        return out

    shape = shape_pred.get("shape", "athletic")
    confidence = shape_pred.get("confidence", _DEFAULT_CONFIDENCE)
    shape_reason = shape_pred.get(
        "reason",
        "Your measurements suggest this proportion category.",
    )

    out["available"] = True
    out["notes"].append(
        "These are preference-based suggestions, not a diagnosis. "
        "Wearly treats body-shape labels as industry heuristics, "
        "never a claim about your body. Review each chip and apply "
        "only what feels right — your saved choices are never "
        "overwritten without your confirmation."
    )

    # ── 1a. Body shape ──────────────────────────────────────────────
    user_shape = (current_profile.get("body_shape") or "").strip().lower()
    shape_source = current_profile.get("_body_shape_source") or ""
    user_locked_shape = bool(user_shape) and shape_source == "user"
    out["suggestions"]["body_shape"] = {
        "value":       shape,
        "confidence":  confidence,
        "reason":      shape_reason,
        "rule_ref":    _RULE_SLUG,
        "user_locked": user_locked_shape,
        "current":     user_shape or None,
    }

    # ── 2. Areas to highlight / balance, preferred fit ──────────────
    table = _SHAPE_TABLE.get(shape, _SHAPE_TABLE["athletic"])

    # 2a. Highlight features.
    highlight = list(table.get("highlight", []))
    if highlight:
        existing = [a.lower() for a in
                    (current_profile.get("highlight_features") or [])]
        out["suggestions"]["highlight_features"] = {
            "values":      highlight,
            "confidence":  confidence,
            "reason":      _highlight_reason(shape, highlight),
            "rule_ref":    _RULE_SLUG,
            "user_locked": bool(existing),
            "current":     existing or [],
        }

    # 2b. Balance areas.
    balance = list(table.get("balance", []))
    if balance:
        existing = [a.lower() for a in
                    (current_profile.get("balance_areas") or [])]
        out["suggestions"]["balance_areas"] = {
            "values":      balance,
            "confidence":  confidence,
            "reason":      _balance_reason(shape, balance),
            "rule_ref":    _RULE_SLUG,
            "user_locked": bool(existing),
            "current":     existing or [],
        }

    # 2c. Preferred fit. Combine shape-table preferences with the weak
    #     waist-definition heuristic. If the two disagree, the shape
    #     table wins (it's the stronger signal); the waist heuristic is
    #     surfaced in the reason text either way.
    fit_options = list(table.get("fit", []))
    waist_def = _waist_definition_inches(measurements)
    waist_hint = _preferred_fit_from_waist(waist_def)
    fit_value = fit_options[0] if fit_options else (waist_hint or "")
    if fit_value:
        user_fit = (current_profile.get("preferred_fit") or "").strip().lower()
        out["suggestions"]["preferred_fit"] = {
            "value":       fit_value,
            "options":     fit_options,         # alternate suggestions if the user wants to swap
            "confidence":  _fit_confidence(fit_options, waist_hint),
            "reason":      _fit_reason(shape, fit_options, waist_hint, waist_def),
            "rule_ref":    _RULE_SLUG,
            "user_locked": bool(user_fit),
            "current":     user_fit or None,
        }

    # 3. style_goals and comfort_needs are deliberately not inferred.
    #    Surface that fact in the UI copy so the user understands the
    #    boundary of what measurements can suggest.
    out["notes"].append(
        "Style goals and comfort preferences are not inferred from "
        "measurements — those are personal and only you can set them. "
        "Use the form below to share them when you're ready."
    )

    return out


# ─────────────────────────────────────────────────────────────────────
# APPLY — caller-driven merge. NEVER auto-runs.
# ─────────────────────────────────────────────────────────────────────

def apply_suggestions(
    current_profile: Dict[str, Any],
    suggestions: Dict[str, Any],
    fields_to_apply: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Merge user-approved suggestions into a profile-updates dict ready
    to pass to ``fit_tool.save_fit_profile()``.

    The caller (the UI) is responsible for collecting the user's
    explicit consent (a checkbox per chip plus the "Apply suggestions"
    button). This function does NOT decide what to apply — it only
    composes the final updates payload, so the UI's intent is always
    transparent in the resulting dict.

    Parameters
    ----------
    current_profile : dict
        The merged profile (seed + overlay) as returned by
        ``fit_tool.get_fit_profile().profile``.
    suggestions : dict
        The full result of ``suggest_profile_from_measurements`` (or
        its ``suggestions`` sub-dict — both shapes are accepted).
    fields_to_apply : list[str] | None
        Which suggestion keys the user actually checked. If None or
        empty, returns an empty updates dict (nothing to apply).

    Returns
    -------
    dict
        Updates payload, e.g. {"body_shape": "pear",
        "highlight_features": ["neckline", "shoulders"]}. Pass this
        directly to ``save_fit_profile``. May be empty when nothing
        was chosen.
    """
    if not fields_to_apply:
        return {}

    # Accept both the full result-dict and the sub-dict.
    sug = suggestions.get("suggestions", suggestions) or {}

    updates: Dict[str, Any] = {}

    if "body_shape" in fields_to_apply and "body_shape" in sug:
        updates["body_shape"] = sug["body_shape"]["value"]

    if "highlight_features" in fields_to_apply and "highlight_features" in sug:
        # Union with the user's existing choices — suggestions add to,
        # never replace, what the user has already chosen.
        existing = list(current_profile.get("highlight_features") or [])
        merged = _merge_unique(existing,
                                sug["highlight_features"]["values"])
        updates["highlight_features"] = merged

    if "balance_areas" in fields_to_apply and "balance_areas" in sug:
        existing = list(current_profile.get("balance_areas") or [])
        merged = _merge_unique(existing,
                                sug["balance_areas"]["values"])
        updates["balance_areas"] = merged

    if "preferred_fit" in fields_to_apply and "preferred_fit" in sug:
        updates["preferred_fit"] = sug["preferred_fit"]["value"]

    return updates


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────

def _waist_definition_inches(measurements: Dict[str, Any]) -> Optional[float]:
    """Return min(bust, hips) - waist in inches, or None when bust /
    waist / hips aren't all present."""
    bust  = measurements.get("bust")
    waist = measurements.get("waist")
    hips  = measurements.get("hips")
    if not all(isinstance(v, (int, float)) and v > 0
               for v in (bust, waist, hips)):
        return None
    return float(min(bust, hips) - waist)


def _preferred_fit_from_waist(waist_def: Optional[float]) -> str:
    """Weak-heuristic fit hint from waist definition. Returns an
    empty string when the heuristic is inconclusive."""
    if waist_def is None:
        return ""
    if waist_def >= _WAIST_DEF_TAILORED_THRESHOLD_IN:
        return "tailored"
    if waist_def < _WAIST_DEF_RELAXED_THRESHOLD_IN:
        return "relaxed"
    return ""


def _fit_confidence(shape_options: List[str], waist_hint: str) -> str:
    """Confidence label for the preferred-fit suggestion.

    Shape-based suggestion is the stronger signal, so we report
    'medium' (matching the body-shape prediction's typical confidence).
    Falling back to the waist-definition heuristic alone is 'weak'."""
    if shape_options:
        return "medium"
    if waist_hint:
        return "weak heuristic"
    return "low"


def _highlight_reason(shape: str, highlight: List[str]) -> str:
    """Body-positive prose explaining the highlight suggestion."""
    chips = ", ".join(highlight)
    return (
        f"For an {shape} proportion, industry styling literature "
        f"commonly suggests drawing attention to {chips} — entirely "
        "preference-based, body-positive, and editable."
    )


def _balance_reason(shape: str, balance: List[str]) -> str:
    """Body-positive prose explaining the balance suggestion. Uses
    'balance' / 'support' / 'bring into proportion' only. Never
    'minimize' or 'hide'."""
    chips = ", ".join(balance)
    return (
        f"For an {shape} proportion, industry styling literature "
        f"commonly suggests pieces that help bring {chips} into "
        "visual proportion — never to conceal, only to balance."
    )


def _fit_reason(shape: str, shape_options: List[str], waist_hint: str,
                 waist_def: Optional[float]) -> str:
    """Body-positive prose explaining the preferred-fit suggestion."""
    parts = []
    if shape_options:
        parts.append(
            f"For an {shape} proportion, {', '.join(shape_options)} "
            "fits are commonly suggested as supportive of the silhouette"
        )
    if waist_hint:
        if waist_def is not None:
            parts.append(
                f"and your waist definition (~{waist_def:.1f} in) "
                f"also leans toward a {waist_hint} cut (weak heuristic)"
            )
        else:
            parts.append(f"and a {waist_hint} cut may also suit (weak heuristic)")
    if not parts:
        return ("Preferred fit is a personal preference — Wearly has no "
                "strong suggestion from measurements alone.")
    return ". ".join(parts) + "."


def _merge_unique(existing: List[str], additions: List[str]) -> List[str]:
    """Combine two string lists case-insensitively, preserving order
    and dropping duplicates."""
    seen = {e.lower() for e in existing}
    out = list(existing)
    for a in additions:
        if a.lower() not in seen:
            out.append(a)
            seen.add(a.lower())
    return out
