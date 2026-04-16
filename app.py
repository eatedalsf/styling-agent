"""
app.py — Streamlit Web Interface for the AI Personal Styling Agent
Run with: streamlit run app.py
"""

import sys
import os
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.styling_agent import run_agent
from tools.calendar_tool import get_upcoming_events

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Style Agent",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
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
    background-color: #F5F0EB;
    color: #1C1917;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1C1917 !important;
    border-right: 1px solid #2E2A27;
}
[data-testid="stSidebar"] * {
    color: #F5F0EB !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p {
    color: #C9B99A !important;
    font-size: 0.82rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #2E2A27 !important;
    border: 1px solid #3D3835 !important;
    color: #F5F0EB !important;
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
.compare-after  { background: #F5F9F5; border-left: 3px solid #5A8C6A; }
.compare-label {
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.9rem;
}
.compare-before .compare-label { color: #8A7060; }
.compare-after  .compare-label { color: #3A6B4A; }
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
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 2px;
    background: #C17F5A;
    color: white;
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

/* Button override */
.stButton > button {
    background: #1C1917 !important;
    color: #F5F0EB !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.8rem !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background: #C17F5A !important;
}
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
    t = item.get("type", "").lower()
    if t in TYPE_EMOJI:
        return TYPE_EMOJI[t]
    if "shoe" in item.get("name", "").lower() or "boot" in item.get("name", "").lower() or "heel" in item.get("name", "").lower() or "sneaker" in item.get("name", "").lower():
        return "👠"
    if any(w in item.get("name","").lower() for w in ["earring","necklace","scarf","bag","tote","clutch"]):
        return "💍"
    return "✨"

def score_color(score):
    if score >= 80: return "#3A8C4A"
    if score >= 60: return "#C17F5A"
    return "#C05252"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 👗 Style Agent")
    st.markdown("---")

    mode = st.radio(
        "Mode",
        ["📅  Next Calendar Event", "✍️  Everyday Request", "📊  Before / After Demo"],
        index=0
    )

    everyday_input = ""
    if "Everyday" in mode:
        everyday_input = st.selectbox(
            "Occasion",
            ["Work", "Gym", "Dinner", "Formal Gala", "Weekend Brunch", "Casual Outing"]
        )

    st.markdown("---")
    run_btn = st.button("Get My Outfit →")

    st.markdown("---")
    st.markdown("""
    <p style="font-size:0.72rem; color:#6B5C52; line-height:1.7;">
    SEIS 666 — Spring 2026<br>
    Track B: Agentic AI System<br>
    4 tools · 7-step workflow<br>
    Weather-aware · Color-checked
    </p>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

st.markdown('<p class="main-title">Your Style,<br><em>Reasoned.</em></p>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">AI Personal Styling Agent — SEIS 666 Capstone</p>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BEFORE / AFTER PAGE
# ─────────────────────────────────────────────

if "Before" in mode and run_btn:
    st.markdown("---")
    st.markdown("### The Delta")

    col1, col2 = st.columns(2, gap="large")

    with col1:
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

    with col2:
        st.markdown("""
        <div class="compare-col compare-after">
            <div class="compare-label">After — Style Agent</div>
            <div class="compare-row"><span class="compare-key">Time to decide</span><span class="compare-val">~3 seconds</span></div>
            <div class="compare-row"><span class="compare-key">Weather check</span><span class="compare-val">Automatic (live API)</span></div>
            <div class="compare-row"><span class="compare-key">Color coordination</span><span class="compare-val">0–100 score</span></div>
            <div class="compare-row"><span class="compare-key">Calendar awareness</span><span class="compare-val">Automatic</span></div>
            <div class="compare-row"><span class="compare-key">Season awareness</span><span class="compare-val">Data-driven</span></div>
            <div class="compare-row"><span class="compare-key">Reasoning</span><span class="compare-val">Fully explained</span></div>
            <div class="compare-row"><span class="compare-key">Confidence</span><span class="compare-val">High (structured)</span></div>
            <div class="compare-row"><span class="compare-key">Coat reminder</span><span class="compare-val">Included ✓</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Now running a live recommendation so you can see the agent in action:**")
    with st.spinner("Running agent…"):
        result = run_agent(mode="calendar")
    # fall through to display below
    mode = "calendar_result"
    st.session_state["result"] = result


# ─────────────────────────────────────────────
# RUN AGENT
# ─────────────────────────────────────────────

result = None

if run_btn and "Before" not in mode:
    with st.spinner("Agent is working…"):
        if "Calendar" in mode:
            result = run_agent(mode="calendar")
        elif "Everyday" in mode:
            result = run_agent(mode="everyday", everyday_request=everyday_input)
    st.session_state["result"] = result

if "result" in st.session_state and st.session_state["result"]:
    result = st.session_state["result"]


# ─────────────────────────────────────────────
# DISPLAY RESULT
# ─────────────────────────────────────────────

if result:
    if result.get("error"):
        st.error(f"Agent Error: {result['error']}")
        st.stop()

    event   = result.get("event", {})
    weather = result.get("weather", {})
    outfit  = result.get("recommendation", [])
    steps   = result.get("steps", [])
    reasons = result.get("reasoning", [])
    gaps    = result.get("gaps", [])
    shopping = result.get("shopping_suggestions", [])
    color   = result.get("color_score", {})

    st.markdown("---")

    # ── Row 1: Event + Weather ──────────────────────────────
    col_event, col_weather = st.columns([1, 1], gap="large")

    with col_event:
        etype = event.get("type", "casual")
        emoji = OCCASION_EMOJI.get(etype, "📌")
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Occasion</div>
            <div class="event-type-badge">{emoji} {etype.upper()}</div>
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
            <div class="weather-advice">🧥 {adv}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Row 2: Outfit + Color Score ─────────────────────────
    col_outfit, col_score = st.columns([3, 2], gap="large")

    with col_outfit:
        items_html = ""
        for item in outfit:
            e = item_emoji(item)
            items_html += f"""
            <div class="outfit-item">
                <span style="font-size:1.1rem">{e}</span>
                <span style="font-weight:500">{item['name']}</span>
                <span class="item-color-chip">{item.get('color','')}</span>
            </div>"""

        st.markdown(f"""
        <div class="card">
            <div class="card-title">Your Outfit — {len(outfit)} pieces</div>
            {items_html if items_html else "<p style='color:#9C8A7A'>No items selected.</p>"}
        </div>
        """, unsafe_allow_html=True)

    with col_score:
        score_val = color.get("score", 0)
        flags     = color.get("flags", [])
        sc        = score_color(score_val)
        bar_pct   = score_val

        flags_html = ""
        for f in flags:
            flags_html += f"<div style='font-size:0.82rem;color:#8A4A20;padding:0.25rem 0;'>⚠ {f}</div>"

        st.markdown(f"""
        <div class="card">
            <div class="card-title">Color Harmony Score</div>
            <div style="font-family:'DM Serif Display',serif; font-size:2.8rem; color:{sc}; line-height:1;">
                {score_val}<span style="font-size:1.2rem; color:#9C8A7A">/100</span>
            </div>
            <div style="font-size:0.78rem;color:#9C8A7A;margin:0.3rem 0 0.4rem;">
                Skin tone: {result.get('event',{}).get('type','')} — warm olive
            </div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{bar_pct}%"></div>
            </div>
            {flags_html if flags_html else "<div style='font-size:0.83rem;color:#3A8C4A;margin-top:0.6rem;'>✓ All colors work well for your skin tone.</div>"}
        </div>
        """, unsafe_allow_html=True)

    # ── Gaps ────────────────────────────────────────────────
    if gaps:
        gap_items = "".join(f"<div class='gap-item'>→ {s}</div>" for s in shopping)
        st.markdown(f"""
        <div class="gap-alert">
            <div class="gap-title">🛍 Wardrobe Gap: {', '.join(gaps)} missing for this occasion</div>
            {gap_items}
        </div>
        """, unsafe_allow_html=True)

    # ── Workflow Steps ──────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    with st.expander("⚙️  Agent Workflow — 7 Steps", expanded=False):
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
    with st.expander("💡  Full Agent Reasoning & Explainability", expanded=False):
        r_html = ""
        for i, r in enumerate([x for x in reasons if x.strip()], 1):
            r_html += f'<div class="reason-item"><span class="reason-num">{i}</span><span>{r}</span></div>'
        st.markdown(f'<div class="card" style="margin-top:0">{r_html}</div>', unsafe_allow_html=True)

elif not run_btn:
    # Landing state
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color: #9C8A7A;">
        <div style="font-size:3rem; margin-bottom:1rem;">👗</div>
        <div style="font-family:'DM Serif Display',serif; font-size:1.5rem; color:#4A3D36; margin-bottom:0.5rem;">
            Ready when you are.
        </div>
        <div style="font-size:0.9rem;">
            Choose a mode in the sidebar and click <strong>Get My Outfit →</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
