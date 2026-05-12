"""
Data-integrity tests for the JSON files shipped with Wearly. Catches
shape regressions (missing keys, bad cross-references) early.

Run with:
    python -m unittest tests.test_data_integrity
"""

import json
import os
import sys
import unittest
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _load(name):
    with open(os.path.join(_ROOT, name), "r", encoding="utf-8") as f:
        return json.load(f)


class TestWardrobeJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = _load("wardrobe.json")

    def test_top_level_keys(self):
        for key in ("owner", "clothing", "shoes", "accessories"):
            self.assertIn(key, self.w, f"wardrobe.json missing top-level key: {key}")

    def test_owner_fields(self):
        owner = self.w["owner"]
        for key in ("name", "body_shape", "skin_tone", "style_preferences"):
            self.assertIn(key, owner)

    def test_every_item_has_id_name_type(self):
        for section in ("clothing", "shoes", "accessories"):
            for item in self.w[section]:
                self.assertIn("id", item, f"{section} item missing id: {item}")
                self.assertIn("name", item)
                # 'type' is required for clothing; shoes/accessories don't always have it.
                if section == "clothing":
                    self.assertIn("type", item)

    def test_ids_are_unique(self):
        all_ids = []
        for section in ("clothing", "shoes", "accessories"):
            for item in self.w[section]:
                all_ids.append(item["id"])
        self.assertEqual(len(all_ids), len(set(all_ids)),
                         "Duplicate item IDs detected across wardrobe.json sections.")


class TestCalendarEventsJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _load("calendar_events.json")

    def test_is_list(self):
        self.assertIsInstance(self.events, list)
        self.assertGreater(len(self.events), 0,
                           "calendar_events.json should have at least one demo event.")

    def test_each_event_has_required_fields(self):
        for ev in self.events:
            for key in ("id", "title", "date", "type"):
                self.assertIn(key, ev, f"Event missing key: {key} in {ev}")

    def test_dates_are_iso(self):
        for ev in self.events:
            try:
                datetime.strptime(ev["date"], "%Y-%m-%d")
            except ValueError:
                self.fail(f"Event date is not YYYY-MM-DD: {ev['date']}")


class TestColorRulesJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = _load("color_rules.json")

    def test_at_least_one_skin_tone(self):
        self.assertGreater(len(self.rules), 0,
                           "color_rules.json should define at least one skin tone.")

    def test_each_tone_has_palettes(self):
        for tone, rules in self.rules.items():
            for key in ("best_colors", "good_colors", "avoid_colors"):
                self.assertIn(key, rules, f"Skin tone '{tone}' missing palette: {key}")
                self.assertIsInstance(rules[key], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
