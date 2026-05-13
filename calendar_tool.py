"""
Tool 1: Calendar Reader
Reads upcoming events from the mock calendar data file.
In a real system this would connect to Google Calendar or Outlook API.
"""

import json
import os
from datetime import datetime


def _find_data_file(filename):
    """Locate a data file in either structured (data/) or flat layout."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "data", filename),   # structured: tools/../data/
        os.path.join(here, "..", filename),            # flat: sibling of everything
        os.path.join(here, filename),                  # flat: same dir as tool
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]  # will raise clear FileNotFoundError


DATA_PATH = _find_data_file("calendar_events.json")
SEED_DATA_PATH = _find_data_file("seed_calendar_events.json")


def _load_calendar_events(seed_fallback: bool = True) -> list:
    """
    Read events from the user's own calendar file.

    When `seed_fallback=True` (default), falls back to the bundled
    seed demo events if the user file is missing or empty — so a
    fresh Streamlit Cloud container shows a populated demo calendar
    to public reviewers, and the Today / everyday flows never crash
    for a first-time visitor.

    When `seed_fallback=False`, the seed is never consulted: the
    function returns only what the user has actually imported via
    .ics or URL subscription. The Planner uses this mode so it never
    shows fabricated events.

    Returns [] on unrecoverable errors. Never raises.
    """
    # Path 1: the user's own events (created by the .ics importer and
    # the URL-subscription refresh).
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass

    # Path 2: seed demo events (Today / everyday fallback only).
    if seed_fallback and os.path.exists(SEED_DATA_PATH):
        try:
            with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    return []


def has_real_calendar_events() -> bool:
    """
    True iff the user has an actual, non-empty calendar_events.json on
    disk (from .ics import or URL subscription). Distinguishes a real
    calendar connection from "we have nothing but the demo seed."

    The Planner uses this to decide between rendering its weekly /
    monthly / all-upcoming tabs vs. showing the "Connect your
    calendar" empty state.
    """
    return bool(_load_calendar_events(seed_fallback=False))


def get_upcoming_events(days_ahead: int = 7, seed_fallback: bool = True) -> dict:
    """
    Reads upcoming calendar events within the next N days.
    Returns a dict with 'success', 'events', and 'error' keys.

    By default falls back to the bundled `seed_calendar_events.json`
    when no user-imported calendar exists, so the Today and everyday
    flows always have something to reason about.

    Pass `seed_fallback=False` to get a *real-calendar-only* view —
    used by the Planner, which must never display fabricated events.
    """
    all_events = _load_calendar_events(seed_fallback=seed_fallback)
    if not all_events:
        msg = (
            "No real calendar events found. Connect a calendar via "
            "Profile -> Connect your calendar to populate this view."
            if not seed_fallback
            else "Calendar data file not found."
        )
        return {"success": False, "events": [], "error": msg}

    today = datetime.today().date()
    upcoming = []
    for event in all_events:
        try:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
            delta = (event_date - today).days
            if 0 <= delta <= days_ahead:
                event["days_from_now"] = delta
                upcoming.append(event)
        except ValueError:
            continue

    upcoming.sort(key=lambda e: e["date"])

    if not upcoming:
        return {
            "success": True,
            "events": [],
            "error": None,
            "message": f"No events found in the next {days_ahead} days."
        }

    return {"success": True, "events": upcoming, "error": None}


def get_event_by_id(event_id: str) -> dict:
    """Fetch a single event by its ID."""
    try:
        with open(DATA_PATH, "r") as f:
            all_events = json.load(f)
    except Exception as e:
        return {"success": False, "event": None, "error": str(e)}

    for event in all_events:
        if event["id"] == event_id:
            return {"success": True, "event": event, "error": None}

    return {"success": False, "event": None, "error": f"Event {event_id} not found."}
