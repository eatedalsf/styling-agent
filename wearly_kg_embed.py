"""
Embed the Wearly Knowledge Graph viewer inside the Streamlit app.

The same viewer that lives at
``docs/sims/wearly-knowledge-graph/main.html`` (rendered by mkdocs in
the Intelligent Book) is reused here. The book version *fetches* the
JSON from the docs site; inside Streamlit there's no static-file
server, so we **inline** the graph JSON into ``window.__WEARLY_KG_DATA``
before the viewer runs and ``loadGraph()`` picks it up first.

A "Regenerate from my data" button calls the public generator with
``--include-user`` to write a *local-only* JSON (the gitignored
overlay path, never the committed seed file) and re-embeds.

Design language: the Alta-inspired matte-black-on-white Wearly app
palette. The viewer was recolored to match in v0.4.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

import streamlit as st


_HERE = os.path.dirname(os.path.abspath(__file__))
_VIEWER_PATH   = os.path.join(_HERE, "docs", "sims",
                              "wearly-knowledge-graph", "main.html")
_PUBLIC_JSON   = os.path.join(_HERE, "graph", "wearly-knowledge-graph.json")
_USER_JSON     = os.path.join(_HERE, "graph",
                              "wearly-knowledge-graph.user.json")
_GENERATOR     = os.path.join(_HERE, "scripts", "generate_wearly_kg.py")


def _read_viewer_html() -> str:
    with open(_VIEWER_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _read_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _regenerate_user_overlay() -> tuple[bool, str]:
    """Run the generator with --include-user and --out pointing at the
    gitignored user JSON path. Returns (ok, message)."""
    try:
        proc = subprocess.run(
            [sys.executable, _GENERATOR,
             "--include-user", "--output", _USER_JSON],
            cwd=_HERE, capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return (False, (proc.stderr or proc.stdout or "").strip()[:400])
        return (True, "Regenerated from your wardrobe + wear history.")
    except Exception as e:
        return (False, f"{type(e).__name__}: {e}")


def _build_embed_html(kg: dict[str, Any], iframe_height: int = 820) -> str:
    """Inject the JSON into the viewer HTML via window.__WEARLY_KG_DATA."""
    viewer = _read_viewer_html()
    payload = json.dumps(kg).replace("</", "<\\/")
    # Insert the data injection right after <head> so it's defined
    # before the viewer's own <script> block runs.
    injection = (
        "<script>window.__WEARLY_KG_DATA = "
        + payload
        + ";</script>"
    )
    # The viewer's main script tag is the vis-network <script src=…>;
    # we place ours immediately after the opening <head>.
    return viewer.replace("<head>", "<head>\n  " + injection, 1)


def render_wardrobe_knowledge_graph_section() -> None:
    """Render the 'Your wardrobe at a glance' section on the Wardrobe
    page. Safe to call unconditionally — guards every external file."""

    import streamlit.components.v1 as components

    st.markdown(
        '<div style="margin-top:1.4rem; margin-bottom:0.6rem;">'
        '  <div style="font-family:\'DM Serif Display\',serif; '
        '              font-size:1.35rem; color:#1C1917; line-height:1.1;">'
        'Your wardrobe at a glance'
        '  </div>'
        '  <div style="font-size:0.84rem; color:#6E6E73; '
        '              margin-top:0.35rem; max-width:54rem;">'
        '    A live knowledge-graph view of your closet. Bigger nodes '
        '    = signals you produced more of (worn often, many items, '
        '    occasion attended a lot). Click any node for details; '
        '    double-click to highlight its 1-hop neighborhood. '
        '    Domain rules and color-theory edges stay quiet so your '
        '    behavior reads first.'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Choose data source ---------------------------------------
    user_kg = _read_json(_USER_JSON)
    public_kg = _read_json(_PUBLIC_JSON)

    if user_kg is None and public_kg is None:
        st.info(
            "Knowledge Graph data not found. Generate the public seed "
            "with `python scripts/generate_wearly_kg.py`."
        )
        return

    use_user = user_kg is not None
    kg = user_kg if use_user else public_kg

    # --- Controls row ---------------------------------------------
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        md = kg.get("metadata", {})
        src_label = ("your wardrobe overlay" if use_user
                     else "public seed (Demo User)")
        st.caption(
            f"Showing **{md.get('node_count', '?')}** nodes · "
            f"**{md.get('edge_count', '?')}** edges · source: *{src_label}* · "
            f"version {md.get('version', '?')}"
        )
    with c2:
        if st.button("Regenerate from my data",
                     key="kg_regen_user",
                     help="Re-runs the generator including your local "
                          "wardrobe, wear history, and rejection log."):
            with st.spinner("Regenerating knowledge graph…"):
                ok, msg = _regenerate_user_overlay()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(f"Regenerate failed: {msg}")
    with c3:
        if use_user and st.button("Use seed view",
                                  key="kg_use_seed",
                                  help="Switch back to the public seed snapshot."):
            try:
                os.remove(_USER_JSON)
                st.rerun()
            except Exception as e:
                st.error(f"Could not remove overlay: {e}")

    # --- Embed -----------------------------------------------------
    try:
        html = _build_embed_html(kg)
        # Streamlit iframes don't pass document height through; we
        # pick a height that comfortably shows the graph + sidebar on
        # a 1080p screen. Scrollbar appears on smaller windows.
        import streamlit.components.v1 as components  # local import
        components.html(html, height=920, scrolling=True)
    except FileNotFoundError:
        st.warning(
            "Viewer template missing at "
            "`docs/sims/wearly-knowledge-graph/main.html`."
        )
    except Exception as e:
        st.error(f"Could not render the knowledge graph: {e}")


def render_knowledge_graph_page() -> None:
    """Dedicated 'Knowledge Graph' page (accessed from the user-menu
    dropdown). Same viewer as the book, embedded full-bleed so the
    user can explore the structured knowledge layer of their wardrobe.

    Encoding (same as the book):
      • Bigger circle = item worn more (worn_count × versatility roll-up)
      • Bigger color circle = many items in that color family
      • Bigger occasion/category circle = many items qualified for it
      • Click a node → details panel · double-click → 1-hop highlight

    Falls back to the public seed snapshot when the user-overlay
    JSON hasn't been generated yet; offers a one-click regenerate.
    """
    import streamlit.components.v1 as components

    # ── Page header ─────────────────────────────────────────────
    st.markdown(
        '<div style="margin-top:0.2rem; margin-bottom:1rem;">'
        '  <div style="font-family:\'DM Serif Display\',serif; '
        '              font-size:1.9rem; color:#1C1917; line-height:1.1;">'
        'Knowledge Graph'
        '  </div>'
        '  <div style="font-size:0.86rem; color:#6E6E73; '
        '              margin-top:0.35rem; max-width:62rem; line-height:1.55;">'
        'Your closet as a structured-knowledge graph. <strong>Bigger '
        'circles = signals you produced more of.</strong> A piece you '
        "wore six times across three occasions grows. A color you keep "
        "returning to grows. A category you've invested in (lots of "
        'tops, lots of outerwear) grows. Domain rules and color-theory '
        "edges stay quiet in the background so your behavior reads first."
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Choose data source ──────────────────────────────────────
    user_kg = _read_json(_USER_JSON)
    public_kg = _read_json(_PUBLIC_JSON)

    if user_kg is None and public_kg is None:
        st.info(
            "Knowledge Graph data not found. Generate the public seed "
            "with `python scripts/generate_wearly_kg.py`, then refresh."
        )
        return

    use_user = user_kg is not None
    kg = user_kg if use_user else public_kg
    md = kg.get("metadata", {})

    # ── Controls row ────────────────────────────────────────────
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        src_label = ("your wardrobe overlay" if use_user
                     else "public seed (Demo User)")
        st.caption(
            f"Showing **{md.get('node_count', '?')}** nodes · "
            f"**{md.get('edge_count', '?')}** edges · "
            f"source: *{src_label}* · "
            f"version {md.get('version', '?')}"
        )
    with c2:
        if st.button("Regenerate from my data",
                     key="kgpage_regen_user",
                     use_container_width=True,
                     help="Re-runs the generator including your local "
                          "wardrobe + wear history + rejection log."):
            with st.spinner("Regenerating knowledge graph…"):
                ok, msg = _regenerate_user_overlay()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(f"Regenerate failed: {msg}")
    with c3:
        if use_user and st.button("Use seed view",
                                  key="kgpage_use_seed",
                                  use_container_width=True,
                                  help="Switch back to the public seed snapshot."):
            try:
                os.remove(_USER_JSON)
                st.rerun()
            except Exception as e:
                st.error(f"Could not remove overlay: {e}")

    # ── Reading guide (matches the book's "What size means" sidebar) ──
    with st.expander("What you can see in this graph", expanded=False):
        st.markdown(
            "**Size signals**\n\n"
            "- **Worn-often items grow.** `WardrobeItem` size = "
            "`1 + worn_count × 0.20 + versatility × 0.10`. A jacket "
            "worn six times across three occasions reaches ~2.4×.\n"
            "- **Heavy color families grow.** A `ColorFamily` node "
            "rolls up the weights of every item that maps to it. A "
            "closet that keeps returning to navy makes the navy "
            "circle large.\n"
            "- **Categories you've invested in grow.** Lots of tops? "
            "The `Top` node is large. Lots of outerwear? Same.\n"
            "- **Occasions you attend often grow.** Calendar events "
            "of each type bump the `OccasionType` node — Work events "
            "on the calendar push the Work circle bigger.\n"
            "- **Recently worn items get a small bonus** (+0.2 if "
            "worn in the last 14 days) so today's rotation reads "
            "live.\n"
            "- **MVP items** — versatility ≥ 3 *and* worn ≥ 3 — get "
            "flagged in their metrics. Look for the items doing the "
            "most work in your closet.\n\n"
            "**Stories the graph tells**\n\n"
            "- **`WardrobeGap` triangles** appear when an occasion "
            "requires a type you don't own (e.g. no `outerwear` "
            "tagged for `gym`). Click one to see the gap.\n"
            "- **`WishlistItem` → `WardrobeGap`** edges connect a "
            "saved-to-wishlist item to the gap it would close.\n"
            "- **`OutfitRecommendation` nodes** appear for your "
            "recent confirmed outfits — each one connects to the "
            "items it contains via `CONTAINS_ITEM`.\n"
            "- **`days_since_worn`** sits on each item's metrics — "
            "items unworn for a long time stay small; recently-worn "
            "items get the bonus.\n\n"
            "**Domain layer stays quiet**\n\n"
            "Rule packs, weather bands, and skin-tone palettes stay "
            "at base size so the user-behavior layer reads first. "
            "Every line is typed (`OWNS`, `HAS_COLOR`, "
            "`SUITABLE_FOR`, `USES_RULE`, `POWERS`, "
            "`WISHLIST_CLOSES_GAP`, …) — click a node and the side "
            "panel lists all incoming and outgoing edges."
        )

    # ── Embed the viewer ────────────────────────────────────────
    try:
        html = _build_embed_html(kg)
        # Slightly taller than the Wardrobe section since this is a
        # dedicated page — give the graph plenty of room.
        components.html(html, height=1080, scrolling=True)
    except FileNotFoundError:
        st.warning(
            "Viewer template missing at "
            "`docs/sims/wearly-knowledge-graph/main.html`."
        )
    except Exception as e:
        st.error(f"Could not render the knowledge graph: {e}")
