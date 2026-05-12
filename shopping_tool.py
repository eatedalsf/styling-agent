"""
Tool 7: Shopping — Favorite Stores + Wishlist

Closes the shopping-gap loop in Wearly. When Step 6 detects a missing
required piece, the existing static SHOPPING_SUGGESTIONS list is now
augmented with a store-aware line that names the user's favorite stores.
Separately, the user can save any gap suggestion to a wishlist for
later acquisition.

No retailer scraping, no paid APIs, no secrets — this is a calm,
inspectable, local-only prototype.

Data files (both at the repo root, tracked with empty seed state):
  favorite_stores.json  → {"stores": [{name, url, notes}, ...]}
  wishlist.json         → {"items":  [{id, name, category, ...}, ...]}

Both writes are atomic (tempfile + os.replace) and read paths tolerate
missing or malformed files by falling back to empty collections.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date


# ─────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────

def _find_data_file(filename: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "data", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(here, filename)


STORES_PATH   = _find_data_file("favorite_stores.json")
WISHLIST_PATH = _find_data_file("wishlist.json")


_EMPTY_STORES   = {"stores": []}
_EMPTY_WISHLIST = {"items": []}


# ─────────────────────────────────────────────
# ATOMIC WRITE
# ─────────────────────────────────────────────

def _atomic_write_json(path: str, data: dict) -> None:
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".shopping_", suffix=".json", dir=dir_)
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
# FAVORITE STORES — READ
# ─────────────────────────────────────────────

def get_favorite_stores() -> dict:
    """
    Load the favorite-stores list. Tolerant of missing/malformed file.

    Returns: {"success": True, "stores": [...], "error": None | str}
    """
    if not os.path.exists(STORES_PATH):
        return {"success": True, "stores": [], "error": None}
    try:
        with open(STORES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        stores = list(data.get("stores", []))
        return {"success": True, "stores": stores, "error": None}
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": True, "stores": [],
            "error": f"favorite_stores.json unreadable ({e}); using empty.",
        }


# ─────────────────────────────────────────────
# FAVORITE STORES — WRITE
# ─────────────────────────────────────────────

def _normalize_store_name(name: str) -> str:
    return (name or "").strip()


def add_favorite_store(name: str, url: str = None, notes: str = None) -> dict:
    """
    Append a store to favorite_stores.json. Returns {success, store, error}.
    Duplicate names (case-insensitive) are rejected.
    """
    name = _normalize_store_name(name)
    if not name:
        return {"success": False, "store": None, "error": "Store name is required."}

    res = get_favorite_stores()
    stores = res["stores"]
    existing = {(s.get("name") or "").strip().lower() for s in stores}
    if name.lower() in existing:
        return {"success": False, "store": None, "error": f"'{name}' is already a favorite."}

    store = {
        "name":  name,
        "url":   (url or "").strip() or None,
        "notes": (notes or "").strip() or None,
    }
    stores.append(store)

    on_disk = {
        "_comment": "Favorite stores. Edited via the Shop section.",
        "stores": stores,
    }
    try:
        _atomic_write_json(STORES_PATH, on_disk)
    except Exception as e:
        return {"success": False, "store": None, "error": f"Failed to save: {e}"}
    return {"success": True, "store": store, "error": None}


def remove_favorite_store(name: str) -> dict:
    """Remove a favorite store by name (case-insensitive)."""
    name = _normalize_store_name(name)
    if not name:
        return {"success": False, "error": "Store name is required."}

    res = get_favorite_stores()
    stores = res["stores"]
    kept = [s for s in stores if (s.get("name") or "").strip().lower() != name.lower()]
    if len(kept) == len(stores):
        return {"success": False, "error": f"'{name}' was not in favorites."}

    on_disk = {
        "_comment": "Favorite stores. Edited via the Shop section.",
        "stores": kept,
    }
    try:
        _atomic_write_json(STORES_PATH, on_disk)
    except Exception as e:
        return {"success": False, "error": f"Failed to save: {e}"}
    return {"success": True, "stores": kept, "error": None}


# ─────────────────────────────────────────────
# WISHLIST — READ
# ─────────────────────────────────────────────

def get_wishlist() -> dict:
    """
    Load wishlist items. Tolerant of missing/malformed file.

    Returns: {"success": True, "items": [...], "error": None | str}
    """
    if not os.path.exists(WISHLIST_PATH):
        return {"success": True, "items": [], "error": None}
    try:
        with open(WISHLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = list(data.get("items", []))
        return {"success": True, "items": items, "error": None}
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": True, "items": [],
            "error": f"wishlist.json unreadable ({e}); using empty.",
        }


# ─────────────────────────────────────────────
# WISHLIST — WRITE
# ─────────────────────────────────────────────

VALID_PRIORITIES = ("low", "medium", "high")


def _next_wishlist_id(items: list) -> str:
    """Auto-increment W001, W002, ... based on existing items."""
    nums = []
    for it in items:
        iid = str(it.get("id", ""))
        if iid.startswith("W"):
            try:
                nums.append(int(iid[1:]))
            except ValueError:
                pass
    n = (max(nums) + 1) if nums else 1
    return f"W{n:03d}"


def add_wishlist_item(fields: dict) -> dict:
    """
    Append a wishlist item. Returns {success, item, error}.

    Accepted fields:
      name              str   (required — item name / gap description)
      category          str   (optional — top / bottom / dress / outerwear / …)
      preferred_store   str   (optional — name of a saved store; free text allowed)
      tags              list  (optional — occasion labels: ["work","dinner"])
      priority          str   (optional — "low" / "medium" / "high", default "medium")
      notes             str   (optional — free text)
      source_url        str   (optional — product URL)
      linked_gap        str   (optional — when added from a Step 6 wardrobe gap;
                                stores the gap type, e.g. "outerwear")

    The item record additionally gets:
      id           auto-generated W001, W002, …
      added_date   ISO date string of when it was saved
    """
    name = (fields.get("name") or "").strip()
    if not name:
        return {"success": False, "item": None, "error": "Wishlist item name is required."}

    priority = (fields.get("priority") or "medium").lower().strip()
    if priority not in VALID_PRIORITIES:
        priority = "medium"

    res = get_wishlist()
    items = res["items"]

    item = {
        "id":              _next_wishlist_id(items),
        "name":            name,
        "category":        (fields.get("category") or "").strip().lower() or None,
        "preferred_store": (fields.get("preferred_store") or "").strip() or None,
        "tags":            [t.lower() for t in (fields.get("tags") or []) if t],
        "priority":        priority,
        "notes":           (fields.get("notes") or "").strip() or None,
        "source_url":      (fields.get("source_url") or "").strip() or None,
        "linked_gap":      (fields.get("linked_gap") or "").strip().lower() or None,
        "added_date":      date.today().isoformat(),
    }
    items.append(item)

    on_disk = {
        "_comment": "Wishlist. Saved suggestions and items the user wants to acquire.",
        "items": items,
    }
    try:
        _atomic_write_json(WISHLIST_PATH, on_disk)
    except Exception as e:
        return {"success": False, "item": None, "error": f"Failed to save: {e}"}
    return {"success": True, "item": item, "error": None}


def remove_wishlist_item(item_id: str) -> dict:
    """Remove a wishlist item by id (case-sensitive — IDs are like W001)."""
    item_id = (item_id or "").strip()
    if not item_id:
        return {"success": False, "error": "Wishlist item id is required."}

    res = get_wishlist()
    items = res["items"]
    kept = [i for i in items if str(i.get("id", "")) != item_id]
    if len(kept) == len(items):
        return {"success": False, "error": f"Item '{item_id}' not found."}

    on_disk = {
        "_comment": "Wishlist. Saved suggestions and items the user wants to acquire.",
        "items": kept,
    }
    try:
        _atomic_write_json(WISHLIST_PATH, on_disk)
    except Exception as e:
        return {"success": False, "error": f"Failed to save: {e}"}
    return {"success": True, "items": kept, "error": None}


# ─────────────────────────────────────────────
# STORE-AWARE SUGGESTIONS (used by the agent)
# ─────────────────────────────────────────────

def store_aware_suggestions(base_suggestions: list, occasion_tag: str = None) -> list:
    """
    Return a copy of `base_suggestions` with an extra line tacked on
    that names the user's saved favorite stores (when any exist).

    The agent calls this from Step 6 once a wardrobe gap is detected.
    No retailer lookup is performed — this is a prototype hint, not a
    live shopping search. See book/08-shopping-gap-logic.md.
    """
    base_suggestions = list(base_suggestions or [])
    stores = get_favorite_stores().get("stores", [])
    if not stores:
        return base_suggestions
    names = [s.get("name", "").strip() for s in stores if s.get("name")]
    if not names:
        return base_suggestions
    if len(names) == 1:
        line = f"Check {names[0]} first — your saved favorite store."
    elif len(names) == 2:
        line = f"Check {names[0]} or {names[1]} first — your saved favorite stores."
    else:
        head = ", ".join(names[:-1])
        line = f"Check {head}, or {names[-1]} first — your saved favorite stores."
    return base_suggestions + [line]


def gap_is_on_wishlist(gap: str, occasion_tag: str = None) -> bool:
    """
    Return True when the user has already queued a wishlist item for
    this gap type (matched via linked_gap or category). Used by the
    UI to say "already on your wishlist" instead of re-suggesting.
    """
    if not gap:
        return False
    items = get_wishlist().get("items", [])
    g = gap.strip().lower()
    for it in items:
        if (it.get("linked_gap") or "").lower() == g:
            return True
        if (it.get("category") or "").lower() == g:
            return True
    return False
