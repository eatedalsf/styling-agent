# Color harmony score (micro-sim)

> **Learning objective.** After working through this sim, you will be
> able to predict how a single color choice shifts the harmony score
> against a given skin-tone palette — and explain why Wearly uses a
> small additive rule rather than a learned model.
>
> **What you're looking at.** A live, p5.js-rendered view of Wearly's
> Step 7 color-coordination rule. Pick a skin tone, pick an outfit,
> watch the score change. The same formula runs at runtime in
> `color_tool.score_outfit_colors()`.
>
> **Why a sim, not just docs.** A static rule description
> (*+8 best, +4 good, −10 avoid, base 60, clamped 0–100*) is easy to
> skim past. Moving the swatches and watching the score respond turns
> the rule into something the reader has *handled*. Pattern adopted
> from [dmccreary/intelligent-textbooks](https://github.com/dmccreary/intelligent-textbooks).

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

---

## What to notice

- **The base of 60 is the neutral starting point.** With no items
  selected (or all items outside both *best* and *avoid*), the score
  sits at 60. Every choice nudges from there.
- **One avoid item costs more than one best item adds.** −10 vs. +8 is
  a deliberate asymmetry: the rule is conservative about clashes.
- **The palette swatch row redraws when the skin tone changes.** The
  bottom of the canvas reveals the best-palette colors for the
  currently-selected wearer — that's the actual data the score reads.

## Try this

1. **Default outfit + warm olive.** Note the starting score.
   **What you should see:** a score in the 60–80 range with a small
   per-item breakdown in the notes panel.
2. **Switch the wearer to *deep warm* without touching the outfit.**
   **What you should see:** the score shifts (often downward) because
   the same colors land in different palette tiers for a different
   skin tone — the formula is unchanged, the lookup table is not.
3. **Set every slot to an *avoid* color for the active palette.**
   **What you should see:** the score drops sharply but clamps at 0
   rather than going negative. The clamp is the floor in the rule.

## Self-check

1. *(Remember)* What are the three palette tiers and their numeric
   contributions?
2. *(Understand)* Why does the rule clamp the final score to 0–100
   rather than letting it go arbitrarily high or low?
3. *(Apply)* Given a cool-fair wearer in `cobalt + cream + navy`,
   predict whether the score lands above or below 80, and justify your
   answer in one sentence.

## Linked concept

- *Styling-rule reference chapter:* **[§S1 · Color and skin tone](../../../book/S1-color-and-skin-tone.md)** — the styling knowledge this sim makes touchable.
- *Learning-graph concept:* **[color harmony rules](../learning-graph/index.md)** (id `color-harmony`, Bloom level *Apply*).
- *Rule citations:* `[color-coordination-rules#R1]`, `[color-coordination-rules#R2]` — see [`color-coordination-rules.md`](../../../skills/wearly-styling-agent/color-coordination-rules.md).

---

## See also

- **[`book/04-styling-knowledge-base.md`](../../../book/04-styling-knowledge-base.md)** — the underlying styling knowledge model.
- **[`skills/wearly-styling-agent/color-coordination-rules.md`](../../../skills/wearly-styling-agent/color-coordination-rules.md)** — the canonical rule pack with edge cases.
- **[`docs/evidence-and-references.md`](../../../docs/evidence-and-references.md)** — sources informing the palette-to-skin-tone mapping.
- **[Learning Graph](../learning-graph/index.md)**, **[Knowledge Graph](../knowledge-graph/index.md)** — the two interactive graphs that round out the Intelligent Book's interactive layer.
