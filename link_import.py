"""
link_import.py — Product Link import for the Wardrobe Builder.

Lets a user paste a product URL and have Wearly pre-fill as much of the
wardrobe-item form as is safely possible. The design priority is **don't
crash** — every step has a graceful fallback, every site that blocks the
fetch is just a degraded-but-usable case.

Strategy:
  1. Parse the URL with the stdlib `urllib.parse` to extract a store name
     and a slug-derived item name.
  2. Scan the URL path + later the page metadata against a small keyword
     vocabulary to guess category, color, and occasion tags.
  3. Best-effort single HTTP fetch with a 5-second timeout and a 512 KB
     body cap, looking for <title>, og:title, og:image, and the
     description meta. Any failure (timeout, 403, parsing error) falls
     back to URL-only inference.
  4. Returns a dict the UI feeds into a review form. The user still
     confirms / edits every field before saving.

No third-party dependencies. No paid APIs. No secrets. No per-store
scrapers. Built for the prototype tier — the Intelligent Book documents
the production-grade replacement path.
"""

from __future__ import annotations

import html as _html
import io as _io
import re
import urllib.parse
import urllib.request
import urllib.error


# ─────────────────────────────────────────────
# COLOR PALETTE for image-based color inference
# ─────────────────────────────────────────────
# Named colors mapped to their canonical RGB anchors. Mirrors the
# 22-color palette demo_wardrobe.py + app.py already use, so a color
# inferred from an image will be one of the names the rest of the app
# understands. RGB anchors are deliberately desaturated / approximate
# so a "navy" patch of variable lighting still maps to "navy".
_NAMED_COLORS_RGB = {
    "ivory":      (241, 231, 214),
    "cream":      (239, 227, 204),
    "white":      (244, 239, 232),
    "beige":      (214, 195, 164),
    "tan":        (201, 167, 127),
    "nude":       (217, 191, 167),
    "camel":      (184, 152, 120),
    "olive":      (122, 117, 72),
    "sage":       (157, 168, 139),
    "gold":       (201, 169, 104),
    "burgundy":   (107, 44, 42),
    "red":        (160, 58, 50),
    "rust":       (168, 90, 60),
    "terracotta": (193, 127, 90),
    "forest":     (62, 92, 68),
    "navy":       (31, 42, 68),
    "blue":       (74, 111, 165),
    "black":      (28, 25, 23),
    "charcoal":   (46, 42, 39),
    "grey":       (154, 147, 140),
    "silver":     (191, 193, 194),
    "brown":      (90, 60, 40),
    "pink":       (220, 170, 175),
}


# ─────────────────────────────────────────────
# KEYWORD VOCABULARIES
# ─────────────────────────────────────────────

# Word → category (matches the seven categories save_user_item knows).
CATEGORY_KEYWORDS = {
    # tops
    "blouse": "top", "shirt": "top", "tee": "top", "tank": "top",
    "sweater": "top", "turtleneck": "top", "cardigan": "top", "tunic": "top",
    "camisole": "top", "polo": "top",
    # bottoms
    "trousers": "bottom", "pants": "bottom", "jeans": "bottom", "skirt": "bottom",
    "shorts": "bottom",
    # dresses
    "dress": "dress", "gown": "dress", "midi-dress": "dress", "maxi": "dress",
    # outerwear
    "blazer": "outerwear", "coat": "outerwear", "jacket": "outerwear",
    "trench": "outerwear", "parka": "outerwear", "puffer": "outerwear",
    "windbreaker": "outerwear",
    # activewear
    "leggings": "activewear", "yoga": "activewear", "activewear": "activewear",
    "sportswear": "activewear", "track": "activewear", "running": "activewear",
    # shoes
    "heels": "shoes", "boots": "shoes", "sneakers": "shoes", "loafers": "shoes",
    "flats": "shoes", "pumps": "shoes", "sandals": "shoes", "mules": "shoes",
    "shoes": "shoes",
    # accessories
    "earrings": "accessory", "necklace": "accessory", "scarf": "accessory",
    "handbag": "accessory", "tote": "accessory", "clutch": "accessory",
    "bag": "accessory", "belt": "accessory", "hat": "accessory",
    "sunglasses": "accessory",
}

# Colour words we recognise from URL slugs / page text.
COLOR_KEYWORDS = [
    "black", "white", "ivory", "cream", "beige", "grey", "gray",
    "navy", "blue", "olive", "camel", "tan", "nude", "blush", "pink",
    "burgundy", "red", "rust", "terracotta", "gold", "silver",
    "brown", "green", "khaki", "charcoal", "sage",
]

# Occasion / context keyword → canonical tag.
TAG_KEYWORDS = {
    "work":     ["work", "office", "business", "professional"],
    "formal":   ["formal", "gala", "black-tie", "blacktie", "tuxedo", "cocktail"],
    "evening":  ["evening", "night-out"],
    "casual":   ["casual", "weekend", "everyday"],
    "gym":      ["gym", "workout", "athletic", "sport", "running"],
    "travel":   ["travel", "vacation", "resort"],
    "dinner":   ["dinner"],
    "date":     ["date-night", "datenight"],
}

