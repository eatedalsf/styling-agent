"""
routine_tool.py — the user's weekly routine.

A routine is a set of recurring weekly activities the agent falls
back to when the calendar has no specific event for the current
moment. It mirrors the "what do you usually do at this time?"
mental model.

DATA MODEL — current canonical schema (routine.json):

    {
      "activities": [
        {
          "id":       "R001",
          "name":     "Morning gym",
          "occasion": "gym",
          "days":     ["monday", "wednesday"],
          "start":    "07:00",     # HH:MM 24-hour internally
          "end":      "08:00",
          "location": "gym",       # free-form text
          "note":     ""
        },
        ...
      ]
    }

Each activity recurs on the days listed in `days`. A single activity
can cover multiple days (Mon + Wed gym). The SAME activity name can
also exist as multiple entries with different days/times (Gym Mon
7 AM + Gym Tue 6 PM).

LEGACY SCHEMA — the old per-day blocks:

    {"schedule": {"monday": [{start, end, occasion, label}, ...],
                  "tuesday": [...], ...}}

Files in that shape are AUTO-MIGRATED on read: each block becomes a
single-day activity. The user never sees the migration; the
`activities` view is the new source of truth.

PUBLIC API
  get_routine()        → {success, activities, schedule, error}
  add_activity(fields) → {success, activity, error}
  remove_activity(id)  → {success, error}
  update_activity(id, fields)
                       → {success, activity, error}
  get_block_for_now(now=None)
                       → {weekday, start, end, occasion, label,
                          location, note} or None
  get_block_for_date(date_str, time_str=None)
                       → same shape as above, or None

OCCASION TAGS recognised: work, gym, dinner, formal, casual.
Anything else normalises to "casual".

DAY GROUP SHORTCUTS the UI may pass into `days`:
  "weekdays" → mon..fri
  "weekends" → sat, sun
  "every_day"/"daily"/"all" → all 7 days
These are expanded to individual day names at write time so the
on-disk shape stays flat and predictable.

The agent only consults the routine when no calendar event is active —
it is a graceful default, never an override. Body-positive framing:
the routine describes the rhythm of your week, never prescribes it.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, time
from typing import List, Dict, Optional, Iterable


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

# Group shortcuts the UI / API may pass instead of a literal day list.
_DAY_GROUPS = {
    "weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "weekday":  ["monday", "tuesday", "wednesday", "thursday", "friday"],
    "weekends": ["saturday", "sunday"],
    "weekend":  ["saturday", "sunday"],
    "every_day": list(DAYS),
    "everyday":  list(DAYS),
    "daily":     list(DAYS),
    "all":       list(DAYS),
}

# Keyword → occasion mapping. Used when the user names an activity
# but doesn't pick an occasion explicitly — we infer from the name.
_NAME_TO_OCCASION = [
    (("gym", "workout", "exercise", "run", "running", "yoga", "pilates",
      "spin", "fitness"), "gym"),
    (("work", "office", "meeting", "remote work", "wfh", "deep work"),
     "work"),
    (("class", "campus", "lecture", "lab", "school"),  "work"),
    (("dinner", "restaurant", "date night", "happy hour"), "dinner"),
    (("formal", "gala", "wedding", "ceremony"), "formal"),
    (("errand", "errands", "grocery", "shopping", "walk", "park",
      "brunch", "casual"), "casual"),
]


def _parse_hhmm(s: str) -> Optional[time]:
    """Parse 'HH:MM' (24-hour) to a datetime.time. Returns None on failure."""
    if not isinstance(s, str) or len(s) < 4:
        return None
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except (ValueError, IndexError):
        return None


def parse_time_input(s: str) -> Optional[str]:
    """
    Parse a user-supplied time string and return canonical "HH:MM"
    24-hour form, or None when unparseable.

    Accepts:
      "07:00"      → "07:00"
      "7:00 AM"    → "07:00"
      "7am"        → "07:00"
      "7"          → "07:00"
      "12 PM"      → "12:00"
      "6:30 PM"    → "18:30"
      "9.30 pm"    → "21:30"   (dot separator tolerated)
    """
    if not isinstance(s, str):
        return None
    raw = s.strip().lower()
    if not raw:
        return None
    # Detect AM/PM marker (and strip).
    suffix = None
    if raw.endswith("am") or raw.endswith("a.m.") or raw.endswith("a"):
        suffix = "am"
    elif raw.endswith("pm") or raw.endswith("p.m.") or raw.endswith("p"):
        suffix = "pm"
    cleaned = re.sub(r"[\s.]*(a\.?m\.?|p\.?m\.?)\s*$", "", raw)
    cleaned = cleaned.replace(".", ":").strip()

    # Now expect HH[:MM]
    m = re.match(r"^(\d{1,2})(?::(\d{1,2}))?$", cleaned)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2)) if m.group(2) else 0
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        # Allow 1..12 with a suffix.
        if suffix and 1 <= hh <= 12 and 0 <= mm <= 59:
            pass
        else:
            return None

    if suffix == "am":
        if hh == 12:
            hh = 0
    elif suffix == "pm":
        if hh != 12:
            hh = hh + 12
    if not (0 <= hh <= 23):
        return None
    return f"{hh:02d}:{mm:02d}"


def format_time_12h(s: str) -> str:
    """Render an "HH:MM" 24-hour string as "h:MM AM/PM". Empty input
    returns empty string; unparseable returns input as-is."""
    if not s:
        return ""
    t = _parse_hhmm(s)
    if not t:
        return s
    hour12 = t.hour % 12 or 12
    suf = "AM" if t.hour < 12 else "PM"
    return f"{hour12}:{t.minute:02d} {suf}"


def _normalize_days(value) -> List[str]:
    """
    Accept any of:
      - a list of day names or group names ["mon", "wednesday", "weekends"]
      - a single string "monday", "weekdays", "every_day"
    Return a deduped, ordered list of canonical day names.
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    out: List[str] = []
    seen = set()
    for entry in value:
        if not entry:
            continue
        token = str(entry).strip().lower().replace(" ", "_")
        # Allow 3-letter day abbreviations.
        abbrev = {
            "mon": "monday", "tue": "tuesday", "tues": "tuesday",
            "wed": "wednesday", "thu": "thursday", "thur": "thursday",
            "thurs": "thursday", "fri": "friday",
            "sat": "saturday", "sun": "sunday",
        }
        token = abbrev.get(token, token)
        if token in _DAY_GROUPS:
            for d in _DAY_GROUPS[token]:
                if d not in seen:
                    seen.add(d)
                    out.append(d)
        elif token in DAYS:
            if token not in seen:
                seen.add(token)
                out.append(token)
        # Anything else is silently dropped — the UI should never
        # send unknown values, but we stay defensive.
    return out


