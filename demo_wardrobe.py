"""
demo_wardrobe.py — bulk loader for the curated demo wardrobe.

The dataset lives in `demo_wardrobe.json` (committed to the repo).
Loading it into the running app:

    from demo_wardrobe import load_demo_wardrobe, unload_demo_wardrobe
    result = load_demo_wardrobe()
    # result = {"added": [...], "skipped": [...], "total_after": N,
    #           "image_errors": [...], "error": None}

What the loader does:
  1. Reads `demo_wardrobe.json`.
  2. For each item, generates a polished colored-card PNG to
     `wardrobe_images/<id>.png` using Pillow — no network needed,
     no external retailer fetches, stable across machines.
  3. Merges the item into `user_wardrobe.json` via direct write
     (NOT through save_user_item, because we want STABLE DM-* IDs
     instead of the auto-numbered UC###).
  4. Deduplication: items whose `id` already exists in the user
     wardrobe are skipped — running the loader twice is a no-op.
  5. Existing user-added items (UC### / US### / UA###) are NEVER
     touched.

Wired into the Streamlit app as a Wardrobe-screen button so the
user can populate a rich demo wardrobe with one click and remove
it just as easily.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from typing import Any, Dict, List


# ── Locations ─────────────────────────────────────────────

def _repo_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


DEMO_JSON_PATH       = os.path.join(_repo_root(), "demo_wardrobe.json")
WARDROBE_IMAGES_DIR  = os.path.join(_repo_root(), "wardrobe_images")
DEMO_ID_PREFIX       = "DM-"


# ── Color palette (kept aligned with wardrobe_tool.NAMED_COLORS
#    and app.py COLOR_HEX so cards visually match other surfaces) ──

_DEMO_PALETTE = {
    "ivory":      "#F1E7D6",
    "cream":      "#EFE3CC",
    "white":      "#F4EFE8",
    "beige":      "#D6C3A4",
    "tan":        "#C9A77F",
    "nude":       "#D9BFA7",
    "camel":      "#B89878",
    "olive":      "#7A7548",
    "sage":       "#9DA88B",
    "gold":       "#C9A968",
    "burgundy":   "#6B2C2A",
    "red":        "#A03A32",
    "rust":       "#A85A3C",
    "terracotta": "#C17F5A",
    "forest":     "#3E5C44",
    "navy":       "#1F2A44",
    "blue":       "#4A6FA5",
    "black":      "#1C1917",
    "charcoal":   "#2E2A27",
    "grey":       "#9A938C",
    "silver":     "#BFC1C2",
}


def _hex_for(color_name: str) -> str:
    """Resolve a color name to a hex. Falls back to a neutral tan when
    we don't know — keeps card generation crash-free."""
    if not color_name:
        return "#C9A77F"
    c = color_name.lower().strip()
    if c in _DEMO_PALETTE:
        return _DEMO_PALETTE[c]
    # Token fallback for compound colors like "warm camel" or "ice blue".
    for token in c.split():
        if token in _DEMO_PALETTE:
            return _DEMO_PALETTE[token]
    return "#C9A77F"


def _hex_to_rgb(hex_str: str) -> tuple:
    s = hex_str.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _luminance(rgb: tuple) -> float:
    """ITU-R BT.601 — keeps text legible on both light and dark cards."""
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0


# ── Card image generator ──────────────────────────────────

