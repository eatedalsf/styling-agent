# Wearly Knowledge Graph — Schema

> A small, inspectable graph modeling the relationships between the contexts and decisions Wearly reasons across.
> Demonstrates that Wearly reasons through **connected context**, not random prompts.

The graph is intentionally minimal — 9 entity types, 14 relation types. Small enough to render on one page, expressive enough to cover every reasoning step in `styling_agent.py`.

---

## Entity types

| ID | Label | Example | Source |
|---|---|---|---|
| `User` | The wearer | "Eatedal" | `wardrobe.json` → `owner` |
| `FitProfile` | Body shape, skin tone, modesty, fit preferences | "hourglass, warm olive, tailored" | `wardrobe.json` → `owner` (Phase 3 splits this out) |
| `CalendarEvent` | An upcoming calendar entry | "Team Strategy Meeting, 2026-05-12" | `calendar_events.json` |
| `WeatherSnapshot` | A point-in-time weather reading | "Minneapolis, 58°F, partly cloudy" | `weather_tool.get_weather()` |
| `WardrobeItem` | A garment, shoe, or accessory | "White Button-Down Blouse, #F4EFE8" | `wardrobe.json` |
| `OutfitRecommendation` | A set of WardrobeItems for an occasion | "Today's work outfit (6 pieces)" | `run_agent()` result |
| `WardrobeGap` | A missing piece the outfit needs | "athletic outerwear" | Step 6 |
| `ShoppingSuggestion` | A recommended-to-buy item resolving a gap | "lightweight running jacket" | `SHOPPING_SUGGESTIONS` |
| `Feedback` | A user's reject/regenerate signal | "rejected · too formal" | Session state |

---

## Relation types

| Relation | Source → Target | Meaning |
|---|---|---|
| `has_fit_profile` | User → FitProfile | A user owns one fit profile |
| `owns` | User → WardrobeItem | A user owns N wardrobe items |
| `has_event` | User → CalendarEvent | A user has N upcoming events |
| `sees_weather` | User → WeatherSnapshot | A user is in one weather context per run |
| `prefers_color_palette` | FitProfile → palette | Drives Step 7 color scoring |
| `prefers_silhouette` | FitProfile → silhouette | Drives Step 5 outfit construction (future) |
| `has_occasion_type` | CalendarEvent → occasion | "work", "dinner", "gym", "formal", "casual" |
| `requires_layer_for` | WeatherSnapshot → layer | "outerwear", "none", "rain shell" |
| `matches_occasion` | WardrobeItem → occasion | An item tagged for an occasion |
| `is_appropriate_for_season` | WardrobeItem → season | An item tagged for a season |
| `recommends` | OutfitRecommendation → WardrobeItem | The N items in an outfit |
| `addresses_event` | OutfitRecommendation → CalendarEvent | The event the outfit is for |
| `flags_gap` | OutfitRecommendation → WardrobeGap | A missing piece detected |
| `suggests_to_buy` | WardrobeGap → ShoppingSuggestion | Phase 5 wiring |
| `was_rejected_with` | WardrobeItem → Feedback | Reject & regenerate |
| `excludes_from_pool` | Feedback → WardrobeItem | Future runs drop this item |
| `cites_step` | OutfitRecommendation → step (1–7) | Reasoning trail (every line) |

---

## Why these specifically

The graph is shaped to answer one question:

> **"Why is this specific outfit being recommended right now?"**

To answer that, we have to traverse from a `User` outward through their `CalendarEvent`, the day's `WeatherSnapshot`, their `FitProfile`, and the `WardrobeItem` pool — converging on a single `OutfitRecommendation` that cites each of the seven workflow steps that produced it.

Every reasoning line in the result dict is a graph traversal.

---

## What's *not* in the graph (yet)

- **Style aesthetic clusters** — "elevated minimal," "boho," "athleisure." Phase 4+.
- **Brand preferences** — Phase 5 (with favorite stores).
- **Wear history transitions** — Phase 4 will add `worn_on` edges between WardrobeItem and CalendarEvent.
- **Cross-user signals** — out of scope. Wearly is per-user; no collaborative filtering.

---

## The visualization

The full graph rendered as a Mermaid diagram lives in `graph/render.md`. The serialized triples live in `graph/graph.json`.

The diagram is sized to fit a slide deck or the README hero — about 12 nodes visible at once, enough to tell the story without overwhelming the page.