def _infer_occasion(name: str) -> str:
    """Return one of VALID_OCCASIONS by inspecting the activity name."""
    if not name:
        return "casual"
    low = name.lower()
    for keywords, occ in _NAME_TO_OCCASION:
        for kw in keywords:
            if kw in low:
                return occ
    return "casual"


def _next_activity_id(activities: List[Dict]) -> str:
    """Generate the next R### id, gap-tolerant."""
    used = []
    for a in activities or []:
        aid = str(a.get("id") or "")
        m = re.match(r"^R(\d+)$", aid)
        if m:
            used.append(int(m.group(1)))
    nxt = (max(used) + 1) if used else 1
    return f"R{nxt:03d}"


def _migrate_schedule_to_activities(schedule: Dict) -> List[Dict]:
    """
    Convert a legacy {day: [block, ...]} schedule into a flat
    activities list. Each block becomes one single-day activity so
    no data is lost. Called once on first read of an old file.
    """
    out: List[Dict] = []
    if not isinstance(schedule, dict):
        return out
    for day in DAYS:
        for blk in (schedule.get(day) or []):
            if not isinstance(blk, dict):
                continue
            start = blk.get("start")
            end   = blk.get("end")
            if not (_parse_hhmm(start) and _parse_hhmm(end)):
                continue
            occ = (blk.get("occasion") or "casual").lower()
            if occ not in VALID_OCCASIONS:
                occ = "casual"
            label = (blk.get("label") or "").strip()
            out.append({
                "id":       _next_activity_id(out),
                "name":     label or occ.title(),
                "occasion": occ,
                "days":     [day],
                "start":    start,
                "end":      end,
                "location": "",
                "note":     "",
            })
    return out


