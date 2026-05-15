# Wearly Knowledge Graph

> **Learning objective.** After working through this graph, you will
> be able to distinguish Wearly's three structured-knowledge layers
> (domain, user behavior, runtime archetypes), explain what node size
> means in terms of user signals, and describe how the graph enables
> future RAG and LLM shopping layers without giving up auditability.
>
> **What you're looking at.** A live render of
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

<iframe
  src="main.html"
  width="100%"
  height="780"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Knowledge Graph">
</iframe>

---

## Three layers in one graph

| Layer | Question it answers | What changes when… |
|---|---|---|
| **Domain** | *What does Wearly know about styling?* | Never. These are the rules + entity types + relations the agent is built around. |
| **User behavior** | *What does Wearly know about this user's patterns?* | The user wears, rejects, wishes, or saves something. Node weights aggregate the underlying signal. |
| **Runtime archetypes** | *What kinds of outputs can the agent produce, and which rules power them?* | New rule packs are added or workflow steps change. |

Use the **Layer dropdown** in the viewer to isolate one slice at a
time. Use **Spotlight User neighborhood** to see the user's first-hop
connections — that view answers *"what does the agent know about me
right now?"*

## How to read the graph

| Visual signal | What it means |
|---|---|
| **Node size** | Aggregated user signal — heavier nodes carry more activity (worn often, covers many occasions, many items in this category). Domain nodes stay at base size because they're equal-importance facts. |
| **Shape** | Encodes node *type*: diamonds for `User` and `OutfitRecommendation`, boxes for declared entities (`OccasionType`, `FitProfile`), hexagons for `RulePack`, dots for instances, triangles for `WardrobeGap` / `ShoppingSuggestion`, stars for `FavoriteStore`. |
| **Color** | Same Wearly book palette — paper / card / warm-rust accent on the domain rules, warmer ivory on the user behavior nodes. Skin-tone-related nodes pick up the deep-warm accent. |
| **Edge label** | Typed relation (`OWNS`, `REQUIRES`, `HAS_TYPE`, `USES_RULE`, `POWERS`, etc.). Hover an edge to read the relation; click either endpoint to expand from there. |

## What's on the graph today (seed-only snapshot)

The committed JSON is built from **public seed data** — the anonymized
"Demo User" closet, the demo wear history, the seven workflow steps,
the eight rule packs, and the 21 registered rule slugs. The schema
contains user-behavior nodes for `WishlistItem` and `FavoriteStore`,
but the seed has none — those slots are reserved for the local
overlay.

Snapshot at the time of writing:

| Node type | Count | Why this number |
|---|---|---|
| `User` | 1 | One owner per snapshot. |
| `FitProfile` | 1 | The seed owner's fit profile. |
| `SkinTonePalette` | 3 | Three palettes defined in `color_rules.json`. |
| `OccasionType` | 5 | `work`, `gym`, `dinner`, `formal`, `casual`. |
| `WeatherCondition` | 5 | Temperature bands the agent uses. |
| `WardrobeItemType` | 7 | The garment-type taxonomy. |
| `ColorFamily` | 7 | Color buckets so the graph doesn't degenerate into 50 leaf colors. |
| `RulePack` | 7 | One per `.md` file in `skills/wearly-styling-agent/`. |
| `Rule` | 21 | One per `R<N>` heading registered in `rule_refs.py`. |
| `WorkflowStep` | 7 | The seven steps of `run_agent()`. |
| `WardrobeItem` | 27 | The 16 + 5 + 6 items in the seed wardrobe. |
| **Total** | **91 nodes** | |
| **Edges** | **187** | Typed relations across all three layers. |

## What size means

Every node has a `weight` (1.0–3.0). The viewer scales the rendered
size proportionally so **big = more user signal**, **small = lightly
used or domain archetype**.

- **`WardrobeItem`**: starts at 1.0, grows with `worn_count` and
  versatility (count of occasion tags). A piece worn six times for
  three different occasions reaches ~2.4.
- **`WardrobeItemType`, `ColorFamily`, `OccasionType`**: roll up
  from their connected `WardrobeItem` nodes. A category with many
  heavy items becomes a heavy category node.
- **`FavoriteStore`**: scales with how often it's chosen (when overlay
  data is included).
- **Domain nodes** (`RulePack`, `Rule`, `SkinTonePalette`,
  `WeatherCondition`, `WorkflowStep`): stay at base size — they're
  facts, not user-weighted.

A small `WardrobeItemType` node = a category you've barely invested
in. A large `OccasionType` node = an occasion your wardrobe is rich
for. The graph reads at a glance.

## What to notice

- **The `User` node is the densest hub.** Every recommendation
  traces back to it. Click the **Spotlight User neighborhood** button
  to see what the agent knows about *you* before any one run.
