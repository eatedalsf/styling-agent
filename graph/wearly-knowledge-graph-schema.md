# Wearly Knowledge Graph — schema

> A three-layer structured-knowledge graph modeling Wearly's **reusable
> domain knowledge**, **user-behavior patterns**, and the **runtime
> archetypes** the agent produces. Distinct from the Learning Graph
> (which teaches the reader concepts in order) and the Reasoning Graph
> (which explains one specific recommendation).
>
> This file is the canonical text description of the graph schema. The
> serialized data lives in `graph/wearly-knowledge-graph.json`; the
> interactive view at
> [`docs/sims/wearly-knowledge-graph/`](../docs/sims/wearly-knowledge-graph/index.md)
> renders that JSON with `vis-network.js`.

## Why three layers

| Layer | Question it answers | Stays the same when… |
|---|---|---|
| **Domain** | *What does Wearly know about styling?* | …every user, every run, every closet. |
| **User behavior** | *What does Wearly know about this user's patterns?* | Recomputed each time the underlying data changes (wear history, wishlist, favorite stores). |
| **Runtime archetype** | *What kinds of outputs can the agent produce, and which rules power them?* | Static; the schema for any per-run result conforms to it. |

Each node carries an explicit `layer` field and a `type` field. The
viewer uses both to filter, color, and group the graph.

## Node types

### Domain layer

| Type | Cardinality | Sample id | Description |
|---|---|---|---|
| `User` | 1 (per snapshot) | `user:demo` | The owner of this graph instance. The committed snapshot uses the anonymized "Demo User". |
| `FitProfile` | 1 | `fit:demo` | Fit + style preferences declared by the user (body shape, preferred fit, modesty, etc.). |
| `SkinTonePalette` | 3 | `skin:warm-olive`, `skin:cool-fair`, `skin:deep-warm` | One of the three skin-tone palettes defined in `color_rules.json`. |
| `OccasionType` | 5 | `occasion:work`, `occasion:gym`, … | The five canonical occasion tags (`work`, `gym`, `dinner`, `formal`, `casual`). |
| `WeatherCondition` | 5 | `weather:cold`, `weather:cool`, … | Temperature bands the agent uses (<40 / 40–59 / 60–74 / 75–84 / ≥85 °F). |
| `WardrobeItemType` | 7+ | `type:top`, `type:bottom`, `type:dress`, `type:outerwear`, `type:activewear`, `type:shoes`, `type:accessory` | The garment-type taxonomy the rule packs reason over. |
| `ColorFamily` | 7 | `color-family:warm-rich`, `color-family:cool-neutral`, … | Grouped color buckets so the graph stays readable (raw colors map up to a family). |
| `RulePack` | 7 | `pack:color-coordination-rules`, `pack:weather-rules`, … | One node per `.md` rule pack in `skills/wearly-styling-agent/`. |
| `Rule` | 21 | `rule:color-coordination-rules-R1`, … | One node per `R<N>` heading registered in `rule_refs.py`. Each carries its summary in `metrics`. |
| `WorkflowStep` | 7 | `step:1` … `step:7` | The seven steps `run_agent()` writes to `result["steps"]`. |

### User-behavior layer

| Type | Cardinality | Sample id | Description |
|---|---|---|---|
| `WardrobeItem` | varies | `item:C001` | One node per item in the wardrobe overlay (seed-only by default; `--include-user` adds the local overlay). |
| `WishlistItem` | varies | `wishlist:<id>` | Item the user wants to acquire next. The seed has none; the user overlay may add. |
| `FavoriteStore` | varies | `store:<id>` | Locally-saved retailer hint. Seed has none. |

### Runtime archetypes (referenced, not instantiated per-run)

| Type | Cardinality | Description |
|---|---|---|
| `OutfitRecommendation`, `WardrobeGap`, `ShoppingSuggestion`, `Feedback` | 0 in the seed snapshot | These types exist in `EDGE_TYPES` so the viewer can show how runtime artifacts plug back into the domain. The Reasoning Graph (per-run) instantiates them; this graph names them so future runtime data can attach. |

## Edge types

Every edge carries a `type` from the catalog below, plus optional
`metadata`. Direction is always `from` → `to`.