# Common subdomains we strip so "shop.nordstrom.com" reads as "nordstrom"
# and "www2.hm.com" reads as "hm". The `www\d*` pattern catches www, www2,
# www3, etc. Country/language prefixes cover most major retailer locales.
_SUBDOMAIN_STRIP_RE = re.compile(
    r"^(www\d*\.|m\.|mobile\.|shop\.|store\.|secure\.|"
    r"us\.|uk\.|en\.|fr\.|de\.|it\.|es\.|ca\.|au\.|nl\.|jp\.|cn\.|kr\.|sa\.)",
    re.IGNORECASE,
)


# Display names for well-known fashion retailers. Keys are the URL-derived
# label (lowercase, no dots). Anything not in this map falls back to a
# title-cased version of the URL label (so "exampleshop" → "Exampleshop").
STORE_DISPLAY_NAMES = {
    "hm":              "H&M",
    "zara":            "Zara",
    "uniqlo":          "Uniqlo",
    "cos":             "COS",
    "nordstrom":       "Nordstrom",
    "revolve":         "Revolve",
    "everlane":        "Everlane",
    "aritzia":         "Aritzia",
    "madewell":        "Madewell",
    "jcrew":           "J.Crew",
    "loft":            "LOFT",
    "bananarepublic":  "Banana Republic",
    "gap":             "Gap",
    "mango":           "Mango",
    "asos":            "ASOS",
    "ssense":          "SSENSE",
    "farfetch":        "Farfetch",
    "mytheresa":       "Mytheresa",
    "shopbop":         "Shopbop",
    "anthropologie":   "Anthropologie",
    "freepeople":      "Free People",
    "urbanoutfitters": "Urban Outfitters",
    "abercrombie":     "Abercrombie",
    "lululemon":       "lululemon",
    "athleta":         "Athleta",
    "reformation":     "Reformation",
    "sezane":          "Sézane",
    "massimodutti":    "Massimo Dutti",
    "andotherstories": "& Other Stories",
    "amazon":          "Amazon",
    "etsy":            "Etsy",
    "net-a-porter":    "Net-a-Porter",
    "netaporter":      "Net-a-Porter",
}


# Segments / words we drop from URL paths because they're navigation
# scaffolding, not product names. After SKU and extension stripping, any
# segment that reduces to ONLY these tokens is rejected entirely (so the
# H&M slug "productpage.1351318001.html" yields "" instead of "Productpage.").
_NOISE_SEGMENT_WORDS = {
    "productpage", "pdp", "product", "products", "item", "items",
    "sku", "p", "shop", "details", "view", "browse",
    "women", "men", "kids", "girls", "boys", "sale",
    "category", "categories", "collection", "collections", "new",
    "ref", "page", "default",
}


# ─────────────────────────────────────────────
# URL PARSING (stdlib only)
# ─────────────────────────────────────────────

def extract_store_from_url(url: str) -> str:
    """
    Extract a presentable store name from the URL host. Strips technical
    subdomains (www, www2, m, mobile, shop, store, secure) and common
    country/language prefixes, then looks up the result in
    STORE_DISPLAY_NAMES for a curated brand name. Unknown stores get a
    title-cased fallback.

        https://www2.hm.com/...     → "H&M"
        https://www.hm.com/...      → "H&M"
        https://hm.com/...          → "H&M"
        https://uk.zara.com/...     → "Zara"
        https://shop.nordstrom.com/ → "Nordstrom"
        https://www.exampleshop.com → "Exampleshop"
        https://...                 → "" if no host can be parsed
    """
    try:
        host = (urllib.parse.urlparse(url).netloc or "").lower()
    except Exception:
        return ""
    if not host:
        return ""
    # Strip ALL leading technical subdomains, not just the first one.
    prev = None
    while host != prev:
        prev = host
        host = _SUBDOMAIN_STRIP_RE.sub("", host)
    first = host.split(".")[0] if host else ""
    if not first:
        return ""
    return STORE_DISPLAY_NAMES.get(first, first.capitalize())


_HEX_SKU_RE = re.compile(r"\b[A-Za-z0-9]*\d{4,}[A-Za-z0-9]*\b")
_EXT_RE = re.compile(r"\.[a-z]{2,5}$", re.IGNORECASE)