- **`OccasionType` nodes connect both ways.** They `REQUIRE` item
  types (domain knowledge) and items `SUITABLE_FOR` them
  (user-behavior coverage). When the two sides match, you have full
  coverage; when they don't, there's a structural wardrobe gap.
- **The `RulePack` hexagons are the bridge** between domain knowledge
  and the runtime workflow. Each one `POWERS` one or more
  `WorkflowStep` nodes. That edge is *literally* the citation chain
  the agent emits at runtime — `<pack>#R<N>` slugs trace through
  this exact edge.
- **Switch the layout to hierarchical top-down.** The User pushes
  down to its wardrobe items, the items to types and color families,
  the types and palettes to the rules that evaluate them, the rules
  to the packs and the packs to the workflow steps. The graph
  literally diagrams *"how the agent gets from a user to an outfit."*

## Try this

1. **Filter to layer = `domain`.** What's left is everything Wearly
   knows independent of any user — the styling vocabulary itself.
2. **Filter to layer = `user_behavior`.** Now you see the items, the
   wishlist (empty in the seed), and the favorite stores (empty in
   the seed). Node sizes show what the user actually does.
3. **Click on `pack:color-coordination-rules`** in the sidebar.
   Follow `CONTAINS_RULE` → one of the color rules → `EVALUATES`
   → a `SkinTonePalette`. That's a literal traversal of the chain
   the runtime engine walks at Step 7.
4. **Switch layout to hierarchical top-down.** Read top-to-bottom.
   This is the agent's reasoning architecture at a glance.
5. **Spotlight User neighborhood.** See exactly what's in the
   agent's context for any decision.

## How this enables RAG and an LLM shopping agent

The graph is **structured context**. Three observable consequences:

### RAG over the Intelligent Book

When a future LLM layer takes a question like *"Why does this dress
work for my profile?"*, a retrieval pipeline walks the graph:

1. Start at the dress's `WardrobeItem` node.
2. Walk one hop to `WardrobeItemType`, `ColorFamily`, and
   `SUITABLE_FOR` occasion(s).
3. Follow `USES_RULE` to the rule packs that govern those
   contexts.
4. Retrieve the **book chapters keyed off the rule slugs** the agent
   already emits in its reasoning trail.

The LLM gets a **compact subgraph + the relevant book passages**.
The retrieval is *along graph edges*, not vector embeddings of free
text — so the explanation cites the same rule the runtime agent
would.

### LLM shopping agent over favorite stores

When a `WardrobeGap` is detected at runtime, the LLM shopping agent:

1. Reads the gap's connected `WardrobeItemType` and `OccasionType`.
2. Walks the user's `HAS_SKIN_TONE` edge for the target palette and
   `HAS_PROFILE` edge for the silhouette.
3. Visits each `FavoriteStore` node and queries that store's
   catalog with the graph-derived constraints (type + color family
   + occasion).
4. Scores any candidate against the same rule packs the runtime
   engine uses (`color#R*`, `fit#R*`, `occasion#R*`).

**The rule engine stays the safety + scoring substrate.** The LLM
becomes the *discovery* layer — but its output is auditable against
the same graph the user's reasoning trail traces through.

### Structure beats prompts

- **Compact**: this whole graph is ~50 KB. The equivalent flat-text
  description of the rule packs + wardrobe + history + occasion table
  is an order of magnitude larger.
- **Queryable**: filtering by `layer`, `type`, or `metric` returns a
  precise subgraph. The LLM doesn't have to vector-search the entire
  book.
- **Auditable**: every edge has a typed `from` → `to` → `type`. The
  citation chain is *literally a graph traversal*.

That's the property the SEIS 666 class kept returning to: structured
knowledge guides the LLM. Wearly's three graphs (Learning, Reasoning,
Knowledge) are three angles on the same body of structured knowledge.

## Linked concept

- *Schema reference:* [`graph/wearly-knowledge-graph-schema.md`](../../../graph/wearly-knowledge-graph-schema.md).
- *Data file:* [`graph/wearly-knowledge-graph.json`](../../../graph/wearly-knowledge-graph.json).
- *Generator:* [`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py) — re-run after wardrobe/history changes.

---

## See also

- **[Learning Graph](../learning-graph/index.md)** — the *reader's* concept DAG (28 concepts, 39 prerequisite edges, Bloom-tagged).
- **[Reasoning Graph](../knowledge-graph/index.md)** — the runtime *per-recommendation* entity model.
- **[Skill package overview](../../../skills/wearly-styling-agent/SKILL.md)** — the eight rule packs the Knowledge Graph models as `RulePack` nodes.
- **[Evidence & references](../../../docs/evidence-and-references.md)** — what informs the rules every `Rule` node represents.