def _generate_card_image(item: Dict[str, Any], size: tuple = (320, 400)) -> bytes:
    """
    Render a polished colored-card PNG for a single demo item.
    Returns PNG bytes. Self-contained — only depends on Pillow,
    which the rest of the app already needs.

    Card layout:
        - Full-bleed background = item color.
        - Small category badge (top-left, pill).
        - Item name + " · " + store, centered, contrast-adjusted.
        - Color name in a faint footer line.

    Body-positive language is enforced upstream in the JSON; this
    function only renders what's there.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return b""

    w, h = size
    bg_hex = _hex_for(item.get("color", ""))
    bg_rgb = _hex_to_rgb(bg_hex)
    lum = _luminance(bg_rgb)
    fg = (28, 25, 23) if lum > 0.55 else (244, 239, 232)        # ink or paper

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Subtle inner border so cards read as "cards" even on a
    # white-on-white site background.
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline=(0, 0, 0, 30), width=1)

    # Top-left category badge (small uppercase pill).
    category_label = (item.get("type") or "").upper() or "ITEM"
    try:
        badge_font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        badge_font = ImageFont.load_default()
    pad_x, pad_y = 10, 6
    # Width via textbbox so we can size the rounded pill.
    bbox = draw.textbbox((0, 0), category_label, font=badge_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2
    pill_x = 14
    pill_y = 14
    pill_bg = (244, 239, 232) if lum < 0.55 else (28, 25, 23)
    pill_fg = (28, 25, 23) if lum < 0.55 else (244, 239, 232)
    try:
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            radius=99, fill=pill_bg,
        )
    except AttributeError:                                      # older PIL
        draw.rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], fill=pill_bg,
        )
    draw.text((pill_x + pad_x, pill_y + pad_y), category_label,
              font=badge_font, fill=pill_fg)

    # Item name (centered, large, serif if available).
    name = item.get("name", "Item")
    store = item.get("source_store", "")
    try:
        name_font   = ImageFont.truetype("georgia.ttf", 21)
        store_font  = ImageFont.truetype("arial.ttf", 12)
        color_font  = ImageFont.truetype("arial.ttf", 10)
    except Exception:
        name_font   = ImageFont.load_default()
        store_font  = ImageFont.load_default()
        color_font  = ImageFont.load_default()

    # Wrap the name to ~2-3 lines so long names don't overflow.
    def _wrap(text, font, max_w):
        words = text.split()
        lines, cur = [], ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            bbox_ = draw.textbbox((0, 0), test, font=font)
            test_w = bbox_[2] - bbox_[0]
            if test_w <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w_
        if cur: lines.append(cur)
        return lines[:3]

    name_lines = _wrap(name, name_font, w - 60)
    line_h = name_font.size + 6
    total_h = line_h * len(name_lines)
    y = (h - total_h) // 2 - 10
    for line in name_lines:
        bbox = draw.textbbox((0, 0), line, font=name_font)
        lw = bbox[2] - bbox[0]
        draw.text(((w - lw) // 2, y), line, font=name_font, fill=fg)
        y += line_h

    if store:
        bbox = draw.textbbox((0, 0), store, font=store_font)
        lw = bbox[2] - bbox[0]
        draw.text(((w - lw) // 2, y + 4), store, font=store_font,
                  fill=tuple(int(c * 0.7 if lum > 0.55 else (c + 60))
                             for c in fg))

    # Footer color name.
    color_label = (item.get("color") or "").upper()
    if color_label:
        bbox = draw.textbbox((0, 0), color_label, font=color_font)
        lw = bbox[2] - bbox[0]
        draw.text(((w - lw) // 2, h - 28), color_label, font=color_font,
                  fill=fg)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _save_card(item: Dict[str, Any]) -> str:
    """Save a generated card and return the relative path stored in the
    item record. Empty string on failure."""
    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)
    item_id = item.get("id", "")
    if not item_id:
        return ""
    png_bytes = _generate_card_image(item)
    if not png_bytes:
        return ""
    out_path = os.path.join(WARDROBE_IMAGES_DIR, f"{item_id}.png")
    try:
        with open(out_path, "wb") as f:
            f.write(png_bytes)
    except OSError:
        return ""
    return f"wardrobe_images/{item_id}.png"


# ── Loader / unloader ─────────────────────────────────────

def _load_demo_seed() -> dict:
    if not os.path.exists(DEMO_JSON_PATH):
        return {"clothing": [], "shoes": [], "accessories": []}
    with open(DEMO_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_user_overlay() -> dict:
    try:
        from wardrobe_tool import USER_DATA_PATH
    except Exception:
        return {"clothing": [], "shoes": [], "accessories": []}
    if not os.path.exists(USER_DATA_PATH):
        return {"clothing": [], "shoes": [], "accessories": []}
    try:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"clothing": [], "shoes": [], "accessories": []}


def _persist_user_overlay(overlay: dict) -> None:
    """Atomic write to user_wardrobe.json. Mirrors wardrobe_tool's
    `_atomic_write_json` style — temp file + rename."""
    from wardrobe_tool import USER_DATA_PATH
    if "_comment" not in overlay:
        overlay = {
            "_comment": ("User-added wardrobe items. Edited by the Wardrobe "
                         "Builder + the demo-wardrobe loader."),
            **overlay,
        }
    dir_ = os.path.dirname(os.path.abspath(USER_DATA_PATH)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".user_wardrobe_demo_",
                                suffix=".json", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(overlay, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, USER_DATA_PATH)
    except Exception:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
        raise


def _section_for_type(item_type: str) -> str:
    t = (item_type or "").lower()
    if t in ("top", "bottom", "dress", "outerwear", "activewear"):
        return "clothing"
    if t == "shoes":
        return "shoes"
    if t == "accessory":
        return "accessories"
    return "clothing"


def load_demo_wardrobe() -> dict:
    """
    Merge every item from `demo_wardrobe.json` into user_wardrobe.json.

    Returns::

        {
          "added":          [item_id, ...],
          "skipped":        [item_id, ...],   # already present
          "total_after":    int,
          "image_errors":   [item_id, ...],   # PNG generation failed
          "error":          str | None,
        }

    Items already present (by id) are skipped — running this twice is
    a no-op. User-added items (UC### / US### / UA###) are never
    touched.
    """
    try:
        seed = _load_demo_seed()
    except Exception as e:
        return {"added": [], "skipped": [], "total_after": 0,
                "image_errors": [], "error": f"Could not read demo seed: {e}"}

    overlay = _load_user_overlay()
    overlay.setdefault("clothing", [])
    overlay.setdefault("shoes", [])
    overlay.setdefault("accessories", [])

    # Index existing IDs across all three sections.
    existing_ids = set()
    for section in ("clothing", "shoes", "accessories"):
        for it in overlay.get(section, []):
            if isinstance(it, dict) and it.get("id"):
                existing_ids.add(it["id"])

    added:   List[str] = []
    skipped: List[str] = []
    img_err: List[str] = []

    all_seed_items = (
        list(seed.get("clothing", []))
        + list(seed.get("shoes", []))
        + list(seed.get("accessories", []))
    )

    for item in all_seed_items:
        if not isinstance(item, dict):
            continue
        iid = item.get("id", "")
        if not iid:
            continue
        if iid in existing_ids:
            skipped.append(iid)
            continue

        # Generate the card image. Errors are non-fatal — the item
        # still loads, just without a visual.
        image_path = _save_card(item)
        if not image_path:
            img_err.append(iid)

        # Build the item record with the canonical wardrobe shape.
        record = {
            "id":           iid,
            "type":         item.get("type", "top"),
            "name":         item.get("name", "Demo item"),
            "color":        item.get("color", ""),
            "formality":    item.get("formality", "casual"),
            "season":       item.get("season") or ["all"],
            "tags":         item.get("tags") or ["casual"],
            "availability": "available",
            "source":       "demo",
        }
        for opt_key in ("fabric", "silhouette", "style_notes",
                        "fit_notes", "source_store"):
            if item.get(opt_key):
                record[opt_key] = item[opt_key]
        if image_path:
            record["image_path"] = image_path

        section = _section_for_type(item.get("type"))
        overlay[section].append(record)
        existing_ids.add(iid)
        added.append(iid)

    if added:
        try:
            _persist_user_overlay(overlay)
        except Exception as e:
            return {"added": [], "skipped": skipped,
                    "total_after": 0, "image_errors": img_err,
                    "error": f"Save failed: {e}"}

    total_after = sum(len(overlay.get(s, [])) for s in
                      ("clothing", "shoes", "accessories"))
    return {
        "added":         added,
        "skipped":       skipped,
        "total_after":   total_after,
        "image_errors":  img_err,
        "error":         None,
    }


def unload_demo_wardrobe() -> dict:
    """
    Remove every DM-* item from user_wardrobe.json. Leaves user-added
    items (UC### / US### / UA###) intact. Also deletes the cached
    card PNGs.
    """
    overlay = _load_user_overlay()
    removed: List[str] = []
    for section in ("clothing", "shoes", "accessories"):
        kept = []
        for it in overlay.get(section, []):
            iid = it.get("id", "") if isinstance(it, dict) else ""
            if iid.startswith(DEMO_ID_PREFIX):
                removed.append(iid)
                # Best-effort image cleanup.
                img_path = os.path.join(WARDROBE_IMAGES_DIR, f"{iid}.png")
                try:
                    if os.path.exists(img_path):
                        os.remove(img_path)
                except OSError:
                    pass
            else:
                kept.append(it)
        overlay[section] = kept

    try:
        _persist_user_overlay(overlay)
    except Exception as e:
        return {"removed": removed, "error": f"Save failed: {e}"}

    return {"removed": removed, "error": None}


def is_demo_loaded() -> bool:
    """True iff at least one DM-* item is present in the user overlay."""
    overlay = _load_user_overlay()
    for section in ("clothing", "shoes", "accessories"):
        for it in overlay.get(section, []):
            if isinstance(it, dict) and \
                    (it.get("id") or "").startswith(DEMO_ID_PREFIX):
                return True
    return False