def slug_to_name(url: str) -> str:
    """
    Convert the deepest meaningful path segment of a product URL into a
    presentable item name. Returns the empty string when no segment
    contains actual product words — the caller should treat empty as
    "ask the user to type it in" rather than substituting noise.

        .../products/cream-linen-blazer-12345    →  "Cream Linen Blazer"
        .../shop/midi-dress-burgundy.html        →  "Midi Dress Burgundy"
        .../p/123456789                          →  ""  (pure SKU)
        .../en_us/productpage.1351318001.html    →  ""  (noise-only after cleanup)
    """
    try:
        path = urllib.parse.urlparse(url).path or ""
    except Exception:
        return ""
    path = urllib.parse.unquote(path)
    segments = [s for s in path.split("/") if s]

    for seg in reversed(segments):
        # Drop file extension(s) — handle compound extensions like ".html".
        seg = _EXT_RE.sub("", seg)
        # Strip long digit runs (4+ digits = almost certainly an SKU).
        seg = _HEX_SKU_RE.sub("", seg)
        # Normalize separators to spaces.
        seg = seg.replace("-", " ").replace("_", " ").replace(".", " ")
        # Remove anything that isn't word-char or whitespace.
        seg = re.sub(r"[^\w\s]", " ", seg)
        seg = re.sub(r"\s+", " ", seg).strip()
        if not seg or seg.isdigit():
            continue

        # Tokenize, drop pure digits, very short tokens, and noise words.
        words = []
        for w in seg.split():
            if not w or w.isdigit():
                continue
            if w.lower() in _NOISE_SEGMENT_WORDS:
                continue
            if len(w) < 2:
                continue
            words.append(w)

        if not words:
            continue
        # Require at least one word of length ≥ 3 — guards against
        # "p s" or other ultra-short remnants.
        if not any(len(w) >= 3 for w in words):
            continue
        return " ".join(w.capitalize() for w in words)
    return ""


def _search_first(haystack: str, candidates: dict | list) -> str | None:
    """Return the first candidate keyword that appears in `haystack`."""
    h = haystack.lower()
    if isinstance(candidates, dict):
        for key, val in candidates.items():
            if re.search(rf"\b{re.escape(key)}\b", h):
                return val
        return None
    for w in candidates:
        if re.search(rf"\b{re.escape(w)}\b", h):
            return w
    return None


def _search_all_tags(haystack: str) -> list:
    """Return canonical tag names matched in `haystack`, deduplicated."""
    h = haystack.lower()
    found = []
    for canonical, words in TAG_KEYWORDS.items():
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", h):
                if canonical not in found:
                    found.append(canonical)
                break
    return found


