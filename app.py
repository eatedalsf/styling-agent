"""
app.py — Streamlit Web Interface for Wearly
Run with: streamlit run app.py
"""

import sys
import os
import streamlit as st
import streamlit.components.v1 as components

# Support both structured layout (agent/styling_agent.py) and
# flat layout (styling_agent.py directly in the same folder)
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, "agent"))
sys.path.insert(0, os.path.join(_here, "tools"))

try:
    from agent.styling_agent import run_agent
    from tools.calendar_tool import get_upcoming_events
    from tools.weather_tool import get_weather
    from tools.wardrobe_tool import (
        get_owner_profile, get_wardrobe, get_user_wardrobe,
        save_user_item, suggest_colors_from_image,
    )
except ModuleNotFoundError:
    from styling_agent import run_agent
    from calendar_tool import get_upcoming_events
    from weather_tool import get_weather
    from wardrobe_tool import (
        get_owner_profile, get_wardrobe, get_user_wardrobe,
        save_user_item, suggest_colors_from_image,
    )

from datetime import datetime

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Wearly",
    page_icon="✦",
    # "centered" gives a ~700px main column that reads like a mobile-app
    # preview on desktop and goes full-width on phones. This is the core
    # of the mobile-first feel — combined with the responsive CSS below
    # that collapses st.columns to single-column under 640px viewports.
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# CUSTOM CSS — Minimal white-on-white aesthetic
# Inspired by altadaily.com — generous whitespace, sans-serif,
# single restrained matte-black accent. Replaces the warm-ivory +
# terracotta palette with a clean editorial look.
# Font: DM Serif Display (hero title only) + DM Sans (everything else)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #111111;
}
/* Pure white background — Alta's signature breathing room. */
[data-testid="stAppViewContainer"] {
    background: #FFFFFF !important;
}
/* Hide Streamlit's default top toolbar entirely so our own app bar
   (with brand + profile chip) becomes the page's true top. Without
   this, the toolbar overlays our app bar and clips the brand wordmark. */
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }

/* Generous top padding so the app bar sits cleanly below the browser
   chrome / the sidebar collapse handle. */
.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 4rem !important;
    max-width: 720px !important;
}
@media (max-width: 640px) {
    .block-container { padding-top: 1.4rem !important; }
}

/* ───── Product top app bar ───── */
.app-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 0.2rem 0.95rem;
    margin-bottom: 0.4rem;
    border-bottom: 1px solid #EEEEEE;
}
.brand {
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
}
.brand-mark {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: #111111;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-family: 'DM Serif Display', serif;
    font-size: 0.95rem;
    line-height: 1;
    transform: translateY(2px);
}
.brand-wordmark {
    font-family: 'DM Serif Display', serif;
    font-size: 1.45rem;
    color: #111111;
    line-height: 1;
    letter-spacing: -0.01em;
}
.brand-tag {
    font-size: 0.6rem;
    color: #8E8E93;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 600;
    border: 1px solid #E5E5E5;
    padding: 2px 7px;
    border-radius: 99px;
    background: #FFFFFF;
    transform: translateY(-2px);
}
.app-bar-right {
    display: flex; align-items: center; gap: 0.6rem;
}
/* ───── Profile popover (top-right chip dropdown) ─────
   The trigger is a real Streamlit popover styled as a pill: thin grey
   border, "Hi, <name>" label, built-in chevron. Hover + focus states
   keep the affordance obvious. Targeted via the global
   [data-testid="stPopover"] selector because this is the only popover
   in the app — see the comment in the app-bar render code below. */
/* Style the profile popover trigger (the only popover in the app, so
   we can target [data-testid="stPopover"] globally without affecting
   anything else). Nuke any background on every ancestor so the warm
   page tint doesn't bleed through, then re-assert pure white on the
   button itself. */
[data-testid="stPopover"],
[data-testid="stPopover"] > div,
[data-testid="stPopover"] > div > div {
    background: transparent !important;
    background-color: transparent !important;
}

[data-testid="stPopover"] button,
[data-testid="stPopover"] > div > button {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    color: #111111 !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 99px !important;
    padding: 0.32rem 0.95rem !important;
    min-height: 40px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
    white-space: nowrap !important;
}
[data-testid="stPopover"] button:hover,
[data-testid="stPopover"] > div > button:hover {
    background: #FAFAFA !important;
    background-color: #FAFAFA !important;
    border-color: #111111 !important;
    color: #111111 !important;
}
[data-testid="stPopover"] button:focus,
[data-testid="stPopover"] button:focus-visible {
    outline: 2px solid #111111 !important;
    outline-offset: 2px !important;
}

/* The popover panel — compact white card. Streamlit's popover renders
   in a portal layer with several wrapping divs; we force pure white +
   a thin border across every wrapper so no warm cream leaks through. */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [data-baseweb="block"],
[data-testid="stPopoverBody"],
div[data-testid="stPopoverBody"] > div {
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
}
[data-testid="stPopoverBody"] {
    border: 1px solid #EEEEEE !important;
    border-radius: 10px !important;
    box-shadow: 0 6px 24px rgba(0,0,0,0.08) !important;
    /* Compact menu — narrow card, not a full-width sheet. */
    width: 260px !important;
    max-width: 260px !important;
    min-width: 220px !important;
    padding: 0.45rem !important;
}

/* Menu items inside the popover — full-width plain rows, no card bg. */
[data-testid="stPopoverBody"] .stButton {
    margin: 0 !important;
}
[data-testid="stPopoverBody"] .stButton > button {
    width: 100% !important;
    text-align: left !important;
    background: #FFFFFF !important;
    color: #111111 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.45rem 0.65rem !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    min-height: 34px !important;
    justify-content: flex-start !important;
    box-shadow: none !important;
}
[data-testid="stPopoverBody"] .stButton > button:hover {
    background: #FAFAFA !important;
    color: #111111 !important;
}

/* Streamlit's divider inside the popover — thinner, less margin. */
[data-testid="stPopoverBody"] hr {
    margin: 0.35rem 0 !important;
    border-color: #EEEEEE !important;
}

/* The "Hi, <name>" header block inside the popover. */
.profile-menu-header {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.5rem 0.6rem 0.7rem;
}
.profile-menu-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    background: #111111;
    color: #FFFFFF;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    display: inline-flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.profile-menu-hi {
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    color: #111111;
    line-height: 1.15;
}
.profile-menu-sub {
    font-size: 0.72rem;
    color: #6E6E73;
    margin-top: 2px;
    letter-spacing: 0.01em;
}
.profile-menu-footnote {
    font-size: 0.7rem;
    color: #8E8E93;
    line-height: 1.45;
    padding: 0.2rem 0.6rem 0.4rem;
}
.profile-avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #111111;
    color: #FFFFFF;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-flex; align-items: center; justify-content: center;
}
.profile-name {
    font-size: 0.78rem; color: #2E2E2E; font-weight: 500;
    max-width: 84px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ───── Section nav pills row ───── */
.nav-row { margin: 0.4rem 0 1.1rem; }

/* Sidebar — pure white with a thin grey rule. */
[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #EEEEEE;
}
[data-testid="stSidebar"] * {
    color: #111111;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p {
    color: #6E6E73 !important;
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #FAFAFA !important;
    border: 1px solid #E5E5E5 !important;
    color: #111111 !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    color: #111111 !important;
    font-size: 0.92rem;
    letter-spacing: 0;
    text-transform: none;
    font-weight: 400;
}

/* Main title */
.main-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    color: #111111;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0;
}
.main-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    color: #6E6E73;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.3rem;
    margin-bottom: 2.5rem;
}

/* Cards — pure white on white, separated by a thin grey rule. */
.card {
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 6px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.1rem;
}
.card-title {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8E8E93;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

/* Outfit items */
.outfit-item {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid #F2F2F2;
    font-size: 0.95rem;
}
.outfit-item:last-child { border-bottom: none; }
.item-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #111111;
    flex-shrink: 0;
}
.item-swatch {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 1px solid rgba(0,0,0,0.10);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.25);
}
.item-color-chip {
    font-size: 0.72rem;
    color: #6E6E73;
    background: #F4F4F5;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: auto;
}

/* Score bar */
.score-bar-bg {
    background: #F2F2F2;
    border-radius: 6px;
    height: 6px;
    margin-top: 0.5rem;
}
.score-bar-fill {
    height: 6px;
    border-radius: 6px;
    background: #111111;
    transition: width 0.6s ease;
}

