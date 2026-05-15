# Wearly Knowledge Graph

> **Learning objective.** After working through this graph, you will
> be able to distinguish Wearly's three structured-knowledge layers
> (domain, user behavior, runtime archetypes), explain what node size
> encodes in terms of user signal, and describe how the graph
> functions as the substrate for future RAG and LLM shopping layers.
>
> **What you're looking at.** A presenter-grade explorer over
> [`graph/wearly-knowledge-graph.json`](../../../graph/wearly-knowledge-graph.json) —
> 91 nodes, 187 typed edges, generated deterministically from public
> seed data by [`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py).
>
> **This is the third interactive graph in Wearly.** The
> [Learning Graph](../learning-graph/index.md) teaches the reader the
> book's concept order. The
> [Reasoning Graph](../knowledge-graph/index.md) explains one specific
> recommendation. **This graph** models the *structured knowledge*
> Wearly reasons over — reusable across users, queryable by future
> LLM layers.

### → [**Open the Knowledge Graph in full screen ↗**](main.html){target="_blank"}

The full-screen view escapes the book's column width and gives the
graph proper room to breathe. Recommended for class demos or any
deep exploration session.

<iframe
  src="main.html"
  width="100%"
  height="820"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Knowledge Graph">
</iframe>

---

## How this viewer is designed (and what the redesign answers)

In class, Dan asked Juan **what each link in his graph represented** —
and praised the fact that Juan's node sizes encoded financial
exposure rather than being decorative. Two principles for this
viewer follow from that:

1. **Every edge has a typed name.** Click any node and the side
   panel shows its 1-hop relationships **grouped by relation type**,
   with the relation name visible as a chip prefix. Hover any edge in
   the canvas (or toggle "Show edge labels" in the sidebar) to read
   the type in place.
2. **Node size encodes user signal, not aesthetic preference.** A
   heavier `WardrobeItem` is worn more often (and covers more
   occasions). A heavier `WardrobeItemType` / `ColorFamily` /
   `OccasionType` rolls up from its connected items. Domain
   archetypes (`RulePack`, `WeatherCondition`, `SkinTonePalette`)
   stay at base size — they're equal-importance facts. The legend in
   the sidebar names every shape; a callout block above the legend
   says **what size means.**

## Eight preset views

The graph defaults to **Overview**, not a 91-node blob. Use the
preset buttons in the sidebar to jump between focused slices.

| Preset | What you see | Best for |
|---|---|---|
| **Overview** *(default)* | The system spine: User · FitProfile · SkinTonePalette · 5 OccasionType · 7 RulePack · 7 WorkflowStep. ~25 nodes. | First read. The shape of Wearly in one screen. |
| **User Pattern** | User + 27 WardrobeItems + their direct neighbors (color family, item type, suitable occasions). | *"What does Wearly know about this user?"* |
| **Occasions** | The 5 occasions, the item types each requires, the rule packs that govern them, and the items that fit. | *"Which wardrobe items connect to which occasions?"* |
| **Wardrobe Items** | Every item, sized by `worn_count × versatility`. Color families and item types as anchors. | *"Which items are heavy hitters in this closet?"* |
| **Rules & Skills** | The 7 rule packs, their R-numbered rules, and the workflow steps they power. | *"Which rules and skills power the workflow?"* |
| **Color & Skin** | 3 skin-tone palettes, 7 color families, the color-coordination rule pack and its rules. | *"How does Step 7 work?"* |
| **Weather & Layers** | 5 temperature bands, the weather rule pack, the rules inside it, and Step 3. | *"How do layering decisions get made?"* |
| **Full Graph** | All 91 nodes, all 187 edges. | A density check, not a reading view. |

## Click any node — and watch the rest fade

When you click a node, the graph **focuses on its 1-hop neighborhood**:

- Selected node gets a thick accent border.
- 1-hop neighbors keep full opacity.
- Everything else fades to ~15% so the local subgraph becomes legible.
- Connected edges turn warm-rust (otherwise grey) and show their
  type as a label.
- The side panel populates with the node's type, layer, weight, a
  one-sentence meaning, its metrics, and **its relationships grouped
  by edge type**.

Click any chip in the side panel to hop to that node. Click any blank
area to clear the focus.

## What each link represents

The graph carries **20 typed relations.** They fall into four families:

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

### Runtime archetypes (the bridge to the Reasoning Graph)

| Edge | Source | Target | Meaning |
|---|---|---|---|
| `POWERS` | RulePack | WorkflowStep | The rule pack runs at this step. |
| `PRODUCES` | WorkflowStep | OutfitRecommendation / WardrobeGap / ShoppingSuggestion | Each step's output archetype. |
| `CONTAINS_ITEM` | OutfitRecommendation | WardrobeItem | Items in an outfit. |
| `FLAGS_GAP` | OutfitRecommendation | WardrobeGap | Per-run gaps. |
| `SUGGESTS` | WardrobeGap | ShoppingSuggestion | Gap-driven suggestion. |
| `REJECTS` | Feedback | WardrobeItem | User pushback. |
| `WISHLIST_CLOSES_GAP` | WishlistItem | WardrobeGap | A wished item that would close a current gap. |

## What node size means in this viewer

| Node type | What size encodes |
|---|---|
| **WardrobeItem** | `1.0 + 0.20 × worn_count + 0.10 × versatility` (versatility = count of distinct canonical occasion tags). A piece worn six times across three occasions reaches ~2.4. |
| **WardrobeItemType, ColorFamily, OccasionType** | Rolled up from connected `WardrobeItem` weights. A category with many heavy items becomes a heavy category node. |
| **FavoriteStore** | Scales with `times_chosen` (when overlay data is included). |
| **All other types** | Base size. Domain archetypes are equal-importance facts; their value is informational, not behavioral. |

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
   engine uses (`color#R*`, `fit#R*`, `occasion#R*`).

**The rule engine stays the safety + scoring substrate; the LLM is
the discovery layer.** The LLM's output is auditable against the
same graph the agent's reasoning trail traces through.

### Structure beats prompts

- **Compact.** The full graph is ~66 KB. The equivalent flat-text
  description of rules + wardrobe + history is an order of magnitude
  larger.
- **Queryable.** Filtering by layer / type / metric returns a precise
  subgraph. No vector search needed for the structural parts.
- **Auditable.** Every edge has a typed `from` / `to` / `type`. The
  citation chain (`evidence → category → rule → reasoning line`) is
  *literally a graph traversal*.

## Linked concept

- *Schema reference:* [`graph/wearly-knowledge-graph-schema.md`](../../../graph/wearly-knowledge-graph-schema.md).
- *Data file:* [`graph/wearly-knowledge-graph.json`](../../../graph/wearly-knowledge-graph.json).
- *Generator:* [`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py) — re-run after wardrobe/history changes to regenerate.

---

## See also

- **[Learning Graph](../learning-graph/index.md)** — the *reader's* concept DAG.
- **[Reasoning Graph](../knowledge-graph/index.md)** — the *runtime per-recommendation* entity model.
- **[Skill package overview](../../../skills/wearly-styling-agent/SKILL.md)** — the eight rule packs the Knowledge Graph models.
- **[Evidence & references](../../../docs/evidence-and-references.md)** — what informs the rules every `Rule` node represents.