def _activities_to_schedule(activities: List[Dict]) -> Dict[str, List[Dict]]:
    """Expand the flat activities list into a per-day schedule for
    callers that want the old shape (the agent's `get_block_for_now`
    uses this internally)."""
    schedule: Dict[str, List[Dict]] = {d: [] for d in DAYS}
    for a in activities or []:
        days = _normalize_days(a.get("days") or [])
        if not days:
            continue
        for d in days:
            schedule[d].append({
                "start":    a.get("start"),
                "end":      a.get("end"),
                "occasion": a.get("occasion") or "casual",
                "label":    a.get("name") or "",
                "location": a.get("location") or "",
                "note":     a.get("note") or "",
                "id":       a.get("id"),
            })
    for d in DAYS:
        schedule[d].sort(key=lambda b: (b.get("start") or "00:00"))
    return schedule


def get_routine() -> dict:
    """
    Read routine.json.

    Returns:
        {
          "success":    bool,
          "activities": [...],          # flat list, the canonical shape
          "schedule":   {day: [...]},   # derived per-day view for the agent
          "error":      str | None,
        }
    """
    activities: List[Dict] = []
    if not os.path.exists(ROUTINE_PATH):
        return {
            "success":    True,
            "activities": [],
            "schedule":   {d: [] for d in DAYS},
            "error":      None,
        }
    try:
        with open(ROUTINE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "success":    False,
            "activities": [],
            "schedule":   {d: [] for d in DAYS},
            "error":      str(e),
        }

    raw_activities = data.get("activities")
    if isinstance(raw_activities, list):
        # Defensive normalisation — drop malformed entries silently.
        for a in raw_activities:
            if not isinstance(a, dict):
                continue
            start = a.get("start")
            end   = a.get("end")
            if not (_parse_hhmm(start) and _parse_hhmm(end)):
                continue
            occ = (a.get("occasion") or "casual").lower()
            if occ not in VALID_OCCASIONS:
                occ = "casual"
            days = _normalize_days(a.get("days"))
            if not days:
                continue
            activities.append({
                "id":       a.get("id") or _next_activity_id(activities),
                "name":     (a.get("name") or "").strip() or occ.title(),
                "occasion": occ,
                "days":     days,
                "start":    start,
                "end":      end,
                "location": (a.get("location") or "").strip(),
                "note":     (a.get("note") or "").strip(),
            })
    else:
        # Migrate legacy {schedule: {day: [block...]}}.
        on_disk_schedule = data.get("schedule") if isinstance(data, dict) else None
        activities = _migrate_schedule_to_activities(on_disk_schedule or {})

    return {
        "success":    True,
        "activities": activities,
        "schedule":   _activities_to_schedule(activities),
        "error":      None,
    }


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


def _persist_activities(activities: List[Dict]) -> None:
    on_disk = {
        "_comment": ("User's weekly routine. The agent falls back to this "
                     "only when the calendar has no event for the current "
                     "time. Edits via Profile -> Weekly Routine."),
        "activities": activities,
    }
    _atomic_write(ROUTINE_PATH, on_disk)


def add_activity(fields: dict) -> dict:
    """
    Add a single recurring activity. Returns
        {"success": bool, "activity": <stored dict>, "error": str|None}.

    Required fields:
      name           — free-text activity name
      days           — list of day names / group shortcuts, OR single str
      start, end     — time strings; accepts "07:00" / "7 AM" / "7am" /
                       "7:30 pm" — see parse_time_input
    Optional:
      occasion       — explicit occasion; defaults to _infer_occasion(name)
      location       — free-text
      note           — free-text
    """
    if not isinstance(fields, dict):
        return {"success": False, "activity": None,
                "error": "Activity fields must be a dict."}

    name  = (fields.get("name") or "").strip()
    days  = _normalize_days(fields.get("days"))
    start = parse_time_input(fields.get("start") or "")
    end   = parse_time_input(fields.get("end") or "")

    if not name:
        return {"success": False, "activity": None,
                "error": "Activity name is required."}
    if not days:
        return {"success": False, "activity": None,
                "error": "Select at least one day for this activity."}
    if not start:
        return {"success": False, "activity": None,
                "error": "Start time is unrecognised. Try '7:00 AM' or '07:00'."}
    if not end:
        return {"success": False, "activity": None,
                "error": "End time is unrecognised. Try '8:00 AM' or '08:00'."}
    if _parse_hhmm(end) <= _parse_hhmm(start):
        return {"success": False, "activity": None,
                "error": f"End time ({format_time_12h(end)}) must be after "
                         f"start time ({format_time_12h(start)})."}

    occasion = (fields.get("occasion") or "").lower().strip()
    if occasion not in VALID_OCCASIONS:
        occasion = _infer_occasion(name)

    existing = get_routine().get("activities", []) or []
    new_act = {
        "id":       _next_activity_id(existing),
        "name":     name,
        "occasion": occasion,
        "days":     days,
        "start":    start,
        "end":      end,
        "location": (fields.get("location") or "").strip(),
        "note":     (fields.get("note") or "").strip(),
    }
    existing.append(new_act)
    try:
        _persist_activities(existing)
    except Exception as e:
        return {"success": False, "activity": None,
                "error": f"Failed to save: {e}"}
    return {"success": True, "activity": new_act, "error": None}


