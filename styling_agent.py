"""
Styling Agent — Core Agent Logic
This is the "brain" of the system. It orchestrates all tools in a
defined multi-step workflow and produces a complete outfit recommendation
with full reasoning explanation.
"""

import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)                                    # flat: tools are siblings
sys.path.insert(0, os.path.dirname(_here))                   # structured: parent has tools/
sys.path.insert(0, os.path.join(os.path.dirname(_here), "tools"))  # structured tools subdir

try:
    from tools.calendar_tool import get_upcoming_events
    from tools.weather_tool import get_weather
    from tools.wardrobe_tool import filter_items_by_occasion, get_owner_profile, check_gaps
    from tools.color_tool import score_outfit_colors
except ModuleNotFoundError:
    from calendar_tool import get_upcoming_events
    from weather_tool import get_weather
    from wardrobe_tool import filter_items_by_occasion, get_owner_profile, check_gaps
    from color_tool import score_outfit_colors


# ─────────────────────────────────────────────
# OCCASION LOGIC MAPS
# ─────────────────────────────────────────────

OCCASION_TAG_MAP = {
    "work": "work",
    "business": "work",
    "meeting": "work",
    "gym": "gym",
    "workout": "gym",
    "yoga": "gym",
    "running": "gym",
    "dinner": "dinner",
    "restaurant": "dinner",
    "date": "dinner",
    "formal_event": "formal",
    "gala": "formal",
    "formal": "formal",
    "casual": "casual",
    "weekend": "casual",
    "brunch": "casual",
    "everyday": "casual"
}

REQUIRED_PIECES = {
    "work":   ["top", "bottom"],
    "dinner": ["top", "bottom"],
    "gym":    ["activewear", "activewear"],
    "formal": ["dress"],
    "casual": ["top", "bottom"]
}

DRESS_OCCASIONS = ["formal", "dinner"]

SHOPPING_SUGGESTIONS = {
    "formal": [
        "A floor-length gown or tailored formal suit would complete a formal look.",
        "Consider a statement clutch and elegant heels for formal events."
    ],
    "work": [
        "A classic blazer would add polish to any work outfit.",
        "A second pair of tailored trousers in a neutral would expand your options."
    ],
    "dinner": [
        "A chic midi dress in a jewel tone would be perfect for dinner occasions.",
        "A pair of elegant strappy heels would elevate dinner outfits."
    ],
    "casual": [
        "A denim jacket is a great casual layering piece.",
        "Versatile flats or loafers work well for casual outings."
    ],
    "gym": [
        "A high-support sports bra would be a useful gym addition.",
        "Moisture-wicking shorts for warmer workout days."
    ]
}


# ─────────────────────────────────────────────
# MAIN AGENT WORKFLOW
# ─────────────────────────────────────────────

