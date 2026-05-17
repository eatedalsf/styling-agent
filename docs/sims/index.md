# MicroSims

> **What's on this page.** The four interactive simulations and graphs
> that make Wearly's reasoning *touchable*. Each one targets a single
> rule or concept the styling-agent prototype applies at runtime,
> declares its learning objective at the top, and ends with a short
> self-check. The sims are the hands-on surface of the Intelligent
> Book — the app demonstrates the agent in action; the sims let you
> try the same rules yourself, in isolation.

## Why a MicroSim?

A static rule description is easy to skim past. A MicroSim is the
opposite: a small, closed-loop activity where the reader sets a value,
sees the rule respond, and walks away with a concrete intuition. The
pattern is borrowed from
[`dmccreary/intelligent-textbooks`](https://dmccreary.github.io/intelligent-textbooks/)
and the
[SEIS 666 MicroSims index](https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/sims/) —
in a Level-2 intelligent textbook, every rule the agent applies at
runtime is also a sim.

All Wearly sims share the same design system (paper / card / accent
palette, DM Sans typography) and the same page structure: *Learning
objective → iframe → How to use it → The rule, written out → What to
notice → Try this → Self-check → Linked concept → See also.*

---

## The sims

| Sim | Learning objective | Linked concept | Bloom |
|---|---|---|---|
| **[Color harmony](color-harmony/index.md)** | Predict how a color choice shifts the harmony score against a given skin-tone palette. | `color-harmony` | Apply |
| **[Wear-history freshness](freshness/index.md)** | Explain why a much-loved item is never exiled and how the 0.4 floor + 3-day window cooperate. | `freshness-score` | Analyze |
| **[Wearly Knowledge Graph](wearly-knowledge-graph/index.md)** *(structured-knowledge layer)* | Distinguish Wearly's three structured-knowledge layers (domain, user behavior, runtime), explain what node size means in terms of user signals, and describe how the graph enables RAG and LLM shopping layers. | *(meta — three-layer schema)* | Analyze |

---

## How sims are made

Each sim is one HTML file under `docs/sims/<sim-name>/` plus a
one-page `index.md` that frames it. The viewer is embedded via
`<iframe>`. No build step, no JS bundler, no React — plain DOM plus a
small CDN-loaded library (`vis-network` for graphs, `p5` for color
sims). That makes every sim:

- **Inspectable.** Right-click → view source. The code IS the
  documentation.
- **Self-contained.** Each sim works without the rest of the site.
- **Reusable.** Drop the HTML into any other Markdown viewer and it
  still works.

The structure mirrors `dmccreary/intelligent-textbooks` and the SEIS
666 course book.

---

## Page template

Every sim follows the same structure so a reader who learns one knows
the rest:

1. **Learning objective** — one sentence at the top, learner-focused.
2. **What you're looking at** — what the screen shows.
3. **Iframe** — the live sim itself.
4. **How to use it** — controls table.
5. **The rule, written out** — the formula in plain Python pseudocode.
6. **What the sim is NOT modeling** — scope notes.
7. **What to notice** — 2–4 guided observations.
8. **Try this** — 3–4 concrete experiments with expected outcomes.
9. **Self-check** — three Bloom-tiered questions (Remember,
   Understand, Apply).
10. **Linked concept** — the matching node in the Learning Graph and
    the rule slug from `rule_refs.py`.
11. **See also** — chapters, skill files, related sims.
