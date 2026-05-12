"""
app.py — Streamlit Web Interface for Wearly
Run with: streamlit run app.py
"""

import sys
import os
import streamlit as st

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
    from tools.wardrobe_tool import get_owner_profile
except ModuleNotFoundError:
    from styling_agent import run_agent
    from calendar_tool import get_upcoming_events
    from weather_tool import get_weather
    from wardrobe_tool import get_owner_profile

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
# CUSTOM CSS — Refined editorial aesthetic
# Dark ivory + warm terracotta + deep charcoal
# Font: DM Serif Display + DM Sans
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #1C1917;
}
/* Soft warm vertical gradient — adds depth without losing the calm.
   Light at the top where the brand sits, slightly warmer toward the bottom. */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #F8F4ED 0%, #F4EDE3 100%) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
/* Tighten the default Streamlit page padding so content sits closer to the
   app bar — feels more like a phone screen, less like a web page. */
.block-container { padding-top: 0.6rem !important; padding-bottom: 4rem !important; max-width: 720px !important; }

/* ───── Product top app bar ───── */
.app-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 0.2rem 0.95rem;
    margin-bottom: 0.4rem;
    border-bottom: 1px solid #EDE5DC;
}
.brand {
    display: flex;
    align-items: baseline;
    gap: 0.55rem;
}
.brand-mark {
    width: 26px; height: 26px;
    border-radius: 50%;
    background: linear-gradient(135deg, #C17F5A 0%, #D4956F 100%);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #FDFAF7;
    font-family: 'DM Serif Display', serif;
    font-size: 0.95rem;
    line-height: 1;
    transform: translateY(2px);
}
.brand-wordmark {
    font-family: 'DM Serif Display', serif;
    font-size: 1.45rem;
    color: #1C1917;
    line-height: 1;
    letter-spacing: -0.01em;
}
.brand-tag {
    font-size: 0.6rem;
    color: #B8A99A;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 600;
    border: 1px solid #E8D7C8;
    padding: 2px 7px;
    border-radius: 99px;
    background: #FDFAF7;
    transform: translateY(-2px);
}
.app-bar-right {
    display: flex; align-items: center; gap: 0.6rem;
}
.profile-chip {
    display: inline-flex; align-items: center; gap: 0.55rem;
    padding: 0.32rem 0.55rem 0.32rem 0.4rem;
    background: #FDFAF7;
    border: 1px solid #E8E0D8;
    border-radius: 99px;
}
.profile-avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #D4956F 0%, #C17F5A 100%);
    color: #FDFAF7;
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-flex; align-items: center; justify-content: center;
}
.profile-name {
    font-size: 0.78rem; color: #4A3D36; font-weight: 500;
    max-width: 84px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ───── Section nav pills row ───── */
.nav-row { margin: 0.4rem 0 1.1rem; }

/* Sidebar — light, calm, warm. No dark blocks. */
[data-testid="stSidebar"] {
    background-color: #FDFAF7 !important;
    border-right: 1px solid #EDE5DC;
}
[data-testid="stSidebar"] * {
    color: #1C1917;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p {
    color: #7C6F64 !important;
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #F5F0EB !important;
    border: 1px solid #E8E0D8 !important;
    color: #1C1917 !important;
}
/* Radio option labels — readable on the new ivory background */
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    color: #1C1917 !important;
    font-size: 0.92rem;
    letter-spacing: 0;
    text-transform: none;
    font-weight: 400;
}

/* Main title */
.main-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    color: #1C1917;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0;
}
.main-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    color: #7C6F64;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.3rem;
    margin-bottom: 2.5rem;
}

/* Cards */
.card {
    background: #FDFAF7;
    border: 1px solid #E8E0D8;
    border-radius: 2px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.1rem;
}
.card-title {
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #A8937E;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

/* Outfit items */
.outfit-item {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid #EDE5DC;
    font-size: 0.95rem;
}
.outfit-item:last-child { border-bottom: none; }
.item-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #C17F5A;
    flex-shrink: 0;
}
/* Actual color swatch for outfit items — replaces emoji glyphs */
.item-swatch {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 1px solid rgba(28,25,23,0.10);
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.25);
}
.item-color-chip {
    font-size: 0.72rem;
    color: #9C8A7A;
    background: #EDE5DC;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: auto;
}

