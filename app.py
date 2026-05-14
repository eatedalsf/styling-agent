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
# AUTO-RELOAD STALE PROJECT MODULES
# ─────────────────────────────────────────────
#
# Streamlit reruns the script on every interaction but it does NOT
# clear sys.modules — so any project module imported by an earlier
# rerun stays cached for the life of the Streamlit process. When the
# user pulls new code and Streamlit's file-watcher reruns the
# script, the imports return the OLD module objects: stale defaults,
# stale function bodies, even stale class definitions.
#
# THE FIRST-RUN BLINDSPOT (fixed below):
#
# A naive implementation that compares the on-disk mtime against a
# remembered "last seen" mtime cannot tell the difference between
# "the file changed two minutes ago, before I started watching" and
# "the file hasn't changed since I started watching." The MODULE in
# sys.modules could still be stale relative to the file. So on the
# very first observation we now compare the file mtime against the
# CURRENT PROCESS START TIME (psutil-free, via the file's mtime vs.
# a per-process sentinel). If the file is newer than the process
# itself, the module IS stale and gets reloaded. After that, we
# do the cheap mtime-compare for future edits.
#
# Cache survives across Streamlit reruns by being stashed on the
# `sys` module itself (which Streamlit never clears).

_VOLATILE_MODULES = (
    "calendar_tool",
    "calendar_import",
    "styling_agent",
    "wardrobe_tool",
    "weather_tool",
    "color_tool",
    "fit_tool",
    "history_tool",
    "shopping_tool",
    "routine_tool",
    "graph_tool",
    "rule_refs",
    "wardrobe_query",
    "compact_kg",
    "link_import",
    "backup_tool",
)

# Stash a single sentinel on the sys module — this survives across
# Streamlit reruns (sys is process-global, never re-imported).
_RELOADER_KEY = "_wearly_module_reloader"
if not hasattr(sys, _RELOADER_KEY):
    # Track when THIS auto-reloader code first started watching, so
    # we can identify modules that were imported with stale code
    # BEFORE we existed.
    import time as _t
    setattr(sys, _RELOADER_KEY, {
        "started_at":   _t.time(),   # epoch when reloader first ran
        "seen_mtimes":  {},          # module-name -> last observed mtime
        "first_pass":   True,        # True for the very first invocation
    })

_RELOADER_STATE: dict = getattr(sys, _RELOADER_KEY)


def _reload_volatile_modules() -> None:
    """
    Reload any locally-authored module whose .py mtime suggests the
    module object in sys.modules is stale.

    On the FIRST invocation in a Streamlit process, every volatile
    module whose .py file was modified before the reloader started
    is force-reloaded. (This catches the typical case: a long-
    running Streamlit that pre-dates a git pull.) After the first
    invocation, modules are only reloaded when their file mtime
    increases. Reload failures are swallowed so a half-saved file
    can never crash the app.
    """
    import importlib
    state = _RELOADER_STATE
    seen = state["seen_mtimes"]
    first_pass = state["first_pass"]
    started_at = state["started_at"]

    for name in _VOLATILE_MODULES:
        mod = sys.modules.get(name)
        if mod is None or not getattr(mod, "__file__", None):
            continue
        try:
            current_mtime = os.path.getmtime(mod.__file__)
        except OSError:
            continue

        should_reload = False
        if first_pass:
            # The MODULE was imported by Streamlit's startup. If the
            # FILE has been modified since the reloader itself first
            # ran, then sys.modules is definitely behind the file
            # contents — reload.
            #
            # We use the reloader's start_at instead of the module
            # file's "true import time" because Python doesn't track
            # per-module import time, and using a slightly-too-late
            # reference point here is safe: a file that was modified
            # in the interval between "Streamlit start" and "reloader
            # first ran" was definitely loaded with stale code.
            #
            # In practice the reloader runs within microseconds of
            # Streamlit picking up the new app.py, so this trigger
            # captures the typical "git pull during Streamlit"
            # scenario.
            should_reload = True   # force on first pass
        else:
            last = seen.get(name)
            if last is not None and current_mtime > last:
                should_reload = True

        if should_reload:
            try:
                importlib.reload(mod)
            except Exception:
                # Reload failed (circular import mid-edit, syntax
                # error in the new file, etc.). Keep the cached
                # version rather than crashing the app.
                pass
        seen[name] = current_mtime

    if first_pass:
        state["first_pass"] = False


_reload_volatile_modules()


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

/* Force Latin (Western Arabic) numerals on number inputs. If the user's
   browser or system locale is set to Arabic, the default font fallback
   stack will render <input type="number"> values like "0.00" as
   "٠٫٠٠" (Arabic-Indic digits). Force LTR direction, isolate the
   bidi run, prefer DM Sans / system Latin fonts, and explicitly request
   lining numerals via OpenType features. */
input[type="number"],
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input {
    direction: ltr !important;
    unicode-bidi: isolate !important;
    text-align: left !important;
    font-family: 'DM Sans', 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
    font-feature-settings: "lnum" 1, "tnum" 1 !important;
    font-variant-numeric: lining-nums tabular-nums !important;
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
    /* Keep button labels on a single line. Two-word actions like
       "Re-sync calendar" otherwise wrap into two lines at narrow
       column widths, which looks broken. */
    white-space: nowrap !important;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease !important;
}
/* Labels inside the button (Streamlit wraps the text in a <p>) also
   need the nowrap so the wrap doesn't happen one layer deeper. */
.stButton > button p,
.stButton > button div {
    white-space: nowrap !important;
}
.stButton > button:hover {
    background: #F5F5F5 !important;
    border-color: #111111 !important;
    color: #111111 !important;
}
/* Primary button — Alta-style CTA, solid matte black with white text.
   Split into two scoped rules so the *shape* matches the context:
     - st.button (regular buttons, including the active nav pill):
       keeps the SAME pill geometry as inactive buttons. Only the color
       flips, never the size or radius. This is what makes the nav row
       feel like a single coherent set with one item highlighted.
     - st.form_submit_button (Save Profile, Save to wardrobe, etc.):
       rectangular CTA, larger touch target. */
[data-testid="stButton"] > button[kind="primary"] {
    background: #111111 !important;
    color: #FFFFFF !important;
    border: 1px solid #111111 !important;
    border-radius: 99px !important;
    font-size: 0.84rem !important;
    padding: 0.5rem 0.85rem !important;
    font-weight: 500 !important;
    min-height: 48px !important;
    box-shadow: none !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #2E2E2E !important;
    border-color: #2E2E2E !important;
    color: #FFFFFF !important;
}
[data-testid="stButton"] > button[kind="primary"]:active {
    transform: translateY(1px) !important;
}