def infer_color_from_image_url(
    url: str, timeout: float = 6.0,
) -> tuple[str, str]:
    """
    Best-effort: download the product image and return the closest
    named color from `_NAMED_COLORS_RGB`. Returns ("", "low") on any
    failure (no PIL, network error, decode error, ambiguous result).

    Returns ``(color_name, confidence)`` where confidence is one of
    "high" / "medium" / "low". The confidence is reported back to the
    UI so the user knows whether to trust the suggestion or not.

    Method:
      1. Download (≤ 4 MB, polite UA, 6 s timeout).
      2. Pillow → center-crop the middle 60% of the frame (avoids the
         retailer's white background + the model's skin / face when
         present). For a product shot of a tee on a model, that
         keeps the torso fabric and drops the periphery.
      3. Resize to 64×64 for stable color histogram.
      4. Quantize to 6 colors via Image.quantize. Take the most-common
         color.
      5. Map that RGB to the nearest named color by Euclidean RGB
         distance. Confidence = "high" if distance < 35, "medium" if
         < 70, else "low" (returned anyway — the caller decides).

    The function never raises and never blocks longer than `timeout`.
    """
    if not url:
        return "", "low"
    try:
        from PIL import Image
    except Exception:
        return "", "low"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": _DEFAULT_UA,
            "Accept":     "image/jpeg, image/png, image/webp",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4 * 1024 * 1024)
        if not raw:
            return "", "low"
    except Exception:
        return "", "low"

    try:
        img = Image.open(_io.BytesIO(raw))
        img.load()
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        if img.mode == "RGBA":
            # Composite onto white so transparent backgrounds (common
            # in catalog PNGs) don't masquerade as black pixels.
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg

        # Center-crop to 60% of width × 60% of height.
        w, h = img.size
        cw, ch = int(w * 0.6), int(h * 0.6)
        left = (w - cw) // 2
        top = (h - ch) // 2
        img = img.crop((left, top, left + cw, top + ch))

        # Small + quantized for stable histogram.
        img = img.resize((64, 64), Image.LANCZOS)
        q = img.quantize(colors=6)
        palette = q.getpalette()
        if not palette:
            return "", "low"
        counts = sorted(q.getcolors() or [], key=lambda c: -c[0])
        if not counts:
            return "", "low"

        # Top color in cropped region.
        _count, idx = counts[0]
        r = palette[idx * 3]
        g = palette[idx * 3 + 1]
        b = palette[idx * 3 + 2]
    except Exception:
        return "", "low"

    # Map to nearest named color.
    best_name = ""
    best_dist = 10 ** 9
    for name, anchor in _NAMED_COLORS_RGB.items():
        dist = ((r - anchor[0]) ** 2
                + (g - anchor[1]) ** 2
                + (b - anchor[2]) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    # Distance is squared. < 35² ≈ 1225 → high; < 70² = 4900 → medium.
    if best_dist < 1225:
        conf = "high"
    elif best_dist < 4900:
        conf = "medium"
    else:
        conf = "low"
    return best_name, conf


def infer_fields_from_text(text: str) -> dict:
    """
    Given any blob of text (URL path, page title, description), guess
    category, color, and a list of occasion tags. Each is None / [] when
    nothing matches — the form will fall back to defaults.
    """
    return {
        "category": _search_first(text, CATEGORY_KEYWORDS),
        "color":    _search_first(text, COLOR_KEYWORDS),
        "tags":     _search_all_tags(text),
    }


# ─────────────────────────────────────────────
# METADATA FETCH (best-effort, never raises)
# ─────────────────────────────────────────────

# A real-browser User-Agent string. Many retailers block obvious bot UAs
# at the edge (Cloudflare, Akamai, etc.), and the prior "Wearly-Prototype/0.1"
# UA was getting timed out / 403'd by H&M and others. Identifying as a
# recent desktop Chrome gives the prototype a fair shot. We're fetching a
# single page the user explicitly chose — not crawling.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def _find_meta(html: str, attr_value: str) -> str | None:
    """
    Find a meta-tag content for property/name == attr_value (e.g.
    "og:title"). Handles both attribute orderings.
    """
    pat1 = (
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(attr_value)}["\']'
        rf'[^>]+content=["\']([^"\']+)["\']'
    )
    m = re.search(pat1, html, re.IGNORECASE)
    if m:
        return _html.unescape(m.group(1).strip())
    pat2 = (
        rf'<meta[^>]+content=["\']([^"\']+)["\']'
        rf'[^>]+(?:property|name)=["\']{re.escape(attr_value)}["\']'
    )
    m = re.search(pat2, html, re.IGNORECASE)
    if m:
        return _html.unescape(m.group(1).strip())
    return None


def _extract_jsonld_product(html: str) -> dict:
    """
    Many retailers embed Schema.org Product JSON-LD inside
    <script type="application/ld+json"> ... </script>. When present
    it's the cleanest signal: name, brand, color, category, image,
    and sometimes price. We pluck just those fields and stay
    schema-tolerant — Schema.org allows nesting under @graph and
    array-valued types.

    Returns {"name", "brand", "color", "category", "image",
    "description"} with None for anything we couldn't find.
    Failures are silent — this layer is best-effort.
    """
    out = {"name": None, "brand": None, "color": None,
           "category": None, "image": None, "description": None}
    try:
        import json as _json
    except Exception:
        return out

    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, flags=re.IGNORECASE | re.DOTALL,
    )

    def _walk(node) -> None:
        # Recursively descend the JSON-LD structure, collecting the
        # first Product-shaped record we can find.
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if not isinstance(node, dict):
            return
        types = node.get("@type")
        type_set: set = set()
        if isinstance(types, str):
            type_set.add(types.lower())
        elif isinstance(types, list):
            for t in types:
                if isinstance(t, str):
                    type_set.add(t.lower())
        if "product" in type_set:
            if out["name"] is None:
                v = node.get("name")
                if isinstance(v, str) and v.strip():
                    out["name"] = _html.unescape(v.strip())
            if out["description"] is None:
                v = node.get("description")
                if isinstance(v, str) and v.strip():
                    out["description"] = _html.unescape(v.strip())
            if out["brand"] is None:
                b = node.get("brand")
                if isinstance(b, str):
                    out["brand"] = b.strip() or None
                elif isinstance(b, dict):
                    out["brand"] = (b.get("name") or "").strip() or None
            if out["color"] is None:
                v = node.get("color")
                if isinstance(v, str) and v.strip():
                    out["color"] = v.strip().lower()
            if out["category"] is None:
                v = node.get("category")
                if isinstance(v, str) and v.strip():
                    out["category"] = v.strip()
                elif isinstance(v, list) and v:
                    if isinstance(v[0], str):
                        out["category"] = v[0]
            if out["image"] is None:
                img = node.get("image")
                if isinstance(img, str) and img.strip():
                    out["image"] = img.strip()
                elif isinstance(img, list) and img:
                    first = img[0]
                    if isinstance(first, str):
                        out["image"] = first.strip()
                    elif isinstance(first, dict):
                        out["image"] = (first.get("url") or "").strip() or None
                elif isinstance(img, dict):
                    out["image"] = (img.get("url") or "").strip() or None
        # Schema.org @graph node — keep walking.
        for k in ("@graph", "mainEntity", "isPartOf"):
            if k in node:
                _walk(node[k])

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            parsed = _json.loads(block)
        except Exception:
            # Some retailers emit JSON-LD with trailing commas or
            # other non-strict syntax. Try a tolerant fallback by
            # stripping line comments. If even that fails, skip.
            try:
                cleaned = re.sub(r",\s*([}\]])", r"\1", block)
                parsed = _json.loads(cleaned)
            except Exception:
                continue
        _walk(parsed)

    return out


