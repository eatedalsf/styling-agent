"""
calendar_import.py — import real calendar events from an .ics file.

Why .ics, not OAuth: Wearly's privacy contract forbids creating accounts
or storing third-party credentials. Every major calendar app
(Google, Apple, Outlook, Fastmail, ProtonMail, …) can export a private
.ics file or expose a private .ics URL. The user controls when to
share, controls what data flows in, and can revoke at any time by
regenerating the private URL or simply not re-uploading. We never see
their account credentials.

This module is stdlib-only — no external icalendar dependency. The
parser handles the common subset of RFC 5545:

  * BEGIN:VEVENT / END:VEVENT blocks
  * SUMMARY, DESCRIPTION, LOCATION, UID
  * DTSTART in both timed (YYYYMMDDTHHMMSS[Z]) and all-day
    (VALUE=DATE: YYYYMMDD) forms
  * Line folding (continuation lines starting with whitespace)
  * Common escape sequences (\\n, \\,, \\;)

Events that fail to parse are skipped silently; the import never crashes
on malformed input.

Imported events are merged into calendar_events.json — items with the
same UID are upserted, so re-importing a fresh export simply refreshes
existing events and adds new ones. The user can also choose REPLACE
mode, which discards everything currently in the calendar file and
keeps only what's in the new .ics.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
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


CALENDAR_PATH = _find_data_file("calendar_events.json")


# Canonical occasion tags Wearly's agent recognizes. When the ICS title
# or description contains one of these keywords (case-insensitive), we
# auto-tag the event with the matching occasion + formality. Otherwise
# the event keeps an empty tag and the agent treats it as casual.
_OCCASION_KEYWORDS = [
    # (keyword,            type,         formality)
    ("gym",                "gym",        "athletic"),
    ("workout",            "gym",        "athletic"),
    ("yoga",               "gym",        "athletic"),
    ("running",            "gym",        "athletic"),
    ("class at the gym",   "gym",        "athletic"),
    ("formal",             "formal",     "formal"),
    ("gala",               "formal",     "formal"),
    ("wedding",            "formal",     "formal"),
    ("interview",          "work",       "business"),
    ("meeting",            "work",       "business"),
    ("client",             "work",       "business"),
    ("presentation",       "work",       "business"),
    ("standup",            "work",       "business"),
    ("office",             "work",       "business"),
    ("work",               "work",       "business"),
    ("call",               "work",       "smart_casual"),
    ("dinner",             "dinner",     "smart_casual"),
    ("restaurant",         "dinner",     "smart_casual"),
    ("date",               "dinner",     "smart_casual"),
    ("brunch",             "casual",     "smart_casual"),
    ("weekend",            "casual",     "casual"),
    ("travel",             "casual",     "casual"),
]


def _infer_event_kind(title: str, notes: str) -> tuple:
    """Return (type, formality) inferred from the title/notes, or
    ('casual', 'casual') if nothing matches. Body-positive: descriptive
    only, never judgmental."""
    blob = f"{title or ''}  {notes or ''}".lower()
    for kw, etype, formality in _OCCASION_KEYWORDS:
        if kw in blob:
            return etype, formality
    return "casual", "casual"


# ---- ICS parsing ----------------------------------------------------

def _unfold_lines(text: str) -> List[str]:
    """RFC 5545 line folding: a line beginning with a space or tab is a
    continuation of the previous line."""
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    for line in raw_lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _unescape(value: str) -> str:
    """Reverse RFC 5545 text escapes."""
    return (
        value.replace("\\n", "\n")
             .replace("\\N", "\n")
             .replace("\\,", ",")
             .replace("\\;", ";")
             .replace("\\\\", "\\")
    )


def _parse_dtstart(raw: str) -> Optional[Dict[str, str]]:
    """
    Parse a DTSTART value. Returns {"date": "YYYY-MM-DD", "time": "HH:MM"}
    on success, or None on parse failure. Time is "" for all-day events.

    Accepts forms:
      VALUE=DATE:20260512                 -> all-day
      :20260512T100000                    -> floating timed
      :20260512T100000Z                   -> UTC timed
      ;TZID=America/Los_Angeles:20260512T100000   -> tz-aware timed
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    # Split out the params (everything before ':') from the value.
    if ":" in raw:
        params, value = raw.split(":", 1)
    else:
        params, value = "", raw

    is_all_day = "VALUE=DATE" in params.upper()

    # Strip trailing UTC marker; we don't try to be tz-correct on
    # display — the user's calendar export already encodes the intent.
    value = value.strip().rstrip("Z")

    try:
        if is_all_day or "T" not in value:
            # YYYYMMDD
            dt = datetime.strptime(value[:8], "%Y%m%d")
            return {"date": dt.strftime("%Y-%m-%d"), "time": ""}
        # YYYYMMDDTHHMMSS or YYYYMMDDTHHMM
        date_part, time_part = value.split("T", 1)
        dt = datetime.strptime(date_part, "%Y%m%d")
        hh = time_part[:2]
        mm = time_part[2:4] if len(time_part) >= 4 else "00"
        return {"date": dt.strftime("%Y-%m-%d"), "time": f"{hh}:{mm}"}
    except (ValueError, IndexError):
        return None


