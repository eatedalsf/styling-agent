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
# Layer 1 — core identity & style fields (mirror the wardrobe.json owner block,
# but live in the overlay so the seed is never mutated).
# Layer 2 — overlay-only preferences (no equivalent in the seed).
# Layer 3 — body measurements (optional; helps Wearly suggest pieces that
# fit the user's real proportions rather than relying only on body-shape
# categories). Every measurement is optional and body-positive in framing.
_EMPTY_OVERLAY = {
    # Layer 1 — core identity (was seed-only, now user-editable)
    "name":               None,
    "body_shape":         None,
    "skin_tone":          None,
    "preferred_fit":      None,
    "style_preferences":  [],
    # Layer 2 — overlay-only preferences
    "modesty_preference": None,
    "comfort_needs":      [],
    "style_goals":        [],
    "highlight_features": [],
    "balance_areas":      [],
    # Layer 3 — body measurements (optional, body-positive)
    "measurements":       {},
}


# Canonical measurement fields. Each entry: key, label, how-to-measure tip.
# The 11 anatomical measurements correspond to the A–J labels in The Sewing
# Revival's body-measurements diagram, plus an overall height. Tips for
# bust, waist, and hips are paraphrased from their "Choosing your size"
# guide (thesewingrevival.com/pages/choosing-your-size). The rest are
# standard tailoring instruction — body-positive and instructional, no
# judgmental language. Measurements are stored in inches internally; the
# UI lets the user toggle inch ↔ cm at display time.
MEASUREMENT_FIELDS = [
    ("height",        "Height",
     "Stand against a wall in bare feet, look straight ahead. Mark the top of your head, then measure floor-to-mark."),
    ("bust",          "Bust (A)",
     "Around the back, under the arms and across the fullest part of the bust. Tape flat against the figure, straight across the back and not too tight."),
    ("waist",         "Natural waist (B)",
     "Around the natural waist, tape flat against the figure, snug but not too tight. The narrowest part of the torso, usually just above the navel."),
    ("hips",          "Hips (C)",
     "Around the fullest part of the hips, usually 21–23 cm / 8–9 in down from the waist. Tape parallel to the floor."),
    ("high_hips",     "High hips (D)",
     "Around the body just below the natural waist — about 8 cm / 3 in down — where a low-rise waistband would sit."),
    ("back_waist",    "Back waist length (E)",
     "Down the spine from the bony bump at the base of the neck to the natural waistline."),
    ("front_waist",   "Front waist length (F)",
     "From the hollow above the collarbone, down the front of the body to the natural waist."),
    ("inseam",        "Inseam (G)",
     "Inner-leg measurement from the top of the inner thigh down to where you want pants to break (usually the ankle bone)."),
    ("sleeve",        "Sleeve length (H)",
     "From the shoulder bone, down the outside of the arm with a slight bend at the elbow, to the wristbone."),
    ("trouser_three_quarter", "3/4 trouser length (I)",
     "Down the outside of the leg from the natural waist to mid-calf."),
    ("trouser_full",  "Full trouser length (J)",
     "Down the outside of the leg from the natural waist to the ankle (where you want pants to break)."),
    ("shoulder",      "Shoulder width",
     "Across the back, from the bony point at one shoulder to the bony point at the other."),
    ("neck",          "Neck",
     "Wrap the tape around the base of the neck where a shirt collar would sit, with one finger of slack."),
]

# Unit conversion. Internal storage is always inches; the UI converts on the
# fly when the user picks centimeters. Round-trip preserves user intent
# because save_fit_profile() normalizes back to inches.
INCH_TO_CM = 2.54


