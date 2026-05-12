# Color harmony score (micro-sim)

> **What you're looking at.** A live, p5.js-rendered toy of Wearly's Step 7 color-coordination rule. Pick a skin tone, pick an outfit, watch the score change. The same formula runs at runtime in `color_tool.score_outfit_colors()`.
>
> **Why it exists.** A static rule description (*+8 for best, +4 for good, −10 for avoid, base 60, clamped 0–100*) is easy to skim and easy to misremember. A micro-sim lets you *feel* the rule — try a deep-warm wearer in muted beige and watch the score crater; swap to cobalt and watch it climb. Pattern adopted from [dmccreary/intelligent-textbooks](https://github.com/dmccreary/intelligent-textbooks).

<iframe
  src="main.html"
  width="100%"
  height="900"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Color Harmony micro-sim">
</iframe>

---

## How to use it

| Control | What it does |
|---|---|
| **Skin tone** | Switches the active palette (warm olive / cool fair / deep warm). The "best palette" swatch row at the bottom of the canvas updates to match. |
| **Top / Bottom / Shoes / Accessory** | Pick a color for each garment slot. The silhouette and the score recompute instantly. |
| **Randomize outfit** | Picks one color per slot at random — useful for stress-testing the rule. |
| **Score gauge** | Arc fills proportional to the 0–100 score. Color shifts: red below 60, terracotta 60–79, green 80+. |
| **Notes panel** | Per-item contribution (+8 / +4 / 0 / −10) plus the palette's plain-English styling note. |

## The rule, written out

```
score = 60                              # base, every outfit starts neutral
for each item in outfit:
    if item.color in palette.best:    score += 8
    elif item.color in palette.good:  score += 4
    elif item.color in palette.avoid: score -= 10
    # else: no change

score = clamp(score, 0, 100)
```

That's it. Three lookups, one clamp. The data behind the lookup lives in [`color_rules.json`](https://github.com/eatedalsf/styling-agent/blob/main/color_rules.json); the per-color hex used by the sim mirrors the `COLOR_HEX` table in `app.py`.

## What the sim is NOT modeling

- **Color contrast theory** (analogous, complementary, triadic) — Wearly's prototype intentionally skips harmony-theory scoring; it only checks skin-tone fit.
- **Material / texture interactions** — the rule operates on color names, not garment materials.
- **Outfit gestalt** — the score is additive per item; there is no penalty for combining two best-palette colors that happen to clash with each other.

These are deliberate scope choices; see [`book/04-styling-knowledge-base.md`](../../../book/04-styling-knowledge-base.md) for the reasoning.

## See also

- **[`book/04-styling-knowledge-base.md`](../../../book/04-styling-knowledge-base.md)** — the underlying styling knowledge model.
- **[`skills/wearly-styling-agent/color-coordination-rules.md`](../../../skills/wearly-styling-agent/color-coordination-rules.md)** — the canonical rule pack with edge cases.
- **[`docs/evidence-and-references.md`](../../../docs/evidence-and-references.md)** — sources informing the palette-to-skin-tone mapping.
- **[Learning Graph](../learning-graph/index.md)**, **[Knowledge Graph](../knowledge-graph/index.md)** — the two interactive graphs that round out the Intelligent Book's interactive layer.
