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
from datetime import datetime, timezone
from typing import List, Dict, Optional

try:
    # Python 3.9+ — stdlib, ships zoneinfo without an external dep.
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # type: ignore
except ImportError:  # pragma: no cover — Wearly requires 3.10+
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore


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
SUBSCRIPTION_PATH = _find_data_file("calendar_subscription.json")
USER_PROFILE_PATH = _find_data_file("user_profile.json")


# ─────────────────────────────────────────────
# USER TIMEZONE RESOLUTION
# ─────────────────────────────────────────────

# Default timezone used when the user hasn't set one. Minneapolis is in
# America/Chicago; making this the default means the live demo Just
# Works for the project owner without forcing them through a settings
# step on first run. Reviewers anywhere else only need to set their
# own zone in Profile to get correct local times.
_DEFAULT_TZ_NAME = "America/Chicago"


def _read_user_timezone_name() -> str:
    """
    Read the user-selected IANA timezone from user_profile.json.

    Falls back to America/Chicago when:
      - the file doesn't exist
      - the "timezone" key is missing or null
      - the value isn't a string

    No exception is ever raised — calendar parsing must keep working
    even with a corrupt profile file.
    """
    if not os.path.exists(USER_PROFILE_PATH):
        return _DEFAULT_TZ_NAME
    try:
        with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        name = data.get("timezone")
        if isinstance(name, str) and name.strip():
            return name.strip()
    except Exception:
        pass
    return _DEFAULT_TZ_NAME


def _resolve_tz(name: Optional[str]) -> "ZoneInfo":
    """
    Resolve an IANA tz name to a ZoneInfo. Falls back to UTC when the
    name is invalid (instead of crashing the importer).
    """
    if ZoneInfo is None:
        return timezone.utc  # type: ignore[return-value]
    try:
        return ZoneInfo(name) if name else ZoneInfo(_DEFAULT_TZ_NAME)
    except ZoneInfoNotFoundError:
        # Bad name in profile or in the .ics TZID — fall back to UTC
        # so the event still loads, just in raw UTC. Documented in tests.
        try:
            return ZoneInfo(_DEFAULT_TZ_NAME)
        except ZoneInfoNotFoundError:
            return timezone.utc  # type: ignore[return-value]


def get_user_tz() -> "ZoneInfo":
    """Public accessor: ZoneInfo for the user's selected timezone."""
    return _resolve_tz(_read_user_timezone_name())


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


