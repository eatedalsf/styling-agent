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


def _load_calendar_events() -> list:
    """
    Read events from the user's own calendar file. Falls back to the
    seed demo events ONLY when the user file is missing or empty —
    so a fresh Streamlit Cloud container shows a populated demo
    calendar to public reviewers, but a real user with an imported
    calendar always sees ONLY their own events.

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

    # Path 2: seed demo events for the first-time / public-reviewer case.
    if os.path.exists(SEED_DATA_PATH):
        try:
            with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass

    return []


def get_upcoming_events(days_ahead: int = 7) -> dict:
    """
    Reads upcoming calendar events within the next N days.
    Returns a dict with 'success', 'events', and 'error' keys.

    Reads from the user's calendar_events.json (created when they
    import an .ics or subscribe to a calendar URL). Falls back to the
    bundled seed_calendar_events.json so the public demo deploy is
    never empty.
    """
    all_events = _load_calendar_events()
    if not all_events:
        return {"success": False, "events": [], "error": "Calendar data file not found."}

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
