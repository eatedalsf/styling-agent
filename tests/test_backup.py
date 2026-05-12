"""
Tests for backup_tool.py — Wearly's persistence path on Streamlit Cloud.

Snapshots ALL five user-data files before each test class and restores
them after, so the suite never pollutes the demo state.

Run with:
    python -m unittest tests.test_backup
"""

import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backup_tool import (  # noqa: E402
    BACKUP_SECTIONS,
    export_user_data, export_user_data_bytes,
    import_user_data, is_wearly_backup,
    suggested_backup_filename,
    _find_data_file,
)


class _AllUserFilesSnapshotMixin:
    """
    Snapshot + restore every file backup_tool touches. The full
    round-trip tests need to write each file, so we need full isolation.
    """

    @classmethod
    def setUpClass(cls):
        cls._snapshots = {}
        for _key, (filename, _default) in BACKUP_SECTIONS.items():
            path = _find_data_file(filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cls._snapshots[path] = f.read()

    @classmethod
    def tearDownClass(cls):
        for path, original in cls._snapshots.items():
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

class TestExport(_AllUserFilesSnapshotMixin, unittest.TestCase):

    def test_export_has_format_header(self):
        b = export_user_data()
        self.assertEqual(b["_format"], "wearly-backup-v1")
        self.assertIn("exported_at", b)

    def test_export_contains_all_known_sections(self):
        b = export_user_data()
        for key in BACKUP_SECTIONS:
            self.assertIn(key, b, f"Backup is missing section: {key}")

    def test_export_bytes_is_valid_utf8_json(self):
        raw = export_user_data_bytes()
        self.assertIsInstance(raw, bytes)
        parsed = json.loads(raw.decode("utf-8"))
        self.assertEqual(parsed["_format"], "wearly-backup-v1")

    def test_suggested_filename_has_iso_date(self):
        fn = suggested_backup_filename()
        self.assertTrue(fn.startswith("wearly-backup-"))
        self.assertTrue(fn.endswith(".json"))
        # YYYY-MM-DD pattern
        import re
        self.assertRegex(fn, r"^wearly-backup-\d{4}-\d{2}-\d{2}\.json$")


# ─────────────────────────────────────────────
# IMPORT — validation + happy path
# ─────────────────────────────────────────────

class TestImportValidation(unittest.TestCase):
    """No data-file snapshots — these tests don't actually write."""

    def test_non_json_rejected(self):
        r = import_user_data(b"definitely not json")
        self.assertFalse(r["success"])
        self.assertIn("parse", r["error"].lower())

    def test_json_but_not_dict_rejected(self):
        r = import_user_data(b'["a", "b"]')
        self.assertFalse(r["success"])
        self.assertIn("top-level", r["error"].lower())

    def test_missing_format_header_rejected(self):
        r = import_user_data(b'{"user_wardrobe": {"clothing": []}}')
        self.assertFalse(r["success"])
        self.assertIn("wearly-backup-v1", r["error"])

    def test_wrong_format_version_rejected(self):
        r = import_user_data(b'{"_format": "wearly-backup-v99"}')
        self.assertFalse(r["success"])
        self.assertIn("wearly-backup-v1", r["error"])

    def test_is_wearly_backup_sniff(self):
        good = b'{"_format": "wearly-backup-v1", "user_wardrobe": {"clothing": []}}'
        bad  = b'{"random": "object"}'
        self.assertTrue(is_wearly_backup(good))
        self.assertFalse(is_wearly_backup(bad))


# ─────────────────────────────────────────────
# IMPORT — round-trip
# ─────────────────────────────────────────────

class TestRoundTrip(_AllUserFilesSnapshotMixin, unittest.TestCase):
    """
    Export → tweak → import → re-export should reflect the change.
    Restored sections must be readable by their respective tools.
    """

    def test_export_then_import_is_idempotent(self):
        # Take a snapshot of the current export, restore it, re-export,
        # confirm the two exports are equal modulo the timestamp.
        bundle_before = export_user_data()
        bundle_bytes  = json.dumps(bundle_before).encode("utf-8")

        r = import_user_data(bundle_bytes)
        self.assertTrue(r["success"], msg=r.get("error"))
        self.assertEqual(set(r["restored"]), set(BACKUP_SECTIONS.keys()))

        bundle_after = export_user_data()
        for key in BACKUP_SECTIONS:
            self.assertEqual(bundle_before[key], bundle_after[key],
                             f"Round-trip changed section: {key}")

    def test_import_overwrites_specific_section(self):
        # Build a bundle with a known wardrobe override; import it;
        # then confirm get_user_wardrobe reflects the override.
        bundle = {
            "_format": "wearly-backup-v1",
            "user_wardrobe": {
                "clothing": [{"id": "UC999", "type": "top", "name": "Backup Test Item",
                              "color": "test"}],
                "shoes": [],
                "accessories": [],
            },
        }
        r = import_user_data(json.dumps(bundle).encode("utf-8"))
        self.assertTrue(r["success"])
        self.assertIn("user_wardrobe", r["restored"])

        from wardrobe_tool import get_user_wardrobe
        ow = get_user_wardrobe()["user_wardrobe"]
        names = [it.get("name") for it in ow["clothing"]]
        self.assertIn("Backup Test Item", names)

    def test_import_with_missing_sections_partial(self):
        # Bundle has only one section; the others should be left untouched
        # (skipped, not zeroed out).
        from wardrobe_tool import get_user_wardrobe
        from shopping_tool import get_favorite_stores

        # Snapshot what's there now (after class setUp restored the originals)
        stores_before = get_favorite_stores()["stores"]

        bundle = {
            "_format": "wearly-backup-v1",
            "user_wardrobe": {"clothing": [], "shoes": [], "accessories": []},
            # favorite_stores intentionally omitted
        }
        r = import_user_data(json.dumps(bundle).encode("utf-8"))
        self.assertTrue(r["success"])
        self.assertIn("user_wardrobe", r["restored"])
        self.assertIn("favorite_stores", r["skipped"])

        stores_after = get_favorite_stores()["stores"]
        self.assertEqual(stores_before, stores_after,
                         "Sections not present in the bundle must be left alone.")

    def test_import_rejects_non_dict_section_silently(self):
        # A backup file that has a bad section type should skip that section
        # rather than blow up.
        bundle = {
            "_format": "wearly-backup-v1",
            "user_wardrobe": "this should be a dict",
            "favorite_stores": {"stores": []},
        }
        r = import_user_data(json.dumps(bundle).encode("utf-8"))
        self.assertTrue(r["success"])
        self.assertIn("user_wardrobe", r["skipped"])
        self.assertIn("favorite_stores", r["restored"])


# ─────────────────────────────────────────────
# AGENT INTEGRATION — imported wardrobe shows up in the agent pool
# ─────────────────────────────────────────────

class TestAgentSeesImportedItems(_AllUserFilesSnapshotMixin, unittest.TestCase):

    def test_imported_item_in_agent_pool(self):
        # Restore via backup_tool; the agent's filter_items_by_occasion
        # must see the new item.
        bundle = {
            "_format": "wearly-backup-v1",
            "user_wardrobe": {
                "clothing": [{"id": "UC555", "type": "top", "name": "Restored Test Blouse",
                              "color": "cream", "formality": "business",
                              "season": ["all"], "tags": ["work"]}],
                "shoes": [], "accessories": [],
            },
        }
        r = import_user_data(json.dumps(bundle).encode("utf-8"))
        self.assertTrue(r["success"])

        from wardrobe_tool import filter_items_by_occasion
        pool = filter_items_by_occasion("work", "fall")
        names = [i["name"] for i in pool["clothing"]]
        self.assertIn("Restored Test Blouse", names,
                      "After restore, the imported item must reach the agent's candidate pool.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