def _parse_dtstart(raw: str, user_tz: Optional["ZoneInfo"] = None) -> Optional[Dict[str, str]]:
    """
    Parse a DTSTART value. Returns {"date": "YYYY-MM-DD", "time": "HH:MM"}
    on success, or None on parse failure. Time is "" for all-day events.

    `user_tz` is the IANA zone the user lives in (resolved via
    get_user_tz() when not supplied). Output dates and times are
    expressed in that zone.

    Accepts the four DTSTART forms RFC 5545 allows:

      VALUE=DATE:20260512                  -> all-day (no time, no
                                              zone conversion)
      :20260512T100000                     -> floating (no zone info
                                              attached; stored as-is)
      :20260512T100000Z                    -> UTC (converted to
                                              user_tz before storing)
      ;TZID=America/Los_Angeles:20260512T100000
                                           -> zone-aware (parsed in
                                              the named zone, then
                                              converted to user_tz)

    Date crossings are handled automatically because every conversion
    flows through aware-datetime arithmetic. E.g. 03:00 UTC May 13
    becomes 22:00 LOCAL May 12 in Chicago, with the date correctly
    rolled back to the previous day.

    If user_tz is unspecified the function reads it from
    user_profile.json. The result of the previous Python-process's
    .astimezone() (which depended on the SERVER's local zone — wrong
    on Streamlit Cloud) is no longer relied on anywhere.
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    if user_tz is None:
        user_tz = get_user_tz()

    # Split params (everything before the first ':') from the value.
    if ":" in raw:
        params, value = raw.split(":", 1)
    else:
        params, value = "", raw

    params_upper = params.upper()
    is_all_day = "VALUE=DATE" in params_upper
    value = value.strip()
    is_utc = value.endswith("Z")
    if is_utc:
        value = value[:-1]

    # Extract TZID=... if present, e.g. ;TZID=America/Los_Angeles
    tzid_match = re.search(r"TZID=([^;:]+)", params, flags=re.IGNORECASE)
    tzid_name = tzid_match.group(1).strip() if tzid_match else None

    try:
        if is_all_day or "T" not in value:
            # All-day: YYYYMMDD, no time component, no zone conversion.
            dt = datetime.strptime(value[:8], "%Y%m%d")
            return {"date": dt.strftime("%Y-%m-%d"), "time": ""}

        # Timed: YYYYMMDDTHHMMSS or YYYYMMDDTHHMM (pad seconds if missing)
        date_part, time_part = value.split("T", 1)
        dt = datetime.strptime(
            date_part + "T" + time_part[:6].ljust(6, "0"),
            "%Y%m%dT%H%M%S",
        )

        if is_utc:
            # Attach UTC tzinfo, then convert to the user's zone.
            dt_aware = dt.replace(tzinfo=timezone.utc).astimezone(user_tz)
        elif tzid_name:
            # Parse in the declared zone, then convert to the user's
            # zone. If we can't resolve TZID (rare, unknown name),
            # fall back to treating the time as floating.
            source_tz = _resolve_tz(tzid_name)
            try:
                dt_aware = dt.replace(tzinfo=source_tz).astimezone(user_tz)
            except Exception:
                dt_aware = dt   # treat as floating
        else:
            # Floating: by spec, this is interpreted as the LOCAL time
            # of whoever is reading. We store it as-is (no conversion,
            # no zone attached) so it displays the same wall-clock
            # number on every machine — matching Google Calendar's
            # behavior for events without an explicit TZ.
            dt_aware = dt

        return {
            "date": dt_aware.strftime("%Y-%m-%d"),
            "time": dt_aware.strftime("%H:%M"),
        }
    except (ValueError, IndexError):
        return None


_PROP_RE = re.compile(r"^([A-Z][A-Z0-9-]*)((?:;[^:]*)?)(?::(.*))?$", re.IGNORECASE)


def parse_ics_text(text: str, user_tz: Optional["ZoneInfo"] = None) -> List[Dict[str, str]]:
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

    `user_tz` controls the timezone used to express dates and times.
    When omitted, the user's profile setting is honored (default
    America/Chicago). Tests pass an explicit zone for determinism.

    Unparseable events are skipped silently. The function never raises.
    """
    if user_tz is None:
        user_tz = get_user_tz()

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
                dt = _parse_dtstart(cur["_dtstart"], user_tz=user_tz)
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


# ---- URL subscription -----------------------------------------------
#
# The closest thing to "auto-connected" without OAuth: the user pastes
# the private .ics feed URL their calendar provider exposes. Wearly
# fetches it whenever asked. No third-party credentials are stored —
# only the URL — but the URL IS itself a capability (anyone who knows
# it can read the calendar). We surface that fact in the UI copy.
#
# Where the URL lives:
#   - Google Calendar : Settings -> select the calendar -> "Integrate
#                       calendar" -> "Secret address in iCal format"
#                       (icalendar URL, starts with https://calendar...)
#   - iCloud / Apple  : iCloud.com -> Calendar -> share the calendar
#                       publicly -> copy URL (starts with webcal:// or
#                       https://p##-caldav.icloud.com/...). We rewrite
#                       webcal:// to https:// for fetching.

import urllib.request as _urlreq
import urllib.error as _urlerr


