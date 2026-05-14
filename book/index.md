<p align="center">
  <img src="../assets/cover.svg" alt="Wearly — an Intelligent Book on Personal Styling Agents" width="100%" style="max-width: 920px; border: 1px solid #EEEEEE; border-radius: 4px;" />
</p>

# The Wearly Intelligent Book

> A mini Intelligent Book documenting how Wearly reasons.
> Inspired by [intelligent-textbooks](https://dmccreary.github.io/intelligent-textbooks/) — Markdown chapters that together form a navigable, structured explanation of the system behind the app.

The book **supports** the working product; it does not replace it. The product is the live Streamlit app; this book documents the reasoning, the data, the trade-offs, and the future.

---

## A Level-2 intelligent textbook

Wearly is built as a **Level 2** intelligent textbook per
[Dan McCreary's framework](https://dmccreary.github.io/intelligent-textbooks/):
a concept-graph–driven, MicroSim-equipped, evidence-citable companion to
the running prototype. That framing is concrete — Wearly ships the
artifacts a Level-2 book is expected to ship:

- a **[concept learning graph](../docs/sims/learning-graph/index.md)** — 28 concepts, 38 prerequisite edges, every node Bloom-tagged (Remember → Understand → Apply → Analyze);
- **[MicroSims](../docs/sims/index.md)** — small interactive simulations for color harmony, freshness, and the two graphs;
- a project-wide **[Glossary](../docs/glossary.md)**, **[FAQ](../docs/faq.md)**, and **[References](../docs/references.md)**;
- per-chapter **Key terms** and **Self-check** footers (Bloom-tiered);
- a canonical **[`book-metadata.yml`](https://github.com/eatedalsf/styling-agent/blob/main/book-metadata.yml)** at the repo root.

See **[`book-metadata.yml`](https://github.com/eatedalsf/styling-agent/blob/main/book-metadata.yml)** for the canonical
version, license, and framework pointers.

---

## Table of contents

| # | Chapter | What it covers |
|---|---|---|
| 01 | [Product vision](01-vision.md) | What Wearly is, who it's for, what it isn't |
| 02 | [User problem](02-user-problem.md) | The 15-minute closet decision and why it matters |
| 03 | [Agent workflow](03-agent-workflow.md) | The seven-step reasoning loop, end to end |
| 04 | [Styling knowledge base](04-styling-knowledge-base.md) | Occasion rules, color rules, the structured logic behind the recommendations |
| 05 | [Wardrobe intelligence](05-wardrobe-intelligence.md) | How wardrobe items are modeled, filtered, and matched |
| 06 | [Fit-profile logic](06-fit-profile-logic.md) | Body-positive personalization, what's modeled today and what's next |
| 07 | [Calendar & weather context](07-calendar-weather-context.md) | Two external context sources and how they steer decisions |
| 08 | [Shopping-gap logic](08-shopping-gap-logic.md) | When the agent says "you don't own this yet" |
| 09 | [Before / after demo](09-before-after-demo.md) | The delta between manual planning and an agentic system |
| 10 | [Privacy & security](10-privacy-security.md) | Data handling, today and in production |
| 11 | [Product roadmap](11-product-roadmap.md) | Where Wearly is going |
| 12 | [Evidence and references](12-evidence-and-references.md) | What informs Wearly's recommendation logic, and what still needs citation work |

---

## How to read this book

- **In order** for the full story.
- **By chapter** if you're verifying a specific claim in the app.
- **As a reference** if you're building on the system — every chapter names the file or data structure it documents.

Each chapter is short. The principle is **structure beats volume**: a small set of organized chapters that match the system, rather than a long unstructured prose.

---

*Companion to `Wearly_Product_Brief.md` (the canonical product vision) and `docs/architecture.md` (the system snapshot).*
