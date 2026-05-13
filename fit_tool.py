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
    # Layer 4 — meta: provenance of auto-fills. "user" = explicitly set
    # by the wearer; "auto" = predicted from measurements; None = unset.
    "_body_shape_source": None,
    # Layer 5 — locale settings. The IANA timezone the user lives in.
    # Used by the .ics calendar importer to convert UTC-timestamped
    # events to local clock time, so a 6 PM event in Google Calendar
    # shows as 6 PM here too — regardless of whether the server is
    # the user's laptop (often Central) or Streamlit Cloud (always
    # UTC). Default America/Chicago (Minneapolis is in that zone).
    "timezone":           "America/Chicago",
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
    ("bust",          "Bust",
     "Around the back, under the arms and across the fullest part of the bust. Tape flat against the figure, straight across the back and not too tight."),
    ("waist",         "Natural waist",
     "Around the natural waist, tape flat against the figure, snug but not too tight. The narrowest part of the torso, usually just above the navel."),
    ("hips",          "Hips",
     "Around the fullest part of the hips, usually 21–23 cm / 8–9 in down from the waist. Tape parallel to the floor."),
    ("high_hips",     "High hips",
     "Around the body just below the natural waist — about 8 cm / 3 in down — where a low-rise waistband would sit."),
    ("back_waist",    "Back waist length",
     "Down the spine from the bony bump at the base of the neck to the natural waistline."),
    ("front_waist",   "Front waist length",
     "From the hollow above the collarbone, down the front of the body to the natural waist."),
    ("inseam",        "Inseam",
     "Inner-leg measurement from the top of the inner thigh down to where you want pants to break (usually the ankle bone)."),
    ("sleeve",        "Sleeve length",
     "From the shoulder bone, down the outside of the arm with a slight bend at the elbow, to the wristbone."),
    ("trouser_three_quarter", "3/4 trouser length",
     "Down the outside of the leg from the natural waist to mid-calf."),
    ("trouser_full",  "Full trouser length",
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


def _closest_column(components: list) -> tuple:
    """
    Internal: given a list of (name, user_cm, chart_row_of_10_values),
    pick the column index with the smallest average absolute deviation.
    Returns (col_index, deviation_cm). Empty input → (0, inf).
    """
    if not components:
        return 0, float("inf")
    best_col, best_dev = 0, float("inf")
    for col in range(10):
        total = sum(abs(user_cm - chart_row[col])
                    for _n, user_cm, chart_row in components)
        avg = total / len(components)
        if avg < best_dev:
            best_dev, best_col = avg, col
    return best_col, best_dev


def _confidence_band(dev_cm: float) -> str:
    """Map a centimeter deviation to a discrete confidence label."""
    if dev_cm <= 2.0:
        return "high"
    if dev_cm <= 5.0:
        return "medium"
    return "low"


def _size_record(col: int, dev_cm: float, matched: list) -> dict:
    """Bundle one column lookup into the standard return shape."""
    return {
        "bundle":       SIZE_CHART["bundle"][col],
        "nz_au_uk":     SIZE_CHART["nz_au_uk"][col],
        "europe":       SIZE_CHART["europe"][col],
        "usa":          SIZE_CHART["usa"][col],
        "confidence":   _confidence_band(dev_cm),
        "matched_on":   matched,
        "deviation_cm": round(dev_cm, 1),
    }


def predict_size(measurements: dict) -> dict:
    """
    Overall closest size on the Sewing Revival chart.

    The match is computed against bust + waist + hip totals because the
    chart steps those three together. If only some of the three are
    present, matches on whichever exist (still useful, less precise).
    Returns {} when no usable input is provided.

    Brands vary — the caller is expected to surface this as a *predicted*
    size, not a definitive label.
    """
    if not isinstance(measurements, dict):
        return {}

    cm = INCH_TO_CM
    components = []
    for key, label, chart_key in (
        ("bust",  "bust",  "bust_cm"),
        ("waist", "waist", "waist_cm"),
        ("hips",  "hip",   "hip_cm"),
    ):
        v = measurements.get(key)
        if isinstance(v, (int, float)) and v > 0:
            components.append((label, v * cm, SIZE_CHART[chart_key]))

    if not components:
        return {}

    col, dev = _closest_column(components)
    return _size_record(col, dev, [c[0] for c in components])


def predict_sizes_by_category(measurements: dict) -> dict:
    """
    Per-garment-category size predictions.

      top:    bust drives top size (chest circumference is the binding
              dimension for shirts / blouses / jackets).
      bottom: max(waist, hips) drives bottom size — sizing up to the
              larger of the two prevents tight-on-hip pants.
      dress:  max(bust, waist, hips) drives dress size — a dress must
              clear the largest cross-section of the torso.

    Returns a dict like::

        {
          "top":    {bundle, nz_au_uk, europe, usa, confidence,
                     matched_on, deviation_cm},
          "bottom": {...},
          "dress":  {...},
        }

    Keys are omitted when the relevant input is missing — a caller can
    iterate `result.items()` safely.
    """
    if not isinstance(measurements, dict):
        return {}

    cm = INCH_TO_CM
    bust  = measurements.get("bust")
    waist = measurements.get("waist")
    hips  = measurements.get("hips")
    by_cat: dict = {}

    # TOP — driven by bust.
    if isinstance(bust, (int, float)) and bust > 0:
        col, dev = _closest_column([("bust", bust * cm, SIZE_CHART["bust_cm"])])
        by_cat["top"] = _size_record(col, dev, ["bust"])

    # BOTTOM — driven by whichever is larger of waist / hips.
    bottom_components = []
    if isinstance(waist, (int, float)) and waist > 0:
        bottom_components.append(("waist", waist * cm, SIZE_CHART["waist_cm"]))
    if isinstance(hips, (int, float)) and hips > 0:
        bottom_components.append(("hip", hips * cm, SIZE_CHART["hip_cm"]))
    if bottom_components:
        # Bias toward the larger cross-section: find the column for each
        # dimension separately, then take the larger column index. This
        # produces "size up if the hips need it" behavior.
        cols = []
        for c in bottom_components:
            col, _dev = _closest_column([c])
            cols.append(col)
        chosen = max(cols)
        # Deviation reported is the avg deviation at the chosen column.
        total_dev = sum(abs(c[1] - c[2][chosen]) for c in bottom_components)
        avg_dev = total_dev / len(bottom_components)
        by_cat["bottom"] = _size_record(chosen, avg_dev, [c[0] for c in bottom_components])

    # DRESS — driven by max of bust / waist / hips.
    dress_components = []
    if isinstance(bust, (int, float)) and bust > 0:
        dress_components.append(("bust",  bust  * cm, SIZE_CHART["bust_cm"]))
    if isinstance(waist, (int, float)) and waist > 0:
        dress_components.append(("waist", waist * cm, SIZE_CHART["waist_cm"]))
    if isinstance(hips, (int, float)) and hips > 0:
        dress_components.append(("hip",   hips  * cm, SIZE_CHART["hip_cm"]))
    if dress_components:
        cols = []
        for c in dress_components:
            col, _dev = _closest_column([c])
            cols.append(col)
        chosen = max(cols)
        total_dev = sum(abs(c[1] - c[2][chosen]) for c in dress_components)
        avg_dev = total_dev / len(dress_components)
        by_cat["dress"] = _size_record(chosen, avg_dev, [c[0] for c in dress_components])

    return by_cat


def predict_body_shape(measurements: dict) -> dict:
    """
    Predict a body-shape category from bust / waist / hip ratios using
    the well-known industry heuristic.

    Important honesty disclosure (mirrors evidence-and-references §3.4
    and §4): body-shape labels are **industry heuristic, not scientific
    taxonomy**. Wearly surfaces a prediction here so first-time users
    have a sensible default — but the value is always editable, and the
    reasoning that produced it is shown to the user in plain English.

    Heuristic boundaries:
      hourglass:           |bust - hips| ≤ 2 in AND waist ≤ min(bust,hips) - 8 in
      pear (triangle):     hips - bust ≥ 2 in AND waist < hips
      inverted triangle:   bust - hips ≥ 2 in AND waist < bust
      rectangle:           all three within ~2 in of each other AND
                           waist > min(bust,hips) - 8 in (low definition)
      athletic:            default when nothing else fires

    Returns {} when bust, waist, or hips is missing. Otherwise::

        {
          "shape":      "hourglass" | "pear" | "inverted triangle" |
                        "rectangle" | "athletic",
          "confidence": "high" | "medium" | "low",
          "reason":     short body-positive plain-English sentence,
          "ratios":     {"bust", "waist", "hips", "bust_minus_hip",
                         "waist_definition"}  (all in inches),
        }
    """
    if not isinstance(measurements, dict):
        return {}

    bust  = measurements.get("bust")
    waist = measurements.get("waist")
    hips  = measurements.get("hips")
    if not all(isinstance(v, (int, float)) and v > 0 for v in (bust, waist, hips)):
        return {}

    bust_minus_hip = bust - hips
    waist_definition = min(bust, hips) - waist  # positive = nipped-in waist
    avg_bh = (bust + hips) / 2.0

    shape = "athletic"
    confidence = "low"
    reason = "Balanced proportions across bust, waist, and hips."

    # Hourglass: bust ≈ hips, well-defined waist.
    if abs(bust_minus_hip) <= 2 and waist_definition >= 8:
        shape = "hourglass"
        confidence = "high"
        reason = ("Bust and hips are within about an inch, with a clearly "
                  "defined waist — the classic hourglass ratio.")
    # Pear: hips notably larger than bust.
    elif bust_minus_hip <= -2 and waist < hips:
        shape = "pear"
        confidence = "high" if abs(bust_minus_hip) >= 3 else "medium"
        reason = ("Hips are larger than bust by about "
                  f"{abs(bust_minus_hip):.1f} in — the pear / triangle ratio.")
    # Inverted triangle: bust notably larger than hips.
    elif bust_minus_hip >= 2 and waist < bust:
        shape = "inverted triangle"
        confidence = "high" if bust_minus_hip >= 3 else "medium"
        reason = ("Bust is larger than hips by about "
                  f"{bust_minus_hip:.1f} in — the inverted-triangle ratio.")
    # Rectangle: similar bust / waist / hips with low waist definition.
    elif abs(bust_minus_hip) <= 2 and waist_definition < 6:
        shape = "rectangle"
        confidence = "medium"
        reason = ("Bust, waist, and hips are all within a couple of inches "
                  "of each other — the rectangle / column ratio.")

    return {
        "shape":      shape,
        "confidence": confidence,
        "reason":     reason,
        "ratios": {
            "bust":             float(bust),
            "waist":            float(waist),
            "hips":             float(hips),
            "bust_minus_hip":   round(bust_minus_hip, 1),
            "waist_definition": round(waist_definition, 1),
        },
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
        "timezone",
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

    # Auto-fill body_shape from measurements. The prediction is an
    # industry heuristic — see predict_body_shape() docstring. Provenance
    # of the value is tracked in _body_shape_source so the UI can show
    # "Auto-filled" vs "Your choice".
    #
    # Logic:
    #   - empty overlay AND we have a prediction → save prediction, src="auto"
    #   - non-empty overlay matching the prediction → keep src as-is (or
    #     default to "auto" if it was never set — user accepted the suggestion)
    #   - non-empty overlay differing from the prediction → src="user"
    _meas = overlay.get("measurements", {}) or {}
    _pred = predict_body_shape(_meas)
    _pred_shape = _pred.get("shape") if _pred else None
    if not overlay.get("body_shape"):
        if _pred_shape:
            overlay["body_shape"] = _pred_shape
            overlay["_body_shape_source"] = "auto"
    else:
        if _pred_shape and overlay["body_shape"] == _pred_shape:
            if not overlay.get("_body_shape_source"):
                overlay["_body_shape_source"] = "auto"
        else:
            overlay["_body_shape_source"] = "user"

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
