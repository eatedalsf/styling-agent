"""
compact_kg.py — export one day's reasoning as a compact knowledge graph.

Pattern borrowed from the instructor's repeated suggestion in class
("save the entire session as a compact knowledge graph at the MD level
and use it as a startup"). Given a single `result` dict from `run_agent`,
produces a small, portable JSON graph capturing:

  - the User
  - the CalendarEvent / occasion
  - the WeatherSnapshot
  - the OutfitRecommendation
  - one node per WardrobeItem actually selected
  - one node per WardrobeGap
  - one node per ShoppingSuggestion
  - one node per Feedback (rejections, today's context)

with typed edges between them, plus the full reasoning trail and the
list of cited rule slugs. The shape mirrors graph/schema.md so the
exported file slots into the same in-app pyvis viewer or the in-book
vis-network.js viewer without translation.

The export is *one outfit, one day* — it is intentionally compact.
For multi-day analytics, future work would merge multiple of these.

No external dependencies; stdlib only.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from typing import Optional


_CITATION_RE = re.compile(r"\[[a-z-]+#R\d+\]")


def _extract_citations(reasoning: list) -> list:
    """Return every rule-citation slug found in the reasoning trail."""
    out: list = []
    seen: set = set()
    for line in reasoning or []:
        for m in _CITATION_RE.findall(line):
            if m not in seen:
                seen.add(m)
                out.append(m)
    return out


def build_compact_kg(result: dict, user_name: Optional[str] = None) -> dict:
    """Produce a compact-KG dict from one `run_agent` result.

    The structure intentionally matches `graph/graph.json`:

        {
          "entities":  [ {"id", "type", "label", "props": {...}}, ... ],
          "relations": [ {"source", "target", "predicate"}, ... ],
          "meta":      { "generated_at", "outfit_summary",
                          "cited_rules", "citations",
                          "color_score", "gap_count" }
        }

    Predicate vocabulary mirrors graph/schema.md
    (has_fit_profile, has_event, sees_weather, recommends,
    addresses_event, evaluated_against, flags_gap, suggests_to_buy,
    was_rejected_with, shaped_run) so the exported file drops into
    the in-book vis-network viewer without any translation step.

    Safe on partial results — every section is guarded.
    """
    entities: list = []
    relations: list = []
    seen_ids: set = set()

    def add_entity(eid: str, etype: str, label: str, **props) -> None:
        if not eid or eid in seen_ids:
            return
        seen_ids.add(eid)
        entities.append({
            "id": eid,
            "type": etype,
            "label": label,
            "props": {k: v for k, v in props.items() if v is not None},
        })

    def add_relation(src: str, tgt: str, predicate: str) -> None:
        if src in seen_ids and tgt in seen_ids:
            relations.append({"source": src, "target": tgt, "predicate": predicate})

    # --- User ---------------------------------------------------------
    profile = result.get("profile") or {}
    uname = user_name or profile.get("name") or "user"
    user_id = "user:" + re.sub(r"[^a-zA-Z0-9_-]", "_", uname.lower())
    add_entity(user_id, "User", uname,
               skin_tone=profile.get("skin_tone"),
               body_shape=profile.get("body_shape"))

    # FitProfile node (one per User, but it's a distinct entity in the schema)
    fit_id = user_id + ":fit"
    add_entity(fit_id, "FitProfile",
               f"{uname}'s fit profile",
               preferred_fit=profile.get("preferred_fit"))
    # Predicate vocabulary mirrors graph/schema.md so this export
    # drops into the in-book vis-network viewer without translation.
    add_relation(user_id, fit_id, "has_fit_profile")

    # Context source — "today" / "planner" / "everyday". When the
    # result came from the Planner's "Plan in detail" button it's
    # planning a FUTURE event; saying "Today's outfit" in the
    # exported KG (or the screen header) is incorrect. We use the
    # event title + date to build context-honest labels.
    _source = (result.get("source") or "").lower()
    _event_meta = result.get("event") or {}
    _ev_title = _event_meta.get("title") or ""
    _ev_date  = _event_meta.get("date") or ""
    if _source == "planner" and _ev_title:
        _outfit_label_prefix  = f"Outfit for {_ev_title}"
        _weather_label_prefix = f"Weather for {_ev_title}"
        _outfit_id_suffix = re.sub(
            r"[^a-zA-Z0-9_-]", "_",
            (_ev_date or _ev_title).lower()
        )[:32] or "planner"
    else:
        _outfit_label_prefix  = "Today's outfit"
        _weather_label_prefix = "Today's weather"
        _outfit_id_suffix = "today"

    # --- CalendarEvent / occasion ------------------------------------
    event = result.get("event") or {}
    if event:
        title = event.get("title", "Today")
        eid = "event:" + re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower())[:48]
        add_entity(eid, "CalendarEvent", title,
                   type=event.get("type"),
                   date=event.get("date"),
                   formality=event.get("formality"))
        add_relation(user_id, eid, "has_event")
        occasion_node_id = eid
    else:
        occasion_node_id = None

    # --- WeatherSnapshot ---------------------------------------------
    weather = result.get("weather") or {}
    if weather:
        wid = "weather:" + _outfit_id_suffix
        add_entity(wid, "WeatherSnapshot", _weather_label_prefix,
                   temperature_f=weather.get("temperature"),
                   conditions=weather.get("conditions"),
                   season=weather.get("season"))
        add_relation(user_id, wid, "sees_weather")
    else:
        wid = None

    # --- OutfitRecommendation ----------------------------------------
    rec = result.get("recommendation") or []
    if rec:
        rid = "outfit:" + _outfit_id_suffix
        labels = [i.get("name", "?") for i in rec]
        add_entity(rid, "OutfitRecommendation",
                   _outfit_label_prefix + ": " + ", ".join(labels)[:80],
                   piece_count=len(rec),
                   color_score=(result.get("color_score") or {}).get("score"))
        add_relation(user_id, rid, "received")
        if occasion_node_id:
            # Schema direction: OutfitRecommendation -> CalendarEvent.
            add_relation(rid, occasion_node_id, "addresses_event")
        if wid:
            add_relation(rid, wid, "evaluated_against")

        for item in rec:
            iid = "item:" + str(item.get("id") or item.get("name", "unknown"))
            add_entity(iid, "WardrobeItem", item.get("name", "?"),
                       type=item.get("type"),
                       color=item.get("color"),
                       formality=item.get("formality"))
            add_relation(rid, iid, "recommends")
    else:
        rid = None

    # --- Gaps + ShoppingSuggestions ----------------------------------
    # --- Gaps + ShoppingSuggestions ----------------------------------
    # Schema: OutfitRecommendation -flags_gap-> WardrobeGap
    #         WardrobeGap          -suggests_to_buy-> ShoppingSuggestion
    last_gap_id: Optional[str] = None
    for i, gap in enumerate(result.get("gaps") or []):
        gid = f"gap:{gap}".lower()
        add_entity(gid, "WardrobeGap", f"Missing: {gap}", piece_type=gap)
        if rid:
            add_relation(rid, gid, "flags_gap")
        last_gap_id = gid

    for i, sugg in enumerate(result.get("shopping_suggestions") or []):
        sid = f"suggestion:{i}"
        text = sugg if isinstance(sugg, str) else sugg.get("text", str(sugg))
        add_entity(sid, "ShoppingSuggestion", text[:60], full_text=text)
        # Prefer a gap-anchored edge if we have one; otherwise leave the
        # node free-standing (export still validates as a graph).
        if last_gap_id:
            add_relation(last_gap_id, sid, "suggests_to_buy")

    # --- Feedback (rejections + today's context) ---------------------
    # Schema direction: WardrobeItem -was_rejected_with-> Feedback.
    rejected = (result.get("rejected_context") or {}).get("reasons", [])
    for rej in rejected or []:
        fid = f"feedback:reject:{rej.get('item_id', 'x')}"
        add_entity(fid, "Feedback", f"Rejected: {rej.get('item_name', '?')}",
                   reason=rej.get("reason"))
        iid = "item:" + str(rej.get("item_id") or rej.get("item_name", "x"))
        if iid in seen_ids:
            add_relation(iid, fid, "was_rejected_with")

    tctx = result.get("todays_context")
    if tctx:
        fid = "feedback:context"
        add_entity(fid, "Feedback", f"Today's context: {tctx[:40]}",
                   text=tctx)
        if rid:
            # No schema predicate exists yet for "context shaped this run."
            # Use a stable, descriptive snake_case predicate so a future
            # schema addition can adopt the same name without breaking
            # exported files.
            add_relation(fid, rid, "shaped_run")

    return {
        "entities": entities,
        "relations": relations,
        "meta": {
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "outfit_summary": ", ".join(i.get("name", "") for i in rec) if rec else None,
            # `cited_rules` matches the dfec85e commit message; `citations`
            # kept as an alias for any existing consumer.
            "cited_rules": _extract_citations(result.get("reasoning") or []),
            "citations": _extract_citations(result.get("reasoning") or []),
            "color_score": (result.get("color_score") or {}).get("score"),
            "gap_count": len(result.get("gaps") or []),
        },
    }


def to_json(result: dict, user_name: Optional[str] = None, indent: int = 2) -> str:
    """Convenience: build_compact_kg + json.dumps."""
    return json.dumps(build_compact_kg(result, user_name), indent=indent)
