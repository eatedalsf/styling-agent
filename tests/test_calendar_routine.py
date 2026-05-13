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

    def test_minimal_timed_event(self):
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
        events = parse_ics_text(ics)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["id"], "abc-123@wearly")
        self.assertEqual(ev["title"], "Team standup")
        self.assertEqual(ev["date"], "2026-05-12")
        self.assertEqual(ev["time"], "09:00")
        self.assertEqual(ev["type"], "work")        # "standup" keyword
        self.assertEqual(ev["formality"], "business")
        self.assertEqual(ev["source"], "ics")

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
