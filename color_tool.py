"""
Tool 4: Color Coordination Checker
Checks whether clothing colors work for a given skin tone.
"""

import json
import os


def _find_data_file(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "data", filename),
        os.path.join(here, "..", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


DATA_PATH = _find_data_file("color_rules.json")


def get_color_rules(skin_tone: str) -> dict:
    try:
        with open(DATA_PATH, "r") as f:
            all_rules = json.load(f)
    except Exception as e:
        return {"success": False, "rules": None, "error": str(e)}

    rules = all_rules.get(skin_tone.lower())
    if not rules:
        return {
            "success": True,
            "rules": {
                "best_colors": ["black", "navy", "white", "camel"],
                "good_colors": [],
                "avoid_colors": [],
                "metal_preference": "gold or silver",
                "notes": f"No specific rules for '{skin_tone}'. Using universal safe palette."
            },
            "error": None
        }
    return {"success": True, "rules": rules, "error": None}


def color_tier_for(color: str, skin_tone: str) -> str:
    """
    Single source of truth for "is this color flattering for this skin
    tone?" — returns one of:
        "best"    → color is in the skin tone's best_colors list
        "good"    → color is in good_colors
        "avoid"   → color is in avoid_colors (this is the only tier that
                    other modules should treat as a color warning /
                    tradeoff)
        "neutral" → no rule fires; treat as harmless

    Used by `score_outfit_colors` (the Step 7 scorer) AND by
    `styling_agent._evaluate_tradeoffs` so the color-harmony score
    and the per-item tradeoff text never disagree.

    Matching mirrors `score_outfit_colors`: substring either direction
    so "white/gold" matches "gold" (best) and "warm white" matches
    "white" (good). The TIER ORDER matters — best wins over good wins
    over avoid, which prevents an item with a primarily-best color and
    a stray avoid token (e.g., "warm white" never hitting "avoid")
    from being mis-tiered.
    """
    if not color or not skin_tone:
        return "neutral"
    rules_result = get_color_rules(skin_tone)
    if not rules_result.get("success"):
        return "neutral"
    rules = rules_result["rules"] or {}
    best  = [c.lower() for c in rules.get("best_colors",  [])]
    good  = [c.lower() for c in rules.get("good_colors",  [])]
    avoid = [c.lower() for c in rules.get("avoid_colors", [])]
    c = color.lower()
    if any(b in c or c in b for b in best):
        return "best"
    if any(g in c or c in g for g in good):
        return "good"
    if any(a in c or c in a for a in avoid):
        return "avoid"
    return "neutral"


def score_outfit_colors(items: list, skin_tone: str) -> dict:
    rules_result = get_color_rules(skin_tone)
    if not rules_result["success"]:
        return {"score": 50, "notes": ["Color check unavailable."], "flags": []}

    rules = rules_result["rules"]
    best = [c.lower() for c in rules.get("best_colors", [])]
    good = [c.lower() for c in rules.get("good_colors", [])]
    avoid = [c.lower() for c in rules.get("avoid_colors", [])]

    score = 60
    notes = []
    flags = []

    for item in items:
        color = item.get("color", "").lower()
        name = item.get("name", "item")
        # Use the shared tier helper so this scoring path stays in
        # sync with any other module that classifies the same color.
        tier = color_tier_for(color, skin_tone)
        if tier == "best":
            score += 8
            notes.append(f"✓ {name} ({color}) — excellent color for your skin tone.")
        elif tier == "good":
            score += 4
            notes.append(f"✓ {name} ({color}) — works well for your skin tone.")
        elif tier == "avoid":
            score -= 10
            flags.append(f"⚠ {name} ({color}) — this color is less flattering for your skin tone.")

    score = max(0, min(100, score))
    notes.append(rules.get("notes", ""))
    return {"score": score, "notes": notes, "flags": flags}