| Edge type | Source types | Target types | Meaning |
|---|---|---|---|
| `HAS_PROFILE` | `User` | `FitProfile` | The user's declared style + fit preferences. |
| `HAS_SKIN_TONE` | `User` | `SkinTonePalette` | The user's color palette anchor. |
| `OWNS` | `User` | `WardrobeItem` | The user has this item in their closet. |
| `HAS_FAVORITE_STORE` | `User` | `FavoriteStore` | Locally-saved retailer hint. |
| `HAS_WISHLIST_ITEM` | `User` | `WishlistItem` | Item flagged for future acquisition. |
| `PREFERS` | `User` | `ColorFamily` | Aggregated user preference signal (placeholder; runtime computes from wear history). |
| `HAS_TYPE` | `WardrobeItem` | `WardrobeItemType` | Classification of this item. |
| `HAS_COLOR` | `WardrobeItem`, `WishlistItem` | `ColorFamily` | Color bucket. |
| `SUITABLE_FOR` | `WardrobeItem` | `OccasionType` | The item carries an occasion tag for this canonical type. |
| `REQUIRES` | `OccasionType` | `WardrobeItemType` | The occasion's minimum required pieces (from `REQUIRED_PIECES`). |
| `USES_RULE` | `OccasionType`, `WeatherCondition` | `RulePack` | Domain knowledge: which rule pack governs this context. |
| `CONTAINS_RULE` | `RulePack` | `Rule` | Each pack contains its R-numbered rules. |
| `EVALUATES` | `Rule` | `SkinTonePalette`, `WardrobeItemType` | Which axes a specific rule is scored against. |
| `POWERS` | `RulePack` | `WorkflowStep` | Which step in `run_agent()` reads this pack. |
| `PRODUCES` | `WorkflowStep` | `OutfitRecommendation`, `WardrobeGap`, `ShoppingSuggestion` | Each step's output archetype. (Edges absent in seed; ready for runtime.) |
| `CONTAINS_ITEM` | `OutfitRecommendation` | `WardrobeItem` | Runtime: items inside an outfit. |
| `FLAGS_GAP` | `OutfitRecommendation` | `WardrobeGap` | Runtime: gaps detected for an outfit. |
| `SUGGESTS` | `WardrobeGap` | `ShoppingSuggestion` | Runtime: gap-driven suggestion. |
| `REJECTS` | `Feedback` | `WardrobeItem` | Runtime: user rejection. |
| `WISHLIST_CLOSES_GAP` | `WishlistItem` | `WardrobeGap` | Runtime: a wishlist item that would close a current gap. |

## Node weight — what size means in the viewer

Every node has a `weight` (1.0–3.0). The viewer scales the rendered
size proportionally. The weight is built up from observed signals so
**big nodes = signals the user produced more of**, and small nodes =
either unused or only declared once.

### How weight is computed

1. **`WardrobeItem`** — base 1.0 + 0.20 × `worn_count` (capped) + 0.10 × versatility (count of distinct occasion tags). Range typically 1.0–2.5.
2. **`WardrobeItemType`, `ColorFamily`, `OccasionType`** — rolled up from their connected `WardrobeItem` nodes. A category with many heavy items becomes a heavy category node. Range 1.0–3.0 after clamping.
3. **`FavoriteStore`** — base 1.0 + 0.05 × `times_chosen` (if data present).
4. **`WishlistItem`, `RulePack`, `Rule`, `WorkflowStep`, `User`, `FitProfile`, `SkinTonePalette`, `WeatherCondition`** — base 1.0 (domain/runtime archetypes; size encodes meaning equally for all).

### Reading sizes in practice

- A **large `WardrobeItem`** = worn often or covers many occasions (heavy rotation, versatile).
- A **large `OccasionType`** = many items in your closet are eligible for this occasion (rich coverage).
- A **large `ColorFamily`** = a color group your closet returns to.
- A **large `WardrobeItemType`** = a category you've invested in (your "tops collection," your "outerwear collection").
- A **small node** = declared in the domain but unused (no items, no events, no rejections).

These signals are **aggregations**, not predictions. The graph isn't learning a model; it's *visibly summarizing what the data already says.*

## Layer relationships — how the three layers interconnect

The cleanest way to read the schema:

```
DOMAIN LAYER (static)
  User ── HAS_PROFILE ──▶ FitProfile
  User ── HAS_SKIN_TONE ──▶ SkinTonePalette
  OccasionType ── REQUIRES ──▶ WardrobeItemType
  OccasionType ── USES_RULE ──▶ RulePack
  WeatherCondition ── USES_RULE ──▶ RulePack
  RulePack ── CONTAINS_RULE ──▶ Rule
  Rule ── EVALUATES ──▶ SkinTonePalette / WardrobeItemType
                          │
                          ▼
USER-BEHAVIOR LAYER (computed from data)
  User ── OWNS ──▶ WardrobeItem
  WardrobeItem ── HAS_TYPE ──▶ WardrobeItemType        (domain link)
  WardrobeItem ── HAS_COLOR ──▶ ColorFamily            (domain link)
  WardrobeItem ── SUITABLE_FOR ──▶ OccasionType        (domain link)
  User ── HAS_WISHLIST_ITEM ──▶ WishlistItem
  User ── HAS_FAVORITE_STORE ──▶ FavoriteStore
                          │
                          ▼
RUNTIME ARCHETYPE LAYER (the bridge to Reasoning Graph)
  RulePack ── POWERS ──▶ WorkflowStep
  WorkflowStep ── PRODUCES ──▶ OutfitRecommendation / WardrobeGap / ShoppingSuggestion
  OutfitRecommendation ── CONTAINS_ITEM ──▶ WardrobeItem    (closes the loop)
  WardrobeGap ── SUGGESTS ──▶ ShoppingSuggestion
  Feedback ── REJECTS ──▶ WardrobeItem
  WishlistItem ── WISHLIST_CLOSES_GAP ──▶ WardrobeGap
```

