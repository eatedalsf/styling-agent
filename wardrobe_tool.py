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


# ─────────────────────────────────────────────
# SMART PHOTO INFERENCE  (Goal 1)
# ─────────────────────────────────────────────

# Filename-keyword vocabulary. A typical phone screenshot or store-saved
# image is named things like "blush-blouse.png", "IMG_aritzia_dress.jpeg",
# "camel-trench-coat.png". When that's present we extract the category,
# color, and occasion tags from the filename — no ML required.
_FILENAME_CATEGORY_KEYWORDS = {
    "dress": "dress", "gown": "dress", "tunic": "dress",
    "blouse": "top", "shirt": "top", "tee": "top", "tank": "top",
    "sweater": "top", "turtleneck": "top", "cardigan": "top",
    "polo": "top", "camisole": "top",
    "trousers": "bottom", "pants": "bottom", "jeans": "bottom",
    "skirt": "bottom", "shorts": "bottom",
    "blazer": "outerwear", "coat": "outerwear", "jacket": "outerwear",
    "trench": "outerwear", "parka": "outerwear", "puffer": "outerwear",
    "leggings": "activewear", "athleisure": "activewear",
    "activewear": "activewear", "yoga": "activewear",
    "heels": "shoes", "boots": "shoes", "sneakers": "shoes",
    "loafers": "shoes", "flats": "shoes", "pumps": "shoes",
    "sandals": "shoes", "mules": "shoes", "shoes": "shoes",
    "earrings": "accessory", "necklace": "accessory", "scarf": "accessory",
    "handbag": "accessory", "tote": "accessory", "clutch": "accessory",
    "bag": "accessory", "belt": "accessory", "sunglasses": "accessory",
}

_FILENAME_COLOR_KEYWORDS = (
    "black", "white", "ivory", "cream", "beige", "grey", "gray",
    "navy", "blue", "olive", "camel", "tan", "nude", "blush", "pink",
    "burgundy", "red", "rust", "terracotta", "gold", "silver",
    "brown", "green", "khaki", "charcoal", "sage",
)

_FILENAME_TAG_KEYWORDS = {
    "work":   ["work", "office", "business", "professional"],
    "formal": ["formal", "gala", "blacktie", "black-tie", "cocktail"],
    "evening":["evening", "nightout"],
    "casual": ["casual", "weekend", "everyday"],
    "gym":    ["gym", "workout", "athletic", "sport", "running"],
    "travel": ["travel", "vacation", "resort"],
    "dinner": ["dinner"],
    "date":   ["datenight"],
}


def _infer_from_filename(filename: str) -> dict:
    """Pull category, color, tags from a filename like
    'blush-floral-blouse.png' or 'IMG_camel_trench_coat.jpeg'."""
    out = {"category": None, "color": None, "tags": []}
    if not filename:
        return out
    name = filename.lower()
    # Strip extension and split on common separators.
    name = __import__("re").sub(r"\.[a-z0-9]{2,5}$", "", name)
    tokens = set(__import__("re").split(r"[\s\-_./]+", name))
    # Category — first match wins, prefer specific terms.
    for kw, target in _FILENAME_CATEGORY_KEYWORDS.items():
        if kw in tokens or kw in name:
            out["category"] = target
            break
    # Color — first match wins (filename usually has just one).
    for col in _FILENAME_COLOR_KEYWORDS:
        if col in tokens or col in name:
            out["color"] = col
            break
    # Tags — collect all hits.
    found_tags: list = []
    for canonical, kws in _FILENAME_TAG_KEYWORDS.items():
        for w in kws:
            if w in tokens or w in name:
                if canonical not in found_tags:
                    found_tags.append(canonical)
                break
    out["tags"] = found_tags
    return out


def _infer_season_from_color(color_name: str) -> list:
    """Heuristic: a color's apparent warmth/saturation suggests
    the season(s) the item is best suited to. Used as a fallback
    when neither filename nor explicit user input provides a season.
    """
    if not color_name:
        return ["all"]
    c = color_name.lower()
    if any(k in c for k in ("burgundy", "rust", "olive", "camel",
                            "brown", "charcoal", "navy", "forest", "wine")):
        return ["fall", "winter"]
    if any(k in c for k in ("blush", "sage", "pastel", "mint",
                            "lavender", "peach", "ivory")):
        return ["spring"]
    if any(k in c for k in ("white", "cream", "tan", "nude", "linen")):
        return ["spring", "summer"]
    return ["all"]