def remove_activity(activity_id: str) -> dict:
    """Delete an activity by id. Returns {success, error}."""
    if not activity_id:
        return {"success": False, "error": "No activity id given."}
    existing = get_routine().get("activities", []) or []
    kept = [a for a in existing if a.get("id") != activity_id]
    if len(kept) == len(existing):
        return {"success": False, "error": f"No activity with id {activity_id}."}
    try:
        _persist_activities(kept)
    except Exception as e:
        return {"success": False, "error": f"Failed to save: {e}"}
    return {"success": True, "error": None}


def update_activity(activity_id: str, fields: dict) -> dict:
    """
    Update an activity in place. Partial updates are allowed — any
    field not present in `fields` is preserved. Returns
        {"success", "activity", "error"}.
    """
    if not activity_id:
        return {"success": False, "activity": None, "error": "No activity id."}
    if not isinstance(fields, dict):
        return {"success": False, "activity": None,
                "error": "Update fields must be a dict."}

    existing = get_routine().get("activities", []) or []
    found = next((a for a in existing if a.get("id") == activity_id), None)
    if not found:
        return {"success": False, "activity": None,
                "error": f"No activity with id {activity_id}."}

    if "name" in fields:
        v = (fields["name"] or "").strip()
        if v:
            found["name"] = v
    if "occasion" in fields:
        v = (fields["occasion"] or "").lower().strip()
        if v in VALID_OCCASIONS:
            found["occasion"] = v
    if "days" in fields:
        days = _normalize_days(fields["days"])
        if days:
            found["days"] = days
    if "start" in fields:
        s = parse_time_input(fields["start"] or "")
        if s:
            found["start"] = s
    if "end" in fields:
        e = parse_time_input(fields["end"] or "")
        if e:
            found["end"] = e
    if "location" in fields:
        found["location"] = (fields["location"] or "").strip()
    if "note" in fields:
        found["note"] = (fields["note"] or "").strip()

    if _parse_hhmm(found["end"]) <= _parse_hhmm(found["start"]):
        return {"success": False, "activity": None,
                "error": "End time must be after start time."}

    try:
        _persist_activities(existing)
    except Exception as e:
        return {"success": False, "activity": None,
                "error": f"Failed to save: {e}"}
    return {"success": True, "activity": found, "error": None}


# ── Legacy compatibility ───────────────────────────────────────────

