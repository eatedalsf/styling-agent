# Color coordination rules

Skin-tone palettes, scoring formula, per-item flag thresholds. Implemented in `color_rules.json` and `color_tool.score_outfit_colors()`.

## R1 — Skin-tone palettes

`color_rules.json` defines three skin tones today, each with three palette lists:

| Skin tone | Best colors | Good colors | Avoid colors |
|---|---|---|---|
| `warm olive` | terracotta, burnt orange, camel, olive, burgundy, warm white, gold, deep teal, mustard, chocolate brown | black, navy, blush, cream, sage green, rust | cool grey, icy pink, lavender, silver |
| `cool fair` | navy, icy blue, lavender, cool grey, silver, emerald, royal blue, raspberry | black, white, pink, plum, burgundy | orange, warm brown, gold-heavy palettes |
| `deep warm` | cobalt, emerald, bright red, gold, orange, white, camel, purple | black, navy, burgundy, teal | muted beige, dusty pink, light grey |

Each tone also declares a `metal_preference` (`gold` / `silver`) and a `notes` line that ships into the reasoning trail.

## R2 — Scoring formula

```
score = 60   # base

for each item in outfit:
    color = item.color (lowercased)
    if color matches any best_color:   score += 8
    elif color matches any good_color: score += 4
    elif color matches any avoid_color: score -= 10

score = clamp(0, 100)
```

## R3 — Match function

Match is **bidirectional substring**: `target in palette_color OR palette_color in target`.

This catches:
- `"warm white"` matches palette `"white"`.
- `"dark indigo"` matches palette `"navy"` indirectly via downstream rules (currently dark indigo just doesn't match — Phase 4 can refine).

The substring approach is permissive on purpose. Tight matching would underscore the system; loose matching surfaces in the reasoning trail.

## R4 — Per-item notes & flags

For every item, the agent appends to the reasoning trail one of:

- `"✓ {name} ({color}) — excellent color for your skin tone."` (best)
- `"✓ {name} ({color}) — works well for your skin tone."` (good)
- `"⚠ {name} ({color}) — this color is less flattering for your skin tone."` (avoid)

The avoid-line is the *only* place where Wearly says a color is *less* flattering. It never says "bad" or "wrong." The note is a guidance, not a verdict.

## R5 — Unknown skin tone fallback

If the user's skin tone isn't in `color_rules.json`, fall back to a universal palette: `["black", "navy", "white", "camel"]` as best, no good list, no avoid list. The reasoning trail explains the fallback.

## R6 — Score color (visual)

The Streamlit color card uses a **warm-palette-only** mapping for the score number:

| Score | Color |
|---|---|
| ≥ 80 | `#9F5A36` (deep terracotta) |
| 60–79 | `#C17F5A` (accent terracotta) |
| < 60 | `#8A4A20` (warm warning brown) |

No greens, no cool tones. The score-color system stays inside the brand palette.

## R7 — Cross-item color harmony (future)

The current scoring is **per-item only**. A future Phase 4 enhancement scores the outfit as a whole — checking that the items don't visually clash with each other. Hue clusters, neutral counts, and accent management would all factor in. The per-item score remains for transparency.
