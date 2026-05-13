# Wearly micro-simulations

> Small, focused interactive widgets that let you **touch the math** behind Wearly's reasoning. Each sim is one rule, surfaced visually, with the controls you'd want to play with. No new dependencies — every sim is plain HTML / CSS / `vis-network.js` or `p5.js`.

Pattern borrowed from [`dmccreary/intelligent-textbooks`](https://dmccreary.github.io/intelligent-textbooks/) and the [SEIS 666 MicroSims index](https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/sims/) — an Intelligent Book isn't just chapters; it's chapters wired up to interactive demos that make the reasoning concrete.

---

## Available sims

### 🎨 Color harmony

[Open the sim →](color-harmony/index.md)

A p5.js micro-sim. Pick a skin tone (warm olive, cool fair, deep warm), then move sliders for two outfit colors. The score updates live using the same `+8 / +4 / −10` rule pack the agent applies in **Step 7 (Color Coordination Check)**.

**What it teaches:** color harmony isn't a black box — it's three palettes and a small additive scoring function. Reading the sim is reading the rule.

---

### 🕸 Knowledge graph

[Open the sim →](knowledge-graph/index.md)

The full `vis-network.js` schema graph from `graph/graph.json` — 9 entity types, 14 relations. Drag nodes, hover for tooltips, zoom freely.

**What it teaches:** Wearly reasons across *connected* context (calendar → weather → wardrobe → outfit), not from raw prompts. The interactive graph is the same shape the live-run reasoning graph takes per outfit; the schema view shows the abstract model the runs traverse.

---

### 🗺️ Learning graph

[Open the sim →](learning-graph/index.md)

A directed acyclic graph of the concepts a reader must understand to grasp Wearly. 28 nodes / 39 edges, color-coded by Bloom level + topic category. Click a node to see its summary, **prerequisites** (read first), **dependents** (what it unlocks), and a deep link into the book.

**What it teaches:** there's a learning path through Wearly, not a flat reference. The graph viewer lets you follow that path top-down, left-right, or by clicking through the dependency chain.

---

### ⏳ Wear-history freshness *(new)*

[Open the sim →](freshness/index.md)

A live calculator for the freshness tie-breaker in `history_tool.get_freshness`. Drag two sliders — wear count and days since last worn — and see the score update according to the rule pack:

```
score = 1.0
       − 0.25 × min(worn_count, 4) / 4    # frequency penalty
       − 0.25 if days_since_last < 3      # recency penalty
       (clamped to [0.40, 1.00])
```

**What it teaches:** wear history is a *tie-breaker, never a filter*. A heavily-worn favorite never gets exiled below 0.40, and a fresh alternative wins when the two are otherwise equally eligible. The sim makes the floor and the penalty bands visible.

---

## How sims are made

Each sim is one HTML file under `docs/sims/<sim-name>/` plus a one-page `index.md` that frames it. The viewer is embedded via `<iframe>`. No build step, no JS bundler, no React. Plain DOM + a small CDN-loaded library (`vis-network` for graphs, `p5` for color sims). That makes every sim:

- **Inspectable.** Right-click → view source. The code IS the documentation.
- **Self-contained.** Each sim works without the rest of the site.
- **Reusable.** Drop the HTML into any other Markdown viewer and it still works.

The structure mirrors `dmccreary/intelligent-textbooks` and the SEIS 666 course book.
