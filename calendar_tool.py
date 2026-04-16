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


def get_upcoming_events(days_ahead: int = 7) -> dict:
    """
    Reads upcoming calendar events within the next N days.
    Returns a dict with 'success', 'events', and 'error' keys.
    """
    try:
        with open(DATA_PATH, "r") as f:
            all_events = json.load(f)
    except FileNotFoundError:
        return {"success": False, "events": [], "error": "Calendar data file not found."}
    except json.JSONDecodeError:
        return {"success": False, "events": [], "error": "Calendar data is malformed."}

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
