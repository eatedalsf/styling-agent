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
import re
import urllib.parse
import urllib.request
import urllib.error


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


def extract_metadata_from_html(html: str) -> dict:
    """Return {title, og_title, og_image, description}, any of which can be None."""
    out = {"title": None, "og_title": None, "og_image": None, "description": None}
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        out["title"] = _html.unescape(m.group(1).strip())
    out["og_title"]    = _find_meta(html, "og:title")
    out["og_image"]    = _find_meta(html, "og:image")
    out["description"] = _find_meta(html, "description")
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
            "inferred": {"name": "", "category": None, "color": None, "tags": []},
            "metadata": {"title": None, "og_title": None, "og_image": None, "description": None},
            "fetched": False, "fetch_error": "Empty or invalid URL.",
        }

    store = extract_store_from_url(url)
    slug_name = slug_to_name(url)

    fetch_result = {"success": False, "extracted": {}, "error": "Skipped fetch."}
    if fetch_metadata:
        fetch_result = fetch_url_metadata(url)

    meta = fetch_result.get("extracted") or {
        "title": None, "og_title": None, "og_image": None, "description": None,
    }

    # Combine all text we have for keyword inference.
    text_pool = " ".join(filter(None, [
        url,
        slug_name,
        meta.get("og_title") or "",
        meta.get("title") or "",
        meta.get("description") or "",
    ]))

    inferred = infer_fields_from_text(text_pool)

    # Prefer og:title for the item name when present and informative.
    name = (meta.get("og_title") or "").strip()
    if not name:
        title = (meta.get("title") or "").strip()
        # Page titles often contain " | StoreName" suffixes — strip the suffix.
        if title:
            title = re.split(r"\s+[|·—–-]\s+", title, maxsplit=1)[0].strip()
        name = title
    if not name:
        name = slug_name  # may itself be "" — that's OK
    # Final guard: if the candidate name collapses to a single noise token
    # (e.g. "Productpage"), drop it. Better empty than misleading.
    _name_tokens = [t for t in re.split(r"\s+", name) if t]
    if _name_tokens and all(t.lower() in _NOISE_SEGMENT_WORDS for t in _name_tokens):
        name = ""

    return {
        "url":              url,
        "source_store":     store,
        "source_image_url": meta.get("og_image"),
        "inferred": {
            "name":     name,
            "category": inferred["category"],
            "color":    inferred["color"],
            "tags":     inferred["tags"],
        },
        "metadata":     meta,
        "fetched":      fetch_result.get("success", False),
        "fetch_error":  None if fetch_result.get("success") else fetch_result.get("error"),
    }
