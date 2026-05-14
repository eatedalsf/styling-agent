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
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple


# ── Real-photo source ─────────────────────────────────────
# As of 2026, the once-popular `source.unsplash.com` keyword
# endpoint returns 503 (deprecated late 2024) and LoremFlickr's
# tag-matching is too loose to be useful for clothing (a
# "terracotta wrap dress" query came back with a cat statue).
# The reliable route is the Pexels REST API — free tier 200 req/h
# / 20 000 / month, accurate keyword search, large clothing
# library — but it requires a 1-minute signup at pexels.com/api
# and an API key.
#
# How to enable real photos:
#   $env:PEXELS_API_KEY = "<your free key>"      # Windows PowerShell
#   export PEXELS_API_KEY="<your free key>"       # bash / zsh
# Then click "Reload demo wardrobe" in the Wardrobe screen.
# Items whose Pexels query fails (rate-limited, no match, network
# down) fall back to the silhouette renderer — the demo always
# loads, just with a mix of real photos and illustrations.

_PEXELS_BASE    = "https://api.pexels.com/v1/search"
_FETCH_UA       = (
    "Mozilla/5.0 (Wearly/0.4; +https://eatedalsf.github.io/styling-agent)"
)
_FETCH_TIMEOUT  = 10.0     # per-photo
_PARALLEL_FETCH = 6        # concurrent connections


def _pexels_api_key() -> str:
    """Return the configured Pexels API key, or empty string when
    none is set. Reading lazily lets the user export the env var
    and click Reload without restarting Streamlit."""
    return os.environ.get("PEXELS_API_KEY", "").strip()


def real_photos_enabled() -> bool:
    """Surface-area helper for the UI: whether the loader will
    actually try Pexels on the next Reload."""
    return bool(_pexels_api_key())


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


# ── Card image generator (silhouette-driven) ──────────────

# A clothing illustration on a card — recognizable at thumbnail
# size. Larger than the previous text-only card (400 x 500). The
# silhouette is the focal element; the name + store sit as an
# overlay band at the bottom.
#
# Why silhouettes and not real product photos: real scraping is
# brittle (rate-limited, license-mixed, photos expire). A clean
# illustration on a colored card communicates the SHAPE of the
# item — top vs dress vs trousers vs heel — which is what the
# user needs to recognize a thumbnail at a glance.

# Default card size used by demo_wardrobe.json. 400 wide x 500 tall
# is enough resolution for clean silhouette curves, and the same
# aspect ratio as a real product card.
_DEFAULT_CARD_SIZE = (400, 500)


def _shade(rgb: tuple, delta: int) -> tuple:
    """Lighten (positive delta) or darken (negative) an RGB tuple."""
    return tuple(max(0, min(255, c + delta)) for c in rgb)


def _silhouette_color(bg_rgb: tuple) -> tuple:
    """Pick a contrast color for the clothing silhouette: a darker
    shade of the item's own color on light backgrounds, a brighter
    shade on dark backgrounds. Keeps everything tonal so the result
    reads as "this color of this item", not "ink-on-paper logo"."""
    lum = _luminance(bg_rgb)
    if lum > 0.65:
        return _shade(bg_rgb, -55)
    if lum < 0.30:
        return _shade(bg_rgb, +60)
    return _shade(bg_rgb, -40)


# ── Silhouette helpers — one per category ─────────────────
# Each helper draws into (cx ± rx, cy ± ry) inside the canvas. The
# center / extent is set by the caller so silhouettes share screen
# real estate consistently. Coordinates flipped so y grows downward
# (Pillow's convention).


def _draw_top(draw, name_lower, cx, cy, rx, ry, color, accent):
    """T-shirt / blouse / sweater / cardigan / turtleneck / oxford /
    polo / camisole / tunic / tee — a standard shirt silhouette. Sub-
    type cues from the name keyword adjust details (turtleneck
    adds a high collar; cardigan splits at center; tank loses
    sleeves)."""
    # Body trapezoid.
    body_top = cy - ry * 0.6
    body_bot = cy + ry * 0.95
    waist_w = rx * 0.92
    hem_w = rx * 1.05
    body = [
        (cx - waist_w, body_top + ry * 0.18),
        (cx + waist_w, body_top + ry * 0.18),
        (cx + hem_w,   body_bot),
        (cx - hem_w,   body_bot),
    ]
    draw.polygon(body, fill=color, outline=accent, width=4)

    # Sleeves.
    sleeve_w = rx * 0.30
    sleeve_h = ry * 0.55
    if "tank" not in name_lower and "camisole" not in name_lower:
        # Left sleeve
        draw.polygon([
            (cx - waist_w, body_top + ry * 0.18),
            (cx - waist_w - sleeve_w, body_top + ry * 0.28),
            (cx - waist_w - sleeve_w * 0.95, body_top + ry * 0.28 + sleeve_h),
            (cx - waist_w + sleeve_w * 0.15, body_top + ry * 0.5),
        ], fill=color, outline=accent, width=4)
        # Right sleeve (mirrored)
        draw.polygon([
            (cx + waist_w, body_top + ry * 0.18),
            (cx + waist_w + sleeve_w, body_top + ry * 0.28),
            (cx + waist_w + sleeve_w * 0.95, body_top + ry * 0.28 + sleeve_h),
            (cx + waist_w - sleeve_w * 0.15, body_top + ry * 0.5),
        ], fill=color, outline=accent, width=4)

    # Neckline.
    neck_w = rx * 0.35
    neck_h = ry * 0.18
    if "turtleneck" in name_lower or "mock" in name_lower or "high-neck" in name_lower:
        # Tall neck cylinder.
        draw.rectangle(
            [(cx - neck_w * 0.7, body_top - ry * 0.05),
             (cx + neck_w * 0.7, body_top + ry * 0.10)],
            fill=color, outline=accent,
        )
    else:
        # Open neckline arc.
        draw.chord(
            [(cx - neck_w, body_top + ry * 0.06),
             (cx + neck_w, body_top + ry * 0.06 + neck_h * 1.5)],
            start=0, end=180, fill=accent, width=3,
        )

    # Center seam for cardigan / open shirt.
    if "cardigan" in name_lower:
        draw.line([(cx, body_top + ry * 0.18), (cx, body_bot)],
                  fill=accent, width=4)
    elif "shirt" in name_lower or "oxford" in name_lower or "button" in name_lower:
        # Faint placket line + buttons.
        draw.line([(cx, body_top + ry * 0.20), (cx, body_bot - ry * 0.05)],
                  fill=accent, width=4)
        for i in range(3):
            yy = body_top + ry * (0.30 + i * 0.18)
            draw.ellipse([(cx - 3, yy - 3), (cx + 3, yy + 3)], fill=accent)


