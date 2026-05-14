# 04 · Styling knowledge base

Wearly's decisions aren't learned from photos — they're driven by a small, **inspectable knowledge base**. This chapter documents what's in it and why.

## Three rule systems

### 1. Occasion → tag map

In `styling_agent.py`:

```
OCCASION_TAG_MAP = {
  "work", "business", "meeting" → "work",
  "gym", "workout", "yoga", "running" → "gym",
  "dinner", "restaurant", "date" → "dinner",
  "formal_event", "gala", "formal" → "formal",
  "casual", "weekend", "brunch", "everyday" → "casual",
}
```

A free-text occasion like *"client dinner"* is matched against this map. The agent always lands on one of five canonical tags. This means the wardrobe filtering, the dress-vs-separates decision, and the required-pieces set are all driven by a small, well-known vocabulary.

### 2. Required pieces per occasion

```
REQUIRED_PIECES = {
  "work":    ["top", "bottom"],
  "dinner":  ["top", "bottom"],   # unless a dress is preferred
  "gym":     ["activewear", "activewear"],
  "formal":  ["dress"],
  "casual":  ["top", "bottom"],
}
```

Step 6 (gap check) compares the built outfit against this list. A missing required piece becomes a wardrobe gap.

### 3. Color rules per skin tone

`color_rules.json` defines `best_colors`, `good_colors`, `avoid_colors`, `metal_preference`, and a `notes` line for each of three skin tones today:

- `warm olive` — terracotta, camel, burgundy, deep teal, mustard, gold
- `cool fair` — navy, icy blue, lavender, silver, emerald, raspberry
- `deep warm` — cobalt, emerald, bright red, gold, orange, purple

The scoring formula is deliberately simple — base 60, +8 for `best`, +4 for `good`, −10 for `avoid`, clamped to 0–100. **It is more important that the score be readable than that it be sophisticated.** A reviewer can verify each item's contribution by inspecting the reasoning trail; a deep-learned color model would be neither explainable nor inspectable.

## Why rules, not ML

The course principle "structure beats volume" applies directly. A trained model would:

- be expensive to label,
- be opaque ("the network said so"),
- be impossible to debug from a reasoning trail,
- not survive scrutiny in a 10-minute demo.

A small rule system, by contrast:

- is fully visible in three JSON files and one Python module,
- can be edited live during a demo to show the system adapting,
- supports an audit trail without extra plumbing,
- is the most defensible foundation for *adding* ML later (the rule outputs are training targets).

## What the rules deliberately don't model (yet)

- **Body shape → silhouette** (Phase 3, fit profile).
- **Modesty preferences** (Phase 3).
- **Comfort and fabric** (Phase 4).
- **Wear history** (Phase 4 — a small piece of this lands in this session).
- **Cross-item color harmony** (currently per-item only).
- **Brand affinity / aesthetic clusters** (Phase 5).

Each of these is a future rule layer, not a future ML feature. The system's structure stays inspectable as it grows.

## What informs these rules

Each rule system is **evidence-informed, design-informed, and user-preference-driven** — not claimed to be exact or objectively correct. The canonical sourcing lives in [`docs/evidence-and-references.md`](../docs/evidence-and-references.md). Quick map:

| Rule system | Primary evidence category | Current basis |
|---|---|---|
| Occasion → tag map | Outfit compatibility (§3.2) | Industry styling heuristics — five canonical occasion types are widely recognized in fashion-product UX. |
| Required-pieces map | Outfit compatibility (§3.2) | Industry styling heuristics. |
| Color palettes | Color harmony (§3.3) | Design-informed conventions (warm / cool color-theory). The "Best for warm olive" claim is *"these tend to read well under warm/cool conventions"* — not an empirical claim. |
| Color scoring formula (+8 / +4 / −10) | Color harmony (§3.3) | UX choice for readability — not derived from a specific empirical model. |

The honesty contract from chapter 12: Wearly says *"tends to work well,"* not *"is correct."*

## Where to verify

- The maps: `styling_agent.py` (`OCCASION_TAG_MAP`, `REQUIRED_PIECES`).
- The palettes: `color_rules.json`.
- The skin-tone scoring: `color_tool.py` · `score_outfit_colors()`.
- The canonical sourcing: `docs/evidence-and-references.md`.

---

## Key terms

- **Required pieces** — the minimum type-set an occasion needs (e.g., work = top + bottom) ([glossary](../docs/glossary.md)).
- **Color tier** — the +8 / +4 / −10 scoring scale for color against skin-tone palette ([glossary](../docs/glossary.md)).
- **Skin-tone palette** — one of three named palettes the color formula reads from ([glossary](../docs/glossary.md)).
- **Rule citation (R<N>)** — a numbered heading inside a Skill rule file ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* Name the three skin-tone palettes Wearly ships today.
2. *(Understand)* Why does Wearly use rules rather than a learned compatibility model in this prototype?
3. *(Apply)* Look up `occasion-rules.md` R2 in the skill pack. Which rule heading does it resolve to, and which chapter cites it?

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
