"""
Tool 1: Calendar Reader
Reads upcoming events from the mock calendar data file.
In a real system this would connect to Google Calendar or Outlook API.
"""

import json
import os
from datetime import datetime


DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "calendar_events.json")


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
            continue  # Skip events with bad date formats

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
