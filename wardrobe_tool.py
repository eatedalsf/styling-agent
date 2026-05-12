"""
Tool 3: Wardrobe Reader / Writer

Reads wardrobe inventory and filters items by formality, season, and
occasion tags. The "wardrobe" the agent sees is the union of two files:

  - wardrobe.json       — the seed wardrobe (owner profile + demo items)
  - user_wardrobe.json  — items the user has added via the Wardrobe Builder

Both live at the repo root in the current flat layout. The user file is
created on first save if it doesn't exist. Reads tolerate a missing or
malformed user file by falling back to an empty overlay — the seed
wardrobe is never the failure point.
"""

import json
import os
import tempfile


# ─────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────

def _find_data_file(filename):
    """Locate a data file in either the structured (data/) or flat layout."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "data", filename),
        os.path.join(here, "..", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


def _user_wardrobe_path():
    """
    Locate user_wardrobe.json (creating its preferred path if needed).
    Mirrors _find_data_file but prefers the same directory as the seed
    wardrobe so the two files always live side by side.
    """
    seed_path = _find_data_file("wardrobe.json")
    seed_dir = os.path.dirname(os.path.abspath(seed_path))
    return os.path.join(seed_dir, "user_wardrobe.json")


def _wardrobe_images_dir():
    """Path to the per-item image storage directory (created on demand)."""
    seed_path = _find_data_file("wardrobe.json")
    seed_dir = os.path.dirname(os.path.abspath(seed_path))
    return os.path.join(seed_dir, "wardrobe_images")


DATA_PATH = _find_data_file("wardrobe.json")
USER_DATA_PATH = _user_wardrobe_path()
WARDROBE_IMAGES_DIR = _wardrobe_images_dir()


# ─────────────────────────────────────────────
# IMAGE UNDERSTANDING — Pillow only, no external models
# ─────────────────────────────────────────────
#
# This is deliberately lightweight. Pillow is already a Streamlit
# transitive dependency, so no install cost. We extract dominant colors
# via PIL's quantizer and map each candidate to the closest named color
# in NAMED_COLORS by Euclidean distance in RGB space.
#
# What we DO NOT attempt (out of safe-on-Streamlit-Cloud scope):
#   - Garment category recognition (would need a CNN or hosted vision API).
#   - True background removal (would need rembg + onnxruntime, ~120MB).
#   - Style / formality detection (no reliable classical-CV path).
#
# Production path is documented in book/05-wardrobe-intelligence.md.

NAMED_COLORS = {
    "white":         "#F4EFE8",
    "ivory":         "#F1E7D6",
    "cream":         "#EFE3CC",
    "beige":         "#D6C3A4",
    "black":         "#1C1917",
    "charcoal":      "#2E2A27",
    "grey":          "#9A938C",
    "navy":          "#1F2A44",
    "dark indigo":   "#1F2347",
    "blue":          "#4A6FA5",
    "pale blue":     "#B5C9D9",
    "olive":         "#7A7548",
    "sage green":    "#9DA88B",
    "camel":         "#B89878",
    "tan":           "#C9A77F",
    "nude":          "#D9BFA7",
    "blush":         "#E5BBAD",
    "pink":          "#E8B6B0",
    "burgundy":      "#6B2C2A",
    "red":           "#A03A32",
    "rust":          "#A85A3C",
    "terracotta":    "#C17F5A",
    "burnt orange":  "#B2562E",
    "mustard":       "#C9A33E",
    "gold":          "#C9A968",
    "silver":        "#BFC1C2",
    "white/gold":    "#E8DAA8",
}


def _hex_to_rgb(hex_str: str):
    s = hex_str.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def _closest_named_color(rgb):
    """Return (name, hex, distance) of the closest entry in NAMED_COLORS."""
    r, g, b = rgb
    best = None
    for name, hex_str in NAMED_COLORS.items():
        nr, ng, nb = _hex_to_rgb(hex_str)
        dist = ((r - nr) ** 2 + (g - ng) ** 2 + (b - nb) ** 2) ** 0.5
        if best is None or dist < best[2]:
            best = (name, hex_str, dist)
    return best


def suggest_colors_from_image(image_bytes: bytes, top_n: int = 3) -> dict:
    """
    Return up to `top_n` suggested color names from an uploaded image.

    Result shape:
        {
          "success": True,
          "suggestions": [
            {"name": "camel", "hex": "#B89878", "rgb": (185,152,120),
             "weight": 0.41, "distance": 24.5},
            ...
          ],
          "error": None,
        }

    Method: resize to 80×80, quantize to 8 colors, count pixels per
    quantized color, snap each to the closest NAMED_COLORS entry,
    deduplicate by name (keep the heaviest hit per name), rank by weight.
    """
    try:
        from PIL import Image
        import io as _io
    except ImportError as e:
        return {"success": False, "suggestions": [], "error": f"Pillow not available: {e}"}

    try:
        img = Image.open(_io.BytesIO(image_bytes))
        img = img.convert("RGB")
        # Resize for speed; preserve aspect ratio.
        img.thumbnail((96, 96))
        # Quantize to a small adaptive palette so similar pixels collapse.
        quant = img.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
        palette = quant.getpalette() or []
        counts = quant.getcolors() or []
    except Exception as e:
        return {"success": False, "suggestions": [], "error": f"Could not decode image: {e}"}

    total = sum(c for c, _ in counts) or 1
    raw = []
    for count, idx in counts:
        base = idx * 3
        if base + 2 >= len(palette):
            continue
        rgb = (palette[base], palette[base + 1], palette[base + 2])
        name, hex_str, dist = _closest_named_color(rgb)
        raw.append({
            "name":     name,
            "hex":      hex_str,
            "rgb":      rgb,
            "weight":   count / total,
            "distance": round(dist, 1),
        })

    # Deduplicate by name — keep the heaviest hit per named color.
    by_name = {}
    for c in raw:
        prev = by_name.get(c["name"])
        if prev is None or c["weight"] > prev["weight"]:
            by_name[c["name"]] = c

    ranked = sorted(by_name.values(), key=lambda c: -c["weight"])
    return {"success": True, "suggestions": ranked[:top_n], "error": None}


def _compose_on_white(pil_image):
    """If image has alpha, composite onto white background; else return RGB."""
    from PIL import Image  # local import — keeps CLI path PIL-free
    if pil_image.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", pil_image.size, (255, 255, 255))
        alpha = pil_image.split()[-1]
        bg.paste(pil_image.convert("RGB"), mask=alpha)
        return bg
    return pil_image.convert("RGB")


def _save_image_for_item(item_id: str, image_bytes: bytes,
                         max_dimension: int = 1024) -> str:
    """
    Save the uploaded image for `item_id` under WARDROBE_IMAGES_DIR.
    Composites alpha onto white, downscales to fit max_dimension.
    Returns the *relative* path (suitable for storing in the JSON record).
    """
    from PIL import Image
    import io as _io

    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)
    img = Image.open(_io.BytesIO(image_bytes))
    img = _compose_on_white(img)

    # Downscale if larger than max_dimension on the longest side.
    w, h = img.size
    longest = max(w, h)
    if longest > max_dimension:
        scale = max_dimension / longest
        img = img.resize((int(w * scale), int(h * scale)))

    out_path = os.path.join(WARDROBE_IMAGES_DIR, f"{item_id}.png")
    img.save(out_path, format="PNG", optimize=True)

    # Return a path relative to the repo root for portability.
    return os.path.relpath(out_path, os.path.dirname(WARDROBE_IMAGES_DIR)).replace(os.sep, "/")


# ─────────────────────────────────────────────
# READ — seed + user overlay
# ─────────────────────────────────────────────

_EMPTY_USER_OVERLAY = {"clothing": [], "shoes": [], "accessories": []}


def get_user_wardrobe() -> dict:
    """
    Return the user-added overlay. Tolerant of:
      - missing file (returns empty overlay)
      - malformed JSON (returns empty overlay, error string set)
    """
    if not os.path.exists(USER_DATA_PATH):
        return {"success": True, "user_wardrobe": dict(_EMPTY_USER_OVERLAY), "error": None}
    try:
        with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Drop the optional _comment key and ensure all three sections exist.
        normalized = {
            "clothing":    list(data.get("clothing", [])),
            "shoes":       list(data.get("shoes", [])),
            "accessories": list(data.get("accessories", [])),
        }
        return {"success": True, "user_wardrobe": normalized, "error": None}
    except (json.JSONDecodeError, OSError) as e:
        return {
            "success": True,  # soft failure — caller still gets an empty overlay
            "user_wardrobe": dict(_EMPTY_USER_OVERLAY),
            "error": f"user_wardrobe.json unreadable ({e}); using empty overlay.",
        }


def get_wardrobe() -> dict:
    """
    Return the merged wardrobe (seed + user overlay).
    The shape matches the original seed wardrobe.json contract:
      { "owner": {...}, "clothing": [...], "shoes": [...], "accessories": [...] }
    """
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            seed = json.load(f)
    except FileNotFoundError:
        return {"success": False, "wardrobe": None, "error": "Wardrobe data file not found."}
    except json.JSONDecodeError:
        return {"success": False, "wardrobe": None, "error": "Wardrobe data is malformed."}

    overlay_result = get_user_wardrobe()
    overlay = overlay_result["user_wardrobe"]

    merged = {
        "owner":       seed.get("owner", {}),
        "clothing":    list(seed.get("clothing", []))    + overlay["clothing"],
        "shoes":       list(seed.get("shoes", []))       + overlay["shoes"],
        "accessories": list(seed.get("accessories", [])) + overlay["accessories"],
    }
    return {"success": True, "wardrobe": merged, "error": overlay_result.get("error")}


def get_owner_profile() -> dict:
    result = get_wardrobe()
    if not result["success"]:
        return result
    return {"success": True, "profile": result["wardrobe"]["owner"], "error": None}


# ─────────────────────────────────────────────
# WRITE — user overlay only
# ─────────────────────────────────────────────

_SECTION_BY_CATEGORY = {
    "top":         "clothing",
    "bottom":      "clothing",
    "dress":       "clothing",
    "outerwear":   "clothing",
    "activewear":  "clothing",
    "shoes":       "shoes",
    "accessory":   "accessories",
}

_ID_PREFIX_BY_SECTION = {
    "clothing":    "UC",
    "shoes":       "US",
    "accessories": "UA",
}


def _atomic_write_json(path: str, data: dict) -> None:
    """
    Write `data` as JSON to `path` via a temp file + rename. Atomic on
    POSIX and Windows (Python 3.3+) so a crash mid-write can't leave
    `path` in a half-written state.
    """
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".user_wardrobe_", suffix=".json", dir=dir_)
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


def _next_user_id(overlay: dict, section: str) -> str:
    """Generate the next per-section user item ID, e.g. UC001, US001, UA001."""
    prefix = _ID_PREFIX_BY_SECTION[section]
    existing = []
    for it in overlay.get(section, []):
        iid = str(it.get("id", ""))
        if iid.startswith(prefix):
            try:
                existing.append(int(iid[len(prefix):]))
            except ValueError:
                pass
    next_n = (max(existing) + 1) if existing else 1
    return f"{prefix}{next_n:03d}"


def save_user_item(category: str, item_fields: dict,
                   image_bytes: bytes = None,
                   link_metadata: dict = None) -> dict:
    """
    Persist a user-entered item into user_wardrobe.json. Returns
    {success, item, error}.

    `category` must be one of the keys in _SECTION_BY_CATEGORY:
        top, bottom, dress, outerwear, activewear, shoes, accessory.

    `item_fields` is a dict that should include at minimum:
        name        (str, required)
        color       (str, required)
        formality   (str, optional)
        season      (list[str], optional — defaults to ["all"])
        tags        (list[str], optional — defaults to [category])
        availability (str, optional — defaults to "available")

    `image_bytes` is optional. When present, the bytes are composited
    onto white, downscaled to ≤1024px on the longest side, saved as PNG
    under WARDROBE_IMAGES_DIR, and the resulting relative path is
    recorded in item["image_path"].

    `link_metadata` is optional. When present, the following keys are
    recorded on the saved item (each is optional individually):
        source_url        original product URL
        source_store      brand/store inferred from URL host
        source_image_url  og:image URL (NOT downloaded — just recorded)
    """
    category = (category or "").lower().strip()
    if category not in _SECTION_BY_CATEGORY:
        return {
            "success": False, "item": None,
            "error": f"Unknown category '{category}'. Expected one of: {', '.join(_SECTION_BY_CATEGORY)}.",
        }

    name = (item_fields.get("name") or "").strip()
    color = (item_fields.get("color") or "").strip()
    if not name:
        return {"success": False, "item": None, "error": "Item name is required."}
    if not color:
        return {"success": False, "item": None, "error": "Item color is required."}

    section = _SECTION_BY_CATEGORY[category]

    # Load current overlay so we can extend it (and to compute the next id).
    overlay_result = get_user_wardrobe()
    overlay = overlay_result["user_wardrobe"]

    item = {
        "id":          _next_user_id(overlay, section),
        "type":        category,
        "name":        name,
        "color":       color,
        "formality":   (item_fields.get("formality") or "casual").lower(),
        "season":      [s.lower() for s in (item_fields.get("season") or ["all"])] or ["all"],
        "tags":        [t.lower() for t in (item_fields.get("tags") or [category])],
        "availability": (item_fields.get("availability") or "available").lower(),
        "source":      "user",
    }

    if image_bytes:
        try:
            item["image_path"] = _save_image_for_item(item["id"], image_bytes)
        except Exception as e:
            # Image save is non-fatal — the item still saves, just without
            # an image. Surface the issue in the response so the UI can
            # show a soft warning.
            item["image_path"] = None
            item.setdefault("_image_error", str(e))

    if link_metadata:
        # Each of these is optional individually — only record present values.
        if link_metadata.get("source_url"):
            item["source_url"] = str(link_metadata["source_url"])
        if link_metadata.get("source_store"):
            item["source_store"] = str(link_metadata["source_store"])
        if link_metadata.get("source_image_url"):
            item["source_image_url"] = str(link_metadata["source_image_url"])

    overlay[section].append(item)

    # Reconstruct the on-disk shape with the comment preserved.
    on_disk = {
        "_comment": "User-added wardrobe items. Created and maintained by the Wardrobe Builder. Items here are MERGED with wardrobe.json at read time by wardrobe_tool.get_wardrobe().",
        "clothing":    overlay["clothing"],
        "shoes":       overlay["shoes"],
        "accessories": overlay["accessories"],
    }

    try:
        _atomic_write_json(USER_DATA_PATH, on_disk)
    except Exception as e:
        return {"success": False, "item": None, "error": f"Failed to save: {e}"}

    return {"success": True, "item": item, "error": None}


# ─────────────────────────────────────────────
# FILTER + GAPS (unchanged behavior, now over merged wardrobe)
# ─────────────────────────────────────────────

def filter_items_by_occasion(occasion_tag: str, season: str = "all") -> dict:
    result = get_wardrobe()
    if not result["success"]:
        return result

    wardrobe = result["wardrobe"]
    tag = occasion_tag.lower()

    def matches(item):
        # Only available items are eligible. Items without an availability
        # field (e.g. seed items) are treated as available by default.
        if item.get("availability", "available").lower() not in ("available", ""):
            return False
        item_tags = [t.lower() for t in item.get("tags", [])]
        item_seasons = [s.lower() for s in item.get("season", ["all"])]
        tag_match = tag in item_tags or any(tag in t for t in item_tags)
        season_match = "all" in item_seasons or season.lower() in item_seasons or season == "all"
        return tag_match and season_match

    clothing = [i for i in wardrobe.get("clothing", []) if matches(i)]
    shoes = [i for i in wardrobe.get("shoes", []) if matches(i)]
    accessories = [i for i in wardrobe.get("accessories", []) if matches(i)]

    if not clothing:
        clothing = [i for i in wardrobe.get("clothing", []) if tag in [t.lower() for t in i.get("tags", [])]]

    return {
        "success": True,
        "error": None,
        "clothing": clothing,
        "shoes": shoes,
        "accessories": accessories,
        "occasion_tag": occasion_tag
    }


def check_gaps(outfit_pieces: list, required_types: list) -> list:
    covered = {piece.get("type", "").lower() for piece in outfit_pieces}
    missing = [t for t in required_types if t.lower() not in covered]
    return missing
