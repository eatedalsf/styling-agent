"""
Tool 5: Wear History

Tracks how many times each wardrobe item has been worn and when last,
so the agent can choose fresher items when multiple candidates are
equally eligible. This is a TIE-BREAKER, never a filter — much-loved
pieces are always allowed (the freshness floor is 0.4, never 0).

Data file: wear_history.json at the repo root, alongside wardrobe.json.
Shape:
    {
      "_comment": "...",
      "history": {
        "C001": {"worn_count": 3, "last_worn_date": "2026-05-12",
                 "last_event": "Team Strategy Meeting"},
        ...
      }
    }

The file is created lazily on first save. Reads tolerate missing or
malformed files by falling back to an empty history (never raises).
Writes are atomic (temp-file + rename) so a crash mid-write can't
leave the file half-written.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime


def _history_path() -> str:
    """
    Return the path to wear_history.json. Looks in a `data/` subfolder
    first (for a future restructure), then alongside this module.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", "wear_history.json"),
        os.path.join(here, "wear_history.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, "wear_history.json")


HISTORY_PATH = _history_path()


def _atomic_write_json(path: str, data: dict) -> None:
    """Write `data` as JSON to `path` via temp-file + rename."""
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".wear_history_", suffix=".json", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def get_history() -> dict:
    """
    Load the wear-history map. Tolerant of missing or malformed files.

    Returns:
        {"success": True, "history": {<id>: <entry>}, "error": None}
    """
    if not os.path.exists(HISTORY_PATH):
        return {"success": True, "history": {}, "error": None}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "history": dict(data.get("history", {})), "error": None}
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": True,
            "history": {},
            "error": f"wear_history.json unreadable ({e}); using empty history.",
        }


def record_wear(item_ids: list, event_name: str = None, when: str = None) -> dict:
    """
    Increment worn_count and update last_worn_date for each item in the list.

    item_ids:    list of wardrobe item IDs (e.g. ["C001", "C006"])
    event_name:  optional event/occasion label to record on each entry
    when:        ISO date string (YYYY-MM-DD); defaults to today

    Returns: {success, history, recorded_count, error}
    """
    when = when or date.today().isoformat()

    result = get_history()
    history = result["history"]

    recorded = 0
    for iid in (item_ids or []):
        if not iid:
            continue
        entry = history.get(iid, {"worn_count": 0, "last_worn_date": None, "last_event": None})
        entry["worn_count"] = int(entry.get("worn_count", 0)) + 1
        entry["last_worn_date"] = when
        if event_name:
            entry["last_event"] = event_name
        history[iid] = entry
        recorded += 1

    on_disk = {
        "_comment": "Wear history. Created and updated when the user confirms an outfit.",
        "history": history,
    }
    try:
        _atomic_write_json(HISTORY_PATH, on_disk)
    except Exception as e:
        return {"success": False, "history": history, "recorded_count": 0, "error": f"Failed to save wear history: {e}"}

    return {"success": True, "history": history, "recorded_count": recorded, "error": None}


def get_freshness(item_id: str, history: dict = None, today: date = None) -> float:
    """
    Return a freshness score in [0.4, 1.0] for an item.

      1.0  never worn — first choice all else equal
     ~0.94 worn once, but a long time ago
     ~0.75 worn 4+ times, but a long time ago
     ~0.50 worn 4+ times recently
      0.4  floor — even the most-worn piece is still eligible

    This is a TIE-BREAKER for the agent, not a filter. A "much-loved"
    piece never gets exiled; it just yields to a fresher equivalent
    when one exists. See skills/wearly-styling-agent/wear-history-rules.md.
    """
    if not item_id:
        return 1.0
    if history is None:
        history = get_history().get("history", {})

    entry = history.get(item_id)
    if not entry:
        return 1.0

    freshness = 1.0

    # Frequency penalty: up to -0.25 once worn_count reaches 4+.
    worn_count = int(entry.get("worn_count", 0) or 0)
    if worn_count >= 1:
        freshness -= 0.25 * min(worn_count, 4) / 4

    # Recency penalty: -0.25 if worn in the last 3 days.
    last_worn = entry.get("last_worn_date")
    if last_worn:
        try:
            d = datetime.fromisoformat(last_worn).date()
            t = today or date.today()
            if (t - d).days < 3:
                freshness -= 0.25
        except (ValueError, TypeError):
            pass

    return max(0.4, min(1.0, freshness))


def days_since_last_worn(item_id: str, history: dict = None, today: date = None) -> int | None:
    """Return days since item was last worn, or None if it has no history."""
    if history is None:
        history = get_history().get("history", {})
    entry = history.get(item_id)
    if not entry or not entry.get("last_worn_date"):
        return None
    try:
        d = datetime.fromisoformat(entry["last_worn_date"]).date()
        t = today or date.today()
        return (t - d).days
    except (ValueError, TypeError):
        return None


def reset_history() -> dict:
    """Test/debug helper: clear all history entries."""
    on_disk = {
        "_comment": "Wear history. Created and updated when the user confirms an outfit.",
        "history": {},
    }
    try:
        _atomic_write_json(HISTORY_PATH, on_disk)
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
