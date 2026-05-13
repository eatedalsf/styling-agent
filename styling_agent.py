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

# Rule citations — see rule_refs.py and skills/wearly-styling-agent/.
# `cite(slug)` returns "" silently for unknown slugs so the agent never
# crashes on a missing citation. The reasoning trail is still readable
# without the trailing tag; the tag adds traceability for UI deep-links
# and for the documentation-integrity test.
try:
    from rule_refs import cite
except Exception:
    def cite(_slug):  # type: ignore[misc]
        return ""


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

def run_agent(
    mode: str = "calendar",
    everyday_request: str = None,
    rejected_ids: list = None,
    rejection_reasons: list = None,
    todays_context: str = None,
) -> dict:
    """
    Main agent entry point.

    mode = "calendar"  → reads next upcoming event automatically
    mode = "everyday"  → uses everyday_request string (e.g. "gym", "work")

    rejected_ids:
        Optional list of wardrobe item ids the user has rejected. The
        agent will exclude these from the wardrobe pool in Step 4.

    rejection_reasons:
        Optional list of {"item_id", "item_name", "reason"} dicts that
        accompany rejected_ids. Used purely for the reasoning trace —
        every rejection reason is surfaced so the user can see WHY the
        outfit changed.

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
    rejected_ids = list(rejected_ids or [])
    rejection_reasons = list(rejection_reasons or [])
    todays_context = (todays_context or "").strip()
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
        "rejected_context": {
            "ids": rejected_ids,
            "reasons": rejection_reasons,
        },
        "todays_context": todays_context,
        "error": None
    }

    # ── STEP 1: Determine Occasion ───────────────────────────────────────────
    step1 = {"step": 1, "name": "Determine Occasion", "status": "ok", "output": ""}

    if mode == "calendar":
        calendar_result = get_upcoming_events(days_ahead=7)
        if not calendar_result["success"] or not calendar_result["events"]:
            # ── Routine fallback ──────────────────────────────────
            # When the calendar has no upcoming event, consult the
            # user's weekly routine for the current weekday + time.
            # The routine is the user's documented rhythm — not a
            # guess. If no block matches the current moment either,
            # default to everyday casual.
            try:
                from routine_tool import get_block_for_now
                _routine_blk = get_block_for_now()
            except Exception:
                _routine_blk = None

            if _routine_blk:
                step1["status"] = "fallback"
                step1["output"] = (
                    f"No calendar event for today. Routine match: "
                    f"{_routine_blk['weekday'].title()} "
                    f"{_routine_blk['start']}–{_routine_blk['end']} → "
                    f"{_routine_blk['occasion']} "
                    f"({_routine_blk['label'] or 'no label'})."
                )
                occasion = {
                    "type":      _routine_blk["occasion"],
                    "title":     _routine_blk["label"] or _routine_blk["occasion"].title(),
                    "formality": _routine_blk["occasion"],
                    "date":      "Today",
                    "time":      _routine_blk["start"],
                    "notes":     "From your weekly routine — Wearly falls back to "
                                 "this when the calendar is empty.",
                    "source":    "routine",
                }
            else:
                step1["status"] = "fallback"
                step1["output"] = (
                    "No upcoming calendar events and no matching routine block. "
                    "Defaulting to everyday casual."
                )
                occasion = {"type": "casual", "title": "Everyday Casual",
                            "formality": "casual", "date": "Today",
                            "time": "", "notes": ""}
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

    # Apply user rejections: drop any item the user previously rejected.
    rejected_set = set(rejected_ids)
    if rejected_set:
        before_total = len(clothing_pool) + len(shoes_pool) + len(accessories_pool)
        clothing_pool = [i for i in clothing_pool if i.get("id") not in rejected_set]
        shoes_pool = [i for i in shoes_pool if i.get("id") not in rejected_set]
        accessories_pool = [i for i in accessories_pool if i.get("id") not in rejected_set]
        after_total = len(clothing_pool) + len(shoes_pool) + len(accessories_pool)
        excluded = before_total - after_total
        step4_note = f" Excluded {excluded} previously rejected item(s)."
    else:
        step4_note = ""

    step4["output"] = (
        f"Found {len(clothing_pool)} clothing items, {len(shoes_pool)} shoe options, "
        f"{len(accessories_pool)} accessories for occasion: {occasion_tag} in {season}."
        + step4_note
    )
    steps.append(step4)

    # ── STEP 5: Build Outfit ──────────────────────────────────────────────────
    step5 = {"step": 5, "name": "Build Outfit", "status": "ok", "output": ""}
    outfit = []
    reasoning = []

    # Surface every rejection reason in the reasoning trail so the user
    # can see WHY this regenerated outfit is different from the previous one.
    # Surface today's free-text context first so the rest of the trail reads
    # in light of it. Honest framing: Wearly acknowledges the context and
    # uses it as a soft signal alongside fit/profile preferences, but does
    # NOT promise the context will override every other rule. The line is
    # informative; the underlying selection logic remains rule-driven.
    if todays_context:
        reasoning.append(
            f"Today's context: \"{todays_context}\" — noted alongside your fit "
            f"profile and event so the rest of the reasoning reads in light of it. "
            f"{cite('fit#R2')}"
        )

    for rej in rejection_reasons:
        nm = rej.get("item_name", "an item")
        rs = rej.get("reason", "rejected")
        reasoning.append(
            f"Skipping '{nm}' — you flagged it as: {rs}. {cite('wardrobe#R5')}"
        )

    # ── Wear-history tie-breaker ──────────────────────────────────────────
    # Sort each pool so fresher items (less recently / less frequently worn)
    # are picked first when multiple candidates are equally eligible. This
    # is a TIE-BREAKER, never a filter — see skill rule R3 in
    # skills/wearly-styling-agent/wear-history-rules.md.
    try:
        from history_tool import get_history, get_freshness, days_since_last_worn
        _history = get_history().get("history", {})
    except Exception:
        _history = {}
        def get_freshness(*_a, **_k): return 1.0  # type: ignore[assignment]
        def days_since_last_worn(*_a, **_k): return None  # type: ignore[assignment]

    # ── Fit profile (merged owner + user overlay) ─────────────────────────
    # Used for fit-alignment notes in the reasoning trail. The agent
    # respects whatever fields the user has shared and silently ignores
    # the rest. Body-positive language contract:
    # skills/wearly-styling-agent/fit-silhouette-rules.md R1.
    try:
        from fit_tool import get_fit_profile, fit_alignment_notes
        _fit_profile_full = get_fit_profile().get("profile", {})
    except Exception:
        _fit_profile_full = profile  # fall back to seed owner from step 2
        def fit_alignment_notes(*_a, **_k): return []  # type: ignore[assignment]

    def _by_freshness(items):
        return sorted(items, key=lambda x: -get_freshness(x.get("id", ""), _history))

    def _freshness_note(item):
        """Return an extra reasoning line if the chosen item is recently
        worn (low freshness) or under-worn (long unseen). Otherwise None."""
        iid = item.get("id", "")
        if not iid:
            return None
        f = get_freshness(iid, _history)
        days = days_since_last_worn(iid, _history)
        worn = _history.get(iid, {}).get("worn_count", 0)
        if f < 0.7:
            return (
                f"  Note: you've worn '{item['name']}' recently"
                + (f" ({days} day{'s' if days != 1 else ''} ago)" if isinstance(days, int) else "")
                + " — it's still the strongest fit for today."
            )
        if worn >= 1 and isinstance(days, int) and days >= 30:
            return (
                f"  Note: you haven't worn '{item['name']}' in {days} days "
                f"— bringing it back today."
            )
        return None

    clothing_pool    = _by_freshness(clothing_pool)
    shoes_pool       = _by_freshness(shoes_pool)
    accessories_pool = _by_freshness(accessories_pool)

    formality = occasion.get("formality", "casual")

    # Check for dress-worthy occasions first
    if occasion_tag in DRESS_OCCASIONS and formality in ["formal", "smart_casual"]:
        dresses = [i for i in clothing_pool if i["type"] == "dress"]
        if dresses:
            # Prefer higher formality dresses for formal occasions, then freshness.
            if formality == "formal":
                dresses.sort(key=lambda d: (0 if d["formality"] == "formal" else 1,
                                            -get_freshness(d.get("id", ""), _history)))
            outfit.append(dresses[0])
            reasoning.append(
                f"Selected '{dresses[0]['name']}' as a one-piece solution "
                f"for this {formality} occasion. {cite('occasion#R3')}"
            )
            for _fnote in fit_alignment_notes(dresses[0], _fit_profile_full):
                reasoning.append(_fnote)
            _note = _freshness_note(dresses[0])
            if _note: reasoning.append(_note)

    # If no dress selected, build top + bottom
    if not any(i["type"] == "dress" for i in outfit):
        tops = [i for i in clothing_pool if i["type"] == "top"]
        bottoms = [i for i in clothing_pool if i["type"] == "bottom"]
        activewear = [i for i in clothing_pool if i["type"] == "activewear"]

        if occasion_tag == "gym":
            if activewear:
                chosen_active = activewear[:2]
                outfit.extend(chosen_active)
                reasoning.append(
                    f"Selected activewear set: "
                    f"{', '.join(i['name'] for i in chosen_active)}. "
                    f"{cite('occasion#R2')}"
                )
                for piece in chosen_active:
                    _note = _freshness_note(piece)
                    if _note: reasoning.append(_note)
            else:
                reasoning.append("No activewear found in wardrobe for this gym occasion.")
        else:
            if tops:
                outfit.append(tops[0])
                reasoning.append(
                    f"Selected top: '{tops[0]['name']}' for its "
                    f"{tops[0]['formality']} formality. {cite('wardrobe#R3')}"
                )
                for _fnote in fit_alignment_notes(tops[0], _fit_profile_full):
                    reasoning.append(_fnote)
                _note = _freshness_note(tops[0])
                if _note: reasoning.append(_note)
            if bottoms:
                outfit.append(bottoms[0])
                reasoning.append(
                    f"Selected bottom: '{bottoms[0]['name']}' to pair with the top. "
                    f"{cite('occasion#R2')}"
                )
                for _fnote in fit_alignment_notes(bottoms[0], _fit_profile_full):
                    reasoning.append(_fnote)
                _note = _freshness_note(bottoms[0])
                if _note: reasoning.append(_note)

    # Add shoes
    if shoes_pool:
        outfit.append(shoes_pool[0])
        reasoning.append(f"Added shoes: '{shoes_pool[0]['name']}' appropriate for the occasion.")
        _note = _freshness_note(shoes_pool[0])
        if _note: reasoning.append(_note)

    # Add accessories (up to 2)
    for acc in accessories_pool[:2]:
        outfit.append(acc)
        reasoning.append(f"Added accessory: '{acc['name']}'.")
        _note = _freshness_note(acc)
        if _note: reasoning.append(_note)

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
                f"Added '{outer_pool[0]['name']}' as outerwear — temperature is "
                f"{temp}°F and {weather['layer_advice']} {cite('weather#R4')}"
            )
        else:
            # No outerwear matches this occasion. Don't force a wrong-style coat
            # onto the outfit; flag it as a wardrobe gap instead.
            outerwear_gap = True
            reasoning.append(
                f"Note: temperature is {temp}°F, but no {occasion_tag}-appropriate "
                f"outerwear was found in the wardrobe. Skipping outerwear rather "
                f"than forcing a mismatched coat. {cite('shopping#R2')}"
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
            f"Shopping suggestion: "
            f"{suggestions[0] if suggestions else 'Consider adding a versatile piece.'} "
            f"{cite('shopping#R3')}"
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

    # Augment suggestions with the user's favorite stores, when any are saved.
    # Adds a single extra line: "Check {stores} first — your saved favorite
    # store(s)." See shopping_tool.store_aware_suggestions().
    if result["gaps"] and result["shopping_suggestions"]:
        try:
            from shopping_tool import store_aware_suggestions
            result["shopping_suggestions"] = store_aware_suggestions(
                result["shopping_suggestions"],
                occasion_tag=occasion_tag,
            )
        except Exception:
            # Tool unavailable → leave suggestions unchanged. Never block the
            # agent on shopping tool failures.
            pass

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
