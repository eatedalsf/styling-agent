"""
Tool 9: Knowledge Graph rendering.

Two interactive graphs power the Knowledge-Graph story in the app:

  1. **Schema graph** — the abstract entity/relation model from
     graph/graph.json. Shown on the Before / After screen as
     "How Wearly models your day."

  2. **Live-run reasoning graph** — built dynamically from a single
     run_agent() result dict. Shows the specific
     User → CalendarEvent → Weather → WardrobeItem traversal that
     produced THIS outfit. Embedded in the outfit result screen.

Both render with pyvis (a small wrapper around vis-network.js) and
embed in Streamlit via st.components.v1.html(). pyvis bundles its
JavaScript inline (cdn_resources="in_line") so no external resources
load at runtime — the resulting HTML is fully self-contained.

No external services. No paid APIs. No secrets. Pyvis is a runtime
dependency declared in requirements.txt.

See `book/12-evidence-and-references.md` for the framing, and
`graph/schema.md` for the entity/relation catalog this module renders.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


# ─────────────────────────────────────────────
# Palette — matches the Streamlit app's design system.
# ─────────────────────────────────────────────

# Minimal white-on-white palette matching the rest of the app. Single
# matte-black accent for the high-importance roles (User, Outfit), a
# mid-grey for context (event / weather / fit profile), a light grey
# for items, and a restrained red for gap-style warning nodes.
_PALETTE = {
    "paper":       "#FFFFFF",
    "card":        "#FFFFFF",
    "subtle_card": "#FAFAFA",
    "item_card":   "#F5F5F5",
    "ink":         "#111111",
    "body":        "#2E2E2E",
    "secondary":   "#6E6E73",
    "edge":        "#D1D1D6",
    "edge_strong": "#111111",
    "accent":      "#111111",
    "warn":        "#FCF2F2",
    "warn_border": "#B91C1C",
}

# Visual styling per entity type. Same colors used in the schema and
# live-run graphs so a reviewer can recognize the role of each node.
# Sizes bumped slightly and shape variety reduced to make hover + click
# targets larger and labels more readable.
_NODE_STYLES: Dict[str, Dict[str, Any]] = {
    "User":                 {"bg": _PALETTE["ink"],         "border": _PALETTE["ink"],         "size": 32, "shape": "dot",          "font_color": "#FFFFFF"},
    "FitProfile":           {"bg": _PALETTE["subtle_card"], "border": _PALETTE["secondary"],   "size": 22, "shape": "box"},
    "CalendarEvent":        {"bg": _PALETTE["subtle_card"], "border": _PALETTE["ink"],         "size": 26, "shape": "box"},
    "WeatherSnapshot":      {"bg": _PALETTE["subtle_card"], "border": _PALETTE["secondary"],   "size": 22, "shape": "box"},
    "WardrobeItem":         {"bg": _PALETTE["item_card"],   "border": _PALETTE["edge"],        "size": 20, "shape": "dot"},
    "OutfitRecommendation": {"bg": _PALETTE["card"],        "border": _PALETTE["ink"],         "size": 34, "shape": "diamond"},
    "WardrobeGap":          {"bg": _PALETTE["warn"],        "border": _PALETTE["warn_border"], "size": 22, "shape": "triangleDown"},
    "ShoppingSuggestion":   {"bg": _PALETTE["warn"],        "border": _PALETTE["secondary"],   "size": 18, "shape": "triangleDown"},
    "Feedback":             {"bg": _PALETTE["item_card"],   "border": _PALETTE["secondary"],   "size": 18, "shape": "square"},
    "Concept":              {"bg": _PALETTE["item_card"],   "border": _PALETTE["edge"],        "size": 16, "shape": "dot"},
}

# Cap nodes per graph to keep the render legible.
_MAX_ITEM_NODES_PER_RUN = 12


def _new_network(height_px: int = 520):
    """Construct a pyvis Network configured with Wearly's palette + physics."""
    from pyvis.network import Network
    net = Network(
        height=f"{height_px}px", width="100%",
        bgcolor=_PALETTE["paper"], font_color=_PALETTE["ink"],
        notebook=False, cdn_resources="in_line", directed=True,
    )
    # Physics retuned for ~10–25-node graphs:
    #   - Stronger repulsion (-6500) so nodes don't crowd each other.
    #   - Longer springs (190) so edges read clearly between roles.
    #   - Heavier damping (0.6) so the simulation settles fast and
    #     stays put, instead of drifting after the user releases a node.
    #   - solver: forceAtlas2Based feels less twitchy than barnesHut on
    #     the medium-sized graphs Wearly renders.
    # Edges use curved smoothing so multi-hop paths don't overlap.
    # Node labels get a white stroke so they're readable on top of
    # neighbouring nodes when the layout briefly crowds during settle.
    net.set_options("""
    {
      "nodes": {
        "borderWidth": 2,
        "font": {"size": 14, "face": "DM Sans, sans-serif", "color": "#111111",
                 "strokeWidth": 3, "strokeColor": "#FFFFFF"},
        "shadow": false,
        "margin": 10
      },
      "edges": {
        "smooth": {"type": "cubicBezier", "forceDirection": "horizontal", "roundness": 0.4},
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.55}},
        "color": {"color": "#D1D1D6", "highlight": "#111111", "hover": "#111111"},
        "font":  {"size": 11, "color": "#6E6E73", "strokeWidth": 3, "strokeColor": "#FFFFFF",
                  "align": "middle"},
        "width": 1.2
      },
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -110,
          "centralGravity": 0.02,
          "springLength": 170,
          "springConstant": 0.06,
          "damping": 0.7,
          "avoidOverlap": 0.85
        },
        "stabilization": {"enabled": true, "iterations": 320, "fit": true},
        "minVelocity": 0.5
      },
      "interaction": {
        "hover": true, "tooltipDelay": 120, "navigationButtons": false,
        "zoomView": true, "dragView": true, "multiselect": false
      }
    }
    """)
    return net