_PROP_RE = re.compile(r"^([A-Z][A-Z0-9-]*)((?:;[^:]*)?)(?::(.*))?$", re.IGNORECASE)


def parse_ics_text(text: str) -> List[Dict[str, str]]:
    """
    Parse an .ics blob and return a list of Wearly-shaped events::

        {
          "id":         <UID or synthesized>,
          "title":      <SUMMARY>,
          "date":       "YYYY-MM-DD",
          "time":       "HH:MM" or "",
          "type":       inferred occasion tag,
          "formality":  inferred formality,
          "notes":      <DESCRIPTION + LOCATION>,
          "source":     "ics",
        }

    Unparseable events are skipped silently. The function never raises.
    """
    out: List[Dict[str, str]] = []
    in_event = False
    cur: Dict[str, str] = {}

    for line in _unfold_lines(text):
        upper = line.upper()
        if upper.startswith("BEGIN:VEVENT"):
            in_event = True
            cur = {}
            continue
        if upper.startswith("END:VEVENT"):
            in_event = False
            if cur.get("_dtstart"):
                dt = _parse_dtstart(cur["_dtstart"])
                if dt:
                    title = cur.get("summary", "Untitled event")
                    notes_bits = []
                    if cur.get("description"):
                        notes_bits.append(cur["description"])
                    if cur.get("location"):
                        notes_bits.append(f"({cur['location']})")
                    notes = " ".join(notes_bits)
                    etype, formality = _infer_event_kind(title, notes)
                    uid = cur.get("uid") or f"ics-{dt['date']}-{dt['time'] or 'allday'}-{abs(hash(title)) % 10**8}"
                    out.append({
                        "id":        uid,
                        "title":     title,
                        "date":      dt["date"],
                        "time":      dt["time"],
                        "type":      etype,
                        "formality": formality,
                        "notes":     notes,
                        "source":    "ics",
                    })
            continue
        if not in_event:
            continue

        # Match a property line. We only care about a few keys.
        m = _PROP_RE.match(line)
        if not m:
            continue
        name = m.group(1).upper()
        value = m.group(3) or ""
        # For DTSTART we need the full "params:value" string so we can
        # see VALUE=DATE etc.
        if name == "DTSTART":
            cur["_dtstart"] = (m.group(2) + (":" + value if value else "")).lstrip(";")
        elif name == "SUMMARY":
            cur["summary"] = _unescape(value)
        elif name == "DESCRIPTION":
            cur["description"] = _unescape(value)
        elif name == "LOCATION":
            cur["location"] = _unescape(value)
        elif name == "UID":
            cur["uid"] = value.strip()

    return out


# ---- merge into calendar_events.json --------------------------------

def _load_calendar() -> list:
    try:
        with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def _atomic_write(path: str, data) -> None:
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".cal_", suffix=".json", dir=dir_)
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


def import_ics_events(text: str, replace: bool = False) -> dict:
    """
    Parse `text` as an .ics blob and merge the events into
    calendar_events.json.

    `replace=False` (default) → upsert: events with the same id are
    refreshed; new events are appended. Existing seed events the user
    didn't put in their own calendar are kept.

    `replace=True` → discard ALL current events and write only what's
    in the new .ics. Use with care; ideal for a clean re-sync.

    Returns::

        {
          "success":  bool,
          "added":    [event ids new to the file],
          "updated":  [event ids that were refreshed in place],
          "skipped":  int,   # raw event blocks that failed to parse
          "total":    int,   # events on disk after the merge
          "error":    str | None,
        }
    """
    if not isinstance(text, str) or "BEGIN:VEVENT" not in text.upper():
        return {"success": False, "added": [], "updated": [],
                "skipped": 0, "total": 0,
                "error": "This doesn't look like an .ics file (no VEVENT blocks found)."}

    parsed = parse_ics_text(text)
    raw_event_blocks = text.upper().count("BEGIN:VEVENT")
    skipped = max(0, raw_event_blocks - len(parsed))

    current = [] if replace else _load_calendar()
    by_id = {ev.get("id"): ev for ev in current if ev.get("id")}

    added: List[str] = []
    updated: List[str] = []
    for ev in parsed:
        eid = ev["id"]
        if eid in by_id:
            by_id[eid].update(ev)
            updated.append(eid)
        else:
            by_id[eid] = ev
            added.append(eid)

    merged = list(by_id.values())
    merged.sort(key=lambda e: (e.get("date", ""), e.get("time", "")))

    try:
        _atomic_write(CALENDAR_PATH, merged)
    except Exception as e:
        return {"success": False, "added": added, "updated": updated,
                "skipped": skipped, "total": len(merged),
                "error": f"Failed to write calendar: {e}"}

    return {"success": True, "added": added, "updated": updated,
            "skipped": skipped, "total": len(merged), "error": None}