def save_routine(schedule_or_payload: dict) -> dict:
    """
    Back-compat shim. Accepts either:
      - The legacy per-day shape: {day: [{start, end, occasion, label}]}.
      - The new shape: {"activities": [...]}.
    Both are converted to the canonical activities list internally.
    Returns {success, error}.
    """
    if not isinstance(schedule_or_payload, dict):
        return {"success": False, "error": "Schedule must be a dict."}

    if "activities" in schedule_or_payload and isinstance(
            schedule_or_payload["activities"], list):
        # Direct activities upload — validate each.
        validated: List[Dict] = []
        for a in schedule_or_payload["activities"]:
            if not isinstance(a, dict):
                continue
            start = parse_time_input(a.get("start") or "")
            end   = parse_time_input(a.get("end") or "")
            days  = _normalize_days(a.get("days"))
            if not (start and end and days):
                continue
            if _parse_hhmm(end) <= _parse_hhmm(start):
                return {"success": False,
                        "error": f"'{a.get('name','')}' ends at or before it "
                                 f"starts ({start}–{end})."}
            occ = (a.get("occasion") or "").lower().strip()
            if occ not in VALID_OCCASIONS:
                occ = _infer_occasion(a.get("name") or "")
            validated.append({
                "id":       a.get("id") or _next_activity_id(validated),
                "name":     (a.get("name") or "").strip() or occ.title(),
                "occasion": occ,
                "days":     days,
                "start":    start,
                "end":      end,
                "location": (a.get("location") or "").strip(),
                "note":     (a.get("note") or "").strip(),
            })
        try:
            _persist_activities(validated)
        except Exception as e:
            return {"success": False, "error": f"Failed to save: {e}"}
        return {"success": True, "error": None}

    # Otherwise interpret as a legacy per-day schedule. Validate
    # the inputs here so we can return clear errors for human
    # mistakes (the migration helper itself silently drops bad
    # entries, which is the right thing on read but wrong on write).
    if not isinstance(schedule_or_payload, dict):
        return {"success": False, "error": "Schedule must be a dict."}
    for d in DAYS:
        for blk in (schedule_or_payload.get(d) or []):
            if not isinstance(blk, dict):
                continue
            start = (blk.get("start") or "").strip()
            end   = (blk.get("end") or "").strip()
            label = (blk.get("label") or "").strip()
            occ   = (blk.get("occasion") or "").lower().strip()
            t_s = _parse_hhmm(start)
            t_e = _parse_hhmm(end)
            if not (t_s and t_e):
                continue
            if t_e <= t_s:
                return {
                    "success": False,
                    "error": (
                        f"On {d.title()}, the '{label or occ}' block "
                        f"ends at or before it starts ({start}–{end})."
                    ),
                }
    activities = _migrate_schedule_to_activities(schedule_or_payload)
    try:
        _persist_activities(activities)
    except Exception as e:
        return {"success": False, "error": f"Failed to save: {e}"}
    return {"success": True, "error": None}


# ── Agent integration ─────────────────────────────────────────────

def get_block_for_now(now: Optional[datetime] = None) -> Optional[Dict]:
    """
    Return the routine block that covers `now` (defaults to datetime.now()).
    Returns None if no block matches or no routine exists.

    Result shape::

        {
          "weekday":  "tuesday",
          "start":    "07:00",
          "end":      "08:00",
          "occasion": "gym",
          "label":    "Morning workout",
          "location": "gym",     # NEW — empty string when not set
          "note":     "",        # NEW — empty string when not set
        }
    """
    if now is None:
        now = datetime.now()
    weekday = DAYS[now.weekday()]
    cur_t = now.time()

    res = get_routine()
    schedule = res.get("schedule") or {}
    for blk in schedule.get(weekday, []):
        t_s = _parse_hhmm(blk.get("start") or "")
        t_e = _parse_hhmm(blk.get("end") or "")
        if t_s and t_e and t_s <= cur_t < t_e:
            return {
                "weekday":  weekday,
                "start":    blk["start"],
                "end":      blk["end"],
                "occasion": blk["occasion"],
                "label":    blk.get("label", ""),
                "location": blk.get("location", ""),
                "note":     blk.get("note", ""),
            }
    return None


def get_block_for_date(date_str: str, time_str: Optional[str] = None) -> Optional[Dict]:
    """
    Look up a routine block for an arbitrary date (and optional time).
    Used by the agent to pre-plan tomorrow's outfit when the calendar
    is empty. `date_str` is "YYYY-MM-DD"; `time_str` is "HH:MM" or
    None (None defaults to noon).
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    t = _parse_hhmm(time_str) if time_str else time(12, 0)
    if not t:
        t = time(12, 0)
    return get_block_for_now(datetime.combine(d.date(), t))


def get_weekly_blocks() -> List[Dict]:
    """
    Goal: a Mon→Sun list of routine blocks for the Routine Week
    Outfits view. Each block carries weekday + everything the agent
    needs to plan an outfit. Used by `plan_routine_week()` in
    styling_agent.py.

    For days with multiple blocks we return the FIRST chronological
    block — that's the "main" activity of the day. Days with no
    routine block contribute an empty placeholder so the UI can
    render a "no routine today" card if it wants.
    """
    res = get_routine()
    schedule = res.get("schedule") or {}
    out: List[Dict] = []
    for d in DAYS:
        blocks = schedule.get(d) or []
        if not blocks:
            out.append({"weekday": d, "empty": True})
            continue
        b = blocks[0]
        out.append({
            "weekday":  d,
            "start":    b.get("start"),
            "end":      b.get("end"),
            "occasion": b.get("occasion") or "casual",
            "label":    b.get("label") or "",
            "location": b.get("location") or "",
            "note":     b.get("note") or "",
            "empty":    False,
        })
    return out
