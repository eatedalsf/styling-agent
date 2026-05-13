# Knowledge Graphs in Wearly — a Dan-McCreary-style FAQ

This page answers every question Dan McCreary asked Leah about her knowledge
graph, applied to Wearly. It catalogs each graph the project ships, what the
visuals encode, what library renders them, and how each graph connects to the
agent's reasoning.

> **TL;DR.** Wearly ships **four** graphs. They share one schema and one
> visual language. Every graph has explicit color, size, edge, and layout
> conventions documented below and surfaced as an in-app legend block.

---

## 1. What graphs does Wearly have?

| # | Graph | Lives in | Purpose | Rendered by |
|---|---|---|---|---|
| 1 | **Schema graph** | `graph/graph.json`, `graph/schema.md` | The static abstract model: 9 entity types, 14 relations. Tells reviewers *how* Wearly thinks. | `pyvis` → `vis-network.js`, embedded in the **Before / After** section of the app, and as a Mermaid diagram in `graph/render.md`. |
| 2 | **Live-run reasoning graph** | `graph_tool.render_run_graph_html(result)` | A per-run instance: the actual `User → CalendarEvent → Weather → Outfit → WardrobeItem` traversal that produced *this* outfit, with gaps and rejections visible. | `pyvis` → `vis-network.js`, embedded inside every outfit-result expander. |
| 3 | **Learning graph** | `graph/learning-graph.json`, `docs/sims/learning-graph/` | A DAG of *concepts a reader must understand* to grasp Wearly. Distinct from #1 (which models runtime data); this models the reader's mental path. Inspired by [Dan's classmate Yarmoluk's learning graph](https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/learning-graph/). | Static HTML using `vis-network.js` directly (no Python), hosted via GitHub Pages. |
| 4 | **Compact knowledge-graph export** | `compact_kg.build_compact_kg(result)` | A portable JSON serialization of any single run, using the same vocabulary as the schema graph. Useful for offline analysis, replaying, or pasting into a Neo4j shell if anyone wants to do that. | No render — it's data. Downloadable from each outfit result. |

The three rendered graphs share a single legend (below). The compact-KG export
follows the same vocabulary so it drops into the in-book viewer untranslated.

---

## 2. What graph library and why?

