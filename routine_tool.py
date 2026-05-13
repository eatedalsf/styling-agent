"""
routine_tool.py — the user's weekly routine.

A routine is a structured weekly schedule the agent falls back to when
the calendar has no specific event for the current moment. It mirrors
the "what do you usually do at this time?" mental model.

Schema (routine.json):

    {
      "schedule": {
        "monday":    [{"start": "07:00", "end": "08:00",
                       "occasion": "gym",  "label": "Morning workout"},
                      {"start": "09:00", "end": "17:00",
                       "occasion": "work", "label": "Office"}],
        "tuesday":   [...],
        ...
        "sunday":    [...]
      }
    }

Time strings are 24-hour "HH:MM". Occasion is one of the five canonical
tags Wearly recognises (work, gym, dinner, formal, casual). Label is a
free-text descriptor surfaced in the UI and the reasoning trail.

The agent only consults the routine when no calendar event is active —
it is a graceful default, never an override. Body-positive framing:
the routine describes the rhythm of your week, never prescribes it.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, time
from typing import List, Dict, Optional


def _find_data_file(filename: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "data", filename),
        os.path.join(here, "..", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]


ROUTINE_PATH = _find_data_file("routine.json")


DAYS = ["monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday"]


VALID_OCCASIONS = {"work", "gym", "dinner", "formal", "casual"}


_EMPTY_SCHEDULE = {d: [] for d in DAYS}


def _parse_hhmm(s: str) -> Optional[time]:
    """Parse 'HH:MM' (24-hour) to a datetime.time. Returns None on failure."""
    if not isinstance(s, str) or len(s) < 4:
        return None
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except (ValueError, IndexError):
        return None


def get_routine() -> dict:
    """
    Read routine.json. Always returns a fully-populated schedule dict
    (every weekday key present, even if empty), so callers can read
    without guarding.
    """
    schedule = dict(_EMPTY_SCHEDULE)
    schedule = {d: [] for d in DAYS}  # fresh copy
    if not os.path.exists(ROUTINE_PATH):
        return {"success": True, "schedule": schedule, "error": None}
    try:
        with open(ROUTINE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"success": False, "schedule": schedule, "error": str(e)}

    on_disk = data.get("schedule", {}) if isinstance(data, dict) else {}
    for d in DAYS:
        blocks = on_disk.get(d, []) or []
        # Defensive normalisation: drop malformed entries silently.
        out_blocks = []
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            start = blk.get("start")
            end   = blk.get("end")
            occ   = (blk.get("occasion") or "").lower()
            if not (_parse_hhmm(start) and _parse_hhmm(end)):
                continue
            if occ not in VALID_OCCASIONS:
                occ = "casual"
            out_blocks.append({
                "start":    start,
                "end":      end,
                "occasion": occ,
                "label":    (blk.get("label") or "").strip(),
            })
        # Sort blocks within a day by start time.
        out_blocks.sort(key=lambda b: b["start"])
        schedule[d] = out_blocks
    return {"success": True, "schedule": schedule, "error": None}


def _atomic_write(path: str, data: dict) -> None:
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".routine_", suffix=".json", dir=dir_)
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


def save_routine(schedule: dict) -> dict:
    """
    Persist a full weekly schedule. `schedule` must be a dict keyed by
    weekday name (lower-case) containing lists of {start, end, occasion,
    label} entries. Times are 'HH:MM'.

    Malformed blocks are silently dropped. Times where end <= start are
    rejected with an error so the user can fix the input.
    """
    if not isinstance(schedule, dict):
        return {"success": False, "error": "Schedule must be a dict."}

    cleaned: Dict[str, List[Dict]] = {d: [] for d in DAYS}
    for d in DAYS:
        for blk in (schedule.get(d) or []):
            if not isinstance(blk, dict):
                continue
            start = (blk.get("start") or "").strip()
            end   = (blk.get("end") or "").strip()
            occ   = (blk.get("occasion") or "").lower().strip()
            label = (blk.get("label") or "").strip()
            t_s = _parse_hhmm(start)
            t_e = _parse_hhmm(end)
            if not (t_s and t_e):
                continue
            if t_e <= t_s:
                return {"success": False,
                        "error": f"On {d.title()}, the '{label or occ}' block "
                                 f"ends at or before it starts ({start}–{end})."}
            if occ not in VALID_OCCASIONS:
                occ = "casual"
            cleaned[d].append({
                "start":    start,
                "end":      end,
                "occasion": occ,
                "label":    label,
            })
        cleaned[d].sort(key=lambda b: b["start"])

    on_disk = {
        "_comment": "User's weekly routine. The agent falls back to this "
                    "when the calendar has no event for the current time.",
        "schedule": cleaned,
    }
    try:
        _atomic_write(ROUTINE_PATH, on_disk)
    except Exception as e:
        return {"success": False, "error": f"Failed to save: {e}"}
    return {"success": True, "error": None}


def get_block_for_now(now: Optional[datetime] = None) -> Optional[Dict]:
    """
    Return the routine block that covers `now` (defaults to datetime.now()).
    Returns None if no block matches or no routine exists.

    Result shape (or None)::

        {
          "weekday":  "tuesday",
          "start":    "07:00",
          "end":      "08:00",
          "occasion": "gym",
          "label":    "Morning workout",
        }
    """
    if now is None:
        now = datetime.now()
    weekday = DAYS[now.weekday()]
    cur_t = now.time()

    res = get_routine()
    schedule = res.get("schedule") or {}
    for blk in schedule.get(weekday, []):
        t_s = _parse_hhmm(blk["start"])
        t_e = _parse_hhmm(blk["end"])
        if t_s and t_e and t_s <= cur_t < t_e:
            return {
                "weekday":  weekday,
                "start":    blk["start"],
                "end":      blk["end"],
                "occasion": blk["occasion"],
                "label":    blk["label"],
            }
    return None


def get_block_for_date(date_str: str, time_str: Optional[str] = None) -> Optional[Dict]:
    """
    Look up a routine block for an arbitrary date (and optional time).
    Used by the agent to pre-plan tomorrow's outfit when the calendar
    is empty. `date_str` is "YYYY-MM-DD"; `time_str` is "HH:MM" or None
    (None defaults to noon — a reasonable midday slot).
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    t = _parse_hhmm(time_str) if time_str else time(12, 0)
    if not t:
        t = time(12, 0)
    return get_block_for_now(datetime.combine(d.date(), t))