def infer_item_from_photo(image_bytes: bytes, filename: str = "") -> dict:
    """
    Combine pixel-level color extraction with filename-keyword
    inference to fill in as many wardrobe fields as we can BEFORE
    the user has to type anything. Returns:

        {
          "name":      str | None,    # cleaned from filename
          "category":  str | None,    # from filename keywords
          "color":     str | None,    # from filename OR top pixel cluster
          "tags":      [str, ...],    # from filename keywords
          "season":    [str, ...],    # from filename, color, or default
          "formality": str | None,    # from category + tags
          "color_palette": [...]      # full ranked palette for review
        }

    The user remains the final reviewer of every field. This is
    inference, not a contract.

    Goal 1: photo upload should feel low-effort. The user shouldn't
    re-type "this is a dress" when the filename already says
    "balloon_sleeve_dress.png". The image just clusters colors;
    the filename — when present — does the rest.
    """
    import re as _re

    # 1. Filename-driven inference.
    from_filename = _infer_from_filename(filename)

    # 2. Pixel-driven color palette.
    palette_result = suggest_colors_from_image(image_bytes, top_n=3)
    palette = palette_result.get("suggestions") or []
    pixel_color = palette[0].get("name") if palette else None

    # 3. Decide which color wins. Filename color is generally more
    #    trustworthy because background pixels often dominate a
    #    palette. We prefer filename when both exist.
    color = from_filename["color"] or pixel_color

    # 4. Clean up filename → name.
    name = filename or ""
    name = _re.sub(r"\.[a-z0-9]{2,5}$", "", name, flags=_re.IGNORECASE)
    name = _re.sub(r"[\-_]+", " ", name)
    name = _re.sub(r"\s+", " ", name).strip()
    # Strip noise prefixes like "IMG", "DSC", date-like tokens.
    tokens = name.split()
    NOISE = {"img", "dsc", "photo", "pic", "image", "screenshot",
             "untitled", "scan"}
    tokens = [t for t in tokens
              if t.lower() not in NOISE and not _re.fullmatch(r"\d{4,}", t)]
    name = " ".join(t.capitalize() for t in tokens)
    if not name and color:
        name = f"{color.title()} item"

    # 5. Season — filename → color heuristic → all.
    season = []
    # Filename tag hints (no explicit season tokens here, just inferred).
    color_season = _infer_season_from_color(color or "")
    season = color_season

    # 6. Formality — rule-based mapping from category + tags.
    category = from_filename["category"]
    tag_set = set(from_filename["tags"])
    formality = None
    if "formal" in tag_set or category == "dress":
        formality = "smart_casual"
    elif "work" in tag_set:
        formality = "business"
    elif category == "activewear" or "gym" in tag_set:
        formality = "athletic"
    elif category in ("outerwear", "top", "bottom"):
        formality = "casual"
    elif category == "shoes":
        formality = "casual"
    if not formality:
        formality = "casual"

    return {
        "name":          name or None,
        "category":      category,
        "color":         color,
        "tags":          from_filename["tags"],
        "season":        season,
        "formality":     formality,
        "color_palette": palette,
    }


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


_CANONICAL_OCCASIONS = {"work", "gym", "dinner", "formal", "casual",
                        "weekend", "evening", "date", "travel"}


def _ensure_useful_occasion_tags(item: dict) -> bool:
    """
    Quiet migration: derive sensible occasion tags for an item that
    has too few, so it doesn't silently drop out of the candidate pool.

    Two passes:

      1. If the item has NO canonical occasion tag, infer a default
         set from its category + formality. (Original behavior.)

      2. If the item has only "casual" and is the kind of piece that
         legitimately works for multiple casual contexts (dress,
         skirt, blouse, knit), add "weekend" and — for dresses — "dinner".
         Without this expansion, a "casual dress" tagged ONLY with
         "casual" would never appear in a "dinner" or "weekend brunch"
         pool, even though that's exactly when a casual dress is most
         useful. The user reported exactly this case: two casual
         dresses they'd added (UC001, UC002) were not being selected
         for dinner/weekend requests.

    Existing legitimate tags are preserved — this only ever appends.
    Returns True iff the item was modified.
    """
    raw_tags = [t.lower() for t in (item.get("tags") or [])]
    tags = list(raw_tags)
    has_canonical = any(t in _CANONICAL_OCCASIONS for t in tags)

    if not has_canonical:
        # Pass 1: no occasion tag at all — derive defaults.
        derived = _default_occasion_tags(
            item.get("type", ""),
            item.get("formality", ""),
        )
        tags = list(dict.fromkeys(tags + derived))
    else:
        # Pass 2: has occasion tag(s) but maybe not enough. Expand
        # legitimately versatile items so the agent considers them.
        category = (item.get("type") or "").lower()
        formality = (item.get("formality") or "casual").lower()
        # Only expand "casual"-anchored items into broader casual
        # contexts. We never auto-promote a casual item to a formal
        # occasion — that's a real semantic step.
        if "casual" in tags and formality in ("casual", "smart_casual"):
            if "weekend" not in tags:
                tags.append("weekend")
            if category in ("dress", "top", "bottom") and "dinner" not in tags:
                tags.append("dinner")

    if tags == raw_tags:
        return False
    item["tags"] = tags
    return True


