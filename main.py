"""
main.py — Wearly AI CLI Runner
Run this file to use Wearly AI from the command line.

Usage:
  python main.py                          → reads next calendar event
  python main.py --everyday "gym"         → everyday request
  python main.py --everyday "work"
  python main.py --compare                → runs before/after comparison demo
"""

import sys
import os
import argparse

# Force UTF-8 on stdout/stderr so the box-drawing characters and emoji used
# below don't crash on Windows consoles using legacy codepages (cp1256, cp1252).
# reconfigure() exists on Python 3.7+ TextIOWrapper streams; if the stream
# can't be reconfigured (e.g. redirected to a non-text wrapper), fail silent.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Support both the current flat layout (styling_agent.py at repo root)
# and the older structured layout (agent/styling_agent.py).
try:
    from agent.styling_agent import run_agent
except ModuleNotFoundError:
    from styling_agent import run_agent


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

DIVIDER = "─" * 60
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 60}{RESET}\n")


def print_section(title: str):
    print(f"\n{BOLD}{title}{RESET}")
    print(DIVIDER)


def format_item(item: dict) -> str:
    return f"  • {item['name']} ({item.get('color', '')})"


def display_result(result: dict):
    """Pretty-prints a full agent result."""

    if result.get("error"):
        print(f"{RED}Agent Error: {result['error']}{RESET}")
        return

    event = result.get("event", {})
    weather = result.get("weather", {})
    outfit = result.get("recommendation", [])
    steps = result.get("steps", [])
    reasoning = result.get("reasoning", [])
    gaps = result.get("gaps", [])
    shopping = result.get("shopping_suggestions", [])
    color = result.get("color_score", {})

    # ── Event Context ──
    print_section("📅  OCCASION")
    print(f"  Event:    {event.get('title', 'N/A')}")
    print(f"  Date:     {event.get('date', 'N/A')}  {event.get('time', '')}")
    print(f"  Type:     {event.get('type', 'N/A').upper()}")
    if event.get("notes"):
        print(f"  Notes:    {event['notes']}")

    # ── Weather ──
    print_section("🌤  WEATHER")
    if weather:
        print(f"  {weather.get('city')}: {weather.get('temp_f')}°F, {weather.get('condition')}")
        print(f"  Feels like: {weather.get('feels_like_f')}°F  |  Wind: {weather.get('wind_mph')} mph")
        print(f"  Rain chance: {weather.get('precip_chance_pct')}%")
        print(f"  Advice: {weather.get('layer_advice')}")

    # ── Agent Steps ──
    print_section("⚙️   AGENT WORKFLOW STEPS")
    for s in steps:
        status_icon = GREEN + "✓" + RESET if s["status"] == "ok" else YELLOW + "⚠" + RESET
        print(f"  Step {s['step']} [{status_icon}] {s['name']}")
        print(f"        → {s['output']}")

    # ── Outfit ──
    print_section("👗  YOUR OUTFIT RECOMMENDATION")
    if outfit:
        for item in outfit:
            print(format_item(item))
    else:
        print("  No outfit could be built. Check wardrobe data.")

    # ── Color Score ──
    if color:
        score = color.get("score", 0)
        score_color = GREEN if score >= 70 else YELLOW if score >= 50 else RED
        print(f"\n  Color harmony score: {score_color}{score}/100{RESET}")

    # ── Gaps & Shopping ──
    if gaps:
        print_section("🛍  WARDROBE GAPS & SHOPPING SUGGESTIONS")
        print(f"  Missing: {', '.join(gaps)}")
        for s in shopping:
            print(f"  → {s}")

    # ── Reasoning ──
    print_section("💡  WHY THIS OUTFIT (Agent Reasoning)")
    for i, reason in enumerate(reasoning, 1):
        if reason.strip():
            print(f"  {i}. {reason}")


def print_before_after():
    """Prints a side-by-side before/after comparison."""
    print_header("BEFORE / AFTER COMPARISON DEMO")

    print(f"{BOLD}BEFORE: Manual Outfit Planning (No Agent){RESET}")
    print(DIVIDER)
    print("""  The user checks their phone calendar to see what's happening today.
  They walk to their closet and look around for a few minutes.
  They're not sure if the terracotta blouse works for a client dinner.
  They forget to check the weather — and step outside underdressed.
  They spend ~15 minutes deciding, and still feel uncertain.
  Time spent: ~15 minutes. Confidence: low. Missed the coat.
""")

    print(f"{BOLD}AFTER: Wearly AI{RESET}")
    print(DIVIDER)
    print("""  Agent reads the calendar → finds "Dinner with Clients" tonight.
  Agent checks real-time weather → 49°F, partly cloudy.
  Agent filters wardrobe by occasion (dinner) and season (spring).
  Agent selects: Terracotta Silk Blouse + Black Tailored Trousers +
    Black Pointed-Toe Heels + Gold Hoop Earrings + Black Trench Coat.
  Agent checks color harmony → terracotta scores excellent for warm olive skin.
  Agent explains every decision. No gaps found.
  Time spent: ~3 seconds. Confidence: high. Coat included.
""")

    print(f"{BOLD}  Delta:{RESET} 15 min → 3 sec | Manual guessing → Structured, reasoned recommendation")
    print(f"  Outfit is personalized, weather-aware, color-checked, and fully explainable.\n")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Wearly AI — Personal Styling Agent")
    parser.add_argument("--everyday", type=str, help='Everyday request, e.g. "gym" or "work"')
    parser.add_argument("--compare", action="store_true", help="Show before/after comparison demo")
    args = parser.parse_args()

    if args.compare:
        print_before_after()
        print("\nNow running a live calendar-based recommendation:\n")
        result = run_agent(mode="calendar")
        print_header("WEARLY AI — LIVE RUN")
        display_result(result)

    elif args.everyday:
        print_header(f"WEARLY AI — Everyday: {args.everyday.upper()}")
        result = run_agent(mode="everyday", everyday_request=args.everyday)
        display_result(result)

    else:
        print_header("WEARLY AI — Calendar Mode")
        result = run_agent(mode="calendar")
        display_result(result)


if __name__ == "__main__":
    main()