def _add_node(net, node_id: str, label: str, type_name: str,
              title: Optional[str] = None) -> None:
    """Add a styled node based on the entity type. Idempotent — pyvis
    silently overwrites duplicate IDs, but we guard anyway."""
    style = _NODE_STYLES.get(type_name, _NODE_STYLES["Concept"])
    # Cap label length so long names don't overlap.
    display_label = label if len(label) <= 28 else (label[:25] + "…")
    # Node-specific font overrides (used by the User node which has a
    # dark background and needs white-on-dark text).
    node_font = None
    if style.get("font_color"):
        node_font = {"color": style["font_color"], "size": 14,
                     "face": "DM Sans, sans-serif",
                     "strokeWidth": 3, "strokeColor": style["bg"]}
    net.add_node(
        node_id,
        label=display_label,
        color={"background": style["bg"], "border": style["border"]},
        shape=style["shape"],
        size=style["size"],
        title=title or f"{type_name}: {label}",
        font=node_font,
    )


# ─────────────────────────────────────────────
# 1. Schema graph (abstract model)
# ─────────────────────────────────────────────

def _graph_json_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "graph", "graph.json"),
        os.path.join(here, "data", "graph", "graph.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def render_schema_graph_html() -> str:
    """
    Render the abstract Knowledge Graph schema (from graph/graph.json)
    as a self-contained HTML page suitable for streamlit.components.html.

    Falls back to a clean error message if the file is missing or
    malformed. Never raises.
    """
    path = _graph_json_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        return (
            f'<div style="font-family:DM Sans,sans-serif; color:#8A4A20; '
            f'background:#FDF3EE; padding:1rem; border:1px solid #EAD7C9; '
            f'border-radius:6px;">Schema graph unavailable: {e}</div>'
        )

    net = _new_network(height_px=560)
    seen_ids = set()

    for ent in data.get("entities", []):
        eid = ent.get("id")
        if not eid:
            continue
        _add_node(
            net, eid, ent.get("label", eid),
            ent.get("type", "Concept"),
            title=f"{ent.get('type','—')} · {ent.get('label','')}",
        )
        seen_ids.add(eid)

    # Edges: list-of-3-tuples [subject, predicate, object].
    for edge in data.get("edges", []):
        if not (isinstance(edge, (list, tuple)) and len(edge) >= 3):
            continue
        src, pred, dst = edge[0], edge[1], edge[2]
        # Some edge targets in graph.json point at concept strings rather
        # than catalogued entities (e.g. "work", "outerwear"). Render
        # those as small Concept nodes so the diagram stays complete.
        if dst not in seen_ids:
            _add_node(net, dst, dst, "Concept",
                      title=f"Concept · {dst}")
            seen_ids.add(dst)
        net.add_edge(src, dst, label=pred, title=pred)

    return net.generate_html(notebook=False)


# ─────────────────────────────────────────────
# 2. Live-run reasoning graph (dynamic, per outfit)
# ─────────────────────────────────────────────

def render_run_graph_html(result: Dict[str, Any]) -> str:
    """
    Build a graph from a single agent run dict, showing the actual
    traversal that produced today's outfit. Never raises — missing
    keys render as truncated graphs with the available data.
    """
    if not isinstance(result, dict):
        return (
            '<div style="font-family:DM Sans,sans-serif; color:#7C6F64; '
            'padding:1rem;">No result to render.</div>'
        )

    net = _new_network(height_px=540)

    profile = result.get("profile") or {}
    event   = result.get("event") or {}
    weather = result.get("weather") or {}
    outfit  = result.get("recommendation") or []
    gaps    = result.get("gaps") or []
    rejected = (result.get("rejected_context") or {}).get("reasons") or []

    # ── User ──
    user_name = profile.get("name", "You")
    _add_node(net, "user", user_name, "User",
              title=f"User · {user_name}")

    # ── Fit profile ──
    fit_bits = []
    if profile.get("body_shape"):  fit_bits.append(profile["body_shape"])
    if profile.get("skin_tone"):   fit_bits.append(profile["skin_tone"])
    if not fit_bits:               fit_bits.append("user-declared")
    _add_node(net, "fit", " · ".join(fit_bits), "FitProfile",
              title=("Fit profile (proportion preferences + skin tone, "
                     "user-declared, never inferred from images)"))
    net.add_edge("user", "fit", label="has_fit_profile")

    # ── Calendar event ──
    ev_label = event.get("title", "—") or "—"
    ev_meta_parts = []
    if event.get("date"): ev_meta_parts.append(str(event["date"]))
    if event.get("time"): ev_meta_parts.append(str(event["time"]))
    ev_meta = " · ".join(ev_meta_parts)
    _add_node(net, "event", ev_label, "CalendarEvent",
              title=f"Event: {ev_label}" + (f"\n{ev_meta}" if ev_meta else ""))
    net.add_edge("user", "event", label="has_event")

    # ── Weather snapshot ──
    w_city = weather.get("city", "—")
    w_temp = weather.get("temp_f", "—")
    w_cond = weather.get("condition", "—")
    _add_node(net, "weather", f"{w_city} · {w_temp}°F", "WeatherSnapshot",
              title=f"{w_city} · {w_temp}°F · {w_cond}")
    net.add_edge("user", "weather", label="sees_weather")

    # ── Outfit Recommendation (the centerpiece) ──
    of_label = f"Outfit · {len(outfit)} piece{'' if len(outfit) == 1 else 's'}"
    of_title = "Today's outfit"
    if outfit:
        of_title += "\n" + "\n".join(f"  · {i.get('name','—')}" for i in outfit[:8])
    _add_node(net, "outfit", of_label, "OutfitRecommendation", title=of_title)
    net.add_edge("outfit", "event", label="addresses_event")
    # Convey that fit + weather + occasion drove the outfit choice.
    net.add_edge("fit",     "outfit", label="informs")
    net.add_edge("weather", "outfit", label="informs")

    # ── Wardrobe items (capped for readability) ──
    # We do NOT draw a user→item "owns" edge here even though the
    # schema has one. With 5–8 items in a typical outfit, those
    # extra edges crowd around the User node and make the graph
    # read as a starburst. The "recommends" edge from Outfit to the
    # item is enough to communicate provenance, and Outfit already
    # links back to User via the event chain. Trade-off documented
    # in graph/render.md.
    for item in outfit[:_MAX_ITEM_NODES_PER_RUN]:
        iid_src = item.get("id") or item.get("name") or "item"
        iid = f"item:{iid_src}"
        name = item.get("name", "—")
        meta_lines = [
            f"Color: {item.get('color','—')}",
            f"Type: {item.get('type','—')}",
            f"Formality: {item.get('formality','—')}",
        ]
        # User-added items get a "(your addition)" hint in the tooltip
        # so the graph also expresses who supplied which piece.
        if str(item.get("id", "")).startswith("U"):
            meta_lines.append("Source: your wardrobe additions")
        _add_node(net, iid, name, "WardrobeItem",
                  title=f"{name}\n" + "\n".join(meta_lines))
        net.add_edge("outfit", iid, label="recommends")

    # ── Wardrobe Gaps (if any) ──
    for gap in gaps:
        gid = f"gap:{gap}"
        _add_node(net, gid, str(gap), "WardrobeGap",
                  title=f"Missing for this occasion: {gap}")
        net.add_edge("outfit", gid, label="flags_gap")

    # ── Feedback / reject-and-regenerate context ──
    for r in rejected[:5]:  # keep readable
        item_id = r.get("item_id")
        item_name = r.get("item_name", "rejected item")
        reason = r.get("reason", "rejected")
        if not item_id:
            continue
        fid = f"fb:{item_id}"
        _add_node(net, fid, reason, "Feedback",
                  title=f"You flagged '{item_name}': {reason}")
        # We may not have added the item node (it was rejected, so it
        # isn't in `outfit`). Add a faint trace if missing.
        target_iid = f"item:{item_id}"
        net.add_node(target_iid, label=item_name,
                     color={"background": _PALETTE["item_card"], "border": _PALETTE["edge"]},
                     shape="dot", size=14,
                     title=f"Excluded from this run: {item_name}")
        net.add_edge(fid, target_iid, label="excludes_from_pool")

    return net.generate_html(notebook=False)


# ─────────────────────────────────────────────
# Small helpers for the UI captions
# ─────────────────────────────────────────────

def run_graph_summary(result: Dict[str, Any]) -> Dict[str, int]:
    """
    Return summary stats for the live-run graph. Used by the Streamlit
    expander caption so the user has a quick read on graph complexity.
    """
    if not isinstance(result, dict):
        return {"nodes": 0, "items": 0, "gaps": 0, "rejections": 0}
    outfit = result.get("recommendation") or []
    gaps = result.get("gaps") or []
    rejected = (result.get("rejected_context") or {}).get("reasons") or []
    # Fixed: User + FitProfile + Event + Weather + Outfit = 5
    fixed = 5
    return {
        "nodes":      fixed + min(len(outfit), _MAX_ITEM_NODES_PER_RUN) + len(gaps) + len(rejected),
        "items":      len(outfit),
        "gaps":       len(gaps),
        "rejections": len(rejected),
    }


def schema_graph_summary() -> Dict[str, int]:
    """Return summary stats for the schema graph (read from graph.json)."""
    try:
        with open(_graph_json_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"entities": 0, "edges": 0}
    return {
        "entities": len(data.get("entities", [])),
        "edges":    len(data.get("edges", [])),
    }