def run_agent(mode: str = "calendar", everyday_request: str = None) -> dict:
    """
    Main agent entry point.

    mode = "calendar"  → reads next upcoming event automatically
    mode = "everyday"  → uses everyday_request string (e.g. "gym", "work")

    Returns a full result dict with:
      - steps: list of workflow steps with status and output
      - recommendation: final outfit dict
      - reasoning: explanation of all decisions
      - gaps: missing items (if any)
      - shopping_suggestions: items to buy if wardrobe is incomplete
      - color_score: how well the outfit works for the owner's skin tone
      - weather: weather context used
      - event: the event or occasion context
    """

    steps = []
    result = {
        "steps": steps,
        "recommendation": None,
        "reasoning": [],
        "gaps": [],
        "shopping_suggestions": [],
        "color_score": None,
        "weather": None,
        "event": None,
        "profile": None,
        "error": None
    }

    # ── STEP 1: Determine Occasion ───────────────────────────────────────────
    step1 = {"step": 1, "name": "Determine Occasion", "status": "ok", "output": ""}

    if mode == "calendar":
        calendar_result = get_upcoming_events(days_ahead=7)
        if not calendar_result["success"] or not calendar_result["events"]:
            step1["status"] = "fallback"
            step1["output"] = "No upcoming calendar events found. Defaulting to everyday casual."
            occasion = {"type": "casual", "title": "Everyday Casual", "formality": "casual",
                        "date": "Today", "time": "", "notes": ""}
        else:
            raw_event = calendar_result["events"][0]
            occasion = raw_event
            step1["output"] = f"Found: '{raw_event['title']}' on {raw_event['date']} at {raw_event.get('time', '')}."

    elif mode == "everyday" and everyday_request:
        request_lower = everyday_request.lower()
        matched_tag = next(
            (v for k, v in OCCASION_TAG_MAP.items() if k in request_lower), "casual"
        )
        occasion = {
            "type": matched_tag,
            "title": everyday_request.strip().title(),
            "formality": matched_tag,
            "date": "Today",
            "time": "",
            "notes": ""
        }
        step1["output"] = f"Everyday request understood: '{everyday_request}' → Occasion type: {matched_tag}."

    else:
        result["error"] = "Invalid mode. Use 'calendar' or 'everyday' with a request string."
        return result

    steps.append(step1)
    result["event"] = occasion

    # ── STEP 2: Get Owner Profile ─────────────────────────────────────────────
    step2 = {"step": 2, "name": "Load Style Profile", "status": "ok", "output": ""}
    profile_result = get_owner_profile()

    if not profile_result["success"]:
        step2["status"] = "error"
        step2["output"] = f"Could not load profile: {profile_result['error']}"
        result["error"] = step2["output"]
        steps.append(step2)
        return result

    profile = profile_result["profile"]
    result["profile"] = profile
    step2["output"] = (
        f"Owner: {profile['name']} | Body shape: {profile['body_shape']} | "
        f"Skin tone: {profile['skin_tone']} | Style: {', '.join(profile['style_preferences'])}"
    )
    steps.append(step2)

    # ── STEP 3: Check Weather ─────────────────────────────────────────────────
    step3 = {"step": 3, "name": "Check Weather", "status": "ok", "output": ""}
    weather_result = get_weather()
    weather = weather_result["weather"]
    result["weather"] = weather

    if weather_result.get("error"):
        step3["status"] = "fallback"
        step3["output"] = f"Weather note: {weather_result['error']} | Using estimate: {weather['temp_f']}°F, {weather['condition']}."
    else:
        step3["output"] = (
            f"{weather['city']}: {weather['temp_f']}°F (feels like {weather['feels_like_f']}°F), "
            f"{weather['condition']}, wind {weather['wind_mph']} mph, "
            f"{weather['precip_chance_pct']}% chance of rain. {weather['layer_advice']}"
        )
    steps.append(step3)

    # Determine current season from temp
    temp = weather["temp_f"]
    if isinstance(temp, (int, float)):
        if temp < 40:
            season = "winter"
        elif temp < 58:
            season = "fall"
        elif temp < 75:
            season = "spring"
        else:
            season = "summer"
    else:
        season = "spring"

    # ── STEP 4: Filter Wardrobe ────────────────────────────────────────────────
    step4 = {"step": 4, "name": "Filter Wardrobe", "status": "ok", "output": ""}
    occasion_tag = OCCASION_TAG_MAP.get(occasion.get("type", "").lower(), "casual")

    wardrobe_result = filter_items_by_occasion(occasion_tag, season)
    if not wardrobe_result["success"]:
        step4["status"] = "error"
        step4["output"] = f"Wardrobe error: {wardrobe_result['error']}"
        result["error"] = step4["output"]
        steps.append(step4)
        return result

    clothing_pool = wardrobe_result["clothing"]
    shoes_pool = wardrobe_result["shoes"]
    accessories_pool = wardrobe_result["accessories"]

    step4["output"] = (
        f"Found {len(clothing_pool)} clothing items, {len(shoes_pool)} shoe options, "
        f"{len(accessories_pool)} accessories for occasion: {occasion_tag} in {season}."
    )
    steps.append(step4)

    # ── STEP 5: Build Outfit ──────────────────────────────────────────────────
    step5 = {"step": 5, "name": "Build Outfit", "status": "ok", "output": ""}
    outfit = []
    reasoning = []

    formality = occasion.get("formality", "casual")

    # Check for dress-worthy occasions first
    if occasion_tag in DRESS_OCCASIONS and formality in ["formal", "smart_casual"]:
        dresses = [i for i in clothing_pool if i["type"] == "dress"]
        if dresses:
            # Prefer higher formality dresses for formal occasions
            if formality == "formal":
                dresses.sort(key=lambda d: 0 if d["formality"] == "formal" else 1)
            outfit.append(dresses[0])
            reasoning.append(f"Selected '{dresses[0]['name']}' as a one-piece solution for this {formality} occasion.")

    # If no dress selected, build top + bottom
    if not any(i["type"] == "dress" for i in outfit):
        tops = [i for i in clothing_pool if i["type"] == "top"]
        bottoms = [i for i in clothing_pool if i["type"] == "bottom"]
        activewear = [i for i in clothing_pool if i["type"] == "activewear"]

        if occasion_tag == "gym":
            if activewear:
                outfit.extend(activewear[:2])
                reasoning.append(f"Selected activewear set: {', '.join(i['name'] for i in outfit)}.")
            else:
                reasoning.append("No activewear found in wardrobe for this gym occasion.")
        else:
            if tops:
                outfit.append(tops[0])
                reasoning.append(f"Selected top: '{tops[0]['name']}' for its {tops[0]['formality']} formality.")
            if bottoms:
                outfit.append(bottoms[0])
                reasoning.append(f"Selected bottom: '{bottoms[0]['name']}' to pair with the top.")

    # Add shoes
    if shoes_pool:
        outfit.append(shoes_pool[0])
        reasoning.append(f"Added shoes: '{shoes_pool[0]['name']}' appropriate for the occasion.")

    # Add accessories (up to 2)
    for acc in accessories_pool[:2]:
        outfit.append(acc)
        reasoning.append(f"Added accessory: '{acc['name']}'.")

    # Add outerwear if weather requires it.
    # Use the CURRENT occasion (not a hardcoded "work" tag) so a gym outfit
    # doesn't get auto-paired with a formal coat.
    outerwear_gap = False
    if isinstance(temp, (int, float)) and temp < 60:
        occ_outer_result = filter_items_by_occasion(occasion_tag, season)
        outer_pool = [i for i in occ_outer_result.get("clothing", []) if i["type"] == "outerwear"]

        if outer_pool:
            outfit.append(outer_pool[0])
            reasoning.append(
                f"Added '{outer_pool[0]['name']}' as outerwear — temperature is {temp}°F and {weather['layer_advice']}"
            )
        else:
            # No outerwear matches this occasion. Don't force a wrong-style coat
            # onto the outfit; flag it as a wardrobe gap instead.
            outerwear_gap = True
            reasoning.append(
                f"Note: temperature is {temp}°F, but no {occasion_tag}-appropriate "
                f"outerwear was found in the wardrobe. Skipping outerwear rather "
                f"than forcing a mismatched coat."
            )

    step5["output"] = f"Built outfit with {len(outfit)} pieces: {', '.join(i['name'] for i in outfit)}."
    steps.append(step5)

    # ── STEP 6: Check for Gaps ────────────────────────────────────────────────
    step6 = {"step": 6, "name": "Check for Wardrobe Gaps", "status": "ok", "output": ""}
    required = REQUIRED_PIECES.get(occasion_tag, ["top", "bottom"])
    gaps = check_gaps(outfit, required)

    if gaps:
        step6["status"] = "gap_found"
        step6["output"] = f"Missing outfit pieces: {', '.join(gaps)}."
        suggestions = SHOPPING_SUGGESTIONS.get(occasion_tag, [])
        result["gaps"] = gaps
        result["shopping_suggestions"] = suggestions
        reasoning.append(
            f"Your wardrobe is missing: {', '.join(gaps)} for this occasion. "
            f"Shopping suggestion: {suggestions[0] if suggestions else 'Consider adding a versatile piece.'}"
        )
    else:
        step6["output"] = "Outfit is complete — all required pieces present."
    steps.append(step6)

    # Record outerwear gap (detected in Step 5) AFTER Step 6 so we don't
    # overwrite check_gaps results, and so shopping_suggestions keeps both.
    if outerwear_gap:
        if "outerwear" not in result["gaps"]:
            result["gaps"].append("outerwear")
        if occasion_tag == "gym":
            outer_suggestion = (
                "A lightweight athletic windbreaker or running jacket would cover "
                "cool-weather gym transit without breaking the activewear look."
            )
        else:
            outer_suggestion = (
                f"A {occasion_tag}-appropriate coat or jacket would round out your "
                f"wardrobe for cool-weather days."
            )
        if outer_suggestion not in result["shopping_suggestions"]:
            result["shopping_suggestions"].append(outer_suggestion)

    # ── STEP 7: Color Check ────────────────────────────────────────────────────
    step7 = {"step": 7, "name": "Color Coordination Check", "status": "ok", "output": ""}
    skin_tone = profile.get("skin_tone", "warm olive")
    color_result = score_outfit_colors(outfit, skin_tone)
    result["color_score"] = color_result

    step7["output"] = (
        f"Color score: {color_result['score']}/100 for skin tone '{skin_tone}'. "
        f"{len(color_result['flags'])} flag(s). "
        f"{color_result['flags'][0] if color_result['flags'] else 'All colors work well.'}"
    )
    reasoning.extend(color_result["notes"])
    steps.append(step7)

    # ── FINAL RESULT ──────────────────────────────────────────────────────────
    result["recommendation"] = outfit
    result["reasoning"] = reasoning

    return result
