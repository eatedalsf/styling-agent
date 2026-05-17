# Wearly Knowledge Graph

> **Learning objective.** After working through this graph, you will
> be able to distinguish Wearly's three structured-knowledge layers
> (domain, user behavior, runtime), explain what node size encodes
> in terms of user signal, and describe how the graph functions as
> the substrate for future RAG and LLM shopping layers.
>
> **What you're looking at.** A live render of
> [`graph/wearly-knowledge-graph.json`](../../../graph/wearly-knowledge-graph.json) —
> 91 nodes, 187 typed edges, generated deterministically from public
> seed data by [`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py).
>
> **What this graph is for.** It models the *structured knowledge*
> Wearly reasons over — reusable across users, queryable by future
> LLM layers. Big nodes = signals you produced more of; small nodes =
> declared in the domain but unused.

### → [**Open the Knowledge Graph in full screen ↗**](main.html){target="_blank"}

Recommended for class demos. The full-screen view escapes the book's
column width and gives the graph proper room to breathe.

<iframe
  src="main.html"
  width="100%"
  height="860"
  style="border: 0; border-radius: 8px;"
  loading="lazy"
  title="Wearly Knowledge Graph">
</iframe>

---

## How to read the graph

The viewer is built in the same design language as the SEIS 666
course learning-graph viewer: gradient page background, frosted-glass
cards, soft pastel-per-type palette, simple toolbar.

| Visual signal | What it encodes |
|---|---|
| **Color** | Node *type*. Each of the 17 types gets a distinct soft pastel; the User is the one dark anchor so the focal point is unmistakable. The legend shows every type with its count. |
| **Shape** | Most nodes are ellipses (uniform, label-readable). The **User** is a star — single focal point. **WardrobeGap** and **ShoppingSuggestion** are triangles — warning shapes. |
| **Size** | User signal — a wardrobe item worn more often + covering more occasions is larger; a color family used across many items is larger; a category with rich coverage is larger. Domain archetypes (rule packs, weather bands, palettes) stay at base size. |
| **Edge color** | Light grey by default — un-emphasized. Highlighted edges (when a node is selected, search matches, or a legend type is filtered) turn periwinkle (#667eea). |

## What the controls do

| Control | Behavior |
|---|---|
| **Search** | Type any name or type. Matching nodes stay full opacity; non-matches fade to ~18%. |
| **Layer filter** *(sidebar)* | Filter to domain / user-behavior / runtime. |
| **Layout dropdown** *(sidebar)* | Switch between **Physics (force-directed)** — default, lets categories cluster naturally — or **Hierarchical** (top-down). |
| **Click any legend row** | Toggle to focus that node type. Everything else fades; the graph re-fits to the matching subset. Click the same row again to clear. |
| **Click any node** | Open the info panel with type, layer, weight, one-sentence meaning, metrics, and in/out edge counts. |
| **Double-click any node** | Highlight its 1-hop neighborhood; everything else fades to 15%. Click empty canvas to reset. |
| **Fit to view** | Re-center and zoom to fit. |
| **Reset** | Clear all filters; restore the default force-directed view. |
| **Toggle Physics** | Pause / resume the simulation. Useful for capturing a screenshot at a stable layout. |

## What each link represents

The graph carries **20 typed relations**. The full catalog:

### Domain knowledge (static)

| Edge | Source | Target | Meaning |
|---|---|---|---|
| `HAS_PROFILE` | User | FitProfile | The user's declared style + fit preferences. |
| `HAS_SKIN_TONE` | User | SkinTonePalette | The user's color-palette anchor. |
| `REQUIRES` | OccasionType | WardrobeItemType | The occasion's minimum required pieces. |
| `USES_RULE` | OccasionType / WeatherCondition | RulePack | Which rule pack governs this context. |
| `CONTAINS_RULE` | RulePack | Rule | Each pack's R-numbered rules. |
| `EVALUATES` | Rule | SkinTonePalette / WardrobeItemType | Which axes a specific rule scores against. |

### User behavior (computed from the user's data)

| Edge | Source | Target | Meaning |
|---|---|---|---|
| `OWNS` | User | WardrobeItem | The item is in the user's closet. |
| `HAS_TYPE` | WardrobeItem | WardrobeItemType | Classification. |
| `HAS_COLOR` | WardrobeItem / WishlistItem | ColorFamily | Color bucket. |
| `SUITABLE_FOR` | WardrobeItem | OccasionType | Has an occasion tag. |
| `HAS_FAVORITE_STORE` | User | FavoriteStore | Saved retailer. |
| `HAS_WISHLIST_ITEM` | User | WishlistItem | Wants to acquire. |
| `PREFERS` | User | ColorFamily | Aggregate preference signal. |

### Runtime archetypes (the bridge to live recommendations)

| Edge | Source | Target | Meaning |
|---|---|---|---|
| `POWERS` | RulePack | WorkflowStep | The rule pack runs at this step. |
| `PRODUCES` | WorkflowStep | OutfitRecommendation / WardrobeGap / ShoppingSuggestion | Each step's output archetype. |
| `CONTAINS_ITEM` | OutfitRecommendation | WardrobeItem | Items in an outfit. |
| `FLAGS_GAP` | OutfitRecommendation | WardrobeGap | Per-run gaps. |
| `SUGGESTS` | WardrobeGap | ShoppingSuggestion | Gap-driven suggestion. |
| `REJECTS` | Feedback | WardrobeItem | User pushback. |
| `WISHLIST_CLOSES_GAP` | WishlistItem | WardrobeGap | A wished item that would close a current gap. |

## How node size is computed

| Node type | Size formula |
|---|---|
| **WardrobeItem** | `1.0 + 0.20 × worn_count + 0.10 × versatility` (versatility = count of distinct canonical occasion tags). A piece worn six times across three occasions reaches ~2.4. |
| **WardrobeItemType, ColorFamily, OccasionType** | Rolled up from connected `WardrobeItem` weights. A category with many heavy items becomes a heavy category node. |
| **FavoriteStore** | Scales with `times_chosen` (when overlay data is included). |
| **All other types** | Base size — domain/runtime archetypes are equal-importance facts. |

All weights clamp to [1.0, 3.0] so a heavy category never dwarfs the
User node.

## How this enables RAG and an LLM shopping agent

The graph is **structured context** — the kind of input modern LLM
agents perform better against than a flat-text dump of the same
information.

### RAG over the Intelligent Book

A question like *"Why does this dress work for my profile?"* becomes:

1. Start at the dress's `WardrobeItem` node.
2. Walk one hop to `WardrobeItemType` + `ColorFamily` +
   `SUITABLE_FOR` occasion(s).
3. Follow `USES_RULE` to the rule packs that govern those contexts.
4. Retrieve the **book chapters keyed off the rule slugs** the agent
   already emits in its reasoning trail.

The LLM gets a **compact subgraph + the relevant book passages**.
Retrieval happens *along graph edges*, not vector embeddings, so the
explanation cites the same rule the runtime agent does.

### LLM shopping agent over favorite stores

When a `WardrobeGap` is detected at runtime, the LLM shopping agent:

1. Reads the gap's connected `WardrobeItemType` and `OccasionType`.
2. Walks the user's `HAS_SKIN_TONE` for the target palette and
   `HAS_PROFILE` for the silhouette.
3. Visits each `FavoriteStore` and queries that store's catalog with
   the graph-derived constraints.
4. Scores any candidate against the same rule packs the runtime
   engine uses.

**The rule engine stays the safety + scoring substrate; the LLM is
the discovery layer.**

### Structure beats prompts

- **Compact** — the full graph is ~66 KB; the equivalent flat-text
  description is an order of magnitude larger.
- **Queryable** — filtering by layer / type / metric returns a
  precise subgraph.
- **Auditable** — every edge has a typed `from` / `to` / `type`. The
  citation chain is *literally a graph traversal*.

## Linked concept

- *Schema reference:* [`graph/wearly-knowledge-graph-schema.md`](../../../graph/wearly-knowledge-graph-schema.md).
- *Data file:* [`graph/wearly-knowledge-graph.json`](../../../graph/wearly-knowledge-graph.json).
- *Generator:* [`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py).

---

## See also

- **[Skill package overview](../../../skills/wearly-styling-agent/SKILL.md)** — the eight rule packs the Knowledge Graph models.
- **[Evidence & references](../../../docs/evidence-and-references.md)** — what informs the rules every `Rule` node represents.
