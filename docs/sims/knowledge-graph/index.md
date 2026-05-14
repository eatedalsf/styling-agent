# Reasoning graph *(runtime entity model)*

> **Learning objective.** After working through this sim, you will be
> able to name the nine entity types Wearly's agent reasons over and
> trace a complete chain from `User → CalendarEvent →
> OutfitRecommendation → WardrobeItem` — and distinguish this
> *runtime* graph from the [Learning Graph](../learning-graph/index.md)
> that maps the reader's path through the book.
>
> **What you're looking at.** An interactive view of Wearly's runtime
> entity graph — the things the agent reasons over (users, fit
> profiles, calendar events, weather snapshots, wardrobe items, outfit
> recommendations, gaps, shopping suggestions, feedback) and the
> typed relations between them. Each node is an entity instance; each
> edge is a typed relation drawn from
> [`graph/schema.md`](../../../graph/schema.md).
>
> **Why we renamed it.** Earlier drafts called this the "Knowledge
> Graph." McCreary's textbook framework uses *knowledge graph* and
> *concept graph* interchangeably for the *reader's* concept DAG, so
> we now call this one the **Reasoning Graph** to avoid confusion.
> File paths and the underlying JSON are unchanged; only the display
> name changed.

<iframe
  src="main.html"
  width="100%"
  height="700"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Reasoning Graph (runtime entity model)">
</iframe>

---

## How to use the graph

| Interaction | What it does |
|---|---|
| **Click a node** | Loads the entity type and label into the sidebar, so you can see what kind of thing it is and how it's named. |
| **Double-click a node** | Centers the view on that node so you can read its neighbors. |
| **Drag a node** | Rearranges the local layout — useful when nodes overlap. |
| **Scroll** | Zooms in / out. |
| **Search box** | Filters nodes by label. |
| **Entity-type dropdown** | Limits the visible nodes to one entity type (for example, only `WardrobeItem`s, or only `OutfitRecommendation`s). |
| **Layout dropdown** | Switch between physics-based (force-directed) and hierarchical (left-to-right) layouts. The hierarchical layout makes provenance chains — *event → recommendation → items* — easier to follow. |
| **Reset view** | Clears every filter and re-fits the graph. |

## Entity vocabulary

The nine entity types come from [`graph/schema.md`](../../../graph/schema.md)
and are styled with distinct shapes so the type is legible even when
labels are short:

- **User** — the wardrobe owner; the root of every reasoning chain.
- **FitProfile** — declared silhouette and comfort preferences (never
  image-derived; see
  [`book/06-fit-profile-logic.md`](../../../book/06-fit-profile-logic.md)).
- **CalendarEvent** — a planned occasion, mapped to one of the five
  canonical occasion tags.
- **WeatherSnapshot** — a temperature / precipitation / wind reading,
  live or fallback.
- **WardrobeItem** — a clothing item with type, color, formality,
  season, and tags.
- **OutfitRecommendation** — a built outfit, the agent's output for
  one occasion.
- **WardrobeGap** — a missing required-piece type detected by Step 6.
- **ShoppingSuggestion** — a descriptive (never promotional) gap
  remedy, optionally tagged to a favorite store.
- **Feedback** — a `rejected_ids` + `rejection_reasons` pair that
  drives a regenerate cycle.

## Relations

Edges are drawn from the schema's relation vocabulary —
*has-profile*, *plans*, *contains*, *recommends*, *evaluated-against*,
*gap-of*, *suggests*, *rejects*. The hierarchical layout reveals the
natural flow: **User → CalendarEvent → OutfitRecommendation →
WardrobeItem**, with WeatherSnapshot and FitProfile feeding into the
recommendation and ShoppingSuggestion / Feedback fanning out from it.

## Data source

The graph is generated from `graph/graph.json` at the repo root. To
extend it, edit that file and add new entries under `entities` (with
`id`, `type`, `label`) plus typed `relations`. The viewer picks up
changes on the next site build.

This view is rendered by
[vis-network.js](https://visjs.github.io/vis-network/docs/network/) —
the same library the Streamlit app uses (via pyvis) to draw the
live-run reasoning graph after every outfit recommendation.

---

## What to notice

- **Every chain starts at a `User`.** Drag the layout to *hierarchical*
  and the structure becomes one tree per user, not a free-form graph.
- **`FitProfile` and `WeatherSnapshot` are *sources*, not children.**
  They feed into `OutfitRecommendation`; nothing in the graph reads
  *from* a recommendation back into them.
- **`Feedback` is the loop-closer.** It's the only relation type that
  flows *backward* — rejecting an outfit creates a `Feedback` node
  that the next recommendation reads as input. That's the "agentic"
  shape of the data.

## Try this

1. **Filter to *OutfitRecommendation* only.**
   **What you should see:** a small set of nodes with no edges drawn
   — recommendations don't connect to each other directly, only to
   their inputs and outputs.
2. **Filter to *WardrobeItem* only.**
   **What you should see:** the largest node group; these are the
   leaves the agent assembles into outfits.
3. **Switch to the hierarchical layout and read top-to-bottom.**
   **What you should see:** the seven-step workflow shape becomes
   visible: context → recommendation → items + gaps + feedback.

## Self-check

1. *(Remember)* List the nine entity types in the Wearly reasoning
   graph.
2. *(Understand)* Why is this called the *Reasoning Graph* rather than
   the *Knowledge Graph*?
3. *(Apply)* A user rejects a recommended outfit. Trace which entities
   are created or updated and which relations are added to the graph.

## Linked concept

- *Learning-graph concept:* **[knowledge graph schema](../learning-graph/index.md)**
  (id `knowledge-graph-schema`, Bloom level *Analyze*).
- *Rule citation:* `[wardrobe-filtering-rules#R3]` — see
  [`wardrobe-filtering-rules.md`](../../../skills/wearly-styling-agent/wardrobe-filtering-rules.md).
  *Note:* the graph itself is a data model rather than a rule; the
  rule cited here is the one that consumes the graph at Step 4.

---

## See also

- **[`graph/schema.md`](../../../graph/schema.md)** — canonical text
  description of entities and relations.
- **[`graph/render.md`](../../../graph/render.md)** — static Mermaid
  diagram of the schema.
- **[Learning Graph](../learning-graph/index.md)** — the *reader's*
  concept DAG, distinct from this runtime view.
- **[`book/05-wardrobe-intelligence.md`](../../../book/05-wardrobe-intelligence.md)** —
  how `WardrobeItem` entities are built from raw closet input.
