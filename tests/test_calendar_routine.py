"""
Tests for calendar_import + routine_tool — the two new modules that
let users connect their real calendar (via .ics upload) and define a
weekly routine that the agent falls back to when the calendar has no
event for the current moment.

Both modules touch on-disk JSON files. Each test snapshots those files
and restores them in tearDown so the developer's working state isn't
polluted.

Run with:
    python -m unittest tests.test_calendar_routine
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class _DiskSnapshot:
    """Mixin: snapshot named files for the duration of each test."""

    FILES: tuple = ()

    @classmethod
    def setUpClass(cls):
        cls._backup = {}
        for path in cls.FILES:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._backup[path] = f.read()

    @classmethod
    def tearDownClass(cls):
        for path, content in cls._backup.items():
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)


class TestICSParser(unittest.TestCase):
    """parse_ics_text handles the common subset of RFC 5545."""

    def test_minimal_timed_event_utc_in_chicago(self):
        # DTSTART ending in `Z` is UTC by RFC 5545. Wearly converts
        # to the user's selected timezone (default America/Chicago).
        # The conversion is now driven by user_tz, not by the server
        # clock — so this test is deterministic on CI (UTC) AND on a
        # developer's laptop. 09:00 UTC = 04:00 Central (CDT, May).
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:abc-123@wearly\r\n"
            "SUMMARY:Team standup\r\n"
            "DTSTART:20260512T090000Z\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        events = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["id"], "abc-123@wearly")
        self.assertEqual(ev["title"], "Team standup")
        self.assertEqual(ev["date"], "2026-05-12")
        self.assertEqual(ev["time"], "04:00")   # 09:00 UTC -> 04:00 CDT
        self.assertEqual(ev["type"], "work")    # "standup" keyword
        self.assertEqual(ev["formality"], "business")
        self.assertEqual(ev["source"], "ics")

    # ── User-tz aware parsing — the bug-fix coverage ─────────────

    def test_utc_event_converted_to_chicago(self):
        """The lunch case the user reported: 1pm Central in Google
        is encoded as 18:00 UTC. Wearly must display 13:00."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:lunch-1@google.com\n"
            "SUMMARY:lunch\n"
            "DTSTART:20260513T180000Z\n"
            "END:VEVENT\n"
        )
        ev = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))[0]
        self.assertEqual(ev["date"], "2026-05-13")
        self.assertEqual(ev["time"], "13:00")

    def test_floating_time_not_shifted(self):
        """No `Z`, no TZID → the spec says interpret as local clock
        time of the viewer. We must NOT shift it."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:floating-1\n"
            "SUMMARY:Floating meeting\n"
            "DTSTART:20260513T130000\n"
            "END:VEVENT\n"
        )
        # Same DTSTART should produce the same wall-clock time on
        # every machine, regardless of user_tz.
        for tz_name in ("America/Chicago", "America/New_York", "UTC"):
            ev = parse_ics_text(ics, user_tz=ZoneInfo(tz_name))[0]
            self.assertEqual(ev["date"], "2026-05-13",
                             f"floating date shifted in {tz_name}")
            self.assertEqual(ev["time"], "13:00",
                             f"floating time shifted in {tz_name}")

    def test_tzid_event_converted_to_user_zone(self):
        """TZID names a source zone. The event is converted from
        there to the user's zone. 10:00 in LA = 12:00 in Chicago."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:tzid-1\n"
            "SUMMARY:LA meeting\n"
            "DTSTART;TZID=America/Los_Angeles:20260513T100000\n"
            "END:VEVENT\n"
        )
        ev = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))[0]
        self.assertEqual(ev["date"], "2026-05-13")
        self.assertEqual(ev["time"], "12:00")

    def test_utc_event_crosses_midnight_to_previous_local_day(self):
        """User's 'Dinner' encoded as T034500Z (3:45 AM UTC May 13)
        is actually Tue May 12 10:45 PM in Chicago. The date field
        must roll back to the previous local day."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:dinner-1@google.com\n"
            "SUMMARY:Dinner\n"
            "DTSTART:20260513T034500Z\n"
            "END:VEVENT\n"
        )
        ev = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))[0]
        self.assertEqual(ev["date"], "2026-05-12")
        self.assertEqual(ev["time"], "22:45")

    def test_utc_midnight_crosses_to_previous_local_evening(self):
        """T000000Z (midnight UTC May 24) is 7:00 PM May 23 Central.
        Both the date and the time must shift."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:wedding-1@google.com\n"
            "SUMMARY:friend's wedding\n"
            "DTSTART:20260524T000000Z\n"
            "END:VEVENT\n"
        )
        ev = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))[0]
        self.assertEqual(ev["date"], "2026-05-23")
        self.assertEqual(ev["time"], "19:00")

    def test_user_tz_is_respected_not_server_tz(self):
        """Same UTC event displayed differently for two user zones."""
        from zoneinfo import ZoneInfo
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:multi-tz-1\n"
            "SUMMARY:Standup\n"
            "DTSTART:20260513T150000Z\n"
            "END:VEVENT\n"
        )
        ev_chi = parse_ics_text(ics, user_tz=ZoneInfo("America/Chicago"))[0]
        ev_nyc = parse_ics_text(ics, user_tz=ZoneInfo("America/New_York"))[0]
        ev_utc = parse_ics_text(ics, user_tz=ZoneInfo("UTC"))[0]
        self.assertEqual(ev_chi["time"], "10:00")   # CDT = UTC-5
        self.assertEqual(ev_nyc["time"], "11:00")   # EDT = UTC-4
        self.assertEqual(ev_utc["time"], "15:00")

    def test_all_day_event(self):
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "UID:holiday-1\n"
            "SUMMARY:Holiday\n"
            "DTSTART;VALUE=DATE:20261225\n"
            "END:VEVENT\n"
        )
        events = parse_ics_text(ics)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-12-25")
        self.assertEqual(events[0]["time"], "")

    def test_unfolded_description(self):
        from calendar_import import parse_ics_text
        # Continuation lines start with a space.
        ics = (
            "BEGIN:VEVENT\n"
            "UID:long-1\n"
            "SUMMARY:Quarterly review\n"
            "DESCRIPTION:Line one\\nLine\n"
            " two continues here.\n"
            "DTSTART:20260512T140000\n"
            "END:VEVENT\n"
        )
        events = parse_ics_text(ics)
        self.assertEqual(len(events), 1)
        self.assertIn("two continues here", events[0]["notes"])

    def test_no_uid_generates_one(self):
        from calendar_import import parse_ics_text
        ics = (
            "BEGIN:VEVENT\n"
            "SUMMARY:Gym session\n"
            "DTSTART:20260512T070000\n"
            "END:VEVENT\n"
        )
        events = parse_ics_text(ics)
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["id"].startswith("ics-"))
        self.assertEqual(events[0]["type"], "gym")

    def test_garbage_ics_returns_empty(self):
        from calendar_import import parse_ics_text
        self.assertEqual(parse_ics_text(""), [])
        self.assertEqual(parse_ics_text("this is not an ics file"), [])

    def test_get_user_tz_reads_from_profile(self):
        """get_user_tz() should honor the user_profile.json setting."""
        import tempfile, json as _json
        from zoneinfo import ZoneInfo
        from calendar_import import _resolve_tz, _read_user_timezone_name, USER_PROFILE_PATH
        # Snapshot existing profile, swap in a test one, restore.
        backup = None
        if os.path.exists(USER_PROFILE_PATH):
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                backup = f.read()
        try:
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                _json.dump({"timezone": "Europe/Athens"}, f)
            self.assertEqual(_read_user_timezone_name(), "Europe/Athens")
            self.assertEqual(_resolve_tz("Europe/Athens").key, "Europe/Athens")
        finally:
            if backup is not None:
                with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                    f.write(backup)
            elif os.path.exists(USER_PROFILE_PATH):
                os.remove(USER_PROFILE_PATH)

    def test_get_user_tz_defaults_to_chicago_when_unset(self):
        """Missing/empty profile → America/Chicago (Minneapolis)."""
        import json as _json
        from calendar_import import _read_user_timezone_name, USER_PROFILE_PATH
        backup = None
        if os.path.exists(USER_PROFILE_PATH):
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                backup = f.read()
        try:
            if os.path.exists(USER_PROFILE_PATH):
                os.remove(USER_PROFILE_PATH)
            self.assertEqual(_read_user_timezone_name(), "America/Chicago")
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                _json.dump({"timezone": None}, f)
            self.assertEqual(_read_user_timezone_name(), "America/Chicago")
        finally:
            if backup is not None:
                with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                    f.write(backup)
            elif os.path.exists(USER_PROFILE_PATH):
                os.remove(USER_PROFILE_PATH)


