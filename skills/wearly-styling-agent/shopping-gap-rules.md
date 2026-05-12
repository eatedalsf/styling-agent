# Shopping & gap rules

Gap detection, occasion-specific shopping suggestions. Implemented in `styling_agent.py` `SHOPPING_SUGGESTIONS` and Step 6.

## R1 — Gap detection (required-piece path)

For each occasion, `REQUIRED_PIECES` defines piece types that must appear in the outfit:

| Occasion | Required pieces |
|---|---|
| work | top + bottom |
| dinner | top + bottom |
| gym | activewear + activewear |
| formal | dress |
| casual | top + bottom |

After Step 5 builds the outfit, Step 6 computes:

```
covered = {item.type for item in outfit}
gaps    = [required for required in REQUIRED_PIECES[occasion] if required not in covered]
```

Any missing required type becomes a gap.

## R2 — Gap detection (outerwear path)

Separately: if `temp < 60°F` and no occasion-appropriate outerwear exists in the wardrobe pool, Step 5 (not Step 6) adds `"outerwear"` to the gap list. This is the case where the agent **chooses to leave a layer out** rather than force a wrong-style piece.

## R3 — Occasion-specific shopping templates

Per-occasion default suggestion text:

| Occasion | Suggestion template |
|---|---|
| formal | "A floor-length gown or tailored formal suit would complete a formal look." · "Consider a statement clutch and elegant heels for formal events." |
| work | "A classic blazer would add polish to any work outfit." · "A second pair of tailored trousers in a neutral would expand your options." |
| dinner | "A chic midi dress in a jewel tone would be perfect for dinner occasions." · "A pair of elegant strappy heels would elevate dinner outfits." |
| casual | "A denim jacket is a great casual layering piece." · "Versatile flats or loafers work well for casual outings." |
| gym | "A high-support sports bra would be a useful gym addition." · "Moisture-wicking shorts for warmer workout days." |

## R4 — Outerwear-specific gap suggestion

When the gap is outerwear (R2 path):

- For gym occasion: *"A lightweight athletic windbreaker or running jacket would cover cool-weather gym transit without breaking the activewear look."*
- For other occasions: *"A {occasion}-appropriate coat or jacket would round out your wardrobe for cool-weather days."*

## R5 — Tone of suggestions

Suggestions are **descriptive**, not promotional:

- ✅ *"A chic midi dress in a jewel tone would be perfect for dinner occasions."* (describes a piece-type)
- ❌ *"Shop our partner brand's dinner dress collection."* (promotional)

The product brief explicitly forbids affiliate behavior. Suggestion text should help the user know *what to look for*, not *where to buy*.

## R6 — UI distinction between owned and suggested

In the Streamlit UI:

- **Owned items** appear inside the outfit card with their actual color swatch.
- **Suggestions** appear inside a separate gap panel with `→` arrow prefixes and warm cream backing.

A user must never confuse "you own this" with "you should buy this."

## R7 — Wishlist (Phase 5)

When wishlists ship, each suggestion becomes a card with:
- a "Save to wishlist" action,
- optional store preference based on `data/stores.json`,
- a clear "we don't sell this" disclaimer.

Until then, suggestion lines are read-only text.

---

## Source basis

**Primary category:** Fashion recommender systems (`docs/evidence-and-references.md` §3.1).
**Secondary:** Wardrobe management (§3.7), Privacy (§3.9).
**Current basis:** Industry styling practice for gap detection + a deliberate product stance on commerce.
**Stance worth naming:** Wearly's gap-suggestion text is **descriptive, not promotional**. The product brief commits to this. No affiliate links. No retailer scraping. Favorite stores act as personalization hints, never as paid placements.
**Pending verification:** Industry whitepapers or case studies from closet-management apps; any peer-reviewed work on shopping recommendations that handles owned-vs-suggested distinction respectfully.
