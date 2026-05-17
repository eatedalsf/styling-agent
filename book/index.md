<p align="center">
  <img src="../assets/cover.svg" alt="Wearly — an Intelligent Book on Personal Styling Agents" width="100%" style="max-width: 920px; border: 1px solid #EEEEEE; border-radius: 4px;" />
</p>

# The Wearly Intelligent Book

> **Wearly's Intelligent Book is the learning and reference companion
> for the styling-agent prototype.** The app shows what Wearly does;
> the book explains how and why it reasons that way.
>
> This is an *intelligent textbook about AI-powered personal styling*,
> using Wearly as the working case study — not app documentation, not
> a generic styling guide. Inspired by
> [intelligent-textbooks](https://dmccreary.github.io/intelligent-textbooks/).

## What this book is — and how it relates to the app

Wearly ships as seven coordinated layers. The app is one of them; the
book is the reference layer that explains every other one.

| Layer | What it is | Where it lives |
|---|---|---|
| **App (prototype)** | The agent running end-to-end on a real wardrobe. | `streamlit run app.py` |
| **Book chapters** | The reasoning behind every step the app takes. | `book/01-vision.md` … `book/12-evidence-and-references.md` |
| **Skill rules** | The operational rules the agent applies at runtime. | [`skills/wearly-styling-agent/`](../skills/wearly-styling-agent/SKILL.md) |
| **Evidence & references** | The verified sources the rules trace back to. | [`docs/evidence-and-references.md`](../docs/evidence-and-references.md), [References](../docs/references.md) |
| **Wearly Knowledge Graph** | A three-layer structured-knowledge graph — domain rules + user-behavior aggregates + runtime archetypes. 91 nodes, 187 typed edges. | [Wearly Knowledge Graph](../docs/sims/wearly-knowledge-graph/index.md) |
| **MicroSims** | Interactive widgets that let the reader try one rule or concept hands-on. | [MicroSims](../docs/sims/index.md) |

A reader who only opens the app sees outcomes. A reader who only
opens the book sees structure. Reading them together is the
intelligent-textbook pattern: the prototype demonstrates the agent in
motion; the book explains every line of its reasoning.

---

## A Level-2 intelligent textbook

Wearly is built as a **Level 2** intelligent textbook per
[Dan McCreary's framework](https://dmccreary.github.io/intelligent-textbooks/):
a concept-graph–driven, MicroSim-equipped, evidence-citable companion to
the running prototype. That framing is concrete — Wearly ships the
artifacts a Level-2 book is expected to ship:

- a **[Wearly Knowledge Graph](../docs/sims/wearly-knowledge-graph/index.md)** — a three-layer structured-knowledge graph (domain rules, user behavior, runtime archetypes), 91 nodes, 187 typed edges, deterministically generated from public seed data;
- **[MicroSims](../docs/sims/index.md)** — small interactive simulations for color harmony, freshness, and the knowledge graph;
- a project-wide **[Glossary](../docs/glossary.md)**, **[FAQ](../docs/faq.md)**, and **[References](../docs/references.md)**;
- per-chapter **Key terms** and **Self-check** footers (Bloom-tiered);
- a canonical **[`book-metadata.yml`](https://github.com/eatedalsf/styling-agent/blob/main/book-metadata.yml)** at the repo root.

See **[`book-metadata.yml`](https://github.com/eatedalsf/styling-agent/blob/main/book-metadata.yml)** for the canonical
version, license, and framework pointers.

---

## Table of contents

The book is organized in three parts. **Part I** explains the agent —
how it reasons, step by step. **Part II** is the *Styling Rule
Reference* — the styling knowledge the agent applies, taught
learner-first with evidence. **Part III** is the evidence base itself.

### Part I — The Wearly Agent

| # | Chapter | What it covers |
|---|---|---|
| 01 | [Product vision](01-vision.md) | What Wearly is, who it's for, what it isn't |
| 02 | [User problem](02-user-problem.md) | The 15-minute closet decision and why it matters |
| 03 | [Agent workflow](03-agent-workflow.md) | The seven-step reasoning loop, end to end |
| 04 | [Styling knowledge base](04-styling-knowledge-base.md) | How the rule packs are organized — entry point to Part II |
| 05 | [Wardrobe intelligence](05-wardrobe-intelligence.md) | How wardrobe items are modeled, filtered, and matched |
| 06 | [Fit-profile logic](06-fit-profile-logic.md) | Body-positive personalization, what's modeled today and what's next |
| 07 | [Calendar & weather context](07-calendar-weather-context.md) | Two external context sources and how they steer decisions |
| 08 | [Shopping-gap logic](08-shopping-gap-logic.md) | When the agent says "you don't own this yet" |
| 09 | [Before / after demo](09-before-after-demo.md) | The delta between manual planning and an agentic system |
| 10 | [Privacy & security](10-privacy-security.md) | Data handling, today and in production |
| 11 | [Product roadmap](11-product-roadmap.md) | Where Wearly is going |

### Part II — Styling Rule Reference

*Each chapter teaches one piece of styling knowledge the agent reasons over, cites the evidence behind it, and points at the rule pack and Part-I chapter that consume it.*

| # | Chapter | What it covers |
|---|---|---|
| S1 | [Color and skin tone](S1-color-and-skin-tone.md) | The warm/cool axis, three palettes, the +8 / +4 / −10 scoring formula |
| S2 | [Silhouette and fit](S2-silhouette-and-fit.md) | Proportion-related styling as user-declared preferences, never classification |
| S3 | [Occasion and context](S3-occasion-and-context.md) | The five canonical tags and why this is the minimum useful taxonomy |
| S4 | [Weather and layering](S4-weather-and-layering.md) | Temperature bands, the <60°F outerwear threshold, the seasonal fallback |
| S5 | [Wardrobe construction](S5-wardrobe-construction.md) | Required pieces, dress-vs-separates branching, the accessory cap |
| S6 | [Rotation and freshness](S6-rotation-and-freshness.md) | Wear-history models, the 0.4 floor, "let it breathe" |
| S7 | [Honest gaps](S7-honest-gaps.md) | Qualified gaps, descriptive-not-promotional tone, honest gaps over forced fits |
| S8 | [Body-positive framing as a discipline](S8-body-positive-framing.md) | The forbidden-token contract enforced in code, not only in prose |

### Part III — Evidence & provenance

| # | Chapter | What it covers |
|---|---|---|
| 12 | [Evidence and references](12-evidence-and-references.md) | What informs Wearly's recommendation logic, and what still needs citation work |

---

## How to read this book

- **In order** for the full story.
- **By chapter** if you're verifying a specific claim in the app.
- **As a reference** if you're building on the system — every chapter names the file or data structure it documents.

Each chapter is short. The principle is **structure beats volume**: a small set of organized chapters that match the system, rather than a long unstructured prose.

---

*Companion to `Wearly_Product_Brief.md` (the canonical product vision) and `docs/architecture.md` (the system snapshot).*
