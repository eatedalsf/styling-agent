# Wardrobe filtering rules

How items are selected from the user's closet for a given occasion + season. Implemented in `wardrobe_tool.filter_items_by_occasion()`.

## R1 — Occasion-tag match

An item matches an occasion if the occasion tag is present in the item's `tags` list:

```
match if occasion in item.tags
```

Items tagged with multiple occasions (e.g., `["work", "dinner", "versatile"]`) are eligible for any of those occasions. The `versatile` tag is informational only; it doesn't auto-match.

## R2 — Season match

An item matches a season if:

- `"all"` is in `item.season`, **or**
- the current season is in `item.season`.

## R3 — Combined filter

A candidate item must satisfy **both** R1 and R2 to enter the pool.

## R4 — Pool relaxation (last resort)

If the combined filter yields **zero clothing items**, relax R2 — keep clothing where the tag matches even if the season doesn't.

This is the lesser of two evils: a slightly-wrong-season piece is better than an empty pool. When this relaxation activates, surface it in the reasoning trail.

## R5 — Rejection exclusion

After the pool is built, drop any item whose `id` appears in `rejected_ids`. This is applied in Step 4 of the agent, and the exclusion count is noted in Step 4's `output`.

The rejection reasons are surfaced separately at the top of Step 5's reasoning trail — one line per rejection, naming both the item and the reason.

## R6 — Pool ordering

Within each pool (clothing / shoes / accessories), items are NOT sorted by the filter. Ordering happens inside the outfit builder (Step 5), based on:

1. Type required by the occasion (top → bottom → shoes → accessories → outerwear).
2. Formality match for the occasion's expected formality.
3. (Phase 4) Wear-history freshness — fresher items preferred.
4. (Phase 3) Fit-profile alignment.

## R7 — Empty-pool handling

If, after all filters and exclusions, a pool is empty:

- The outfit builder produces a best-available result with the items it can find.
- Step 6 (gap check) catches the missing required pieces.
- The reasoning trail surfaces the constraint that led to the empty pool.

The agent never fakes a piece. An empty pool is honest data.