def extract_metadata_from_html(html: str) -> dict:
    """
    Return all useful metadata signals from a product page:
      {title, og_title, og_image, og_description, description,
       jsonld_product: {name, brand, color, category, image,
                        description}}

    Any field can be None. JSON-LD Product schema is the cleanest
    signal when present (retailers like Aritzia, Nordstrom, ASOS,
    Madewell, Net-a-Porter, Zalando all emit it). OpenGraph is the
    common fallback. Plain <title> is the last resort.
    """
    out = {
        "title":          None,
        "og_title":       None,
        "og_image":       None,
        "og_description": None,
        "description":    None,
        "jsonld_product": _extract_jsonld_product(html),
    }
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        out["title"] = _html.unescape(m.group(1).strip())
    out["og_title"]       = _find_meta(html, "og:title")
    out["og_image"]       = _find_meta(html, "og:image")
    out["og_description"] = _find_meta(html, "og:description")
    out["description"]    = _find_meta(html, "description")
    return out


def _maybe_decompress(raw: bytes, content_encoding: str) -> bytes:
    """Decompress gzip/deflate responses; on failure, return raw bytes.

    The byte cap means we sometimes truncate gzip streams. gzip.decompress
    fails on truncated input, so we also try gzip.GzipFile (which can
    decode prefixes), then plain-deflate, then raw-deflate. Anything we
    can't decompress is left as-is — the downstream decode step uses
    errors='replace', so worst case we lose readability of metadata that
    sits after the cut.
    """
    encoding = (content_encoding or "").lower()
    if "gzip" in encoding:
        try:
            import gzip
            return gzip.decompress(raw)
        except Exception:
            try:
                import gzip, io
                return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            except Exception:
                return raw
    if "deflate" in encoding:
        try:
            import zlib
            return zlib.decompress(raw)
        except Exception:
            try:
                import zlib
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                return raw
    return raw


