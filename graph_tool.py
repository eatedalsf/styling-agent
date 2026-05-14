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
              title: Optional[str] = None,
              size_override: Optional[float] = None) -> None:
    """
    Add a styled node based on the entity type. Idempotent — pyvis
    silently overwrites duplicate IDs, but we guard anyway.

    `size_override` lets the caller bump the node's rendered radius
    to encode a SEMANTIC signal: how many times an item has been
    worn, how many pieces an outfit contains, etc. Node size now
    means something the user can interpret — see the legend block
    rendered next to every graph and graph/render.md for the rules.
    """
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
    final_size = float(size_override) if size_override is not None else style["size"]
    # Clamp so a heavily-worn item can't dwarf the User anchor, and an
    # unworn item still reads as a real node.
    final_size = max(14.0, min(50.0, final_size))
    net.add_node(
        node_id,
        label=display_label,
        color={"background": style["bg"], "border": style["border"]},
        shape=style["shape"],
        size=final_size,
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

    return _freeze_after_stabilization(net.generate_html(notebook=False))


# ─────────────────────────────────────────────
# Post-render: freeze layout after stabilization
# ─────────────────────────────────────────────

def _freeze_after_stabilization(html: str) -> str:
    """
    Inject a small JS snippet that disables physics ONCE the initial
    stabilization completes. The result: nodes settle into a clean
    layout and then stop moving — no perpetual jitter during the demo,
    no extra UI controls needed. Users can still drag nodes manually
    after freeze (dragging temporarily re-enables physics in vis.js
    only for the dragged subset, then it stops again).

    Idempotent: if the snippet is already present, returns html as-is.
    """
    sentinel = "/* wearly:freeze-after-stabilize */"
    if sentinel in html:
        return html

    inject = (
        "<script>"
        f"{sentinel}\n"
        "(function() {"
        "  function tryAttach() {"
        "    if (typeof network !== 'undefined' && network &&"
        "        typeof network.once === 'function') {"
        "      network.once('stabilizationIterationsDone', function() {"
        "        try {"
        "          network.setOptions({physics: {enabled: false}});"
        "        } catch (e) { /* swallow */ }"
        "      });"
        "      return true;"
        "    }"
        "    return false;"
        "  }"
        "  if (!tryAttach()) {"
        "    var n = 0;"
        "    var iv = setInterval(function() {"
        "      if (tryAttach() || ++n > 40) { clearInterval(iv); }"
        "    }, 50);"
        "  }"
        "})();"
        "</script>"
    )
    # Inject right before </body> so it runs after pyvis defines `network`.
    if "</body>" in html:
        return html.replace("</body>", inject + "</body>", 1)
    return html + inject


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

    # Wear-history map for node-size scaling. Heavily-worn items are
    # rendered larger so the graph's geometry encodes "what you reach
    # for most" — the same signal Wearly uses internally as the
    # freshness tie-breaker (see history_tool.get_freshness). Failure
    # to load just falls back to a flat size.
    try:
        from history_tool import get_history as _gh
        _wear_hist = _gh().get("history", {}) or {}
    except Exception:
        _wear_hist = {}

    # ── Outfit Recommendation (the centerpiece) ──
    # Outfit node size scales with how many pieces are in this outfit:
    #   1 piece  → 24px   (a one-piece dress, baseline)
    #   3 pieces → 30px
    #   6 pieces → 36px   (a fully-loaded everyday outfit)
    #   12+      → 44px   (capped)
    _outfit_size = min(44.0, 22.0 + 2.0 * len(outfit))
    of_label = f"Outfit · {len(outfit)} piece{'' if len(outfit) == 1 else 's'}"
    of_title = "Today's outfit"
    if outfit:
        of_title += "\n" + "\n".join(f"  · {i.get('name','—')}" for i in outfit[:8])
    of_title += f"\n\nSize encodes piece count: {len(outfit)}."
    _add_node(net, "outfit", of_label, "OutfitRecommendation",
              title=of_title, size_override=_outfit_size)
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
    #
    # Item node size encodes WEAR COUNT — the more often the user has
    # worn this piece (confirmed via the "Wear this outfit today"
    # button), the bigger its dot. Never-worn items stay at the
    # baseline. Heavy wearers cap out so the layout stays balanced.
    for item in outfit[:_MAX_ITEM_NODES_PER_RUN]:
        iid_src = item.get("id") or item.get("name") or "item"
        iid = f"item:{iid_src}"
        name = item.get("name", "—")
        wear_count = int((_wear_hist.get(iid_src) or {}).get("worn_count", 0) or 0)
        item_size = 18.0 + min(12.0, 2.0 * wear_count)
        meta_lines = [
            f"Color: {item.get('color','—')}",
            f"Type: {item.get('type','—')}",
            f"Formality: {item.get('formality','—')}",
            f"Worn: {wear_count} time{'' if wear_count == 1 else 's'} "
            f"(node size encodes this)",
        ]
        # User-added items get a "(your addition)" hint in the tooltip
        # so the graph also expresses who supplied which piece.
        if str(item.get("id", "")).startswith("U"):
            meta_lines.append("Source: your wardrobe additions")
        _add_node(net, iid, name, "WardrobeItem",
                  title=f"{name}\n" + "\n".join(meta_lines),
                  size_override=item_size)
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

    return _freeze_after_stabilization(net.generate_html(notebook=False))


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


# ─────────────────────────────────────────────
# LEGEND — the explicit "what does this graph mean?" block
# ─────────────────────────────────────────────

# Inspired by Dan McCreary's review of a classmate's graph: every
# graph needs an explicit legend. Node SIZE, COLOR, SHAPE, and edge
# DIRECTION all carry meaning, but if the meaning lives only in the
# code, the user can't read the graph. The dict below is the single
# source of truth that drives both `legend_for_app` (HTML for
# Streamlit) and the matching docs page.
LEGEND_DICT = {
    "library": {
        "name":  "pyvis",
        "wraps": "vis-network.js",
        "why":   ("Pyvis renders an interactive vis-network HTML "
                  "graph from Python with no external services. "
                  "Stdlib + Pillow + Streamlit are the only other "
                  "runtime deps. Neo4j was rejected because the "
                  "demo needs to run offline on Streamlit Cloud, "
                  "with no database daemon, no auth, no backups."),
    },
    "layout": {
        "kind":   "force-directed",
        "solver": "forceAtlas2Based",
        "params": {
            "gravitationalConstant": -110,
            "centralGravity":         0.02,
            "springLength":           170,
            "damping":                0.7,
            "avoidOverlap":           0.85,
        },
        "interaction": ("Drag any node to reposition; the spring "
                        "settles in ~0.5 s. Scroll to zoom, drag "
                        "background to pan. Hover for full tooltip."),
    },
    "node_size_meaning": {
        "OutfitRecommendation":
            "Diameter encodes piece count (1-piece dress ≈ 24px; "
            "fully-loaded 6-piece outfit ≈ 36px; capped at 44px).",
        "WardrobeItem":
            "Diameter encodes wear-count from history_tool: an "
            "unworn item is 18px, +2px per confirmed wear, "
            "capped at 30px. Lets you see at a glance which "
            "pieces you reach for most.",
        "User":      "Fixed anchor (32px) — the visual centerpoint.",
        "CalendarEvent / FitProfile / Weather":
            "Fixed by role (22–26px) so context nodes read as "
            "context, not as the centerpiece.",
        "Gaps / Feedback / ShoppingSuggestion":
            "Smaller (18–22px) — these are derived, not primary.",
    },
    "node_color_meaning": [
        ("User",                 "matte black",  "the wearer, visual anchor"),
        ("FitProfile",           "warm cream",   "user-declared body/skin/fit"),
        ("CalendarEvent",        "warm cream + dark border",
                                                "an occasion the agent reads"),
        ("WeatherSnapshot",      "warm cream",   "live or cached weather"),
        ("WardrobeItem",         "soft tan",     "a garment, shoe, or accessory"),
        ("OutfitRecommendation", "white + bold black border",
                                                "the centerpiece, today's outfit"),
        ("WardrobeGap",          "warm pink",    "a missing piece"),
        ("ShoppingSuggestion",   "warm pink",    "what to buy to close a gap"),
        ("Feedback",             "muted tan",    "your reject/regenerate signal"),
    ],
    "edge_label_meaning": [
        ("has_fit_profile",   "User → FitProfile"),
        ("has_event",         "User → CalendarEvent"),
        ("sees_weather",      "User → WeatherSnapshot"),
        ("addresses_event",   "Outfit → CalendarEvent"),
        ("recommends",        "Outfit → WardrobeItem"),
        ("informs",           "FitProfile / Weather → Outfit"),
        ("flags_gap",         "Outfit → WardrobeGap"),
        ("suggests_to_buy",   "WardrobeGap → ShoppingSuggestion"),
        ("was_rejected_with", "WardrobeItem → Feedback"),
        ("excludes_from_pool","Feedback → WardrobeItem (future run)"),
    ],
    "what_user_learns": (
        "The graph turns the agent's seven reasoning steps into a "
        "single picture. You can see at a glance: what context the "
        "agent read, which pieces it chose, which it rejected, and "
        "what's still missing. Heavier-worn items are bigger, "
        "fuller outfits are bigger — geometry encodes pattern."
    ),
    "how_it_connects_to_agent": (
        "Every node in the live-run graph corresponds to a value "
        "the agent actually computed during run_agent(). The "
        "reasoning trail explains the choices in prose; the graph "
        "explains them in shape. They're two views of the same run."
    ),
}


def legend_for_app() -> str:
    """
    Return a self-contained HTML legend ready to pass to
    st.markdown(..., unsafe_allow_html=True). Designed to render
    next to either the schema or live-run graph and answer Dan
    McCreary's questions without forcing the user into the docs.
    """
    L = LEGEND_DICT
    rows_color = "".join(
        f"<tr><td style='padding:0.18rem 0.6rem 0.18rem 0; "
        f"font-family:DM Sans,sans-serif; font-size:0.78rem; "
        f"color:#1C1917; white-space:nowrap;'>{name}</td>"
        f"<td style='padding:0.18rem 0.6rem 0.18rem 0; font-size:0.78rem; "
        f"color:#6E6E73;'>{color}</td>"
        f"<td style='padding:0.18rem 0; font-size:0.78rem; "
        f"color:#6E6E73;'>{desc}</td></tr>"
        for name, color, desc in L["node_color_meaning"]
    )
    rows_size = "".join(
        f"<li style='margin-bottom:0.3rem;'>"
        f"<strong style='color:#1C1917;'>{node_type}:</strong> "
        f"<span style='color:#6E6E73;'>{meaning}</span></li>"
        for node_type, meaning in L["node_size_meaning"].items()
    )
    rows_edges = "".join(
        f"<tr><td style='padding:0.15rem 0.6rem 0.15rem 0; "
        f"font-family:DM Mono,monospace; font-size:0.74rem; "
        f"color:#111111;'>{label}</td>"
        f"<td style='padding:0.15rem 0; font-size:0.78rem; "
        f"color:#6E6E73;'>{flow}</td></tr>"
        for label, flow in L["edge_label_meaning"]
    )
    return (
        "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
        "border-radius:6px; padding:1rem 1.15rem; margin-top:0.6rem; "
        "font-family:DM Sans,sans-serif;'>"

        "<div style='font-size:0.66rem; color:#8E8E93; "
        "letter-spacing:0.14em; text-transform:uppercase; "
        "font-weight:600; margin-bottom:0.4rem;'>Graph legend</div>"

        f"<div style='font-size:0.82rem; color:#2E2E2E; "
        f"line-height:1.55; margin-bottom:0.8rem;'>"
        f"<strong>Library:</strong> "
        f"{L['library']['name']} (wraps {L['library']['wraps']}).&nbsp; "
        f"<strong>Layout:</strong> {L['layout']['kind']} "
        f"({L['layout']['solver']}). "
        f"<em style='color:#6E6E73;'>"
        f"{L['layout']['interaction']}</em>"
        f"</div>"

        "<div style='font-size:0.7rem; color:#8E8E93; "
        "letter-spacing:0.10em; text-transform:uppercase; "
        "font-weight:600; margin-top:0.55rem; margin-bottom:0.25rem;'>"
        "Node size encodes</div>"
        f"<ul style='font-size:0.82rem; line-height:1.5; padding-left:1.1rem; "
        f"margin:0.2rem 0 0.55rem;'>{rows_size}</ul>"

        "<div style='font-size:0.7rem; color:#8E8E93; "
        "letter-spacing:0.10em; text-transform:uppercase; "
        "font-weight:600; margin-top:0.55rem; margin-bottom:0.25rem;'>"
        "Node colors</div>"
        f"<table style='border-collapse:collapse; margin-bottom:0.55rem;'>"
        f"{rows_color}</table>"

        "<div style='font-size:0.7rem; color:#8E8E93; "
        "letter-spacing:0.10em; text-transform:uppercase; "
        "font-weight:600; margin-top:0.55rem; margin-bottom:0.25rem;'>"
        "Edge labels (read source → target)</div>"
        f"<table style='border-collapse:collapse; margin-bottom:0.55rem;'>"
        f"{rows_edges}</table>"

        "<div style='font-size:0.74rem; color:#6E6E73; "
        "line-height:1.55; padding-top:0.55rem; "
        "border-top:1px solid #EEEEEE;'>"
        f"{L['what_user_learns']}<br><br>"
        f"<em>{L['how_it_connects_to_agent']}</em>"
        "</div>"
        "</div>"
    )
