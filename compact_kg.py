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
          "meta":      { "generated_at", "outfit_summary", "citations" }
        }

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
    add_relation(user_id, fit_id, "has-profile")

    # --- CalendarEvent / occasion ------------------------------------
    event = result.get("event") or {}
    if event:
        title = event.get("title", "Today")
        eid = "event:" + re.sub(r"[^a-zA-Z0-9_-]", "_", title.lower())[:48]
        add_entity(eid, "CalendarEvent", title,
                   type=event.get("type"),
                   date=event.get("date"),
                   formality=event.get("formality"))
        add_relation(user_id, eid, "plans")
        occasion_node_id = eid
    else:
        occasion_node_id = None

    # --- WeatherSnapshot ---------------------------------------------
    weather = result.get("weather") or {}
    if weather:
        wid = "weather:today"
        add_entity(wid, "WeatherSnapshot", "Today's weather",
                   temperature_f=weather.get("temperature"),
                   conditions=weather.get("conditions"),
                   season=weather.get("season"))
        add_relation(user_id, wid, "observes")
    else:
        wid = None

    # --- OutfitRecommendation ----------------------------------------
    rec = result.get("recommendation") or []
    if rec:
        rid = "outfit:today"
        labels = [i.get("name", "?") for i in rec]
        add_entity(rid, "OutfitRecommendation",
                   "Today's outfit: " + ", ".join(labels)[:80],
                   piece_count=len(rec),
                   color_score=(result.get("color_score") or {}).get("score"))
        add_relation(user_id, rid, "received")
        if occasion_node_id:
            add_relation(occasion_node_id, rid, "answered-by")
        if wid:
            add_relation(rid, wid, "evaluated-against")

        for item in rec:
            iid = "item:" + str(item.get("id") or item.get("name", "unknown"))
            add_entity(iid, "WardrobeItem", item.get("name", "?"),
                       type=item.get("type"),
                       color=item.get("color"),
                       formality=item.get("formality"))
            add_relation(rid, iid, "contains")
    else:
        rid = None

    # --- Gaps + ShoppingSuggestions ----------------------------------
    for i, gap in enumerate(result.get("gaps") or []):
        gid = f"gap:{gap}".lower()
        add_entity(gid, "WardrobeGap", f"Missing: {gap}", piece_type=gap)
        if rid:
            add_relation(rid, gid, "has-gap")

    for i, sugg in enumerate(result.get("shopping_suggestions") or []):
        sid = f"suggestion:{i}"
        text = sugg if isinstance(sugg, str) else sugg.get("text", str(sugg))
        add_entity(sid, "ShoppingSuggestion", text[:60], full_text=text)
        if rid:
            add_relation(rid, sid, "suggests")

    # --- Feedback (rejections + today's context) ---------------------
    rejected = (result.get("rejected_context") or {}).get("reasons", [])
    for rej in rejected or []:
        fid = f"feedback:reject:{rej.get('item_id', 'x')}"
        add_entity(fid, "Feedback", f"Rejected: {rej.get('item_name', '?')}",
                   reason=rej.get("reason"))
        if rid:
            add_relation(fid, rid, "rejects")

    tctx = result.get("todays_context")
    if tctx:
        fid = "feedback:context"
        add_entity(fid, "Feedback", f"Today's context: {tctx[:40]}",
                   text=tctx)
        if rid:
            add_relation(fid, rid, "shapes")

    return {
        "entities": entities,
        "relations": relations,
        "meta": {
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "outfit_summary": ", ".join(i.get("name", "") for i in rec) if rec else None,
            "citations": _extract_citations(result.get("reasoning") or []),
            "color_score": (result.get("color_score") or {}).get("score"),
            "gap_count": len(result.get("gaps") or []),
        },
    }


def to_json(result: dict, user_name: Optional[str] = None, indent: int = 2) -> str:
    """Convenience: build_compact_kg + json.dumps."""
    return json.dumps(build_compact_kg(result, user_name), indent=indent)
