"""
Tool 8: Backup + Restore

Bundles every user-generated data file into a single JSON for export,
and restores from that JSON on import. This is the persistence path
on Streamlit Cloud (where the container filesystem is ephemeral —
saved items vanish on every container restart / redeploy).

Five files are covered:
  user_wardrobe.json   — manually added wardrobe items
  user_profile.json    — fit / style profile overlay
  wear_history.json    — worn-count + last-worn map
  favorite_stores.json — saved favorite retailers
  wishlist.json        — saved wishlist items

No new dependencies. No secrets. No paid APIs. The user owns their
data — they can inspect the backup file, edit it manually, share it
between devices, or version-control it themselves.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date


_FORMAT_HEADER = "wearly-backup-v1"


def _find_data_file(filename: str) -> str:
    """
    Locate a data file. Matches the helper pattern used in every other
    tool module so paths stay consistent across the repo.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, filename)


# Section key in the backup bundle → (filename on disk, default shape when missing)
BACKUP_SECTIONS = {
    "user_wardrobe":   ("user_wardrobe.json",
                        {"clothing": [], "shoes": [], "accessories": []}),
    "user_profile":    ("user_profile.json",
                        {"modesty_preference": None, "comfort_needs": [],
                         "style_goals": [], "highlight_features": [],
                         "balance_areas": []}),
    "wear_history":    ("wear_history.json",
                        {"history": {}}),
    "favorite_stores": ("favorite_stores.json",
                        {"stores": []}),
    "wishlist":        ("wishlist.json",
                        {"items": []}),
}


def _atomic_write_json(path: str, data: dict) -> None:
    """Write `data` as JSON to `path` via temp-file + rename."""
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".backup_restore_", suffix=".json", dir=dir_)
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


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def export_user_data() -> dict:
    """
    Read every user-data file from disk and return a single bundle
    dict the caller can serialize to JSON for download. Missing or
    malformed sections fall through to their default empty shapes so
    the bundle always has all five keys — easier for restore.
    """
    bundle = {
        "_format":     _FORMAT_HEADER,
        "exported_at": date.today().isoformat(),
        "note":        "Wearly backup. Re-upload this file on a fresh "
                       "Streamlit Cloud session to restore your closet.",
    }
    for key, (filename, default) in BACKUP_SECTIONS.items():
        path = _find_data_file(filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                bundle[key] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            # Missing or malformed → use the default empty shape so the
            # downloaded bundle is always self-contained.
            bundle[key] = dict(default)
    return bundle


def export_user_data_bytes() -> bytes:
    """Convenience wrapper for st.download_button: returns UTF-8 bytes."""
    return json.dumps(export_user_data(), indent=2, ensure_ascii=False).encode("utf-8")


def suggested_backup_filename() -> str:
    """Return a stable, dated filename for the download button."""
    return f"wearly-backup-{date.today().isoformat()}.json"


# ─────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────

def _validate_bundle(raw_bytes: bytes) -> tuple:
    """
    Parse raw JSON bytes into a bundle dict. Return (bundle, error_msg).
    Either bundle is a dict OR error_msg is a string explaining why
    the input couldn't be accepted.
    """
    try:
        text = raw_bytes.decode("utf-8") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)
        bundle = json.loads(text)
    except Exception as e:
        return None, f"Could not parse the upload as JSON ({e})."

    if not isinstance(bundle, dict):
        return None, "The uploaded file is not a Wearly backup (top-level must be an object)."

    fmt = bundle.get("_format")
    if fmt != _FORMAT_HEADER:
        return None, (
            f"This file doesn't look like a Wearly backup. Expected "
            f"\"_format\": \"{_FORMAT_HEADER}\", got {fmt!r}. "
            f"Use the Export button to produce a valid backup."
        )

    return bundle, None


def import_user_data(raw_bytes: bytes) -> dict:
    """
    Restore each known section from a backup bundle. Returns:
      {"success": True, "restored": ["user_wardrobe", "wishlist", …],
       "skipped": [], "error": None}
    or
      {"success": False, "restored": [], "skipped": [], "error": "<reason>"}

    Each section is written atomically. A failure on one section
    short-circuits and reports which sections HAD been restored before
    the failure — so the caller can show partial success honestly.
    """
    bundle, err = _validate_bundle(raw_bytes)
    if err:
        return {"success": False, "restored": [], "skipped": [], "error": err}

    restored, skipped = [], []

    for key, (filename, _default) in BACKUP_SECTIONS.items():
        if key not in bundle:
            skipped.append(key)
            continue
        section = bundle[key]
        if not isinstance(section, dict):
            skipped.append(key)
            continue
        path = _find_data_file(filename)
        try:
            _atomic_write_json(path, section)
            restored.append(key)
        except Exception as e:
            return {
                "success": False,
                "restored": restored,
                "skipped": skipped,
                "error": f"Failed to write {filename}: {e}",
            }

    return {"success": True, "restored": restored, "skipped": skipped, "error": None}


def is_wearly_backup(raw_bytes: bytes) -> bool:
    """Quick sniff: does this look like a Wearly backup? Used by the UI
    to enable/disable the Restore button before parsing."""
    bundle, err = _validate_bundle(raw_bytes)
    return err is None