/* Form-submit primary — rectangular CTA. */
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: #111111 !important;
    color: #FFFFFF !important;
    border: 1px solid #111111 !important;
    border-radius: 6px !important;
    font-size: 0.95rem !important;
    padding: 0.82rem 1.6rem !important;
    box-shadow: none !important;
}
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
    background: #2E2E2E !important;
    border-color: #2E2E2E !important;
    color: #FFFFFF !important;
}
[data-testid="stFormSubmitButton"] > button[kind="primary"]:active {
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

def _format_time_12h(time_str: str) -> str:
    """
    Render a calendar event's "HH:MM" or "H:MM AM/PM" string in
    user-friendly 12-hour format. Returns "" on empty / unparseable
    input (so the caller can safely concatenate without showing junk).

    Accepted inputs:
      "18:00"      -> "6:00 PM"
      "09:05"      -> "9:05 AM"
      "00:30"      -> "12:30 AM"
      "12:00"      -> "12:00 PM"
      "8:00 AM"    -> "8:00 AM" (already 12-hour, passed through)
      ""           -> ""
      "all-day"    -> "all-day"
    """
    s = (time_str or "").strip()
    if not s:
        return ""
    # Already 12-hour? Pass through (covers manually-entered seed events
    # like "10:00 AM" in seed_calendar_events.json).
    upper = s.upper()
    if upper.endswith(" AM") or upper.endswith(" PM"):
        return s
    # Non-numeric tokens ("all-day") — return verbatim.
    if ":" not in s:
        return s
    try:
        hh_str, mm_str = s.split(":", 1)
        hh = int(hh_str)
        mm = int(mm_str[:2])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            return s
    except (ValueError, IndexError):
        return s
    suffix = "AM" if hh < 12 else "PM"
    hh12 = hh % 12
    if hh12 == 0:
        hh12 = 12
    return f"{hh12}:{mm:02d} {suffix}"


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
if _qp in {"home", "today", "planner", "wardrobe", "shop", "profile", "demo"}:
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


def _auto_refresh_subscription_if_needed(max_age_seconds: int = 300) -> None:
    """
    If the user has a calendar URL subscription and it hasn't been
    synced in the last `max_age_seconds`, refresh it silently before
    the agent runs. Best-effort — any failure is logged to a session
    flag but never blocks the agent. The cached events from the last
    successful sync are used as a fall-back.
    """
    try:
        from calendar_import import get_subscription, refresh_subscription
        from datetime import datetime, timedelta
    except Exception:
        return

    sub = get_subscription()
    if not sub.get("url"):
        return

    last = sub.get("last_synced_at")
    needs_refresh = True
    if last:
        try:
            # last_synced_at is ISO-8601 with a trailing "Z"
            ts = datetime.fromisoformat(last.replace("Z", ""))
            needs_refresh = (datetime.utcnow() - ts) > timedelta(seconds=max_age_seconds)
        except Exception:
            needs_refresh = True

    if not needs_refresh:
        return

    try:
        # Mirror mode: pick up deletions in the source calendar
        # automatically. See refresh_subscription docstring.
        res = refresh_subscription(replace=True, timeout=8)
        st.session_state["_cal_auto_refresh_result"] = res
    except Exception as _e:
        st.session_state["_cal_auto_refresh_result"] = {
            "success": False, "error": f"Auto-refresh failed: {_e}",
        }


def _run_and_store(mode: str, everyday_request: str = None,
                   rejected_ids=None, rejection_reasons=None,
                   todays_context: str = None,
                   target_event_id: str = None,
                   source: str = "today") -> dict:
    """Wrapper: runs the agent, stores result + the invocation params so
    a later 'Regenerate' can replay the same mode with rejection context.

    `target_event_id` — when supplied, the agent pulls THAT specific
    calendar event instead of the chronologically-next one. This is
    how a Planner "Plan in detail" click preserves which event it's
    planning for, even across Replan/Regenerate.

    `source` — "today" | "planner" | "everyday". Stamps the result
    so the renderer can pick the right page title ("Today's outfit"
    vs "Outfit for <event>") and so derived surfaces (compact KG
    export, reasoning header) know which context to use.

    Auto-refreshes the calendar subscription (if any) before the run.
    todays_context is a free-text "what's going on right now" field
    — a pattern borrowed from a classmate's dream-journal project."""
    _auto_refresh_subscription_if_needed()

    ctx = todays_context if todays_context is not None else st.session_state.get("todays_context", "")
    res = run_agent(
        mode=mode,
        everyday_request=everyday_request,
        rejected_ids=rejected_ids,
        rejection_reasons=rejection_reasons,
        todays_context=ctx,
        target_event_id=target_event_id,
    )
    # Stamp the source so the renderer can branch on it without
    # re-deriving from event dates.
    if isinstance(res, dict):
        res["source"] = source
        if target_event_id:
            res["target_event_id"] = target_event_id
    st.session_state["result"] = res
    st.session_state["last_run"] = {
        "mode":              mode,
        "everyday_request":  everyday_request,
        "todays_context":    ctx,
        "target_event_id":   target_event_id,
        "source":            source,
    }
    return res


def _render_user_items_list(items: list) -> None:
    """
    Render the user's saved wardrobe items with per-item Edit + Delete
    controls. The Edit button opens an inline form in an expander
    pre-filled with the item's current values; saving calls
    `update_user_item()`. Delete removes the item via
    `delete_user_item()` and reruns to reflect the change.

    Seed wardrobe items are NEVER editable — only items in the user
    overlay (id starts with "U") reach this function.
    """
    try:
        from wardrobe_tool import update_user_item, delete_user_item
    except Exception as _e:
        st.error(f"Edit/delete unavailable: {_e}")
        return

    # Same constraints used by the Add forms — keep the dropdowns aligned.
    _CAT_OPTIONS = ["top", "bottom", "dress", "outerwear",
                    "activewear", "shoes", "accessory"]
    _FORM_OPTIONS = ["casual", "smart_casual", "business", "formal", "athletic"]
    _SEAS_OPTIONS = ["all", "spring", "summer", "fall", "winter"]
    _TAG_OPTIONS  = ["work", "gym", "dinner", "formal",
                     "casual", "weekend", "date", "travel"]

    for it in items:
        item_id = it.get("id", "—")
        swatch = color_to_swatch(it.get("color", ""))

        # Image — preserve the same priority order as elsewhere:
        # local image_path → remote source_image_url → none.
        thumb_html = ""
        ipath = it.get("image_path")
        src_image = it.get("source_image_url")
        if ipath:
            data_uri = _image_to_data_uri(ipath)
            if data_uri:
                thumb_html = (
                    f'<img src="{data_uri}" alt="" '
                    f'style="width:72px; height:72px; object-fit:cover; '
                    f'border-radius:4px; border:1px solid #E5E5E5; flex-shrink:0;" '
                    f'onerror="this.style.display=\'none\'">'
                )
        if not thumb_html and src_image:
            thumb_html = (
                f'<img src="{src_image}" alt="" '
                f'style="width:72px; height:72px; object-fit:cover; '
                f'border-radius:4px; border:1px solid #E5E5E5; flex-shrink:0;" '
                f'onerror="this.style.display=\'none\'">'
            )
        if not thumb_html:
            # Calm "no image" placeholder so the row alignment stays clean.
            thumb_html = (
                '<div style="width:72px; height:72px; background:#FAFAFA; '
                'border:1px dashed #E5E5E5; border-radius:4px; flex-shrink:0; '
                'display:flex; align-items:center; justify-content:center; '
                'font-size:0.7rem; color:#8E8E93;">img</div>'
            )

        # Pexels attribution — required by their API guidelines when
        # we display a real photographer's work. Rendered as a tiny
        # caption line at the bottom of the row.
        credit_html = ""
        cr_name = it.get("photo_credit_name")
        cr_url  = it.get("photo_credit_url")
        cr_src  = it.get("photo_credit_source") or "Pexels"
        if cr_name:
            if cr_url:
                credit_html = (
                    f'<div style="font-size:0.66rem; color:#8E8E93; '
                    f'margin-top:0.25rem; margin-left:84px;">Photo: '
                    f'<a href="{cr_url}" target="_blank" '
                    f'style="color:#8E8E93; text-decoration:none;">'
                    f'{cr_name}</a> · {cr_src}</div>'
                )
            else:
                credit_html = (
                    f'<div style="font-size:0.66rem; color:#8E8E93; '
                    f'margin-top:0.25rem; margin-left:84px;">'
                    f'Photo: {cr_name} · {cr_src}</div>'
                )

        # Row container — markdown for the visual, Streamlit columns for buttons.
        st.markdown(
            f'<div style="background:#FFFFFF; border:1px solid #E5E5E5; '
            f'border-radius:6px; padding:0.7rem 1rem; margin-bottom:0.6rem;">'
            f'<div style="display:flex; align-items:center; gap:0.7rem;">'
            f'{thumb_html}'
            f'<span class="item-swatch" style="background:{swatch}"></span>'
            f'<span style="font-weight:500; color:#1C1917;">{it.get("name","—")}</span>'
            f'<span style="font-size:0.74rem; color:#6E6E73; margin-left:auto; text-align:right;">'
            f'{it.get("type","—")} · {it.get("formality","—")}'
            f'</span>'
            f'</div>'
            f'{credit_html}'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Action row — two buttons under each item card.
        col_e, col_d, col_pad = st.columns([1, 1, 6], gap="small")
        with col_e:
            edit_open = st.toggle(
                "Edit", key=f"item_edit_toggle_{item_id}", value=False,
            )
        with col_d:
            if st.button("Delete", key=f"item_delete_{item_id}",
                         use_container_width=True):
                res = delete_user_item(item_id)
                if res.get("success"):
                    st.toast(f"Removed {it.get('name','item')}.")
                    st.rerun()
                else:
                    st.error(f"Could not delete: {res.get('error','unknown error')}")

        # Inline editor — only renders when the toggle is on for THIS item.
        if edit_open:
            with st.form(f"item_edit_form_{item_id}", clear_on_submit=False):
                col_a, col_b = st.columns(2, gap="small")
                with col_a:
                    e_name = st.text_input(
                        "Name", value=it.get("name", ""),
                        key=f"e_name_{item_id}",
                    )
                    cur_cat = it.get("type", "top")
                    e_cat = st.selectbox(
                        "Category",
                        options=_CAT_OPTIONS,
                        index=_CAT_OPTIONS.index(cur_cat) if cur_cat in _CAT_OPTIONS else 0,
                        key=f"e_cat_{item_id}",
                    )
                    cur_form = it.get("formality", "casual")
                    e_form = st.selectbox(
                        "Formality",
                        options=_FORM_OPTIONS,
                        index=_FORM_OPTIONS.index(cur_form) if cur_form in _FORM_OPTIONS else 0,
                        key=f"e_form_{item_id}",
                    )
                with col_b:
                    e_color = st.text_input(
                        "Color", value=it.get("color", ""),
                        key=f"e_color_{item_id}",
                    )
                    e_seasons = st.multiselect(
                        "Seasons",
                        options=_SEAS_OPTIONS,
                        default=[s for s in (it.get("season") or []) if s in _SEAS_OPTIONS] or ["all"],
                        key=f"e_seas_{item_id}",
                    )
                    e_tags = st.multiselect(
                        "Occasion tags",
                        options=_TAG_OPTIONS,
                        default=[t for t in (it.get("tags") or []) if t in _TAG_OPTIONS],
                        key=f"e_tags_{item_id}",
                    )

                # Replace the photo? Optional file uploader.
                e_new_image = st.file_uploader(
                    "Replace the photo (optional)",
                    type=["png", "jpg", "jpeg", "webp"],
                    key=f"e_img_{item_id}",
                    label_visibility="visible",
                )

                e_url = st.text_input(
                    "Image URL (optional)",
                    value=it.get("source_image_url", ""),
                    key=f"e_image_url_{item_id}",
                    placeholder="Paste a product image URL — overrides the uploaded photo.",
                )

                save_edit = st.form_submit_button(
                    "Save changes", type="primary", use_container_width=True,
                )
                if save_edit:
                    img_bytes = e_new_image.read() if e_new_image else None
                    link_meta = None
                    cleaned_url = (e_url or "").strip()
                    if cleaned_url != (it.get("source_image_url") or ""):
                        link_meta = {
                            "source_url":       it.get("source_url"),
                            "source_store":     it.get("source_store"),
                            "source_image_url": cleaned_url or None,
                        }
                    res = update_user_item(
                        item_id=item_id,
                        item_fields={
                            "name":      e_name,
                            "color":     e_color,
                            "type":      e_cat,
                            "formality": e_form,
                            "season":    e_seasons or ["all"],
                            "tags":      e_tags,
                        },
                        image_bytes=img_bytes,
                        link_metadata=link_meta,
                    )
                    if res.get("success"):
                        st.toast(f"Updated {res['item'].get('name','item')}.")
                        # Collapse the editor and refresh.
                        st.session_state.pop(f"item_edit_toggle_{item_id}", None)
                        st.rerun()
                    else:
                        st.error(f"Could not save: {res.get('error','unknown error')}")


def _measurement_diagram_svg() -> str:
    """
    Clear, body-positive HTML legend explaining what each measurement
    field means and how to take it. Returned as a single-line HTML
    string with NO leading whitespace per line, so Streamlit's markdown
    renderer doesn't interpret indented lines as a code block (which
    would break inline HTML).

    A link to the original Sewing Revival measurement diagram is
    included for users who want the visual reference — we don't embed
    the published image directly (copyright).
    """
    # Single-row HTML string; no leading whitespace inside the value.
    return (
        '<div style="background:#FFFFFF; border:1px solid #EEEEEE; '
        'border-radius:6px; padding:1rem 1.1rem; margin:0.4rem 0;">'
        '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; '
        'text-transform:uppercase; font-weight:600; margin-bottom:0.7rem;">'
        'What each field measures'
        '</div>'
        '<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); '
        'gap:0.6rem 1.4rem; font-family:DM Sans,sans-serif; font-size:0.86rem; '
        'color:#2E2E2E; line-height:1.55;">'
        '<div><strong>Height</strong> — floor to top of head, in bare feet.</div>'
        '<div><strong>Bust</strong> — around the back, under the arms and across the fullest part of the bust. Tape flat, not too tight.</div>'
        '<div><strong>Natural waist</strong> — narrowest part of the torso, usually just above the navel. Tape flat, snug but not tight.</div>'
        '<div><strong>Hips</strong> — fullest part of the hips and seat, about 21–23 cm / 8–9 in below the waist.</div>'
        '<div><strong>High hips</strong> — about 8 cm / 3 in below the waist, where a low-rise waistband sits.</div>'
        '<div><strong>Back waist length</strong> — nape (bony bump at the base of the neck) down the spine to the natural waist.</div>'
        '<div><strong>Front waist length</strong> — hollow above the collarbone, down the front to the natural waist.</div>'
        '<div><strong>Inseam</strong> — inner thigh down to where pants should break (usually the ankle bone).</div>'
        '<div><strong>Sleeve length</strong> — shoulder bone to wristbone with a slight elbow bend.</div>'
        '<div><strong>3/4 trouser length</strong> — outside of the leg from the waist to mid-calf.</div>'
        '<div><strong>Full trouser length</strong> — outside of the leg from the waist to the ankle.</div>'
        '<div><strong>Shoulder width</strong> — across the back, shoulder bone to shoulder bone.</div>'
        '<div><strong>Neck</strong> — base of the neck where a shirt collar would sit, with one finger of slack.</div>'
        '</div>'
        '<div style="margin-top:0.9rem; padding-top:0.8rem; border-top:1px solid #EEEEEE; '
        'font-size:0.78rem; color:#6E6E73; line-height:1.55;">'
        'For a visual reference, see the '
        '<a href="https://thesewingrevival.com/pages/choosing-your-size" target="_blank" '
        'style="color:#111111;">Sewing Revival measurement diagram</a>'
        ' — the source for our bust / waist / hips wording.'
        '</div>'
        '</div>'
    )


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
    # Wordmark only — the "Prototype" tag was removed.
    st.markdown(f"""
    <div class="brand">
        <span class="brand-mark">W</span>
        <span class="brand-wordmark">Wearly</span>
    </div>
    """, unsafe_allow_html=True)

with _bar_right:
    # The popover's trigger button is the only popover in the whole app,
    # so we style it via the global [data-testid="stPopover"] selector.
    # Dropdown contents are intentionally minimal — items that already
    # live in the main nav (Profile, Wardrobe, Before/After) are NOT
    # duplicated here. Only items unique to a user-menu surface remain:
    # the local-account status note, a backup shortcut (a Wardrobe
    # sub-feature), and Sign out.
    with st.popover(
        f"Hi, {_name}",
        use_container_width=True,
        help="Wearly has no accounts — your data stays local on this device.",
    ):
        st.markdown(
            "<div class='profile-menu-sub' style='padding:0.5rem 0.6rem 0.4rem;'>"
            "Signed in locally · no cloud account"
            "</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Navigation entries that used to live in the main nav row but
        # were moved here to keep the top of the screen reserved for the
        # four daily-use destinations (Home, Today, Wardrobe, Shop).
        if st.button("Profile", key="menu_profile_btn", use_container_width=True):
            _goto("profile")
        if st.button("Before / after demo", key="menu_demo_btn", use_container_width=True):
            _goto("demo")

        st.divider()

        if st.button("Backup & restore", key="menu_backup_btn", use_container_width=True):
            # Routes to the Wardrobe screen where the Backup expander
            # lives at the top — Backup is a Wardrobe sub-feature, so
            # there's no other place to surface it as a top-level link.
            _goto("wardrobe")
        if st.button("Sign out", key="menu_signout_btn", use_container_width=True):
            _sign_out()

        st.markdown(
            "<div class='profile-menu-footnote'>"
            "Signing out clears your fit profile but keeps your wardrobe "
            "and wear history."
            "</div>",
            unsafe_allow_html=True,
        )

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
    ("planner",  "Planner"),
    ("routine",  "Routine"),
    ("wardrobe", "Wardrobe"),
    ("shop",     "Shop"),
    # Profile and Before / After were moved out of the top nav into
    # the user dropdown menu — see the popover block above. The top
    # nav is reserved for the daily-use destinations.
    #
    # Planner   = actual calendar events (week / month / all upcoming).
    # Routine   = recurring weekly rhythm fallback (no calendar needed).
    # Today     = the current recommendation, whatever its source.
]
_active = st.session_state["section"]

# Sub-routes that should still highlight their originating top-nav
# pill. event_detail is reached from Planner or Routine "Plan in
# detail" clicks; the originating tab stays lit so the user always
# knows where they are.
if _active == "event_detail":
    _src = (st.session_state.get("result") or {}).get("source", "")
    _nav_active = "routine" if str(_src).lower() == "routine" else "planner"
else:
    _nav_active = _active

_nav_cols = st.columns(len(_SECTIONS), gap="small")
for _col, (_key, _label) in zip(_nav_cols, _SECTIONS):
    with _col:
        _btn_type = "primary" if _key == _nav_active else "secondary"
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
                {event.get('date','Today')} &nbsp;·&nbsp; {_format_time_12h(event.get('time',''))}
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
        # Items render with real thumbnails (image_path / source_image_url
        # / clean placeholder) so the card shows what was picked, not
        # just a row of names. Centralized in _item_thumbnail_html.
        item_rows = []
        for item in outfit:
            swatch_hex = color_to_swatch(item.get("color", ""))
            thumb = _item_thumbnail_html(item, size_px=48)
            row = (
                '<div class="outfit-item" style="gap:0.85rem;">'
                + thumb +
                '<div style="display:flex; flex-direction:column; line-height:1.3; flex:1; min-width:0;">'
                  '<span style="font-weight:500; color:#1C1917; '
                  'overflow:hidden; text-overflow:ellipsis;">'
                  + item.get("name", "—") +
                  '</span>'
                  '<span style="font-size:0.74rem; color:#6E6E73; margin-top:0.15rem;">'
                  + (item.get("type", "—") or "—") +
                  '</span>'
                '</div>'
                '<span class="item-swatch" style="background:' + swatch_hex + ';"></span>'
                '<span class="item-color-chip">' + (item.get("color", "") or "—") + '</span>'
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

    # ── Reasoning (story-style, grouped, citation pills) ─────
    # The flat numbered list felt like a debug log. This version groups
    # reasoning lines by which step they came from (Selected, Color,
    # Note, Skipping, etc.) and renders rule citations as small pills
    # rather than inline brackets — same data, much more readable.
    with st.expander("Why this outfit — the agent's reasoning",
                     expanded=False):
        _render_reasoning_story(reasons)

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
                # Explicit legend (Dan-McCreary-style review answer):
                # library, layout, node-size meaning, color meaning,
                # edge-label meaning, what to read out of the graph.
                try:
                    from graph_tool import legend_for_app as _legend
                    with st.expander("What does this graph mean? (legend)",
                                     expanded=False):
                        st.markdown(_legend(), unsafe_allow_html=True)
                except Exception:
                    pass
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

            last = st.session_state.get(
                "last_run",
                {"mode": "calendar", "everyday_request": None,
                 "target_event_id": None, "source": "today"},
            )
            with st.spinner("Re-reading your context · applying your feedback…"):
                # Preserve target_event_id + source so reject-and-
                # regenerate on a Planner-sourced result still plans
                # for the SAME future event, with the SAME page title.
                _run_and_store(
                    mode=last.get("mode", "calendar"),
                    everyday_request=last.get("everyday_request"),
                    rejected_ids=st.session_state["rejected_ids"],
                    rejection_reasons=st.session_state["rejection_reasons"],
                    target_event_id=last.get("target_event_id"),
                    source=last.get("source") or "today",
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
    # If the user has a URL subscription and it hasn't synced in the
    # last 5 minutes, mirror it now so the "Next event" card reflects
    # what's actually in their calendar — not a snapshot from before
    # they deleted something. Bust the @st.cache_data cache afterwards
    # so the next call to _load_home_context() reads the fresh file.
    _stale_marker_before = st.session_state.get("_cal_auto_refresh_result")
    _auto_refresh_subscription_if_needed()
    if st.session_state.get("_cal_auto_refresh_result") is not _stale_marker_before:
        try:
            _load_home_context.clear()
        except Exception:
            pass
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
            ev_meta_parts.append(_format_time_12h(next_event["time"]))
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

    # Non-empty placeholder when there are no notes — keeps the line
    # in the f-string below from collapsing to pure whitespace, which
    # markdown would otherwise parse as a paragraph break and then
    # render the subsequent indented HTML as a code block.
    notes_html = (
        f'<div style="font-size:0.8rem; color:#6E6E73; margin-top:0.3rem; font-style:italic; line-height:1.5;">{ev_notes}</div>'
        if ev_notes else "<span></span>"
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

_REASONING_CITATION_RE = __import__("re").compile(r"\[([a-z-]+#R\d+)\]")


def _render_reasoning_story(lines: list) -> None:
    """
    Render the reasoning trail as a clean, grouped, story-style panel.

    Groups by the first word of each line (Selected / Added / Skipping /
    Note / etc.) so closely-related decisions cluster together. Rule
    citations like `[occasion-rules#R3]` are extracted from the prose
    and surfaced as small pills below the sentence — so the citation
    is still visible but no longer interrupts the reading rhythm.

    Goal 9 improvements:
      - New "Taste" section recognises the wishlist-derived taste
        narrative ("Your wishlist suggests …").
      - New "Rotation" section recognises cross-event rotation notes
        ("Rotation: avoiding …").
      - A short story-level summary card at the very top — a single
        body-positive sentence answering "why this outfit?" — built
        deterministically from the picked pieces in the trail.
    """
    raw_lines = [(ln or "").strip() for ln in (lines or []) if (ln or "").strip()]
    if not raw_lines:
        st.markdown(
            "<div style='font-size:0.86rem; color:#6E6E73;'>"
            "No reasoning recorded for this run.</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Top-of-panel TL;DR — "Why this outfit?" ──
    # Build a single sentence by mining the trail for picks (Selected
    # / Added) and stating the dominant reason class. This gives the
    # user a body-positive headline before they scroll the details.
    picks: list = []
    has_color_note = False
    has_fit_note   = False
    has_wishlist   = False
    has_rotation   = False
    for ln in raw_lines:
        low = ln.lower().lstrip()
        if low.startswith(("selected", "added")):
            # pull the quoted item name
            import re as _re
            m = _re.search(r"['\"]([^'\"]+)['\"]", ln)
            if m and m.group(1) not in picks:
                picks.append(m.group(1))
        if low.startswith("complements your"):
            has_color_note = True
        if low.startswith(("aligns with", "matches your", "supports your",
                           "respects your")):
            has_fit_note = True
        if low.startswith("your wishlist"):
            has_wishlist = True
        if low.startswith("rotation:"):
            has_rotation = True
    if picks:
        head = ", ".join(picks[:3])
        why_bits: list = []
        if has_fit_note:    why_bits.append("aligned with your fit profile")
        if has_color_note:  why_bits.append("color-harmony for your skin tone")
        if has_wishlist:    why_bits.append("in the direction your wishlist points")
        if has_rotation:    why_bits.append("rotated from yesterday's outfit")
        why_clause = (
            ", ".join(why_bits[:-1]) + (
                ", and " + why_bits[-1] if len(why_bits) > 1 else
                why_bits[-1] if why_bits else ""
            )
        ) if why_bits else "based on your wardrobe, occasion, and weather"
        st.markdown(
            "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
            "border-radius:8px; padding:0.9rem 1.1rem; margin-bottom:0.8rem;'>"
            "<div style='font-size:0.66rem; color:#8E8E93; "
            "letter-spacing:0.14em; text-transform:uppercase; "
            "font-weight:600; margin-bottom:0.25rem;'>Why this outfit</div>"
            "<div style='font-size:0.92rem; color:#1C1917; line-height:1.55;'>"
            f"Built around <strong>{head}</strong>"
            + (" and others" if len(picks) > 3 else "")
            + f", {why_clause}.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    # Group classification — used to pick the section header + icon.
    def _classify(line: str) -> tuple:
        low = line.lower().lstrip()
        if low.startswith("today's context"):
            return ("Context",   "Your context for today")
        if low.startswith("your wishlist"):
            return ("Taste",     "What your wishlist suggests")
        if low.startswith("rotation:"):
            return ("Rotation",  "Avoiding repeats from nearby events")
        if low.startswith("skipping"):
            return ("Excluded",  "Items you ruled out")
        if low.startswith(("selected", "added", "chose")):
            return ("Pieces",    "What Wearly picked, and why")
        if low.startswith("note:"):
            return ("Notes",     "Heads-up notes")
        if line.startswith("✓") or line.startswith("⚠"):
            return ("Color",     "Color-harmony check")
        if "missing" in low or "shopping suggestion" in low:
            return ("Gaps",      "What's missing, and what to add")
        if low.startswith("warm") or low.startswith("cool") or low.startswith("bold"):
            return ("Palette",   "Palette notes")
        return ("Other", "Other reasoning")

    # Order sections deliberately — context + taste first (they FRAME
    # the rest), then picks, excluded, color, palette, notes, gaps,
    # rotation, and the catch-all "Other" trails at the end.
    section_order = [
        "Context", "Taste",
        "Pieces", "Excluded",
        "Color", "Palette",
        "Notes", "Gaps", "Rotation", "Other",
    ]
    grouped: dict = {k: [] for k in section_order}
    for line in raw_lines:
        sec, _ = _classify(line)
        grouped[sec].append(line)

    # Section subtitle lookup (used in header).
    subtitle_for = {
        "Context":  "Your context for today",
        "Taste":    "What your wishlist suggests",
        "Pieces":   "What Wearly picked, and why",
        "Excluded": "Items you ruled out",
        "Color":    "Color-harmony check",
        "Palette":  "Palette notes",
        "Notes":    "Heads-up notes",
        "Gaps":     "What's missing, and what to add",
        "Rotation": "Avoiding repeats from nearby events",
        "Other":    "Other reasoning",
    }

    for section in section_order:
        bucket = grouped.get(section) or []
        if not bucket:
            continue

        # Section header card.
        st.markdown(
            "<div style='margin-top:0.9rem; margin-bottom:0.4rem;'>"
            "<div style='font-size:0.66rem; color:#8E8E93; "
            "letter-spacing:0.14em; text-transform:uppercase; font-weight:600;'>"
            f"{section}</div>"
            f"<div style='font-size:0.78rem; color:#6E6E73; margin-top:0.15rem;'>"
            f"{subtitle_for[section]}</div></div>",
            unsafe_allow_html=True,
        )

        for line in bucket:
            # Split out any rule citations into pills shown below the line.
            tags = _REASONING_CITATION_RE.findall(line)
            clean = _REASONING_CITATION_RE.sub("", line).strip().rstrip(".")
            pills_html = ""
            if tags:
                pills_html = "".join(
                    f'<span style="font-size:0.66rem; color:#111111; '
                    f'background:#FAFAFA; border:1px solid #EEEEEE; '
                    f'padding:1px 9px; border-radius:99px; margin-right:0.35rem; '
                    f'letter-spacing:0.04em; font-family:DM Mono, monospace;">'
                    f'{t}</span>'
                    for t in tags
                )

            # Sub-note indentation: lines that start with two spaces are
            # secondary detail (e.g. "  Aligns with your preferred tailored fit").
            is_subnote = line.startswith("  ") or line.startswith("\t")
            row_style = ("padding:0.45rem 0 0.5rem 1.2rem; border-left:2px solid "
                         "#EEEEEE; margin-left:0.4rem;"
                         if is_subnote else
                         "padding:0.5rem 0;")
            text_color = "#6E6E73" if is_subnote else "#1C1917"

            st.markdown(
                f"<div style='{row_style}'>"
                f"<div style='font-size:0.9rem; color:{text_color}; line-height:1.55;'>"
                f"{clean}.</div>"
                + (f"<div style='margin-top:0.35rem;'>{pills_html}</div>" if pills_html else "")
                + "</div>",
                unsafe_allow_html=True,
            )


def _item_thumbnail_html(item: dict, size_px: int = 44) -> str:
    """
    Single source of truth for item thumbnails across the app.

    Priority order:
      1. Local image_path (saved by the Photo tab) -> embedded as
         data: URI so it renders even on a transient filesystem.
      2. Remote source_image_url (from the Link tab) -> direct img src
         with onerror fallback that hides the broken-glyph.
      3. Clean placeholder card showing the item's type initial. No
         broken-image glyphs anywhere.
    """
    if not isinstance(item, dict):
        item = {}
    size = max(20, int(size_px))
    base_style = (
        f"width:{size}px; height:{size}px; object-fit:cover; "
        f"border-radius:6px; border:1px solid #E5E5E5; flex-shrink:0; "
        f"background:#FAFAFA;"
    )
    ipath = item.get("image_path")
    src_image = item.get("source_image_url")
    if ipath:
        data_uri = _image_to_data_uri(ipath)
        if data_uri:
            return (
                f'<img src="{data_uri}" alt="" style="{base_style}" '
                f'onerror="this.style.display=\'none\'">'
            )
    if src_image:
        return (
            f'<img src="{src_image}" alt="" style="{base_style}" '
            f'onerror="this.style.display=\'none\'">'
        )
    # Goal 8: placeholder takes the item's COLOR as its background so a
    # photoless camel coat still reads as a camel coat at a glance,
    # not just a grey card with an initial. Contrast-aware text color
    # keeps the initial legible on both light and dark swatches. If we
    # don't know the color, fall back to the original neutral card.
    initial = (item.get("type") or item.get("name") or "?")[:1].upper()
    color_name = (item.get("color") or "").lower().strip()
    try:
        hex_str = color_to_swatch(color_name) if color_name else None
    except Exception:
        hex_str = None
    if hex_str and hex_str.startswith("#") and len(hex_str) == 7:
        try:
            r = int(hex_str[1:3], 16); g = int(hex_str[3:5], 16); b = int(hex_str[5:7], 16)
            # Perceived luminance per ITU-R BT.601 — keeps text legible
            # on both very dark and very light swatches.
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        except Exception:
            lum = 0.5
        text = "#111111" if lum > 0.55 else "#FFFFFF"
        colored_style = base_style.replace("background:#FAFAFA;", f"background:{hex_str};")
        return (
            f'<div style="{colored_style} '
            f'display:flex; align-items:center; justify-content:center; '
            f'color:{text}; font-family:DM Sans,sans-serif; font-size:0.78rem; '
            f'font-weight:600; letter-spacing:0.04em; '
            f'box-shadow:inset 0 0 0 1px rgba(0,0,0,0.04);">'
            f'{initial}</div>'
        )
    return (
        f'<div style="{base_style} display:flex; align-items:center; '
        f'justify-content:center; color:#8E8E93; '
        f'font-family:DM Sans,sans-serif; font-size:0.78rem; '
        f'font-weight:600; letter-spacing:0.04em;">{initial}</div>'
    )


def _render_coming_up_this_week() -> None:
    """
    "Coming up this week" panel rendered below the current outfit on the
    Today screen. Shows up to four upcoming events (after the one
    currently displayed) with a pre-planned outfit summary for each.
    A "Plan in detail →" button per event swaps the active result to
    that event's full agent output without losing your place.
    """
    try:
        from styling_agent import plan_upcoming_events
    except Exception:
        return

    current_event_id = ((st.session_state.get("result") or {}).get("event") or {}).get("id")
    plans = plan_upcoming_events(limit=6, days_ahead=14)

    # Skip whichever event is the one currently shown in the main card.
    upcoming = [p for p in plans
                if (p.get("event") or {}).get("id") != current_event_id][:4]

    if not upcoming:
        return

    st.markdown(
        '<div style="margin:1.6rem 0 0.6rem; padding-top:1.2rem; '
        'border-top:1px solid #EEEEEE;">'
        '<div style="font-family:\'DM Serif Display\',serif; font-size:1.25rem; '
        'color:#111111; line-height:1.2;">Coming up this week</div>'
        '<div style="font-size:0.82rem; color:#6E6E73; margin-top:0.3rem; '
        'line-height:1.55;">'
        "Wearly pre-plans an outfit for each upcoming event. Weather is a "
        "forecast — re-plan closer to the day if the forecast shifts."
        "</div></div>",
        unsafe_allow_html=True,
    )

    for p in upcoming:
        ev = p.get("event") or {}
        rec = p.get("recommendation") or []
        weather = p.get("weather") or {}

        ev_title = ev.get("title", "Untitled event")
        ev_when = ev.get("date", "—")
        if ev.get("time"):
            ev_when = f"{ev_when}  ·  {_format_time_12h(ev['time'])}"
        ev_type = (ev.get("type") or "").lower()

        # Tiny weather note (skip if no usable data).
        weather_note = ""
        if isinstance(weather, dict) and weather.get("temp_f") not in (None, "—"):
            temp = weather.get("temp_f")
            cond = weather.get("condition", "")
            weather_note = (
                f'<span style="font-size:0.74rem; color:#6E6E73; margin-left:0.6rem;">'
                f'· {temp}°F {cond}</span>'
            )

        # Up to 4 outfit items shown as swatch + name.
        items_html = ""
        for it in rec[:4]:
            swatch = color_to_swatch(it.get("color", ""))
            items_html += (
                '<span style="display:inline-flex; align-items:center; gap:0.4rem; '
                'margin-right:0.85rem; font-size:0.84rem; color:#1C1917;">'
                f'<span class="item-swatch" style="background:{swatch}"></span>'
                f'{it.get("name","—")}'
                '</span>'
            )
        if not rec:
            items_html = (
                '<span style="font-size:0.82rem; color:#8E8E93; font-style:italic;">'
                "No matching items in your wardrobe — Wearly would suggest a gap."
                "</span>"
            )

        # Type badge top-right.
        type_badge = ""
        if ev_type:
            type_badge = (
                f'<span style="font-size:0.62rem; color:#111111; background:#FAFAFA; '
                f'border:1px solid #EEEEEE; padding:1px 9px; border-radius:99px; '
                f'letter-spacing:0.08em; text-transform:uppercase; font-weight:600;">'
                f'{ev_type}</span>'
            )

        # Card markup as a flat single-line string (markdown-safe).
        row_html = (
            '<div style="background:#FFFFFF; border:1px solid #E5E5E5; '
            'border-radius:6px; padding:0.95rem 1.1rem; margin-bottom:0.6rem;">'
            '<div style="display:flex; justify-content:space-between; '
            'align-items:baseline; gap:0.6rem; flex-wrap:wrap;">'
            f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.1rem; '
            f'color:#1C1917; line-height:1.2;">{ev_title}</div>'
            f'{type_badge}'
            '</div>'
            f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.25rem;">'
            f'{ev_when}{weather_note}</div>'
            f'<div style="margin-top:0.6rem;">{items_html}</div>'
            '</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)

        # The button has to live OUTSIDE the markdown so it's clickable.
        if st.button(
            f"Plan in detail →",
            key=f"plan_in_detail_{ev.get('id','')}",
            use_container_width=False,
        ):
            # Stamp source so the result page renders "Outfit for X"
            # instead of "Today's outfit" — this plan is for a future
            # event, not today. target_event_id is preserved so a
            # later Replan/Regenerate re-runs against THIS event,
            # not whatever's next on the calendar at click-time.
            p_stamped = dict(p)
            p_stamped["source"] = "planner"
            if ev.get("id"):
                p_stamped["target_event_id"] = ev.get("id")
            st.session_state["result"] = p_stamped
            st.session_state["last_run"] = {
                "mode":            "calendar",
                "everyday_request": None,
                "target_event_id":  ev.get("id"),
                "source":           "planner",
            }
            st.rerun()


def _render_calendar_import() -> None:
    """
    Privacy-respecting calendar connection — two paths:

      1. URL subscription  — paste the private .ics URL your calendar
         provider exposes. Wearly auto-fetches it. Closest thing to a
         real "connect my Google/Apple calendar" without OAuth.
      2. File upload       — export the .ics manually and drop it in.
         Fallback for corporate/Exchange calendars that don't expose
         a public feed URL.

    Both paths feed into the same calendar_events.json. No OAuth, no
    third-party tokens. The URL is treated as a credential and is
    stored locally only.
    """
    try:
        from calendar_import import (
            import_ics_events, subscribe_calendar_url, unsubscribe_calendar,
            refresh_subscription, get_subscription,
        )
    except Exception as _e:
        st.caption(f"Calendar connection unavailable: {_e}")
        return

    with st.expander("Connect your real calendar", expanded=False):
        st.markdown(
            "<div style='font-size:0.84rem; color:#2E2E2E; line-height:1.55; margin-bottom:0.8rem;'>"
            "Two ways to connect. Both run locally — <strong>no Google/Apple "
            "sign-in</strong>, no third-party tokens, no account on Wearly's side."
            "</div>",
            unsafe_allow_html=True,
        )

        _tab_url, _tab_file = st.tabs([
            "🔗  Calendar URL (recommended)",
            "📁  Upload .ics file",
        ])

        # ── Tab 1: URL subscription (auto-refreshing) ─────────────────
        with _tab_url:
            st.markdown(
                "<div style='font-size:0.84rem; color:#2E2E2E; line-height:1.55; margin-bottom:0.6rem;'>"
                "Paste the private <strong>.ics URL</strong> your calendar exposes. "
                "Wearly fetches it whenever you ask — events stay in sync without you "
                "having to re-upload."
                "</div>",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<details style='font-size:0.78rem; color:#6E6E73; line-height:1.55; "
                "background:#FAFAFA; border:1px solid #EEEEEE; border-radius:6px; "
                "padding:0.7rem 0.9rem; margin-bottom:0.8rem;'>"
                "<summary style='cursor:pointer; color:#111111; font-weight:500;'>"
                "Where do I find this URL?</summary>"
                "<div style='margin-top:0.6rem;'>"
                "<strong>Google Calendar</strong> · open "
                "<a href='https://calendar.google.com' target='_blank' style='color:#111111;'>"
                "calendar.google.com</a> → click the ⚙ → <em>Settings</em> → "
                "scroll to your calendar in the left list → click it → scroll to "
                "<em>\"Integrate calendar\"</em> → copy <strong>Secret address in "
                "iCal format</strong> (it ends with <code>.ics</code>)."
                "<br><br>"
                "<strong>Apple iCloud Calendar</strong> · open "
                "<a href='https://www.icloud.com/calendar/' target='_blank' style='color:#111111;'>"
                "iCloud.com/calendar</a> → hover the calendar in the sidebar → "
                "click the <em>share</em> icon → tick <em>\"Public Calendar\"</em> → "
                "copy the URL (starts with <code>webcal://</code> — Wearly converts it "
                "automatically)."
                "<br><br>"
                "<strong>What this URL is.</strong> It's a private link — anyone with "
                "it can read this one calendar (not your account). Wearly stores it "
                "locally only. If you ever want to revoke access, regenerate the URL "
                "in your calendar provider's settings."
                "</div></details>",
                unsafe_allow_html=True,
            )

            current_sub = get_subscription()
            if current_sub:
                last = current_sub.get("last_synced_at", "")
                last_count = current_sub.get("last_event_count", "—")
                st.markdown(
                    "<div style='background:#FFFFFF; border:1px solid #EEEEEE; "
                    "border-radius:6px; padding:0.7rem 0.9rem; margin-bottom:0.8rem;'>"
                    f"<div style='font-size:0.7rem; color:#1D6033; letter-spacing:0.1em; "
                    f"text-transform:uppercase; font-weight:600;'>Connected</div>"
                    f"<div style='font-size:0.92rem; color:#111111; margin-top:0.3rem;'>"
                    f"{current_sub.get('label','Calendar')}</div>"
                    f"<div style='font-size:0.74rem; color:#6E6E73; margin-top:0.25rem;'>"
                    f"Last sync: {last or 'never'} · "
                    f"{last_count} event{'' if last_count == 1 else 's'}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                col_r, col_u = st.columns([3, 1], gap="small")
                with col_r:
                    if st.button("↻  Refresh from calendar", key="cal_url_refresh",
                                 type="primary", use_container_width=True):
                        with st.spinner("Fetching your calendar…"):
                            # Mirror mode: deletions in the source
                            # calendar are reflected locally.
                            res = refresh_subscription(replace=True)
                        if res.get("success"):
                            dropped = max(
                                0,
                                (sub.get("last_event_count") or 0)
                                - res.get("total", 0)
                            )
                            st.success(
                                f"Synced. {len(res['added'])} new · "
                                f"{len(res['updated'])} refreshed · "
                                f"{dropped} removed · "
                                f"{res['total']} total."
                            )
                            st.rerun()
                        else:
                            st.error(res.get("error", "Sync failed."))
                with col_u:
                    if st.button("Disconnect", key="cal_url_unsub",
                                 use_container_width=True):
                        unsubscribe_calendar()
                        st.toast("Disconnected — calendar events kept.")
                        st.rerun()
            else:
                st.text_input(
                    "Calendar URL",
                    placeholder="https://calendar.google.com/calendar/ical/.../basic.ics  "
                                "or  webcal://p##-caldav.icloud.com/...",
                    key="cal_url_input",
                    label_visibility="collapsed",
                )
                if st.button("Connect & sync now", key="cal_url_subscribe",
                             type="primary", use_container_width=True):
                    url = (st.session_state.get("cal_url_input") or "").strip()
                    if not url:
                        st.error("Paste a calendar URL above.")
                    else:
                        sub_res = subscribe_calendar_url(url)
                        if not sub_res.get("success"):
                            st.error(sub_res.get("error", "Could not save the URL."))
                        else:
                            with st.spinner(f"Fetching your {sub_res['label']}…"):
                                # First sync from a URL — replace any
                                # stale local seeds with the source.
                                res = refresh_subscription(replace=True)
                            if res.get("success"):
                                st.success(
                                    f"Connected to your {sub_res['label']}. "
                                    f"Imported {len(res['added'])} new event"
                                    f"{'' if len(res['added']) == 1 else 's'}"
                                    f" · {res['total']} total."
                                )
                                st.rerun()
                            else:
                                # The URL was saved, but the first fetch failed.
                                # Keep the URL so the user can retry without
                                # re-pasting; surface the actual error clearly.
                                st.error(
                                    f"URL saved, but the first sync failed: "
                                    f"{res.get('error','unknown error')}"
                                )

        # ── Tab 2: file upload (fallback) ─────────────────────────────
        with _tab_file:
            st.markdown(
                "<div style='font-size:0.84rem; color:#2E2E2E; line-height:1.55; margin-bottom:0.6rem;'>"
                "Drop a <strong>.ics</strong> file you exported from your calendar app. "
                "Useful when your calendar doesn't expose a public URL (corporate "
                "Outlook / Exchange calendars typically don't)."
                "</div>"
                "<div style='font-size:0.78rem; color:#6E6E73; line-height:1.55; margin-bottom:0.8rem;'>"
                "<strong>How to export:</strong> "
                "<em>Google Calendar</em> → Settings → \"Import & export\" → Export. "
                "<em>Apple Calendar</em> → File → Export → Export… "
                "<em>Outlook</em> → File → Save Calendar."
                "</div>",
                unsafe_allow_html=True,
            )
            up = st.file_uploader(
                "Drop your .ics file",
                type=["ics"],
                accept_multiple_files=False,
                key="cal_ics_upload",
                label_visibility="collapsed",
            )
            replace_mode = st.checkbox(
                "Replace existing events (otherwise merge)",
                value=False,
                key="cal_ics_replace",
                help="Off: events with the same id refresh in place; new events append. "
                     "On: clear the calendar and keep only what's in this file.",
            )
            if up is not None:
                if st.button("Import events", key="cal_ics_import_btn",
                             type="primary", use_container_width=True):
                    try:
                        text = up.getvalue().decode("utf-8", errors="replace")
                    except Exception as _e:
                        st.error(f"Could not read the file: {_e}")
                    else:
                        res = import_ics_events(text, replace=replace_mode)
                        if res.get("success"):
                            st.success(
                                f"Imported {len(res['added'])} new event"
                                f"{'' if len(res['added']) == 1 else 's'}"
                                f" · refreshed {len(res['updated'])}"
                                f" · total now {res['total']}."
                                + (f" ({res['skipped']} block"
                                   f"{'' if res['skipped'] == 1 else 's'} couldn't be parsed.)"
                                   if res.get("skipped") else "")
                            )
                        else:
                            st.error(res.get("error", "Import failed."))


def _render_routine_editor() -> None:
    """
    Weekly-routine editor — REDESIGNED.

    The old editor showed an input row under every weekday, which made
    it feel like a per-event scheduler. The new editor centers on a
    single "Add activity" form (name + multi-day select + start/end +
    location/note), with a list view of saved activities below. One
    activity can recur on multiple days; the same activity name can
    also be added multiple times with different days/times.

    Body-positive framing: describes the rhythm of your week, never
    prescribes it. Every activity is optional. Wearly only consults
    the routine when the calendar has no event for the current
    moment — never as an override.
    """
    try:
        from routine_tool import (
            get_routine, add_activity, remove_activity,
            format_time_12h, DAYS, VALID_OCCASIONS,
        )
    except Exception as _e:
        st.caption(f"Routine editor unavailable: {_e}")
        return

    with st.expander("Your weekly routine — fallback when the calendar is empty",
                     expanded=False):
        st.markdown(
            "<div style='font-size:0.82rem; color:#2E2E2E; line-height:1.55; "
            "margin-bottom:0.9rem;'>"
            "Describe the rhythm of your typical week — work, gym, class, "
            "remote-work blocks, errand windows. Wearly uses this only "
            "<strong>when your calendar has no event</strong> for the "
            "current moment — never as an override."
            "</div>",
            unsafe_allow_html=True,
        )

        # ── Existing activities (saved on disk) ───────────────────
        activities = get_routine().get("activities", []) or []
        if activities:
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; "
                "letter-spacing:0.14em; text-transform:uppercase; "
                "font-weight:600; margin-bottom:0.5rem;'>"
                f"Your routine ({len(activities)} "
                f"activit{'y' if len(activities) == 1 else 'ies'})</div>",
                unsafe_allow_html=True,
            )
            for a in activities:
                days_pretty = ", ".join(d.title() for d in (a.get("days") or []))
                start12 = format_time_12h(a.get("start", ""))
                end12   = format_time_12h(a.get("end", ""))
                loc     = a.get("location", "") or ""
                note    = a.get("note", "") or ""
                meta_bits = [s for s in (loc, note) if s]
                meta_line = " · ".join(meta_bits)
                row = st.columns([6, 1], gap="small")
                with row[0]:
                    st.markdown(
                        "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
                        "border-radius:6px; padding:0.7rem 0.95rem; "
                        "margin-bottom:0.55rem;'>"
                        "<div style='display:flex; align-items:baseline; "
                        "gap:0.6rem; flex-wrap:wrap;'>"
                        f"<div style='font-size:0.94rem; color:#1C1917; "
                        f"font-weight:500;'>{a.get('name','—')}</div>"
                        f"<div style='font-size:0.72rem; color:#8E8E93; "
                        f"letter-spacing:0.06em;'>{a.get('occasion','casual').upper()}"
                        f"</div></div>"
                        f"<div style='font-size:0.82rem; color:#6E6E73; "
                        f"margin-top:0.25rem;'>"
                        f"{days_pretty} · {start12} – {end12}"
                        + (f" · {meta_line}" if meta_line else "")
                        + "</div></div>",
                        unsafe_allow_html=True,
                    )
                with row[1]:
                    if st.button(
                        "Delete",
                        key=f"routine_del_{a.get('id','x')}",
                        use_container_width=True,
                    ):
                        rd = remove_activity(a.get("id"))
                        if rd.get("success"):
                            st.toast(f"Removed '{a.get('name','activity')}'.")
                        else:
                            st.error(rd.get("error", "Could not remove."))
                        st.rerun()
        else:
            st.markdown(
                "<div style='font-size:0.82rem; color:#8E8E93; "
                "margin:0.4rem 0 1rem; font-style:italic;'>"
                "No routine activities yet. Add one below — Wearly will "
                "fall back to it whenever your calendar is empty."
                "</div>",
                unsafe_allow_html=True,
            )

        # ── Add activity form ─────────────────────────────────────
        st.markdown(
            "<div style='font-size:0.7rem; color:#8E8E93; "
            "letter-spacing:0.14em; text-transform:uppercase; "
            "font-weight:600; margin:1.1rem 0 0.45rem;'>"
            "Add routine activity</div>",
            unsafe_allow_html=True,
        )

        with st.form("routine_add_form", clear_on_submit=True):
            r1 = st.columns([2, 2], gap="medium")
            with r1[0]:
                a_name = st.text_input(
                    "Activity",
                    placeholder="e.g. Work, Morning gym, Class, Errands",
                    key="routine_add_name",
                )
            with r1[1]:
                a_occasion = st.selectbox(
                    "Occasion (used by the agent)",
                    options=["(auto-infer)"] + sorted(VALID_OCCASIONS),
                    index=0,
                    key="routine_add_occasion",
                    help=(
                        "Leave on auto-infer to have Wearly guess from the "
                        "activity name (e.g. 'Morning gym' → gym). Override "
                        "explicitly when needed."
                    ),
                )

            # Day picker with group shortcuts. Multiple groups can be
            # selected; routine_tool._normalize_days expands them.
            day_options = [
                "Every day", "Weekdays", "Weekends",
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            a_days = st.multiselect(
                "Days",
                options=day_options,
                default=[],
                key="routine_add_days",
                help="Pick one or more days. 'Weekdays' = Mon–Fri, "
                     "'Weekends' = Sat–Sun, 'Every day' = all 7.",
            )

            r2 = st.columns([1, 1], gap="medium")
            with r2[0]:
                a_start = st.text_input(
                    "Start time",
                    placeholder="e.g. 7:00 AM",
                    key="routine_add_start",
                    help="12-hour ('7:00 AM') or 24-hour ('07:00') both work.",
                )
            with r2[1]:
                a_end = st.text_input(
                    "End time",
                    placeholder="e.g. 8:00 AM",
                    key="routine_add_end",
                )

            a_location = st.text_input(
                "Location / note (optional)",
                placeholder="e.g. office, remote, gym, campus, outdoor walk",
                key="routine_add_location",
                help=(
                    "Influences outfit reasoning when relevant: 'outdoor' nudges "
                    "weather sensitivity, 'office' nudges polish, 'remote' "
                    "nudges comfort."
                ),
            )

            submit = st.form_submit_button(
                "Add to routine", type="primary", use_container_width=True,
            )
            if submit:
                fields = {
                    "name":     a_name,
                    "days":     a_days,
                    "start":    a_start,
                    "end":      a_end,
                    "location": a_location,
                    "note":     "",
                }
                if a_occasion and a_occasion != "(auto-infer)":
                    fields["occasion"] = a_occasion
                rd = add_activity(fields)
                if rd.get("success"):
                    st.success(
                        f"Added '{rd['activity']['name']}' "
                        f"({', '.join(d.title() for d in rd['activity']['days'])} · "
                        f"{format_time_12h(rd['activity']['start'])}–"
                        f"{format_time_12h(rd['activity']['end'])})."
                    )
                    st.rerun()
                else:
                    # Surface the error and stop here — no rerun would
                    # otherwise clear the message before the user sees it.
                    st.error(rd.get("error", "Could not add activity."))


def _render_event_detail():
    """
    Dedicated route for Planner- and Routine-sourced results.

    This is the page the user sees when they click "Plan in detail"
    on a Planner card (a future calendar event) or a Routine card (a
    recurring weekly rhythm). It is NOT Today. The previous design
    re-skinned Today's header, which left the top-nav "Today" pill
    highlighted and the URL on `?section=today` — confusing because
    the outfit is for a future event, not today.

    Behavior:
      - Eyebrow says "Planned outfit" (planner) or "Routine outfit"
        (routine), with a clear "← Back to <Planner|Routine>" link.
      - Title is "Outfit for <event title>".
      - Subtitle carries date, time, occasion, location (routine
        only), and the source.
      - The shared `_render_outfit_result(res)` renders the body
        (reasoning, items, gaps, graph, KG export) — same component
        Today uses, so all derivatives stay tied to THIS result.
      - Replan / Reject-and-regenerate buttons preserve the
        target_event_id and source so a regenerate stays scoped to
        this event, never falls back to "today's next event".
      - Top-nav highlights the originating pill (Planner / Routine).
        See the _nav_active computation alongside _SECTIONS.
    """
    res = st.session_state.get("result")
    if not res:
        # No result in session state — bounce the user back to Planner
        # so they can pick an event. Avoids a blank page if they typed
        # the URL directly.
        st.warning(
            "No event selected yet. Open the Planner and click "
            "**Plan in detail** on any upcoming event."
        )
        if st.button("← Go to Planner", key="event_detail_no_res_back",
                     use_container_width=False):
            st.session_state["section"] = "planner"
            st.rerun()
        return

    _source = (res.get("source") or "").lower()
    _event  = res.get("event") or {}
    is_routine = _source == "routine"

    # ── Back link + eyebrow ─────────────────────────────────────
    back_target = "routine" if is_routine else "planner"
    back_label  = "Routine" if is_routine else "Planner"
    back_cols = st.columns([1, 5], gap="small")
    with back_cols[0]:
        if st.button(f"← Back", key=f"event_detail_back",
                     use_container_width=True,
                     help=f"Return to the {back_label} list."):
            st.session_state["section"] = back_target
            st.rerun()
    with back_cols[1]:
        st.markdown(
            "<div style='font-size:0.78rem; color:#6E6E73; padding-top:0.45rem;'>"
            f"Showing one event from <strong>{back_label}</strong>. "
            f"This is not today's outfit."
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Event header ───────────────────────────────────────────
    ev_title = _event.get("title", "Untitled event") or "Untitled event"
    ev_date  = _event.get("date", "") or ""
    ev_time  = _event.get("time", "") or ""
    ev_time_str = _format_time_12h(ev_time) if ev_time else ""
    ev_type  = (_event.get("type") or "casual").lower()
    ev_loc   = (_event.get("location") or "").strip()

    try:
        from datetime import datetime as _dt
        if ev_date and "-" in ev_date:
            _d = _dt.strptime(ev_date, "%Y-%m-%d")
            pretty_date = _d.strftime("%a %b ") + str(_d.day) + ", " + str(_d.year)
        else:
            pretty_date = ev_date
    except (ValueError, TypeError):
        pretty_date = ev_date

    subtitle_bits = [b for b in (pretty_date, ev_time_str, ev_type.title()) if b]
    if ev_loc:
        subtitle_bits.append(f"location: {ev_loc}")
    subtitle = " · ".join(subtitle_bits)

    eyebrow_text = "Routine outfit" if is_routine else "Planned outfit"
    source_note = (
        f"Planned from your <strong>{back_label}</strong>. "
        "Reasoning, graph, and exports below all refer to this event "
        "— not today."
    )

    st.markdown(
        "<div style='margin-top:0.6rem; margin-bottom:1.2rem;'>"
        "<div style='font-size:0.66rem; color:#8E8E93; "
        "letter-spacing:0.14em; text-transform:uppercase; "
        "font-weight:600; margin-bottom:0.35rem;'>"
        f"{eyebrow_text}</div>"
        f"<div style='font-family:\"DM Serif Display\",serif; "
        f"font-size:1.9rem; color:#1C1917; line-height:1.1;'>"
        f"Outfit for {ev_title}</div>"
        + (f"<div style='font-size:0.86rem; color:#6E6E73; "
           f"margin-top:0.35rem;'>{subtitle}</div>" if subtitle else "")
        + f"<div style='font-size:0.8rem; color:#6E6E73; "
        f"margin-top:0.5rem; line-height:1.55;'>{source_note}</div>"
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Shared outfit body (reasoning, items, gaps, graph, KG export) ──
    _render_outfit_result(res)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Replan THIS event (not today's next event) ─────────────
    if st.button("Replan this event", key="replan_event_detail",
                 use_container_width=False,
                 help=(f"Re-run the agent against {ev_title!r} only. "
                       "Clears any rejection feedback first.")):
        st.session_state["rejected_ids"] = []
        st.session_state["rejection_reasons"] = []
        last = st.session_state.get(
            "last_run",
            {"mode": "calendar", "everyday_request": None,
             "target_event_id": None, "source": _source or "planner"},
        )
        with st.spinner(f"Re-planning '{ev_title}'…"):
            _run_and_store(
                mode=last.get("mode", "calendar"),
                everyday_request=last.get("everyday_request"),
                target_event_id=last.get("target_event_id"),
                source=last.get("source") or _source or "planner",
            )
        # Stay on the event_detail route after replanning.
        st.session_state["section"] = "event_detail"
        st.rerun()

    # Footer hint pointing back where they came from.
    st.markdown(
        "<div style='margin:1.4rem 0 0; padding-top:1rem; "
        "border-top:1px solid #EEEEEE; font-size:0.84rem; color:#6E6E73;'>"
        f"Browsing more events? Open <a href='?section={back_target}' "
        f"target='_self' style='color:#111111; font-weight:500;'>"
        f"{back_label}</a> for the full list."
        "</div>",
        unsafe_allow_html=True,
    )


def _render_today():
    res = st.session_state.get("result")

    # Surface any silent auto-refresh outcome from the last run so the
    # user sees that fresh events were pulled (or notices an issue).
    _ar = st.session_state.pop("_cal_auto_refresh_result", None)
    if _ar:
        if _ar.get("success") and (_ar.get("added") or _ar.get("updated")):
            st.toast(
                f"Calendar synced: {len(_ar.get('added', []))} new · "
                f"{len(_ar.get('updated', []))} refreshed."
            )
        elif not _ar.get("success") and _ar.get("error"):
            # Don't pop a toast for every "no URL" case — only when there
            # IS a subscription and the refresh actually failed.
            if "subscribed" not in (_ar.get("error", "") or "").lower():
                st.toast(f"Calendar auto-refresh: {_ar.get('error', 'failed')}")

    # SAFETY HATCH: if the current result was produced by the Planner
    # or Routine "Plan in detail" buttons, redirect to the event-detail
    # route instead of rendering as Today. This catches users who land
    # on /?section=today with a planner-sourced result still in
    # session state (e.g. from a bookmark / browser-back) and keeps
    # the contract clean: Today = today, planner-sourced results live
    # at event_detail.
    if res:
        _source = (res.get("source") or "").lower()
        if _source in ("planner", "routine"):
            st.session_state["section"] = "event_detail"
            st.rerun()

    if res:
        st.markdown("""
        <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Today's outfit</div>
            <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">Wearly's recommendation for the next event on your calendar.</div>
        </div>
        """, unsafe_allow_html=True)
        _render_outfit_result(res)
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        if st.button("Replan from scratch", key="replan_today",
                     use_container_width=False):
            st.session_state["rejected_ids"] = []
            st.session_state["rejection_reasons"] = []
            last = st.session_state.get(
                "last_run",
                {"mode": "calendar", "everyday_request": None,
                 "target_event_id": None, "source": "today"},
            )
            with st.spinner("Re-running the agent…"):
                _run_and_store(
                    mode=last.get("mode", "calendar"),
                    everyday_request=last.get("everyday_request"),
                    target_event_id=last.get("target_event_id"),
                    source=last.get("source") or "today",
                )
            st.rerun()

        # The week-ahead view used to live here. It now has its own
        # top-nav section ("Planner") so users can browse upcoming
        # events without first having to plan today's outfit. A
        # compact link points there from the bottom of the result.
        st.markdown(
            "<div style='margin:1.4rem 0 0; padding-top:1rem; "
            "border-top:1px solid #EEEEEE; font-size:0.84rem; color:#6E6E73;'>"
            "Browsing the week ahead? Open the "
            "<a href='?section=planner' target='_self' style='color:#111111; "
            "font-weight:500;'>Planner</a> for outfits + gaps across "
            "every upcoming event."
            "</div>",
            unsafe_allow_html=True,
        )
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

        # Note: the calendar-connection surface used to live here but
        # moved to the Profile screen — it's a one-time setup, not a
        # daily-use control.


# ─────────────────────────────────────────────
# PLANNER — the week + month ahead
# ─────────────────────────────────────────────

def _render_planner():
    """
    Calendar-driven view of upcoming events with a recommended outfit
    per event. Three tabs:

      This week   — events in the next 7 days
      This month  — events in the next 31 days
      All upcoming — everything we know about (capped at days_ahead=60)

    Per-event card carries: title + type, date/time, weather, the
    recommended outfit with images, any wardrobe gaps + a one-click
    "Save to wishlist" for the missing piece type.
    """
    # Defensive imports. Streamlit reruns the script on every rerender
    # but it does NOT clear sys.modules — so when calendar_tool /
    # styling_agent have changed on disk since this Streamlit process
    # started, `from <mod> import <new_name>` raises ImportError because
    # Python returns the stale cached module. We catch that, force a
    # reload, and try again. Restarting Streamlit is the proper fix
    # but this keeps the Planner usable without restarting.
    try:
        from styling_agent import plan_upcoming_events
        from calendar_import import get_subscription
        from calendar_tool import has_real_calendar_events
        from shopping_tool import add_wishlist_item, gap_is_on_wishlist
    except ImportError:
        try:
            import importlib
            import calendar_tool as _ct, styling_agent as _sa
            importlib.reload(_ct)
            importlib.reload(_sa)
            from styling_agent import plan_upcoming_events
            from calendar_import import get_subscription
            from calendar_tool import has_real_calendar_events
            from shopping_tool import add_wishlist_item, gap_is_on_wishlist
        except Exception as _e:
            st.error(
                f"Planner unavailable: {_e}. "
                "If you just pulled new code, restart Streamlit "
                "(Ctrl+C in the terminal, then `streamlit run app.py`)."
            )
            return
    except Exception as _e:
        st.error(f"Planner unavailable: {_e}")
        return

    # Refresh subscription if stale, so newly-added Google/Apple events
    # show up here even if the user came straight to the Planner.
    _auto_refresh_subscription_if_needed()

    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Planner</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">
            Outfits, gaps, and wishlist suggestions for every event on your real
            calendar — week and month ahead. Connect a calendar to populate this view.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # The Planner is a real-calendar-only surface. Determine whether
    # the user has either (a) a subscription URL set, or (b) at least
    # one event in their own calendar_events.json (from an .ics
    # upload or a prior subscription sync). If neither, show a
    # dedicated empty state and stop — no fabricated seed events.
    sub = get_subscription()
    has_events = has_real_calendar_events()
    if not sub and not has_events:
        st.markdown(
            "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
            "border-radius:6px; padding:1.4rem 1.5rem; margin-top:0.4rem;'>"
            "<div style='font-family:\"DM Serif Display\",serif; font-size:1.25rem; color:#1C1917;'>"
            "Connect your calendar"
            "</div>"
            "<div style='font-size:0.88rem; color:#6E6E73; margin-top:0.5rem; line-height:1.55;'>"
            "The Planner only shows real events from <em>your</em> calendar — "
            "it never fabricates demo events. To populate this view, open the "
            "<a href='?section=profile' target='_self' style='color:#111111; "
            "font-weight:500;'>Profile screen</a> and either:"
            "<ul style='margin:0.6rem 0 0.4rem 1.2rem; padding:0; line-height:1.65;'>"
            "<li>paste a Google Calendar or iCloud ICS URL (one click, no sign-in), or</li>"
            "<li>upload an <code>.ics</code> file exported from your calendar app.</li>"
            "</ul>"
            "After that, every upcoming event will appear here with a recommended outfit, "
            "weather, wardrobe gaps, and one-click wishlist suggestions for missing pieces."
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    # Plan up to 30 events across 60 days — plenty for week + month
    # tabs. Cached per-session so flipping between tabs is instant;
    # the refresh button below clears the cache. seed_fallback stays
    # at its False default — the Planner is real-calendar-only.
    plans = st.session_state.get("planner_plans")
    if plans is None:
        with st.spinner("Reading your calendar and planning each event…"):
            try:
                plans = plan_upcoming_events(limit=30, days_ahead=60)
            except Exception as _e:
                plans = []
                st.error(f"Could not plan upcoming events: {_e}")
        st.session_state["planner_plans"] = plans

    # Right column needs ~12 characters of horizontal space for the
    # "↻ Re-sync calendar" label to stay on one line. A 5:1 split
    # collapses it to two lines; 5:3 keeps it inline at every common
    # viewport width.
    col_l, col_r = st.columns([5, 3], gap="small")
    with col_r:
        if st.button("↻ Re-sync calendar", key="planner_refresh",
                     use_container_width=True,
                     help=("Pulls fresh events from your subscribed calendar "
                           "and drops anything you've deleted at the source.")):
            # Force a full mirror-mode resync from the URL (if any),
            # then invalidate the planner cache so the next render
            # rebuilds plans from the now-truthful event list.
            if sub:
                try:
                    from calendar_import import refresh_subscription as _refresh
                    with st.spinner("Re-syncing your calendar…"):
                        _refresh(replace=True, timeout=10)
                except Exception as _e:
                    st.warning(f"Re-sync failed: {_e}. Showing cached events.")
            st.session_state.pop("planner_plans", None)
            st.rerun()

    if not plans:
        st.markdown(
            "<div style='margin-top:1rem; font-size:0.86rem; color:#6E6E73;'>"
            "Your calendar is connected, but there are no events in the next "
            "60 days. Add an event in Google Calendar or Apple Calendar (or "
            "upload a fresh <code>.ics</code> from Profile) and click "
            "<strong>↻ Refresh</strong>."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Split plans by how far away the event is.
    from datetime import date, datetime, timedelta
    today_d = date.today()
    end_week = today_d + timedelta(days=7)
    end_month = today_d + timedelta(days=31)

    def _ev_date(p):
        try:
            return datetime.strptime(
                (p.get("event") or {}).get("date", ""), "%Y-%m-%d"
            ).date()
        except Exception:
            return None

    week_plans  = [p for p in plans if (_ev_date(p) and today_d <= _ev_date(p) <= end_week)]
    month_plans = [p for p in plans if (_ev_date(p) and today_d <= _ev_date(p) <= end_month)]
    all_plans   = [p for p in plans if (_ev_date(p) and _ev_date(p) >= today_d)]

    # Week / month / all digest narrative — Goal 7. One small line per
    # tab telling the user "what does my plan look like at a glance"
    # so they don't have to scroll every card to understand.
    try:
        from styling_agent import plan_summary as _plan_summary
        _summaries = {
            "week":  _plan_summary(week_plans),
            "month": _plan_summary(month_plans),
            "all":   _plan_summary(all_plans),
        }
    except Exception:
        _summaries = {"week": {}, "month": {}, "all": {}}

    def _render_summary_pill(summary: dict) -> None:
        text = (summary or {}).get("narrative") or ""
        if not text:
            return
        st.markdown(
            "<div style='background:#FAFAFA; border:1px solid #EEEEEE; "
            "border-radius:6px; padding:0.7rem 0.9rem; margin-bottom:0.7rem; "
            "font-size:0.84rem; color:#2E2E2E; line-height:1.45;'>"
            f"<strong style='color:#111111;'>Week at a glance —</strong> {text}"
            "</div>",
            unsafe_allow_html=True,
        )

    _tab_week, _tab_month, _tab_all = st.tabs([
        f"This week ({len(week_plans)})",
        f"This month ({len(month_plans)})",
        f"All upcoming ({len(all_plans)})",
    ])
    with _tab_week:
        _render_summary_pill(_summaries["week"])
        _render_planner_card_list(week_plans, scope_label="this week",
                                  scope_key="week")
    with _tab_month:
        _render_summary_pill(_summaries["month"])
        _render_planner_card_list(month_plans, scope_label="this month",
                                  scope_key="month")
    with _tab_all:
        _render_summary_pill(_summaries["all"])
        _render_planner_card_list(all_plans, scope_label="upcoming",
                                  scope_key="all")


def _render_routine_week() -> None:
    """
    Weekly Routine Outfits — separate from the Planner (which only
    shows real calendar events).

    Routine outfits are for the user's normal weekly rhythm: what
    they wear on a typical Monday, Tuesday, etc., when no calendar
    event is on the books. Calendar events still win when both
    exist for the same moment — this view is the rhythm, not the
    schedule.
    """
    st.markdown("""
    <div style="margin-top:0.2rem; margin-bottom:1.1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.9rem; color:#1C1917; line-height:1.1;">Routine week</div>
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem; line-height:1.55;">
            Outfits for your normal weekly rhythm — work / gym / class /
            errands. Wearly only consults this when your calendar has no
            event for that moment. Edit your routine activities in
            <a href="?section=profile" target="_self" style="color:#111111; font-weight:500;">Profile</a>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        from styling_agent import plan_routine_week
        from routine_tool import get_routine, format_time_12h
    except Exception as _e:
        st.error(f"Routine week unavailable: {_e}")
        return

    activities = get_routine().get("activities", []) or []
    if not activities:
        st.markdown(
            "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
            "border-radius:6px; padding:1.4rem 1.5rem; margin-top:0.4rem;'>"
            "<div style='font-family:\"DM Serif Display\",serif; "
            "font-size:1.25rem; color:#1C1917;'>"
            "No routine activities yet"
            "</div>"
            "<div style='font-size:0.88rem; color:#6E6E73; margin-top:0.5rem; "
            "line-height:1.55;'>"
            "Open <a href='?section=profile' target='_self' style='color:#111111; "
            "font-weight:500;'>Profile</a> → <em>Your weekly routine</em>, "
            "and add an activity (work, gym, class, remote work, errands, …). "
            "Wearly will then plan outfits for every weekday of your normal "
            "week here."
            "</div></div>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Planning each day of your routine week…"):
        try:
            plans = plan_routine_week()
        except Exception as _e:
            plans = []
            st.error(f"Could not plan routine week: {_e}")

    if not plans:
        st.info("No routine plans returned.")
        return

    # 7 cards — Mon through Sun. Empty days get a quiet placeholder.
    for p in plans:
        weekday = (p.get("weekday") or "").title() or "—"
        if p.get("empty"):
            st.markdown(
                "<div style='background:#FFFFFF; border:1px dashed #E5E5E5; "
                "border-radius:6px; padding:0.9rem 1.1rem; margin-bottom:0.7rem;'>"
                f"<div style='font-size:0.78rem; color:#8E8E93; "
                f"letter-spacing:0.14em; text-transform:uppercase; "
                f"font-weight:600;'>{weekday}</div>"
                "<div style='font-size:0.84rem; color:#6E6E73; "
                "margin-top:0.3rem;'>No routine activity scheduled.</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            continue

        ev = p.get("event") or {}
        rec = p.get("recommendation") or []
        title = ev.get("title") or "Routine"
        time_pretty = format_time_12h(ev.get("time") or "")
        location = ev.get("location") or ""

        items_html = ""
        for it in rec[:5]:
            color = (it.get("color") or "").strip()
            try:
                hex_color = color_to_swatch(color) if color else "#FAFAFA"
            except Exception:
                hex_color = "#FAFAFA"
            items_html += (
                "<div style='display:inline-flex; align-items:center; "
                "gap:0.45rem; padding:0.32rem 0.75rem; background:#FFFFFF; "
                "border:1px solid #E5E5E5; border-radius:99px; "
                "font-size:0.78rem; color:#3D332D; margin:0 0.35rem 0.35rem 0;'>"
                f"<span style='width:12px; height:12px; border-radius:50%; "
                f"background:{hex_color}; border:1px solid rgba(28,25,23,0.10); "
                f"display:inline-block;'></span>"
                f"{it.get('name','—')}</div>"
            )

        # The day card.
        cols = st.columns([5, 1], gap="small")
        with cols[0]:
            st.markdown(
                "<div style='background:#FFFFFF; border:1px solid #E5E5E5; "
                "border-radius:6px; padding:0.95rem 1.1rem; margin-bottom:0.7rem;'>"
                f"<div style='font-size:0.66rem; color:#8E8E93; "
                f"letter-spacing:0.14em; text-transform:uppercase; "
                f"font-weight:600;'>{weekday}</div>"
                f"<div style='font-family:\"DM Serif Display\",serif; "
                f"font-size:1.25rem; color:#1C1917; margin-top:0.25rem;'>"
                f"{title}</div>"
                + (f"<div style='font-size:0.82rem; color:#6E6E73; "
                   f"margin-top:0.2rem;'>"
                   + " · ".join(filter(None, [time_pretty, location]))
                   + "</div>" if (time_pretty or location) else "")
                + f"<div style='margin-top:0.55rem;'>{items_html}</div>"
                + "</div>",
                unsafe_allow_html=True,
            )
        with cols[1]:
            if st.button(
                "Plan in detail →",
                key=f"routine_detail_{weekday}",
                use_container_width=True,
            ):
                # Stamp source="routine" so the dedicated event_detail
                # route knows the back-link should go to Routine (not
                # Planner) and the eyebrow reads "Routine outfit".
                p_stamped = dict(p)
                p_stamped["source"] = "routine"
                st.session_state["result"]   = p_stamped
                st.session_state["last_run"] = {
                    "mode":            "everyday",
                    "everyday_request": ev.get("title") or ev.get("type") or "casual",
                    "source":          "routine",
                    "todays_context":  ev.get("note") or "",
                }
                # NEW: dedicated route — Today stays for today, this
                # is a routine-driven recurring outfit.
                st.session_state["section"] = "event_detail"
                st.rerun()


def _render_planner_card_list(plans: list, scope_label: str,
                              scope_key: str) -> None:
    """Render a list of event-plan cards, with an empty-state nudge.

    `scope_key` is a short string ('week' / 'month' / 'all') used to
    namespace the button keys for this tab. Streamlit renders all tab
    contents simultaneously, so the same event appearing in multiple
    tabs would otherwise collide on its st.button key. Each tab passes
    its own scope_key; that way an event id 'EVT001' becomes three
    independent button keys: planner_detail_week_EVT001 etc.
    """
    try:
        from shopping_tool import add_wishlist_item, gap_is_on_wishlist
    except Exception:
        add_wishlist_item = gap_is_on_wishlist = None

    if not plans:
        st.markdown(
            "<div style='margin-top:1rem; font-size:0.86rem; color:#6E6E73;'>"
            f"Nothing on your calendar {scope_label}. "
            "Add an event in Google/Apple Calendar — Wearly will pick it up on the next refresh."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    for p in plans:
        _render_planner_event_card(p, add_wishlist_item, gap_is_on_wishlist,
                                   scope_key=scope_key)


def _render_planner_event_card(p: dict, add_wishlist_item, gap_is_on_wishlist,
                               scope_key: str = "default") -> None:
    """One rich card per event: header, weather, outfit-with-images,
    gaps, save-to-wishlist actions, plan-in-detail button."""
    ev = p.get("event") or {}
    rec = p.get("recommendation") or []
    weather = p.get("weather") or {}
    gaps = p.get("gaps") or []
    suggestions = p.get("shopping_suggestions") or []

    ev_title = ev.get("title", "Untitled event")
    ev_date  = ev.get("date", "—")
    ev_time  = _format_time_12h(ev.get("time", ""))
    ev_type  = (ev.get("type") or "").lower()
    when_text = ev_date + (f"  ·  {ev_time}" if ev_time else "")

    weather_text = ""
    if isinstance(weather, dict) and weather.get("temp_f") not in (None, "—"):
        # Source-honest label so the user can tell a real forecast
        # apart from a seasonal estimate.
        _src = (weather.get("_source") or "").lower()
        if _src == "forecast":
            src_prefix = "Forecast"
        elif _src == "seasonal-fallback":
            src_prefix = "Seasonal estimate"
        elif _src == "live":
            src_prefix = "Live"
        else:
            src_prefix = ""
        prefix = f"{src_prefix} · " if src_prefix else ""
        weather_text = (
            f"{prefix}{weather.get('temp_f')}°F · {weather.get('condition','')}"
        )
        if weather.get("layer_advice"):
            weather_text += f" · {weather['layer_advice']}"

    # Type badge top-right.
    type_badge = ""
    if ev_type:
        type_badge = (
            f'<span style="font-size:0.62rem; color:#111111; background:#FAFAFA; '
            f'border:1px solid #EEEEEE; padding:1px 9px; border-radius:99px; '
            f'letter-spacing:0.08em; text-transform:uppercase; font-weight:600;">'
            f'{ev_type}</span>'
        )

    # ── Outer card frame ──
    st.markdown(
        '<div style="background:#FFFFFF; border:1px solid #E5E5E5; '
        'border-radius:8px; padding:1.1rem 1.2rem; margin-bottom:0.8rem;">'
        '<div style="display:flex; justify-content:space-between; '
        'align-items:baseline; gap:0.6rem; flex-wrap:wrap;">'
        f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.2rem; '
        f'color:#1C1917; line-height:1.2;">{ev_title}</div>'
        f'{type_badge}'
        '</div>'
        f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.25rem;">'
        f'{when_text}</div>'
        + (f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.15rem;">'
           f'<em>{weather_text}</em></div>' if weather_text else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    # ── Outfit row with thumbnails ──
    if rec:
        thumbs_html = '<div style="display:flex; flex-wrap:wrap; gap:0.8rem; margin:0.6rem 0 0.9rem;">'
        for it in rec[:6]:
            thumb = _item_thumbnail_html(it, size_px=56)
            color_chip = ""
            if it.get("color"):
                color_chip = (
                    f'<span style="font-size:0.66rem; color:#6E6E73; '
                    f'background:#FAFAFA; border:1px solid #EEEEEE; padding:1px 7px; '
                    f'border-radius:99px;">{it["color"]}</span>'
                )
            thumbs_html += (
                '<div style="display:flex; align-items:center; gap:0.55rem; '
                'padding:0.4rem 0.7rem; background:#FFFFFF; border:1px solid #EEEEEE; '
                'border-radius:6px;">'
                f'{thumb}'
                '<div>'
                f'<div style="font-size:0.84rem; color:#1C1917; font-weight:500;">{it.get("name","—")}</div>'
                f'<div style="font-size:0.7rem; color:#6E6E73; margin-top:0.15rem;">'
                f'{it.get("type","")}'
                + ('  ·  ' + color_chip if color_chip else "") +
                '</div></div></div>'
            )
        thumbs_html += '</div>'
        st.markdown(thumbs_html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="font-size:0.84rem; color:#8E8E93; font-style:italic; '
            'margin:0.5rem 0 0.8rem;">'
            "No matching pieces in your wardrobe for this event."
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Gaps + wishlist actions ──
    if gaps:
        st.markdown(
            '<div style="background:#FAFAFA; border:1px solid #EEEEEE; '
            'border-left:3px solid #111111; border-radius:6px; '
            'padding:0.7rem 0.95rem; margin-bottom:0.7rem;">'
            '<div style="font-size:0.7rem; color:#8E8E93; letter-spacing:0.12em; '
            'text-transform:uppercase; font-weight:600;">Missing for this event</div>'
            f'<div style="font-size:0.86rem; color:#1C1917; margin-top:0.35rem;">'
            + ", ".join(gaps) +
            '</div></div>',
            unsafe_allow_html=True,
        )
        # One Save-to-wishlist button per gap, if the wishlist tool is available.
        if add_wishlist_item and gap_is_on_wishlist:
            for gi, gap in enumerate(gaps):
                key_suffix = f"{scope_key}_{ev.get('id','x')}_{gi}_{gap}"
                if gap_is_on_wishlist(gap):
                    st.caption(f"✓ '{gap}' is already on your wishlist.")
                else:
                    sugg = suggestions[gi] if gi < len(suggestions) else f"A versatile {gap}."
                    if st.button(
                        f"Save '{gap}' to my wishlist",
                        key=f"planner_wish_{key_suffix}",
                        use_container_width=False,
                    ):
                        rr = add_wishlist_item({
                            "name":        f"Missing {gap} for upcoming events",
                            "category":    gap,
                            "tags":        [ev_type] if ev_type else [],
                            "priority":    "medium",
                            "notes":       sugg,
                            "linked_gap":  gap,
                        })
                        if rr.get("success"):
                            st.toast(f"Added '{gap}' to your wishlist.")
                            st.rerun()
                        else:
                            st.error(rr.get("error", "Could not add to wishlist."))

    # ── Plan-in-detail link ──
    cols = st.columns([3, 1], gap="small")
    with cols[1]:
        if st.button(
            "Plan in detail →",
            key=f"planner_detail_{scope_key}_{ev.get('id','x')}",
            use_container_width=True,
        ):
            # Stamp source + target_event_id so the dedicated
            # event_detail route renders "Outfit for <event>" with a
            # "← Back to Planner" link, NOT a re-skinned Today page.
            p_stamped = dict(p)
            p_stamped["source"] = "planner"
            if ev.get("id"):
                p_stamped["target_event_id"] = ev.get("id")
            st.session_state["result"] = p_stamped
            st.session_state["last_run"] = {
                "mode":            "calendar",
                "everyday_request": None,
                "target_event_id":  ev.get("id"),
                "source":           "planner",
            }
            # NEW: dedicated route. Top-nav highlights stay on
            # "Planner" (handled by _nav_active near _SECTIONS).
            st.session_state["section"] = "event_detail"
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

    # ── Demo wardrobe loader (curated 48-item seed) ─────────────
    # One-click button to populate a polished demo closet — useful
    # before recording a demo or showing the project to a reviewer.
    # Items are tagged `source: "demo"` with stable DM-* IDs so a
    # second click is a safe no-op and a separate "Remove demo"
    # button undoes the load. User-added items (UC###/US###/UA###)
    # are never touched. Local card images live under
    # wardrobe_images/DM-*.png.
    try:
        from demo_wardrobe import (
            load_demo_wardrobe, unload_demo_wardrobe, is_demo_loaded,
            real_photos_enabled,
        )
        _demo_active = is_demo_loaded()
        _photos_on   = real_photos_enabled()
    except Exception as _e:
        _demo_active = False
        _photos_on   = False
        load_demo_wardrobe = unload_demo_wardrobe = None  # type: ignore

    if load_demo_wardrobe is not None:
        # Always-visible card (not an expander) — the previous
        # collapsed expander was missed twice. This sits at the very
        # top of the Wardrobe page, above Backup & Restore.
        photo_status_line = (
            "<div style='font-size:0.78rem; color:#2E5B41; "
            "background:#E8F1EA; border:1px solid #C5DBC9; "
            "border-radius:4px; padding:0.45rem 0.75rem; "
            "margin-top:0.7rem;'>"
            "✓ <strong>Real photos enabled</strong> — PEXELS_API_KEY "
            "detected. Reload will fetch keyword-matched product "
            "photos via the free Pexels API."
            "</div>"
            if _photos_on else
            "<div style='font-size:0.78rem; color:#7C5A22; "
            "background:#FBF1DD; border:1px solid #EFD9A6; "
            "border-radius:4px; padding:0.55rem 0.85rem; "
            "margin-top:0.7rem; line-height:1.5;'>"
            "<strong>Real product photos available — 1-minute setup.</strong><br>"
            "Pexels gives free keyword-matched fashion photos "
            "(200/hr, no card needed). Sign up at "
            "<a href='https://www.pexels.com/api/' target='_blank' "
            "style='color:#7C5A22; font-weight:500;'>pexels.com/api</a>, "
            "then set the env var and restart Streamlit:<br>"
            "<code style='font-size:0.74rem;'>"
            "$env:PEXELS_API_KEY = \"&lt;your key&gt;\""
            "</code> (Windows) &nbsp;or&nbsp; "
            "<code style='font-size:0.74rem;'>"
            "export PEXELS_API_KEY=\"&lt;your key&gt;\""
            "</code> (bash).<br>"
            "Without a key, items fall back to clean drawn "
            "silhouettes — recognizable but not photos."
            "</div>"
        )

        st.markdown(
            "<div style='background:#FFFFFF; border:2px solid #111111; "
            "border-radius:8px; padding:1.25rem 1.4rem 1.05rem; "
            "margin-bottom:1.1rem; box-shadow:0 1px 0 rgba(0,0,0,0.04);'>"
            "<div style='font-size:0.66rem; color:#8E8E93; "
            "letter-spacing:0.14em; text-transform:uppercase; "
            "font-weight:600; margin-bottom:0.35rem;'>"
            + ("Demo wardrobe loaded" if _demo_active else "Demo wardrobe")
            + "</div>"
            "<div style='font-family:\"DM Serif Display\",serif; "
            "font-size:1.35rem; color:#1C1917; line-height:1.15; "
            "margin-bottom:0.4rem;'>"
            + ("48 curated demo items in your closet"
               if _demo_active else
               "Load 48 curated items in one click")
            + "</div>"
            "<div style='font-size:0.84rem; color:#6E6E73; "
            "line-height:1.55;'>"
            "Tops, bottoms, dresses, outerwear, activewear, shoes, "
            "and accessories — fabric, silhouette, and style notes "
            "for every item so the agent can demo full reasoning."
            "</div>"
            + photo_status_line
            + "</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns([1, 1], gap="small")
        with cols[0]:
            if st.button(
                "↻ Reload demo wardrobe" if _demo_active else "Load demo wardrobe",
                key="demo_load_btn",
                type="primary", use_container_width=True,
            ):
                with st.spinner("Loading demo wardrobe + generating card images…"):
                    res = load_demo_wardrobe()
                if res.get("error"):
                    st.error(res["error"])
                else:
                    refreshed = len(res.get("refreshed", []))
                    if res["added"]:
                        msg = (
                            f"Added {len(res['added'])} demo items. "
                            f"Skipped {len(res['skipped'])} (already loaded). "
                            f"Wardrobe now totals {res['total_after']}."
                        )
                        if refreshed:
                            msg += (f" Refreshed {refreshed} card image"
                                    f"{'s' if refreshed != 1 else ''}.")
                        st.success(msg)
                    elif refreshed:
                        st.success(
                            f"Refreshed {refreshed} card image"
                            f"{'s' if refreshed != 1 else ''} from the latest "
                            "silhouette renderer. Items themselves unchanged."
                        )
                    else:
                        st.info(
                            f"Demo already fully loaded — "
                            f"{len(res['skipped'])} item(s) already present."
                        )
                    if res.get("image_errors"):
                        st.warning(
                            f"Could not render card image for "
                            f"{len(res['image_errors'])} item(s). They still "
                            "load — just without a thumbnail."
                        )
                    rep = res.get("review_report") or ""
                    if rep:
                        photos_n = res.get("photos", 0)
                        sil_n = res.get("silhouettes", 0)
                        st.caption(
                            f"Pexels accepted **{photos_n}** items, "
                            f"silhouette fallback for **{sil_n}**. "
                            f"Per-item decision report at `{rep}` "
                            "(open in any spreadsheet)."
                        )
                    st.rerun()
        with cols[1]:
            if _demo_active:
                if st.button(
                    "Remove demo wardrobe",
                    key="demo_unload_btn",
                    use_container_width=True,
                    help=("Removes every DM-* item and its card image. "
                          "Your own added pieces stay."),
                ):
                    with st.spinner("Removing demo items…"):
                        ur = unload_demo_wardrobe()
                    if ur.get("error"):
                        st.error(ur["error"])
                    else:
                        st.success(
                            f"Removed {len(ur['removed'])} demo items. "
                            "Your own added items are untouched."
                        )
                        st.rerun()
            else:
                st.caption(
                    "Once loaded, a button to remove the demo set "
                    "appears here. User-added items are never affected."
                )

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
        _photo_inferred = None

        if uploaded is not None:
            image_bytes_for_save = uploaded.getvalue()
            prev_col, info_col = st.columns([2, 3], gap="medium")
            with prev_col:
                st.image(uploaded, caption=None, use_container_width=True)
            with info_col:
                # Goal 1: combine pixel color extraction with filename-
                # keyword inference so the user doesn't re-type fields
                # the filename already implies.
                with st.spinner("Reading image…"):
                    try:
                        from wardrobe_tool import infer_item_from_photo
                        _photo_inferred = infer_item_from_photo(
                            image_bytes_for_save,
                            filename=getattr(uploaded, "name", "") or "",
                        )
                    except Exception:
                        _photo_inferred = None
                    sugg = suggest_colors_from_image(image_bytes_for_save, top_n=3)

                if _photo_inferred:
                    if _photo_inferred.get("color"):
                        suggested_color_default = _photo_inferred["color"]
                    # Tell the user what we inferred, so the pre-fills aren't surprising.
                    bits: list = []
                    if _photo_inferred.get("category"):
                        bits.append(f"category <strong>{_photo_inferred['category']}</strong>")
                    if _photo_inferred.get("color"):
                        bits.append(f"color <strong>{_photo_inferred['color']}</strong>")
                    if _photo_inferred.get("formality"):
                        bits.append(f"formality <strong>{_photo_inferred['formality']}</strong>")
                    if _photo_inferred.get("season"):
                        bits.append(
                            f"season <strong>{', '.join(_photo_inferred['season'])}</strong>"
                        )
                    if _photo_inferred.get("tags"):
                        bits.append(f"tags <strong>{', '.join(_photo_inferred['tags'])}</strong>")
                    if bits:
                        st.markdown(
                            "<div style='font-size:0.66rem; color:#8E8E93; "
                            "letter-spacing:0.14em; text-transform:uppercase; "
                            "font-weight:600; margin-bottom:0.3rem;'>"
                            "What Wearly inferred"
                            "</div>"
                            f"<div style='font-size:0.84rem; color:#2E2E2E; "
                            f"line-height:1.55;'>{'; '.join(bits)}. "
                            f"<em style='color:#6E6E73;'>Review and adjust below.</em>"
                            "</div>",
                            unsafe_allow_html=True,
                        )

                if sugg.get("success") and sugg["suggestions"]:
                    if not suggested_color_default:
                        suggested_color_default = sugg["suggestions"][0]["name"]
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
                    <div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; text-transform:uppercase; font-weight:600; margin:0.55rem 0 0.3rem;">
                        Pixel-level color palette
                    </div>
                    <div style="margin-bottom:0.6rem;">{chips}</div>
                    """, unsafe_allow_html=True)
                elif not _photo_inferred:
                    st.warning(
                        f"Couldn't read this image — fill in the fields manually. "
                        f"{sugg.get('error','')}"
                    )

        # Helpers to pre-select options the inference suggested.
        def _safe_index(options, value, default=0):
            try:
                return options.index(value) if value in options else default
            except Exception:
                return default

        _inf_cat       = (_photo_inferred or {}).get("category") or "top"
        _inf_formality = (_photo_inferred or {}).get("formality") or "casual"
        _inf_seasons   = (_photo_inferred or {}).get("season") or ["all"]
        _inf_tags      = (_photo_inferred or {}).get("tags") or []
        _inf_name      = (_photo_inferred or {}).get("name") or ""

        with st.form("wardrobe_add_form_photo", clear_on_submit=True):
            col_a, col_b = st.columns([3, 2], gap="small")
            with col_a:
                p_name = st.text_input("Name", value=_inf_name,
                                       placeholder="e.g. Cream Linen Blazer", key="p_name")
            with col_b:
                p_color = st.text_input("Color", value=suggested_color_default, key="p_color")

            col_c, col_d = st.columns([1, 1], gap="small")
            with col_c:
                p_category = st.selectbox(
                    "Category", options=_CATEGORY_OPTIONS,
                    index=_safe_index(_CATEGORY_OPTIONS, _inf_cat),
                    key="p_category",
                )
            with col_d:
                p_formality = st.selectbox(
                    "Formality", options=_FORMALITY_OPTIONS,
                    index=_safe_index(_FORMALITY_OPTIONS, _inf_formality),
                    key="p_formality",
                )

            # Pre-select inferred seasons (only the ones that are in the option list).
            _default_seasons = [s for s in _inf_seasons if s in _SEASON_OPTIONS] or ["all"]
            p_seasons = st.multiselect(
                "Seasons (leave empty to mean year-round)",
                options=_SEASON_OPTIONS, default=_default_seasons, key="p_seasons",
            )
            _default_tags = [t for t in _inf_tags if t in _OCCASION_TAG_OPTIONS]
            p_tags = st.multiselect(
                "Suitable for these occasions",
                options=_OCCASION_TAG_OPTIONS,
                default=_default_tags,
                key="p_tags",
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

    # ── Items you've added (with edit + delete) ─────────────────
    overlay = get_user_wardrobe().get("user_wardrobe", {"clothing": [], "shoes": [], "accessories": []})
    user_rows = []
    for section in ("clothing", "shoes", "accessories"):
        for it in overlay.get(section, []):
            user_rows.append(it)

    if user_rows:
        st.markdown(
            '<div style="margin-top:1.4rem; margin-bottom:0.4rem; '
            'font-family:\'DM Serif Display\',serif; font-size:1.2rem; '
            'color:#1C1917; line-height:1.2;">Items you\'ve added</div>',
            unsafe_allow_html=True,
        )
        _render_user_items_list(user_rows)
    else:
        st.markdown(
            '<div style="margin-top:1.2rem; font-size:0.82rem; color:#6E6E73;">'
            "No items added yet. The seed wardrobe is already available to Wearly — adding pieces here grows the candidate pool."
            "</div>",
            unsafe_allow_html=True,
        )

    # The previous "Coming soon" chips listed features that are now all
    # shipped (photo upload, product link import, wear history, item
    # editing). Removed — keeping them would be misleading.




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

                # Single-line HTML — no per-line indentation, so Streamlit's
                # markdown parser doesn't treat the indented inner tags as a
                # code block when interpolated `</div>` / `<a>` content
                # appears.
                row_html = (
                    '<div style="background:#FFFFFF; border:1px solid #E5E5E5; '
                    'border-radius:6px; padding:0.85rem 1.05rem; margin-bottom:0.55rem;">'
                    '<div style="display:flex; align-items:baseline; gap:0.5rem; flex-wrap:wrap;">'
                    f'<span style="font-family:\'DM Serif Display\',serif; font-size:1.05rem; color:#1C1917;">{it.get("name","—")}</span>'
                    f'<span style="font-size:0.66rem; color:{pri_color}; letter-spacing:0.12em; text-transform:uppercase; font-weight:700;">{priority}</span>'
                    f'{linked}'
                    '</div>'
                    f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.3rem;">{meta}{source_link}</div>'
                    f'{notes_block}'
                    '</div>'
                )
                row_a, row_b = st.columns([5, 1], gap="small")
                with row_a:
                    st.markdown(row_html, unsafe_allow_html=True)
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

                # Same flat-HTML pattern as the wishlist row above —
                # no leading whitespace per line so the markdown parser
                # doesn't misinterpret interpolated tags.
                row_html = (
                    '<div style="background:#FFFFFF; border:1px solid #E5E5E5; '
                    'border-radius:6px; padding:0.85rem 1.05rem; margin-bottom:0.55rem;">'
                    f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.05rem; color:#1C1917;">{name}</div>'
                    f'<div style="font-size:0.78rem; color:#6E6E73; margin-top:0.2rem;">{url or "no link saved"}</div>'
                    f'{notes_block}'
                    '</div>'
                )
                row_a, row_b = st.columns([5, 1], gap="small")
                with row_a:
                    st.markdown(row_html, unsafe_allow_html=True)
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

def _render_measurement_analysis_panel(profile: dict, measurements: dict) -> None:
    """
    Always-visible Analyze panel. Surfaces R8-grounded styling
    suggestions when the user has shared bust + waist + hips; otherwise
    renders an empty state with a clear "add measurements below" CTA so
    the feature is discoverable without first having to save anything.

    Source basis: skills/wearly-styling-agent/fit-silhouette-rules.md
    §R8. Every suggestion carries the `[fit-silhouette-rules#R8]`
    citation; the slug is registered in `rule_refs.py`.

    Body-positive language contract (fit#R1) is enforced two ways:
      1. profile_inference uses only "highlight / balance / support"
         vocabulary.
      2. save_fit_profile() screens every value via
         check_value_for_forbidden_language() before persisting.
    """
    try:
        from profile_inference import (
            suggest_profile_from_measurements,
            apply_suggestions,
        )
        from fit_tool import save_fit_profile
    except Exception:
        # Defensive — the panel must never break the Profile page.
        return

    # Sufficiency check up front so we render the right state.
    _bwh = ("bust", "waist", "hips")
    _have = {k for k in _bwh
             if isinstance(measurements.get(k), (int, float))
             and measurements.get(k, 0) > 0}
    _ready_for_analysis = (_have == set(_bwh))
    _missing = [k for k in _bwh if k not in _have]

    # Card frame so the panel reads as a first-class section.
    st.markdown(
        '<div style="background:#FFFFFF; border:2px solid #111111; '
        'border-radius:8px; padding:1.5rem 1.6rem 1.3rem; margin-bottom:1.1rem; '
        'box-shadow:0 1px 0 rgba(0,0,0,0.04);">'
        '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; '
        'text-transform:uppercase; font-weight:600; margin-bottom:0.4rem;">'
        'Fit profile · testing lab</div>'
        '<div style="font-family:\'DM Serif Display\',serif; font-size:1.45rem; '
        'color:#111111; line-height:1.15; margin-bottom:0.4rem;">'
        'Analyze measurements and suggest styling profile'
        '</div>'
        '<div style="font-size:0.82rem; color:#2E2E2E; line-height:1.55;">'
        "Preference-based, not a diagnosis. Wearly maps your bust / waist / "
        "hip ratios to documented industry styling heuristics "
        "<code style='font-size:0.74rem;'>[fit-silhouette-rules#R8]</code> "
        "and shows the suggestions for your review. Nothing is saved unless "
        "you check a chip and click Apply."
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── EMPTY STATE: no bust/waist/hips yet ────────────────────────
    if not _ready_for_analysis:
        st.info(
            "**To unlock suggestions, share at least bust, waist, and "
            "hip measurements.** "
            f"Missing: {', '.join(_missing) if _missing else 'all three'}. "
            "Open *Edit your profile, preferences & measurements* below "
            "and fill in those fields — every measurement is optional "
            "and editable."
        )
        return

    # ── READY: button + result ─────────────────────────────────────
    btn_col, _spacer = st.columns([1, 2], gap="small")
    with btn_col:
        analyze_clicked = st.button(
            "Analyze measurements →",
            key="profile_analyze_btn",
            type="primary",
            use_container_width=True,
            help="Compute preference-based styling suggestions from "
                 "your measurements. Nothing is saved until you Apply.",
        )

    if analyze_clicked:
        st.session_state["_profile_inference_result"] = \
            suggest_profile_from_measurements(measurements, profile)

    result = st.session_state.get("_profile_inference_result")
    if not result or not result.get("available"):
        return

    suggestions = result.get("suggestions", {})

    # Per-field chips with a checkbox. Each chip shows: field name,
    # suggested value, confidence label, user-locked badge if already
    # set, plain-English reason, and the R8 citation.
    _CONF_COLOR = {"high": "#1D6033", "medium": "#7D5A00",
                   "low": "#7A1D21", "weak heuristic": "#7A1D21"}

    selected: list = []

    def _chip_row(field_key: str, label: str, sug: dict) -> bool:
        """Render one chip row; returns True if the checkbox is on."""
        value_str = sug.get("value")
        if not value_str:
            value_str = ", ".join(sug.get("values") or [])
        conf = sug.get("confidence", "medium")
        conf_color = _CONF_COLOR.get(conf, "#6E6E73")
        locked = sug.get("user_locked", False)
        current = sug.get("current")
        current_str = (
            current if isinstance(current, str)
            else (", ".join(current) if current else "—")
        )

        cols = st.columns([0.6, 5], gap="medium")
        with cols[0]:
            # Don't pre-check anything — the user must opt-in per chip.
            on = st.checkbox(
                " ", key=f"profile_sug_chk_{field_key}", value=False,
                label_visibility="collapsed",
            )
        with cols[1]:
            badge_html = (
                f'<span style="font-size:0.6rem; color:{conf_color}; '
                f'letter-spacing:0.08em; text-transform:uppercase; '
                f'font-weight:600; margin-left:0.6rem;">'
                f'{conf}</span>'
            )
            lock_html = (
                '<span style="font-size:0.6rem; color:#7D5A00; '
                'letter-spacing:0.08em; text-transform:uppercase; '
                'font-weight:600; margin-left:0.6rem;">'
                'YOU\'VE SET A VALUE</span>'
                if locked else ""
            )
            st.markdown(
                f'<div style="background:#FAFAFA; border:1px solid #EEEEEE; '
                f'border-radius:6px; padding:0.85rem 1.1rem; margin-bottom:0.6rem;">'
                f'<div style="display:flex; align-items:baseline; flex-wrap:wrap; gap:0.3rem;">'
                f'<span style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; '
                f'text-transform:uppercase; font-weight:600;">{label}</span>'
                f'{badge_html}{lock_html}'
                f'</div>'
                f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.25rem; '
                f'color:#111111; line-height:1.1; margin:0.35rem 0;">{value_str}</div>'
                f'<div style="font-size:0.76rem; color:#2E2E2E; line-height:1.5;">'
                f'{sug.get("reason", "")}</div>'
                f'<div style="font-size:0.7rem; color:#8E8E93; margin-top:0.45rem;">'
                f'Currently saved: <strong>{current_str}</strong> &nbsp;·&nbsp; '
                f'Source basis: <code style="font-size:0.7rem;">'
                f'[{sug.get("rule_ref","fit#R8").replace("#","-rules#")}]</code>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        return on

    field_labels = [
        ("body_shape",         "Body shape"),
        ("highlight_features", "Features you may choose to highlight"),
        ("balance_areas",      "Areas you may choose to balance"),
        ("preferred_fit",      "Preferred fit"),
    ]
    for fkey, flabel in field_labels:
        if fkey in suggestions:
            if _chip_row(fkey, flabel, suggestions[fkey]):
                selected.append(fkey)

    # Apply controls — the user must EXPLICITLY click Apply. Nothing is
    # saved by the checkboxes alone.
    apply_col, cancel_col, status_col = st.columns([1, 1, 4], gap="medium")
    with apply_col:
        apply_clicked = st.button(
            "Apply suggestions",
            key="profile_sug_apply_btn",
            type="primary",
            use_container_width=True,
            disabled=not selected,
            help=("Merge the checked suggestions into your profile. "
                  "Highlight / balance lists are unioned with your "
                  "existing choices; body_shape and preferred_fit "
                  "replace the current value if checked."),
        )
    with cancel_col:
        cancel_clicked = st.button(
            "Discard suggestions",
            key="profile_sug_cancel_btn",
            use_container_width=True,
            help="Close the panel without saving anything.",
        )

    if apply_clicked and selected:
        updates = apply_suggestions(profile, result, selected)
        if updates:
            res = save_fit_profile(updates)
            if res.get("success"):
                # Mark body_shape provenance as user-confirmed since the
                # user actively applied it.
                if "body_shape" in updates:
                    save_fit_profile({"_body_shape_source": "user"})
                st.session_state.pop("_profile_inference_result", None)
                st.success(
                    f"Applied {len(updates)} suggestion"
                    f"{'s' if len(updates) != 1 else ''} to your profile. "
                    "You can edit any field in the form below."
                )
                st.rerun()
            else:
                st.error(
                    f"Could not save: {res.get('error', 'unknown error')}."
                )
    elif cancel_clicked:
        st.session_state.pop("_profile_inference_result", None)
        st.rerun()


def _render_reset_fit_profile_panel(profile: dict) -> None:
    """
    "Reset fit profile test data" — a scoped destructive action that
    clears ONLY fit-profile fields (measurements, body_shape,
    preferred_fit, highlight_features, balance_areas) plus the cached
    inference. Wardrobe / wishlist / calendar / routine / wear history /
    favorite stores are intentionally outside this function's reach —
    the structural separation is documented in
    `fit_tool.reset_fit_profile_test_data`.

    The reset is two-step: first click flips a session flag, second
    click executes. A "Cancel" button always escapes.
    """
    try:
        from fit_tool import reset_fit_profile_test_data
    except Exception:
        return

    pending_key = "_reset_fit_profile_pending"
    pending = st.session_state.get(pending_key, False)

    # Only show the panel when there's something to reset — keeps the
    # Profile page calm for first-time users.
    has_anything = bool(
        profile.get("measurements") or profile.get("body_shape")
        or profile.get("preferred_fit") or profile.get("highlight_features")
        or profile.get("balance_areas")
    )
    if not has_anything and not pending:
        return

    if not pending:
        cols = st.columns([1, 3], gap="medium")
        with cols[0]:
            if st.button(
                "Reset fit profile test data",
                key="profile_reset_btn",
                use_container_width=True,
                help="Clears measurements, body shape, preferred fit, "
                     "highlight features, and balance areas. Wardrobe, "
                     "wishlist, calendar, routine, wear history, and "
                     "favorite stores are NOT touched.",
            ):
                st.session_state[pending_key] = True
                st.rerun()
        with cols[1]:
            st.markdown(
                "<div style='font-size:0.78rem; color:#6E6E73; "
                "line-height:1.55; padding-top:0.35rem;'>"
                "Resets <strong>only your fit profile and measurements</strong> — "
                "not your wardrobe, wishlist, calendar, routine, "
                "wear history, or favorite stores."
                "</div>",
                unsafe_allow_html=True,
            )
        return

    # Pending → confirmation step.
    st.warning(
        "**Confirm reset.** This will clear only your fit profile "
        "and measurements (body shape, preferred fit, highlight / "
        "balance areas, all measurements). Your wardrobe, wishlist, "
        "calendar, routine, wear history, and favorite stores will "
        "**not** be deleted."
    )
    cols = st.columns([1, 1, 3], gap="medium")
    with cols[0]:
        if st.button("Yes, reset", key="profile_reset_confirm_btn",
                     type="primary", use_container_width=True):
            r = reset_fit_profile_test_data()
            st.session_state[pending_key] = False
            st.session_state.pop("_profile_inference_result", None)
            if r.get("success"):
                st.success("Fit profile test data cleared.")
                st.rerun()
            else:
                st.error(f"Could not reset: {r.get('error', 'unknown error')}.")
    with cols[1]:
        if st.button("Cancel", key="profile_reset_cancel_btn",
                     use_container_width=True):
            st.session_state[pending_key] = False
            st.rerun()


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
        <div style="font-size:0.86rem; color:#6E6E73; margin-top:0.3rem;">Stored locally on this device. Every field is optional and editable.</div>
    </div>

    <div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; padding:1.4rem 1.6rem; margin-bottom:1.1rem;">
        <div style="display:flex; align-items:center; gap:1rem;">
            <div style="width:52px; height:52px; border-radius:50%; background:linear-gradient(135deg, #2E2E2E 0%, #111111 100%); color:#FFFFFF; display:flex; align-items:center; justify-content:center; font-family:'DM Serif Display',serif; font-size:1.5rem;">
                {initial}
            </div>
            <div style="font-family:'DM Serif Display',serif; font-size:1.45rem; color:#1C1917; line-height:1.1;">{name}</div>
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

    # ── Analyze measurements → preference-based styling suggestions ──
    # ALWAYS visible — has its own empty state so the user knows the
    # feature exists even before any measurements are saved. Surfaces
    # R8-grounded suggestions for body_shape / highlight / balance /
    # preferred_fit derived from bust + waist + hips.
    _meas = profile.get("measurements", {}) or {}
    _render_measurement_analysis_panel(profile, _meas)

    # ── Reset fit profile test data ──────────────────────────────
    # Clears ONLY fit-profile fields (measurements, body_shape,
    # preferred_fit, highlight_features, balance_areas) plus the
    # cached inference result. Wardrobe / wishlist / calendar / routine
    # / wear history / favorite stores are untouched.
    _render_reset_fit_profile_panel(profile)

    # ── Measurements card (renders only when at least one is saved) ──
    # Display unit comes from session state ("measure_unit"), set by the
    # toggle inside the edit form. Internal storage is always inches.
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

        # ── Predicted sizes by category + body-shape suggestion ─────
        # Runs only when at least bust / waist / hips is present.
        # Compared against The Sewing Revival's size-bundles chart.
        # Brands vary — honestly framed as a prediction, not a label.
        try:
            from fit_tool import (
                predict_sizes_by_category as _predict_cat,
                predict_body_shape as _predict_shape,
            )
            _sizes = _predict_cat(_meas)
            _shape_pred = _predict_shape(_meas)
        except Exception:
            _sizes, _shape_pred = {}, {}

        if _sizes:
            # Render one row of three category cards.
            _conf_color = lambda c: {"high": "#1D6033", "medium": "#7D5A00",
                                      "low": "#7A1D21"}.get(c, "#6E6E73")

            def _cat_block(label: str, rec: dict) -> str:
                if not rec:
                    return (
                        '<div style="flex:1; min-width:160px; padding:1rem 1.1rem; '
                        'background:#FAFAFA; border:1px solid #EEEEEE; border-radius:6px;">'
                        f'<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; '
                        f'text-transform:uppercase; margin-bottom:0.4rem;">{label}</div>'
                        '<div style="font-size:0.84rem; color:#8E8E93;">Add the relevant '
                        'measurement to see a size.</div></div>'
                    )
                return (
                    '<div style="flex:1; min-width:160px; padding:1rem 1.1rem; '
                    'background:#FFFFFF; border:1px solid #EEEEEE; border-radius:6px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:baseline;">'
                    f'<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.12em; '
                    f'text-transform:uppercase;">{label}</div>'
                    f'<div style="font-size:0.6rem; color:{_conf_color(rec.get("confidence","low"))}; '
                    f'letter-spacing:0.1em; text-transform:uppercase; font-weight:600;">'
                    f'{rec.get("confidence","—")}</div>'
                    f'</div>'
                    f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.55rem; '
                    f'color:#111111; line-height:1.1; margin:0.4rem 0;">{rec["bundle"]}</div>'
                    f'<div style="font-size:0.78rem; color:#2E2E2E; line-height:1.5;">'
                    f'NZ/AU/UK <strong>{rec["nz_au_uk"]}</strong>'
                    f' &nbsp;·&nbsp; EU <strong>{rec["europe"]}</strong>'
                    f' &nbsp;·&nbsp; US <strong>{rec["usa"]}</strong>'
                    f'</div>'
                    '</div>'
                )

            st.markdown(
                '<div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; '
                'padding:1.4rem 1.6rem; margin-bottom:1.1rem;">'
                '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; '
                'text-transform:uppercase; font-weight:600; margin-bottom:0.9rem;">'
                'Your sizes (predicted)</div>'
                '<div style="display:flex; gap:1rem; flex-wrap:wrap;">'
                + _cat_block("Tops",    _sizes.get("top"))
                + _cat_block("Bottoms", _sizes.get("bottom"))
                + _cat_block("Dresses", _sizes.get("dress"))
                + '</div>'
                '<div style="font-size:0.74rem; color:#8E8E93; margin-top:1rem; line-height:1.55;">'
                "Tops are matched on bust; bottoms on whichever of waist or hips is larger "
                "(sized up if needed); dresses on the largest of bust / waist / hips. "
                "Reference chart: "
                "<a href='https://thesewingrevival.com/pages/choosing-your-size' "
                "target='_blank' style='color:#111111;'>The Sewing Revival</a>. "
                "Brands vary — start here, then check the brand's own size guide."
                '</div></div>',
                unsafe_allow_html=True,
            )

        # ── Body-shape suggestion ────────────────────────────────
        # Surfaces the prediction even after the user has overridden it,
        # so the reasoning is always visible. The form's selectbox is the
        # field that actually drives the agent — this card is informative.
        if _shape_pred:
            _src = profile.get("_body_shape_source")
            _user_locked = (_src == "user")
            _shown_shape = (profile.get("body_shape") or _shape_pred["shape"]).title()
            _badge = "Your choice" if _user_locked else "Auto-filled from measurements"
            _badge_color = "#111111" if _user_locked else "#1D6033"
            st.markdown(
                '<div style="background:#FFFFFF; border:1px solid #E5E5E5; border-radius:6px; '
                'padding:1.4rem 1.6rem; margin-bottom:1.1rem;">'
                '<div style="display:flex; justify-content:space-between; align-items:baseline; '
                'margin-bottom:0.6rem;">'
                '<div style="font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; '
                'text-transform:uppercase; font-weight:600;">Body shape</div>'
                f'<div style="font-size:0.6rem; color:{_badge_color}; letter-spacing:0.1em; '
                f'text-transform:uppercase; font-weight:600;">{_badge}</div>'
                '</div>'
                f'<div style="font-family:\'DM Serif Display\',serif; font-size:1.6rem; '
                f'color:#111111; line-height:1.1; margin-bottom:0.4rem;">{_shown_shape}</div>'
                f'<div style="font-size:0.82rem; color:#2E2E2E; line-height:1.55;">'
                f'{_shape_pred["reason"]}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Edit form ─────────────────────────────────────────────────
    # Auto-expand when no measurements yet so the user immediately sees
    # WHERE to enter bust / waist / hips. After they've saved at least
    # one measurement the form collapses by default to keep the page
    # calm. Every field below is optional and stored locally only.
    measurements = profile.get("measurements", {}) or {}
    _expand_edit_form = not any(measurements.values())

    with st.expander("Edit your profile, preferences & measurements",
                     expanded=_expand_edit_form):
        st.markdown(
            "<div style='font-size:0.82rem; color:#6E6E73; "
            "line-height:1.55; margin-bottom:0.8rem;'>"
            "Every field is optional. Measurements are stored locally "
            "on this device. Body-positive language is enforced — "
            "corrective vocabulary is blocked by design."
            "</div>",
            unsafe_allow_html=True,
        )

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
            # Single "?" entry point at the heading level. Per-field
            # tooltips were dropped — the diagram inside the expander
            # serves the same purpose with less visual clutter.
            st.markdown(
                "<div style='display:flex; align-items:baseline; gap:0.6rem; "
                "margin:1.4rem 0 0.4rem;'>"
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600;'>"
                "Body measurements</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            with st.expander("?  How to measure", expanded=False):
                st.markdown(_measurement_diagram_svg(), unsafe_allow_html=True)

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
                        _initial = 0.0
                        if isinstance(_current_in, (int, float)) and _current_in:
                            _initial = float(_current_in) * (_IN2CM if _use_cm else 1.0)
                        _shown = st.number_input(
                            f"{_label} ({_unit_choice})",
                            min_value=0.0,
                            max_value=_max_input,
                            step=_step,
                            value=round(_initial, 1),
                            # No per-field help= — the single diagram
                            # expander above is the canonical reference.
                            key=f"measure_{_key}",
                        )
                        new_measurements[_key] = (
                            _shown / _IN2CM if _use_cm else _shown
                        )

            # ── Section 5: Timezone (locale setting) ─────────────
            # Drives how UTC-stamped calendar events (e.g. Google
            # Calendar's .ics export) are converted to local clock
            # time. Without this, Streamlit Cloud (server in UTC)
            # would display every event five hours off for a
            # Minneapolis user.
            st.markdown(
                "<div style='font-size:0.7rem; color:#8E8E93; letter-spacing:0.14em; "
                "text-transform:uppercase; font-weight:600; margin:1.4rem 0 0.4rem;'>"
                "Time zone</div>",
                unsafe_allow_html=True,
            )
            _TZ_OPTIONS = [
                "America/Chicago",      # Central — Minneapolis, Chicago, Dallas, Mexico City
                "America/New_York",     # Eastern — NYC, Boston, Toronto
                "America/Denver",       # Mountain — Denver, Salt Lake City
                "America/Los_Angeles",  # Pacific — LA, Seattle, Vancouver
                "America/Anchorage",    # Alaska
                "Pacific/Honolulu",     # Hawaii
                "America/Phoenix",      # Arizona (no DST)
                "America/Toronto",
                "America/Vancouver",
                "America/Mexico_City",
                "Europe/London",
                "Europe/Paris",
                "Europe/Berlin",
                "Europe/Athens",
                "Asia/Riyadh",          # Arabic timezone — relevant to the user base
                "Asia/Dubai",
                "Asia/Tokyo",
                "Asia/Singapore",
                "Australia/Sydney",
                "UTC",
            ]
            _current_tz = profile.get("timezone") or "America/Chicago"
            if _current_tz not in _TZ_OPTIONS:
                _TZ_OPTIONS = [_current_tz] + _TZ_OPTIONS
            new_timezone = st.selectbox(
                "Your time zone",
                options=_TZ_OPTIONS,
                index=_TZ_OPTIONS.index(_current_tz),
                help=(
                    "Calendar events from Google / Apple are stored in UTC and "
                    "converted to this zone for display. Pick the zone you live "
                    "in. Minneapolis is America/Chicago."
                ),
                label_visibility="collapsed",
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
                    "timezone":           new_timezone,
                }
                res = save_fit_profile(upd)
                if res.get("success"):
                    # If the timezone changed and there's a calendar
                    # subscription on file, re-sync immediately so
                    # the events repopulate in the new zone instead
                    # of staying stuck on the old one until the next
                    # auto-refresh.
                    _tz_changed = (
                        (profile.get("timezone") or "America/Chicago")
                        != new_timezone
                    )
                    if _tz_changed:
                        try:
                            from calendar_import import get_subscription, refresh_subscription
                            if get_subscription().get("url"):
                                with st.spinner("Re-syncing calendar to the new time zone…"):
                                    refresh_subscription(replace=True, timeout=10)
                                # Invalidate the per-event-plan cache
                                # so the Planner rebuilds with the
                                # newly-zoned times.
                                st.session_state.pop("planner_plans", None)
                        except Exception:
                            # Best-effort — profile save succeeded
                            # even if the resync didn't, and the
                            # next auto-refresh will catch up.
                            pass
                    st.success(
                        "Profile updated. Wearly will reflect these in your next outfit."
                    )
                    st.rerun()
                else:
                    st.error(f"Could not save: {res.get('error', 'unknown error')}")

    # ── Other settings (calendar + weekly routine) ────────────────
    # Moved below the fit-profile testing area so the Profile page
    # opens with the most-tested feature first.
    _render_calendar_import()
    _render_routine_editor()

    st.markdown(
        "<p style='font-size:0.74rem; color:#6E6E73; line-height:1.55; "
        "margin-top:1rem;'>"
        "<strong style='color:#6E6E73; letter-spacing:0.04em;'>Privacy.</strong> "
        "Your profile is stored locally in this prototype. Real authentication "
        "and cloud sync are future work."
        "</p>"
        "<div style='margin-top:1.2rem; padding-top:1rem; border-top:1px solid #EEEEEE;'>"
        "<div style='font-size:0.66rem; color:#8E8E93; letter-spacing:0.14em; "
        "text-transform:uppercase; font-weight:600; margin-bottom:0.5rem;'>"
        "Learn more</div>"
        "<p style='font-size:0.82rem; color:#2E2E2E; line-height:1.6;'>"
        "The <a href='https://eatedalsf.github.io/styling-agent/' target='_blank' "
        "style='color:#111111; text-decoration:underline;'>Wearly Intelligent Book</a> "
        "documents the design principles, evidence, skill rules, knowledge graph, "
        "and architecture."
        "</p></div>",
        unsafe_allow_html=True,
    )


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
            try:
                from graph_tool import legend_for_app as _legend
                with st.expander("What does this graph mean? (legend)",
                                 expanded=False):
                    st.markdown(_legend(), unsafe_allow_html=True)
            except Exception:
                pass
            st.caption(
                "Canonical source: `graph/graph.json` and `graph/schema.md`. "
                "Read more in the **Knowledge Graph** section of the "
                "[Intelligent Book](https://eatedalsf.github.io/styling-agent/). "
                "For library, layout, and node-size meanings, see "
                "`docs/knowledge-graph-faq.md`."
            )
        except ImportError as _e:
            st.info(f"Graph rendering unavailable: {_e}")
        except Exception as _e:
            st.warning(f"Graph could not render: {_e}")


# ─────────────────────────────────────────────
# SECTION ROUTER
# ─────────────────────────────────────────────

_router = {
    "home":         _render_home,
    "today":        _render_today,
    "planner":      _render_planner,
    "routine":      _render_routine_week,
    # Sub-route used by Planner / Routine "Plan in detail" buttons.
    # NOT in the top-nav list — the originating Planner or Routine
    # pill stays highlighted (see _nav_active above _SECTIONS).
    "event_detail": _render_event_detail,
    "wardrobe":     _render_wardrobe,
    "shop":         _render_shop,
    "profile":      _render_profile,
    "demo":         _render_demo,
}
_router.get(st.session_state["section"], _render_home)()
