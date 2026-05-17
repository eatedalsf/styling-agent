# 05 · Wardrobe intelligence

*The app filters and builds outfits from this data model; this chapter explains how items become candidates and candidates become outfits.*

> The *styling knowledge* the construction rules apply is taught in
> Part II: [§S5 · Wardrobe construction](S5-wardrobe-construction.md)
> covers required pieces, dress-vs-separates, and the accessory cap;
> [§S6 · Rotation and freshness](S6-rotation-and-freshness.md) covers
> the tie-breaker that picks among equally-eligible items.

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

Wearly's wear-history layer is focused and visible:

- `data/wear_history.json` (or similar) holds a list of `{item_id, worn_count, last_worn_date}`.
- `history_tool.record_wear(item_ids)` increments counts.
- `history_tool.get_freshness(item_id)` returns a freshness score (1.0 = never worn, decays toward 0 as `worn_count` rises or as `last_worn_date` becomes recent).
- The outfit builder can prefer fresher items when ties happen.

Rotation is visible — when a fresher item is chosen, the reasoning trail says so. Optimization layers can ride on top later.

## Image understanding (what ships today vs the production path)

The Wardrobe Builder accepts a photo and uses it to **assist** the user — not to fully classify the garment. Concretely:

| Today, in the prototype | Production path |
|---|---|
| **Pillow-only dominant-color extraction** — resize to 96×96, quantize to 8 colors with `Image.Quantize.MEDIANCUT`, count pixels per color, snap each to the closest named color in `NAMED_COLORS` via Euclidean distance in RGB. Return top 3 candidates with weights. | Real per-pixel segmentation against a fine-tuned model so we can extract the garment's colors specifically, not the background's. |
| **No category recognition** — the user picks "top / bottom / dress / outerwear / activewear / shoes / accessory" from a dropdown. | Fine-tuned CLIP or a hosted vision API (Google Vision, AWS Rekognition) returning a category + formality estimate that the user can confirm or override. |
| **Alpha → white composite, not true bg removal.** Images uploaded with transparency are placed on a white canvas. Photos with complex backgrounds are stored as-is. | `rembg` (ONNX models, ~120MB) for client-side bg removal, or a server-side service like Remove.bg / Cloudinary. |
| **Local filesystem write** to `wardrobe_images/{id}.png`, downscaled to ≤1024 px on the longest side, PNG optimize=true. | Object storage (S3, Cloudflare R2) with signed URLs. Replaces the ephemeral Streamlit Cloud filesystem. |
| **Ephemeral on Streamlit Cloud.** Saved images and added items survive only until the container restarts (Cloud free-tier filesystem is ephemeral). Surfaced to the user via a `st.info` notice on the photo tab. | Real database + blob store. The prototype's `user_wardrobe.json` becomes a per-user row in a managed DB. |
| **No URL import** yet. | A small parser pulling `og:image` and `application/ld+json` Product fields, with manual user confirmation. Per-store adapters for the top retailers. |

**Why "upload + review" rather than fully autonomous?** User-in-the-loop classification is a design choice: Pillow-level color extraction runs free on any environment, the user confirms category in one tap (which is faster than waiting for a vision API to return), and production-grade vision can be dropped in later without changing the wardrobe-builder UX. The agent stays fast, free, and inspectable today — and stays inspectable when the classifier ships.

## Future wardrobe extensions

- **Edit / delete** — straightforward CRUD on `user_wardrobe.json` (Phase 4).
- **Modesty / comfort / fabric** fields — used by the agent once the fit profile is fully wired (Phase 3 / 4).
- **Availability** — `"in laundry"` / `"loaned out"` — already drops items from the pool today via `filter_items_by_occasion()` (shipped in the Wardrobe Builder pass).

## Where to verify

- `wardrobe.json` for the data shape.
- `wardrobe_tool.py` for the filter implementation.
- `styling_agent.py` (steps 4–6) for the orchestration.
- `tests/test_tools.py` for pool-filter correctness.

---

## Key terms

- **Wardrobe filtering** — Step 4 — narrow the closet by occasion tags, season, availability, and rejection exclusions ([glossary](../docs/glossary.md)).
- **Outfit construction** — Step 5 — dress vs. separates branching, gym branching, outerwear injection below 60°F ([glossary](../docs/glossary.md)).
- **Knowledge graph (runtime)** — `graph/graph.json` — wardrobe items + relations the agent reasons over ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* What temperature threshold injects outerwear into a non-formal outfit?
2. *(Understand)* Why is dress-vs-separates a branch rather than a score?
3. *(Apply)* Given a 55°F dinner event, which Step 5 branches fire, in order?

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze).*