A reader following the arrows from the `User` node downward traverses
the *entire reasoning surface*: from declared profile to owned items
to qualifying rules to powered steps to produced artifacts.

## How this enables RAG and an LLM shopping agent

The graph is **structured context** — exactly the kind of input
modern LLM agents perform better against than free-text descriptions
of the same information.

### For a future RAG layer over the Intelligent Book

When the user asks an open-ended question like *"Why does this
blazer work for my profile?"*, a RAG pipeline can:

1. Query the graph for **nodes matching the user's question** (e.g.
   the blazer's `WardrobeItem` node + connected `WardrobeItemType` +
   `ColorFamily` + `SUITABLE_FOR` occasions).
2. Walk one hop outward to **the rules and rule packs** linked via
   `USES_RULE` and `CONTAINS_RULE`.
3. Retrieve the **book passages** keyed off those rule slugs (the same
   `<pack>#R<N>` slugs the agent already emits in its reasoning trail).
4. Feed the LLM a **compact subgraph plus the retrieved book
   passages**, not a wall of text.

The result: an explanation that cites the same rule the runtime
agent does, by retrieving along the graph rather than embedding
search alone.

### For a future LLM shopping agent over favorite stores

When the user has saved favorite stores and the runtime detects a
qualified gap, an LLM shopping agent can:

1. Read the current `WardrobeGap` and walk to the connected
   `OccasionType` and `WardrobeItemType` it needs to close.
2. Walk the user's `HAS_SKIN_TONE` edge for the target palette and
   the `FitProfile` for the preferred silhouette.
3. Visit each `FavoriteStore` node, extract its tags / city, and
   query the store's product catalog for candidates matching the
   graph-derived constraints.
4. Score candidates against the same rule packs the runtime engine
   uses (`color#R*`, `fit#R*`, `occasion#R*`), so the LLM
   recommendation **passes the same audit the deterministic engine
   would apply.**

The rule engine stays the safety/scoring layer. The LLM is the
discovery layer.

### For "structure beats prompts"

Three observable properties:

- **Compact**: the JSON is ~50–100 KB even with the user overlay
  loaded. That's an order of magnitude smaller than the equivalent
  flat-text representation of the rule packs + wardrobe + history.
- **Queryable**: filtering by `layer`, `type`, or `metric` returns a
  precise subgraph. No vector search needed for the structural parts.
- **Auditable**: every edge has a typed `from` / `to` / `type`. The
  citation chain is **literally traversable** as graph hops.

These properties are why Wearly's Intelligent Book chapter 04 frames
the rule layer as a foundation rather than a limitation: it's the
substrate on top of which future LLM and RAG layers stay inspectable.

## Generation

The graph is built by `scripts/generate_wearly_kg.py`. The default
mode reads only **public seed data**:

```
python scripts/generate_wearly_kg.py
```

Developer-only mode that includes the (gitignored) per-user overlay
files for personal exploration — never committed:

```
python scripts/generate_wearly_kg.py --include-user
```

Sources consulted by the generator (all public unless `--include-user`):

| Source | What it contributes |
|---|---|
| `wardrobe.json` (seed owner = "Demo User") | `WardrobeItem` nodes + `OWNS` / `HAS_TYPE` / `HAS_COLOR` / `SUITABLE_FOR` edges |
| `seed_wear_history.json` (committed demo) | `worn_count` and `last_worn` metrics on `WardrobeItem` nodes |
| `color_rules.json` | `SkinTonePalette` nodes + sample-color metadata |
| `rule_refs.py` | `RulePack` and `Rule` nodes |
| `styling_agent.OCCASION_TAG_MAP`, `REQUIRED_PIECES` | `OccasionType` nodes + `REQUIRES` edges |
| `--include-user` only: `user_wardrobe.json`, `wear_history.json`, `wishlist.json`, `favorite_stores.json` | Adds the developer's local overlay to the corresponding nodes |

## Versioning and extensibility

- The schema version is in `metadata.version` (`0.1.0` at the time of
  writing).
- New node types should be added to `NODE_TYPE_STYLES` in the
  generator and documented in this file.
- New edge types should be added to `EDGE_TYPES` with valid
  `source_types` / `target_types` lists so the viewer can color them
  consistently.
- Adding a new rule pack to `skills/wearly-styling-agent/` and
  registering its slugs in `rule_refs.py` automatically grows the
  graph (new `RulePack` + `Rule` nodes, new `CONTAINS_RULE` edges).

## What this is *not*

- Not a runtime side-effect. Generating the graph never affects the
  agent's recommendations. The agent reads its own structures; this
  graph is the public-facing summary of them.
- Not a learned model. No training, no weights, no inference. Every
  weight is a deterministic aggregation of observable signals.
- Not a replacement for the Reasoning Graph. The Reasoning Graph
  shows *one* recommendation in detail; the Knowledge Graph shows the
  *background* against which any recommendation is made.

---

*Companion to* [`graph/learning-graph.json`](learning-graph.json) (reader concepts) *and* [`graph/graph.json`](graph.json) (runtime Reasoning Graph schema)*.*
