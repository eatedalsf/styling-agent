"""
Tool 6: Fit Profile

Merges the seed owner block (in wardrobe.json) with an optional user
overlay (user_profile.json) into a single fit profile the agent reads
to personalize outfit construction.

The merged profile carries:
  - name, body_shape, skin_tone, preferred_fit, style_preferences
    (sourced from wardrobe.json — the seed wardrobe owner)
  - modesty_preference   (null | "low" | "moderate" | "high")
  - comfort_needs        (list of free-form strings: "soft fabrics", …)
  - style_goals          (list of strings: "elevated", "modernized", …)
  - highlight_features   (list of body areas to draw attention to)
  - balance_areas        (list of areas to bring into proportion)

Every overlay field is optional. The agent applies a constraint only
when the corresponding field is present and non-empty.

LANGUAGE CONTRACT: see skills/wearly-styling-agent/fit-silhouette-rules.md.
This module never outputs corrective vocabulary (hide / fix / minimize /
correct / flaw). The check_reasoning_for_forbidden_language() helper
formalizes that contract for tests + CI.
"""

from __future__ import annotations

import json
import os
import tempfile


# ─────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────

def _profile_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", "user_profile.json"),
        os.path.join(here, "user_profile.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, "user_profile.json")


def _seed_wardrobe_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", "wardrobe.json"),
        os.path.join(here, "wardrobe.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, "wardrobe.json")


PROFILE_PATH = _profile_path()
SEED_WARDROBE_PATH = _seed_wardrobe_path()


# Empty overlay used as a fallback when user_profile.json is missing or unreadable.
_EMPTY_OVERLAY = {
    "modesty_preference": None,
    "comfort_needs":      [],
    "style_goals":        [],
    "highlight_features": [],
    "balance_areas":      [],
}


# ─────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────

def _load_seed_owner() -> dict:
    """Read the owner block from wardrobe.json. Returns {} on any failure."""
    try:
        with open(SEED_WARDROBE_PATH, "r", encoding="utf-8") as f:
            seed = json.load(f)
        return dict(seed.get("owner", {}))
    except Exception:
        return {}


def _load_overlay() -> dict:
    if not os.path.exists(PROFILE_PATH):
        return dict(_EMPTY_OVERLAY)
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(_EMPTY_OVERLAY)
    overlay = dict(_EMPTY_OVERLAY)
    for k in overlay:
        if k in data:
            overlay[k] = data[k]
    return overlay


def get_fit_profile() -> dict:
    """
    Return {"success": True, "profile": <merged>, "error": None}.
    The merged profile is the seed owner dict + the user overlay, with
    overlay keys taking precedence when present. Empty / null overlay
    fields don't override seed values.
    """
    owner = _load_seed_owner()
    overlay = _load_overlay()
    merged = dict(owner)
    for k, v in overlay.items():
        if v is None:
            continue
        if isinstance(v, list) and not v:
            continue
        merged[k] = v
    # Ensure expected keys exist so the UI can render without KeyErrors.
    for k, default in (
        ("name", ""), ("body_shape", ""), ("skin_tone", ""),
        ("preferred_fit", ""), ("style_preferences", []),
        ("modesty_preference", None), ("comfort_needs", []),
        ("style_goals", []), ("highlight_features", []), ("balance_areas", []),
    ):
        merged.setdefault(k, default)
    return {"success": True, "profile": merged, "error": None}


# ─────────────────────────────────────────────
# WRITE (overlay only — never touches wardrobe.json)
# ─────────────────────────────────────────────

def _atomic_write_json(path: str, data: dict) -> None:
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".user_profile_", suffix=".json", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def save_fit_profile(updates: dict) -> dict:
    """
    Persist a partial update to the overlay. Only the five overlay keys
    are honored:
        modesty_preference, comfort_needs, style_goals,
        highlight_features, balance_areas.

    Anything else is ignored. Body-positive language is enforced on
    free-form text fields — see check_value_for_forbidden_language().
    """
    overlay = _load_overlay()
    accepted = ("modesty_preference", "comfort_needs", "style_goals",
                "highlight_features", "balance_areas")
    for k in accepted:
        if k in updates:
            v = updates[k]
            # Scan any free-form list/string content for forbidden language.
            forbidden = check_value_for_forbidden_language(v)
            if forbidden:
                return {
                    "success": False, "profile": overlay,
                    "error": (f"Body-positive language only. Avoid: "
                              f"{', '.join(sorted(forbidden))}."),
                }
            overlay[k] = v

    on_disk = {
        "_comment": "User fit / style profile overlay. See fit_tool.py.",
        **overlay,
    }
    try:
        _atomic_write_json(PROFILE_PATH, on_disk)
    except Exception as e:
        return {"success": False, "profile": overlay, "error": f"Failed to save: {e}"}
    return {"success": True, "profile": overlay, "error": None}


# ─────────────────────────────────────────────
# BODY-POSITIVE LANGUAGE CONTRACT
# ─────────────────────────────────────────────

# Verbs / phrases that frame body features as flaws. The skill rule
# fit-silhouette-rules.md R1 names these explicitly. We enforce the
# contract at both write-time (user profile input) and on the agent's
# reasoning trail (via check_reasoning_for_forbidden_language).
FORBIDDEN_TOKENS = {
    "flaw", "flaws",
    "fix",      # "fix the waist" — corrective framing
    "hide",     # "hide the hips" — corrective framing
    "minimize", "minimise",
    "correct",  "corrective",
    "problem area", "problem-area", "problem_area", "problem zone",
    "trouble area", "trouble-area",
    "slimming", "slimmer",
    "shameful",
}


def _contains_forbidden(text: str) -> set:
    """Return the set of forbidden tokens that appear in `text`."""
    if not isinstance(text, str):
        return set()
    low = text.lower()
    return {tok for tok in FORBIDDEN_TOKENS if tok in low}


def check_value_for_forbidden_language(value) -> set:
    """
    Scan a profile-field value (string, list, or dict of strings) for
    forbidden tokens. Returns the set of offenders (empty if clean).
    """
    if value is None:
        return set()
    if isinstance(value, str):
        return _contains_forbidden(value)
    if isinstance(value, list):
        found = set()
        for item in value:
            found |= check_value_for_forbidden_language(item)
        return found
    if isinstance(value, dict):
        found = set()
        for v in value.values():
            found |= check_value_for_forbidden_language(v)
        return found
    return set()


def check_reasoning_for_forbidden_language(reasoning: list) -> set:
    """
    Scan an agent reasoning trail (list of strings) and return any
    forbidden tokens that appear. Empty set means the trail is clean
    and the body-positive contract holds.
    """
    found = set()
    for line in (reasoning or []):
        found |= _contains_forbidden(line)
    return found


# ─────────────────────────────────────────────
# FIT-DRIVEN REASONING NOTES (for Step 5 of the agent)
# ─────────────────────────────────────────────

def fit_alignment_notes(item: dict, profile: dict) -> list:
    """
    Return a LIST of reasoning lines (possibly empty) explaining how this
    picked item aligns with the user's fit preferences. Each line is
    indented with two leading spaces so it reads as a sub-bullet under
    the main pick line in the agent's reasoning trail.

    Examples of generated notes:
      "  Aligns with your preferred tailored fit."
      "  Matches your style preference for classic, elegant pieces."
      "  Supports your goal to feel elevated."

    LANGUAGE: every note uses body-positive verbs (highlight, support,
    align). Never hide/fix/minimize/correct.
    """
    if not item or not isinstance(profile, dict):
        return []

    notes = []

    # Preferred fit
    pf = (profile.get("preferred_fit") or "").lower().strip()
    if pf and pf in (item.get("formality", "") + " " + item.get("name", "")).lower():
        notes.append(f"aligns with your preferred {pf} fit")
    elif pf == "tailored" and item.get("formality") in ("business", "smart_casual", "formal"):
        notes.append("aligns with your preferred tailored fit")

    # Style preferences (seed-owner-level — classic, elegant, minimal, etc.)
    style_prefs = profile.get("style_preferences") or []
    if style_prefs:
        prefs_str = ", ".join(style_prefs[:3])
        tags = [t.lower() for t in (item.get("tags") or [])]
        if "versatile" in tags or item.get("formality") in ("formal", "business"):
            notes.append(f"matches your style preference for {prefs_str} pieces")

    # Style goals (user overlay — elevated, modernized, feel like myself, …)
    goals = profile.get("style_goals") or []
    if goals:
        notes.append(f"supports your goal to feel {goals[0].lower()}")

    return [f"  {n.capitalize()}." for n in notes]


def fit_alignment_note(item: dict, profile: dict):
    """
    Backward-compatible single-line helper. Returns the first alignment
    note from fit_alignment_notes(), or None when there are no notes.
    Prefer fit_alignment_notes() in new code.
    """
    notes = fit_alignment_notes(item, profile)
    return notes[0] if notes else None