class TestICSImport(_DiskSnapshot, unittest.TestCase):
    """import_ics_events merges into calendar_events.json."""

    @classmethod
    def setUpClass(cls):
        from calendar_import import CALENDAR_PATH
        cls.FILES = (CALENDAR_PATH,)
        super().setUpClass()

    def setUp(self):
        from calendar_import import CALENDAR_PATH
        # Start each test from a known empty calendar.
        with open(CALENDAR_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)

    def test_rejects_non_ics_input(self):
        from calendar_import import import_ics_events
        r = import_ics_events("hello world")
        self.assertFalse(r["success"])
        self.assertIn("ics", (r.get("error") or "").lower())

    def test_merge_appends_new_events(self):
        from calendar_import import import_ics_events, CALENDAR_PATH
        ics = (
            "BEGIN:VEVENT\nUID:a\nSUMMARY:Meeting\n"
            "DTSTART:20260512T100000\nEND:VEVENT\n"
        )
        r = import_ics_events(ics)
        self.assertTrue(r["success"], r.get("error"))
        self.assertEqual(len(r["added"]), 1)
        self.assertEqual(len(r["updated"]), 0)

        # Re-importing the same content refreshes, doesn't duplicate.
        r2 = import_ics_events(ics)
        self.assertEqual(len(r2["added"]), 0)
        self.assertEqual(len(r2["updated"]), 1)

        # File on disk has exactly one event.
        with open(CALENDAR_PATH) as f:
            on_disk = json.load(f)
        self.assertEqual(len(on_disk), 1)

    def test_replace_clears_existing(self):
        from calendar_import import import_ics_events, CALENDAR_PATH
        ics_a = ("BEGIN:VEVENT\nUID:a\nSUMMARY:Old\n"
                 "DTSTART:20260512T100000\nEND:VEVENT\n")
        ics_b = ("BEGIN:VEVENT\nUID:b\nSUMMARY:New\n"
                 "DTSTART:20260513T100000\nEND:VEVENT\n")
        import_ics_events(ics_a)
        r = import_ics_events(ics_b, replace=True)
        self.assertTrue(r["success"])
        with open(CALENDAR_PATH) as f:
            on_disk = json.load(f)
        self.assertEqual({ev["id"] for ev in on_disk}, {"b"})


