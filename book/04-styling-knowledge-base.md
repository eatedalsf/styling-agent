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

## Where to verify

- The maps: `styling_agent.py` (`OCCASION_TAG_MAP`, `REQUIRED_PIECES`).
- The palettes: `color_rules.json`.
- The skin-tone scoring: `color_tool.py` · `score_outfit_colors()`.
