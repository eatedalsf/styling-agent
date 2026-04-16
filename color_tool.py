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

        if any(b in color or color in b for b in best):
            score += 8
            notes.append(f"✓ {name} ({color}) — excellent color for your skin tone.")
        elif any(g in color or color in g for g in good):
            score += 4
            notes.append(f"✓ {name} ({color}) — works well for your skin tone.")
        elif any(a in color or color in a for a in avoid):
            score -= 10
            flags.append(f"⚠ {name} ({color}) — this color is less flattering for your skin tone.")

    score = max(0, min(100, score))
    notes.append(rules.get("notes", ""))
    return {"score": score, "notes": notes, "flags": flags}