def _load_subscription() -> dict:
    """Read the subscription file. Returns {} when missing or malformed."""
    if not os.path.exists(SUBSCRIPTION_PATH):
        return {}
    try:
        with open(SUBSCRIPTION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_subscription() -> dict:
    """
    Public accessor for the saved subscription record. Returns::

        {
          "url":            "<the ics URL>",
          "label":          "Google Calendar" | "iCloud" | "Custom",
          "last_synced_at": ISO-8601 string,
          "last_event_count": int,
        }

    Or {} when no subscription is saved.
    """
    sub = _load_subscription()
    if not sub.get("url"):
        return {}
    return sub


def _save_subscription(sub: dict) -> None:
    on_disk = {
        "_comment": "Calendar subscription. Stored locally only — the URL "
                    "is treated as a credential and never transmitted to "
                    "any third party except the calendar provider itself.",
        **sub,
    }
    _atomic_write(SUBSCRIPTION_PATH, on_disk)


def _normalize_calendar_url(url: str) -> str:
    """Rewrite webcal://... to https://... so urllib can fetch it."""
    url = (url or "").strip()
    if url.startswith("webcal://"):
        return "https://" + url[len("webcal://"):]
    if url.startswith("webcals://"):
        return "https://" + url[len("webcals://"):]
    return url


def _infer_provider_label(url: str) -> str:
    """Best-effort 'where is this from' label for the UI."""
    u = (url or "").lower()
    if "google.com" in u or "googleusercontent" in u:
        return "Google Calendar"
    if "icloud.com" in u or "caldav.icloud" in u:
        return "iCloud"
    if "outlook" in u or "office" in u:
        return "Outlook"
    return "Custom calendar"


def subscribe_calendar_url(url: str) -> dict:
    """
    Save (or update) the subscribed calendar URL. Does NOT fetch yet —
    callers should follow up with refresh_subscription() to verify the
    URL works and import the events.

    Returns {"success": bool, "url": str, "label": str, "error": ...}.
    """
    norm = _normalize_calendar_url(url)
    if not norm.startswith(("http://", "https://")):
        return {"success": False, "url": url, "label": "",
                "error": "URL must start with http://, https://, or webcal://."}

    sub = _load_subscription()
    sub.update({
        "url":   norm,
        "label": _infer_provider_label(norm),
    })
    try:
        _save_subscription(sub)
    except Exception as e:
        return {"success": False, "url": norm, "label": sub.get("label", ""),
                "error": f"Could not save subscription: {e}"}
    return {"success": True, "url": norm, "label": sub["label"], "error": None}


def unsubscribe_calendar() -> dict:
    """Remove the saved calendar subscription (events stay in calendar_events.json)."""
    try:
        if os.path.exists(SUBSCRIPTION_PATH):
            os.remove(SUBSCRIPTION_PATH)
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "error": None}


def refresh_subscription(replace: bool = True, timeout: int = 10) -> dict:
    """
    Fetch the subscribed URL and write the resulting events to
    calendar_events.json. Behaves like import_ics_events() under the
    hood and returns the same result shape, plus a "fetched_bytes"
    key so the UI can show how much came in.

    `replace=True` (default) — MIRROR mode. The .ics URL is treated
    as the source of truth: any event currently in the local file
    that is NOT in the fetched .ics gets dropped. This is what users
    expect from a calendar "subscription" — removing an event from
    Google Calendar must remove it from Wearly too, the same way
    Apple Calendar drops it from a subscribed view.

    `replace=False` — UPSERT mode. New events are added, existing
    events with matching IDs are refreshed in place, and anything
    not in the .ics is left alone. Useful when the user has a mix
    of URL-subscribed events and ad-hoc events they don't want
    overwritten — but the standard subscription contract is mirror,
    so this is the non-default branch.

    .ics FILE uploads use import_ics_events() directly with its own
    default of replace=False — uploads are one-shot additions, not
    a recurring source of truth.
    """
    sub = _load_subscription()
    url = sub.get("url")
    if not url:
        return {"success": False, "error": "No calendar URL subscribed yet.",
                "added": [], "updated": [], "skipped": 0, "total": 0,
                "fetched_bytes": 0}

    # Polite default User-Agent — some providers reject the python-urllib
    # default. We don't impersonate a browser; we identify as Wearly.
    req = _urlreq.Request(url, headers={
        "User-Agent": "Wearly/0.4 (+https://eatedalsf.github.io/styling-agent)",
        "Accept": "text/calendar, */*;q=0.5",
    })
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            blob = resp.read()
    except _urlerr.HTTPError as e:
        return {"success": False,
                "error": f"Calendar server returned HTTP {e.code}. "
                         f"The URL may have expired or you may need to "
                         f"regenerate it from your calendar provider.",
                "added": [], "updated": [], "skipped": 0, "total": 0,
                "fetched_bytes": 0}
    except _urlerr.URLError as e:
        return {"success": False,
                "error": f"Couldn't reach the calendar server: {e.reason}. "
                         f"Check the URL or your network.",
                "added": [], "updated": [], "skipped": 0, "total": 0,
                "fetched_bytes": 0}
    except Exception as e:
        return {"success": False, "error": f"Fetch failed: {e}",
                "added": [], "updated": [], "skipped": 0, "total": 0,
                "fetched_bytes": 0}

    try:
        text = blob.decode("utf-8", errors="replace")
    except Exception:
        text = blob.decode("latin-1", errors="replace")

    res = import_ics_events(text, replace=replace)
    res["fetched_bytes"] = len(blob)

    # Stamp the subscription record with last-sync metadata.
    if res.get("success"):
        sub["last_synced_at"]   = datetime.utcnow().isoformat() + "Z"
        sub["last_event_count"] = res.get("total", 0)
        try:
            _save_subscription(sub)
        except Exception:
            pass  # non-fatal: events were still imported

    return res