/* Score bar */
.score-bar-bg {
    background: #EDE5DC;
    border-radius: 2px;
    height: 6px;
    margin-top: 0.5rem;
}
.score-bar-fill {
    height: 6px;
    border-radius: 2px;
    background: linear-gradient(90deg, #C17F5A, #D4956F);
    transition: width 0.6s ease;
}

/* Step log */
.step-row {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid #EDE5DC;
    font-size: 0.87rem;
}
.step-row:last-child { border-bottom: none; }
.step-badge {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    padding: 2px 7px;
    border-radius: 2px;
    flex-shrink: 0;
    margin-top: 1px;
}
.badge-ok { background: #D4EDDA; color: #1D6033; }
.badge-fallback { background: #FFF3CD; color: #7D5A00; }
.badge-gap { background: #F8D7DA; color: #7A1D21; }
.step-name { font-weight: 600; color: #1C1917; white-space: nowrap; }
.step-output { color: #6B5C52; }

/* Reasoning */
.reason-item {
    padding: 0.45rem 0;
    border-bottom: 1px solid #EDE5DC;
    font-size: 0.88rem;
    color: #4A3D36;
    display: flex;
    gap: 0.6rem;
}
.reason-num {
    color: #C17F5A;
    font-weight: 700;
    flex-shrink: 0;
    font-size: 0.8rem;
    margin-top: 1px;
}

/* Before/after */
.compare-col {
    padding: 1.4rem 1.6rem;
    border-radius: 2px;
}
.compare-before { background: #F0EAE4; border-left: 3px solid #B8A99A; }
.compare-after  { background: #FAF3EE; border-left: 3px solid #C17F5A; }
.compare-label {
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.9rem;
}
.compare-before .compare-label { color: #8A7060; }
.compare-after  .compare-label { color: #9F5A36; }
.compare-row {
    display: flex;
    justify-content: space-between;
    padding: 0.35rem 0;
    font-size: 0.87rem;
    border-bottom: 1px solid rgba(0,0,0,0.06);
}
.compare-row:last-child { border-bottom: none; }
.compare-key { color: #6B5C52; }
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
    background: #FAF3EE;
    color: #9F5A36;
    border: 1px solid #EAD7C9;
    margin-bottom: 0.6rem;
}

/* Gap alert */
.gap-alert {
    background: #FDF3EE;
    border: 1px solid #E8C4A8;
    border-left: 3px solid #C17F5A;
    border-radius: 2px;
    padding: 1rem 1.2rem;
    margin-top: 0.5rem;
}
.gap-title { font-weight: 600; color: #8A4A20; font-size: 0.88rem; margin-bottom: 0.5rem; }
.gap-item { font-size: 0.86rem; color: #6B4030; padding: 0.2rem 0; }

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
    color: #1C1917;
    line-height: 1;
}
.weather-detail {
    font-size: 0.82rem;
    color: #7C6F64;
    line-height: 1.8;
}
.weather-advice {
    font-size: 0.84rem;
    color: #4A3D36;
    background: #EDE5DC;
    padding: 0.5rem 0.9rem;
    border-radius: 2px;
    margin-top: 0.5rem;
}

/* Default button (used for section nav, secondary actions) — subtle, warm */
.stButton > button {
    background: #FDFAF7 !important;
    color: #4A3D36 !important;
    border: 1px solid #E8E0D8 !important;
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
    background: #F5EDE3 !important;
    border-color: #D4C4B2 !important;
    color: #1C1917 !important;
}
/* Primary button (the CTA — terracotta filled, larger touch target) */
.stButton > button[kind="primary"] {
    background: #C17F5A !important;
    color: #FDFAF7 !important;
    border: none !important;
    border-radius: 4px !important;
    font-size: 0.95rem !important;
    padding: 0.82rem 1.6rem !important;
    box-shadow: 0 1px 0 rgba(28,25,23,0.04) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #A86A48 !important;
    color: #FDFAF7 !important;
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
    # Warm-palette only: no cool greens or reds.
    if score >= 80: return "#9F5A36"   # confident deep terracotta
    if score >= 60: return "#C17F5A"   # accent terracotta
    return "#8A4A20"                    # warm warning brown


# ─────────────────────────────────────────────
# SESSION STATE — section routing + mock profile
# ─────────────────────────────────────────────

if "section" not in st.session_state:
    st.session_state["section"] = "home"
if "result" not in st.session_state:
    st.session_state["result"] = None
if "signed_in" not in st.session_state:
    # Mock auth state. Real authentication is future work. The UI shows
    # a profile chip either way so the product feels owned by a person.
    st.session_state["signed_in"] = True
if "everyday_choice" not in st.session_state:
    st.session_state["everyday_choice"] = "Work"


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


# ─────────────────────────────────────────────
# TOP APP BAR — wordmark left, profile chip right
# ─────────────────────────────────────────────

_name, _initial = _profile_display()

st.markdown(f"""
<div class="app-bar">
    <div class="brand">
        <span class="brand-mark">W</span>
        <span class="brand-wordmark">Wearly</span>
        <span class="brand-tag">Prototype</span>
    </div>
    <div class="app-bar-right">
        <div class="profile-chip" title="Prototype profile · local only">
            <span class="profile-avatar">{_initial}</span>
            <span class="profile-name">{_name}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SECTION NAV — primary product navigation
# ─────────────────────────────────────────────

_SECTIONS = [
    ("home",     "Home"),
    ("today",    "Today"),
    ("wardrobe", "Wardrobe"),
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
        <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.16em; text-transform:uppercase; margin-top:0.35rem;">Prototype controls</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("<p style='font-size:0.72rem; color:#7C6F64; line-height:1.55;'>Try a specific occasion instead of today's calendar event:</p>", unsafe_allow_html=True)
    st.session_state["everyday_choice"] = st.selectbox(
        "Occasion",
        ["Work", "Gym", "Dinner", "Formal Gala", "Weekend Brunch", "Casual Outing"],
        index=["Work", "Gym", "Dinner", "Formal Gala", "Weekend Brunch", "Casual Outing"].index(st.session_state.get("everyday_choice","Work")),
        label_visibility="collapsed",
    )
    if st.button("Plan this occasion →", key="sidebar_everyday", use_container_width=True):
        with st.spinner("Reading your closet · scoring color harmony…"):
            st.session_state["result"] = run_agent(
                mode="everyday",
                everyday_request=st.session_state["everyday_choice"],
            )
        _goto("today")

    st.markdown("---")
    st.markdown("""
    <p style="font-size:0.72rem; color:#7C6F64; line-height:1.6;">
    <strong style="color:#4A3D36;">Privacy.</strong>
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
            <div style="font-size:0.84rem; color:#7C6F64;">
                {event.get('date','Today')} &nbsp;·&nbsp; {event.get('time','')}
            </div>
            {"<div style='font-size:0.82rem;color:#9C8A7A;margin-top:0.5rem;'>" + event.get('notes','') + "</div>" if event.get('notes') else ""}
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

        inner = "".join(item_rows) if item_rows else "<p style='color:#9C8A7A'>No items selected.</p>"
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
            flags_html += f"<div style='font-size:0.82rem;color:#8A4A20;padding:0.25rem 0;'>{f}</div>"

        st.markdown(f"""
        <div class="card">
            <div class="card-title">Color Harmony Score</div>
            <div style="font-family:'DM Serif Display',serif; font-size:2.8rem; color:{sc}; line-height:1;">
                {score_val}<span style="font-size:1.2rem; color:#9C8A7A">/100</span>
            </div>
            <div style="font-size:0.78rem;color:#9C8A7A;margin:0.3rem 0 0.4rem;">
                Skin tone: {result.get('profile',{}).get('skin_tone','—')}
            </div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_pct}%"></div>
            </div>
            {flags_html if flags_html else "<div style='font-size:0.83rem;color:#9F5A36;margin-top:0.6rem;'>All colors work well for your skin tone.</div>"}
        </div>
        """, unsafe_allow_html=True)

    # ── Gaps ────────────────────────────────────────────────
    if gaps:
        gap_items = "".join(f"<div class='gap-item'>→ {s}</div>" for s in shopping)
        st.markdown(f"""
        <div class="gap-alert">
            <div class="gap-title">Wardrobe Gap · {', '.join(gaps)} missing for this occasion</div>
            {gap_items}
        </div>
        """, unsafe_allow_html=True)

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
        f'<div style="font-size:0.8rem; color:#9C8A7A; margin-top:0.3rem; font-style:italic; line-height:1.5;">{ev_notes}</div>'
        if ev_notes else ""
    )

    st.markdown(f"""
    <div style="position:relative; background:#FDFAF7; border:1px solid #E8E0D8; border-radius:6px; padding:1.55rem 1.6rem 1.4rem; margin-bottom:1.1rem; overflow:hidden; box-shadow:0 1px 0 rgba(28,25,23,0.02);">
        <div style="position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg, #C17F5A 0%, #D4956F 60%, #E8B998 100%);"></div>
        <div style="font-size:0.7rem; color:#A8937E; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:1rem;">
            Today · {today_label}
        </div>
        <div style="margin-bottom:1.1rem;">
            <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">Next event</div>
            <div style="font-family:'DM Serif Display',serif; font-size:1.45rem; color:#1C1917; line-height:1.15;">{ev_title}</div>
            <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">{ev_meta}</div>
            {notes_html}
        </div>
        <div style="height:1px; background:#EDE5DC; margin:0 0 1.05rem;"></div>
        <div>
            <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem;">Weather · {w_city}</div>
            <div style="display:flex; align-items:baseline; gap:0.65rem; flex-wrap:wrap;">
                <div style="font-family:'DM Serif Display',serif; font-size:1.6rem; color:#1C1917; line-height:1;">{w_temp}°F</div>
                <div style="font-size:0.95rem; color:#4A3D36;">{w_cond}</div>
            </div>
            <div style="font-size:0.82rem; color:#7C6F64; margin-top:0.45rem; line-height:1.5;">{w_advice}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Plan today's outfit →", key="home_cta", type="primary", use_container_width=True):
        with st.spinner("Reading your calendar · checking the weather · filtering your closet · scoring color harmony…"):
            st.session_state["result"] = run_agent(mode="calendar")
        _goto("today")

    st.markdown("""
    <div style="text-align:center; font-size:0.72rem; color:#9C8A7A; margin-top:0.55rem; margin-bottom:0.4rem; letter-spacing:0.02em;">
        7 reasoning steps · ~3 seconds · no account required
    </div>
    """, unsafe_allow_html=True)

    # ── Agent-process pill row ──
    pill = (
        "display:inline-flex; align-items:center; gap:0.45rem; "
        "padding:0.42rem 0.82rem 0.42rem 0.7rem; background:#FDFAF7; "
        "border:1px solid #E8E0D8; border-radius:99px; "
        "font-size:0.78rem; color:#3D332D; font-weight:500;"
    )
    num = (
        "color:#C17F5A; font-size:0.66rem; font-weight:700; "
        "letter-spacing:0.05em; font-family:'DM Sans',sans-serif;"
    )
    arrow = "color:#C8B8A8; font-size:0.85rem; padding:0 0.05rem;"
    st.markdown(f"""
    <div style="margin-top:1.4rem; padding:1rem 0.2rem 0.4rem; text-align:center;">
        <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.16em; text-transform:uppercase; font-weight:600; margin-bottom:0.85rem;">
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
        <p style="font-size:0.82rem; color:#7C6F64; margin:1rem auto 0; max-width:24rem; line-height:1.55;">
            An <strong style="color:#1C1917;">agent</strong>, not a chatbot.
            Wearly reads your context first, then recommends — and explains every choice.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.6rem; padding-top:1.05rem; border-top:1px solid #EDE5DC;">
        <p style="font-size:0.74rem; color:#9C8A7A; line-height:1.55; margin:0; max-width:30rem;">
            <strong style="color:#7C6F64; letter-spacing:0.04em;">Privacy first.</strong>
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
            <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">Wearly's recommendation for the next event on your calendar.</div>
        </div>
        """, unsafe_allow_html=True)
        _render_outfit_result(res)
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        if st.button("Replan from scratch", key="replan_today", use_container_width=False):
            with st.spinner("Re-running the agent…"):
                st.session_state["result"] = run_agent(mode="calendar")
            st.rerun()
    else:
        st.markdown("""
        <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Today</div>
            <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">No outfit yet — let's plan one.</div>
        </div>
        <div style="background:#FDFAF7; border:1px solid #E8E0D8; border-radius:6px; padding:2rem 1.6rem; text-align:center;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.2rem; color:#4A3D36;">Plan today's outfit</div>
            <div style="font-size:0.84rem; color:#7C6F64; margin-top:0.5rem; max-width:24rem; margin-left:auto; margin-right:auto; line-height:1.55;">
                Wearly will read your calendar, check the weather, and choose pieces from your closet — with reasoning at every step.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        if st.button("Plan today's outfit →", key="today_cta", type="primary", use_container_width=True):
            with st.spinner("Reading your calendar · checking the weather · filtering your closet · scoring color harmony…"):
                st.session_state["result"] = run_agent(mode="calendar")
            st.rerun()


# ─────────────────────────────────────────────
# WARDROBE — coming-soon stub
# ─────────────────────────────────────────────

def _render_wardrobe():
    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Wardrobe</div>
        <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">Your digital closet — coming soon.</div>
    </div>
    <div style="background:#FDFAF7; border:1px solid #E8E0D8; border-radius:6px; padding:2.4rem 1.6rem; text-align:center;">
        <div style="display:inline-block; padding:4px 11px; background:#FAF3EE; color:#9F5A36; border:1px solid #EAD7C9; border-radius:99px; font-size:0.66rem; letter-spacing:0.12em; text-transform:uppercase; font-weight:600; margin-bottom:1rem;">In design</div>
        <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1.2; max-width:24rem; margin:0 auto;">
            Build a real closet, one piece at a time.
        </div>
        <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.7rem; max-width:28rem; margin-left:auto; margin-right:auto; line-height:1.6;">
            Snap a photo of any garment, drop in a product link, or type in pieces by hand.
            Wearly remembers what you own, what you've worn recently, and what's missing.
        </div>
        <div style="display:flex; gap:0.6rem; flex-wrap:wrap; justify-content:center; margin-top:1.4rem;">
            <span style="font-size:0.78rem; color:#7C6F64; padding:0.4rem 0.9rem; background:#F5EDE3; border:1px solid #E8E0D8; border-radius:99px;">Photo upload</span>
            <span style="font-size:0.78rem; color:#7C6F64; padding:0.4rem 0.9rem; background:#F5EDE3; border:1px solid #E8E0D8; border-radius:99px;">Product link import</span>
            <span style="font-size:0.78rem; color:#7C6F64; padding:0.4rem 0.9rem; background:#F5EDE3; border:1px solid #E8E0D8; border-radius:99px;">Wear history</span>
            <span style="font-size:0.78rem; color:#7C6F64; padding:0.4rem 0.9rem; background:#F5EDE3; border:1px solid #E8E0D8; border-radius:99px;">Reject &amp; regenerate</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# PROFILE — mock profile screen
# ─────────────────────────────────────────────

def _render_profile():
    p_res = get_owner_profile()
    profile = p_res.get("profile", {}) if p_res.get("success") else {}
    name = profile.get("name", "You")
    body = profile.get("body_shape", "—")
    skin = profile.get("skin_tone", "—")
    fit  = profile.get("preferred_fit", "—")
    prefs = profile.get("style_preferences", []) or []
    prefs_html = "".join(
        f'<span style="display:inline-block; font-size:0.78rem; color:#7C6F64; padding:0.34rem 0.85rem; background:#F5EDE3; border:1px solid #E8E0D8; border-radius:99px; margin:0 0.35rem 0.45rem 0;">{x}</span>'
        for x in prefs
    ) or '<span style="font-size:0.84rem; color:#9C8A7A;">No preferences saved yet.</span>'

    initial = (name[:1] or "Y").upper()

    st.markdown(f"""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Profile</div>
        <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">Prototype profile · stored locally on this device.</div>
    </div>

    <div style="background:#FDFAF7; border:1px solid #E8E0D8; border-radius:6px; padding:1.6rem 1.6rem 1.4rem; margin-bottom:1.1rem;">
        <div style="display:flex; align-items:center; gap:1rem;">
            <div style="width:60px; height:60px; border-radius:50%; background:linear-gradient(135deg, #D4956F 0%, #C17F5A 100%); color:#FDFAF7; display:flex; align-items:center; justify-content:center; font-family:'DM Serif Display',serif; font-size:1.6rem;">
                {initial}
            </div>
            <div>
                <div style="font-family:'DM Serif Display',serif; font-size:1.55rem; color:#1C1917; line-height:1.1;">{name}</div>
                <div style="font-size:0.8rem; color:#9C8A7A; margin-top:0.25rem; letter-spacing:0.04em;">Wearly member · local prototype</div>
            </div>
        </div>
    </div>

    <div style="background:#FDFAF7; border:1px solid #E8E0D8; border-radius:6px; padding:1.4rem 1.6rem; margin-bottom:1.1rem;">
        <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.9rem;">Style profile</div>
        <div style="display:flex; flex-wrap:wrap; gap:1.4rem; row-gap:1rem;">
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Body shape</div>
                <div style="font-size:0.95rem; color:#1C1917;">{body.title() if body else '—'}</div>
            </div>
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Skin tone</div>
                <div style="font-size:0.95rem; color:#1C1917;">{skin.title() if skin else '—'}</div>
            </div>
            <div style="flex:1; min-width:140px;">
                <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.25rem;">Preferred fit</div>
                <div style="font-size:0.95rem; color:#1C1917;">{fit.title() if fit else '—'}</div>
            </div>
        </div>
        <div style="margin-top:1.2rem;">
            <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.5rem;">Style preferences</div>
            <div>{prefs_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="small")
    with c1:
        if st.button("Edit profile (coming soon)", key="profile_edit", disabled=True, use_container_width=True):
            pass
    with c2:
        if st.button("Sign in with Apple / Google (coming soon)", key="profile_signin", disabled=True, use_container_width=True):
            pass

    st.markdown("""
    <p style="font-size:0.74rem; color:#9C8A7A; line-height:1.55; margin-top:1rem;">
        <strong style="color:#7C6F64; letter-spacing:0.04em;">Privacy.</strong>
        Your profile data is stored locally in this prototype. Real authentication and cloud sync are future work.
    </p>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BEFORE / AFTER — comparison + live run
# ─────────────────────────────────────────────

def _render_demo():
    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Before &amp; After</div>
        <div style="font-size:0.86rem; color:#7C6F64; margin-top:0.3rem;">What changes when a styling agent reasons through your day.</div>
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
        with st.spinner("Running the agent live…"):
            st.session_state["result"] = run_agent(mode="calendar")
        st.rerun()

    if st.session_state.get("result"):
        st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.66rem; color:#A8937E; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin-bottom:0.6rem;">Live result</div>
        """, unsafe_allow_html=True)
        _render_outfit_result(st.session_state["result"])


# ─────────────────────────────────────────────
# SECTION ROUTER
# ─────────────────────────────────────────────

_router = {
    "home":     _render_home,
    "today":    _render_today,
    "wardrobe": _render_wardrobe,
    "profile":  _render_profile,
    "demo":     _render_demo,
}
_router.get(st.session_state["section"], _render_home)()
