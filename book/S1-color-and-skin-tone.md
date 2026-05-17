# S1 · Color and skin tone

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains the color framework Wearly applies at Step 7.*

## The concept

Wearly's color logic rests on the **warm / cool axis** — the design-school
convention that classifies skin undertones and garment colors along the
same warm-to-cool dimension and then asks how well a color sits with the
wearer. The convention is centuries old; Wearly's implementation is the
rule layer that operationalizes the convention against an actual wardrobe.

Three named palettes ship today:

- **warm olive** — yellow / golden undertone with green influence.
- **cool fair** — pink / blue undertone with low contrast.
- **deep warm** — rich brown / golden undertone with high contrast.

Each palette declares three tiers — *best*, *good*, *avoid* — and the
agent scores an outfit against the wearer's palette:

```
score = 60                                  # neutral base
for each item:
    if item.color in palette.best:    score += 8
    elif item.color in palette.good:  score += 4
    elif item.color in palette.avoid: score −= 10
score = clamp(score, 0, 100)
```

Three lookups, one clamp — every term visible in the reasoning trail.
The +8 / +4 / −10 asymmetry is a deliberate UX choice: a clash should
cost more than a match adds, so the score is conservative.

## Where this knowledge comes from

Color theory is not a science of "correct" palettes, but it does have a
recognized vocabulary and a measured foundation:

- The **warm / cool framework** descends from Itten's *Elements of Color* —
  the formal vocabulary of color contrasts (hue, light/dark, cold/warm,
  complementary, simultaneous, saturation, extension) that design-school
  color teaching builds on. ⟶ [References [4]](../docs/references.md)
- The **measured-color foundation** under named palettes goes back to
  Munsell (1905), who formalized hue × value × chroma as a system a
  century before today's named palettes. ⟶ [References [5]](../docs/references.md)
- The **modern perceptual standard** is the CIELAB color space (ISO
  11664-4:2008). Wearly does *not* compute ΔE distances at runtime; the
  citation acknowledges the framework Wearly's named palette sits above.
  ⟶ [References [6]](../docs/references.md)

What Wearly deliberately does **not** claim:

- That its palettes are empirically optimal for any wearer. They're
  design-informed conventions, not findings from a randomized study.
- That seasonal-color analysis ("Color Me Beautiful" and similar
  industry frameworks) is science. The framework is widely referenced
  but not peer-reviewed; Wearly cites it as industry practice, never
  as evidence.

## Why named colors instead of CIELAB

Three reasons, in order of importance:

1. **The rule has to be auditable.** A reasoning line that reads
   *"forest green pairs well with deep-warm undertones"* is a sentence
   a non-expert user can argue with. *"ΔE 12.4 against L\* 43.2"* is
   not.
2. **The data is small.** Three palettes × roughly 30 named colors
   each fits in `color_rules.json` and is editable by a non-engineer.
3. **The honesty contract demands it.** "Tends to work well" is a
   calibrated claim; a numeric distance suggests precision Wearly does
   not have.

The trade-off: Wearly cannot reason about colors it doesn't have a
name for, and it cannot compute contrast between two named colors in
the same outfit. Both are deliberate scope choices — see [Chapter
04](04-styling-knowledge-base.md) for the *"why rules, not ML"*
discussion.

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md) — R1 (palettes), R2 (scoring), R5 (unknown skin tone) |
| **Runtime code** | `color_tool.score_outfit_colors()` |
| **Agent step** | Step 7 of the seven-step workflow |
| **Where it surfaces** | The color-score panel + the per-item +8 / +4 / −10 note in the reasoning trail |
| **Part I chapter** | [Chapter 04 · Styling knowledge base](04-styling-knowledge-base.md) |
| **MicroSim** | [Color harmony](../docs/sims/color-harmony/index.md) — try the formula on every combination |

---

## Key terms

- **Skin-tone palette** — one of three named palettes (warm olive, cool fair, deep warm). See [Glossary](../docs/glossary.md).
- **Color tier** — *best* (+8), *good* (+4), *avoid* (−10). See [Glossary](../docs/glossary.md).
- **Warm / cool axis** — the design-school dimension the three palettes pivot on.

## Self-check

1. *(Remember)* What are the three palette tiers and their numeric contributions?
2. *(Understand)* Why does Wearly use named colors instead of CIELAB distances at runtime?
3. *(Apply)* For a cool-fair wearer, predict whether `navy + cream + cobalt` lands above or below 80, and justify your answer in one sentence.

*Self-check follows Bloom's progression — same pattern as Part I chapters and MicroSim pages.*