/* Step log */
.step-row {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid #F2F2F2;
    font-size: 0.87rem;
}
.step-row:last-child { border-bottom: none; }
.step-badge {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 3px;
    flex-shrink: 0;
    margin-top: 1px;
}
.badge-ok { background: #F0F7F2; color: #1D6033; }
.badge-fallback { background: #FBF5E6; color: #7D5A00; }
.badge-gap { background: #FCF2F2; color: #7A1D21; }
.step-name { font-weight: 600; color: #111111; white-space: nowrap; }
.step-output { color: #6E6E73; }

/* Reasoning */
.reason-item {
    padding: 0.45rem 0;
    border-bottom: 1px solid #F2F2F2;
    font-size: 0.88rem;
    color: #2E2E2E;
    display: flex;
    gap: 0.6rem;
}
.reason-num {
    color: #111111;
    font-weight: 700;
    flex-shrink: 0;
    font-size: 0.8rem;
    margin-top: 1px;
}

/* Before/after */
.compare-col {
    padding: 1.4rem 1.6rem;
    border-radius: 6px;
}
.compare-before { background: #FAFAFA; border-left: 3px solid #D1D1D6; }
.compare-after  { background: #FFFFFF; border-left: 3px solid #111111; border: 1px solid #EEEEEE; }
.compare-label {
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.9rem;
}
.compare-before .compare-label { color: #8E8E93; }
.compare-after  .compare-label { color: #111111; }
.compare-row {
    display: flex;
    justify-content: space-between;
    padding: 0.35rem 0;
    font-size: 0.87rem;
    border-bottom: 1px solid rgba(0,0,0,0.05);
}
.compare-row:last-child { border-bottom: none; }
.compare-key { color: #6E6E73; }
.compare-val { font-weight: 600; }

/* Event badge */
.event-type-badge {
    display: inline-block;
    font-size: 0.7rem;
    letter-spacing: 0.06em;
    text-transform: none;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 99px;
    background: #FAFAFA;
    color: #111111;
    border: 1px solid #E5E5E5;
    margin-bottom: 0.6rem;
}

/* Gap alert */
.gap-alert {
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-left: 3px solid #111111;
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-top: 0.5rem;
}
.gap-title { font-weight: 600; color: #111111; font-size: 0.88rem; margin-bottom: 0.5rem; }
.gap-item { font-size: 0.86rem; color: #2E2E2E; padding: 0.2rem 0; }

/* Weather */
.weather-block {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    flex-wrap: wrap;
}
.weather-temp {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #111111;
    line-height: 1;
}
.weather-detail {
    font-size: 0.82rem;
    color: #6E6E73;
    line-height: 1.8;
}
.weather-advice {
    font-size: 0.84rem;
    color: #2E2E2E;
    background: #FAFAFA;
    padding: 0.5rem 0.9rem;
    border-radius: 6px;
    margin-top: 0.5rem;
    border: 1px solid #EEEEEE;
}

/* Default button (secondary actions) — white card, dark text, thin border. */
.stButton > button {
    background: #FFFFFF !important;
    color: #111111 !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 99px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.01em !important;
    text-transform: none !important;
    padding: 0.5rem 0.85rem !important;
    font-weight: 500 !important;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease !important;
}
.stButton > button:hover {
    background: #F5F5F5 !important;
    border-color: #111111 !important;
    color: #111111 !important;
}
/* Primary button — solid black, white text. Alta-style CTA. */
.stButton > button[kind="primary"] {
    background: #111111 !important;
    color: #FFFFFF !important;
    border: 1px solid #111111 !important;
    border-radius: 6px !important;
    font-size: 0.95rem !important;
    padding: 0.82rem 1.6rem !important;
    box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: #2E2E2E !important;
    border-color: #2E2E2E !important;
    color: #FFFFFF !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(1px) !important;
}

/* Full-width primary button so CTAs feel app-like on mobile */
.stButton > button {
    width: 100% !important;
    min-height: 48px !important;
}

/* Mobile-first responsive layer
   ─────────────────────────────────────────────────────────
   Streamlit's st.columns does NOT auto-collapse on small viewports.
   Without this rule, two-card rows become unreadably cramped on phones.
   Below 640px we force every column inside a horizontal block to take
   the full row width and stack vertically. */
@media (max-width: 640px) {
    [data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
        gap: 0.9rem !important;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    .main-title { font-size: 2.4rem !important; line-height: 1.05 !important; }
    .main-subtitle { font-size: 0.82rem !important; margin-bottom: 1.6rem !important; }
    .card { padding: 1.1rem 1.2rem !important; }
    .weather-temp { font-size: 2rem !important; }
}

/* Tighten the title on all viewports so it doesn't dominate the
   ~700px centered column on desktop. */
.main-title { font-size: 2.8rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

TYPE_EMOJI = {
    "top": "👚", "bottom": "👖", "dress": "👗",
    "outerwear": "🧥", "activewear": "🩱", "shoes": "👠",
    "accessories": "💍", "accessory": "💍"
}

OCCASION_EMOJI = {
    "work": "💼", "gym": "🏋️", "dinner": "🍽️",
    "formal": "🥂", "casual": "☕", "formal_event": "🥂"
}

def item_emoji(item):
    # Retained for backward compatibility but no longer used in the UI —
    # outfit items now render with a real color swatch (see color_to_swatch).
    t = item.get("type", "").lower()
    if t in TYPE_EMOJI:
        return TYPE_EMOJI[t]
    if "shoe" in item.get("name", "").lower() or "boot" in item.get("name", "").lower() or "heel" in item.get("name", "").lower() or "sneaker" in item.get("name", "").lower():
        return "👠"
    if any(w in item.get("name","").lower() for w in ["earring","necklace","scarf","bag","tote","clutch"]):
        return "💍"
    return "✨"

# Map common clothing color names to display hex values for the swatch
# circles. Fashion apps recognize garments by color, not by icon — so we
# render a real swatch instead of an emoji glyph.
COLOR_HEX = {
    "white":         "#F4EFE8",
    "ivory":         "#F1E7D6",
    "cream":         "#EFE3CC",
    "black":         "#1C1917",
    "charcoal":      "#2E2A27",
    "grey":          "#9A938C",
    "gray":          "#9A938C",
    "navy":          "#1F2A44",
    "dark indigo":   "#1F2347",
    "blue":          "#4A6FA5",
    "pale blue":     "#B5C9D9",
    "olive":         "#7A7548",
    "sage green":    "#9DA88B",
    "camel":         "#B89878",
    "tan":           "#C9A77F",
    "nude":          "#D9BFA7",
    "blush":         "#E5BBAD",
    "pink":          "#E8B6B0",
    "burgundy":      "#6B2C2A",
    "red":           "#A03A32",
    "rust":          "#A85A3C",
    "terracotta":    "#C17F5A",
    "burnt orange":  "#B2562E",
    "gold":          "#C9A968",
    "silver":        "#BFC1C2",
    "white/gold":    "#E8DAA8",
}

def _resolve_image_path(rel_or_abs: str) -> str:
    """Resolve a wardrobe image path (typically `wardrobe_images/UC001.png`)
    to an absolute path that lives next to wardrobe.json."""
    if not rel_or_abs:
        return ""
    if os.path.isabs(rel_or_abs):
        return rel_or_abs
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, rel_or_abs)


def _image_to_data_uri(path: str) -> str:
    """Return a `data:image/png;base64,...` URI for a local image, or '' on any failure."""
    try:
        import base64
        with open(_resolve_image_path(path), "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except Exception:
        return ""


def color_to_swatch(color_str: str) -> str:
    """Return a display hex for a garment color name (graceful fallback)."""
    if not color_str:
        return "#C8B8A8"
    c = color_str.lower().strip()
    if c in COLOR_HEX:
        return COLOR_HEX[c]
    # Token fallback — handle multi-word colors like "dark blue" or "warm white"
    for token in c.split():
        if token in COLOR_HEX:
            return COLOR_HEX[token]
    return "#C8B8A8"

def score_color(score):
    # Minimal palette: dark for strong, mid-grey for fine, muted red for low.
    # Keeps the gauge readable without breaking the white-on-white aesthetic.
    if score >= 80: return "#111111"   # confident matte black
    if score >= 60: return "#4A4A4A"   # neutral grey
    return "#B91C1C"                    # restrained warning red


# ─────────────────────────────────────────────
# SESSION STATE — section routing + mock profile
# ─────────────────────────────────────────────

if "section" not in st.session_state:
    st.session_state["section"] = "home"

# Query-param routing — lets clickable HTML links (e.g. the profile chip
# in the top app bar) navigate the app without a full reload. Reads
# ?section=<key> on every rerun and updates session state to match.
# `_VALID_SECTIONS` is consulted lower in the file; we guard with a
# small inline set here so the import order doesn't matter.
_qp = st.query_params.get("section")
if _qp in {"home", "today", "wardrobe", "shop", "profile", "demo"}:
    if st.session_state["section"] != _qp:
        st.session_state["section"] = _qp
    # Clear the query param so the address bar stays clean and a manual
    # refresh doesn't re-trigger the navigation.
    try:
        st.query_params.clear()
    except Exception:
        pass
if "result" not in st.session_state:
    st.session_state["result"] = None
if "signed_in" not in st.session_state:
    # Mock auth state. Real authentication is future work. The UI shows
    # a profile chip either way so the product feels owned by a person.
    st.session_state["signed_in"] = True
if "everyday_choice" not in st.session_state:
    st.session_state["everyday_choice"] = "Work"
if "last_run" not in st.session_state:
    # Remember the most recent invocation so "Regenerate" can replay it
    # with accumulated rejection context.
    st.session_state["last_run"] = {"mode": "calendar", "everyday_request": None}
if "rejected_ids" not in st.session_state:
    st.session_state["rejected_ids"] = []
if "rejection_reasons" not in st.session_state:
    st.session_state["rejection_reasons"] = []


def _run_and_store(mode: str, everyday_request: str = None,
                   rejected_ids=None, rejection_reasons=None,
                   todays_context: str = None) -> dict:
    """Wrapper: runs the agent, stores result + the invocation params so
    a later 'Regenerate' can replay the same mode with rejection context.
    todays_context is a free-text "what's going on right now" field — a
    pattern borrowed from a classmate's dream-journal project where adding
    real-life context made the AI's reasoning feel grounded."""
    ctx = todays_context if todays_context is not None else st.session_state.get("todays_context", "")
    res = run_agent(
        mode=mode,
        everyday_request=everyday_request,
        rejected_ids=rejected_ids,
        rejection_reasons=rejection_reasons,
        todays_context=ctx,
    )
    st.session_state["result"] = res
    st.session_state["last_run"] = {
        "mode": mode,
        "everyday_request": everyday_request,
        "todays_context": ctx,
    }
    return res


def _profile_display():
    """Return (display_name, initial). Falls back to a friendly default."""
    try:
        p = get_owner_profile()
        if p.get("success") and p.get("profile"):
            name = p["profile"].get("name", "You")
            return name, (name[:1] or "Y").upper()
    except Exception:
        pass
    return "You", "Y"


def _goto(section_key: str):
    st.session_state["section"] = section_key
    st.rerun()


def _sign_out():
    """
    Clear the user-profile overlay and the session-specific state so the
    next page load shows the seed identity. Wearly has no real accounts
    (privacy contract), so 'sign out' here means: drop the personalization
    overlay, reset the active session, and return to Home. Wardrobe and
    wear history files are preserved — those are user data, not session
    state, and a real product would have them survive a sign-out.
    """
    # Empty the user-profile overlay file. If write fails (e.g. read-only
    # filesystem on certain hosts), we still clear session state.
    try:
        from fit_tool import PROFILE_PATH
        import json as _json
        with open(PROFILE_PATH, "w", encoding="utf-8") as _f:
            _json.dump({"profile": {}}, _f)
    except Exception:
        pass

    # Clear session-specific state, keep wardrobe and history untouched.
    for _k in (
        "result", "last_run", "rejected_ids", "rejection_reasons",
        "todays_context", "wq_result", "worn_outfit_key",
    ):
        st.session_state.pop(_k, None)
    st.session_state["section"] = "home"
    st.toast("Signed out. Your wardrobe stays local — wear history preserved.")
    st.rerun()


# ─────────────────────────────────────────────
# TOP APP BAR — wordmark left, popover menu right
# ─────────────────────────────────────────────

_name, _initial = _profile_display()

# The app bar is laid out as two Streamlit columns so the right column
# can host a real st.popover (a clickable dropdown menu). The brand
# wordmark on the left is still rendered as HTML inside its column for
# the typographic look.
_bar_left, _bar_right = st.columns([4, 1], gap="small")

with _bar_left:
    st.markdown(f"""
    <div class="brand">
        <span class="brand-mark">W</span>
        <span class="brand-wordmark">Wearly</span>
        <span class="brand-tag">Prototype</span>
    </div>
    """, unsafe_allow_html=True)

with _bar_right:
    # The popover's trigger button is the only popover in the whole app,
    # so we style it via the global [data-testid="stPopover"] selector
    # (see CSS block above). Earlier attempts used a .profile-popover-slot
    # wrapper div, but Streamlit renders each st.markdown call as a
    # SIBLING block, never wrapping the popover — so that scoping never
    # took effect. The global selector works and is safe.
    with st.popover(
        f"Hi, {_name}",
        use_container_width=True,
        help="Wearly has no accounts — your data stays local on this device.",
    ):
        st.markdown(f"""
        <div class="profile-menu-header">
            <div class="profile-menu-avatar">{_initial}</div>
            <div class="profile-menu-greeting">
                <div class="profile-menu-hi">Hi, {_name}.</div>
                <div class="profile-menu-sub">Signed in locally · no cloud account</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if st.button("Open profile", key="menu_profile_btn", use_container_width=True):
            _goto("profile")
        if st.button("My wardrobe", key="menu_wardrobe_btn", use_container_width=True):
            _goto("wardrobe")
        if st.button("Backup & restore", key="menu_backup_btn", use_container_width=True):
            # The Backup expander lives at the top of the Wardrobe screen.
            _goto("wardrobe")
        if st.button("Before / after demo", key="menu_demo_btn", use_container_width=True):
            _goto("demo")

        st.divider()

        st.markdown(
            "<div class='profile-menu-footnote'>"
            "Wearly stores your wardrobe and wear history locally. "
            "Signing out clears your fit profile but keeps your closet."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="menu_signout_btn", use_container_width=True):
            _sign_out()

# Visual divider under the app bar — matches the old single-row look.
st.markdown(
    "<div style='border-bottom:1px solid #EEEEEE; margin:0.2rem 0 1rem;'></div>",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# SECTION NAV — primary product navigation
# ─────────────────────────────────────────────

_SECTIONS = [
    ("home",     "Home"),
    ("today",    "Today"),
    ("wardrobe", "Wardrobe"),
    ("shop",     "Shop"),
    ("profile",  "Profile"),
    ("demo",     "Before / After"),
]
_active = st.session_state["section"]

_nav_cols = st.columns(len(_SECTIONS), gap="small")
for _col, (_key, _label) in zip(_nav_cols, _SECTIONS):
    with _col:
        _btn_type = "primary" if _key == _active else "secondary"
        if st.button(_label, key=f"nav_{_key}", type=_btn_type, use_container_width=True):
            if _key != _active:
                _goto(_key)


# ─────────────────────────────────────────────
# SIDEBAR — secondary controls only (collapsed by default)
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:0.3rem 0 0.2rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.5rem; color:#1C1917; line-height:1;">Settings</div>
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.16em; text-transform:uppercase; margin-top:0.35rem;">Prototype controls</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<p style='font-size:0.72rem; color:#6E6E73; line-height:1.55;'>Try a specific occasion instead of today's calendar event:</p>", unsafe_allow_html=True)
    st.session_state["everyday_choice"] = st.selectbox(
        "Occasion",
        ["Work", "Gym", "Dinner", "Formal Gala", "Weekend Brunch", "Casual Outing"],
        index=["Work", "Gym", "Dinner", "Formal Gala", "Weekend Brunch", "Casual Outing"].index(st.session_state.get("everyday_choice","Work")),
        label_visibility="collapsed",
    )
    if st.button("Plan this occasion →", key="sidebar_everyday", use_container_width=True):
        st.session_state["rejected_ids"] = []
        st.session_state["rejection_reasons"] = []
        with st.spinner("Reading your closet · scoring color harmony…"):
            _run_and_store("everyday", st.session_state["everyday_choice"])
        _goto("today")

    st.markdown("---")
    st.markdown("""
    <p style="font-size:0.72rem; color:#6E6E73; line-height:1.6;">
    <strong style="color:#2E2E2E;">Privacy.</strong>
    Your calendar, weather, wardrobe, and profile data are used only for outfit planning in this prototype.
    </p>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────

def _render_outfit_result(result: dict):
    """Render the agent's outfit result (event card, weather card,
    outfit + color score, gaps, workflow, reasoning)."""
    if result.get("error"):
        st.error(f"Agent Error: {result['error']}")
        return

    event    = result.get("event", {})
    weather  = result.get("weather", {})
    outfit   = result.get("recommendation", [])
    steps    = result.get("steps", [])
    reasons  = result.get("reasoning", [])
    gaps     = result.get("gaps", [])
    shopping = result.get("shopping_suggestions", [])
    color    = result.get("color_score", {})

    # ── Row 1: Event + Weather ──────────────────────────────
    col_event, col_weather = st.columns([1, 1], gap="large")

    with col_event:
        etype = event.get("type", "casual")
        etype_label = etype.replace("_", " ").title()
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Occasion</div>
            <div class="event-type-badge">{etype_label}</div>
            <div style="font-family:'DM Serif Display',serif; font-size:1.35rem; margin-bottom:0.3rem;">
                {event.get('title','N/A')}
            </div>
            <div style="font-size:0.84rem; color:#6E6E73;">
                {event.get('date','Today')} &nbsp;·&nbsp; {event.get('time','')}
            </div>
            {"<div style='font-size:0.82rem;color:#6E6E73;margin-top:0.5rem;'>" + event.get('notes','') + "</div>" if event.get('notes') else ""}
        </div>
        """, unsafe_allow_html=True)

    with col_weather:
        temp  = weather.get("temp_f", "—")
        cond  = weather.get("condition", "—")
        fl    = weather.get("feels_like_f", "—")
        wind  = weather.get("wind_mph", "—")
        prec  = weather.get("precip_chance_pct", "—")
        adv   = weather.get("layer_advice", "")
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Weather · {weather.get('city','')}</div>
            <div class="weather-block">
                <div class="weather-temp">{temp}°F</div>
                <div class="weather-detail">
                    {cond}<br>
                    Feels like {fl}°F<br>
                    Wind {wind} mph · {prec}% rain
                </div>
            </div>
            <div class="weather-advice">{adv}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Row 2: Outfit + Color Score ─────────────────────────
    col_outfit, col_score = st.columns([3, 2], gap="large")

    with col_outfit:
        item_rows = []
        for item in outfit:
            swatch_hex = color_to_swatch(item.get("color", ""))
            row = (
                '<div class="outfit-item">'
                '<span class="item-swatch" style="background:' + swatch_hex + '"></span>'
                '<span style="font-weight:500">' + item["name"] + '</span>'
                '<span class="item-color-chip">' + item.get("color", "") + '</span>'
                '</div>'
            )
            item_rows.append(row)

        inner = "".join(item_rows) if item_rows else "<p style='color:#6E6E73'>No items selected.</p>"
        outfit_html = (
            '<div class="card">'
            '<div class="card-title">Your Outfit &mdash; ' + str(len(outfit)) + ' pieces</div>'
            + inner +
            '</div>'
        )
        st.markdown(outfit_html, unsafe_allow_html=True)

    with col_score:
        score_val = color.get("score", 0)
        flags     = color.get("flags", [])
        sc        = score_color(score_val)
        bar_pct   = score_val

        flags_html = ""
        for f in flags:
            flags_html += f"<div style='font-size:0.82rem;color:#111111;padding:0.25rem 0;'>{f}</div>"

        st.markdown(f"""
        <div class="card">
            <div class="card-title">Color Harmony Score</div>
            <div style="font-family:'DM Serif Display',serif; font-size:2.8rem; color:{sc}; line-height:1;">
                {score_val}<span style="font-size:1.2rem; color:#6E6E73">/100</span>
            </div>
            <div style="font-size:0.78rem;color:#6E6E73;margin:0.3rem 0 0.4rem;">
                Skin tone: {result.get('profile',{}).get('skin_tone','—')}
            </div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_pct}%"></div>
            </div>
            {flags_html if flags_html else "<div style='font-size:0.83rem;color:#111111;margin-top:0.6rem;'>All colors work well for your skin tone.</div>"}
        </div>
        """, unsafe_allow_html=True)

    # ── Gaps ────────────────────────────────────────────────
    if gaps:
        # Render the alert text as HTML, then drop interactive
        # "Save to wishlist" buttons immediately below — Streamlit
        # buttons can't live inside an unsafe_allow_html block.
        gap_items = "".join(f"<div class='gap-item'>→ {s}</div>" for s in shopping)
        st.markdown(f"""
        <div class="gap-alert">
            <div class="gap-title">Wardrobe Gap · {', '.join(gaps)} missing for this occasion</div>
            {gap_items}
        </div>
        """, unsafe_allow_html=True)

        # ── Save-to-wishlist actions ──
        # Each shopping suggestion gets its own per-gap save button so the
        # user can queue the right piece into their wishlist with the gap
        # type already linked. Already-queued gaps surface a calm chip
        # instead of the button.
        try:
            from shopping_tool import add_wishlist_item, gap_is_on_wishlist
            _shopping_ok = True
        except ImportError:
            _shopping_ok = False

        if _shopping_ok and shopping:
            # Use the FIRST gap type as the canonical linked_gap. Outerwear
            # gaps come from Step 5 (always type 'outerwear'); required-piece
            # gaps come from Step 6 (type matches REQUIRED_PIECES entries).
            primary_gap = gaps[0]
            occ_tag = (result.get("event") or {}).get("type", "casual") or "casual"

            if gap_is_on_wishlist(primary_gap):
                st.markdown(
                    f'<div style="margin-top:0.6rem; padding:0.55rem 0.9rem; '
                    f'background:#FAFAFA; border:1px solid #EEEEEE; border-radius:99px; '
                    f'display:inline-block; font-size:0.78rem; color:#111111;">'
                    f"✓ '{primary_gap}' is already on your wishlist"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="font-size:0.74rem; color:#6E6E73; margin-top:0.65rem;">'
                    "Save a suggestion to your wishlist for later:"
                    "</div>",
                    unsafe_allow_html=True,
                )
                # One button per suggestion line. Hash the text into the key.
                import hashlib as _hashlib
                for sug_idx, sug_text in enumerate(shopping):
                    # Skip the "Check {stores} first" augmentation line —
                    # it's a prompt, not a saveable suggestion.
                    if sug_text.lower().startswith("check ") and "favorite store" in sug_text.lower():
                        continue
                    btn_key = "save_wl_" + _hashlib.md5(
                        f"{primary_gap}|{sug_idx}|{sug_text[:30]}".encode()
                    ).hexdigest()[:10]
                    label = f"Save: {sug_text[:60]}{'…' if len(sug_text) > 60 else ''}"
                    if st.button(label, key=btn_key, use_container_width=True):
                        rr = add_wishlist_item({
                            "name":       sug_text,
                            "category":   primary_gap,
                            "tags":       [occ_tag] if occ_tag else [],
                            "priority":   "medium",
                            "linked_gap": primary_gap,
                            "notes":      f"Saved from a wardrobe-gap suggestion ({occ_tag}).",
                        })
                        if rr.get("success"):
                            st.success(
                                f"Added to wishlist as {rr['item']['id']}. "
                                f"View it on the Shop tab."
                            )
                            st.rerun()
                        else:
                            st.error(rr.get("error", "Could not save."))

    # ── Workflow Steps ──────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    with st.expander("Agent Workflow — 7 Steps", expanded=False):
        steps_html = ""
        for s in steps:
            badge_class = {"ok":"badge-ok","fallback":"badge-fallback","gap_found":"badge-gap","error":"badge-gap"}.get(s["status"],"badge-ok")
            label = {"ok":"OK","fallback":"FALLBACK","gap_found":"GAP","error":"ERROR"}.get(s["status"],"OK")
            steps_html += f"""
            <div class="step-row">
                <span class="step-badge {badge_class}">{label}</span>
                <span class="step-name">Step {s['step']}: {s['name']}</span>
                <span class="step-output">{s['output']}</span>
            </div>"""
        st.markdown(f'<div class="card" style="margin-top:0">{steps_html}</div>', unsafe_allow_html=True)

    # ── Reasoning ──────────────────────────────────────────
    with st.expander("Full Agent Reasoning", expanded=False):
        r_html = ""
        for i, r in enumerate([x for x in reasons if x.strip()], 1):
            r_html += f'<div class="reason-item"><span class="reason-num">{i}</span><span>{r}</span></div>'
        st.markdown(f'<div class="card" style="margin-top:0">{r_html}</div>', unsafe_allow_html=True)

    # ── Reasoning graph (live, interactive — built from THIS result) ──────────
    # This is the "agent, not chatbot" feature in graph form. The schema view
    # lives on the Before / After screen; here we render the actual traversal
    # the agent just performed: User → CalendarEvent → Weather → wardrobe
    # items → OutfitRecommendation, with any gaps or rejection feedback
    # surfaced visibly. Built dynamically every run, so the graph changes
    # whenever the outfit does.
    if outfit:
        with st.expander("Reasoning graph — how this outfit emerged"):
            try:
                from graph_tool import render_run_graph_html, run_graph_summary
                summary = run_graph_summary(result)
                st.caption(
                    f"{summary['nodes']} nodes · {summary['items']} item"
                    f"{'' if summary['items'] == 1 else 's'} · "
                    f"{summary['gaps']} gap{'' if summary['gaps'] == 1 else 's'}"
                    + (f" · {summary['rejections']} rejection"
                       + ('' if summary['rejections'] == 1 else 's')
                       if summary['rejections'] else "")
                    + " — drag nodes to rearrange, hover for details."
                )
                html_doc = render_run_graph_html(result)
                components.html(html_doc, height=560, scrolling=False)
                st.caption(
                    "This graph is generated from the agent's *current* result. "
                    "Tap **Plan today's outfit →** or reject an item and "
                    "regenerate — the graph rebuilds. The abstract model that "
                    "shapes every run lives in the **Before / After** section "
                    "as the **schema graph**."
                )
            except ImportError as _e:
                st.info(f"Graph rendering unavailable: {_e}")
            except Exception as _e:
                st.warning(f"Graph could not render: {_e}")

    # ── Compact knowledge-graph export ─────────────────────────────────
    # Pattern borrowed from the SEIS 666 instructor: "save the entire
    # session as a compact knowledge graph at the MD level and use it
    # as a startup." One outfit becomes a small, portable JSON graph
    # that mirrors graph/schema.md — so it can be opened in the same
    # in-app and in-book viewers without translation.
    if outfit:
        try:
            from compact_kg import to_json as _kg_to_json
            import datetime as _dt_local
            kg_blob = _kg_to_json(result).encode("utf-8")
            fname = f"wearly-outfit-{_dt_local.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
            st.download_button(
                label="Export today's reasoning as a compact knowledge graph",
                data=kg_blob,
                file_name=fname,
                mime="application/json",
                use_container_width=True,
                key="compact_kg_dl",
                help="One outfit → one small JSON graph. Same shape as graph/schema.md. "
                     "Open it in the in-book Knowledge-Graph viewer or share it with a stylist.",
            )
        except Exception as _e:
            st.caption(f"Compact-KG export unavailable: {_e}")

    # ── Wear-today: record this outfit in wear history ──────────
    # Tells Wearly "I'm actually wearing this." Next time the agent runs,
    # the freshness tie-breaker prefers items you haven't just worn.
    # This is the second "agent, not chatbot" signal (paired with reject/regenerate):
    # the system LEARNS from accepted recommendations, not just from declined ones.
    if outfit:
        outfit_key = "|".join(sorted(i.get("id", "") for i in outfit))
        already_worn = st.session_state.get("worn_outfit_key") == outfit_key

        st.markdown("""
        <div style="margin:1.4rem 0 0.6rem; padding-top:1.2rem; border-top:1px solid #EEEEEE;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.25rem; color:#1C1917; line-height:1.2;">
                Wearing this today?
            </div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.35rem; line-height:1.55;">
                Mark the outfit worn so Wearly can rotate fresher pieces into your next recommendation.
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not already_worn:
            if st.button(
                "✓ Wear this outfit today",
                key="wear_today_btn", type="primary", use_container_width=True,
            ):
                try:
                    from history_tool import record_wear
                except ImportError:
                    from tools.history_tool import record_wear  # legacy layout
                item_ids = [i.get("id") for i in outfit if i.get("id")]
                event_name = (result.get("event") or {}).get("title") or "Today"
                rec = record_wear(item_ids, event_name=event_name)
                if rec.get("success"):
                    st.session_state["worn_outfit_key"] = outfit_key
                    st.success(
                        f"Recorded — {rec.get('recorded_count', 0)} piece"
                        f"{'s' if rec.get('recorded_count', 0) != 1 else ''} marked worn. "
                        f"Wearly will prefer fresher options for your next recommendation."
                    )
                    st.rerun()
                else:
                    st.error(f"Could not record wear: {rec.get('error', 'unknown error')}")
        else:
            st.success("Marked worn — Wearly will prefer fresher pieces next time.")

    # ── Refine this outfit (reject & regenerate) ──────────
    # This is the "agent, not chatbot" moment — the user can push back
    # on the recommendation with specific reasons and the agent re-runs
    # with those constraints, surfacing every reason in the reasoning
    # trail so the user sees WHY the new outfit is different.
    if outfit:
        st.markdown("""
        <div style="margin:1.6rem 0 0.8rem; padding-top:1.2rem; border-top:1px solid #EEEEEE;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.25rem; color:#1C1917; line-height:1.2;">
                Not quite right?
            </div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.35rem; line-height:1.55;">
                Tell Wearly what to swap out and why. The agent will re-run with your feedback —
                and explain every change.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Build a label → id map for the multiselect
        _id_by_label = {it.get("name", "—"): it.get("id") for it in outfit if it.get("id")}
        _labels = list(_id_by_label.keys())

        _reasons_options = [
            "Wore it recently",
            "Too formal",
            "Too casual",
            "Uncomfortable",
            "Not suitable for weather",
            "Doesn't fit well",
            "Not modest enough",
            "Don't like this color today",
            "Unavailable / in laundry",
        ]

        _swap = st.multiselect(
            "Items to swap out",
            options=_labels,
            key="refine_items",
            help="Pick one or more pieces you'd rather not wear today.",
        )
        _reason = st.selectbox(
            "Reason",
            options=_reasons_options,
            key="refine_reason",
            help="Wearly will record this reason in the reasoning trail.",
        )

        if st.button(
            "Regenerate with these changes →",
            key="refine_regenerate",
            type="primary",
            use_container_width=True,
            disabled=not _swap,
        ):
            # Accumulate the new rejections on top of any previous ones
            # in this session, so successive "Regenerate" presses keep
            # narrowing the candidate pool.
            new_ids = [_id_by_label[lbl] for lbl in _swap if lbl in _id_by_label]
            new_reasons = [
                {"item_id": _id_by_label[lbl], "item_name": lbl, "reason": _reason}
                for lbl in _swap if lbl in _id_by_label
            ]
            prior_ids = st.session_state.get("rejected_ids", [])
            prior_reasons = st.session_state.get("rejection_reasons", [])
            st.session_state["rejected_ids"] = list({*prior_ids, *new_ids})
            st.session_state["rejection_reasons"] = prior_reasons + new_reasons

            last = st.session_state.get("last_run", {"mode": "calendar", "everyday_request": None})
            with st.spinner("Re-reading your context · applying your feedback…"):
                _run_and_store(
                    last.get("mode", "calendar"),
                    last.get("everyday_request"),
                    rejected_ids=st.session_state["rejected_ids"],
                    rejection_reasons=st.session_state["rejection_reasons"],
                )
            st.rerun()

        # If we already regenerated at least once, show a small "what changed" banner.
        prior = result.get("rejected_context", {})
        prior_reasons_list = prior.get("reasons", []) if isinstance(prior, dict) else []
        if prior_reasons_list:
            chips = "".join(
                f'<span style="display:inline-block; font-size:0.74rem; color:#111111; padding:0.32rem 0.8rem; background:#FAFAFA; border:1px solid #EEEEEE; border-radius:99px; margin:0 0.4rem 0.4rem 0;">{r.get("item_name","—")} · {r.get("reason","rejected")}</span>'
                for r in prior_reasons_list
            )
            st.markdown(f"""
            <div style="margin-top:1.1rem; padding:1rem 1.1rem; background:#FFFFFF; border:1px solid #EEEEEE; border-radius:6px;">
                <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.6rem;">
                    What changed in this run
                </div>
                <div>{chips}</div>
                <div style="font-size:0.78rem; color:#6E6E73; margin-top:0.65rem; line-height:1.55;">
                    These items were excluded from the candidate pool. The reasoning trail above shows what Wearly chose instead.
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HOME — landing screen with personalized "Today" preview
# ─────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def _load_home_context():
    ev = get_upcoming_events(days_ahead=7)
    next_event = ev["events"][0] if ev.get("events") else None
    w = get_weather()
    return next_event, w.get("weather"), w.get("error")


def _render_home():
    next_event, weather, _ = _load_home_context()
    _today = datetime.today()
    today_label = _today.strftime("%A · %B ") + str(_today.day)

    st.markdown(f"""
    <div style="margin-top:0.2rem; margin-bottom:1.3rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:2.1rem; color:#1C1917; line-height:1.1; letter-spacing:-0.01em;">
            Good day, {_name.split()[0] if _name else 'there'}.
        </div>
        <div style="font-size:0.95rem; color:#5C5048; margin-top:0.45rem; line-height:1.55; max-width:34rem;">
            Plan today's outfit in three seconds — reasoned through your calendar, the weather, and your real closet.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Today card (centerpiece, accent stripe) ──
    if next_event:
        ev_title = next_event.get("title", "—")
        ev_meta_parts = []
        if next_event.get("time"):
            ev_meta_parts.append(next_event["time"])
        if next_event.get("type"):
            ev_meta_parts.append(next_event["type"].replace("_", " ").title())
        ev_meta = " · ".join(ev_meta_parts) if ev_meta_parts else "Today"
        ev_notes = next_event.get("notes", "")
    else:
        ev_title = "No upcoming events"
        ev_meta = "We'll plan a versatile everyday outfit."
        ev_notes = ""

    if weather:
        w_city = weather.get("city", "—")
        w_temp = weather.get("temp_f", "—")
        w_cond = weather.get("condition", "—")
        w_advice = weather.get("layer_advice", "")
    else:
        w_city, w_temp, w_cond, w_advice = "—", "—", "—", ""

    notes_html = (
        f'<div style="font-size:0.8rem; color:#6E6E73; margin-top:0.3rem; font-style:italic; line-height:1.5;">{ev_notes}</div>'
        if ev_notes else ""
    )

    st.markdown(f"""
    <div style="position:relative; background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.55rem 1.6rem 1.4rem; margin-bottom:1.1rem; overflow:hidden; box-shadow:0 1px 0 rgba(28,25,23,0.02);">
        <div style="position:absolute; top:0; left:0; right:0; height:2px; background:#111111;"></div>
        <div style="font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:1rem;">
            Today · {today_label}
        </div>
        <div style="margin-bottom:1.1rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">Next event</div>
            <div style="font-family:'DM Serif Display',serif; font-size:1.45rem; color:#1C1917; line-height:1.15;">{ev_title}</div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">{ev_meta}</div>
            {notes_html}
        </div>
        <div style="height:1px; background:#EEEEEE; margin:0 0 1.05rem;"></div>
        <div>
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">Weather · {w_city}</div>
            <div style="display:flex; align-items:baseline; gap:0.65rem; flex-wrap:wrap;">
                <div style="font-family:'DM Serif Display',serif; font-size:1.6rem; color:#1C1917; line-height:1;">{w_temp}°F</div>
                <div style="font-size:0.95rem; color:#2E2E2E;">{w_cond}</div>
            </div>
            <div style="font-size:0.82rem; color:#6E6E73; margin-top:0.45rem; line-height:1.5;">{w_advice}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Plan today's outfit →", key="home_cta", type="primary", use_container_width=True):
        st.session_state["rejected_ids"] = []
        st.session_state["rejection_reasons"] = []
        with st.spinner("Reading your calendar · checking the weather · filtering your closet · scoring color harmony…"):
            _run_and_store("calendar")
        _goto("today")

    st.markdown("""
    <div style="text-align:center; font-size:0.72rem; color:#6E6E73; margin-top:0.55rem; margin-bottom:0.4rem; letter-spacing:0.02em;">
        7 reasoning steps · ~3 seconds · no account required
    </div>
    """, unsafe_allow_html=True)

    # ── Agent-process pill row ──
    pill = (
        "display:inline-flex; align-items:center; gap:0.45rem; "
        "padding:0.42rem 0.82rem 0.42rem 0.7rem; background:#FFFFFF; "
        "border:1px solid #E5E5E5; border-radius:99px; "
        "font-size:0.78rem; color:#3D332D; font-weight:500;"
    )
    num = (
        "color:#111111; font-size:0.66rem; font-weight:700; "
        "letter-spacing:0.05em; font-family:'DM Sans',sans-serif;"
    )
    arrow = "color:#C8B8A8; font-size:0.85rem; padding:0 0.05rem;"
    st.markdown(f"""
    <div style="margin-top:1.4rem; padding:1rem 0.2rem 0.4rem; text-align:center;">
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.16em; text-transform:uppercase; font-weight:600; margin-bottom:0.85rem;">
            How Wearly thinks
        </div>
        <div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:0.42rem; row-gap:0.55rem;">
            <span style="{pill}"><span style="{num}">01</span> Calendar</span>
            <span style="{arrow}">→</span>
            <span style="{pill}"><span style="{num}">02</span> Weather</span>
            <span style="{arrow}">→</span>
            <span style="{pill}"><span style="{num}">03</span> Closet</span>
            <span style="{arrow}">→</span>
            <span style="{pill}"><span style="{num}">04</span> Color</span>
            <span style="{arrow}">→</span>
            <span style="{pill}"><span style="{num}">05</span> Outfit</span>
        </div>
        <p style="font-size:0.82rem; color:#6E6E73; margin:1rem auto 0; max-width:24rem; line-height:1.55;">
            An <strong style="color:#1C1917;">agent</strong>, not a chatbot.
            Wearly reads your context first, then recommends — and explains every choice.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.6rem; padding-top:1.05rem; border-top:1px solid #EEEEEE;">
        <p style="font-size:0.74rem; color:#6E6E73; line-height:1.55; margin:0; max-width:30rem;">
            <strong style="color:#6E6E73; letter-spacing:0.04em;">Privacy first.</strong>
            Calendar, weather, wardrobe, and profile data are used only for outfit planning in this prototype.
            No accounts. No third parties.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TODAY — outfit result (or empty state)
# ─────────────────────────────────────────────

def _render_today():
    res = st.session_state.get("result")
    if res:
        st.markdown("""
        <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Today's outfit</div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">Wearly's recommendation for the next event on your calendar.</div>
        </div>
        """, unsafe_allow_html=True)
        _render_outfit_result(res)
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        if st.button("Replan from scratch", key="replan_today", use_container_width=False):
            st.session_state["rejected_ids"] = []
            st.session_state["rejection_reasons"] = []
            last = st.session_state.get("last_run", {"mode": "calendar", "everyday_request": None})
            with st.spinner("Re-running the agent…"):
                _run_and_store(last.get("mode", "calendar"), last.get("everyday_request"))
            st.rerun()
    else:
        st.markdown("""
        <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Today</div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">No outfit yet — let's plan one.</div>
        </div>
        <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:2rem 1.6rem; text-align:center;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.2rem; color:#2E2E2E;">Plan today's outfit</div>
            <div style="font-size:0.84rem; color:#6E6E73; margin-top:0.5rem; max-width:24rem; margin-left:auto; margin-right:auto; line-height:1.55;">
                Wearly will read your calendar, check the weather, and choose pieces from your closet — with reasoning at every step.
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Today's context — free-text "what's going on right now" field.
        # Pattern borrowed from a classmate's dream-journal project where
        # adding real-life context grounded the AI's analysis.
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-size:0.78rem; color:#6E6E73; margin-bottom:0.3rem;'>"
            "Anything Wearly should know about today? <em>(optional — "
            "e.g. \"tired and want comfort\", \"first day at a new job\", "
            "\"traveling, packable\")</em></div>",
            unsafe_allow_html=True,
        )
        st.text_input(
            label="Today's context",
            label_visibility="collapsed",
            key="todays_context",
            placeholder="e.g. tired, comfort over polish today",
        )
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        if st.button("Plan today's outfit →", key="today_cta", type="primary", use_container_width=True):
            st.session_state["rejected_ids"] = []
            st.session_state["rejection_reasons"] = []
            with st.spinner("Reading your calendar · checking the weather · filtering your closet · scoring color harmony…"):
                _run_and_store("calendar")
            st.rerun()


# ─────────────────────────────────────────────
# WARDROBE — coming-soon stub
# ─────────────────────────────────────────────

def _render_backup_restore():
    """
    Backup + restore expander rendered at the top of the Wardrobe screen.

    Why this exists: Streamlit Cloud's container filesystem is ephemeral.
    Anything the user adds (wardrobe items, profile edits, wear history,
    favorite stores, wishlist items) is wiped when the container restarts.
    Downloading the bundle preserves their entire personal Wearly state
    in one file they can re-upload later. On localhost the same UI is
    useful for portability and version-controlling your closet — files
    persist on disk there.
    """
    try:
        from backup_tool import (
            export_user_data_bytes, suggested_backup_filename,
            import_user_data, is_wearly_backup,
        )
    except ImportError as _e:
        st.warning(f"Backup tool unavailable: {_e}")
        return

    with st.expander("Backup & restore your closet", expanded=False):
        st.markdown("""
        <div style="font-size:0.82rem; color:#2E2E2E; line-height:1.55; margin-bottom:0.8rem;">
            <strong style="color:#111111;">Why this matters.</strong>
            On Streamlit Cloud, anything you save (wardrobe items, profile
            preferences, wear history, favorite stores, wishlist) is
            cleared when the container restarts. Download the backup
            after a session and re-upload it the next time to keep
            everything. On localhost your data persists on disk —
            backups still help for moving between devices or
            version-controlling your closet.
        </div>
        <div style="font-size:0.74rem; color:#6E6E73; line-height:1.55; margin-bottom:1rem;">
            <strong style="color:#6E6E73;">What's in a backup.</strong>
            One JSON file bundling your wardrobe (manually added pieces),
            profile, wear history, favorite stores, and wishlist. Seed
            wardrobe and color rules aren't included — those ship with
            the app.
        </div>
        """, unsafe_allow_html=True)

        col_dl, col_ul = st.columns(2, gap="medium")

        with col_dl:
            st.markdown(
                '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.4rem;">Download backup</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                "Download my Wearly backup",
                data=export_user_data_bytes(),
                file_name=suggested_backup_filename(),
                mime="application/json",
                use_container_width=True,
                help=("Saves a single JSON containing your wardrobe, profile, "
                      "wear history, favorite stores, and wishlist."),
            )

        with col_ul:
            st.markdown(
                '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.4rem;">Restore from a backup</div>',
                unsafe_allow_html=True,
            )
            uploaded = st.file_uploader(
                "Pick a Wearly backup JSON",
                type=["json"],
                accept_multiple_files=False,
                key="backup_upload",
                label_visibility="collapsed",
            )

            if uploaded is not None:
                raw = uploaded.getvalue()
                if not is_wearly_backup(raw):
                    st.error(
                        "This file doesn't look like a Wearly backup. "
                        "Re-export from the Download button to produce a valid file."
                    )
                else:
                    st.caption(
                        "Restoring will **overwrite** your current wardrobe, "
                        "profile, wear history, favorite stores, and wishlist "
                        "with the contents of this backup."
                    )
                    if st.button("Restore now", key="backup_restore_btn",
                                 type="primary", use_container_width=True):
                        res = import_user_data(raw)
                        if res.get("success"):
                            restored = ", ".join(res.get("restored") or [])
                            st.success(
                                f"Restored: {restored or 'nothing changed'}. "
                                f"Reloading the app to pick up the new state…"
                            )
                            st.rerun()
                        else:
                            st.error(f"Restore failed: {res.get('error', 'unknown error')}")


def _render_ask_wardrobe():
    """Pre-baked queries over the wardrobe + wear-history.

    Each question is answered by `wardrobe_query.CANNED_QUERIES` —
    deterministic Python over the same data the agent uses, surfaced
    as an interactive panel so the user can explore their own closet.
    No LLM is called; the rule citation on each answer ties back to the
    Skill rule pack that defines the underlying filter."""
    with st.expander("Ask your wardrobe", expanded=False):
        st.markdown(
            "<div style='font-size:0.82rem; color:#6B5F55; line-height:1.55; "
            "margin-bottom:0.8rem;'>Pre-baked questions Wearly can answer about "
            "your closet — same data the agent uses at recommendation time, "
            "queried directly.</div>",
            unsafe_allow_html=True,
        )
        try:
            from wardrobe_query import CANNED_QUERIES
        except Exception as _e:
            st.caption(f"Query module unavailable: {_e}")
            return

        # Each question gets a button; clicking stores the result for display.
        cols = st.columns(2, gap="small")
        for i, (label, fn) in enumerate(CANNED_QUERIES):
            col = cols[i % 2]
            with col:
                if st.button(label, key=f"wq_{i}", use_container_width=True):
                    try:
                        st.session_state["wq_result"] = fn()
                    except Exception as _e:
                        st.session_state["wq_result"] = {
                            "question": label,
                            "items": [],
                            "summary": f"Query failed: {_e}",
                            "rule": "",
                        }

        wq = st.session_state.get("wq_result")
        if wq:
            st.markdown(
                f"<div style='margin-top:1rem; padding:0.9rem 1rem; "
                f"background:#FAFAFA; border:1px solid #EEEEEE; border-radius:6px;'>"
                f"<div style='font-size:0.78rem; color:#6E6E73; text-transform:uppercase; "
                f"letter-spacing:0.4px;'>{wq.get('question', '')}</div>"
                f"<div style='font-size:0.92rem; color:#2E2A27; line-height:1.55; margin-top:0.4rem;'>"
                f"{wq.get('summary', '')}"
                f"</div>"
                f"<div style='font-size:0.72rem; color:#6E6E73; margin-top:0.5rem;'>"
                f"{wq.get('rule', '')}"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            items = wq.get("items") or []
            if items:
                st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
                grid = st.columns(min(3, max(1, len(items))), gap="small")
                for j, it in enumerate(items[:6]):
                    with grid[j % len(grid)]:
                        nm = it.get("name", "—")
                        tp = (it.get("type") or "").title()
                        co = it.get("color", "")
                        st.markdown(
                            f"<div style='padding:0.6rem 0.7rem; background:#FFFFFF; "
                            f"border:1px solid #E5E5E5; border-radius:6px; "
                            f"font-size:0.82rem; color:#2E2A27; line-height:1.4;'>"
                            f"<strong>{nm}</strong>"
                            f"<div style='font-size:0.72rem; color:#6E6E73;'>"
                            f"{tp}{' · ' + co if co else ''}</div></div>",
                            unsafe_allow_html=True,
                        )
                if len(items) > 6:
                    st.caption(f"…and {len(items) - 6} more.")


def _render_wardrobe():
    # ── Page header ─────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Wardrobe</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">Your digital closet — seed pieces plus anything you've added.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Backup & Restore ────────────────────────────────────────
    # The persistence path. On localhost, files persist on disk and the
    # backup is for portability / safekeeping. On Streamlit Cloud, the
    # container filesystem is ephemeral — backups are the way your
    # closet survives between sessions. Same UI either way.
    _render_backup_restore()

    # ── Ask your wardrobe (pre-baked queries over the closet) ────────
    # Pattern borrowed from a classmate's project that lets the user
    # query the knowledge graph in plain language ("what did I dream
    # about when anxious?"). Wearly's version is a small set of canned
    # questions that traverse the wardrobe + wear-history files and
    # surface a body-positive plain-English summary.
    _render_ask_wardrobe()

    # ── Inventory summary (seed + user counts) ───────────────────
    seed_clothing = seed_shoes = seed_accessories = 0
    user_clothing = user_shoes = user_accessories = 0
    try:
        full = get_wardrobe()
        if full.get("success"):
            user_only = get_user_wardrobe().get("user_wardrobe", {})
            user_clothing    = len(user_only.get("clothing", []))
            user_shoes       = len(user_only.get("shoes", []))
            user_accessories = len(user_only.get("accessories", []))
            seed_clothing    = len(full["wardrobe"].get("clothing", []))    - user_clothing
            seed_shoes       = len(full["wardrobe"].get("shoes", []))       - user_shoes
            seed_accessories = len(full["wardrobe"].get("accessories", [])) - user_accessories
    except Exception:
        pass

    total_seed = seed_clothing + seed_shoes + seed_accessories
    total_user = user_clothing + user_shoes + user_accessories

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.2rem 1.4rem; margin-bottom:1.1rem;">
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.7rem;">Inventory</div>
        <div style="display:flex; gap:1.2rem; flex-wrap:wrap;">
            <div style="flex:1; min-width:120px;">
                <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1;">{seed_clothing + user_clothing}</div>
                <div style="font-size:0.72rem; color:#6E6E73; margin-top:0.25rem;">clothing pieces</div>
            </div>
            <div style="flex:1; min-width:120px;">
                <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1;">{seed_shoes + user_shoes}</div>
                <div style="font-size:0.72rem; color:#6E6E73; margin-top:0.25rem;">shoes</div>
            </div>
            <div style="flex:1; min-width:120px;">
                <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1;">{seed_accessories + user_accessories}</div>
                <div style="font-size:0.72rem; color:#6E6E73; margin-top:0.25rem;">accessories</div>
            </div>
        </div>
        <div style="font-size:0.76rem; color:#6E6E73; margin-top:0.85rem; line-height:1.55;">
            {total_seed} seed piece{'' if total_seed == 1 else 's'} · <strong style="color:#111111;">{total_user} added by you</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Add-item flows: manual + photo ──────────────────────────
    st.markdown("""
    <div style="margin-bottom:0.5rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.3rem; color:#1C1917; line-height:1.2;">Add an item</div>
        <div style="font-size:0.82rem; color:#6E6E73; margin-top:0.25rem;">Type a piece in by hand, or upload a photo and let Wearly suggest the color. Either way, the item joins the candidate pool the next time you ask for an outfit.</div>
    </div>
    """, unsafe_allow_html=True)

    _OCCASION_TAG_OPTIONS = [
        "work", "dinner", "gym", "formal", "casual",
        "weekend", "evening", "date", "travel", "versatile",
    ]
    _SEASON_OPTIONS = ["spring", "summer", "fall", "winter", "all"]
    _CATEGORY_OPTIONS = [
        "top", "bottom", "dress", "outerwear", "activewear", "shoes", "accessory",
    ]
    _FORMALITY_OPTIONS = [
        "casual", "smart_casual", "business", "formal", "athletic",
    ]

    _tab_manual, _tab_photo, _tab_link = st.tabs(["Manual entry", "From a photo", "From a link"])

    # ── Manual tab ──────────────────────────────────────────────
    with _tab_manual:
        with st.form("wardrobe_add_form_manual", clear_on_submit=True):
            col_a, col_b = st.columns([3, 2], gap="small")
            with col_a:
                m_name = st.text_input("Name", placeholder="e.g. Cream Linen Blazer", key="m_name")
            with col_b:
                m_color = st.text_input("Color", placeholder="e.g. cream", key="m_color")

            col_c, col_d = st.columns([1, 1], gap="small")
            with col_c:
                m_category = st.selectbox("Category", options=_CATEGORY_OPTIONS, key="m_category")
            with col_d:
                m_formality = st.selectbox("Formality", options=_FORMALITY_OPTIONS, key="m_formality")

            m_seasons = st.multiselect(
                "Seasons (leave empty to mean year-round)",
                options=_SEASON_OPTIONS, default=["all"], key="m_seasons",
            )
            m_tags = st.multiselect(
                "Suitable for these occasions", options=_OCCASION_TAG_OPTIONS, default=[], key="m_tags",
            )
            m_submit = st.form_submit_button("Add to wardrobe", type="primary", use_container_width=True)

            if m_submit:
                # availability defaults to "available" inside save_user_item().
                # The closet-status flow (in laundry / loaned out / etc.) is a
                # separate later feature, not part of item creation.
                res = save_user_item(
                    category=m_category,
                    item_fields={
                        "name":         m_name,
                        "color":        m_color,
                        "formality":    m_formality,
                        "season":       m_seasons or ["all"],
                        "tags":         m_tags or [m_category],
                    },
                )
                if res.get("success"):
                    added = res["item"]
                    st.success(
                        f"Saved **{added['name']}** ({added['color']}, {added['type']}) "
                        f"as `{added['id']}`. It's now eligible for outfits tagged "
                        f"{', '.join(added['tags']) or added['type']}."
                    )
                else:
                    st.error(f"Could not save: {res.get('error', 'unknown error')}")

    # ── Photo tab ───────────────────────────────────────────────
    with _tab_photo:
        st.markdown("""
        <div style="font-size:0.82rem; color:#6E6E73; margin-bottom:0.7rem; line-height:1.5;">
            Upload a photo of the piece. Wearly reads the dominant colors in the image and
            suggests the closest named color — you confirm or override before saving.
            <br><span style="color:#6E6E73; font-size:0.74rem;">No AI category recognition yet; you'll fill in type, formality, and tags. <a href="#" style="color:#8E8E93;">Production path is documented in the Intelligent Book.</a></span>
        </div>
        """, unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Photo (PNG / JPG, up to ~4 MB)",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=False,
            key="p_uploader",
        )

        suggested_color_default = ""
        image_bytes_for_save = None

        if uploaded is not None:
            image_bytes_for_save = uploaded.getvalue()
            prev_col, info_col = st.columns([2, 3], gap="medium")
            with prev_col:
                st.image(uploaded, caption=None, use_container_width=True)
            with info_col:
                with st.spinner("Reading colors…"):
                    sugg = suggest_colors_from_image(image_bytes_for_save, top_n=3)
                if sugg.get("success") and sugg["suggestions"]:
                    top = sugg["suggestions"][0]
                    suggested_color_default = top["name"]
                    chips = ""
                    for s in sugg["suggestions"]:
                        pct = round(s["weight"] * 100)
                        chips += (
                            f'<div style="display:inline-flex; align-items:center; gap:0.45rem; '
                            f'padding:0.35rem 0.75rem; background:#FFFFFF; border:1px solid #E5E5E5; '
                            f'border-radius:99px; font-size:0.78rem; color:#3D332D; margin:0 0.4rem 0.4rem 0;">'
                            f'<span style="width:14px; height:14px; border-radius:50%; background:{s["hex"]}; '
                            f'border:1px solid rgba(28,25,23,0.10); display:inline-block;"></span>'
                            f'{s["name"]} · {pct}%</div>'
                        )
                    st.markdown(f"""
                    <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.4rem;">
                        Suggested colors
                    </div>
                    <div style="margin-bottom:0.6rem;">{chips}</div>
                    <div style="font-size:0.76rem; color:#6E6E73; line-height:1.5;">
                        The top suggestion is pre-filled below. You can keep it, pick one of the others,
                        or type in any color.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(
                        f"Couldn't read colors from this image — fill in the color field manually. "
                        f"{sugg.get('error','')}"
                    )

        with st.form("wardrobe_add_form_photo", clear_on_submit=True):
            col_a, col_b = st.columns([3, 2], gap="small")
            with col_a:
                p_name = st.text_input("Name", placeholder="e.g. Cream Linen Blazer", key="p_name")
            with col_b:
                p_color = st.text_input("Color", value=suggested_color_default, key="p_color")

            col_c, col_d = st.columns([1, 1], gap="small")
            with col_c:
                p_category = st.selectbox("Category", options=_CATEGORY_OPTIONS, key="p_category")
            with col_d:
                p_formality = st.selectbox("Formality", options=_FORMALITY_OPTIONS, key="p_formality")

            p_seasons = st.multiselect(
                "Seasons (leave empty to mean year-round)",
                options=_SEASON_OPTIONS, default=["all"], key="p_seasons",
            )
            p_tags = st.multiselect(
                "Suitable for these occasions", options=_OCCASION_TAG_OPTIONS, default=[], key="p_tags",
            )
            p_submit = st.form_submit_button(
                ("Save photo & add to wardrobe" if image_bytes_for_save else "Add to wardrobe (no photo attached)"),
                type="primary", use_container_width=True,
            )

            if p_submit:
                # availability defaults to "available" — closet status is a
                # separate later feature, not part of item creation.
                res = save_user_item(
                    category=p_category,
                    item_fields={
                        "name":         p_name,
                        "color":        p_color,
                        "formality":    p_formality,
                        "season":       p_seasons or ["all"],
                        "tags":         p_tags or [p_category],
                    },
                    image_bytes=image_bytes_for_save,
                )
                if res.get("success"):
                    added = res["item"]
                    photo_note = ""
                    if added.get("image_path"):
                        photo_note = f" Photo saved at `{added['image_path']}`."
                    elif added.get("_image_error"):
                        photo_note = f" (Photo could not be saved: {added['_image_error']})"
                    st.success(
                        f"Saved **{added['name']}** ({added['color']}, {added['type']}) "
                        f"as `{added['id']}`.{photo_note} It's now eligible for outfits tagged "
                        f"{', '.join(added['tags']) or added['type']}."
                    )
                else:
                    st.error(f"Could not save: {res.get('error', 'unknown error')}")

        st.info(
            "**Heads up.** On the live Streamlit Cloud demo, uploaded images and added items "
            "persist only until the container restarts (Streamlit Cloud's filesystem is ephemeral). "
            "For a permanent personal closet, run Wearly locally — or wait for the upcoming "
            "real-storage release.",
            icon="ℹ️",
        )

    # ── Link tab ────────────────────────────────────────────────
    with _tab_link:
        st.markdown("""
        <div style="font-size:0.82rem; color:#6E6E73; margin-bottom:0.7rem; line-height:1.5;">
            Paste a product URL. Wearly will infer the store, suggest an item name from the URL slug,
            and try to read the page's public metadata (page title, og:title, og:image) to pre-fill
            the form. Every field is yours to confirm or edit before saving.
            <br><span style="color:#6E6E73; font-size:0.74rem;">
                Some retailers block automated requests. If the fetch fails we still pre-fill from the URL slug alone — no crashes.
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Lazy import so the rest of the app stays decoupled.
        try:
            from link_import import import_product_link
        except ImportError as _e:
            st.error(f"Link import module unavailable: {_e}")
            import_product_link = None

        url_col_a, url_col_b = st.columns([5, 2], gap="small")
        with url_col_a:
            link_url = st.text_input(
                "Product URL",
                placeholder="https://www.example.com/products/cream-linen-blazer",
                key="l_url_input",
                label_visibility="collapsed",
            )
        with url_col_b:
            link_analyze = st.button(
                "Analyze link →", key="l_analyze",
                type="primary", use_container_width=True,
                disabled=(import_product_link is None),
            )

        # Reset the form state when the URL field is cleared.
        if not link_url and "link_data" in st.session_state:
            del st.session_state["link_data"]

        if link_analyze and link_url and import_product_link is not None:
            with st.spinner("Reading the page…"):
                st.session_state["link_data"] = import_product_link(link_url)

        link_data = st.session_state.get("link_data")

        if link_data:
            inferred = link_data.get("inferred", {})
            meta = link_data.get("metadata", {})
            fetched = link_data.get("fetched", False)
            fetch_err = link_data.get("fetch_error")
            source_image = link_data.get("source_image_url")

            # ── Preview card ──────────────────────────────
            # Image: real og:image if available; otherwise a calm placeholder
            # that explicitly invites the user to upload a photo later.
            if source_image:
                preview_img_block = (
                    f'<img src="{source_image}" alt="product image" '
                    f'style="width:100%; max-width:220px; border-radius:6px; '
                    f'border:1px solid #E5E5E5; display:block;" '
                    f'onerror="this.style.display=\'none\'">'
                )
            else:
                preview_img_block = (
                    '<div style="width:160px; height:120px; background:#F5EDE3; '
                    'border:1px dashed #D4C4B2; border-radius:6px; display:flex; '
                    'align-items:center; justify-content:center; text-align:center; '
                    'font-size:0.72rem; color:#6E6E73; padding:0.6rem; line-height:1.35;">'
                    'No image found —<br>upload a photo later'
                    '</div>'
                )

            # Status chip: green when the page was read, warm-warning when not.
            fetch_chip = (
                '<span style="font-size:0.66rem; color:#3A6B4A; background:#EFF5EB; '
                'border:1px solid #C9DDC1; padding:2px 9px; border-radius:99px; '
                'letter-spacing:0.06em; text-transform:uppercase; font-weight:600;">Page read OK</span>'
                if fetched else
                '<span style="font-size:0.66rem; color:#111111; background:#FAFAFA; '
                'border:1px solid #EEEEEE; padding:2px 9px; border-radius:99px; '
                'letter-spacing:0.06em; text-transform:uppercase; font-weight:600;">URL only</span>'
            )

            # Suggested-name placeholder: never show useless text like "Productpage."
            suggested_name_display = inferred.get("name") or '<span style="color:#8E8E93;">Review item name below</span>'

            # When the fetch failed, surface a calm one-liner explaining the
            # situation. The user can still save once they've reviewed fields.
            fetch_explanation_block = ""
            if not fetched:
                fetch_explanation_block = (
                    '<div style="font-size:0.78rem; color:#111111; background:#FAFAFA; '
                    'border:1px solid #EEEEEE; border-radius:6px; padding:0.7rem 0.95rem; '
                    'margin-top:0.85rem; line-height:1.55;">'
                    "We couldn't read this page automatically "
                    f'<span style="color:#6E6E73;">({fetch_err or "unknown reason"})</span>, '
                    'but you can still save the item after reviewing the fields below.'
                    '</div>'
                )

            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.2rem 1.4rem; margin-top:0.4rem; margin-bottom:1rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                    <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600;">Link preview</div>
                    {fetch_chip}
                </div>
                <div style="display:flex; gap:1.2rem; flex-wrap:wrap;">
                    <div style="flex:0 0 auto; min-width:160px;">{preview_img_block}</div>
                    <div style="flex:1; min-width:220px;">
                        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Store</div>
                        <div style="font-size:0.95rem; color:#1C1917; margin-bottom:0.6rem;">{link_data.get('source_store') or '—'}</div>
                        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Suggested name</div>
                        <div style="font-family:'DM Serif Display',serif; font-size:1.15rem; color:#1C1917; line-height:1.25;">{suggested_name_display}</div>
                        <div style="font-size:0.76rem; color:#6E6E73; margin-top:0.5rem; line-height:1.5;">
                            Category: <strong>{inferred.get('category') or '— (pick below)'}</strong><br>
                            Color: <strong>{inferred.get('color') or '— (type below)'}</strong><br>
                            Occasion tags: <strong>{', '.join(inferred.get('tags', [])) or '—'}</strong>
                        </div>
                    </div>
                </div>
                {fetch_explanation_block}
            </div>
            """, unsafe_allow_html=True)

            # ── Review form (pre-filled from inference) ──
            with st.form("wardrobe_add_form_link", clear_on_submit=False):
                col_a, col_b = st.columns([3, 2], gap="small")
                with col_a:
                    l_name = st.text_input(
                        "Name",
                        value=inferred.get("name") or "",
                        placeholder="Review item name…",
                        key="l_name",
                    )
                with col_b:
                    l_color = st.text_input(
                        "Color",
                        value=(inferred.get("color") or ""),
                        placeholder="e.g. cream, navy, terracotta…",
                        key="l_color",
                    )

                # Helpful nudge when color couldn't be inferred — never lie.
                if not inferred.get("color"):
                    msg = ("Enter the product color shown on the retailer page."
                           if not fetched else
                           "We couldn't spot a color word in the page text. "
                           "Enter the product color shown on the retailer page.")
                    st.caption(msg)

                # Pre-select inferred category if it matches one of our options.
                cat_default = inferred.get("category") if inferred.get("category") in _CATEGORY_OPTIONS else "top"
                col_c, col_d = st.columns([1, 1], gap="small")
                with col_c:
                    l_category = st.selectbox(
                        "Category", options=_CATEGORY_OPTIONS,
                        index=_CATEGORY_OPTIONS.index(cat_default), key="l_category",
                    )
                with col_d:
                    l_formality = st.selectbox("Formality", options=_FORMALITY_OPTIONS, key="l_formality")

                l_seasons = st.multiselect(
                    "Seasons (leave empty to mean year-round)",
                    options=_SEASON_OPTIONS, default=["all"], key="l_seasons",
                )

                # Pre-select inferred tags, intersected with our known vocabulary.
                pre_tags = [t for t in (inferred.get("tags") or []) if t in _OCCASION_TAG_OPTIONS]
                l_tags = st.multiselect(
                    "Suitable for these occasions",
                    options=_OCCASION_TAG_OPTIONS, default=pre_tags, key="l_tags",
                )

                # Manual image URL fallback. Pre-filled with og:image when
                # we found one; users can paste their own when we didn't
                # (e.g. for retailers whose product page is a Single Page App
                # that doesn't expose product metadata in the initial HTML).
                l_image_url = st.text_input(
                    "Image URL (optional)",
                    value=(source_image or ""),
                    placeholder="Paste a product image URL — shown next to the item in your wardrobe.",
                    key="l_image_url",
                    help=(
                        "If we couldn't read the page automatically, open the retailer page "
                        "in your browser, right-click the product image, choose "
                        "'Copy image address', and paste it here. The image will appear "
                        "next to this item in your wardrobe list."
                    ),
                )

                l_submit = st.form_submit_button(
                    "Save to wardrobe", type="primary", use_container_width=True,
                )

                if l_submit:
                    # availability defaults to "available" — closet status is a
                    # separate later feature, not part of item creation.
                    effective_image_url = (l_image_url or "").strip() or None
                    res = save_user_item(
                        category=l_category,
                        item_fields={
                            "name":         l_name,
                            "color":        l_color,
                            "formality":    l_formality,
                            "season":       l_seasons or ["all"],
                            "tags":         l_tags or [l_category],
                        },
                        link_metadata={
                            "source_url":       link_data.get("url"),
                            "source_store":     link_data.get("source_store"),
                            "source_image_url": effective_image_url,
                        },
                    )
                    if res.get("success"):
                        added = res["item"]
                        chips = []
                        if added.get("source_store"):
                            chips.append(f"from `{added['source_store']}`")
                        if added.get("source_url"):
                            chips.append(f"[original link]({added['source_url']})")
                        chip_str = " · ".join(chips)
                        st.success(
                            f"Saved **{added['name']}** ({added['color']}, {added['type']}) "
                            f"as `{added['id']}` {chip_str}. It's now eligible for outfits tagged "
                            f"{', '.join(added['tags']) or added['type']}."
                        )
                        # Clear the analyzed state so the next URL is a fresh start.
                        st.session_state.pop("link_data", None)
                    else:
                        st.error(f"Could not save: {res.get('error', 'unknown error')}")
        else:
            st.markdown(
                '<div style="font-size:0.82rem; color:#6E6E73; margin-top:0.4rem;">'
                "Paste a URL above and tap <strong>Analyze link →</strong> to see the inferred fields."
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Items you've added ──────────────────────────────────────
    overlay = get_user_wardrobe().get("user_wardrobe", {"clothing": [], "shoes": [], "accessories": []})
    user_rows = []
    for section in ("clothing", "shoes", "accessories"):
        for it in overlay.get(section, []):
            user_rows.append(it)

    if user_rows:
        rows_html = ""
        for it in user_rows:
            swatch = color_to_swatch(it.get("color", ""))
            tags_label = ", ".join(it.get("tags", []) or [])
            avail = it.get("availability", "available")
            avail_chip = ""
            if avail != "available":
                avail_chip = (
                    f'<span style="margin-left:0.5rem; font-size:0.66rem; color:#111111; '
                    f'background:#FAFAFA; border:1px solid #EEEEEE; padding:1px 7px; '
                    f'border-radius:99px; letter-spacing:0.06em;">{avail}</span>'
                )
            # Optional inline thumbnail. Priority:
            #   1. Local image_path (from the Photo tab) — embedded as data URI.
            #   2. Remote source_image_url (from the Link tab) — direct img src.
            # `onerror` hides the element if the remote image fails to load.
            thumb_html = ""
            ipath = it.get("image_path")
            src_image = it.get("source_image_url")
            if ipath:
                data_uri = _image_to_data_uri(ipath)
                if data_uri:
                    thumb_html = (
                        f'<img src="{data_uri}" alt="" '
                        f'style="width:42px; height:42px; object-fit:cover; '
                        f'border-radius:4px; border:1px solid #E5E5E5; flex-shrink:0;" '
                        f'onerror="this.style.display=\'none\'">'
                    )
            elif src_image:
                thumb_html = (
                    f'<img src="{src_image}" alt="" '
                    f'style="width:42px; height:42px; object-fit:cover; '
                    f'border-radius:4px; border:1px solid #E5E5E5; flex-shrink:0;" '
                    f'onerror="this.style.display=\'none\'">'
                )
            rows_html += (
                f'<div style="display:flex; align-items:center; gap:0.7rem; padding:0.6rem 0; border-bottom:1px solid #EEEEEE; font-size:0.92rem;">'
                f'{thumb_html}'
                f'<span class="item-swatch" style="background:{swatch}"></span>'
                f'<span style="font-weight:500; color:#1C1917;">{it.get("name","—")}</span>'
                f'<span style="font-size:0.74rem; color:#6E6E73; margin-left:auto; text-align:right;">'
                f'{it.get("type","—")} · {it.get("formality","—")}<br>'
                f'<span style="font-size:0.7rem;">{tags_label or "no tags"}</span></span>'
                f'{avail_chip}'
                f'</div>'
            )
        st.markdown(
            f'<div style="margin-top:1.4rem;">'
            f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.2rem; color:#1C1917; line-height:1.2; margin-bottom:0.4rem;">Items you\'ve added</div>'
            f'<div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:0.4rem 1.2rem;">'
            f'{rows_html}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="margin-top:1.2rem; font-size:0.82rem; color:#6E6E73;">'
            "No items added yet. The seed wardrobe is already available to Wearly — adding pieces here grows the candidate pool."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Coming-soon roadmap chips (preserved from prior pass) ───
    st.markdown("""
    <div style="margin-top:2rem; padding-top:1.05rem; border-top:1px solid #EEEEEE;">
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.6rem;">Coming soon</div>
        <div style="display:flex; gap:0.6rem; flex-wrap:wrap;">
            <span style="font-size:0.76rem; color:#6E6E73; padding:0.36rem 0.8rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px;">Photo upload</span>
            <span style="font-size:0.76rem; color:#6E6E73; padding:0.36rem 0.8rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px;">Product link import</span>
            <span style="font-size:0.76rem; color:#6E6E73; padding:0.36rem 0.8rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px;">Wear history</span>
            <span style="font-size:0.76rem; color:#6E6E73; padding:0.36rem 0.8rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px;">Item editing</span>
        </div>
    </div>
    """, unsafe_allow_html=True)




# ─────────────────────────────────────────────
# SHOP — Favorite stores + Wishlist
# ─────────────────────────────────────────────

def _render_shop():
    """Two-tab management surface for the shopping-gap loop.

    Tab 1 — Wishlist: list saved items, add new items manually, remove.
    Tab 2 — Favorite stores: list stores, add new, remove.

    Wardrobe gaps surfaced in the Today result get a "Save to wishlist"
    button (rendered in _render_outfit_result below); items added that
    way carry a linked_gap field so the user can later see which gap
    each wishlist entry was queued for.
    """
    try:
        from shopping_tool import (
            get_favorite_stores, add_favorite_store, remove_favorite_store,
            get_wishlist, add_wishlist_item, remove_wishlist_item,
            VALID_PRIORITIES,
        )
    except ImportError as _e:
        st.error(f"Shopping tool unavailable: {_e}")
        return

    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Shop</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">
            Favorite stores and a wishlist of pieces you want to acquire.
            Wearly uses both to make gap suggestions feel personal.
        </div>
    </div>
    """, unsafe_allow_html=True)

    _tab_wishlist, _tab_stores = st.tabs(["Wishlist", "Favorite stores"])

    # ── Wishlist tab ──────────────────────────────────────────
    with _tab_wishlist:
        wl = get_wishlist().get("items", [])
        stores_for_select = [s.get("name", "") for s in get_favorite_stores().get("stores", []) if s.get("name")]

        if wl:
            st.markdown(f"""
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.5rem;">
                {len(wl)} item{'' if len(wl) == 1 else 's'} on your wishlist
            </div>
            """, unsafe_allow_html=True)

            for it in wl:
                priority = (it.get("priority") or "medium").lower()
                pri_color = {"high": "#111111", "medium": "#111111", "low": "#8E8E93"}.get(priority, "#8E8E93")
                meta_bits = []
                if it.get("category"): meta_bits.append(it["category"])
                if it.get("preferred_store"): meta_bits.append(f"@ {it['preferred_store']}")
                if it.get("tags"): meta_bits.append(", ".join(it["tags"]))
                meta = " · ".join(meta_bits) or "—"
                linked = (
                    f'<span style="display:inline-block; font-size:0.66rem; color:#111111; '
                    f'background:#FAFAFA; border:1px solid #EEEEEE; padding:1px 7px; '
                    f'border-radius:99px; letter-spacing:0.06em; margin-left:0.5rem;">'
                    f'from a wardrobe gap · {it["linked_gap"]}</span>'
                ) if it.get("linked_gap") else ""
                source_link = (
                    f' · <a href="{it["source_url"]}" target="_blank" style="color:#111111;">link</a>'
                ) if it.get("source_url") else ""
                notes_block = (
                    f'<div style="font-size:0.8rem; color:#6E6E73; margin-top:0.3rem; font-style:italic;">{it["notes"]}</div>'
                ) if it.get("notes") else ""

                row_a, row_b = st.columns([5, 1], gap="small")
                with row_a:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:0.85rem 1.05rem; margin-bottom:0.55rem;">
                        <div style="display:flex; align-items:baseline; gap:0.5rem; flex-wrap:wrap;">
                            <span style="font-family:'DM Serif Display',serif; font-size:1.05rem; color:#1C1917;">{it.get('name','—')}</span>
                            <span style="font-size:0.66rem; color:{pri_color}; letter-spacing:0.12em; text-transform:uppercase; font-weight:700;">{priority}</span>
                            {linked}
                        </div>
                        <div style="font-size:0.78rem; color:#6E6E73; margin-top:0.3rem;">{meta}{source_link}</div>
                        {notes_block}
                    </div>
                    """, unsafe_allow_html=True)
                with row_b:
                    if st.button("Remove", key=f"wl_rm_{it.get('id','')}", use_container_width=True):
                        rr = remove_wishlist_item(it.get("id", ""))
                        if rr.get("success"):
                            st.success(f"Removed {it.get('id','')}.")
                            st.rerun()
                        else:
                            st.error(rr.get("error", "Could not remove."))
        else:
            st.markdown(
                '<div style="font-size:0.82rem; color:#6E6E73; margin-bottom:1rem;">'
                'No wishlist items yet. Add one below, or save a wardrobe-gap suggestion '
                'from a recommended outfit.'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Add form ──
        st.markdown("""
        <div style="margin-top:1.4rem; margin-bottom:0.4rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.2rem; color:#1C1917;">Add to wishlist</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("wishlist_add_form", clear_on_submit=True):
            col_a, col_b = st.columns([3, 2], gap="small")
            with col_a:
                w_name = st.text_input("Item name or gap description", placeholder="e.g. Tailored cream blazer")
            with col_b:
                w_category = st.selectbox(
                    "Category (optional)",
                    options=["", "top", "bottom", "dress", "outerwear", "activewear", "shoes", "accessory"],
                )

            col_c, col_d = st.columns([2, 2], gap="small")
            with col_c:
                w_store = st.selectbox(
                    "Preferred store (optional)",
                    options=[""] + stores_for_select,
                    help=("Choose from your saved favorites. Add new stores in the "
                          "Favorite stores tab to see them here."),
                )
            with col_d:
                w_priority = st.selectbox("Priority", options=list(VALID_PRIORITIES), index=1)

            w_tags = st.multiselect(
                "Occasions",
                options=["work", "dinner", "gym", "formal", "casual", "weekend", "evening", "date", "travel", "versatile"],
                default=[],
            )
            w_notes = st.text_area("Notes (optional)", placeholder="Anything to remember when you eventually buy this.")
            w_url   = st.text_input("Product URL (optional)", placeholder="https://…")

            w_submit = st.form_submit_button("Add to wishlist", type="primary", use_container_width=True)
            if w_submit:
                rr = add_wishlist_item({
                    "name":            w_name,
                    "category":        w_category,
                    "preferred_store": w_store,
                    "tags":            w_tags,
                    "priority":        w_priority,
                    "notes":           w_notes,
                    "source_url":      w_url,
                })
                if rr.get("success"):
                    st.success(f"Saved {rr['item']['id']} · {rr['item']['name']}.")
                    st.rerun()
                else:
                    st.error(rr.get("error", "Could not save."))

    # ── Favorite stores tab ───────────────────────────────────
    with _tab_stores:
        stores = get_favorite_stores().get("stores", [])

        if stores:
            st.markdown(f"""
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.5rem;">
                {len(stores)} favorite store{'' if len(stores) == 1 else 's'}
            </div>
            """, unsafe_allow_html=True)
            for s in stores:
                name = s.get("name", "—")
                url = s.get("url")
                notes = s.get("notes")
                link_block = f' · <a href="{url}" target="_blank" style="color:#111111;">{url}</a>' if url else ""
                notes_block = f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.2rem; font-style:italic;">{notes}</div>' if notes else ""

                row_a, row_b = st.columns([5, 1], gap="small")
                with row_a:
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:0.85rem 1.05rem; margin-bottom:0.55rem;">
                        <div style="font-family:'DM Serif Display',serif; font-size:1.05rem; color:#1C1917;">{name}</div>
                        <div style="font-size:0.78rem; color:#6E6E73; margin-top:0.2rem;">{url or "no link saved"}{link_block if False else ""}</div>
                        {notes_block}
                    </div>
                    """, unsafe_allow_html=True)
                with row_b:
                    if st.button("Remove", key=f"st_rm_{name}", use_container_width=True):
                        rr = remove_favorite_store(name)
                        if rr.get("success"):
                            st.success(f"Removed {name}.")
                            st.rerun()
                        else:
                            st.error(rr.get("error", "Could not remove."))
        else:
            st.markdown(
                '<div style="font-size:0.82rem; color:#6E6E73; margin-bottom:1rem;">'
                "No favorite stores saved yet. Add a few below — Wearly will reference them "
                "when it spots a wardrobe gap."
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("""
        <div style="margin-top:1.4rem; margin-bottom:0.4rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.2rem; color:#1C1917;">Add a store</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("store_add_form", clear_on_submit=True):
            s_name  = st.text_input("Store name", placeholder="e.g. COS, Aritzia, Mejuri")
            s_url   = st.text_input("Store URL (optional)", placeholder="https://…")
            s_notes = st.text_input("Notes (optional)", placeholder="Why is this a favorite?")
            s_submit = st.form_submit_button("Add store", type="primary", use_container_width=True)
            if s_submit:
                rr = add_favorite_store(s_name, s_url, s_notes)
                if rr.get("success"):
                    st.success(f"Saved {rr['store']['name']} as a favorite.")
                    st.rerun()
                else:
                    st.error(rr.get("error", "Could not save."))

    # ── Prototype disclosure ──
    st.markdown("""
    <div style="margin-top:1.6rem; padding-top:1.05rem; border-top:1px solid #EEEEEE;">
        <p style="font-size:0.74rem; color:#6E6E73; line-height:1.6; margin:0;">
            <strong style="color:#6E6E73; letter-spacing:0.04em;">Prototype.</strong>
            Wearly doesn't perform live retailer searches yet — favorite stores act as
            personalization hints in shopping suggestions, and the wishlist is a saved
            local list. Real product catalogs and price lookups are future production work.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PROFILE — mock profile screen
# ─────────────────────────────────────────────

def _render_profile():
    # Pull the merged fit profile (seed owner + user overlay).
    try:
        from fit_tool import get_fit_profile, save_fit_profile
    except ImportError:
        from tools.fit_tool import get_fit_profile, save_fit_profile  # legacy layout

    fp_res = get_fit_profile()
    profile = fp_res.get("profile", {}) if fp_res.get("success") else {}

    name  = profile.get("name", "You")
    body  = profile.get("body_shape", "—")
    skin  = profile.get("skin_tone", "—")
    fit_v = profile.get("preferred_fit", "—")
    prefs = profile.get("style_preferences", []) or []
    prefs_html = "".join(
        f'<span style="display:inline-block; font-size:0.78rem; color:#6E6E73; padding:0.34rem 0.85rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px; margin:0 0.35rem 0.45rem 0;">{x}</span>'
        for x in prefs
    ) or '<span style="font-size:0.84rem; color:#6E6E73;">No preferences saved yet.</span>'

    modesty   = profile.get("modesty_preference") or "—"
    comfort   = profile.get("comfort_needs", []) or []
    goals     = profile.get("style_goals", []) or []
    highlights = profile.get("highlight_features", []) or []
    balances   = profile.get("balance_areas", []) or []

    initial = (name[:1] or "Y").upper()

    # ── Header card ──
    st.markdown(f"""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Profile</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">Prototype profile · stored locally on this device.</div>
    </div>

    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.6rem 1.6rem 1.4rem; margin-bottom:1.1rem;">
        <div style="display:flex; align-items:center; gap:1rem;">
            <div style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, #2E2E2E 0%, #111111 100%); color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-family:'DM Serif Display',serif; font-size:1.6rem;">
                {initial}
            </div>
            <div>
                <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1.1;">{name}</div>
                <div style="font-size:0.8rem; color:#6E6E73; margin-top:0.25rem; letter-spacing:0.04em;">Wearly member · local prototype</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Read-only "what Wearly knows" card ──
    def _list_chips(values, empty="—"):
        if not values:
            return f'<span style="font-size:0.86rem; color:#6E6E73;">{empty}</span>'
        return "".join(
            f'<span style="display:inline-block; font-size:0.78rem; color:#6E6E73; padding:0.32rem 0.8rem; background:#F5EDE3; border:1px solid #E5E5E5; border-radius:99px; margin:0 0.35rem 0.4rem 0;">{x}</span>'
            for x in values
        )

    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.4rem 1.6rem; margin-bottom:1.1rem;">
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.9rem;">Style profile</div>
        <div style="display:flex; flex-wrap:wrap; gap:1.4rem; row-gap:1rem;">
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Body shape</div>
                <div style="font-size:0.95rem; color:#1C1917;">{(body or '—').title() if isinstance(body, str) else '—'}</div>
            </div>
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Skin tone</div>
                <div style="font-size:0.95rem; color:#1C1917;">{(skin or '—').title() if isinstance(skin, str) else '—'}</div>
            </div>
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Preferred fit</div>
                <div style="font-size:0.95rem; color:#1C1917;">{(fit_v or '—').title() if isinstance(fit_v, str) else '—'}</div>
            </div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Style preferences</div>
            <div>{prefs_html}</div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Modesty preference</div>
            <div style="font-size:0.9rem; color:#1C1917;">{(modesty or '—').title() if isinstance(modesty, str) else '—'}</div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Comfort needs</div>
            <div>{_list_chips(comfort)}</div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Style goals</div>
            <div>{_list_chips(goals)}</div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Areas to highlight</div>
            <div>{_list_chips(highlights)}</div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Areas to balance</div>
            <div>{_list_chips(balances)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Measurements card (renders only when at least one is saved) ──
    # Display unit comes from session state ("measure_unit"), set by the
    # toggle inside the edit form. Internal storage is always inches.
    _meas = profile.get("measurements", {}) or {}
    if any(_meas.values()):
        try:
            from fit_tool import MEASUREMENT_FIELDS as _MF, INCH_TO_CM as _IN2CM
        except Exception:
            _MF, _IN2CM = [], 2.54
        _disp_unit = st.session_state.get("measure_unit", "in")
        _rows = ""
        for _key, _label, _tip in _MF:
            _val = _meas.get(_key)
            if _val:
                _shown = _val if _disp_unit == "in" else (_val * _IN2CM)
                _rows += (
                    f'<div style="flex:1; min-width:120px;">'
                    f'<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; '
                    f'text-transform:uppercase; margin-bottom:0.25rem;">{_label}</div>'
                    f'<div style="font-size:0.95rem; color:#1C1917;">{_shown:.1f} {_disp_unit}</div>'
                    f'</div>'
                )
        if _rows:
            st.markdown(
                f'<div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; '
                f'padding:1.4rem 1.6rem; margin-bottom:1.1rem;">'
                f'<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; '
                f'text-transform:uppercase; font-weight:600; margin-bottom:0.9rem;">Measurements</div>'
                f'<div style="display:flex; flex-wrap:wrap; gap:1.4rem; row-gap:1rem;">{_rows}</div>'
                f'<div style="font-size:0.74rem; color:#8E8E93; margin-top:1rem; line-height:1.55;">'
                f"Private. Stored locally on this device. Used only to suggest pieces "
                f"that fit your real proportions."
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # ── Edit form (overlay only — never touches seed wardrobe) ──
    # First-time users land on a blank seed and can fill in everything;
    # returning users see their saved values pre-filled. Every field is
    # optional. Wearly never frames a body as a problem.
    measurements = profile.get("measurements", {}) or {}

    with st.expander("Edit your profile, preferences & measurements", expanded=False):
        st.markdown("""
        <div style="font-size:0.82rem; color:#6E6E73; line-height:1.55; margin-bottom:0.8rem;">
            Every field is optional. Wearly applies a preference only when you've shared it.
            <br><strong style="color:#111111;">Body-positive language only.</strong>
            Wearly rejects corrective vocabulary like "hide," "fix," or "minimize" by design.
            Measurements are private and stored locally — they help Wearly suggest pieces
            that fit your real proportions instead of relying only on a body-shape label.
        </div>
        """, unsafe_allow_html=True)

        _BODY_SHAPE_OPTIONS = ["", "hourglass", "pear", "apple", "rectangle",
                               "inverted triangle", "athletic", "neat hourglass"]
        _SKIN_TONE_OPTIONS  = ["", "warm olive", "cool fair", "deep warm",
                               "neutral", "cool deep", "warm light"]
        _FIT_OPTIONS        = ["", "tailored", "relaxed", "structured",
                               "fluid", "loose", "fitted"]
        _STYLE_PREFS_OPTIONS = ["classic", "elegant", "minimal", "edgy",
                                "romantic", "playful", "preppy", "bohemian",
                                "androgynous", "sporty", "modern"]
        _MODESTY_OPTIONS = ["", "low", "moderate", "high"]
        _COMFORT_OPTIONS = ["soft fabrics", "stretchy fabrics", "no stiff collars",
                            "breathable layers", "no tight waistbands", "no scratchy seams"]
        _GOAL_OPTIONS = ["elevated", "modernized", "stay timeless", "more confident",
                         "feel like myself", "look pulled together"]
        _AREA_OPTIONS = ["shoulders", "neckline", "waist", "hips", "legs",
                         "arms", "back", "collarbone"]

        # Unit toggle for measurements. Lives OUTSIDE the form so flipping
        # it re-renders the inputs immediately (st.form batches inputs and
        # would only react on submit). Internal storage is always inches —
        # we convert on save and on display.
        _unit_cols = st.columns([2, 1], gap="medium")
        with _unit_cols[0]:
            st.markdown(
                "<div style='font-size:0.78rem; color:#6E6E73; padding-top:0.4rem;'>"
                "Measurement units</div>",
                unsafe_allow_html=True,
            )
        with _unit_cols[1]:
            _unit_choice = st.radio(
                "Units",
                options=["in", "cm"],
                horizontal=True,
                label_visibility="collapsed",
                index=0 if st.session_state.get("measure_unit", "in") == "in" else 1,
                key="measure_unit",
            )

        with st.form("profile_edit_form"):
            # ── Section 1: Identity ──────────────────────────────
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600; margin:0.2rem 0 0.6rem;'>"
                "Identity</div>", unsafe_allow_html=True,
            )
            new_name = st.text_input(
                "Display name",
                value=(name if isinstance(name, str) and name != "You" else ""),
                placeholder="What should Wearly call you?",
                help="Used only in greetings (the chip and the home screen).",
            )

            # ── Section 2: Style profile ─────────────────────────
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600; margin:1.2rem 0 0.6rem;'>"
                "Style profile</div>", unsafe_allow_html=True,
            )
            col_s1, col_s2, col_s3 = st.columns(3, gap="medium")
            with col_s1:
                new_body = st.selectbox(
                    "Body shape",
                    options=_BODY_SHAPE_OPTIONS,
                    index=_BODY_SHAPE_OPTIONS.index(body) if (isinstance(body, str) and body in _BODY_SHAPE_OPTIONS) else 0,
                    help="A proportion preference, not a classification. Industry-standard "
                         "label set — Wearly uses it only to suggest cuts you've said work for you. "
                         "Leave blank if you'd rather skip the category.",
                )
            with col_s2:
                new_skin = st.selectbox(
                    "Skin tone palette",
                    options=_SKIN_TONE_OPTIONS,
                    index=_SKIN_TONE_OPTIONS.index(skin) if (isinstance(skin, str) and skin in _SKIN_TONE_OPTIONS) else 0,
                    help="Pick the palette closest to your undertone. Drives Step 7 color scoring.",
                )
            with col_s3:
                new_fit = st.selectbox(
                    "Preferred fit",
                    options=_FIT_OPTIONS,
                    index=_FIT_OPTIONS.index(fit_v) if (isinstance(fit_v, str) and fit_v in _FIT_OPTIONS) else 0,
                    help="The cut you reach for most often.",
                )
            new_prefs = st.multiselect(
                "Style preferences",
                options=_STYLE_PREFS_OPTIONS,
                default=[p for p in prefs if p in _STYLE_PREFS_OPTIONS],
                help="A few words that describe your taste. Wearly surfaces these in the reasoning trail.",
            )

            # ── Section 3: Comfort & expression ──────────────────
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600; margin:1.4rem 0 0.6rem;'>"
                "Comfort & expression</div>", unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2, gap="medium")
            with col_a:
                new_modesty = st.selectbox(
                    "Modesty preference",
                    options=_MODESTY_OPTIONS,
                    index=_MODESTY_OPTIONS.index(modesty) if modesty in _MODESTY_OPTIONS else 0,
                    help="Higher modesty filters out very revealing pieces; 'low' applies no constraint.",
                )
                new_goals = st.multiselect(
                    "Style goals", options=_GOAL_OPTIONS,
                    default=[g for g in goals if g in _GOAL_OPTIONS],
                )
                new_highlights = st.multiselect(
                    "Features to highlight", options=_AREA_OPTIONS,
                    default=[h for h in highlights if h in _AREA_OPTIONS],
                    help="Body areas you want to draw attention to.",
                )
            with col_b:
                new_comfort = st.multiselect(
                    "Comfort preferences", options=_COMFORT_OPTIONS,
                    default=[c for c in comfort if c in _COMFORT_OPTIONS],
                )
                new_balances = st.multiselect(
                    "Areas to balance", options=_AREA_OPTIONS,
                    default=[b for b in balances if b in _AREA_OPTIONS],
                    help="Body areas you'd like to bring into proportion. Wearly never frames these as flaws.",
                )

            # ── Section 4: Measurements ──────────────────────────
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600; margin:1.4rem 0 0.4rem;'>"
                "Body measurements</div>", unsafe_allow_html=True,
            )
            st.markdown(
                "<div style='font-size:0.78rem; color:#6E6E73; line-height:1.55; margin-bottom:0.8rem;'>"
                "Stored locally. Each field has a small <strong>?</strong> tip explaining how to "
                "measure — bust, waist, and hips paraphrased from "
                "<a href='https://thesewingrevival.com/pages/choosing-your-size' target='_blank' "
                "style='color:#111111;'>The Sewing Revival</a>. Helps Wearly suggest pieces that fit "
                "your <em>actual</em> proportions."
                "</div>", unsafe_allow_html=True,
            )

            # Import the field definitions from fit_tool so the form and the
            # data model never drift.
            try:
                from fit_tool import MEASUREMENT_FIELDS as _MEAS_FIELDS, INCH_TO_CM as _IN2CM
            except Exception:
                _MEAS_FIELDS, _IN2CM = [], 2.54

            # Unit-aware bounds. Internal storage is always inches; the
            # input displays in the user-selected unit and we convert on save.
            _use_cm = (_unit_choice == "cm")
            _max_input = 120.0 * (_IN2CM if _use_cm else 1.0)
            _step      = 1.0   if _use_cm else 0.5

            new_measurements = {}
            # 4 columns x N rows
            _per_row = 4
            for _row_start in range(0, len(_MEAS_FIELDS), _per_row):
                _row = _MEAS_FIELDS[_row_start:_row_start + _per_row]
                _cols = st.columns(len(_row), gap="medium")
                for _i, (_key, _label, _tip) in enumerate(_row):
                    with _cols[_i]:
                        _current_in = measurements.get(_key)
                        # The number_input displays whichever unit the user
                        # picked; we convert from stored inches.
                        _initial = 0.0
                        if isinstance(_current_in, (int, float)) and _current_in:
                            _initial = float(_current_in) * (_IN2CM if _use_cm else 1.0)
                        _shown = st.number_input(
                            f"{_label} ({_unit_choice})",
                            min_value=0.0,
                            max_value=_max_input,
                            step=_step,
                            value=round(_initial, 1),
                            help=_tip,
                            key=f"measure_{_key}",
                        )
                        # Convert back to inches for storage.
                        new_measurements[_key] = (
                            _shown / _IN2CM if _use_cm else _shown
                        )

            # ── Save ─────────────────────────────────────────────
            st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
            save_btn = st.form_submit_button(
                "Save profile", type="primary", use_container_width=True,
            )
            if save_btn:
                upd = {
                    "name":               (new_name.strip() or None),
                    "body_shape":         (new_body or None),
                    "skin_tone":          (new_skin or None),
                    "preferred_fit":      (new_fit or None),
                    "style_preferences":  new_prefs,
                    "modesty_preference": (new_modesty or None),
                    "comfort_needs":      new_comfort,
                    "style_goals":        new_goals,
                    "highlight_features": new_highlights,
                    "balance_areas":      new_balances,
                    "measurements":       new_measurements,
                }
                res = save_fit_profile(upd)
                if res.get("success"):
                    st.success(
                        "Profile updated. Wearly will reflect these in your next outfit."
                    )
                    st.rerun()
                else:
                    st.error(f"Could not save: {res.get('error', 'unknown error')}")

    st.markdown("""
    <p style="font-size:0.74rem; color:#6E6E73; line-height:1.55; margin-top:1rem;">
        <strong style="color:#6E6E73; letter-spacing:0.04em;">Privacy.</strong>
        Your profile is stored locally in this prototype. Real authentication and cloud sync are future work.
    </p>
    <div style="margin-top:1.2rem; padding-top:1rem; border-top:1px solid #EEEEEE;">
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.5rem;">Learn more</div>
        <p style="font-size:0.82rem; color:#2E2E2E; line-height:1.6;">
            The <a href="https://eatedalsf.github.io/styling-agent/" target="_blank" style="color:#111111; text-decoration:underline;">Wearly Intelligent Book</a>
            documents the agent's design principles, evidence categories, skill rules, knowledge graph, and architecture — all searchable in one place.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BEFORE / AFTER — comparison + live run
# ─────────────────────────────────────────────

def _render_demo():
    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Before &amp; After</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">What changes when a styling agent reasons through your day.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("""
        <div class="compare-col compare-before">
            <div class="compare-label">Before — Manual Planning</div>
            <div class="compare-row"><span class="compare-key">Time to decide</span><span class="compare-val">~15 minutes</span></div>
            <div class="compare-row"><span class="compare-key">Weather check</span><span class="compare-val">Often forgotten</span></div>
            <div class="compare-row"><span class="compare-key">Color coordination</span><span class="compare-val">Guesswork</span></div>
            <div class="compare-row"><span class="compare-key">Calendar awareness</span><span class="compare-val">Manual lookup</span></div>
            <div class="compare-row"><span class="compare-key">Season awareness</span><span class="compare-val">Mental model</span></div>
            <div class="compare-row"><span class="compare-key">Reasoning</span><span class="compare-val">Invisible</span></div>
            <div class="compare-row"><span class="compare-key">Confidence</span><span class="compare-val">Low–Medium</span></div>
            <div class="compare-row"><span class="compare-key">Coat reminder</span><span class="compare-val">Missed it</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="compare-col compare-after">
            <div class="compare-label">After — Wearly</div>
            <div class="compare-row"><span class="compare-key">Time to decide</span><span class="compare-val">~3 seconds</span></div>
            <div class="compare-row"><span class="compare-key">Weather check</span><span class="compare-val">Automatic (live API)</span></div>
            <div class="compare-row"><span class="compare-key">Color coordination</span><span class="compare-val">0–100 score</span></div>
            <div class="compare-row"><span class="compare-key">Calendar awareness</span><span class="compare-val">Automatic</span></div>
            <div class="compare-row"><span class="compare-key">Season awareness</span><span class="compare-val">Data-driven</span></div>
            <div class="compare-row"><span class="compare-key">Reasoning</span><span class="compare-val">Fully explained</span></div>
            <div class="compare-row"><span class="compare-key">Confidence</span><span class="compare-val">High (structured)</span></div>
            <div class="compare-row"><span class="compare-key">Coat reminder</span><span class="compare-val">Included</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
    if st.button("See it live →", key="demo_live", type="primary", use_container_width=True):
        st.session_state["rejected_ids"] = []
        st.session_state["rejection_reasons"] = []
        with st.spinner("Running the agent live…"):
            _run_and_store("calendar")
        st.rerun()

    if st.session_state.get("result"):
        st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.6rem;">Live result</div>
        """, unsafe_allow_html=True)
        _render_outfit_result(st.session_state["result"])

    # ── Schema graph (the abstract knowledge graph) ─────────
    # Sits at the bottom of the demo screen so a reviewer who's just
    # seen the live agent run can step up one level of abstraction and
    # see HOW the system models the world. Read alongside the live-run
    # graph rendered inside any outfit result.
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Serif Display',serif; font-size:1.45rem; color:#1C1917; line-height:1.2;">
        How Wearly models your day
    </div>
    <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem; margin-bottom:0.7rem; line-height:1.55;">
        The knowledge graph below shows the entity types and relations Wearly
        reasons over. Every recommendation traces through this graph — the
        live-run graph inside an outfit result shows one specific traversal.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("View the schema graph (interactive)"):
        try:
            from graph_tool import render_schema_graph_html, schema_graph_summary
            summary = schema_graph_summary()
            st.caption(
                f"{summary['entities']} entities · {summary['edges']} relations · "
                f"drag nodes to rearrange, hover for definitions, scroll to zoom."
            )
            html_doc = render_schema_graph_html()
            components.html(html_doc, height=600, scrolling=False)
            st.caption(
                "Canonical source: `graph/graph.json` and `graph/schema.md`. "
                "Read more in the **Knowledge Graph** section of the "
                "[Intelligent Book](https://eatedalsf.github.io/styling-agent/)."
            )
        except ImportError as _e:
            st.info(f"Graph rendering unavailable: {_e}")
        except Exception as _e:
            st.warning(f"Graph could not render: {_e}")


# ─────────────────────────────────────────────
# SECTION ROUTER
# ─────────────────────────────────────────────

_router = {
    "home":     _render_home,
    "today":    _render_today,
    "wardrobe": _render_wardrobe,
    "shop":     _render_shop,
    "profile":  _render_profile,
    "demo":     _render_demo,
}
_router.get(st.session_state["section"], _render_home)()
