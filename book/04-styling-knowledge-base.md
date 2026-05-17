# 04 · Styling knowledge base

*The app applies these rules at runtime; this chapter is the reference layer that explains each rule pack and the data it reads.*

> **Entry point to Part II.** This chapter is the structural map of
> what Wearly knows. Each rule system below is taught in its own Part-II
> chapter, learner-first, with the evidence behind it:
>
> - Color → [§S1 · Color and skin tone](S1-color-and-skin-tone.md)
> - Silhouette / fit → [§S2 · Silhouette and fit](S2-silhouette-and-fit.md)
> - Occasion → [§S3 · Occasion and context](S3-occasion-and-context.md)
> - Weather / layering → [§S4 · Weather and layering](S4-weather-and-layering.md)
> - Construction → [§S5 · Wardrobe construction](S5-wardrobe-construction.md)
> - Rotation → [§S6 · Rotation and freshness](S6-rotation-and-freshness.md)
> - Gaps → [§S7 · Honest gaps](S7-honest-gaps.md)
> - Body-positive framing → [§S8 · Body-positive framing as a discipline](S8-body-positive-framing.md)

Every Wearly decision traces to an **inspectable knowledge base** — three rule systems, eight rule packs, and a citation registry. This chapter documents what's in it and why.

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

The scoring formula is **intentionally transparent** — base 60, +8 for `best`, +4 for `good`, −10 for `avoid`, clamped to 0–100. Every contribution is visible in the reasoning trail; a reviewer can verify each item's score by inspection — a property a deep-learned color model would not have.

## Why the reasoning core is inspectable rules

The course principle "structure beats volume" applies directly. A learned compatibility model would:

- need large labeled datasets to train,
- be opaque ("the network said so"),
- be impossible to trace from a reasoning line back to a citable rule,
- prevent the body-positive language contract from being enforced at the prose layer.

A structured rule system, by contrast:

- is fully visible across eight rule packs, the citation registry (`rule_refs.py`), and the [Wearly Knowledge Graph](../docs/sims/wearly-knowledge-graph/index.md) — every decision traces to a named rule,
- can be edited at runtime — rule changes take effect on the next recommendation, with the new reasoning trail showing exactly what changed,
- supports an audit trail without extra plumbing,
- is the **strongest foundation for adding learned layers later** — the rule outputs become labeled training data for any future model, and the safety + scoring substrate stays in place underneath.

## Next rule layers on the roadmap

- **Body shape → silhouette** (Phase 3, fit profile).
- **Modesty preferences** (Phase 3).
- **Comfort and fabric** (Phase 4).
- **Wear history** (Phase 4 — a piece of this is shipped today).
- **Cross-item color harmony** (currently per-item only).
- **Brand affinity / aesthetic clusters** (Phase 5).

Each is a future rule layer, not a future ML feature. The structure stays inspectable as it grows.

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
2. *(Understand)* Why is Wearly's reasoning core structured as inspectable rules, and what does that enable that a learned model could not?
3. *(Apply)* Look up `occasion-rules.md` R2 in the skill pack. Which rule heading does it resolve to, and which chapter cites it?

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze).*
