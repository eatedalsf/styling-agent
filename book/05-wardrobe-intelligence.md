# 05 · Wardrobe intelligence

How Wearly models, filters, and reasons about the user's actual closet.

## Item model

Every wardrobe item in `wardrobe.json` carries:

| Field | Example | Used by |
|---|---|---|
| `id` | `"C001"` | Reject/regenerate, wear history |
| `name` | `"White Button-Down Blouse"` | UI rendering, reasoning trail |
| `type` | `"top"` / `"bottom"` / `"dress"` / `"outerwear"` / `"activewear"` | Required-piece check, outfit builder |
| `color` | `"white"` / `"terracotta"` / `"camel"` | Color score, item swatch |
| `formality` | `"business"` / `"smart_casual"` / `"casual"` / `"athletic"` / `"formal"` | Dress-vs-separates branching, outfit ordering |
| `season` | `["fall", "winter"]` | Season filter (derived from temperature) |
| `tags` | `["work", "dinner", "versatile"]` | Occasion filter |

Three sections: `clothing` (16 items), `shoes` (5 items), `accessories` (6 items). Plus an `owner` block (Phase 3 will split this out).

## The filter, step by step

`wardrobe_tool.filter_items_by_occasion(occasion_tag, season)` performs:

```
for each item in clothing/shoes/accessories:
    tag_match    = occasion_tag in item.tags
    season_match = "all" in item.season  OR  season in item.season

    keep if (tag_match AND season_match)

if no clothing kept (rare):
    relax season constraint, keep clothing where tag matches alone
```

The relaxation rule prevents an empty pool when a season is sparsely tagged. Better an outfit with a slightly-wrong-season item than no outfit at all — paired with a reasoning note when it happens.

## The outfit build, in pseudocode

```
if occasion is formal or dinner AND formality ≥ smart_casual:
    look for a dress
if no dress chosen:
    if occasion is gym: pick up to 2 activewear pieces
    else: pick a top + a bottom

add 1 shoes from the pool
add up to 2 accessories from the pool

if temp < 60°F:
    look for outerwear matching THIS occasion (not "work" as a fallback)
    if found: add it, note the weather reason
    if not: skip outerwear, flag a wardrobe gap
```

The "match THIS occasion" rule was added explicitly to prevent the agent from putting a `Camel Wool Coat` on top of a gym outfit. The fix is documented in `docs/architecture.md` and the test in `tests/test_agent_smoke.py`.

## Wear history (lightweight)

Wearly's first pass at wear history is intentionally small:

- `data/wear_history.json` (or similar) holds a list of `{item_id, worn_count, last_worn_date}`.
- `history_tool.record_wear(item_ids)` increments counts.
- `history_tool.get_freshness(item_id)` returns a freshness score (1.0 = never worn, decays toward 0 as `worn_count` rises or as `last_worn_date` becomes recent).
- The outfit builder can prefer fresher items when ties happen.

The point isn't a perfect rotation engine — it's a *visible* one. When a fresher item is chosen, the reasoning trail says so.

## Future wardrobe extensions

- **Add by photo** — Streamlit file uploader, background → white-bg composite (Phase 4).
- **Add by URL** — paste a product link, fill in fields manually for prototype, then per-store adapters in production (Phase 4 + 5).
- **Edit / delete** — straightforward CRUD on `wardrobe.json` (Phase 4).
- **Modesty / comfort / fabric** fields — used by the agent once the fit profile is fully wired (Phase 3 / 4).
- **Availability** — "in laundry" / "loaned out" — directly drops items from the pool (Phase 4).

## Where to verify

- `wardrobe.json` for the data shape.
- `wardrobe_tool.py` for the filter implementation.
- `styling_agent.py` (steps 4–6) for the orchestration.
- `tests/test_tools.py` for pool-filter correctness.