def fetch_url_metadata(
    url: str,
    timeout: float = 10.0,
    max_bytes: int = 2 * 1024 * 1024,
    user_agent: str = _DEFAULT_UA,
) -> dict:
    """
    Best-effort HTTP fetch. Returns:
        {"success": True,  "extracted": {...}, "error": None}
      or
        {"success": False, "extracted": {}, "error": "<reason>"}

    NEVER raises. NEVER touches third-party libs. Caps the response at
    `max_bytes` so a huge page can't hang the prototype. Sends a full
    browser-like header set (UA, Accept-Language, Accept-Encoding,
    Upgrade-Insecure-Requests) so polite retailers don't 403 us at the
    edge. Decompresses gzip/deflate responses transparently.

    Notes on residual limits:
      - Some retailers serve a Single Page App where the initial HTML
        has only generic brand metadata; product details load later via
        JavaScript. We can't see those.
      - Some retailers (Akamai/Cloudflare Pro) will still block us. The
        UI provides a manual image-URL field for that case.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":                _DEFAULT_UA if user_agent is None else user_agent,
                "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language":           "en-US,en;q=0.9",
                "Accept-Encoding":           "gzip, deflate",
                "Cache-Control":             "no-cache",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(max_bytes)
            raw = _maybe_decompress(raw, resp.headers.get("Content-Encoding", ""))
            charset = resp.headers.get_content_charset() or "utf-8"
            html_text = raw.decode(charset, errors="replace")
        return {"success": True, "extracted": extract_metadata_from_html(html_text), "error": None}
    except urllib.error.HTTPError as e:
        return {"success": False, "extracted": {}, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"success": False, "extracted": {}, "error": f"Network error: {getattr(e, 'reason', str(e))}"}
    except Exception as e:
        return {"success": False, "extracted": {}, "error": f"Could not read page: {e}"}


# ─────────────────────────────────────────────
# ORCHESTRATION
# ─────────────────────────────────────────────

def import_product_link(url: str, fetch_metadata: bool = True) -> dict:
    """
    The single public entry point. Always returns a dict with the keys
    expected by the UI's review form; never raises. The user remains the
    final reviewer of every field before save.

    Result shape:
        {
          "url":               str,
          "source_store":      str,            # "zara", "nordstrom", …
          "source_image_url":  str | None,     # from og:image
          "inferred": {
              "name":      str,
              "category":  str | None,
              "color":     str | None,
              "tags":      list[str],
          },
          "metadata": {                        # raw extracted page metadata
              "title":       str | None,
              "og_title":    str | None,
              "og_image":    str | None,
              "description": str | None,
          },
          "fetched":  bool,
          "fetch_error": str | None,           # populated if the fetch failed
        }
    """
    if not url or not isinstance(url, str):
        return {
            "url": url, "source_store": "", "source_image_url": None,
            "inferred": {"name": "", "category": None, "color": None, "tags": [],
                         "formality": None, "season": None},
            "sources": {
                "name": "default", "category": "default", "color": "default",
                "tags": "default", "formality": "default", "season": "default",
                "image": "default",
            },
            "metadata": {"title": None, "og_title": None, "og_image": None,
                         "og_description": None, "description": None,
                         "jsonld_product": {}},
            "fetched": False, "fetch_error": "Empty or invalid URL.",
        }

    store = extract_store_from_url(url)
    slug_name = slug_to_name(url)

    fetch_result = {"success": False, "extracted": {}, "error": "Skipped fetch."}
    if fetch_metadata:
        fetch_result = fetch_url_metadata(url)

    meta = fetch_result.get("extracted") or {
        "title": None, "og_title": None, "og_image": None,
        "og_description": None, "description": None, "jsonld_product": {},
    }

    jsonld = meta.get("jsonld_product") or {}

    # Combine all text we have for keyword inference, INCLUDING the
    # Schema.org JSON-LD fields. This makes the inferred tags, color,
    # and category respect retailer-provided structured data.
    text_pool = " ".join(filter(None, [
        url,
        slug_name,
        meta.get("og_title") or "",
        meta.get("title") or "",
        meta.get("og_description") or "",
        meta.get("description") or "",
        jsonld.get("name") or "",
        jsonld.get("description") or "",
        jsonld.get("category") or "",
        jsonld.get("color") or "",
        jsonld.get("brand") or "",
    ]))

    inferred = infer_fields_from_text(text_pool)

    # Source tracking: each inferred field records WHERE its value
    # came from so the UI can render a "from metadata" / "from image"
    # caption next to each chip. "default" means an opinionated
    # fallback (no signal in the page / image / URL).
    sources: dict = {
        "name":      "default",
        "category":  "default",
        "color":     "default",
        "tags":      "default",
        "formality": "default",
        "season":    "default",
        "image":     "default",
    }

    # Category: JSON-LD wins; otherwise text-pool keyword match.
    if jsonld.get("category"):
        cat_text = jsonld["category"].lower()
        for keyword, target in CATEGORY_KEYWORDS.items():
            if keyword in cat_text:
                inferred["category"] = target
                sources["category"] = "metadata"
                break
    elif inferred.get("category"):
        sources["category"] = "text"

    # Color: JSON-LD wins; then text-pool keyword; then (only as a
    # final fallback) the dominant-color sampler against the og:image.
    # Image-based inference NEVER overrides a metadata or text color.
    image_url = jsonld.get("image") or meta.get("og_image")
    if jsonld.get("color"):
        inferred["color"] = jsonld["color"].lower()
        sources["color"] = "metadata"
    elif inferred.get("color"):
        sources["color"] = "text"
    elif image_url:
        # No textual color signal — sample the image.
        img_color, img_conf = infer_color_from_image_url(image_url)
        if img_color and img_conf in ("high", "medium"):
            inferred["color"] = img_color
            sources["color"] = f"image:{img_conf}"
        # Low-confidence image guess is dropped — better empty than wrong.

    # ── Formality inference ─────────────────────────────────────────
    # Category-aware cues. Each branch sets `formality` AND records
    # whether the call was forced by an explicit keyword (source=
    # "text") or by a category-based default (source="category-fallback").
    text_low = text_pool.lower()
    cat = (inferred.get("category") or "").lower()
    tag_set = set(inferred.get("tags") or [])
    formality = None
    formality_source = ""

    # 1) Strong textual cues — these win regardless of category.
    if "formal" in tag_set or any(w in text_low for w in
            ("gown", "tuxedo", "black tie", "black-tie", "blacktie",
             "cocktail", "evening gown")):
        formality, formality_source = "formal", "text"
    elif "work" in tag_set or any(w in text_low for w in
            ("blazer", "suit ", "suiting", "professional", "office wear",
             "workwear", "tailored")):
        formality, formality_source = "business", "text"
    elif cat == "activewear" or "gym" in tag_set or any(
            w in text_low for w in (
                "activewear", "sportswear", "training", "yoga ",
                "running", "athletic", "workout")):
        formality, formality_source = "athletic", "text"
    elif any(w in text_low for w in ("silk", "chiffon", "satin", "lace")):
        formality, formality_source = "smart_casual", "text"
    elif "evening" in tag_set or "dinner" in tag_set or "date" in tag_set:
        formality, formality_source = "smart_casual", "text"

    # 2) Category-aware fallbacks. Encodes what the user listed:
    #    tee / tank / hoodie / shorts / sneakers → casual
    #    blouse / oxford / button-down / silk top → smart_casual
    #    sheath / midi / wrap dress → smart_casual; gown → formal
    #    heels / pumps → smart_casual (formal if "evening"/"black tie")
    #    boots → smart_casual; sneakers → casual
    if formality is None:
        if cat == "top":
            if any(w in text_low for w in (
                    "tee", "t-shirt", "tshirt", "tank", "hoodie",
                    "sweatshirt", "henley")):
                formality, formality_source = "casual", "category-fallback"
            elif any(w in text_low for w in (
                    "blouse", "oxford", "button-down", "button down",
                    "button-up", "button up", "collared")):
                formality, formality_source = "smart_casual", "category-fallback"
            else:
                formality, formality_source = "casual", "category-fallback"
        elif cat == "bottom":
            if any(w in text_low for w in ("jeans", "denim", "shorts",
                                            "joggers", "sweatpants")):
                formality, formality_source = "casual", "category-fallback"
            elif any(w in text_low for w in ("trousers", "slacks",
                                              "pleated", "wide-leg",
                                              "wide leg")):
                formality, formality_source = "smart_casual", "category-fallback"
            else:
                formality, formality_source = "casual", "category-fallback"
        elif cat == "dress":
            if any(w in text_low for w in ("gown", "cocktail",
                                            "black tie", "evening")):
                formality, formality_source = "formal", "category-fallback"
            elif any(w in text_low for w in ("sundress", "sleeveless",
                                              "t-shirt dress")):
                formality, formality_source = "casual", "category-fallback"
            else:
                # Sheath, midi, wrap, slip, etc.
                formality, formality_source = "smart_casual", "category-fallback"
        elif cat == "outerwear":
            formality, formality_source = "smart_casual", "category-fallback"
        elif cat == "shoes":
            if any(w in text_low for w in ("heel", "heels", "pump",
                                            "pumps", "stiletto")):
                formality, formality_source = "smart_casual", "category-fallback"
            elif any(w in text_low for w in ("sneaker", "sneakers",
                                              "trainer", "trainers",
                                              "running")):
                formality, formality_source = "casual", "category-fallback"
            elif any(w in text_low for w in ("boot", "boots", "loafer",
                                              "loafers")):
                formality, formality_source = "smart_casual", "category-fallback"
            else:
                formality, formality_source = "casual", "category-fallback"
        elif cat == "activewear":
            formality, formality_source = "athletic", "category-fallback"
        else:
            formality, formality_source = "casual", "default"

    sources["formality"] = formality_source

    # ── Season inference ───────────────────────────────────────────
    # Two passes:
    #   1) Direct fabric / item-type keyword matching (existing logic).
    #   2) Category + item-type combination fallback so a Uniqlo "tee"
    #      doesn't fall back to ["all"]. T-shirts are spring/summer
    #      (plus fall for layering); knitwear is fall/winter.
    season_hits: list = []
    spring_kw = ("spring", "linen", "cotton", "chambray", "poplin",
                 "seersucker", "midi", "lightweight")
    summer_kw = ("summer", "linen", "cotton", "muslin", "sundress",
                 "swim", "shorts", "tank", "camisole", "sleeveless",
                 "short sleeve", "short-sleeve")
    fall_kw   = ("fall", "autumn", "knit", "cardigan", "wool blend",
                 "long sleeve", "long-sleeve", "merino", "flannel")
    winter_kw = ("winter", "wool", "cashmere", "puffer", "parka",
                 "heavyweight", "thermal", "shearling", "fleece",
                 "down jacket", "down coat")
    def _hits(words):
        return any(re.search(rf"\b{re.escape(w)}\b", text_low) for w in words)
    if _hits(spring_kw): season_hits.append("spring")
    if _hits(summer_kw): season_hits.append("summer")
    if _hits(fall_kw):   season_hits.append("fall")
    if _hits(winter_kw): season_hits.append("winter")
    season_source = "text" if season_hits else ""

    # Category-based season fallback (when text-pool keyword pass
    # produced nothing). Aligned with the user's expectations:
    #   tee / t-shirt → spring + summer + fall (layering)
    #   tank          → summer
    #   knit/sweater  → fall + winter
    #   coat/puffer   → fall + winter
    #   sandal        → summer
    #   sneaker/jeans → all
    if not season_hits:
        if cat == "top":
            if any(w in text_low for w in ("tee", "t-shirt", "tshirt")):
                season_hits = ["spring", "summer", "fall"]
            elif "tank" in text_low or "camisole" in text_low:
                season_hits = ["summer"]
            elif any(w in text_low for w in ("sweater", "cardigan",
                                              "turtleneck", "knit")):
                season_hits = ["fall", "winter"]
            # else stays empty → final default ["all"]
        elif cat == "outerwear":
            if any(w in text_low for w in ("puffer", "parka", "wool",
                                            "cashmere", "shearling",
                                            "down")):
                season_hits = ["fall", "winter"]
            else:
                season_hits = ["fall", "winter"]
        elif cat == "shoes":
            if any(w in text_low for w in ("sandal", "sandals")):
                season_hits = ["summer"]
            elif any(w in text_low for w in ("boot", "boots")):
                season_hits = ["fall", "winter"]
        elif cat == "dress":
            if any(w in text_low for w in ("sundress", "linen",
                                            "sleeveless")):
                season_hits = ["spring", "summer"]
        if season_hits:
            season_source = "category-fallback"

    season = season_hits if season_hits else ["all"]
    sources["season"] = season_source or "default"

    # Prefer JSON-LD name, then og:title, then plain <title>, then slug.
    # Every name source goes through the same suffix-strip so a title
    # like "Unisex Crew Neck T-Shirt | UNIQLO US" becomes the clean
    # product name "Unisex Crew Neck T-Shirt". Without this, the form's
    # Name field is pre-filled with the store name appended, which the
    # user had to manually edit on every link import.
    def _strip_store_suffix(s: str) -> str:
        if not s:
            return s
        # Common separators retailers use to pin the brand at the end.
        parts = re.split(r"\s+[|·—–\-]\s+", s, maxsplit=1)
        head = parts[0].strip()
        # If head is non-empty and clearly the product (longer than 3
        # chars), prefer it over the full string.
        return head if len(head) >= 3 else s.strip()

    # Name resolution (provenance tracked separately).
    if jsonld.get("name"):
        name = _strip_store_suffix(jsonld["name"].strip())
        sources["name"] = "metadata"
    elif meta.get("og_title"):
        name = _strip_store_suffix(meta["og_title"].strip())
        sources["name"] = "title"
    elif meta.get("title"):
        name = _strip_store_suffix(meta["title"].strip())
        sources["name"] = "title"
    else:
        name = slug_name
        sources["name"] = "slug" if name else "default"
    _name_tokens = [t for t in re.split(r"\s+", name) if t]
    if _name_tokens and all(t.lower() in _NOISE_SEGMENT_WORDS for t in _name_tokens):
        name = ""
        sources["name"] = "default"

    # Tags: text-derived hits first, then expand using a
    # (category, formality) table when text yielded nothing. Aligned
    # with how the recommendation engine filters by occasion tag —
    # e.g. a t-shirt should reach the candidate pool for "casual",
    # "weekend", AND "travel" even when the retailer page doesn't
    # name any of those words.
    final_tags = list(inferred.get("tags") or [])
    tag_source = "text" if final_tags else ""

    if not final_tags:
        # (category, formality) → useful occasion tags.
        _TAG_FALLBACK = {
            ("top",        "casual"):       ["casual", "weekend", "travel"],
            ("top",        "smart_casual"): ["dinner", "smart_casual", "work"],
            ("top",        "business"):     ["work", "smart_casual"],
            ("top",        "formal"):       ["formal"],
            ("top",        "athletic"):     ["gym"],
            ("bottom",     "casual"):       ["casual", "weekend", "travel"],
            ("bottom",     "smart_casual"): ["smart_casual", "work"],
            ("bottom",     "business"):     ["work", "smart_casual"],
            ("dress",      "casual"):       ["casual", "weekend"],
            ("dress",      "smart_casual"): ["dinner", "smart_casual"],
            ("dress",      "formal"):       ["formal"],
            ("outerwear",  "casual"):       ["casual", "travel"],
            ("outerwear",  "smart_casual"): ["work", "smart_casual", "travel"],
            ("outerwear",  "business"):     ["work", "smart_casual"],
            ("outerwear",  "formal"):       ["formal"],
            ("shoes",      "casual"):       ["casual", "weekend", "travel"],
            ("shoes",      "smart_casual"): ["dinner", "smart_casual", "work"],
            ("shoes",      "business"):     ["work"],
            ("shoes",      "formal"):       ["formal"],
            ("accessory",  "casual"):       ["casual", "weekend"],
            ("accessory",  "smart_casual"): ["dinner", "smart_casual"],
            ("accessory",  "formal"):       ["formal"],
            ("activewear", "athletic"):     ["gym"],
        }
        final_tags = _TAG_FALLBACK.get((cat, formality), [])
        if final_tags:
            tag_source = "category-fallback"
        else:
            # Last-resort fallback by formality only (unchanged from v1).
            if formality == "business":
                final_tags = ["work"]
            elif formality == "formal":
                final_tags = ["formal"]
            elif formality == "athletic":
                final_tags = ["gym"]
            elif formality == "smart_casual":
                final_tags = ["dinner"]
            else:
                final_tags = ["casual"]
            tag_source = "default"

    sources["tags"] = tag_source

    if image_url:
        sources["image"] = "metadata"

    return {
        "url":              url,
        "source_store":     store,
        "source_image_url": image_url,
        "inferred": {
            "name":      name,
            "category":  inferred["category"],
            "color":     inferred["color"],
            "tags":      final_tags,
            "formality": formality,
            "season":    season,
        },
        "sources":      sources,
        "metadata":     meta,
        "fetched":      fetch_result.get("success", False),
        "fetch_error":  None if fetch_result.get("success") else fetch_result.get("error"),
    }