def get_user_wardrobe() -> dict:
    """
    Return the user-added overlay. Tolerant of:
      - missing file (returns empty overlay)
      - malformed JSON (returns empty overlay, error string set)

    Also runs a one-time tag migration on existing items so user-added
    items that lack any occasion tag get reasonable defaults and become
    eligible for the agent's candidate pool. The migration is silent
    and writes the corrected overlay back to disk.
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
        # Quiet tag migration. Writes back ONLY when something changed.
        modified = False
        for section in ("clothing", "shoes", "accessories"):
            for it in normalized[section]:
                if _ensure_useful_occasion_tags(it):
                    modified = True
        if modified:
            try:
                on_disk = {
                    "_comment": data.get(
                        "_comment",
                        "User-added wardrobe items. Created and maintained by the "
                        "Wardrobe Builder. Items here are MERGED with wardrobe.json "
                        "at read time by wardrobe_tool.get_wardrobe(),",
                    ),
                    "clothing":    normalized["clothing"],
                    "shoes":       normalized["shoes"],
                    "accessories": normalized["accessories"],
                }
                _atomic_write_json(USER_DATA_PATH, on_disk)
            except Exception:
                # Migration is best-effort; if the write fails we still
                # return the in-memory normalised overlay.
                pass
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


def _default_occasion_tags(category: str, formality: str) -> list:
    """
    Derive a useful set of occasion tags when the user didn't pick any.
    Without this fallback an item saved with just its category as a tag
    (e.g. ['dress']) would never match an occasion-tag filter and would
    be silently ignored by the agent. The derivation is conservative —
    we map by formality first, category second.
    """
    formality = (formality or "casual").lower()
    category  = (category  or "").lower()

    if category == "activewear" or formality == "athletic":
        return ["gym"]
    if formality == "formal":
        return ["formal", "dinner"]
    if formality == "business":
        return ["work", "dinner"]
    if formality == "smart_casual":
        return ["work", "dinner", "casual"]
    # casual / unset / unknown
    base = ["casual", "weekend"]
    if category in ("dress",):
        base.append("dinner")
    return base


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

    formality = (item_fields.get("formality") or "casual").lower()

    # Tags: if the user supplied a non-empty list, honor it; otherwise
    # derive useful defaults so the agent can actually use this item.
    # Bare [category] tags were causing user-added items to fall out
    # of the candidate pool for every occasion — see the docstring of
    # _default_occasion_tags() for the why.
    raw_tags = item_fields.get("tags") or []
    if raw_tags:
        tags = [t.lower() for t in raw_tags]
    else:
        tags = _default_occasion_tags(category, formality)

    item = {
        "id":          _next_user_id(overlay, section),
        "type":        category,
        "name":        name,
        "color":       color,
        "formality":   formality,
        "season":      [s.lower() for s in (item_fields.get("season") or ["all"])] or ["all"],
        "tags":        tags,
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


def _find_item_in_overlay(overlay: dict, item_id: str) -> tuple:
    """Locate (section_name, index, item_dict) for a given user-added id.

    Returns (None, -1, None) when not found. Read-only — does not mutate
    the overlay.
    """
    for section in ("clothing", "shoes", "accessories"):
        for i, it in enumerate(overlay.get(section, [])):
            if it.get("id") == item_id:
                return section, i, it
    return None, -1, None


def update_user_item(item_id: str, item_fields: dict,
                     image_bytes: bytes = None,
                     link_metadata: dict = None) -> dict:
    """
    Update a user-added wardrobe item in place by id. Only items in the
    user overlay (user_wardrobe.json) can be edited — seed items in
    wardrobe.json are immutable and never touched.

    item_fields keys that are honored (each optional in an update):
        name, color, formality, season, tags, availability, type

    If `type` changes (e.g. user reclassifies a saved "top" as "dress")
    the item moves between sections of the overlay; its id is regenerated
    to match the new section's prefix so the id format stays consistent.

    image_bytes — when present, replaces the image_path. Falsy → no change.
    link_metadata — when present, REPLACES (not merges) the three source_*
    keys to match save_user_item's behavior. Pass {} to clear them.

    Returns {success, item, error}.
    """
    if not item_id:
        return {"success": False, "item": None, "error": "item_id is required."}

    overlay = get_user_wardrobe()["user_wardrobe"]
    section, idx, item = _find_item_in_overlay(overlay, item_id)
    if item is None:
        return {"success": False, "item": None,
                "error": f"Item '{item_id}' is not in your overlay — seed items can't be edited."}

    # Apply field updates. Empty strings clear text fields (caller's choice).
    upd = dict(item_fields or {})
    new_type = (upd.get("type") or item.get("type", "")).lower().strip()

    if "name" in upd:
        item["name"] = (upd["name"] or "").strip() or item["name"]
    if "color" in upd:
        item["color"] = (upd["color"] or "").strip() or item["color"]
    if "formality" in upd:
        item["formality"] = (upd["formality"] or "casual").lower()
    if "season" in upd:
        season_list = upd["season"] or ["all"]
        item["season"] = [s.lower() for s in season_list] or ["all"]
    if "tags" in upd:
        tag_list = upd["tags"] or []
        item["tags"] = [t.lower() for t in tag_list] or item["tags"]
    if "availability" in upd:
        item["availability"] = (upd["availability"] or "available").lower()

    # Handle a category move (e.g. "top" → "dress").
    if new_type and new_type != item.get("type"):
        if new_type not in _SECTION_BY_CATEGORY:
            return {"success": False, "item": item,
                    "error": f"Unknown category '{new_type}'."}
        new_section = _SECTION_BY_CATEGORY[new_type]
        item["type"] = new_type
        if new_section != section:
            # Remove from old section, append to new, regenerate id.
            overlay[section].pop(idx)
            new_id = _next_user_id(overlay, new_section)
            item["id"] = new_id
            overlay[new_section].append(item)
            section, idx = new_section, len(overlay[new_section]) - 1

    # Optional fresh image.
    if image_bytes:
        try:
            item["image_path"] = _save_image_for_item(item["id"], image_bytes)
            item.pop("_image_error", None)
        except Exception as e:
            item.setdefault("_image_error", str(e))

    # Link metadata: replace (not merge) when caller supplies a dict.
    if link_metadata is not None:
        for k in ("source_url", "source_store", "source_image_url"):
            item.pop(k, None)
        if link_metadata.get("source_url"):
            item["source_url"] = str(link_metadata["source_url"])
        if link_metadata.get("source_store"):
            item["source_store"] = str(link_metadata["source_store"])
        if link_metadata.get("source_image_url"):
            item["source_image_url"] = str(link_metadata["source_image_url"])

    # Persist.
    on_disk = {
        "_comment": "User-added wardrobe items. Created and maintained by the Wardrobe Builder. Items here are MERGED with wardrobe.json at read time by wardrobe_tool.get_wardrobe().",
        "clothing":    overlay["clothing"],
        "shoes":       overlay["shoes"],
        "accessories": overlay["accessories"],
    }
    try:
        _atomic_write_json(USER_DATA_PATH, on_disk)
    except Exception as e:
        return {"success": False, "item": item, "error": f"Failed to save: {e}"}
    return {"success": True, "item": item, "error": None}


def delete_user_item(item_id: str) -> dict:
    """
    Remove a user-added item from the overlay. Seed items are immutable
    and silently ignored. Returns {success, removed_id, error}.
    """
    if not item_id:
        return {"success": False, "removed_id": None, "error": "item_id is required."}

    overlay = get_user_wardrobe()["user_wardrobe"]
    section, idx, item = _find_item_in_overlay(overlay, item_id)
    if item is None:
        return {"success": False, "removed_id": None,
                "error": f"Item '{item_id}' is not in your overlay."}

    overlay[section].pop(idx)
    on_disk = {
        "_comment": "User-added wardrobe items. Created and maintained by the Wardrobe Builder. Items here are MERGED with wardrobe.json at read time by wardrobe_tool.get_wardrobe().",
        "clothing":    overlay["clothing"],
        "shoes":       overlay["shoes"],
        "accessories": overlay["accessories"],
    }
    try:
        _atomic_write_json(USER_DATA_PATH, on_disk)
    except Exception as e:
        return {"success": False, "removed_id": None, "error": f"Failed to save: {e}"}
    return {"success": True, "removed_id": item_id, "error": None}


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
    """
    Return the required piece-types not covered by `outfit_pieces`.

    Special case: a dress satisfies the conventional "top + bottom"
    requirement on its own. Without that rule, the agent would flag
    "missing top, missing bottom" the moment it builds an outfit
    around a dress — turning a deliberate one-piece choice into a
    false wardrobe gap.
    """
    covered = {piece.get("type", "").lower() for piece in outfit_pieces}
    has_dress = "dress" in covered
    required_lower = [t.lower() for t in required_types]
    # If a dress is present and the requirement is "top + bottom",
    # treat both as covered (the dress IS the top + bottom).
    if has_dress and set(required_lower) >= {"top", "bottom"}:
        required_lower = [t for t in required_lower if t not in ("top", "bottom")]
    missing = [t for t in required_lower if t not in covered]
    return missing
