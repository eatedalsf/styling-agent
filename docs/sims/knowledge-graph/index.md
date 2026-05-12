# Knowledge graph

> **What you're looking at.** An interactive view of Wearly's *runtime* knowledge graph — the entities the agent reasons over (users, fit profiles, calendar events, weather snapshots, wardrobe items, outfit recommendations, gaps, shopping suggestions, feedback) and the relations between them. Each node is an entity instance; each edge is a typed relation drawn from `graph/schema.md`.
>
> **This is different from the [Learning Graph](../learning-graph/index.md).** The learning graph models the *reader's* path through the Intelligent Book — concepts plus prerequisites. This one models the *agent's* data world at runtime. Same library (vis-network.js), different question.

<iframe
  src="main.html"
  width="100%"
  height="700"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Knowledge Graph">
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
| **Entity-type dropdown** | Limits the visible nodes to one entity type (e.g., only `WardrobeItem`s, only `OutfitRecommendation`s). |
| **Layout dropdown** | Switch between physics-based (force-directed) and hierarchical (left-to-right) layouts. The hierarchical layout makes provenance chains — *event → recommendation → items* — easier to follow. |
| **Reset view** | Clears every filter and re-fits the graph. |

## Entity vocabulary

The nine entity types come from [`graph/schema.md`](../../../graph/schema.md) and are styled with distinct shapes so the type is legible even when labels are short:

- **User** — the wardrobe owner; the root of every reasoning chain.
- **FitProfile** — declared silhouette and comfort preferences (never image-derived; see [`book/06-fit-profile-logic.md`](../../../book/06-fit-profile-logic.md)).
- **CalendarEvent** — a planned occasion, mapped to one of the five canonical occasion tags.
- **WeatherSnapshot** — a temperature/precip/wind reading, live or fallback.
- **WardrobeItem** — a clothing item with type, color, formality, season, tags.
- **OutfitRecommendation** — a built outfit, the agent's output for one occasion.
- **WardrobeGap** — a missing required-piece type detected by Step 6.
- **ShoppingSuggestion** — a descriptive (non-promotional) gap remedy, optionally tagged to a favorite store.
- **Feedback** — a `rejected_ids` + `rejection_reasons` pair that drives a regenerate cycle.

## Relations

Edges are drawn from the schema's relation vocabulary — *has-profile*, *plans*, *contains*, *recommends*, *evaluated-against*, *gap-of*, *suggests*, *rejects*. The hierarchical layout reveals the natural flow: **User → CalendarEvent → OutfitRecommendation → WardrobeItem**, with WeatherSnapshot and FitProfile feeding into the recommendation and ShoppingSuggestion / Feedback fanning out from it.

## Data source

The graph is generated from `graph/graph.json` at the repo root. To extend it, edit that file and add new entries under `entities` (with `id`, `type`, `label`) plus typed `relations`. The viewer picks up changes on the next site build.

This view is rendered by [vis-network.js](https://visjs.github.io/vis-network/docs/network/) — the same library the Streamlit app uses (via pyvis) to draw the live-run reasoning graph after every outfit recommendation.

## See also

- **[`graph/schema.md`](../../../graph/schema.md)** — canonical text description of entities and relations.
- **[`graph/render.md`](../../../graph/render.md)** — static Mermaid diagram of the schema.
- **[Learning Graph](../learning-graph/index.md)** — the *reader's* concept DAG, distinct from this runtime view.
- **[`book/05-wardrobe-intelligence.md`](../../../book/05-wardrobe-intelligence.md)** — how `WardrobeItem` entities are built from raw closet input.