**Library:** [`pyvis`](https://pyvis.readthedocs.io/) — a small Python wrapper
around [`vis-network.js`](https://visjs.github.io/vis-network/).

**Why pyvis (and not Neo4j):**

- **No daemon.** The whole demo runs offline on Streamlit Cloud / a laptop /
  Wi-Fi-free room. Neo4j needs a running database, an auth surface, and a
  backup story for tens of nodes.
- **No external services.** Pyvis bundles the JS inline
  (`cdn_resources="in_line"`), so the HTML is self-contained.
- **Right scale.** Both rendered graphs sit at 10–25 nodes (live run) or
  ~25 nodes (schema). A graph database is the wrong tool at that scale —
  the data fits in two JSON files.
- **One-page reviewability.** A reviewer can read the entity catalog in
  `schema.md` in 60 seconds. With Neo4j the schema would live in Cypher
  constraints + APOC procedures + Python migrations — much harder to audit.
- **Reuse for free.** vis-network.js is also what the learning graph uses,
  so a single visual vocabulary covers all three rendered graphs.

The trade-off: pyvis doesn't give us multi-user query, indexing, or
ACID transactions. We don't need any of those — the graph is materialized
on each run from JSON.

---

## 3. What does **node size** mean?

This was the question Dan asked first and Wearly should answer first.

| Node type | Diameter rule | Why |
|---|---|---|
| `User` | Fixed 32 px | The visual anchor. Always the same so the graph orients consistently. |
| `OutfitRecommendation` | `22 + 2 × piece_count` (clamped 22..44 px) | A 1-piece dress looks small; a 6-piece outfit with outerwear + accessories looks visibly bigger. Size = "how many decisions did Wearly make this run?" |
| `WardrobeItem` | `18 + 2 × worn_count` (clamped 18..30 px) | Heavy-rotation pieces grow. Geometry encodes the same wear-history signal Wearly uses as a freshness tie-breaker. At a glance: which items are you reaching for? |
| `CalendarEvent` / `FitProfile` / `WeatherSnapshot` | Fixed by role (22–26 px) | Context nodes — they're not the centerpiece, they shouldn't compete with it. |
| `WardrobeGap` / `ShoppingSuggestion` / `Feedback` | Smaller (18–22 px) | Derived nodes. Smaller means "consequence", not "input". |

The hover tooltip on each `WardrobeItem` explicitly states `"Worn: N times
(node size encodes this)"` so the rule isn't hidden.

---

## 4. What do **node colors** mean?

| Role | Color | Meaning |
|---|---|---|
| `User` | matte black | The wearer. Anchor. |
| `FitProfile`, `CalendarEvent`, `WeatherSnapshot` | warm cream | User context (declared / external). |
| `WardrobeItem` | soft tan | A garment / shoe / accessory. |
| `OutfitRecommendation` | white with bold black border | The centerpiece. Always the most prominent shape (a diamond, not a dot). |
| `WardrobeGap`, `ShoppingSuggestion` | warm pink | A gap or what to buy. Distinct color so it reads as "something to address". |
| `Feedback` | muted tan | User reject/regenerate signal. |

Colors are stable across the schema graph and live-run graph so a
reviewer learns the language once. The palette is defined in
`graph_tool._PALETTE` and exposed as `LEGEND_DICT["node_color_meaning"]`.

---

## 5. What do **edge labels** mean?

Every edge is directed (`source → target`) and labeled with a snake_case
predicate from the canonical schema in `graph/schema.md`. The common ones:

| Edge label | Reads as |
|---|---|
| `has_fit_profile` | User → FitProfile |
| `has_event` | User → CalendarEvent |
| `sees_weather` | User → WeatherSnapshot |
| `addresses_event` | OutfitRecommendation → CalendarEvent |
| `recommends` | OutfitRecommendation → WardrobeItem |
| `informs` | FitProfile / Weather → OutfitRecommendation |
| `flags_gap` | OutfitRecommendation → WardrobeGap |
| `suggests_to_buy` | WardrobeGap → ShoppingSuggestion |
| `was_rejected_with` | WardrobeItem → Feedback |
| `excludes_from_pool` | Feedback → WardrobeItem (next run) |

The exported compact-KG JSON uses the **same** predicate vocabulary so an
external viewer needs no translation table.

---

## 6. What layout do the graphs use?

All three rendered graphs use **force-directed** layout, specifically
`forceAtlas2Based` (a vis-network solver). Key parameters:

```
gravitationalConstant: -110     (stronger repulsion = less crowding)
centralGravity:         0.02    (mild pull toward the center)
springLength:           170     (longer springs = clearer edges)
damping:                0.7     (settles fast, doesn't drift)
avoidOverlap:           0.85    (nodes give each other room)
stabilization:          enabled, 320 iterations
```

**Interaction.** Drag any node to reposition; the spring settles in ~0.5 s.
Scroll to zoom, drag the background to pan. Hover over a node to see its
tooltip (color, type, worn-count, formality, etc.).

We chose `forceAtlas2Based` over `barnesHut` because the medium-sized graphs
Wearly renders (10–25 nodes) look twitchy under barnesHut at default
parameters. ForceAtlas2 is calmer and converges faster.

A hierarchical layout (top-down trees) was considered and rejected: the
graph has multiple roots (User, OutfitRecommendation, WardrobeGap) and
cross-cutting edges (`informs`), so a tree layout misrepresents the
relationships.

---

## 7. Are tooltips / labels clear?

Every node renders:
- A short visible label (capped at 28 chars so they don't overlap),
- A multi-line tooltip on hover including type, color, formality,
  worn-count, and for user-added items, a "Source: your wardrobe
  additions" line.

Every edge renders its predicate as a label, with a white stroke under the
text so it reads cleanly against the canvas.

The in-app **legend expander** (under both the schema graph and the live-run
graph) is the new addition from this review: it lists library, layout,
node-size rule, node-color table, edge-label table, and a paragraph on how
the graph maps to the agent's reasoning trail.

---

## 8. Does the graph support date / event filtering?

**The live-run graph is intrinsically scoped to one event.** Each invocation
of `run_agent()` produces one result; the graph renders that result. There's
no time window to filter — the moment IS the scope.

**For multi-run analysis,** the compact-KG export carries
`meta.generated_at`. Multiple exports can be loaded together in any external
tool that consumes the JSON.

**The Planner screen** is where "across many events" lives — but it shows a
list of cards, not a combined graph. We deliberately don't try to merge N
runs into one graph because the visual would crowd past readability.

If you want a "show me my wardrobe across the last month" view, that
belongs in the wardrobe analytics direction, not the per-run reasoning
graph. We have one structured-query helper today (next section).

---

## 9. Can users ask structured questions of the graph?

Yes — **"Ask your wardrobe"** is the structured-query surface, sitting next
to the wardrobe in the app. It does pure traversal over the same data the
agent reasons over, not text search:

| Pre-baked query | What it does | Citation |
|---|---|---|
| Worn 30+ days ago | items with `worn_count == 0` or `days_since_last_worn ≥ 30` | `history#R4` |
| Most-loved pieces | top-N by `worn_count` | `history#R2` |
| Wardrobe shape | distribution of items by `type` | `wardrobe#R3` |
| Work-ready pieces | `filter_items_by_occasion("work")` | `wardrobe#R3` |
| Casual-ready pieces | `filter_items_by_occasion("casual")` | `wardrobe#R3` |

A new helper added during this overnight pass, `wardrobe_query.infer_wishlist_taste()`,
also traverses the wishlist deterministically to produce a body-positive
taste summary the agent uses both at selection time and in the reasoning trail.

Everything is rule-based and explainable. No LLM call.

---

## 10. Is the graph search structured or text-based?

**Structured.** Every query operates over typed nodes and typed edges. A
"Most-loved pieces" query walks `WardrobeItem` nodes filtered by their
`worn_count` attribute; it doesn't grep "loved" in free text. The same is
true of `filter_items_by_occasion` (typed `tags` + `season`) and of the
agent's outfit construction itself.

---

## 11. Is the graph too crowded?

The Goal-10 overnight pass dropped the redundant `User → owns → Item`
edges that turned the live-run graph into a starburst. The graph now
follows a single directed flow:

```
User → has_event → Event ← addresses_event ← Outfit → recommends → [items]
User → sees_weather → Weather → informs → Outfit
User → has_fit_profile → FitProfile → informs → Outfit
```

with `flags_gap` and `was_rejected_with` peeling off only when those
edges apply. For a typical 5-item outfit this is ~9 edges, well within
readable density.

The schema graph caps at 25 nodes; the learning graph at 28. Both
forceAtlas2 layouts have been retuned to give plenty of breathing room.

---

## 12. How does each graph help the user?

- **Schema graph** — tells a reviewer in one image *what kind of system
  Wearly is*: agent vs chatbot, structured vs free-text. Lives on the
  Before/After page.
- **Live-run reasoning graph** — turns the seven prose-form reasoning
  steps into a single picture. The user can see at a glance which
  context the agent read, which pieces it chose, which it rejected, and
  what's still missing. Wear-count is encoded geometrically, so a
  recurring "I keep wearing the same blouse" pattern is visible without
  reading the trail.
- **Learning graph** — the reader's path through the project's
  concepts, organized by Bloom's taxonomy. Lives in the book.
- **Compact-KG export** — for the user who wants the data after the
  run. Saves as a JSON file; the in-book vis-network viewer renders it
  with no translation.

---

## 13. Why not Neo4j?

Already answered in §2, but worth being blunt about: Neo4j is great when
you have millions of nodes, multi-user concurrent writes, and a security
boundary worth running a daemon for. Wearly has none of those. The graph
is a 10–25-node materialization per outfit, regenerated from JSON each
run, served from a Streamlit app that has to start cold in ~10 s on a
free-tier container. Pyvis fits the constraints exactly.

If the project ever grows to multi-user, persistent, multi-day analytics,
Neo4j is back on the table — the schema vocabulary already in
`graph/schema.md` translates 1-1 to Cypher.

---

## 14. How does the graph connect to the agent's reasoning?

Every node in the live-run graph corresponds to a value the agent
actually computed during `run_agent()`:

| Reasoning trail line | Graph counterpart |
|---|---|
| Step 1: "Found 'Movie' on 2026-05-15" | `CalendarEvent: Movie` node + `has_event` edge from User |
| Step 2: "Owner: Eatedal · warm olive · classic" | `FitProfile` node + `informs` edge to Outfit |
| Step 3: "Minneapolis: 58°F, partly cloudy" | `WeatherSnapshot` node + `informs` edge to Outfit |
| Step 4: "Found 8 clothing items for occasion: casual in spring" | Determines the pool the next graph nodes come from |
| Step 5: "Selected '...' as a one-piece solution" | `recommends` edges from Outfit to each picked `WardrobeItem` |
| Step 6: "Your wardrobe is missing: outerwear" | `WardrobeGap` node + `flags_gap` edge |
| Step 7: "Color score 84/100 for skin tone 'warm olive'" | Goes into the `color_score` attribute on the Outfit node's tooltip |

The two views — prose trail and shape graph — describe the same run from
two angles. The prose explains *why*; the graph explains *how it's
connected*.

---

## 15. Where can I see this in the app?

- Schema graph + legend → **Before / After** screen.
- Live-run graph + legend → **Today** screen, inside the
  "Reasoning graph — how this outfit emerged" expander on every result.
- Learning graph → the [Intelligent Book](https://eatedalsf.github.io/styling-agent/).
- Compact-KG export → download button on every Today / Planner result.

---

## Source of truth

- Schema vocabulary: `graph/schema.md`
- Rendering code + legend dict: `graph_tool.py`
- Compact KG serializer: `compact_kg.py`
- Wardrobe queries: `wardrobe_query.py`
- This FAQ: `docs/knowledge-graph-faq.md`
