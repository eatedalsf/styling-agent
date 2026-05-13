# Wearly Knowledge Graph — Visualization

This page renders the schema in `schema.md` as a Mermaid diagram. GitHub renders Mermaid natively, so opening this file on GitHub shows the diagram directly. The schema and the serialized triples live alongside (`schema.md`, `graph.json`).

> **Looking for the FAQ?** Library used, what node size means, what colors mean, why not Neo4j, structured queries, how the graph connects to the agent's reasoning — all in [`docs/knowledge-graph-faq.md`](../docs/knowledge-graph-faq.md). That page is the single source of truth for the visual legend; the same content is also embedded into the app under every interactive graph as a "What does this graph mean?" expander.

## Node-size legend (live-run graph)

Node size encodes a real signal — not just role.

| Node type | Diameter rule | Meaning |
|---|---|---|
| `User` | fixed 32 px | visual anchor |
| `OutfitRecommendation` | `22 + 2 × piece_count`, clamped 22..44 px | how many decisions this run made |
| `WardrobeItem` | `18 + 2 × worn_count`, clamped 18..30 px | how often you reach for this piece |
| Context (`CalendarEvent`, `FitProfile`, `WeatherSnapshot`) | fixed 22–26 px | context is context, not centerpiece |
| Derived (`WardrobeGap`, `ShoppingSuggestion`, `Feedback`) | fixed 18–22 px | downstream of the picks |

Hover tooltips on items state `"Worn: N times (node size encodes this)"` so the rule isn't hidden in the code.

---

## The graph at a glance

```mermaid
graph LR
    %% Entity styles
    classDef user        fill:#FDFAF7,stroke:#C17F5A,stroke-width:2px,color:#1C1917;
    classDef context     fill:#FAF3EE,stroke:#9F5A36,color:#1C1917;
    classDef item        fill:#F5EDE3,stroke:#A8937E,color:#1C1917;
    classDef outcome     fill:#FDFAF7,stroke:#1C1917,stroke-width:2px,color:#1C1917;
    classDef gap         fill:#FDF3EE,stroke:#C17F5A,stroke-dasharray:4 2,color:#8A4A20;
    classDef feedback    fill:#EFE3CC,stroke:#7C6F64,color:#1C1917;

    User((Eatedal · User))
    Fit[Fit Profile<br/>hourglass · warm olive · tailored]
    Event1[Calendar Event<br/>Team Strategy Meeting · 2026-05-12]
    Wx[Weather<br/>Minneapolis · 58°F · Partly Cloudy]

    Blouse[White Button-Down Blouse]
    Trousers[Black Tailored Trousers]
    Heels[Black Pointed-Toe Heels]
    Coat[Camel Wool Coat]
    Earring1[Gold Hoop Earrings]
    Earring2[Pearl Stud Earrings]

    Outfit{{Outfit Recommendation<br/>Work · 6 pieces}}
    Gap[/Wardrobe Gap<br/>athletic outerwear/]
    Shop[Shopping Suggestion<br/>Lightweight windbreaker]
    Feedback[(Feedback<br/>Too formal)]

    User -- has_fit_profile --> Fit
    User -- has_event --> Event1
    User -- sees_weather --> Wx
    User -- owns --> Blouse
    User -- owns --> Trousers
    User -- owns --> Heels
    User -- owns --> Coat
    User -- owns --> Earring1
    User -- owns --> Earring2

    Event1 -- has_occasion_type --> Work[work]
    Wx -- requires_layer_for --> Layer[outerwear]

    Outfit -- addresses_event --> Event1
    Outfit -- recommends --> Blouse
    Outfit -- recommends --> Trousers
    Outfit -- recommends --> Heels
    Outfit -- recommends --> Coat
    Outfit -- recommends --> Earring1
    Outfit -- recommends --> Earring2

    Outfit -- flags_gap --> Gap
    Gap -- suggests_to_buy --> Shop

    Blouse -- was_rejected_with --> Feedback
    Feedback -- excludes_from_pool --> Blouse

    class User user;
    class Fit,Event1,Wx,Work,Layer context;
    class Blouse,Trousers,Heels,Coat,Earring1,Earring2 item;
    class Outfit outcome;
    class Gap,Shop gap;
    class Feedback feedback;
```

---

## How to read this

- **The User** sits on the left. Every traversal starts from there.
- **Context entities** (Fit Profile, Calendar Event, Weather) feed into the agent's reasoning.
- **Wardrobe items** are *owned* by the user. The agent picks from these.
- **The Outfit Recommendation** in the middle-right is the **product of the seven-step workflow** — it points back to the event it addresses and forward to the items it includes.
- **Wardrobe Gap → Shopping Suggestion** is the resolution path when a piece is missing.
- **Feedback → excludes_from_pool** is the reject-and-regenerate loop.

If you trace any edge from the Outfit Recommendation node, you'll arrive at the **reason** it exists.

---

## Why a graph at all

The course principle "structure beats volume" is operational here. A reviewer asking *"how does Wearly decide?"* gets one of three answers:

1. **A flowchart** (`workflow_diagram.md`) — shows the *steps*.
2. **An architecture diagram** (`docs/architecture.md`) — shows the *files*.
3. **This knowledge graph** — shows the *relationships*.

Each lens is necessary. The graph in particular makes it visible that Wearly isn't a chain of prompts — it's a model of the user's life, their day, and their closet, with explicit edges between them.
