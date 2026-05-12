# Learning graph

> **What you're looking at.** A directed acyclic graph of the concepts a reader needs to understand to fully grasp Wearly. Each node is a concept (with a one-sentence summary, a Bloom-taxonomy level, and a link into the book). Each edge is a prerequisite: "you should understand A before you can fully understand B."
>
> **This is different from `graph/schema.md`.** That graph models *wardrobe items + outfits at runtime*. This one models *the reader's path through the Intelligent Book*. Both are vis-network.js graphs, both are interactive, but they answer different questions.

<iframe
  src="main.html"
  width="100%"
  height="700"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Learning Graph">
</iframe>

---

## How to use the graph

| Interaction | What it does |
|---|---|
| **Click a node** | Loads its summary, Bloom level, and a deep link to the relevant book chapter into the sidebar. |
| **Double-click a node** | Centers the view on that node so you can read its neighbors. |
| **Drag a node** | Rearranges the local layout — useful when nodes overlap. |
| **Scroll** | Zooms in / out. |
| **Search box** | Filters nodes by label or summary text. |
| **Category dropdown** | Limits the visible nodes to one of six categories. |
| **Bloom-level dropdown** | Limits the visible nodes to one cognitive tier (Remember / Understand / Apply / Analyze). |
| **Layout dropdown** | Switch between physics-based (force-directed) and hierarchical (top-down DAG) layouts. The hierarchical layout makes prerequisite chains easier to read top-to-bottom. |
| **Reset view** | Clears every filter and re-fits the graph. |

## Reading paths through Wearly

The graph supports several reading paths. Try filtering to one category at a time:

- **Foundation** → start here. Two concepts: the user problem and the agent-vs-chatbot framing.
- **Workflow** → the seven steps of the agent, each step linked to its rule pack.
- **Knowledge** → the rule systems and data models the agent reasons over (wardrobe model, color harmony, required pieces).
- **Personalization** → how the agent learns about the user (fit profile, wear history, reject & regenerate, favorite stores).
- **Framing** → the honesty contract, body-positive language, evidence categories, privacy stance.
- **System** → the architectural concepts (result-dict contract, knowledge-graph schema, live-run graph, skill package).

## Bloom levels

Following the convention used by the [dmccreary intelligent-textbooks](https://github.com/dmccreary/intelligent-textbooks) template, each concept carries a Bloom cognitive-tier label:

- **Remember** — recognize or recall the concept (e.g., the five canonical occasion tags).
- **Understand** — explain the concept in your own words (e.g., the agent-vs-chatbot framing).
- **Apply** — use the concept correctly in a new context (e.g., evaluating an outfit against the gap rules).
- **Analyze** — break the concept down into its parts and see how they interact (e.g., why the freshness floor is 0.4 rather than 0).

## Data source

The graph is generated from `graph/learning-graph.json` at the repo root. To add a concept, edit that file and add a new entry under `concepts` (with `id`, `label`, `category`, `bloom`, `url`, `summary`) plus one or more `edges` declaring its prerequisites. The viewer picks up changes on the next site build.

This learning graph is rendered by [vis-network.js](https://visjs.github.io/vis-network/docs/network/) — the same library that powers the runtime knowledge graph in the Streamlit app and the course-level learning graph at [yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026](https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/learning-graph/).

## See also

- **[`graph/schema.md`](../../../graph/schema.md)** — the runtime knowledge graph schema (entities + relations, not concepts + prerequisites).
- **[`book/12-evidence-and-references.md`](../../../book/12-evidence-and-references.md)** — what informs Wearly's reasoning.
- **[`docs/evidence-and-references.md`](../../../docs/evidence-and-references.md)** — the canonical references doc.
- **[Source repo `docs/sims/` directory](https://github.com/eatedalsf/styling-agent/tree/main/docs/sims)** — other interactive sims live alongside this one.