def _draw_bottom(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Trousers / jeans / shorts / skirt / leggings / chinos."""
    if "skirt" in name_lower:
        # A-line skirt: narrow waist, wide hem.
        draw.polygon([
            (cx - rx * 0.60, cy - ry * 0.8),
            (cx + rx * 0.60, cy - ry * 0.8),
            (cx + rx * 1.05, cy + ry * 0.95),
            (cx - rx * 1.05, cy + ry * 0.95),
        ], fill=color, outline=accent, width=4)
        # Pleats hint.
        if "pleated" in name_lower:
            for off in (-0.4, -0.13, 0.13, 0.4):
                draw.line(
                    [(cx + rx * 0.6 * off, cy - ry * 0.65),
                     (cx + rx * 1.0 * off, cy + ry * 0.95)],
                    fill=accent, width=2,
                )
        return

    # Trousers / shorts: waistband + two legs.
    waist_top = cy - ry * 0.85
    crotch_y  = cy - ry * 0.05
    leg_inner = rx * 0.08
    leg_outer = rx * 0.78
    if "shorts" in name_lower:
        leg_bottom = cy + ry * 0.20
    elif "shorts" in name_lower:
        leg_bottom = cy + ry * 0.20
    else:
        leg_bottom = cy + ry * 0.95

    # Waistband
    draw.rectangle(
        [(cx - leg_outer, waist_top), (cx + leg_outer, waist_top + ry * 0.13)],
        fill=color, outline=accent,
    )
    # Left leg
    draw.polygon([
        (cx - leg_outer,  waist_top + ry * 0.13),
        (cx - leg_inner,  waist_top + ry * 0.13),
        (cx - leg_inner * 0.75,  leg_bottom),
        (cx - leg_outer * 0.85,  leg_bottom),
    ], fill=color, outline=accent, width=4)
    # Right leg
    draw.polygon([
        (cx + leg_outer,  waist_top + ry * 0.13),
        (cx + leg_inner,  waist_top + ry * 0.13),
        (cx + leg_inner * 0.75,  leg_bottom),
        (cx + leg_outer * 0.85,  leg_bottom),
    ], fill=color, outline=accent, width=4)
    # Center seam
    draw.line([(cx, waist_top + ry * 0.13), (cx, crotch_y)],
              fill=accent, width=4)


def _draw_dress(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Dress / gown / sundress / wrap / sheath / maxi / midi.
    Combined bodice + skirt. Sub-types: 'gown'/'maxi' → floor-length
    elongated skirt; 'sheath' → straight column; 'wrap' → center wrap line."""
    bodice_top = cy - ry * 0.8
    waist_y    = cy - ry * 0.0
    hem_y      = cy + ry * 0.98
    if "gown" in name_lower or "floor-length" in name_lower:
        hem_y = cy + ry * 1.05
    elif "midi" in name_lower:
        hem_y = cy + ry * 0.95

    bodice_half = rx * 0.65
    waist_half  = rx * 0.50
    is_sheath   = "sheath" in name_lower
    is_column   = is_sheath or "column" in name_lower
    if is_column:
        hem_half = rx * 0.55
    else:
        hem_half = rx * 1.05    # flared

    # Single polygon for bodice + skirt
    draw.polygon([
        (cx - bodice_half, bodice_top + ry * 0.18),
        (cx + bodice_half, bodice_top + ry * 0.18),
        (cx + waist_half,  waist_y),
        (cx + hem_half,    hem_y),
        (cx - hem_half,    hem_y),
        (cx - waist_half,  waist_y),
    ], fill=color, outline=accent, width=4)

    # Sleeves (most dresses are sleeveless; show only when name says so)
    if "long-sleeve" in name_lower or "long sleeve" in name_lower:
        sleeve_w = rx * 0.25
        # Left
        draw.polygon([
            (cx - bodice_half, bodice_top + ry * 0.18),
            (cx - bodice_half - sleeve_w, bodice_top + ry * 0.30),
            (cx - bodice_half - sleeve_w * 0.85, bodice_top + ry * 0.85),
            (cx - bodice_half + sleeve_w * 0.20, bodice_top + ry * 0.55),
        ], fill=color, outline=accent, width=4)
        # Right
        draw.polygon([
            (cx + bodice_half, bodice_top + ry * 0.18),
            (cx + bodice_half + sleeve_w, bodice_top + ry * 0.30),
            (cx + bodice_half + sleeve_w * 0.85, bodice_top + ry * 0.85),
            (cx + bodice_half - sleeve_w * 0.20, bodice_top + ry * 0.55),
        ], fill=color, outline=accent, width=4)

    # Neckline
    neck_w = rx * 0.30
    draw.chord(
        [(cx - neck_w, bodice_top + ry * 0.10),
         (cx + neck_w, bodice_top + ry * 0.32)],
        start=0, end=180, fill=accent, width=3,
    )

    # Wrap line for wrap dress
    if "wrap" in name_lower:
        draw.line([(cx - bodice_half * 0.8, bodice_top + ry * 0.25),
                   (cx + waist_half * 0.5, waist_y)],
                  fill=accent, width=4)
        # tie-knot dot
        draw.ellipse(
            [(cx + waist_half * 0.40, waist_y - 4),
             (cx + waist_half * 0.55, waist_y + 4)],
            fill=accent,
        )


def _draw_outerwear(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Coat / blazer / trench / parka / puffer / cardigan / vest /
    jacket. Body open at center (lapels), structured shoulders.
    Trench gets a belt line; vest loses sleeves; puffer gets quilt
    rows."""
    body_top = cy - ry * 0.85
    body_bot = cy + ry * 0.95
    shoulder = rx * 1.05
    waist    = rx * 0.95
    hem      = rx * 1.10

    # Body
    draw.polygon([
        (cx - shoulder, body_top + ry * 0.18),
        (cx + shoulder, body_top + ry * 0.18),
        (cx + waist,    cy + ry * 0.10),
        (cx + hem,      body_bot),
        (cx - hem,      body_bot),
        (cx - waist,    cy + ry * 0.10),
    ], fill=color, outline=accent, width=4)

    # Sleeves (skip for vest)
    if "vest" not in name_lower:
        sleeve_w = rx * 0.32
        # Left
        draw.polygon([
            (cx - shoulder, body_top + ry * 0.18),
            (cx - shoulder - sleeve_w * 0.5, body_top + ry * 0.32),
            (cx - shoulder - sleeve_w * 0.2, body_bot - ry * 0.05),
            (cx - shoulder + sleeve_w * 0.45, body_bot - ry * 0.12),
        ], fill=color, outline=accent, width=4)
        # Right
        draw.polygon([
            (cx + shoulder, body_top + ry * 0.18),
            (cx + shoulder + sleeve_w * 0.5, body_top + ry * 0.32),
            (cx + shoulder + sleeve_w * 0.2, body_bot - ry * 0.05),
            (cx + shoulder - sleeve_w * 0.45, body_bot - ry * 0.12),
        ], fill=color, outline=accent, width=4)

    # Center opening + lapels
    draw.line([(cx, body_top + ry * 0.18), (cx, body_bot)],
              fill=accent, width=4)
    # Lapel triangles
    draw.line([(cx - shoulder * 0.40, body_top + ry * 0.18),
               (cx, body_top + ry * 0.55)],
              fill=accent, width=4)
    draw.line([(cx + shoulder * 0.40, body_top + ry * 0.18),
               (cx, body_top + ry * 0.55)],
              fill=accent, width=4)

    # Trench belt
    if "trench" in name_lower:
        belt_y = cy + ry * 0.05
        draw.line([(cx - waist, belt_y), (cx + waist, belt_y)],
                  fill=accent, width=4)
        # buckle
        draw.rectangle(
            [(cx - rx * 0.08, belt_y - 5),
             (cx + rx * 0.08, belt_y + 5)],
            outline=accent, width=2,
        )

    # Puffer quilt rows
    if "puffer" in name_lower or "quilted" in name_lower:
        for k in range(3):
            yy = body_top + ry * (0.40 + k * 0.22)
            draw.line([(cx - shoulder * 0.85, yy),
                       (cx + shoulder * 0.85, yy)],
                      fill=accent, width=4)


def _draw_activewear(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Leggings / sports bra / athletic tee / joggers."""
    if "bra" in name_lower:
        # Two cup shapes side-by-side, band underneath.
        cup_r = rx * 0.42
        cy_band = cy + ry * 0.05
        draw.pieslice(
            [(cx - rx * 0.92, cy - ry * 0.35),
             (cx - rx * 0.08, cy + ry * 0.35)],
            start=0, end=180, fill=color, outline=accent,
        )
        draw.pieslice(
            [(cx + rx * 0.08, cy - ry * 0.35),
             (cx + rx * 0.92, cy + ry * 0.35)],
            start=0, end=180, fill=color, outline=accent,
        )
        # Band
        draw.rectangle(
            [(cx - rx * 0.95, cy_band),
             (cx + rx * 0.95, cy_band + ry * 0.20)],
            fill=color, outline=accent,
        )
        return

    if "legging" in name_lower or "tight" in name_lower:
        # Tight pants — fitted bottom silhouette.
        waist_top = cy - ry * 0.85
        leg_outer_top = rx * 0.85
        leg_outer_bot = rx * 0.55
        # Waistband
        draw.rectangle(
            [(cx - leg_outer_top, waist_top),
             (cx + leg_outer_top, waist_top + ry * 0.12)],
            fill=color, outline=accent,
        )
        # Legs (tighter than trousers — taper to ankle)
        draw.polygon([
            (cx - leg_outer_top, waist_top + ry * 0.12),
            (cx - rx * 0.05,     waist_top + ry * 0.12),
            (cx - rx * 0.05,     cy + ry * 0.95),
            (cx - leg_outer_bot, cy + ry * 0.95),
        ], fill=color, outline=accent, width=4)
        draw.polygon([
            (cx + leg_outer_top, waist_top + ry * 0.12),
            (cx + rx * 0.05,     waist_top + ry * 0.12),
            (cx + rx * 0.05,     cy + ry * 0.95),
            (cx + leg_outer_bot, cy + ry * 0.95),
        ], fill=color, outline=accent, width=4)
        draw.line([(cx, waist_top + ry * 0.12), (cx, cy - ry * 0.10)],
                  fill=accent, width=4)
        return

    if "jogger" in name_lower:
        # Trousers but with cuffed ankles.
        _draw_bottom(draw, name_lower, cx, cy, rx, ry, color, accent)
        # Cuff lines
        cuff_y = cy + ry * 0.78
        draw.line([(cx - rx * 0.70, cuff_y), (cx - rx * 0.18, cuff_y)],
                  fill=accent, width=4)
        draw.line([(cx + rx * 0.18, cuff_y), (cx + rx * 0.70, cuff_y)],
                  fill=accent, width=4)
        return

    # Athletic tee → re-use the top silhouette.
    _draw_top(draw, name_lower, cx, cy, rx, ry, color, accent)


def _draw_shoes(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Pumps / heels / sneakers / boots / sandals / flats. Profile view."""
    sole_y = cy + ry * 0.45

    if "heel" in name_lower or "pump" in name_lower or \
            "stiletto" in name_lower:
        # Heel profile: pointed toe, arch, thin heel.
        toe_x = cx + rx * 0.95
        heel_x = cx - rx * 0.65
        body = [
            (toe_x, sole_y),
            (cx + rx * 0.30, cy - ry * 0.05),
            (cx - rx * 0.15, cy - ry * 0.15),
            (heel_x + rx * 0.10, cy - ry * 0.05),
            (heel_x, sole_y - ry * 0.20),
        ]
        draw.polygon(body, fill=color, outline=accent, width=4)
        # Heel column
        draw.polygon([
            (heel_x, sole_y - ry * 0.20),
            (heel_x + rx * 0.06, sole_y - ry * 0.20),
            (heel_x + rx * 0.10, sole_y + ry * 0.05),
            (heel_x - rx * 0.02, sole_y + ry * 0.05),
        ], fill=accent)
        # Sole shadow
        draw.line([(heel_x, sole_y + ry * 0.05),
                   (toe_x, sole_y + ry * 0.05)],
                  fill=accent, width=4)
        return

    if "sandal" in name_lower or "strappy" in name_lower:
        # Open sole + strap arcs.
        toe_x = cx + rx * 0.95
        heel_x = cx - rx * 0.65
        # Sole
        draw.line([(heel_x, sole_y), (toe_x, sole_y)],
                  fill=accent, width=5)
        # Strap arc (across the foot)
        draw.arc(
            [(cx - rx * 0.30, cy - ry * 0.10),
             (cx + rx * 0.45, sole_y)],
            start=180, end=360, fill=accent, width=4,
        )
        # Heel
        draw.polygon([
            (heel_x, sole_y),
            (heel_x + rx * 0.08, sole_y),
            (heel_x + rx * 0.12, sole_y + ry * 0.25),
            (heel_x - rx * 0.02, sole_y + ry * 0.25),
        ], fill=accent)
        return

    if "boot" in name_lower:
        # Ankle/Chelsea boot — taller shaft, rounded toe.
        draw.polygon([
            (cx - rx * 0.55, cy - ry * 0.55),
            (cx + rx * 0.30, cy - ry * 0.55),
            (cx + rx * 0.45, sole_y - ry * 0.15),
            (cx + rx * 0.95, sole_y - ry * 0.10),
            (cx + rx * 0.95, sole_y),
            (cx - rx * 0.55, sole_y),
        ], fill=color, outline=accent, width=4)
        # Sole
        draw.line([(cx - rx * 0.55, sole_y),
                   (cx + rx * 0.95, sole_y)],
                  fill=accent, width=4)
        # Pull tab
        draw.rectangle(
            [(cx + rx * 0.10, cy - ry * 0.70),
             (cx + rx * 0.28, cy - ry * 0.55)],
            outline=accent, width=2,
        )
        return

    if "sneaker" in name_lower or "running" in name_lower or \
            "trainer" in name_lower:
        # Low sneaker with chunky sole.
        # Upper
        draw.polygon([
            (cx - rx * 0.85, sole_y - ry * 0.05),
            (cx - rx * 0.60, cy - ry * 0.18),
            (cx + rx * 0.10, cy - ry * 0.18),
            (cx + rx * 0.85, cy + ry * 0.10),
            (cx + rx * 0.95, sole_y - ry * 0.05),
        ], fill=color, outline=accent, width=4)
        # Sole
        draw.rectangle(
            [(cx - rx * 0.92, sole_y - ry * 0.05),
             (cx + rx * 0.98, sole_y + ry * 0.05)],
            fill=accent,
        )
        # Lace lines
        for k in range(3):
            xx = cx - rx * 0.25 + k * rx * 0.18
            draw.line(
                [(xx, cy - ry * 0.18),
                 (xx + rx * 0.06, cy - ry * 0.05)],
                fill=accent, width=2,
            )
        return

    # Default — ballet flat / loafer outline.
    draw.polygon([
        (cx - rx * 0.55, cy + ry * 0.05),
        (cx + rx * 0.90, cy + ry * 0.10),
        (cx + rx * 0.95, sole_y),
        (cx - rx * 0.55, sole_y),
    ], fill=color, outline=accent, width=4)
    # Vamp (top edge cutout)
    draw.chord(
        [(cx - rx * 0.40, cy - ry * 0.05),
         (cx + rx * 0.30, cy + ry * 0.20)],
        start=180, end=360, fill=accent, width=3,
    )


def _draw_accessory(draw, name_lower, cx, cy, rx, ry, color, accent):
    """Earrings, necklace, scarf, handbag, tote, clutch, belt."""
    if "hoop" in name_lower:
        # Two hoops side by side.
        r = rx * 0.40
        draw.ellipse(
            [(cx - rx * 0.80 - r, cy - r),
             (cx - rx * 0.80 + r, cy + r)],
            outline=accent, width=5,
        )
        draw.ellipse(
            [(cx + rx * 0.80 - r, cy - r),
             (cx + rx * 0.80 + r, cy + r)],
            outline=accent, width=5,
        )
        # Posts
        draw.ellipse(
            [(cx - rx * 0.80 - 3, cy - r - 5),
             (cx - rx * 0.80 + 3, cy - r + 1)],
            fill=accent,
        )
        draw.ellipse(
            [(cx + rx * 0.80 - 3, cy - r - 5),
             (cx + rx * 0.80 + 3, cy - r + 1)],
            fill=accent,
        )
        return

    if "stud" in name_lower or "earring" in name_lower:
        # Two filled circles side by side.
        r = rx * 0.30
        draw.ellipse(
            [(cx - rx * 0.55 - r, cy - r),
             (cx - rx * 0.55 + r, cy + r)],
            fill=color, outline=accent, width=3,
        )
        draw.ellipse(
            [(cx + rx * 0.55 - r, cy - r),
             (cx + rx * 0.55 + r, cy + r)],
            fill=color, outline=accent, width=3,
        )
        return

    if "necklace" in name_lower or "chain" in name_lower:
        # V-chain with pendant.
        draw.arc(
            [(cx - rx * 0.90, cy - ry * 0.85),
             (cx + rx * 0.90, cy + ry * 0.30)],
            start=0, end=180, fill=accent, width=3,
        )
        draw.ellipse(
            [(cx - rx * 0.10, cy + ry * 0.20),
             (cx + rx * 0.10, cy + ry * 0.40)],
            fill=color, outline=accent, width=3,
        )
        return

    if "scarf" in name_lower:
        # Triangle silk scarf with knot.
        draw.polygon([
            (cx - rx * 0.85, cy - ry * 0.45),
            (cx + rx * 0.85, cy - ry * 0.45),
            (cx,              cy + ry * 0.75),
        ], fill=color, outline=accent, width=4)
        draw.rectangle(
            [(cx - rx * 0.20, cy - ry * 0.60),
             (cx + rx * 0.20, cy - ry * 0.40)],
            fill=color, outline=accent,
        )
        # Print dots hint
        for (xx, yy) in (
            (cx - rx * 0.3, cy - ry * 0.1),
            (cx + rx * 0.25, cy + ry * 0.05),
            (cx - rx * 0.05, cy + ry * 0.3),
        ):
            draw.ellipse([(xx - 3, yy - 3), (xx + 3, yy + 3)], fill=accent)
        return

    if "belt" in name_lower:
        # Horizontal belt with buckle.
        bag_h = ry * 0.20
        draw.rectangle(
            [(cx - rx * 0.95, cy - bag_h),
             (cx + rx * 0.95, cy + bag_h)],
            fill=color, outline=accent,
        )
        # Buckle
        draw.rectangle(
            [(cx - rx * 0.15, cy - bag_h - 6),
             (cx + rx * 0.15, cy + bag_h + 6)],
            outline=accent, width=3,
        )
        return

    if "tote" in name_lower:
        # Rectangular tote with two strap arcs.
        body_top = cy - ry * 0.40
        draw.rectangle(
            [(cx - rx * 0.85, body_top),
             (cx + rx * 0.85, cy + ry * 0.80)],
            fill=color, outline=accent,
        )
        # Long straps
        draw.arc(
            [(cx - rx * 0.60, body_top - ry * 0.60),
             (cx + rx * 0.05, body_top + ry * 0.05)],
            start=0, end=180, fill=accent, width=4,
        )
        draw.arc(
            [(cx - rx * 0.05, body_top - ry * 0.60),
             (cx + rx * 0.60, body_top + ry * 0.05)],
            start=0, end=180, fill=accent, width=4,
        )
        return

    if "clutch" in name_lower:
        # Long narrow rectangle.
        draw.rectangle(
            [(cx - rx * 0.95, cy - ry * 0.18),
             (cx + rx * 0.95, cy + ry * 0.18)],
            fill=color, outline=accent,
        )
        # Center clasp
        draw.line([(cx - rx * 0.95, cy - ry * 0.04),
                   (cx + rx * 0.95, cy - ry * 0.04)],
                  fill=accent, width=4)
        draw.ellipse(
            [(cx - rx * 0.04, cy - ry * 0.08),
             (cx + rx * 0.04, cy)],
            fill=accent,
        )
        return

    # Default — generic handbag with single top-handle.
    body_top = cy - ry * 0.30
    body_bot = cy + ry * 0.75
    draw.rectangle(
        [(cx - rx * 0.78, body_top),
         (cx + rx * 0.78, body_bot)],
        fill=color, outline=accent,
    )
    # Top-handle arc
    draw.arc(
        [(cx - rx * 0.50, body_top - ry * 0.55),
         (cx + rx * 0.50, body_top + ry * 0.05)],
        start=0, end=180, fill=accent, width=5,
    )


_DRAW_BY_TYPE = {
    "top":        _draw_top,
    "bottom":     _draw_bottom,
    "dress":      _draw_dress,
    "outerwear":  _draw_outerwear,
    "activewear": _draw_activewear,
    "shoes":      _draw_shoes,
    "accessory":  _draw_accessory,
}


# ── Real-photo fetcher (Unsplash Source, no API key) ─────

# Per-type query suffixes — biased toward FULL-ITEM catalog / product
# imagery. The "full length" / "full item" / "pair" wording pushes
# Pexels toward photographs where the entire garment is visible,
# instead of cropped detail / texture / runway-walking shots. The
# loader tries the variants in order and stops at the first non-empty
# result set.
_QUERY_BIAS_BY_TYPE: Dict[str, Tuple[str, ...]] = {
    "top":        ("blouse flat lay full item",
                   "shirt flat lay product photo",
                   "clothing flat lay full item",
                   "product photo white background",
                   ""),
    "bottom":     ("trousers flat lay product photo",
                   "pants flat lay full item",
                   "clothing flat lay full item",
                   "product photo white background",
                   ""),
    "dress":      ("full length dress product photo",
                   "dress on hanger full length",
                   "dress flat lay full item",
                   "product photo white background",
                   ""),
    "outerwear":  ("coat on hanger full length",
                   "jacket flat lay product photo",
                   "outerwear product photo",
                   "product photo white background",
                   ""),
    "activewear": ("activewear flat lay full set",
                   "sportswear product photo",
                   "clothing flat lay full item",
                   ""),
    "shoes":      ("shoes pair product photo",
                   "shoes on white background",
                   "shoes studio shot",
                   ""),
    "accessory":  ("product photo white background",
                   "studio shot product photo",
                   ""),
}

# Per-type aspect-ratio sweet spots. The "ideal" is the W/H ratio of
# a typical catalog tile for that category; the band is the range
# where candidates score well. Outside the band, candidates get a
# heavy penalty so they only win when nothing else is on offer.
#
# Numbers come from how a fully-visible item tends to be framed:
#   - Full-length dresses / coats: tall narrow rectangle (ratio ~0.5–0.7).
#   - Tops, bottoms, activewear:   medium portrait        (ratio ~0.7–0.9).
#   - Shoes / handbags:            squat-ish              (ratio ~0.8–1.05).
_ASPECT_BY_TYPE: Dict[str, Tuple[float, float, float]] = {
    # (ideal, low, high)
    "top":        (0.78, 0.55, 0.95),
    "bottom":     (0.72, 0.50, 0.90),
    "dress":      (0.62, 0.42, 0.82),
    "outerwear":  (0.62, 0.45, 0.85),
    "activewear": (0.78, 0.55, 0.95),
    "shoes":      (0.90, 0.65, 1.10),
    "accessory":  (0.90, 0.65, 1.10),
}
_DEFAULT_ASPECT = (0.78, 0.55, 0.95)

# Fetching 25 candidates per query (vs. 15 earlier) gives the scorer
# room to skip cropped / face-only shots without falling off the end
# of the result page.
_CANDIDATES_PER_SEARCH = 25

# How tightly the candidate dimensions must match the target before
# we cover-crop. Sources that deviate more than this fraction from
# the target aspect get LETTERBOXED (object-fit: contain) so the
# full garment stays visible, padded with white. Sources within the
# threshold are center-cropped (object-fit: cover) for a tight tile.
_RESIZE_COVER_TOLERANCE = 0.20


def _pexels_search(query: str, key: str, per_page: int,
                   timeout: float) -> list:
    """Run one Pexels search. Returns the `photos` list (possibly empty)
    on success, [] on any failure. Never raises."""
    if not key or not query:
        return []
    params = {
        "query":       query.replace(",", " "),
        "per_page":    per_page,
        "orientation": "portrait",
    }
    url = f"{_PEXELS_BASE}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": key,
            "User-Agent":    _FETCH_UA,
            "Accept":        "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read(2 * 1024 * 1024))
        return data.get("photos") or []
    except Exception:
        return []


# ── Alt-text validation lexicons ──────────────────────────────────
# Pexels returns an `alt` description for each photo. The PRIOR scorer
# ignored this field entirely, so a photo of a woman posing in a
# green silk blouse scored identically to an ivory blouse on a hanger.
# These lexicons let _score_candidate penalize lifestyle / person-
# focused shots and reward product-style imagery.

# Tokens that signal a person/lifestyle/editorial photo. Heavy penalty
# when found. Word-boundary regex elsewhere so we don't false-match
# substrings like "personal" or "modelled".
_PERSON_TOKENS = {
    "woman", "women", "man", "men", "person", "people",
    "girl", "boy", "lady", "ladies", "guy", "guys",
    "model", "models", "modeling", "modelling",
    "portrait", "pose", "poses", "posing", "posed",
    "wearing", "wears", "wear",
    "barefoot", "smiling", "stands", "standing", "stand",
    "stroll", "strolling", "exercise", "exercises", "exercising",
    "athlete", "athletes", "performing",
    "female", "male", "she ", "he ",
    "selfie", "shoot", "fashion shoot", "street style", "street-style",
    "muscular", "fitness model",
    # Body-part close-ups — "hands in a jacket", "feet in heels",
    # "hand holding shoes" etc. Person-centric even without naming
    # the person.
    "hands in", "hand in", "feet in", "foot in", "legs in", "leg in",
    "neck in", "arms in", "arm in", "torso", "waist of",
    "hand holding", "hands holding", "holding shoes", "holding a",
    "holding the",
    # Influencer / presenter / dancer alts — common Pexels lifestyle
    # category that v6 missed: "fashion vlogger presents", "ballerina
    # holding shoes", etc.
    "vlogger", "blogger", "influencer", "ballerina", "dancer",
    "presents", "presenting", "showcases a", "showcasing a",
    # Age-mismatch cues — children's/baby/kid alts pollute the adult
    # wardrobe demo. "Cute children's blouse" sneaked past v6.
    "child", "children", "children's", "childs", "baby", "babies",
    "kid", "kids", "kid's", "teen", "teenager", "teenagers",
}

# Tokens suggesting a SINGLE-product / catalog shot. Bonus when found.
_PRODUCT_TOKENS = {
    "flat lay", "flatlay", "on hanger", "on a hanger",
    "hanger", "hangers", "hanging",
    "isolated", "white background", "plain background",
    "studio shot", "studio shots", "in studio",
    "on display", "displayed", "showcased", "showcasing",
    "product photo", "catalog", "catalogue", "lookbook",
    "draped on", "draped over", "folded", "stacked",
    "top view of", "close-up of an", "close-up of a", "macro of",
}

# Per-type required category words. A candidate's alt MUST contain at
# least one of these tokens or it is rejected outright (+20 penalty,
# "category miss"). Synonyms are listed so a "sweater" can stand in
# for "cardigan", etc.
#
# CAREFUL with ambiguous words. "top" was originally in here but it
# matched "Top view of scented candles" (Pexels alts very commonly
# start with "Top view of"). Removed to prevent that false positive.
# "flat" / "flats" are kept for shoes only — there's no off-category
# reading. Same for "knit" (word-boundary regex blocks "knitting").
_CATEGORY_TOKENS: Dict[str, Tuple[str, ...]] = {
    "top":        ("blouse", "shirt", "tee", "t-shirt", "sweater",
                   "cardigan", "knit", "camisole", "tunic", "polo",
                   "turtleneck", "tank top"),
    "bottom":     ("trouser", "trousers", "pants", "pant", "jeans",
                   "skirt", "shorts", "chino", "chinos", "legging",
                   "leggings", "slacks"),
    "dress":      ("dress", "gown", "frock", "sundress"),
    "outerwear":  ("coat", "jacket", "blazer", "vest", "trench",
                   "parka", "puffer"),
    "activewear": ("activewear", "sportswear", "athletic", "athleisure",
                   "tee", "t-shirt", "tshirt", "training", "workout",
                   "gym", "yoga", "sports bra", "leggings", "jogger",
                   "joggers"),
    "shoes":      ("shoe", "shoes", "heel", "heels", "pump", "pumps",
                   "flat", "flats", "sneaker", "sneakers", "boot",
                   "boots", "sandal", "sandals", "loafer", "loafers"),
    "accessory":  ("scarf", "belt", "handbag", "bag", "tote", "clutch",
                   "necklace", "earring", "earrings", "hoop", "stud",
                   "chain", "accessory", "accessories"),
}

# Non-garment props common in lifestyle flat lays. When a garment is
# the named category match BUT one of these props also appears, the
# photo's main subject is probably the prop (a flat lay sells the
# mood, not the garment). Heavy penalty.
_PROP_TOKENS = {
    # Personal-care
    "skincare", "perfume", "fragrance", "cosmetic", "cosmetics",
    "makeup", "lipstick", "mascara", "lotion", "moisturizer",
    # Decorative
    "candle", "candles", "bouquet", "roses", "rose petals",
    "flower", "flowers", "petal", "petals",
    "plant", "plants", "leafy",
    "vase", "tray",
    # Food / drink
    "coffee", "tea", "teacup", "mug", "wine glass", "wine glasses",
    "champagne", "cocktail",
    # Stationery / lifestyle
    "magazine", "magazines", "book", "books", "notebook", "notebooks",
    "art supplies", "instant camera",
    # Tech
    "earphone", "earphones", "headphones", "smartphone",
    "yoga mat", "wedding ring", "wedding rings",
    # Containers (very common prop in skincare-flat-lay alts)
    "container", "containers", "bottle", "bottles", "jar", "jars",
    # Wedding/bridal context — implicitly white, conflicts with most
    # demo items (DM-D006 black dress picked "wedding dress in bridal
    # shop"). Penalize unless the item itself is white/ivory/cream.
    # (Implementation note: the prop check fires unconditionally; if
    # the alt color also matches the item family, the bonuses can
    # outweigh.)
    "wedding", "bridal", "wedding dress",
}

# Tokens suggesting MULTIPLE separate garments in one photo — heavy
# penalty when the alt lists more than one clothing noun joined by
# commas / "and". Detection regex below the lexicon.
_MULTI_GARMENT_NOUNS = (
    "blouse", "shirt", "tee", "t-shirt", "sweater", "cardigan",
    "blazer", "jacket", "coat", "vest", "trench",
    "trouser", "trousers", "pants", "jeans", "skirt", "shorts",
    "dress", "gown",
    "shoe", "shoes", "heel", "heels", "boot", "boots", "sneaker", "sneakers",
    "scarf", "belt", "bag", "handbag", "tote",
)

# Color synonyms — small but covers the demo palette. Used by the alt
# scorer to reward color matches and penalize obvious conflicts.
_COLOR_FAMILY = {
    "ivory":      {"ivory", "cream", "off-white", "off white", "white"},
    "cream":      {"cream", "ivory", "off-white", "off white", "white"},
    "white":      {"white", "ivory", "cream", "off-white"},
    "beige":      {"beige", "tan", "nude", "sand", "khaki"},
    "tan":        {"tan", "beige", "khaki", "camel", "nude"},
    "nude":       {"nude", "beige", "tan", "blush"},
    "camel":      {"camel", "tan", "caramel"},  # camel ≠ chocolate brown
    "olive":      {"olive", "army", "khaki", "dark green", "olive green"},
    "sage":       {"sage", "mint", "light green"},
    "gold":       {"gold", "yellow", "mustard", "amber"},
    "burgundy":   {"burgundy", "bordeaux", "wine", "maroon", "oxblood",
                   "dark red"},
    "red":        {"red", "scarlet", "crimson", "maroon", "bordeaux"},
    "rust":       {"rust", "burnt orange", "terracotta", "russet"},
    "terracotta": {"terracotta", "rust", "burnt orange", "clay", "brick"},
    "forest":     {"forest", "dark green", "evergreen", "pine"},
    "navy":       {"navy", "dark blue", "deep blue", "midnight"},
    "blue":       {"blue", "navy", "azure", "cobalt"},
    "black":      {"black"},
    "charcoal":   {"charcoal", "dark grey", "dark gray", "graphite",
                   "slate"},
    "grey":       {"grey", "gray", "slate", "silver"},
    "silver":     {"silver", "grey", "gray", "metallic"},
    "brown":      {"brown", "chocolate", "espresso", "coffee"},
    "pink":       {"pink", "rose", "blush", "fuchsia"},
}

# Universe of color words the alt scorer recognizes. If alt contains a
# color word from THIS set that is not in the item's own family, that's
# a soft conflict (+2). Stronger conflicts come from the disjoint-pair
# list below.
_ALL_COLOR_WORDS = {
    "ivory", "cream", "off-white", "off white", "white",
    "beige", "tan", "nude", "sand", "khaki",
    "camel", "caramel",
    "olive", "army", "sage", "mint",
    "gold", "yellow", "mustard", "amber",
    "burgundy", "bordeaux", "wine", "maroon", "oxblood",
    "red", "scarlet", "crimson",
    "rust", "burnt orange", "terracotta", "russet", "clay", "brick",
    "forest", "evergreen", "pine",
    "navy", "azure", "cobalt", "midnight",
    "blue", "teal", "turquoise",
    "black",
    "charcoal", "graphite", "slate",
    "grey", "gray", "silver",
    "brown", "chocolate", "espresso", "coffee",
    "pink", "rose", "blush", "fuchsia",
    "purple", "violet", "lavender", "lilac",
    "orange", "peach", "coral", "salmon",
    "green",
}

# Tokens that DEFINITELY conflict — when these appear and the item's
# color family doesn't include them, the candidate is almost certainly
# the wrong color. Penalty is heavier (+7) than a soft conflict.
_DISJOINT_COLOR_FAMILIES = (
    ({"green", "olive", "sage", "forest"},
     {"red", "burgundy", "rust", "terracotta", "wine", "scarlet",
      "maroon", "bordeaux"}),
    ({"green", "olive", "sage", "forest"},
     {"blue", "navy", "azure", "cobalt"}),
    ({"green", "olive", "sage", "forest"},
     {"orange", "pink"}),
    ({"black", "charcoal", "graphite"},
     {"white", "ivory", "cream", "off-white"}),
    ({"black"},
     {"brown", "chocolate", "espresso", "tan", "beige", "camel"}),
    ({"black"},
     {"burgundy", "bordeaux", "wine", "maroon", "red"}),
    ({"black"},
     {"pink", "rose", "blush"}),
    # Burgundy / wine / oxblood items vs the white/ivory family.
    ({"burgundy", "bordeaux", "wine", "maroon", "oxblood"},
     {"white", "ivory", "cream", "off-white"}),
    # Camel / tan / beige vs orange/red (DM-B002 picked an orange
    # jacket as a camel trouser).
    ({"camel", "tan", "beige"},
     {"orange", "red", "scarlet"}),
    ({"camel", "tan", "beige"},
     {"black", "navy", "burgundy", "wine"}),
    ({"red", "burgundy", "wine", "bordeaux"},
     {"blue", "navy", "green"}),
    ({"orange", "terracotta", "rust"},
     {"green", "blue", "navy"}),
    ({"pink", "rose", "blush", "fuchsia"},
     {"beige", "black", "navy", "olive", "green"}),
)

# Collective-noun cues — "a collection of coats", "stack of sweaters",
# "various dresses". These signal multiple items even when only ONE
# clothing noun appears, so the regular multi-garment check (which
# requires ≥ 2 distinct nouns) misses them.
_COLLECTIVE_CUES = (
    "collection of", "stack of", "row of", "rack of", "rows of",
    "stacks of", "stacked ", "various ", "multiple ", "several ", "many ",
    "assortment of", "set of", "lineup of", "line up of", "array of",
    "selection of",
)


def _alt_analysis(alt: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect a Pexels `alt` string and return a diagnosis used by
    _score_candidate. Returns a dict with:
      penalty:        float   — sum of score penalties (higher = worse)
      bonus:          float   — sum of score bonuses   (subtracted from penalty)
      category_match: bool    — alt contains a token for the item type
      person_match:   bool    — alt names a person / pose / wearing-style
      multi_match:    bool    — alt lists ≥ 2 distinct clothing nouns
      color_match:    bool    — alt mentions the item color family
      color_conflict: bool    — alt mentions a disjoint color family
      product_match:  bool    — alt contains a product/catalog cue
      reasons:        list[str] — human-readable explanation for the report
    """
    import re
    a = (alt or "").lower()
    item_type = (item.get("type") or "").lower()
    item_color = (item.get("color") or "").lower().strip()

    reasons: list = []
    penalty = 0.0
    bonus = 0.0

    # Category check — uses WORD BOUNDARIES so "knit" doesn't match
    # "knitting" (the prior substring check was a false-positive source
    # — a photo of yarn and knitting needles was treated as a sweater).
    cat_tokens = _CATEGORY_TOKENS.get(item_type, ())
    category_match = False
    if cat_tokens:
        for t in cat_tokens:
            if re.search(rf"\b{re.escape(t)}\b", a):
                category_match = True
                break
    if cat_tokens and not category_match:
        penalty += 20.0
        reasons.append(f"alt missing required {item_type} noun")

    # Person tokens — heavy penalty. Treat the alt's first ~120 chars
    # as the meaningful subject; person tokens after that are less
    # determinative.
    head = a[:140]
    person_hits = [t for t in _PERSON_TOKENS if t.strip() in head]
    person_match = bool(person_hits)
    if person_match:
        # +6 per hit, capped at +12. Two-plus person tokens is almost
        # always a portrait — make it unattractive.
        penalty += min(12.0, 6.0 * len(person_hits))
        reasons.append(f"person/lifestyle ({', '.join(person_hits[:3])})")

    # Multi-garment listing — find 2+ distinct clothing nouns. Comma /
    # "and" separated.
    distinct_nouns = set()
    for noun in _MULTI_GARMENT_NOUNS:
        if re.search(rf"\b{re.escape(noun)}\b", a):
            distinct_nouns.add(noun)
    multi_match = len(distinct_nouns) >= 2
    # Collective-noun cue ("collection of coats") — counts as multi.
    collective_hit = next((c for c in _COLLECTIVE_CUES if c in a), "")
    if collective_hit:
        multi_match = True

    # Comma-list heuristic: a flat-lay alt that enumerates ≥3 things
    # via comma separators (e.g. "pink sports bra, sneakers, and yoga
    # mat") almost always shows multiple loose items. Catches novel
    # noun combinations the _MULTI_GARMENT_NOUNS list misses.
    comma_list_hit = False
    if not multi_match:
        # Trim off the leading category clause ("Flat lay of") so we
        # don't over-trigger on "Flat lay, top-down view, ..." style
        # marketing copy.
        body = a.split(" of ", 1)[-1] if " of " in a else a
        commas = body.count(",")
        and_count = body.count(" and ")
        if commas >= 2 or (commas >= 1 and and_count >= 1):
            comma_list_hit = True
            multi_match = True

    if multi_match:
        penalty += 8.0
        why = (collective_hit if collective_hit
               else "comma-list" if comma_list_hit
               else ", ".join(sorted(distinct_nouns)[:3]))
        reasons.append(f"multi-garment ({why})")

    # Color check. Four states (color_match and color_conflict can BOTH
    # be true — e.g. "clay pot in front of GREEN dress" matches the
    # terracotta family on "clay" but ALSO names green, which is
    # disjoint from terracotta. Conflict takes precedence over match.)
    color_match = False
    color_conflict = False
    if item_color:
        synonyms = _COLOR_FAMILY.get(item_color, {item_color})
        family_hit = any(c in a for c in synonyms)
        # Disjoint check ALWAYS runs, regardless of family_hit. The
        # earlier version skipped it after a family hit, which let
        # "clay pot in front of green dress" slip through.
        disjoint_hit = False
        for fam_a, fam_b in _DISJOINT_COLOR_FAMILIES:
            if synonyms & fam_a and any(t in a for t in fam_b):
                disjoint_hit = True
                break
            if synonyms & fam_b and any(t in a for t in fam_a):
                disjoint_hit = True
                break
        if disjoint_hit:
            color_conflict = True
            penalty += 7.0
            reasons.append(f"color conflict (item={item_color})")
        elif family_hit:
            color_match = True
            bonus += 1.5
            reasons.append(f"color match ({item_color})")
        else:
            # Soft conflict: alt names ANY color word that isn't in
            # the item's family.
            alt_colors = {c for c in _ALL_COLOR_WORDS if c in a}
            out_of_family = alt_colors - synonyms
            if alt_colors and out_of_family == alt_colors:
                penalty += 2.0
                reasons.append(
                    f"soft color mismatch ({sorted(out_of_family)[0]} "
                    f"vs item {item_color})"
                )

    # Product / catalog cues — bonus.
    product_hits = [t for t in _PRODUCT_TOKENS if t in a]
    product_match = bool(product_hits)
    if product_match:
        bonus += 1.0 + 0.5 * min(3, len(product_hits))
        reasons.append(f"product cue ({product_hits[0]})")

    # Prop penalty — when the alt names lifestyle props (skincare,
    # candles, bouquets, plants, books, coffee, etc.) alongside the
    # garment, the photo's main subject is almost certainly the
    # prop / mood, not the garment we want for the demo card.
    prop_hits = [t for t in _PROP_TOKENS if t in a]
    if prop_hits:
        # +5 per prop, capped at +10. Two props in one alt is enough
        # to push a borderline candidate over the confidence threshold.
        penalty += min(10.0, 5.0 * len(prop_hits))
        reasons.append(f"lifestyle prop ({', '.join(prop_hits[:2])})")

    return {
        "penalty":        penalty,
        "bonus":          bonus,
        "category_match": category_match,
        "person_match":   person_match,
        "multi_match":    multi_match,
        "color_match":    color_match,
        "color_conflict": color_conflict,
        "product_match":  product_match,
        "reasons":        reasons,
    }


def _score_candidate(photo: dict, item_type: str = "",
                      item: Optional[Dict[str, Any]] = None) -> float:
    """Lower is better. Combines:

      - aspect-ratio fit  (per-type sweet spot)
      - source pixel size (tiebreaker, larger is slightly better)
      - alt-text analysis (heavy penalties for person / multi-garment /
        wrong color / off-category; bonuses for product cues + color
        match)

    The alt-text component is the critical addition over the v2 scorer.
    Without it, lifestyle photos were tied with product photos on
    aspect ratio alone, and Pexels' default ranking — which favors
    "engaging" portraits — won every tie.
    """
    try:
        w = float(photo.get("width") or 0)
        h = float(photo.get("height") or 0)
        if w <= 0 or h <= 0:
            return 99.0
        ratio = w / h
    except Exception:
        return 99.0

    ideal, low, high = _ASPECT_BY_TYPE.get(
        (item_type or "").lower(), _DEFAULT_ASPECT)
    if ratio < low or ratio > high:
        base = 10.0 + abs(ratio - ideal)
    else:
        base = abs(ratio - ideal)

    # Pixel-size tiebreaker.
    long_side = max(w, h)
    if long_side >= 1500:
        base -= 0.02
    elif long_side < 700:
        base += 0.10

    # Alt-text adjustment.
    if item is not None:
        diag = _alt_analysis(photo.get("alt") or "", item)
        base += diag["penalty"]
        base -= diag["bonus"]

    return base


# Confidence threshold: if the best candidate's score is above this,
# the alt-text checks flagged the photo as bad — fall back to the
# silhouette renderer rather than ship a wrong image.
# Tuned against probe v5 + v6 with prop penalty:
#   clean product / hanger / single-item shots score ≤ 0
#   single-item with one weak issue scores 0.5 – 1.5
#   props + lifestyle scores ≥ 3
#   person / multi-garment scores ≥ 5
# Set to 1.5 for demo-grade strictness — better to show a silhouette
# than a flat lay where skincare bottles share the frame with the top.
_CONFIDENCE_THRESHOLD = 1.5


# Photo-ID dedup. Prevents the same Pexels photo from being assigned
# to multiple wardrobe items (the v3 loader assigned ONE skincare
# flat lay to three different items, because that photo passed basic
# checks for top / linen tee / midi skirt). Reset at the start of
# every load_demo_wardrobe call.
import threading as _threading
_used_photo_ids: set = set()
_used_photo_lock = _threading.Lock()


def _reset_used_photo_ids() -> None:
    """Reset the dedup set; called by load_demo_wardrobe."""
    global _used_photo_ids
    with _used_photo_lock:
        _used_photo_ids = set()


def _claim_photo_id(pid) -> bool:
    """Atomically claim a Pexels photo id. Returns True if newly
    claimed, False if already taken by another item this load."""
    with _used_photo_lock:
        if pid in _used_photo_ids:
            return False
        _used_photo_ids.add(pid)
        return True


def _fetch_real_photo(
    query: str,
    w: int = 400,
    h: int = 500,
    timeout: float = _FETCH_TIMEOUT,
    item_type: str = "",
    item_color: str = "",
) -> Tuple[bytes, str, str]:
    """
    Fetch a real, keyword-matched product photo from Pexels.

    Returns ``(image_bytes, photographer, photo_url)``. On any failure
    (no key, network error, no result, decode error, rate limit) returns
    ``(b"", "", "")`` — the loader falls back to silhouette.

    Strategy:
      1. Try the query with a product-bias suffix derived from item_type
         ("clothing flat lay", "shoes product photo", etc.).
      2. If that returns zero results, fall back to the raw query.
      3. From the candidate pool, pick the photo whose aspect ratio is
         closest to a typical e-commerce product tile (~0.75 portrait).
         Wider lifestyle / model shots get a heavy penalty so they only
         win when the query produced nothing else.

    Pexels requires attribution; the returned photographer name + photo
    page URL are stored on the wardrobe record so the UI can render
    "Photo: <Name> · Pexels" under each demo card.
    """
    key = _pexels_api_key()
    if not key or not query:
        return b"", "", ""

    biases = _QUERY_BIAS_BY_TYPE.get((item_type or "").lower(),
                                      ("product photo white background", ""))

    # Aggregate candidates across ALL bias queries (vs. taking the
    # first non-empty result set). Pexels' first hit for "blouse flat
    # lay full item" tends to be a portrait; the second query might
    # surface a cleaner product shot. Pooling lets the alt-text scorer
    # pick the best of the combined pool.
    item_for_scoring = {"type": item_type, "color": item_color,
                         "name": ""}
    pooled: list = []
    seen_ids: set = set()
    queries_tried: list = []
    for bias in biases:
        q = f"{query} {bias}".strip() if bias else query
        queries_tried.append(q)
        photos = _pexels_search(q, key, _CANDIDATES_PER_SEARCH, timeout)
        for p in photos:
            pid = p.get("id")
            if pid not in seen_ids:
                pooled.append(p)
                seen_ids.add(pid)
        # Stop early once we have plenty of candidates.
        if len(pooled) >= 40:
            break
    if not pooled:
        return b"", "", ""

    # Rank by combined aspect-ratio + alt-text scoring.
    pooled.sort(key=lambda p: _score_candidate(p, item_type,
                                                 item_for_scoring))

    # Walk candidates in score order; take the first one that
    #   (a) passes the confidence threshold, AND
    #   (b) hasn't been claimed by another item this load.
    # If no candidate satisfies both, fall back to silhouette.
    best = None
    best_score = 99.0
    for cand in pooled:
        score = _score_candidate(cand, item_type, item_for_scoring)
        if score > _CONFIDENCE_THRESHOLD:
            # All remaining candidates score worse (sorted) — stop.
            break
        pid = cand.get("id")
        if pid is None or not _claim_photo_id(pid):
            continue
        best = cand
        best_score = score
        break
    if best is None:
        return b"", "", ""

    src = best.get("src") or {}
    img_url = src.get("large") or src.get("medium") or src.get("original")
    if not img_url:
        return b"", "", ""

    try:
        req = urllib.request.Request(img_url, headers={
            "User-Agent": _FETCH_UA,
            "Accept":     "image/jpeg, image/png, image/webp",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(4 * 1024 * 1024)
    except Exception:
        return b"", "", ""

    photographer = (best.get("photographer") or "").strip()
    photo_url    = (best.get("url") or "").strip()
    return raw, photographer, photo_url


# Back-compat alias — old callers / tests might still import the
# Unsplash name; map it to the new working implementation. Drops the
# attribution tuple for the legacy bytes-only signature.
def _fetch_unsplash_photo(query: str, w: int = 400, h: int = 500,
                          timeout: float = _FETCH_TIMEOUT) -> bytes:
    return _fetch_real_photo(query, w, h, timeout)[0]


def _resize_for_card(
    raw_bytes: bytes,
    size: tuple = _DEFAULT_CARD_SIZE,
) -> bytes:
    """
    Re-encode an arbitrary photo to a 400×500 PNG with object-fit:
    cover semantics. Returns empty bytes on failure.

    Pillow loads any JPEG/PNG/WEBP Unsplash returns, we center-crop
    to the card aspect ratio, then resize. Consistent output size
    keeps the wardrobe-list thumbnail grid tidy.
    """
    if not raw_bytes:
        return b""
    try:
        from PIL import Image
    except ImportError:
        return b""

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()
        # Convert to RGB so PNGs with alpha or palette-mode images
        # serialize cleanly downstream.
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        if img.mode == "RGBA":
            # Composite alpha onto white so the card background is
            # uniform (matching the rest of Wearly's white-on-white).
            from PIL import Image as _I
            bg = _I.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg

        target_w, target_h = size
        target_ratio = target_w / target_h
        src_w, src_h = img.size
        src_ratio = src_w / src_h

        # Decision: cover (center-crop) vs. contain (letterbox with
        # white padding). When the source aspect is close to the card
        # aspect, cover gives a tight tile and crops only a few pixels.
        # When the source is much taller or much wider (e.g. a full-
        # length dress photographed at 0.5 aspect vs. the card at 0.8),
        # cover would cut off the garment's head or feet — so we
        # letterbox instead, preserving the entire item.
        deviation = abs(src_ratio - target_ratio) / target_ratio
        from PIL import Image as _I
        if deviation <= _RESIZE_COVER_TOLERANCE:
            # COVER — center-crop to target aspect, then resize.
            if src_ratio > target_ratio:
                new_w = int(src_h * target_ratio)
                left = (src_w - new_w) // 2
                img = img.crop((left, 0, left + new_w, src_h))
            elif src_ratio < target_ratio:
                new_h = int(src_w / target_ratio)
                top = (src_h - new_h) // 2
                img = img.crop((0, top, src_w, top + new_h))
            img = img.resize((target_w, target_h), Image.LANCZOS)
        else:
            # CONTAIN — fit inside the card, pad sides with white. The
            # full garment is preserved.
            scale = min(target_w / src_w, target_h / src_h)
            new_w = max(1, int(src_w * scale))
            new_h = max(1, int(src_h * scale))
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            canvas = _I.new("RGB", (target_w, target_h), (255, 255, 255))
            ox = (target_w - new_w) // 2
            oy = (target_h - new_h) // 2
            canvas.paste(resized, (ox, oy))
            img = canvas

        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return b""


# ── Card image generator ──────────────────────────────────

def _generate_card_image(
    item: Dict[str, Any],
    size: tuple = _DEFAULT_CARD_SIZE,
) -> bytes:
    """
    Render a polished demo-wardrobe card. Returns PNG bytes.

    Layout (400 x 500 default):
      ┌──────────────────────────────────────────┐
      │ [TYPE pill]                              │   top
      │                                          │
      │         CLOTHING SILHOUETTE              │   body (recognizable
      │         drawn in a darker / lighter      │           shape per
      │         shade of the item's own color    │           category)
      │                                          │
      │  ────────────────────────────────────── │
      │  Item Name                       Store   │   footer (overlay band)
      │  COLOR                                   │
      └──────────────────────────────────────────┘

    The silhouette is the focal element — that's what the user
    scans the wardrobe for. Name + store sit at the bottom in a
    tinted overlay band so they don't compete with the shape.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return b""

    w, h = size
    bg_hex = _hex_for(item.get("color", ""))
    bg_rgb = _hex_to_rgb(bg_hex)
    accent = _silhouette_color(bg_rgb)
    lum = _luminance(bg_rgb)
    fg = (28, 25, 23) if lum > 0.55 else (244, 239, 232)

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Subtle inner border so cards read as cards on a white site bg.
    draw.rectangle([(0, 0), (w - 1, h - 1)],
                   outline=_shade(bg_rgb, -25 if lum > 0.5 else +30),
                   width=2)

    # ── Top: category pill ─────────────────────────────
    category_label = (item.get("type") or "").upper() or "ITEM"
    try:
        badge_font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        badge_font = ImageFont.load_default()
    pad_x, pad_y = 12, 6
    bbox = draw.textbbox((0, 0), category_label, font=badge_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pill_w = tw + pad_x * 2
    pill_h = th + pad_y * 2
    pill_x = 18
    pill_y = 18
    pill_bg = (244, 239, 232) if lum < 0.55 else (28, 25, 23)
    pill_fg = (28, 25, 23) if lum < 0.55 else (244, 239, 232)
    try:
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            radius=99, fill=pill_bg,
        )
    except AttributeError:
        draw.rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            fill=pill_bg,
        )
    draw.text((pill_x + pad_x, pill_y + pad_y), category_label,
              font=badge_font, fill=pill_fg)

    # ── Body: silhouette fills 80% of the canvas ──────
    # Earlier draft kept a footer band with the name + store + color,
    # but at 48-80px thumbnail size that text is unreadable noise and
    # the silhouette was too small to recognize. The wardrobe row
    # ALREADY shows the name and the color dot next to the image, so
    # we drop the in-card text entirely and let the silhouette fill
    # the available space.
    body_cy = int(h * 0.52)
    body_rx = int(w * 0.42)
    body_ry = int(h * 0.40)
    item_type = (item.get("type") or "").lower()
    name_lower = (item.get("name") or "").lower()
    drawer = _DRAW_BY_TYPE.get(item_type, _draw_top)
    try:
        drawer(draw, name_lower, w // 2, body_cy, body_rx, body_ry,
               _shade(bg_rgb, -12 if lum > 0.5 else +22),    # silhouette fill
               accent)                                        # silhouette outline
    except Exception:
        pass

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _read_local_override(rel_or_abs: str) -> bytes:
    """Read a local image override file. Returns its raw bytes, or
    empty bytes if the path is missing / unreadable. Accepts paths
    relative to the repo root or absolute paths."""
    if not rel_or_abs:
        return b""
    p = rel_or_abs
    if not os.path.isabs(p):
        p = os.path.join(_repo_root(), p)
    if not os.path.exists(p):
        return b""
    try:
        with open(p, "rb") as f:
            return f.read(8 * 1024 * 1024)
    except OSError:
        return b""


def _fetch_override_url(url: str, timeout: float = _FETCH_TIMEOUT) -> bytes:
    """Fetch raw bytes from an arbitrary HTTPS URL set by the demo
    JSON's `image_url_override`. NEVER raises — empty bytes on any
    failure."""
    if not url:
        return b""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": _FETCH_UA,
            "Accept":     "image/jpeg, image/png, image/webp",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(8 * 1024 * 1024)
    except Exception:
        return b""


def _fetch_from_retailer_link(
    page_url: str, timeout: float = _FETCH_TIMEOUT,
) -> Tuple[bytes, str]:
    """
    Resolve a retailer product page URL to its product image bytes,
    reusing the existing link_import pipeline (the same code that
    powers the Wardrobe → Link tab the user adds items through).

    Returns (image_bytes, source_page_url). Empty bytes on any failure
    (no link_import module, page fetch failed, no og:image, image
    download failed, decode error). NEVER raises — the loader falls
    through to Pexels / silhouette.

    The product image is sourced in priority order:
      1. JSON-LD `image` (Schema.org Product) — usually higher quality.
      2. `og:image` meta tag.
    """
    if not page_url:
        return b"", ""
    try:
        from link_import import import_product_link
    except Exception:
        return b"", ""
    try:
        meta = import_product_link(page_url, fetch_metadata=True)
    except Exception:
        return b"", ""
    if not meta or not meta.get("fetched"):
        return b"", page_url

    # Prefer JSON-LD product image; fall back to og:image.
    md = meta.get("metadata") or {}
    jsonld = md.get("jsonld_product") or {}
    img_url = ""
    j_img = jsonld.get("image")
    if isinstance(j_img, list) and j_img:
        img_url = j_img[0]
    elif isinstance(j_img, str):
        img_url = j_img
    if not img_url:
        img_url = (md.get("og_image") or meta.get("source_image_url") or "")
    if not img_url:
        return b"", page_url

    raw = _fetch_override_url(img_url, timeout=timeout)
    return raw, page_url


def _save_card(item: Dict[str, Any], use_photos: bool = True
               ) -> Tuple[str, str, str, str]:
    """
    Save a card image for a demo item. Returns
    ``(relative_path, source, photographer, photo_url)`` where:
      - source ∈ {"photo", "override", "silhouette", ""}
      - photographer / photo_url are populated only when source=="photo"
        so the UI can render "Photo: <Name> · Pexels" attribution.
        Manual overrides carry no attribution (the operator who set
        them is responsible for the image's licensing).

    Resolution order:
      1. `local_image_path_override`  → read a file from disk.
      2. `image_url_override`         → HTTP GET an explicit URL.
      3. `source_link`                → fetch retailer product page,
                                         extract og:image / JSON-LD
                                         image via the same code path
                                         as the user-facing Link tab.
      4. Pexels search                → biased product-photo query.
      5. Drawn silhouette             → final fallback.

    Why source_link is preferred over Pexels: Pexels is a stock-photo
    library, not a product catalog. Even the best-scored Pexels
    candidate for a "burgundy wrap blouse" is going to be a lifestyle
    shot, not the kind of clean catalog tile a real retailer's
    product page carries. The link-import path was already added for
    user-uploaded items via the Wardrobe Link tab; this just wires it
    into the demo seed too.
    """
    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)
    item_id = item.get("id", "")
    if not item_id:
        return "", "", "", ""

    png_bytes = b""
    source = ""
    photographer = ""
    photo_url = ""

    # 1. Local file override — operator-supplied image on disk.
    local_override = item.get("local_image_path_override")
    if local_override:
        raw = _read_local_override(local_override)
        if raw:
            png_bytes = _resize_for_card(raw, _DEFAULT_CARD_SIZE)
            if png_bytes:
                source = "override"

    # 2. URL override — operator-supplied direct image URL.
    if not png_bytes and item.get("image_url_override"):
        raw = _fetch_override_url(item["image_url_override"])
        if raw:
            png_bytes = _resize_for_card(raw, _DEFAULT_CARD_SIZE)
            if png_bytes:
                source = "override"

    # 3. Retailer product link — re-uses the exact pipeline the user
    #    sees in the Wardrobe Link tab, so demo items get the same
    #    high-quality catalog imagery as manually-added ones.
    if not png_bytes and item.get("source_link"):
        raw, retailer_url = _fetch_from_retailer_link(item["source_link"])
        if raw:
            png_bytes = _resize_for_card(raw, _DEFAULT_CARD_SIZE)
            if png_bytes:
                source = "retailer"
                # Reuse the photo_url field to carry the source page
                # so the UI can credit the store.
                photo_url = retailer_url

    # 4. Pexels — `unsplash_query` is the legacy field name; the
    #    keywords drive whichever real-photo source we use.
    if not png_bytes and use_photos and item.get("unsplash_query"):
        raw, photographer, photo_url = _fetch_real_photo(
            item["unsplash_query"],
            item_type=item.get("type", ""),
            item_color=item.get("color", ""),
        )
        if raw:
            png_bytes = _resize_for_card(raw, _DEFAULT_CARD_SIZE)
            if png_bytes:
                source = "photo"

    if not png_bytes:
        png_bytes = _generate_card_image(item)
        if png_bytes:
            source = "silhouette"
            photographer = ""
            photo_url = ""

    if not png_bytes:
        return "", "", "", ""

    out_path = os.path.join(WARDROBE_IMAGES_DIR, f"{item_id}.png")
    try:
        with open(out_path, "wb") as f:
            f.write(png_bytes)
    except OSError:
        return "", "", "", ""
    return f"wardrobe_images/{item_id}.png", source, photographer, photo_url


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


def load_demo_wardrobe(
    regenerate_images: bool = True,
    use_photos: bool = True,
) -> dict:
    """
    Merge every item from `demo_wardrobe.json` into user_wardrobe.json.

    Returns::

        {
          "added":          [item_id, ...],     # newly inserted
          "skipped":        [item_id, ...],     # already in overlay (record kept as-is)
          "refreshed":      [item_id, ...],     # already present BUT card image re-rendered
          "photos":         int,                # of refreshed/added, how many got a real photo
          "silhouettes":    int,                # of refreshed/added, how many fell back to silhouette
          "total_after":    int,
          "image_errors":   [item_id, ...],     # save failed entirely
          "error":          str | None,
        }

    When `use_photos=True` (default) the loader fetches a real
    photo from Unsplash for each item that has an `unsplash_query`
    field. Fetches run in parallel (six concurrent connections) so
    the full 48-item load completes in ~10-15 s on a normal
    connection. Items whose fetch fails fall back to the silhouette
    renderer — the demo still loads, just with a mix of photos and
    illustrations.

    User-added items (UC### / US### / UA###) are NEVER touched.
    """
    # Reset the photo-id dedup set so each load starts fresh. Without
    # this, a second load in the same Python process could see all
    # photos as "already taken" and silhouette every item.
    _reset_used_photo_ids()

    try:
        seed = _load_demo_seed()
    except Exception as e:
        return {"added": [], "skipped": [], "refreshed": [],
                "photos": 0, "silhouettes": 0,
                "total_after": 0, "image_errors": [],
                "error": f"Could not read demo seed: {e}"}

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

    added:     List[str] = []
    skipped:   List[str] = []
    refreshed: List[str] = []
    img_err:   List[str] = []
    photo_count = 0
    silhouette_count = 0

    all_seed_items = (
        list(seed.get("clothing", []))
        + list(seed.get("shoes", []))
        + list(seed.get("accessories", []))
    )

    # Decide up front which items need an image render. Then do the
    # actual render work in parallel — 48 sequential Unsplash fetches
    # would block the UI for 30 s+, but ~6 concurrent connections
    # bring it under 15 s.
    items_to_render: List[dict] = []
    new_items: List[dict] = []
    for item in all_seed_items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        iid = item["id"]
        if iid in existing_ids:
            if regenerate_images:
                items_to_render.append(item)
        else:
            items_to_render.append(item)
            new_items.append(item)

    render_results: Dict[str, Tuple[str, str, str, str]] = {}
    if items_to_render:
        with ThreadPoolExecutor(max_workers=_PARALLEL_FETCH) as pool:
            futures = {
                pool.submit(_save_card, it, use_photos): it.get("id")
                for it in items_to_render
            }
            for fut in as_completed(futures):
                iid = futures[fut]
                try:
                    render_results[iid] = fut.result()
                except Exception:
                    render_results[iid] = ("", "", "", "")

    # Now apply the results in the original (deterministic) order.
    for item in all_seed_items:
        if not isinstance(item, dict):
            continue
        iid = item.get("id", "")
        if not iid:
            continue

        # Refresh path (item already in user overlay).
        if iid in existing_ids:
            skipped.append(iid)
            if regenerate_images:
                new_path, source, photographer, photo_url = \
                    render_results.get(iid, ("", "", "", ""))
                if new_path:
                    refreshed.append(iid)
                    if source in ("photo", "retailer", "override"):
                        photo_count += 1
                    elif source == "silhouette":
                        silhouette_count += 1
                    # Update attribution on the existing record.
                    for sec in ("clothing", "shoes", "accessories"):
                        for rec in overlay.get(sec, []):
                            if isinstance(rec, dict) and rec.get("id") == iid:
                                if source == "photo" and photographer:
                                    rec["photo_credit_name"]   = photographer
                                    rec["photo_credit_url"]    = photo_url
                                    rec["photo_credit_source"] = "Pexels"
                                else:
                                    rec.pop("photo_credit_name", None)
                                    rec.pop("photo_credit_url", None)
                                    rec.pop("photo_credit_source", None)
                                break
                else:
                    img_err.append(iid)
            continue

        # New-item path.
        image_path, source, photographer, photo_url = \
            render_results.get(iid, ("", "", "", ""))
        if not image_path:
            img_err.append(iid)
        else:
            if source == "photo":
                photo_count += 1
            elif source == "silhouette":
                silhouette_count += 1

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
            return {"added": [], "skipped": skipped, "refreshed": refreshed,
                    "photos": photo_count, "silhouettes": silhouette_count,
                    "total_after": 0, "image_errors": img_err,
                    "error": f"Save failed: {e}"}

    total_after = sum(len(overlay.get(s, [])) for s in
                      ("clothing", "shoes", "accessories"))

    # ── Review report ──────────────────────────────────────────
    # Write a CSV under wardrobe_images/_pexels_review.csv listing
    # the source decision per item. Useful both for the demo operator
    # (spot bad images quickly) and as a regression catch (compare
    # before / after a Pexels-pipeline tweak).
    report_path = ""
    try:
        report_path = _write_review_report(all_seed_items, render_results)
    except Exception:
        pass

    return {
        "added":         added,
        "skipped":       skipped,
        "refreshed":     refreshed,
        "photos":        photo_count,
        "silhouettes":   silhouette_count,
        "total_after":   total_after,
        "image_errors":  img_err,
        "review_report": report_path,
        "error":         None,
    }


def _write_review_report(all_seed_items: list,
                          render_results: dict) -> str:
    """Write a CSV review report listing the source decision per item.

    Columns:
      id, name, type, color, query_base, picked_source, image_path,
      photographer, photo_url, reason

    Returned path is relative to repo root. Empty string on failure.
    """
    import csv
    os.makedirs(WARDROBE_IMAGES_DIR, exist_ok=True)
    path = os.path.join(WARDROBE_IMAGES_DIR, "_pexels_review.csv")
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "name", "type", "color", "query_base",
                "picked_source", "image_path", "photographer",
                "photo_url", "reason",
            ])
            for it in all_seed_items:
                if not isinstance(it, dict):
                    continue
                iid = it.get("id", "")
                rec = render_results.get(iid, ("", "", "", ""))
                ipath, source, photog, photo_url = rec
                reason = {
                    "retailer":   "retailer product page (source_link "
                                   "via link_import)",
                    "photo":      "Pexels accepted (passed alt-text checks)",
                    "silhouette": "fell back — no source_link, Pexels "
                                   "candidates failed alt-text checks, "
                                   "OR network",
                    "override":   "manual override (image_url_override "
                                   "or local_image_path_override)",
                    "":           "render failed",
                }.get(source, source)
                writer.writerow([
                    iid,
                    it.get("name", ""),
                    it.get("type", ""),
                    it.get("color", ""),
                    it.get("unsplash_query", ""),
                    source or "render-failed",
                    ipath,
                    photog,
                    photo_url,
                    reason,
                ])
        return os.path.relpath(path, _repo_root())
    except OSError:
        return ""


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