class TestRoutineTool(_DiskSnapshot, unittest.TestCase):
    """routine_tool save / get / lookup behavior."""

    @classmethod
    def setUpClass(cls):
        from routine_tool import ROUTINE_PATH
        cls.FILES = (ROUTINE_PATH,)
        super().setUpClass()

    def setUp(self):
        # Start each test with a fresh empty routine file removed.
        from routine_tool import ROUTINE_PATH
        if os.path.exists(ROUTINE_PATH):
            os.remove(ROUTINE_PATH)

    def test_get_returns_empty_when_missing(self):
        from routine_tool import get_routine, DAYS
        res = get_routine()
        self.assertTrue(res["success"])
        for d in DAYS:
            self.assertEqual(res["schedule"][d], [])

    def test_save_and_get_roundtrip(self):
        from routine_tool import save_routine, get_routine
        schedule = {
            "monday": [{"start": "07:00", "end": "08:00",
                        "occasion": "gym", "label": "Morning"}],
            "wednesday": [{"start": "09:00", "end": "17:00",
                           "occasion": "work", "label": "Office"}],
        }
        r = save_routine(schedule)
        self.assertTrue(r["success"], r.get("error"))
        got = get_routine()
        self.assertEqual(len(got["schedule"]["monday"]), 1)
        self.assertEqual(got["schedule"]["monday"][0]["occasion"], "gym")
        self.assertEqual(len(got["schedule"]["wednesday"]), 1)

    def test_rejects_inverted_time_block(self):
        from routine_tool import save_routine
        r = save_routine({"monday": [{"start": "09:00", "end": "08:00",
                                       "occasion": "work", "label": "Bad"}]})
        self.assertFalse(r["success"])
        self.assertIn("ends at or before", r["error"])

    def test_lookup_for_now(self):
        from routine_tool import save_routine, get_block_for_now, DAYS
        save_routine({
            "monday":    [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "tuesday":   [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "wednesday": [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "thursday":  [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "friday":    [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "saturday":  [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
            "sunday":    [{"start": "07:00", "end": "08:00",
                           "occasion": "gym", "label": "Morning"}],
        })
        # An arbitrary moment INSIDE every day's block hits gym.
        target = datetime(2026, 5, 12, 7, 30)   # 07:30 on a Tuesday
        b = get_block_for_now(target)
        self.assertIsNotNone(b)
        self.assertEqual(b["occasion"], "gym")
        self.assertEqual(b["weekday"], DAYS[target.weekday()])

    def test_lookup_outside_blocks_returns_none(self):
        from routine_tool import save_routine, get_block_for_now
        save_routine({"monday": [{"start": "07:00", "end": "08:00",
                                   "occasion": "gym", "label": "M"}]})
        target = datetime(2026, 5, 11, 22, 0)  # 22:00 Monday — outside
        self.assertIsNone(get_block_for_now(target))

    # ── New canonical activities API (Task 2 redesign) ──────────

    def test_add_activity_multi_day(self):
        """One activity spanning Mon + Wed expands to two schedule days."""
        from routine_tool import add_activity, get_routine
        r = add_activity({
            "name":  "Morning gym",
            "days":  ["Monday", "Wednesday"],
            "start": "7:00 AM",
            "end":   "8:00 AM",
            "location": "gym",
        })
        self.assertTrue(r["success"], r.get("error"))
        got = get_routine()
        self.assertEqual(len(got["activities"]), 1)
        self.assertEqual(got["activities"][0]["days"], ["monday", "wednesday"])
        self.assertEqual(got["activities"][0]["start"], "07:00")
        self.assertEqual(got["schedule"]["monday"][0]["occasion"], "gym")
        self.assertEqual(got["schedule"]["wednesday"][0]["occasion"], "gym")

    def test_day_group_shortcuts_expand(self):
        """'Weekdays' expands to Mon..Fri; 'Weekends' to Sat+Sun;
        'Every day' to all 7."""
        from routine_tool import add_activity, get_routine
        add_activity({"name": "Work", "days": ["Weekdays"],
                       "start": "9:00 AM", "end": "5:00 PM",
                       "location": "office"})
        got = get_routine()
        self.assertEqual(
            got["activities"][0]["days"],
            ["monday", "tuesday", "wednesday", "thursday", "friday"],
        )
        for d in ("monday", "tuesday", "friday"):
            self.assertEqual(got["schedule"][d][0]["occasion"], "work")
        for d in ("saturday", "sunday"):
            self.assertEqual(got["schedule"][d], [])

    def test_parse_time_input_accepts_12h_and_24h(self):
        from routine_tool import parse_time_input
        self.assertEqual(parse_time_input("7:00 AM"), "07:00")
        self.assertEqual(parse_time_input("7am"),     "07:00")
        self.assertEqual(parse_time_input("12 PM"),   "12:00")
        self.assertEqual(parse_time_input("12 AM"),   "00:00")
        self.assertEqual(parse_time_input("6:30 PM"), "18:30")
        self.assertEqual(parse_time_input("07:00"),   "07:00")
        self.assertEqual(parse_time_input("23:59"),   "23:59")
        self.assertIsNone(parse_time_input("not a time"))

    def test_format_time_12h(self):
        from routine_tool import format_time_12h
        self.assertEqual(format_time_12h("07:00"), "7:00 AM")
        self.assertEqual(format_time_12h("18:30"), "6:30 PM")
        self.assertEqual(format_time_12h("00:30"), "12:30 AM")
        self.assertEqual(format_time_12h("12:00"), "12:00 PM")
        self.assertEqual(format_time_12h(""),      "")

    def test_remove_activity(self):
        from routine_tool import add_activity, remove_activity, get_routine
        r = add_activity({"name": "Gym", "days": ["Monday"],
                          "start": "7:00", "end": "8:00"})
        aid = r["activity"]["id"]
        rd = remove_activity(aid)
        self.assertTrue(rd["success"], rd.get("error"))
        self.assertEqual(get_routine()["activities"], [])

    def test_update_activity_partial(self):
        from routine_tool import add_activity, update_activity, get_routine
        r = add_activity({"name": "Gym", "days": ["Monday"],
                          "start": "7:00", "end": "8:00"})
        aid = r["activity"]["id"]
        upd = update_activity(aid, {"days": ["Tuesday", "Thursday"],
                                     "location": "home gym"})
        self.assertTrue(upd["success"], upd.get("error"))
        got = get_routine()["activities"][0]
        self.assertEqual(got["days"], ["tuesday", "thursday"])
        self.assertEqual(got["location"], "home gym")
        self.assertEqual(got["start"], "07:00")   # preserved

    def test_legacy_schedule_migrates_on_read(self):
        """A routine.json with the old per-day shape is read back as
        an activities list — no manual migration needed."""
        import json as _json
        from routine_tool import ROUTINE_PATH, get_routine
        legacy = {
            "schedule": {
                "monday":    [{"start": "07:00", "end": "08:00",
                               "occasion": "gym", "label": "Morning"}],
                "wednesday": [{"start": "09:00", "end": "17:00",
                               "occasion": "work", "label": "Office"}],
                "tuesday": [], "thursday": [], "friday": [],
                "saturday": [], "sunday": [],
            }
        }
        with open(ROUTINE_PATH, "w", encoding="utf-8") as f:
            _json.dump(legacy, f)
        got = get_routine()
        self.assertEqual(len(got["activities"]), 2)
        names = sorted(a["name"] for a in got["activities"])
        self.assertEqual(names, ["Morning", "Office"])

    def test_multiple_same_activity_different_days(self):
        """Gym Monday 7 AM + Gym Tuesday 6 PM coexist."""
        from routine_tool import add_activity, get_routine
        add_activity({"name": "Gym", "days": ["Monday"],
                      "start": "7:00 AM", "end": "8:00 AM"})
        add_activity({"name": "Gym", "days": ["Tuesday"],
                      "start": "6:00 PM", "end": "7:00 PM"})
        got = get_routine()
        self.assertEqual(len(got["activities"]), 2)
        self.assertEqual(got["schedule"]["monday"][0]["start"], "07:00")
        self.assertEqual(got["schedule"]["tuesday"][0]["start"], "18:00")

    def test_add_activity_validates_inverted_times(self):
        from routine_tool import add_activity
        r = add_activity({"name": "Bad", "days": ["Monday"],
                          "start": "9:00 AM", "end": "8:00 AM"})
        self.assertFalse(r["success"])
        self.assertIn("after start time", r["error"])

    def test_occasion_auto_inferred_from_name(self):
        from routine_tool import add_activity, get_routine
        add_activity({"name": "Morning yoga", "days": ["Monday"],
                      "start": "7:00", "end": "8:00"})
        got = get_routine()["activities"][0]
        self.assertEqual(got["occasion"], "gym")

    # ── get_weekly_blocks now returns ALL activities per day ────────

    def test_get_weekly_blocks_returns_all_activities_per_day(self):
        """A Monday with TWO activities (gym 7am + work 10am) must
        produce TWO Monday entries from get_weekly_blocks(), not one.
        Earlier behavior took blocks[0] only and silently dropped Work."""
        from routine_tool import add_activity, get_weekly_blocks
        add_activity({"name": "gym",  "days": ["Monday"],
                      "start": "7:00",  "end": "8:00"})
        add_activity({"name": "Work", "days": ["Monday"],
                      "start": "10:00", "end": "17:00"})
        weekly = get_weekly_blocks()
        monday = [b for b in weekly if b.get("weekday") == "monday"
                   and not b.get("empty")]
        self.assertEqual(
            len(monday), 2,
            "Monday must produce two blocks when two activities exist; "
            f"got {[b.get('label') for b in monday]}",
        )
        # Chronological order
        self.assertEqual(monday[0]["start"], "07:00")
        self.assertEqual(monday[1]["start"], "10:00")
        # block_index stamped 0, 1
        self.assertEqual(monday[0]["block_index"], 0)
        self.assertEqual(monday[1]["block_index"], 1)
        # blocks_for_day matches
        self.assertEqual(monday[0]["blocks_for_day"], 2)
        self.assertEqual(monday[1]["blocks_for_day"], 2)

    def test_get_weekly_blocks_empty_day_still_returns_placeholder(self):
        """Empty days continue to return one empty placeholder so
        the UI can render a 'no routine today' card."""
        from routine_tool import add_activity, get_weekly_blocks
        add_activity({"name": "gym", "days": ["Monday"],
                      "start": "7:00", "end": "8:00"})
        weekly = get_weekly_blocks()
        tuesday = [b for b in weekly if b.get("weekday") == "tuesday"]
        self.assertEqual(len(tuesday), 1)
        self.assertTrue(tuesday[0]["empty"])

    def test_get_weekly_blocks_sorts_blocks_by_start_time(self):
        """When activities are added out of order, get_weekly_blocks
        returns them chronologically within each day."""
        from routine_tool import add_activity, get_weekly_blocks
        # Add work first (later in the day), then gym (earlier)
        add_activity({"name": "Work", "days": ["Wednesday"],
                      "start": "10:00", "end": "17:00"})
        add_activity({"name": "gym", "days": ["Wednesday"],
                      "start": "7:00", "end": "8:00"})
        weekly = get_weekly_blocks()
        wed = [b for b in weekly if b.get("weekday") == "wednesday"
                and not b.get("empty")]
        self.assertEqual(wed[0]["label"], "gym")
        self.assertEqual(wed[1]["label"], "Work")


class TestCalendarSubscription(_DiskSnapshot, unittest.TestCase):
    """URL-subscription save/load/disconnect behavior (no network)."""

    @classmethod
    def setUpClass(cls):
        from calendar_import import SUBSCRIPTION_PATH
        cls.FILES = (SUBSCRIPTION_PATH,)
        super().setUpClass()

    def setUp(self):
        from calendar_import import SUBSCRIPTION_PATH
        if os.path.exists(SUBSCRIPTION_PATH):
            os.remove(SUBSCRIPTION_PATH)

    def test_rejects_non_http_url(self):
        from calendar_import import subscribe_calendar_url
        r = subscribe_calendar_url("not-a-url")
        self.assertFalse(r["success"])
        self.assertIn("http://", r["error"])

    def test_webcal_normalizes_to_https(self):
        from calendar_import import subscribe_calendar_url, get_subscription
        r = subscribe_calendar_url("webcal://p99-caldav.icloud.com/cal.ics")
        self.assertTrue(r["success"])
        sub = get_subscription()
        self.assertTrue(sub["url"].startswith("https://"))
        self.assertEqual(sub["label"], "iCloud")

    def test_provider_label_inference(self):
        from calendar_import import subscribe_calendar_url, get_subscription
        for url, expected in (
            ("https://calendar.google.com/calendar/ical/x/basic.ics", "Google Calendar"),
            ("https://p99-caldav.icloud.com/published/x.ics",         "iCloud"),
            ("https://outlook.live.com/owa/calendar/x/cid-abc.ics",   "Outlook"),
            ("https://my-server.example/cal.ics",                     "Custom calendar"),
        ):
            r = subscribe_calendar_url(url)
            self.assertTrue(r["success"], r.get("error"))
            sub = get_subscription()
            self.assertEqual(sub["label"], expected,
                             f"Expected {expected!r} for {url!r}, got {sub['label']!r}")

    def test_unsubscribe_clears_record(self):
        from calendar_import import (
            subscribe_calendar_url, unsubscribe_calendar, get_subscription,
        )
        subscribe_calendar_url("https://calendar.example/feed.ics")
        self.assertTrue(get_subscription())
        r = unsubscribe_calendar()
        self.assertTrue(r["success"])
        self.assertEqual(get_subscription(), {})

    def test_refresh_without_subscription_returns_clear_error(self):
        from calendar_import import refresh_subscription
        r = refresh_subscription()
        self.assertFalse(r["success"])
        self.assertIn("subscribed", r["error"].lower())


if __name__ == "__main__":
    unittest.main()
