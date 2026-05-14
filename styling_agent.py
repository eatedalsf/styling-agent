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
    target_event_id: str = None,
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
        calendar_result = get_upcoming_events(days_ahead=14)

        # If the caller specified a specific event (used by the
        # "Coming up this week" panel that plans for each upcoming
        # event), pick that one instead of the chronologically-next.
        if (target_event_id and calendar_result.get("success")
                and calendar_result.get("events")):
            picked = [e for e in calendar_result["events"]
                      if e.get("id") == target_event_id]
            if picked:
                calendar_result = {**calendar_result, "events": picked}

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
                _r_label  = _routine_blk.get('label') or 'no label'
                _r_loc    = _routine_blk.get('location') or ''
                _r_note   = _routine_blk.get('note') or ''
                _r_meta_bits = [s for s in (_r_loc, _r_note) if s]
                _r_meta = (" · " + ", ".join(_r_meta_bits)) if _r_meta_bits else ""
                step1["output"] = (
                    f"No calendar event for today. Routine match: "
                    f"{_routine_blk['weekday'].title()} "
                    f"{_routine_blk['start']}–{_routine_blk['end']} → "
                    f"{_routine_blk['occasion']} "
                    f"({_r_label}){_r_meta}."
                )
                # Build the routine-fallback occasion. We stuff
                # location + note into the occasion's notes field so
                # the reasoning trail downstream can mention them
                # ("remote", "office", "outdoor", "campus", …).
                _occ_notes_bits = [
                    "From your weekly routine — Wearly falls back to this "
                    "when the calendar is empty."
                ]
                if _r_loc:
                    _occ_notes_bits.append(f"Location: {_r_loc}.")
                if _r_note:
                    _occ_notes_bits.append(f"Note: {_r_note}.")
                occasion = {
                    "type":      _routine_blk["occasion"],
                    "title":     _r_label if _r_label != 'no label' else _routine_blk["occasion"].title(),
                    "formality": _routine_blk["occasion"],
                    "date":      "Today",
                    "time":      _routine_blk["start"],
                    "notes":     " ".join(_occ_notes_bits),
                    "source":    "routine",
                    "location":  _r_loc,
                    "routine_note": _r_note,
                }
                # Routine-only signals that nudge selection without
                # overriding occasion. Location words like "outdoor"
                # or "campus" should hint at weather sensitivity and
                # comfort; "office" at polish; "remote" at comfort.
                # We surface as a free-text todays_context the existing
                # _profile_alignment_bonus picks up. Caller-supplied
                # todays_context wins when both are present.
                if not todays_context:
                    _ctx_bits = []
                    if _r_loc:  _ctx_bits.append(f"routine location: {_r_loc}")
                    if _r_note: _ctx_bits.append(_r_note)
                    if _ctx_bits:
                        todays_context = " — ".join(_ctx_bits)
                        result["todays_context"] = todays_context
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

    # Use the MERGED profile (seed + user_profile.json overlay) as the
    # canonical source for Step 2's display string AND for result["profile"]
    # — the same source the fit/balance/color logic uses later in the run.
    # `get_owner_profile()` alone returns seed-only and silently drops the
    # user's overlay edits (body_shape, preferred_fit, etc.), causing
    # Step 2 to disagree with the rest of the reasoning.
    profile = profile_result["profile"]
    try:
        from fit_tool import get_fit_profile as _gfp
        _merged = (_gfp() or {}).get("profile") or {}
        if _merged:
            # Preserve a sensible name when the overlay didn't set one.
            if not _merged.get("name"):
                _merged["name"] = profile.get("name", "You")
            profile = _merged
    except Exception:
        pass
    result["profile"] = profile
    # Stamp the profile fingerprint so the UI can detect when a cached
    # result was generated against a now-outdated profile and surface
    # the "Profile updated — Regenerate" banner instead of stale data.
    try:
        from fit_tool import profile_hash as _profile_hash
        result["profile_hash"] = _profile_hash(profile)
    except Exception:
        result["profile_hash"] = ""
    step2["output"] = (
        f"Owner: {profile.get('name','You')} | "
        f"Body shape: {profile.get('body_shape') or '—'} | "
        f"Preferred fit: {profile.get('preferred_fit') or '—'} | "
        f"Skin tone: {profile.get('skin_tone') or '—'} | "
        f"Style: {', '.join(profile.get('style_preferences') or []) or '—'}"
    )
    steps.append(step2)

    # ── STEP 3: Check Weather ─────────────────────────────────────────────────
    # Honest per-event weather: when the occasion has a real date (a
    # Planner card for a future event, a calendar event a few days
    # out), ask Open-Meteo for THAT day's forecast — not "now".
    #
    # The three honest sources:
    #   "live"              → current readings, same-day event.
    #   "forecast"          → daily forecast, 1..15 days out.
    #   "seasonal-fallback" → coarse seasonal estimate when the date
    #                          is past, beyond 15 days, or the API is
    #                          unreachable. The fallback_reason tells
    #                          the user (and the reasoning trail)
    #                          which case we hit.
    step3 = {"step": 3, "name": "Check Weather", "status": "ok", "output": ""}
    _event_date_for_weather = (occasion.get("date") or "").strip()
    # "Today" sentinel from routine fallback isn't a real date — drop it.
    if _event_date_for_weather and _event_date_for_weather.lower() in ("today", ""):
        _event_date_for_weather = ""

    if _event_date_for_weather:
        try:
            from weather_tool import get_weather_for_date as _gwfd
            weather_result = _gwfd(_event_date_for_weather)
        except Exception:
            weather_result = get_weather()
    else:
        weather_result = get_weather()

    weather = weather_result["weather"]
    weather_source = (weather_result.get("source") or "").lower()
    weather_target = weather_result.get("target_date") or ""
    # Stash source + target_date on the weather object so the UI can
    # show "live" vs "forecast" vs "seasonal estimate" labels without
    # re-deriving from the agent's reasoning trail.
    weather["_source"]      = weather_source
    weather["_target_date"] = weather_target
    result["weather"]       = weather

    # Honest reasoning-trail framing per source.
    if weather_source == "forecast":
        step3["output"] = (
            f"Forecast for {weather_target} in {weather['city']}: "
            f"{weather['temp_f']}°F"
            + (f" (high {weather['temp_high_f']}°F / "
               f"low {weather['temp_low_f']}°F)"
               if weather.get('temp_high_f') is not None else "")
            + f", {weather['condition']}, "
            f"wind {weather['wind_mph']} mph, "
            f"{weather['precip_chance_pct']}% chance of rain. "
            f"{weather['layer_advice']}"
        )
    elif weather_source == "seasonal-fallback":
        step3["status"] = "fallback"
        why = weather.get("fallback_reason") or ""
        why_phrase = {
            "past-date":              "this event is in the past",
            "beyond-forecast-window":
                "this event is more than 15 days out (beyond the "
                "free Open-Meteo forecast window)",
            "api-error":              "the weather service was unreachable",
            "missing-data":           "the forecast returned no readings for that day",
        }.get(why, "no live forecast was available for this day")
        step3["output"] = (
            f"Seasonal estimate for {weather_target or 'this day'} "
            f"({why_phrase}): {weather['temp_f']}°F, "
            f"{weather['condition']}. {weather['layer_advice']}"
        )
    elif weather_result.get("error"):
        step3["status"] = "fallback"
        step3["output"] = (
            f"Weather note: {weather_result['error']} | "
            f"Using estimate: {weather['temp_f']}°F, {weather['condition']}."
        )
    else:
        # "live" — current readings.
        step3["output"] = (
            f"{weather['city']} (live): {weather['temp_f']}°F "
            f"(feels like {weather['feels_like_f']}°F), "
            f"{weather['condition']}, wind {weather['wind_mph']} mph, "
            f"{weather['precip_chance_pct']}% chance of rain. "
            f"{weather['layer_advice']}"
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

    # Wishlist taste inference (Goal 5). Computed once per run so it's
    # available both for the reasoning narrative (this section) AND for
    # the candidate scoring (Goal 4, further down). Module call is
    # cheap; on a clean wishlist it returns {}.
    try:
        from wardrobe_query import infer_wishlist_taste
        _wishlist_taste = infer_wishlist_taste()
    except Exception:
        _wishlist_taste = {}

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

    # Goal 5: surface the wishlist taste signal so the user can see
    # the agent is reading their saved aspirations. We write this
    # once per run, BEFORE the per-item lines, so subsequent picks
    # read "in light of" the taste profile.
    if _wishlist_taste.get("summary"):
        reasoning.append(
            f"{_wishlist_taste['summary']} I prioritized wardrobe items "
            f"that resemble this direction. {cite('wardrobe#R4')}"
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

    # ── Dress-vs-separates selection ─────────────────────────────────
    # Previous logic: dress branch only fired when occasion_tag was in
    # DRESS_OCCASIONS AND formality was "formal" / "smart_casual". That
    # meant a user with two casual dresses asking for a "dinner" outfit
    # got top+bottom every time, ignoring the dresses entirely. The new
    # rule keeps the same "formal occasions prefer a formal dress" bias
    # but lets the dress branch fire whenever:
    #   - occasion is naturally dress-worthy (formal / dinner / weekend
    #     brunch / casual), AND
    #   - at least one dress is in the candidate pool,
    #   - AND it's a stronger main-piece than the available top+bottom
    #     for this occasion (formality match, fit match, freshness).
    #
    # No more gating on a single string equality. The dress wins on its
    # merits or the separates win on theirs.
    dresses    = [i for i in clothing_pool if i.get("type") == "dress"]
    tops       = [i for i in clothing_pool if i.get("type") == "top"]
    bottoms    = [i for i in clothing_pool if i.get("type") == "bottom"]
    activewear = [i for i in clothing_pool if i.get("type") == "activewear"]

    # Profile-aware scoring signals are computed once per run so we
    # don't re-derive them per candidate.
    _prof = _fit_profile_full or profile or {}
    _pref_fit          = (_prof.get("preferred_fit") or "").lower().strip()
    _style_prefs       = [s.lower() for s in (_prof.get("style_preferences") or [])]
    _style_goals       = [s.lower() for s in (_prof.get("style_goals") or [])]
    _comfort_needs     = [c.lower() for c in (_prof.get("comfort_needs") or [])]
    _modesty           = (_prof.get("modesty_preference") or "").lower().strip()
    _highlights        = [h.lower() for h in (_prof.get("highlight_features") or [])]
    _balances          = [b.lower() for b in (_prof.get("balance_areas") or [])]
    _skin_tone         = (_prof.get("skin_tone") or "").lower().strip()

    # Wishlist taste signals (the dict itself was built earlier; here
    # we just pre-extract the fields used in the scoring loop so each
    # candidate doesn't re-read them).
    _wishlist_colors     = set(_wishlist_taste.get("colors") or [])
    _wishlist_categories = set(_wishlist_taste.get("categories") or [])
    _wishlist_formality  = (_wishlist_taste.get("preferred_formality") or "").lower()

    def _profile_alignment_bonus(item: dict) -> float:
        """
        How well does this item align with the user's stated
        profile? Returns a 0..~0.6 weight that nudges selection
        toward items the user said they want, BEFORE reasoning.

        Signals (each capped, additive, never negative):
          +0.20 preferred fit appears in name/formality
          +0.15 style preference appears in tags / name
          +0.10 style goal aligns with item formality
          +0.10 comfort need matches the item's tags
          +0.10 modesty preference compatible with the item
          +0.08 item color complements skin tone
          +0.08 wishlist signal: same color OR same category OR
                same formality bucket as what the user has saved

        Language contract: this function's results are CONSUMED by
        the selector. The visible reasoning lines are still written
        by fit_alignment_notes() (which is body-positive only).
        """
        s = 0.0
        item_form  = (item.get("formality") or "").lower()
        item_name  = (item.get("name") or "").lower()
        item_color = (item.get("color") or "").lower()
        item_tags  = [t.lower() for t in (item.get("tags") or [])]
        item_haystack = " ".join([item_name, item_form] + item_tags)

        # --- preferred fit (e.g. "tailored", "relaxed", "loose") ---
        if _pref_fit:
            if _pref_fit in item_haystack:
                s += 0.20
            elif _pref_fit == "tailored" and item_form in ("business", "smart_casual", "formal"):
                s += 0.15
            elif _pref_fit == "relaxed" and item_form in ("casual",):
                s += 0.15

        # --- style preferences (e.g. "classic", "elegant", "minimal") ---
        for pref in _style_prefs[:3]:
            if pref and (pref in item_haystack):
                s += 0.05      # up to 3 prefs => +0.15
        # Also reward "versatile" tagging when the user prefers
        # classic/elegant/minimal styles.
        if any(p in ("classic", "elegant", "minimal", "polished") for p in _style_prefs):
            if "versatile" in item_tags or item_form in ("business", "smart_casual"):
                s += 0.05

        # --- style goals (e.g. "elevated", "feminine", "modernized") ---
        if _style_goals:
            primary = _style_goals[0]
            if primary in ("elevated", "polished") and item_form in ("business", "smart_casual", "formal"):
                s += 0.10
            if primary in ("comfortable", "easy", "relaxed") and item_form in ("casual",):
                s += 0.10
            if primary in item_haystack:
                s += 0.05

        # --- comfort needs (e.g. "stretch", "soft", "breathable") ---
        for need in _comfort_needs:
            if need and need in item_haystack:
                s += 0.05
                break       # one match is enough; cap at +0.05

        # --- modesty preference ---
        # The skill rule (fit-silhouette-rules.md R2) says modesty
        # adjusts coverage, not body shape. We bias toward sleeved /
        # longer / less-skin tags when modesty is "moderate" or
        # "conservative". Never penalize — only add bonus to matching.
        if _modesty in ("moderate", "conservative"):
            modest_signals = ("sleeve", "long-sleeve", "long sleeve",
                              "midi", "maxi", "turtleneck", "high-neck",
                              "covered", "modest", "trouser", "wide-leg")
            if any(sig in item_haystack for sig in modest_signals):
                s += 0.10

        # --- skin tone harmony ---
        # We don't re-implement the full color_tool scoring per item
        # here — that runs at Step 7. But we can give a small
        # selection-time nudge for "obviously friendly" colors.
        if _skin_tone:
            warm_friendly = ("camel", "cream", "warm white", "olive",
                             "terracotta", "rust", "gold", "tan", "brown",
                             "burgundy", "blush")
            cool_friendly = ("navy", "white", "black", "grey", "silver",
                             "charcoal", "ice blue", "pearl")
            if "warm" in _skin_tone and any(c in item_color for c in warm_friendly):
                s += 0.08
            elif "cool" in _skin_tone and any(c in item_color for c in cool_friendly):
                s += 0.08

        # --- wishlist taste (rule-based, conservative) ---
        # Items resembling what the user already saves to wishlist
        # match their aspirational direction. Capped at +0.08 total.
        ws = 0.0
        if _wishlist_colors and item_color:
            if any(wc in item_color or item_color in wc for wc in _wishlist_colors):
                ws += 0.04
        if _wishlist_categories and item.get("type", "").lower() in _wishlist_categories:
            ws += 0.02
        if _wishlist_formality and item_form == _wishlist_formality:
            ws += 0.02
        s += min(0.08, ws)

        return s

    def _score_main_piece(item: dict) -> float:
        """
        Score a candidate top OR dress. Higher = better fit for this
        moment.

        Signal stack (cumulative, conservative):
          + formality match (most weighted, capped at 1.0)
          + freshness (wear-history tie-breaker, 0..0.4)
          + user-added bonus (very small, 0.15) so user items beat
            equally-ranked seed items
          + profile alignment (0..~0.6) — Goal 4: body/fit/skin-tone/
            comfort/modesty/style preferences influence selection
            BEFORE post-hoc reasoning, not just narration.
          + wishlist taste (folded into profile alignment) — Goal 5

        See book/04-styling-knowledge-base.md "Why rules, not ML."
        """
        s = 0.0
        if item.get("formality") == formality:
            s += 1.0
        elif occasion_tag == "formal" and item.get("formality") in ("formal", "business"):
            s += 0.6
        elif occasion_tag == "dinner" and item.get("formality") in ("formal", "business", "smart_casual"):
            s += 0.5
        elif occasion_tag == "casual" and item.get("formality") in ("casual", "smart_casual"):
            s += 0.5
        elif occasion_tag == "work" and item.get("formality") in ("business", "smart_casual", "formal"):
            s += 0.5
        # Freshness — 0.0..1.0 — already a 0-1 weight.
        s += 0.4 * get_freshness(item.get("id", ""), _history)
        # User-added preference.
        if str(item.get("id", "")).startswith("U"):
            s += 0.15
        # Profile + wishlist alignment.
        s += _profile_alignment_bonus(item)
        return s

    pick_dress = False
    if dresses and occasion_tag in DRESS_OCCASIONS + ["casual"]:
        # For formal: dress is almost always the right call.
        if occasion_tag == "formal":
            pick_dress = True
        else:
            # Compare best dress vs best top+bottom pair.
            best_dress = max(dresses, key=_score_main_piece)
            best_top   = max(tops,    key=_score_main_piece) if tops    else None
            best_btm   = max(bottoms, key=_score_main_piece) if bottoms else None
            dress_score = _score_main_piece(best_dress)
            pair_score  = (
                _score_main_piece(best_top) + _score_main_piece(best_btm)
                if (best_top and best_btm) else -1
            )
            # Pair score sums two pieces; halve for fair comparison.
            pick_dress = dress_score >= (pair_score / 2 if pair_score >= 0 else -1)

    if pick_dress:
        # Prefer formal-rated dresses for formal occasions, otherwise
        # sort by the same score the comparison used so it's consistent.
        if occasion_tag == "formal":
            dresses.sort(key=lambda d: (0 if d.get("formality") == "formal" else 1,
                                        -_score_main_piece(d)))
        else:
            dresses.sort(key=lambda d: -_score_main_piece(d))
        outfit.append(dresses[0])
        _is_user_item = str(dresses[0].get("id", "")).startswith("U")
        reasoning.append(
            f"Selected '{dresses[0]['name']}' as a one-piece solution "
            f"for this {formality} occasion"
            + (" — from your own wardrobe additions" if _is_user_item else "")
            + f". {cite('occasion#R3')}"
        )
        for _fnote in fit_alignment_notes(dresses[0], _fit_profile_full):
            reasoning.append(_fnote)
        _note = _freshness_note(dresses[0])
        if _note: reasoning.append(_note)

    # If no dress selected, build top + bottom
    if not any(i.get("type") == "dress" for i in outfit):
        if occasion_tag == "gym":
            if activewear:
                # Gym set = ONE top + ONE bottom from activewear pool,
                # never two bottoms. Earlier behavior took activewear[:2]
                # which produced "leggings + yoga pants" duplicates.
                # Classify by item name so even items tagged "activewear"
                # generically route to the right slot.
                def _gym_slot(item):
                    n = (item.get("name") or "").lower()
                    t = (item.get("name") or "").lower()
                    if any(k in n for k in (
                        "legging", "pant", "trouser", "jogger", "short",
                        "bottom", "skort")):
                        return "bottom"
                    if any(k in n for k in (
                        "bra", "tank", "tee", "top", "shirt", "crop",
                        "hoodie", "sweatshirt", "jacket")):
                        return "top"
                    # Default by activewear sub-types — fall back to top.
                    return "top"

                activewear.sort(key=lambda i: -_score_main_piece(i))
                gym_top = next((it for it in activewear
                                if _gym_slot(it) == "top"), None)
                gym_bot = next((it for it in activewear
                                if _gym_slot(it) == "bottom"), None)
                chosen_active = [x for x in (gym_top, gym_bot) if x]
                if chosen_active:
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
                    reasoning.append(
                        "No activewear top+bottom pair found in wardrobe "
                        "for this gym occasion.")
            else:
                reasoning.append("No activewear found in wardrobe for this gym occasion.")
        else:
            if tops:
                tops_sorted = sorted(tops, key=lambda i: -_score_main_piece(i))
                outfit.append(tops_sorted[0])
                _is_user = str(tops_sorted[0].get("id", "")).startswith("U")
                reasoning.append(
                    f"Selected top: '{tops_sorted[0]['name']}' for its "
                    f"{tops_sorted[0].get('formality','')} formality"
                    + (" — from your own wardrobe additions" if _is_user else "")
                    + f". {cite('wardrobe#R3')}"
                )
                for _fnote in fit_alignment_notes(tops_sorted[0], _fit_profile_full):
                    reasoning.append(_fnote)
                _note = _freshness_note(tops_sorted[0])
                if _note: reasoning.append(_note)
            if bottoms:
                bottoms_sorted = sorted(bottoms, key=lambda i: -_score_main_piece(i))
                outfit.append(bottoms_sorted[0])
                _is_user = str(bottoms_sorted[0].get("id", "")).startswith("U")
                reasoning.append(
                    f"Selected bottom: '{bottoms_sorted[0]['name']}' to pair with the top"
                    + (" — from your own wardrobe additions" if _is_user else "")
                    + f". {cite('occasion#R2')}"
                )
                for _fnote in fit_alignment_notes(bottoms_sorted[0], _fit_profile_full):
                    reasoning.append(_fnote)
                _note = _freshness_note(bottoms_sorted[0])
                if _note: reasoning.append(_note)

    # Add shoes — score so user-added shoes can win.
    # For gym occasions, re-rank toward athletic / training silhouettes
    # so a pair of leather sneakers ranked high by general scoring
    # doesn't beat a proper training shoe in the pool.
    if shoes_pool:
        _athletic_shoes_gap = False
        if occasion_tag == "gym":
            _athletic_keywords = (
                "sneaker", "trainer", "training", "running", "athletic",
                "sport", "performance", "cross-trainer",
            )
            _athletic_neg = ("leather", "loafer", "heel", "pump",
                              "stiletto", "ballet", "boot")
            def _athletic_score(it):
                n = (it.get("name") or "").lower()
                tags = " ".join((it.get("tags") or [])).lower()
                hay = n + " " + tags
                pos = sum(1 for k in _athletic_keywords if k in hay)
                neg = sum(1 for k in _athletic_neg if k in hay)
                # Items with athletic cues AND no negative cues lead.
                return (pos > 0, -neg, _score_main_piece(it))
            shoes_sorted = sorted(shoes_pool,
                                    key=lambda i: tuple(-x for x in _athletic_score(i)))
            if not any("sneaker" in (s.get("name") or "").lower()
                       or "trainer" in (s.get("name") or "").lower()
                       or "training" in (s.get("name") or "").lower()
                       or "running" in (s.get("name") or "").lower()
                       or "athletic" in (s.get("name") or "").lower()
                       for s in shoes_sorted[:1]):
                # No athletic shoe in pool — flag as a gym-specific gap.
                _athletic_shoes_gap = True
        else:
            shoes_sorted = sorted(shoes_pool, key=lambda i: -_score_main_piece(i))
        outfit.append(shoes_sorted[0])
        _is_user = str(shoes_sorted[0].get("id", "")).startswith("U")
        reasoning.append(
            f"Added shoes: '{shoes_sorted[0]['name']}' appropriate for the occasion"
            + (" — from your wardrobe additions" if _is_user else "")
            + "."
        )
        if _athletic_shoes_gap:
            reasoning.append(
                "  Note: no athletic training shoes were found in the "
                "wardrobe — this gym pick is the best available option, "
                f"but a dedicated training sneaker would be better. "
                f"{cite('shopping#R1')}"
            )
        _note = _freshness_note(shoes_sorted[0])
        if _note: reasoning.append(_note)
    else:
        _athletic_shoes_gap = False

    # Add accessories (up to 2) — score for the same reason.
    if accessories_pool:
        accessories_sorted = sorted(accessories_pool, key=lambda i: -_score_main_piece(i))
        for acc in accessories_sorted[:2]:
            outfit.append(acc)
            _is_user = str(acc.get("id", "")).startswith("U")
            reasoning.append(
                f"Added accessory: '{acc['name']}'"
                + (" (from your wardrobe additions)" if _is_user else "")
                + "."
            )
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
            # No outerwear matches this occasion. Don't force a wrong-
            # style coat onto the outfit; flag it as a wardrobe gap
            # instead. The Wardrobe-Gap card AND Step 6 already convey
            # this same information, so we do NOT add a duplicate
            # "Note: temperature is …" line to the reasoning trail —
            # previously the same fact appeared in three surfaces.
            outerwear_gap = True

    step5["output"] = f"Built outfit with {len(outfit)} pieces: {', '.join(i['name'] for i in outfit)}."
    steps.append(step5)

    # ── Tradeoff records for picked main pieces ──────────────────────────────
    # When the winning item has obvious misalignments with the user's
    # profile (color, fit, balance, modesty), surface them explicitly
    # instead of letting the reasoning read as unconditionally positive.
    # The same records feed Step 6's qualified-gap detection so a
    # poorly-aligned dress still generates a wardrobe gap.
    def _evaluate_tradeoffs(item: dict) -> list:
        """
        Return a list of `{dimension, severity, reason}` dicts for the
        ways `item` is less aligned with the user's profile. Empty
        list = the item passes all checks.

        Body-positive vocabulary throughout — every `reason` describes
        misalignment in preference-based terms (less aligned with,
        differs from), never as a flaw of the item or the user.

        Dimensions inspected:
          color    — skin-tone vs item color (warm/cool conflict)
          fit      — preferred_fit absent from name/tags/formality
          balance  — user has balance_areas set but item doesn't carry
                     a silhouette signal for any of them
          modesty  — modesty=moderate|conservative but item shows
                     revealing signals
        """
        out = []
        if not item or not isinstance(item, dict):
            return out
        name = (item.get("name") or "").lower()
        color = (item.get("color") or "").lower()
        form  = (item.get("formality") or "").lower()
        tags  = [t.lower() for t in (item.get("tags") or [])]
        sil   = (item.get("silhouette") or "").lower()
        haystack = " ".join([name, form, sil] + tags)

        # 1) Color × skin tone, weighted by garment placement.
        # A color near the face (top, dress, outerwear, scarf, necklace)
        # has high impact on skin-tone harmony. A color on the lower
        # body (skirt, trousers, jeans) has low impact and should not
        # generate a tradeoff on its own. Earlier behavior flagged a
        # white skirt as a "less aligned" tradeoff for warm olive
        # users, which contradicted the color score.
        skin = (profile.get("skin_tone") or "").lower().strip()
        item_type_lc = (item.get("type") or "").lower()
        _high_impact_types = ("top", "dress", "outerwear", "scarf")
        _med_impact_types  = ("accessory",)  # necklaces/earrings vary
        _low_impact_types  = ("bottom", "shoes")
        # Necklaces / earrings / hoops sit near the face — bump them up
        # by name even if the type is "accessory".
        name_lower = (item.get("name") or "").lower()
        near_face_acc = any(k in name_lower for k in
                             ("necklace", "earring", "hoop", "scarf"))
        if item_type_lc in _high_impact_types:
            placement_severity = "medium"
        elif near_face_acc:
            placement_severity = "medium"
        elif item_type_lc in _med_impact_types:
            placement_severity = "low"
        elif item_type_lc in _low_impact_types:
            # Low-impact: a bottom that mismatches the palette does not
            # create a tradeoff on its own. We skip the color check
            # entirely for these placements.
            placement_severity = None
        else:
            placement_severity = "low"

        if skin and color and placement_severity is not None:
            # Single source of truth: call color_tool.color_tier_for —
            # the same lookup that drives Step 7's color score. Only
            # "avoid" tier (the same colors that get the ⚠ flag in
            # the color check) generates a tradeoff. "best", "good",
            # and "neutral" never fire here. Previously this branch
            # used a hardcoded local set where "white", "black",
            # "pearl", "silver" were all "cool", which contradicted
            # the JSON-backed nuance (e.g. for warm-olive, gold is
            # best and black is good — neither should be a tradeoff).
            try:
                from color_tool import color_tier_for
                tier = color_tier_for(color, skin)
            except Exception:
                tier = "neutral"
            if tier == "avoid":
                out.append({
                    "dimension": "color",
                    "severity":  placement_severity,
                    "reason":    f"its {color} tone is less aligned with "
                                  f"your {skin} palette near the face",
                })

        # 2) Preferred-fit alignment
        pf = (profile.get("preferred_fit") or "").lower().strip()
        if pf:
            _PF_FORMALITY = {
                "tailored":   ("business", "smart_casual", "formal"),
                "structured": ("business", "smart_casual", "formal"),
                "fitted":     ("business", "smart_casual", "formal", "casual"),
                "relaxed":    ("casual", "smart_casual", "athletic"),
                "fluid":      ("casual", "smart_casual", "formal"),
                "loose":      ("casual", "athletic"),
            }
            if pf not in haystack and form not in _PF_FORMALITY.get(pf, ()):
                out.append({
                    "dimension": "fit",
                    "severity":  "low",
                    "reason":    f"the cut differs from your preferred "
                                  f"{pf} fit",
                })

        # 3) Balance areas — item should support at least one if user set them
        balance = [a.lower() for a in (profile.get("balance_areas") or [])]
        if balance:
            _SIGNALS = {
                "waist":      ("belted", "cinched", "wrap", "sheath",
                               "fit-and-flare", "fit and flare",
                               "peplum", "tailored", "tie-waist"),
                "neckline":   ("v-neck", "scoop", "square neck",
                               "boat neck", "halter", "off-shoulder",
                               "sweetheart", "cowl"),
                "shoulders":  ("structured shoulder", "strong shoulder",
                               "padded shoulder", "off-shoulder",
                               "puff sleeve", "puff-sleeve"),
                "hips":       ("peplum", "a-line", "flared",
                               "fit-and-flare", "wide-leg", "trumpet"),
                "legs":       ("mini", "slit", "cropped", "tapered",
                               "skinny", "slim-leg"),
            }
            _CATEGORY_AREAS = {
                "top": {"neckline", "shoulders", "arms", "collarbone"},
                "dress": {"neckline", "waist", "hips", "shoulders", "legs"},
                "bottom": {"waist", "hips", "legs"},
                "outerwear": {"shoulders", "neckline"},
            }
            item_type = (item.get("type") or "").lower()
            natural = _CATEGORY_AREAS.get(item_type, set())
            relevant_balance = [a for a in balance if a in natural]
            if relevant_balance:
                any_match = any(
                    sig in haystack
                    for area in relevant_balance
                    for sig in _SIGNALS.get(area, ())
                )
                if not any_match:
                    out.append({
                        "dimension": "balance",
                        "severity":  "low",
                        "reason":    f"the silhouette doesn't strongly "
                                      f"support balance at your "
                                      f"{', '.join(relevant_balance)}",
                    })

        # 4) Modesty
        modesty = (profile.get("modesty_preference") or "").lower().strip()
        if modesty in ("moderate", "conservative"):
            revealing = ("sleeveless", "spaghetti", "tank top", "crop",
                          "halter", "backless", "low-cut", "deep-v",
                          "mini ")
            if any(sig in haystack for sig in revealing):
                out.append({
                    "dimension": "modesty",
                    "severity":  "medium",
                    "reason":    "the coverage differs from your "
                                  f"{modesty} modesty preference",
                })

        return out

    # Evaluate each picked piece. Store as a flat list of tradeoff
    # records, each annotated with the item it came from so downstream
    # consumers (gap detector, reasoning surface) can quote it.
    tradeoffs: list = []
    for _it in outfit:
        for _td in _evaluate_tradeoffs(_it):
            tradeoffs.append({
                "item_id":   _it.get("id"),
                "item_name": _it.get("name"),
                "item_type": _it.get("type"),
                **_td,
            })
    result["tradeoffs"] = tradeoffs

    # Surface a one-line note per tradeoff in the reasoning trail so
    # the user can SEE why a less-aligned item was still selected.
    # Cites shopping-gap rules R1 (the "no better-aligned option"
    # framing) and fit-silhouette-rules R8 for fit/balance dimensions.
    if tradeoffs:
        # Group tradeoffs by item to avoid one-line-per-dimension
        # spam when an item has multiple misalignments.
        from collections import defaultdict as _dd
        by_item = _dd(list)
        for _td in tradeoffs:
            by_item[_td["item_id"]].append(_td)
        for _iid, _tds in by_item.items():
            _name = _tds[0]["item_name"]
            _reasons = "; ".join(t["reason"] for t in _tds)
            _cite = (cite("fit#R8") if any(t["dimension"] in
                     ("fit","balance","modesty") for t in _tds)
                     else cite("color#R2"))
            reasoning.append(
                f"  Note on '{_name}': selected as the best available "
                f"option, though {_reasons}. "
                f"This reveals a wardrobe gap. {_cite} {cite('shopping#R1')}"
            )

    # ── STEP 6: Check for Gaps ────────────────────────────────────────────────
    step6 = {"step": 6, "name": "Check for Wardrobe Gaps", "status": "ok", "output": ""}
    required = REQUIRED_PIECES.get(occasion_tag, ["top", "bottom"])
    gaps = check_gaps(outfit, required)

    if gaps:
        step6["status"] = "gap_found"
        # The output is reconciled below after qualified-gap promotion
        # so the wording covers true-missing vs qualified vs both. We
        # set an initial value so a check_gaps()-only path still has
        # readable copy if qualified-gap detection adds nothing.
        step6["output"] = f"Required piece missing: {', '.join(gaps)}."
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
        step6["output"] = "Core outfit complete — all required pieces present."
    steps.append(step6)

    # ── Qualified gaps from tradeoff records ──────────────────────────────
    # A piece is "present" in the wardrobe sense but its tradeoffs
    # reveal that the wardrobe lacks a well-aligned option. Promote
    # those tradeoffs to wardrobe gaps with concrete descriptors
    # built from the user's profile, not hand-written generic copy.
    # Cites shopping-gap rules R1 + fit-silhouette-rules R8.
    def _palette_for_skin(skin: str) -> list:
        skin = (skin or "").lower()
        if "warm" in skin:
            return ["terracotta", "olive", "burgundy", "cream",
                    "camel", "rust"]
        if "cool" in skin:
            return ["navy", "ice blue", "charcoal", "silver",
                    "pearl", "deep purple"]
        return ["cream", "navy", "olive", "burgundy"]

    def _silhouette_hint_for_shape(shape: str) -> str:
        shape = (shape or "").lower()
        if shape == "pear":
            return ("neckline detail or a structured upper "
                    "(a-line or fit-and-flare on bottom)")
        if shape == "apple":
            return ("a defined neckline and vertical lines through "
                    "the midsection")
        if shape == "hourglass":
            return "waist-defining cuts (wrap, fit-and-flare, belted)"
        if shape == "rectangle":
            return "waist-creating cuts (belted, peplum, fit-and-flare)"
        if shape == "inverted triangle":
            return "a fluid upper paired with a structured lower (a-line)"
        return "a silhouette that supports your preferred areas"

    def _length_hint_for_modesty(modesty: str) -> str:
        modesty = (modesty or "").lower()
        if modesty in ("moderate", "conservative"):
            return "midi or longer"
        return "any length you prefer"

    def _build_qualified_gap_descriptor(piece_type: str,
                                         dims: set) -> str:
        """Compose a one-sentence shopping descriptor from the profile,
        using only the dimensions that had tradeoffs."""
        parts = []
        skin = profile.get("skin_tone") or ""
        shape = profile.get("body_shape") or ""
        modesty = profile.get("modesty_preference") or ""
        pf = profile.get("preferred_fit") or ""

        if "color" in dims and skin:
            cols = _palette_for_skin(skin)[:3]
            parts.append(
                f"in a {skin} palette ({', '.join(cols)})"
            )
        if "balance" in dims or "fit" in dims:
            if shape:
                parts.append(_silhouette_hint_for_shape(shape))
            if pf and "fit" in dims:
                parts.append(f"a {pf}-leaning cut")
        if "modesty" in dims and modesty in ("moderate", "conservative"):
            parts.append(_length_hint_for_modesty(modesty))

        if not parts:
            return f"A {occasion_tag} {piece_type} that aligns with your profile"

        return (f"A {occasion_tag} {piece_type} "
                + ", with ".join(parts)
                + ".")

    # Group tradeoffs by piece type and dimension set, then synthesize
    # ONE descriptor per piece type (a dress with color+fit tradeoffs
    # generates one "warm-toned, fit-supportive dinner dress" gap,
    # not two separate gaps).
    if tradeoffs:
        from collections import defaultdict as _dd2
        dims_by_type = _dd2(set)
        for _td in tradeoffs:
            t = (_td.get("item_type") or "").lower()
            if t:
                dims_by_type[t].add(_td["dimension"])
        for piece_type, dims in dims_by_type.items():
            # Promote ONLY when at least one tradeoff has medium-or-high
            # severity. Earlier the "two low dimensions = promote" rule
            # over-triggered gaps for minor combined issues (e.g. a
            # casual top that's slightly off-fit AND slightly off-balance
            # would generate a gap even though both signals were weak).
            severities = [t["severity"] for t in tradeoffs
                          if (t.get("item_type") or "").lower() == piece_type]
            promote = any(s in ("medium", "high") for s in severities)
            if not promote:
                continue
            descriptor = _build_qualified_gap_descriptor(piece_type, dims)
            gap_key = f"qualified:{piece_type}"
            if gap_key not in result["gaps"]:
                result["gaps"].append(gap_key)
            if descriptor not in result["shopping_suggestions"]:
                result["shopping_suggestions"].append(descriptor)

    # Record outerwear gap (detected in Step 5) AFTER Step 6 so we don't
    # overwrite check_gaps results, and so shopping_suggestions keeps both.
    if outerwear_gap:
        if "outerwear" not in result["gaps"]:
            result["gaps"].append("outerwear")
        if occasion_tag == "gym":
            # Frame outerwear as a commute layer for the gym — never
            # suggest something like a trench coat as part of the workout.
            outer_suggestion = (
                "Optional commute layer: a light athletic windbreaker "
                "or running jacket would cover cool-weather travel to "
                "and from the gym."
            )
        else:
            outer_suggestion = (
                f"A {occasion_tag}-appropriate coat or jacket would round out your "
                f"wardrobe for cool-weather days."
            )
        if outer_suggestion not in result["shopping_suggestions"]:
            result["shopping_suggestions"].append(outer_suggestion)

    # Gym-specific qualified gap: athletic shoes missing from pool.
    # Surfaces alongside other gaps; the rendering layer will phrase
    # it as a "better-aligned option" rather than "missing".
    try:
        _athletic_shoes_gap
    except NameError:
        _athletic_shoes_gap = False
    if _athletic_shoes_gap and "qualified:shoes" not in result["gaps"]:
        result["gaps"].append("qualified:shoes")
        gym_shoe_suggestion = (
            "Athletic training sneakers (cushioned cross-trainers or "
            "running shoes) would better serve the gym than the casual "
            "leather styles currently in your wardrobe."
        )
        if gym_shoe_suggestion not in result["shopping_suggestions"]:
            result["shopping_suggestions"].append(gym_shoe_suggestion)

    # ── Reconcile Step 6 output with qualified gaps ──────────────
    # Step 6 was decided BEFORE qualified gaps were processed, so its
    # output may say "Outfit is complete" while result["gaps"] now
    # contains qualified:<type> entries from tradeoff promotion. Three
    # cases need different copy:
    #
    #   - true_missing only        : "Required piece missing: <type>."
    #   - qualified only           : "Core outfit complete; better-aligned
    #                                 option(s) identified for <type>."
    #   - true_missing + qualified : both, joined.
    #
    # This keeps Step 6, the wardrobe-gap card, and the reasoning
    # trail telling the same story.
    _all_gaps = result.get("gaps", []) or []
    _true_missing = [g for g in _all_gaps if not str(g).startswith("qualified:")]
    _qualified    = [str(g).split(":", 1)[1] for g in _all_gaps
                      if str(g).startswith("qualified:")]
    if _true_missing and _qualified:
        step6["status"] = "gap_found"
        step6["output"] = (
            f"Required piece missing: {', '.join(_true_missing)}; "
            f"better-aligned option identified for {', '.join(_qualified)}."
        )
    elif _qualified and not _true_missing:
        step6["status"] = "qualified_gap"
        step6["output"] = (
            f"Core outfit complete; better-aligned option identified "
            f"for {', '.join(_qualified)}."
        )
    elif _true_missing and not step6["output"].startswith("Required"):
        step6["status"] = "gap_found"
        step6["output"] = f"Required piece missing: {', '.join(_true_missing)}."

    # Augment suggestions with the user's favorite stores AND wishlist.
    # The store call is now gap-aware: a missing dress routes to the
    # favorite store that already has a saved dress on the wishlist
    # first, and if the wishlist already covers the gap we tell the
    # user instead of re-suggesting a new buy. See
    # shopping_tool.store_aware_suggestions().
    if result["gaps"] and result["shopping_suggestions"]:
        try:
            from shopping_tool import store_aware_suggestions
            primary_gap = result["gaps"][0] if result["gaps"] else None
            result["shopping_suggestions"] = store_aware_suggestions(
                result["shopping_suggestions"],
                occasion_tag=occasion_tag,
                gap=primary_gap,
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


# ──────────────────────────────────────────────────────────────────────────────
# AHEAD-OF-TIME PLANNING
# ──────────────────────────────────────────────────────────────────────────────

def plan_upcoming_events(limit: int = 5, days_ahead: int = 14,
                         seed_fallback: bool = False,
                         rotate: bool = True) -> list:
    """
    Pre-plan an outfit for each of the user's next `limit` calendar
    events within `days_ahead` days. Returns a list of `result` dicts —
    one per event, in chronological order. Each result has the same
    shape as a single run_agent() call.

    `rotate=True` (default) — Goal 7: cross-event awareness. Items
    already assigned to an event within the previous 2 days are
    marked rejected for the next event, so the agent picks a fresh
    main piece instead of repeating the same blouse for three work
    events in the same week. Shoes and accessories are NOT rotated
    out (those legitimately repeat across outfits and would force
    weird substitutions if hard-blocked). Outerwear is also kept
    because matching outerwear options are usually scarce.

    `seed_fallback=False` (default) — Planner is real-calendar-only.

    Errors during individual event runs are caught — that one event
    gets an `error`-stamped result, and the rest still plan.
    """
    try:
        cal_result = get_upcoming_events(days_ahead=days_ahead,
                                          seed_fallback=seed_fallback)
    except Exception:
        return []
    if not cal_result.get("success") or not cal_result.get("events"):
        return []

    events = cal_result["events"][: max(0, int(limit))]
    plans = []

    # Cross-event rotation tracking. Keyed by event date string so we
    # can compute proximity between consecutive picks. Only top /
    # bottom / dress / activewear are tracked — see docstring.
    _ROTATABLE_TYPES = {"top", "bottom", "dress", "activewear"}
    prior_picks: list = []   # list of (date_str, item_id, type)

    from datetime import datetime as _dt

    def _close_to_any(this_date: str, ids_iter) -> set:
        """Return the set of item ids that were used within 2 days of
        `this_date` in `prior_picks`. Items beyond that window are
        considered re-pickable."""
        try:
            d1 = _dt.strptime(this_date, "%Y-%m-%d").date()
        except Exception:
            return set()
        recent: set = set()
        for d_str, iid, _t in prior_picks:
            try:
                d0 = _dt.strptime(d_str, "%Y-%m-%d").date()
            except Exception:
                continue
            if abs((d1 - d0).days) <= 2:
                recent.add(iid)
        return recent

    for ev in events:
        ev_date = ev.get("date", "")
        try:
            rejected = sorted(_close_to_any(ev_date, prior_picks)) if rotate else []
            r = run_agent(
                mode="calendar",
                target_event_id=ev.get("id"),
                rejected_ids=rejected if rejected else None,
            )
            if rotate and rejected and r.get("recommendation"):
                # Friendly trail line so the user can SEE rotation in action.
                r.setdefault("reasoning", []).append(
                    f"Rotation: avoiding "
                    f"{', '.join(rejected[:3])}"
                    f"{' and others' if len(rejected) > 3 else ''} "
                    "because the same items were already assigned to "
                    "another event within 2 days."
                )
            plans.append(r)
            # Record the rotatable picks for the next iteration.
            if rotate:
                for it in (r.get("recommendation") or []):
                    if it.get("type") in _ROTATABLE_TYPES and it.get("id"):
                        prior_picks.append((ev_date, it["id"], it.get("type")))
        except Exception as e:
            plans.append({
                "event": ev,
                "recommendation": [],
                "reasoning": [f"Could not plan this event: {e}"],
                "error": str(e),
                "gaps": [],
                "color_score": None,
                "weather": None,
                "steps": [],
            })
    return plans


def plan_summary(plans: list) -> dict:
    """
    Goal 7: a tiny rule-based digest over a list of plans returned by
    plan_upcoming_events(). The Planner UI surfaces this above the
    per-event cards so the user gets a "what's the week look like?"
    glance without scrolling every card.

    Returns:
      {
        "total":            int,
        "by_occasion":      {"work": 3, "dinner": 1, ...},
        "any_gaps":         bool,
        "unique_gap_types": [...],          # ordered, deduped
        "preferred_stores": ["Aritzia", ...] # stores worth checking
        "narrative":        "You have 5 events this week — 3 work, 1
                             dinner, 1 weekend. Two are missing
                             outerwear; Aritzia is a good first
                             check based on your wishlist."
      }

    Errors are swallowed; an empty input returns an empty digest.
    """
    if not plans:
        return {
            "total": 0, "by_occasion": {}, "any_gaps": False,
            "unique_gap_types": [], "preferred_stores": [],
            "narrative": "",
        }
    by_occ: dict = {}
    gap_types: list = []
    for p in plans:
        ev = p.get("event") or {}
        occ = (ev.get("type") or "casual").lower()
        by_occ[occ] = by_occ.get(occ, 0) + 1
        for g in (p.get("gaps") or []):
            g_low = (g or "").lower()
            if g_low and g_low not in gap_types:
                gap_types.append(g_low)

    # Stores worth checking — favorite-store ranking is gap-aware
    # already inside store_aware_suggestions; here we just surface
    # the top names as a digest-friendly hint.
    pref_stores: list = []
    try:
        from shopping_tool import get_favorite_stores, get_wishlist
        favs = [s.get("name") for s in (get_favorite_stores().get("stores") or [])
                if s.get("name")]
        wishlist_stores = [
            w.get("preferred_store") for w in (get_wishlist().get("items") or [])
            if w.get("preferred_store")
        ]
        seen: set = set()
        for name in wishlist_stores + favs:   # wishlist matches lead
            if name and name.lower() not in seen:
                seen.add(name.lower())
                pref_stores.append(name)
    except Exception:
        pref_stores = []

    parts: list = []
    parts.append(
        f"You have {len(plans)} event{'s' if len(plans) != 1 else ''} "
        "in the planning window"
    )
    if by_occ:
        parts.append(
            " — " + ", ".join(
                f"{n} {occ}" for occ, n in
                sorted(by_occ.items(), key=lambda kv: -kv[1])
            )
        )
    if gap_types:
        parts.append(
            f". {len(gap_types)} gap type"
            f"{'s' if len(gap_types) != 1 else ''} to address: "
            + ", ".join(gap_types[:3])
        )
        if pref_stores:
            parts.append(
                f". Worth checking {pref_stores[0]}"
                + (f" or {pref_stores[1]}" if len(pref_stores) > 1 else "")
                + " first"
            )
    parts.append(".")
    narrative = "".join(parts)

    return {
        "total": len(plans),
        "by_occasion": by_occ,
        "any_gaps": bool(gap_types),
        "unique_gap_types": gap_types,
        "preferred_stores": pref_stores,
        "narrative": narrative,
    }


# ──────────────────────────────────────────────────────────────────────────────
# WEEKLY ROUTINE PLANNING
# ──────────────────────────────────────────────────────────────────────────────

def plan_routine_week() -> list:
    """
    Produce a Mon→Sun list of routine-driven outfit plans, one per
    weekday. Used by the "Routine Week Outfits" view in the app —
    separate from `plan_upcoming_events` because routine outfits are
    NOT calendar events; they're the user's normal weekly rhythm.

    For each weekday's first routine block (chronologically), we run
    the agent in `everyday` mode with that block's occasion. The
    block's location and note flow into the run as a free-text
    `todays_context` so the reasoning trail can mention "outdoor",
    "office", "remote", etc.

    Returns a list of 7 dicts. Days with no routine activity return
    a placeholder dict with `empty=True` so the UI can render a
    "no routine for <weekday>" card.

    Calendar events are not consulted here — that's a deliberate
    contract. The Planner view shows calendar events; the Routine
    view shows the recurring weekly rhythm; the two surfaces stay
    cleanly separated.
    """
    try:
        from routine_tool import get_weekly_blocks, DAYS
    except Exception:
        return []

    weekly = get_weekly_blocks() or []
    plans: list = []
    # Soft rotation across the week: items picked for earlier blocks
    # are passed as `rejected_ids` to later blocks so the agent
    # rotates to different pieces. Falls back to the same items when
    # the wardrobe is too small to rotate (run_agent's rejected_ids
    # is a SOFT preference, not a hard filter — it down-ranks rather
    # than excludes when nothing else fits).
    seen_this_week: list = []
    for blk in weekly:
        weekday = blk.get("weekday")
        if blk.get("empty"):
            plans.append({
                "weekday":      weekday,
                "empty":        True,
                "block_index":  blk.get("block_index", 0),
                "blocks_for_day": blk.get("blocks_for_day", 0),
                "event":   {"title": "No routine block",
                            "type":  "casual",
                            "date":  ""},
            })
            continue

        # Build a per-block "today's context" so the agent can speak
        # to location and notes in its reasoning trail.
        ctx_bits: list = []
        if blk.get("location"):
            ctx_bits.append(f"location: {blk['location']}")
        if blk.get("note"):
            ctx_bits.append(blk["note"])
        todays_ctx = " — ".join(ctx_bits) if ctx_bits else ""

        try:
            r = run_agent(
                mode="everyday",
                everyday_request=blk.get("label") or blk.get("occasion") or "casual",
                todays_context=todays_ctx,
                # Pass week-so-far picks as soft rejections to encourage
                # rotation. Wear-history isn't updated until the user
                # actually wears something, so this is the only signal
                # that varies the picks across the seven plans.
                rejected_ids=list(seen_this_week) if seen_this_week else None,
            )
        except Exception as e:
            plans.append({
                "weekday":     weekday,
                "empty":       False,
                "block_index": blk.get("block_index", 0),
                "blocks_for_day": blk.get("blocks_for_day", 0),
                "event":   {"title": blk.get("label") or blk.get("occasion"),
                            "type":  blk.get("occasion"),
                            "date":  ""},
                "error":   str(e),
                "recommendation": [],
                "reasoning": [f"Could not plan {weekday}: {e}"],
                "gaps": [],
            })
            continue

        # Stamp source so the result page (if the user clicks one of
        # these cards) renders "Outfit for <activity>" instead of
        # "Today's outfit". Routine-sourced results get source=routine.
        if isinstance(r, dict):
            r["source"]       = "routine"
            r["weekday"]      = weekday
            r["block_index"]  = blk.get("block_index", 0)
            r["blocks_for_day"] = blk.get("blocks_for_day", 0)
            # Surface the routine metadata on the event object so the
            # UI can render the activity name + location.
            ev = r.get("event") or {}
            ev["title"]     = blk.get("label") or blk.get("occasion", "Routine")
            ev["time"]      = f"{blk.get('start','')}"
            ev["type"]      = blk.get("occasion") or "casual"
            ev["location"]  = blk.get("location") or ""
            ev["note"]      = blk.get("note") or ""
            r["event"] = ev
            # Record this plan's picks so later days try different items.
            for it in (r.get("recommendation") or []):
                iid = it.get("id")
                if iid and iid not in seen_this_week:
                    seen_this_week.append(iid)
        plans.append(r)
    return plans