# Size chart reference — values transcribed from The Sewing Revival's
# Size Bundles - Women chart. Measurements in centimeters; 10 columns
# left-to-right covering NZ/AU/UK 6 through 24. The four size "bundles"
# (Small / Medium / Large / X-Large) group consecutive columns.
SIZE_CHART = {
    "nz_au_uk": [6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
    "europe":   [35, 37, 39, 41, 43, 45, 47, 49, 51, 53],
    "usa":      [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    "bust_cm":   [80,  85,  90,  95, 100, 105, 110, 115, 120, 125],
    "waist_cm":  [66,  71,  76,  81,  86,  91,  96, 101, 106, 111],
    "hip_cm":    [89,  94,  99, 104, 109, 114, 119, 124, 129, 134],
    "height_cm": [169, 170, 171, 172, 173, 174, 175, 176, 177, 178],
    # Bundle label per column index 0..9
    "bundle":    ["Small", "Small",
                  "Medium", "Medium", "Medium",
                  "Large", "Large",
                  "X-Large", "X-Large", "X-Large"],
}


def predict_size(measurements: dict) -> dict:
    """
    Given a measurements dict (values in inches, internal storage unit),
    return the closest size on the Sewing Revival chart in each system.

    The match is computed against bust + waist + hip totals because the
    chart steps those three together. If only some of the three are
    present, we match on whichever exist (still useful, less precise).
    Returns {} when no usable input is provided.

    Result shape::

        {
            "bundle":  "Medium",
            "nz_au_uk": 12,
            "europe":  41,
            "usa":     8,
            "confidence": "high" | "medium" | "low",
            "matched_on": ["bust", "waist", "hip"],
        }

    Brands vary — the caller is expected to surface this as a *predicted*
    size, not a definitive label.
    """
    if not isinstance(measurements, dict):
        return {}

    cm = INCH_TO_CM
    bust_in  = measurements.get("bust")
    waist_in = measurements.get("waist")
    hip_in   = measurements.get("hips")

    components = []
    if isinstance(bust_in, (int, float)) and bust_in > 0:
        components.append(("bust", bust_in * cm, SIZE_CHART["bust_cm"]))
    if isinstance(waist_in, (int, float)) and waist_in > 0:
        components.append(("waist", waist_in * cm, SIZE_CHART["waist_cm"]))
    if isinstance(hip_in, (int, float)) and hip_in > 0:
        components.append(("hip", hip_in * cm, SIZE_CHART["hip_cm"]))

    if not components:
        return {}

    # For each of the 10 columns compute the average absolute deviation
    # across the components the user provided. Pick the column with the
    # smallest deviation.
    best_col = 0
    best_dev = float("inf")
    for col in range(10):
        total = 0.0
        for _name, user_cm, chart_row in components:
            total += abs(user_cm - chart_row[col])
        avg = total / len(components)
        if avg < best_dev:
            best_dev = avg
            best_col = col

    # Confidence band — average deviation in cm.
    if best_dev <= 2.0:
        confidence = "high"
    elif best_dev <= 5.0:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "bundle":     SIZE_CHART["bundle"][best_col],
        "nz_au_uk":   SIZE_CHART["nz_au_uk"][best_col],
        "europe":     SIZE_CHART["europe"][best_col],
        "usa":        SIZE_CHART["usa"][best_col],
        "confidence": confidence,
        "matched_on": [c[0] for c in components],
        "deviation_cm": round(best_dev, 1),
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
    # Backward compatibility: the field formerly known as "arm" is now
    # "sleeve" (the Sewing-Revival diagram's H label, same anatomical
    # measurement). Copy across so existing users don't lose data.
    _meas = overlay.get("measurements", {}) or {}
    if isinstance(_meas, dict) and "arm" in _meas and "sleeve" not in _meas:
        _meas["sleeve"] = _meas.pop("arm")
        overlay["measurements"] = _meas
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
        ("measurements", {}),
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
    Persist a partial update to the overlay. Accepted keys:

      Layer 1 (core identity, was seed-only):
        name, body_shape, skin_tone, preferred_fit, style_preferences
      Layer 2 (overlay-only preferences):
        modesty_preference, comfort_needs, style_goals,
        highlight_features, balance_areas
      Layer 3 (optional measurements):
        measurements   — dict of {field_key: float | None}

    Anything else is ignored. Body-positive language is enforced on
    free-form text fields — see check_value_for_forbidden_language().
    Empty strings normalize to None so the seed value can show through.
    """
    overlay = _load_overlay()
    accepted = (
        "name", "body_shape", "skin_tone", "preferred_fit", "style_preferences",
        "modesty_preference", "comfort_needs", "style_goals",
        "highlight_features", "balance_areas",
        "measurements",
    )
    for k in accepted:
        if k not in updates:
            continue
        v = updates[k]

        # Body-positive language check on any free-form text content.
        # measurements is numeric and exempt; other keys go through the
        # scanner so the contract holds even on the new core fields.
        if k != "measurements":
            forbidden = check_value_for_forbidden_language(v)
            if forbidden:
                return {
                    "success": False, "profile": overlay,
                    "error": (f"Body-positive language only. Avoid: "
                              f"{', '.join(sorted(forbidden))}."),
                }

        # Normalize empty strings to None for single-value text fields so
        # the seed value shines through when the user clears a field.
        if isinstance(v, str) and v.strip() == "":
            v = None

        # measurements: sanitize the dict — keep only known keys, drop
        # blanks / non-numeric values silently.
        if k == "measurements" and isinstance(v, dict):
            known = {f[0] for f in MEASUREMENT_FIELDS}
            cleaned = {}
            for mk, mv in v.items():
                if mk not in known:
                    continue
                try:
                    if mv in (None, "", 0, 0.0):
                        continue
                    cleaned[mk] = float(mv)
                except (TypeError, ValueError):
                    continue
            v = cleaned

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
