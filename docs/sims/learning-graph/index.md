# Learning graph

> **Learning objective.** After working through this graph, you will
> be able to navigate the Wearly book by prerequisite order, identify
> which concepts an unfamiliar idea depends on, and explain how
> Bloom's-taxonomy tags scaffold the reading path from *Remember*
> through *Analyze*.
>
> **What you're looking at.** A directed acyclic graph of the 28
> concepts a reader needs to understand to grasp Wearly. Each node is
> a concept (with a one-sentence summary, a Bloom-taxonomy level, and
> a link into the book). Each edge is a prerequisite: *"you should
> understand A before you can fully understand B."*
>
> **This is different from the [Reasoning Graph](../knowledge-graph/index.md).**
> That graph models *wardrobe items + outfits at runtime* — the
> agent's data world. This graph models *the reader's path through
> the Intelligent Book*. Both use vis-network.js; both are interactive;
> they answer different questions.

<iframe
  src="main.html"
  width="100%"
  height="780"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Learning Graph">
</iframe>

---

## How this graph is built

The DAG is hand-curated, not learned. Every node carries:

- a stable `id` (used by cross-links from chapter pages and sims),
- a one-sentence `summary` (what the concept *means*),
- a `category` (Foundation, Workflow, Knowledge, Personalization,
  Framing, System) for color coding,
- a Bloom level (`Remember`, `Understand`, `Apply`, `Analyze`) that
  scaffolds reading difficulty,
- a `url` deep-linking to the chapter or rule file that introduces it.

Every edge is a prerequisite, read as *"you should understand A
before B."* The graph is acyclic by construction; a documentation
test would catch any cycle a future contributor introduced.

The default layout is **hierarchical top-down** because that's the
layout that *teaches* the prerequisite chain. Switch to physics
(force-directed) for an organic view when you want to see clusters
rather than order.

## How to use the graph

| Interaction | What it does |
|---|---|
| **Click a node** | Loads its summary, Bloom level, prerequisites, dependents, and a deep link to the relevant book chapter into the sidebar. |
| **Double-click a node** | Centers the view on that node so you can read its neighbors. |
| **Drag a node** | Rearranges the local layout — useful when nodes overlap. |
| **Scroll** | Zooms in / out. |
| **Search box** | Filters nodes by label or summary text. |
| **Category dropdown** | Limits the visible nodes to one of six categories. |
| **Bloom-level dropdown** | Limits the visible nodes to one cognitive tier (Remember / Understand / Apply / Analyze). |
| **Layout dropdown** | Switch between hierarchical top-down (default), hierarchical left-to-right, and physics. |
| **Suggested reading path** | Highlights one canonical chain through the graph — see below. |
| **Reset view** | Clears every filter and re-fits the graph. |

## Reading paths through Wearly

Filter to one category at a time:

- **Foundation** → start here. The user problem and the
  agent-vs-chatbot framing.
- **Workflow** → the seven steps, each step linked to its rule pack.
- **Knowledge** → the rule systems and data models the agent reasons
  over (wardrobe model, color harmony, required pieces).
- **Personalization** → how the agent learns about the user (fit
  profile, wear history, reject & regenerate, favorite stores).
- **Framing** → the honesty contract, body-positive language,
  evidence categories, privacy stance.
- **System** → the architectural concepts (result-dict contract,
  knowledge-graph schema, live-run graph, skill package).

The **Suggested reading path** button surfaces one canonical chain a
first-time reader can follow end-to-end: *personal styling problem →
agent vs. chatbot → seven-step workflow → outfit construction →
result-dict contract.*

## Bloom levels

Following the convention used by the
[dmccreary intelligent-textbooks](https://github.com/dmccreary/intelligent-textbooks)
template, each concept carries a Bloom cognitive-tier label:

- **Remember** — recognize or recall the concept (for example, the
  five canonical occasion tags).
- **Understand** — explain the concept in your own words (for
  example, the agent-vs-chatbot framing).
- **Apply** — use the concept correctly in a new context (for
  example, evaluating an outfit against the gap rules).
- **Analyze** — break the concept into its parts and see how they
  interact (for example, why the freshness floor is 0.4 rather than 0).

## Data source

The graph is generated from `graph/learning-graph.json` at the repo
root. To add a concept, edit that file and add a new entry under
`concepts` (with `id`, `label`, `category`, `bloom`, `url`, `summary`)
plus one or more `edges` declaring its prerequisites. The viewer picks
up changes on the next site build.

This learning graph is rendered by
[vis-network.js](https://visjs.github.io/vis-network/docs/network/) —
the same library that powers the runtime Reasoning Graph in the
Streamlit app and the course-level learning graph at
[yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026](https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/learning-graph/).

---

## What to notice

- **The Foundation category sits at the top.** Hierarchical layout
  pushes prerequisite-free concepts upward; if a concept floats high,
  it depends on little else.
- **The seven-step workflow is the densest hub.** It has the most
  outgoing edges — the agent's spine teaches almost everything else.
- **Framing concepts cross-cut the rest.** The honesty contract and
  body-positive language sit on the side and connect across categories
  rather than within one — they're constraints, not steps.

## Try this

1. **Click *seven-step-workflow*.**
   **What you should see:** a long list of *Dependents* in the
   sidebar — every step of the agent's logic depends on this concept.
2. **Filter by Bloom level *Remember*.**
   **What you should see:** a small set of foundational facts —
   what you'd want to memorize before reading the rest. Most
   concepts are *Understand* or higher.
3. **Click *freshness-score* (Analyze).** Read its prerequisites in
   the sidebar.
   **What you should see:** *wear-history* shows up as a prerequisite.
   You can't analyze the floor without understanding the inputs first.
4. **Click *Suggested reading path*.**
   **What you should see:** five concepts highlighted in order;
   everything else dims to background. *Clear path* restores the
   full graph.

## Self-check

1. *(Remember)* What are the six categories used to color-code the
   learning graph?
2. *(Understand)* Why is the default layout hierarchical top-down
   rather than force-directed?
3. *(Apply)* Pick a concept tagged *Analyze*. Name two of its
   prerequisites and explain why you can't reach the *Analyze* level
   without them.

## Linked concept

- *Learning-graph concept:* this page is the meta view — there is no
  single node for the graph itself; every node in the graph is a
  concept this page lets you reach.
- *Framework citation:* the pattern is
  [intelligent-textbooks → learning-graph-generator](https://github.com/dmccreary/claude-skills).

---

## See also

- **[`graph/schema.md`](../../../graph/schema.md)** — the runtime
  Reasoning Graph schema (entities + relations, not concepts +
  prerequisites).
- **[`book/12-evidence-and-references.md`](../../../book/12-evidence-and-references.md)** —
  what informs Wearly's reasoning.
- **[`docs/evidence-and-references.md`](../../../docs/evidence-and-references.md)** —
  the canonical references doc.
- **[Source repo `docs/sims/` directory](https://github.com/eatedalsf/styling-agent/tree/main/docs/sims)** —
  other interactive sims live alongside this one.
