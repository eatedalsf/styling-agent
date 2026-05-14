# 08 · Shopping-gap logic

*The app surfaces gaps when an occasion needs a piece you don't own; this chapter explains the gap-detection logic and its body-positive tone rules.*

When Wearly says *"you don't own this yet,"* that's a deliberate design decision, not a missing feature. This chapter explains the logic.

## When a gap is detected

Step 6 (`check_gaps`) runs after the outfit is built:

```python
required = REQUIRED_PIECES[occasion_tag]   # e.g. ["top","bottom"] for work
covered  = {item.type for item in outfit}
gaps     = [t for t in required if t not in covered]
```

Plus a second gap path: if the weather demands outerwear but no occasion-appropriate outerwear exists in the wardrobe, Step 5 adds `"outerwear"` to the gap list and skips the layer.

## What the user sees

When `gaps` is non-empty, the result card displays a calm terracotta-accented panel:

> **Wardrobe Gap · outerwear missing for this occasion**
>
> → *A lightweight athletic windbreaker or running jacket would cover cool-weather gym transit without breaking the activewear look.*

The shopping suggestion is **occasion-specific** — gym gets a windbreaker, work gets a tailored coat, dinner gets a chic midi dress. The mapping lives in `SHOPPING_SUGGESTIONS` in `styling_agent.py`.

## Why this design

### A gap is information, not an upsell

The user might genuinely not own a piece. Saying so is honest. Hiding the gap to pretend the outfit is complete would be dishonest *and* would leave the user underdressed.

Wearly does not push affiliate links. The suggestion text is descriptive ("A lightweight athletic windbreaker would …") so the user can act on it however they prefer — searching their preferred retailer, asking a friend, or filing it for later.

### The owned/suggested distinction is explicit

The product brief calls this out:

> Distinguish between owned items and suggested-to-buy items.

In the UI, owned items appear inside the outfit card with their actual color swatch. Suggested items appear inside the gap panel with the `→` arrow prefix and warmer panel coloring. A user never confuses one for the other.

### Production: favorite stores + wishlist

Phase 5 plan:

- `data/stores.json` — user's favorite stores, ordered by preference.
- `data/wishlist.json` — saved suggestions for later.
- `shopping_tool.suggest(gap, stores)` — instead of a static line, returns a list of {name, store, url, price_range} drawn from a curated mock catalog per store.
- Outfit screen → gap panel → store-prioritized cards → "Save to wishlist" action.

Live retailer scraping is out of scope. Per-store adapters with HTML/JSON-LD parsing would be the production path; affiliate-compliant catalogs would be the commercial path.

## Where to verify

- `styling_agent.py` → `REQUIRED_PIECES`, `SHOPPING_SUGGESTIONS`, Step 6.
- `wardrobe_tool.py` → `check_gaps()`.
- The Streamlit screen: tap **Everyday Occasion → Gym** in the sidebar → outerwear gap appears at the bottom of the outfit screen.

---

## Key terms

- **Gap** — a required piece type the user does not own for the current occasion ([glossary](../docs/glossary.md)).
- **Qualified gap** — a gap that's *also* plausibly shoppable for this occasion ([glossary](../docs/glossary.md)).
- **Favorite stores** — locally-saved retailer hints — personalize the suggestion, never transmit ([glossary](../docs/glossary.md)).
- **Wishlist** — locally-saved items the user wants next, with optional priority + `linked_gap` ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* What two conditions must hold for a gap to be *qualified*?
2. *(Understand)* Why are shopping suggestions descriptive rather than promotional?
3. *(Apply)* A user with no blazer attends a work meeting. Trace the gap from detection to the surfaced suggestion.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
