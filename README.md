# Wearly

*An evidence-informed, body-positive personal styling agent — with a reasoning trail you can argue with.*

[![tests](https://github.com/eatedalsf/styling-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/eatedalsf/styling-agent/actions/workflows/tests.yml)
[![docs](https://github.com/eatedalsf/styling-agent/actions/workflows/docs.yml/badge.svg)](https://github.com/eatedalsf/styling-agent/actions/workflows/docs.yml)

**SEIS 666 — Digital Transformation 2.0 with Generative AI | Spring 2026**
**Track B: Agentic AI System**

### 🔗 [**Open the live app →**](https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/) · 📖 [**Read the Intelligent Book →**](https://eatedalsf.github.io/styling-agent/)

---

## What Wearly is

Wearly is an **agentic personal styling prototype** that recommends complete outfits using your calendar, real-time weather, wardrobe, and fit profile — and shows every line of reasoning that led to the recommendation. The user can argue with any choice; the agent re-runs with the pushback as a new constraint.

It is two things at once:

1. **A working Streamlit app** — the prototype demonstrates the agent in action.
2. **An Intelligent Book** — a published MkDocs Material site that explains the rules, evidence, and reasoning patterns behind the prototype. Built to Dan McCreary's [Level-2 intelligent-textbook framework](https://dmccreary.github.io/intelligent-textbooks/).

> **The app shows what Wearly does. The Intelligent Book explains how and why it reasons that way.**

> [!IMPORTANT]
> **All shipped data is demo data, not real personal data.** The seed `wardrobe.json` belongs to a fictional "Demo User." Per-user state files written by the running app (`user_wardrobe.json`, `user_profile.json`, `wishlist.json`, `favorite_stores.json`, `routine.json`, `wear_history.json`, `calendar_events.json`) are `.gitignore`d and never committed. Each developer who runs the app builds their own local overlay.

---

## Why I built it

Every morning, deciding what to wear can take real time — and it isn't just "pick a shirt." The decision depends on the calendar, the weather, what's actually in the closet, the occasion, fit preferences, skin tone, and sometimes what's *missing* from the wardrobe. Most styling tools just suggest clothes. I wanted an **agent I could argue with**: one that reads context first, explains its reasoning step by step, identifies real wardrobe gaps without inventing forced fits, and gets out of the way when its choice is wrong.

The agent runs through a **seven-step reasoning loop** every time. Each step writes to a visible trail with rule citations like `[color-coordination-rules#R2]`. Users can reject any pick with a reason, and the agent re-runs with that rejection recorded as a constraint. That loop — context → decision → explanation → pushback → re-run — is the agent stance, distinct from a chatbot that waits for a prompt and responds to it.

---

## Track B mapping — Agentic AI System rubric

| Requirement | How Wearly satisfies it |
|---|---|
| **Working agent** | Runs end-to-end via CLI (`python main.py`) or Streamlit (`streamlit run app.py`). Produces a recommendation with full reasoning trail in ~3 seconds. |
| **Two or more external tools / data sources** | Eight: Open-Meteo weather API, calendar (iCalendar `.ics` import + URL subscription + seed JSON), wardrobe inventory, fit profile, wishlist, favorite stores, wear history, color-rules table. |
| **Documented decision tree** | Seven-step agent workflow (see below). Each step appends an audit record to `result["steps"]`. Per-step decision flow is in [`workflow_diagram.md`](workflow_diagram.md). |
| **Error handling** | Every tool has a graceful fallback (seasonal weather estimate when API unavailable, empty-wardrobe handling, unknown occasion → casual, etc.). |
| **Before / after comparison** | `python main.py --compare` shows manual planning (10–15 min) vs. agent (~3 s) side by side. Surfaced inside the app's Today and Demo screens. |
| **10-minute presentation** | Demonstrated live: see [`docs/demo_script.md`](docs/demo_script.md). |
| **Reasoning is auditable** | Every line carries a citation back to a Skill rule pack, which cites verified evidence categories. Closed end-to-end. |
| **Body-positive language contract** | Forbidden tokens (`flaw`, `fix`, `hide`, `minimize`, `correct`, `problem area`, `trouble area`, `slimming`, `shameful`) enforced at runtime AND in a documentation-integrity test that scans every Markdown file in the repo. |

**Tests: 375 passing.** Docs build clean under `mkdocs build --strict`.

---

## How to run it locally

**Requirements:** Python 3.10+ (3.12 recommended). The core agent uses only the standard library; the Streamlit web UI and the docs build need a small set of extra packages.

### Run the app

```bash
git clone https://github.com/eatedalsf/styling-agent.git
cd styling-agent
pip install -r requirements.txt
streamlit run app.py
```

The app opens at **<http://localhost:8501/>**. First load shows a tour of the Today page; the Wardrobe page exposes a one-click demo-wardrobe loader (48 curated items) if you don't have a personal closet yet.

### CLI alternative

```bash
python main.py                  # auto-read the next calendar event
python main.py --everyday gym   # everyday request (work / gym / dinner / formal / casual)
python main.py --compare        # before/after demo
```

### Run the Intelligent Book locally

```bash
pip install -r requirements-docs.txt
python scripts/stage_docs.py    # copies Markdown into _docs_build/
mkdocs serve                    # serves at http://127.0.0.1:8000/styling-agent/
```

Or for a one-off static build: `mkdocs build` — output lands in `site/`.

---

## The seven-step agent workflow

Every recommendation runs this loop. Each step writes an audit record the app surfaces in the "Agent Workflow — 7 Steps" expander.

```
Step 1 · Determine Occasion       → calendar event title or free-text request
                                    → mapped to one of 5 canonical tags
                                      (work, gym, dinner, formal, casual)
Step 2 · Load Style Profile       → body_shape, skin_tone, preferred_fit,
                                    style_preferences, modesty_preference,
                                    highlight_features, balance_areas
Step 3 · Check Weather            → live Open-Meteo call; seasonal fallback if offline
                                    → temperature → layer thresholds (<60°F = outerwear)
Step 4 · Filter Wardrobe          → candidate pool by occasion + season
                                    → previously-rejected items excluded
Step 5 · Build Outfit             → dress-vs-separates branching
                                    → activewear handling for gym
                                    → outerwear injection when cold
                                    → freshness tie-breaker (0.4 floor)
Step 6 · Check for Wardrobe Gaps  → required-pieces table per occasion
                                    → qualified gaps promoted to descriptive
                                      (never promotional) shopping suggestions
Step 7 · Color Coordination Check → +8 / +4 / −10 against skin-tone palette
                                    → 0–100 score, body-positive flags
```

Body-positive throughout. Every line of the reasoning trail can be traced to a `<pack>#R<N>` rule slug via `rule_refs.py`.

---

## External tools and data sources

| Tool | What it does | Source |
|---|---|---|
| **Open-Meteo API** | Live temperature, feels-like, precipitation, wind | <https://open-meteo.com> (free, no key) |
| **iCalendar import** | Parse `.ics` files; subscribe to a calendar URL | `calendar_import.py` |
| **Wardrobe inventory** | Seed (`wardrobe.json`) + user overlay (`user_wardrobe.json`, gitignored) | Hand-curated demo + Add-by-Link |
| **Add-by-Link product import** | Parse a retailer product page → catalog item with color + tags | `link_import.py` |
| **Pexels (optional)** | Real product photos for demo wardrobe; falls back to silhouettes | `demo_wardrobe.py` (set `PEXELS_API_KEY` env var; 200/hr free) |
| **Fit profile** | User-declared body shape, skin tone, fit, modesty, comfort, style goals | `fit_tool.py` |
| **Wear history** | `worn_count` + `last_worn_date` per item, written on confirm | `history_tool.py` |
| **Shopping signals** | Wishlist, favorite stores, gap-driven suggestions | `shopping_tool.py` |
| **Reasoning graph** | Live entity graph per recommendation; schema graph at the book level | `graph_tool.py`, `graph/graph.json` |
| **Skill rule packs** | Eight `<pack>-rules.md` files the agent reads at runtime | `skills/wearly-styling-agent/` |
| **Color rules** | Three skin-tone palettes (warm olive, cool fair, deep warm) × three tiers | `color_rules.json` |

---

## Three graph layers — they answer different questions

Wearly ships **three** interactive `vis-network` graphs. They sit at different altitudes of the same project and answer fundamentally different questions.

| | **Learning Graph** | **Reasoning Graph** | **Wearly Knowledge Graph** |
|---|---|---|---|
| **Question** | *In what order should I learn Wearly's concepts?* | *How did the agent produce this specific outfit?* | *What does Wearly **know** about styling, this user, and the rules that connect them?* |
| **What it models** | The reader's path through the Intelligent Book | The agent's runtime data for one recommendation | The reusable structured-knowledge layer: domain rules + user-behavior aggregates + runtime archetypes |
| **Nodes are** | Concepts (28 total) | Entity instances (User, CalendarEvent, WardrobeItem, ...) — one run | Domain types + user-behavior aggregates + runtime archetypes (91 in the seed snapshot) |
| **Edges are** | Prerequisites (*"understand A before B"*) | Typed relations from `graph/schema.md` | Typed relations across all three layers (`OWNS`, `REQUIRES`, `USES_RULE`, `POWERS`, `EVALUATES`, `CONTAINS_RULE`, ...) |
| **Node size means** | Equal weight; Bloom level by color | Wear-count for items, piece-count for outfit | **Aggregated user signal** — heavier nodes carry more user activity (worn often, covers more occasions, items invested in this category) |
| **Read it when** | You're trying to *learn* Wearly | You're auditing *one* recommendation | You're trying to *understand the structured knowledge under the agent* — or build a future RAG / LLM layer on top of it |
| **Source file** | [`graph/learning-graph.json`](graph/learning-graph.json) | [`graph/graph.json`](graph/graph.json) + per-run dynamic graph | [`graph/wearly-knowledge-graph.json`](graph/wearly-knowledge-graph.json) (generated) |
| **Generator** | hand-curated | per-run via `graph_tool.py` | [`scripts/generate_wearly_kg.py`](scripts/generate_wearly_kg.py) — deterministic, seed-only by default |

### Why the Knowledge Graph is not decorative

The Wearly Knowledge Graph is **structured context** — the kind of input modern LLM agents perform better against than a flat-text dump of the same information. Three observable properties:

- **Compact.** The committed JSON is ~50 KB even though it covers every domain entity, every user-behavior aggregate, every rule pack, and the workflow. The equivalent flat-text description of the rules + wardrobe + history + occasion table is an order of magnitude larger.
- **Queryable.** Filtering by `layer` (domain / user_behavior / runtime), by `type`, or by `metric` returns a precise subgraph. An LLM doesn't have to vector-search the whole book to find the relevant rule.
- **Auditable.** Every edge has a typed `from` / `to` / `type`. The citation chain (`evidence → category → rule → reasoning line`) is *literally a graph traversal* you can follow with a finger.

### How node size encodes user behavior over time

Domain archetypes (`RulePack`, `WeatherCondition`, `SkinTonePalette`, `WorkflowStep`) stay at base size — they're equal-importance facts. **User-behavior nodes scale with observable signals:**

- A `WardrobeItem` grows with `worn_count` + versatility (count of distinct occasion tags).
- A `WardrobeItemType`, `ColorFamily`, or `OccasionType` rolls up from its connected `WardrobeItem` nodes. A category with many heavy items becomes a heavy category node.
- A `FavoriteStore` scales with `times_chosen` when the user-overlay data is included.

A glance at the graph tells you which colors your closet returns to, which occasions you're well-covered for, and which item types you've invested in.

### How this enables future LLM and RAG layers

The Knowledge Graph is the **substrate** the roadmap items in the next section sit on. Two examples:

1. **RAG over the Intelligent Book** — a question like *"Why does this dress work for my profile?"* becomes: start at the dress's `WardrobeItem` node → walk to `WardrobeItemType` + `ColorFamily` + `SUITABLE_FOR` occasion → follow `USES_RULE` to the powering rule packs → retrieve the book chapters keyed off those rule slugs. The LLM gets a *subgraph + relevant book passages*, not a wall of text. Retrieval is **along graph edges**, not vector embeddings, so the explanation cites the same rule the runtime agent does.
2. **LLM shopping agent over favorite stores** — when a `WardrobeGap` is detected, walk to the connected `WardrobeItemType`, the user's `HAS_SKIN_TONE`, and `FitProfile`; visit each `FavoriteStore`; query that store's catalog with the graph-derived constraints; score any candidate against the same rule packs the runtime engine uses. **The rule engine stays the safety + scoring substrate; the LLM is the discovery layer.**

This is what "structure beats prompts" looks like in practice: structured knowledge guides the LLM rather than the LLM having to discover the structure inside free-text prompts.

### How to view the three graphs

| Graph | Where to view |
|---|---|
| Learning Graph | [Book → Learning Graph](https://eatedalsf.github.io/styling-agent/docs/sims/learning-graph/) |
| Reasoning Graph (schema) | [Book → Reasoning Graph](https://eatedalsf.github.io/styling-agent/docs/sims/knowledge-graph/) |
| Reasoning Graph (live per-recommendation) | Inside the app, expander below every outfit result |
| **Wearly Knowledge Graph** | [Book → Wearly Knowledge Graph](https://eatedalsf.github.io/styling-agent/docs/sims/wearly-knowledge-graph/) |

---

## The compact reasoning graph export

Each outfit result has an **"Export today's reasoning as a compact reasoning graph"** button. One click writes a small JSON file (typically 3–8 KB) that captures the entire run as structured knowledge: User → CalendarEvent → WeatherSnapshot → Outfit → WardrobeItems → Gaps → Feedback. Same shape as `graph/schema.md`.

Why it matters: the file is **portable structured knowledge at the MD level**, the pattern Dan McCreary's class explored as the future of LLM context-management. Instead of feeding the next session a transcript, you feed it this 5-KB graph and the LLM (or a human reviewer) gets a precise, queryable snapshot of what happened.

Implementation: [`compact_kg.py`](compact_kg.py).

---

## Specialized rule-based skills

Wearly's reasoning isn't a black-box LLM. It's a small, inspectable rule layer documented as a [Claude Skill package](skills/wearly-styling-agent/) (Advanced tier — agentskills.io conventions). Eight rule packs, each cited from the runtime reasoning trail via `[<pack>#R<N>]` slugs in [`rule_refs.py`](rule_refs.py).

| Rule pack | What it governs |
|---|---|
| [`occasion-rules.md`](skills/wearly-styling-agent/occasion-rules.md) | The five canonical occasion tags + required-piece sets + dress-vs-separates branching + accessory cap of 2 |
| [`weather-rules.md`](skills/wearly-styling-agent/weather-rules.md) | Temperature bands, the <60°F outerwear threshold, seasonal-estimate fallback |
| [`wardrobe-filtering-rules.md`](skills/wearly-styling-agent/wardrobe-filtering-rules.md) | Step 4 candidate pool: occasion + season + rejection-exclusion |
| [`fit-silhouette-rules.md`](skills/wearly-styling-agent/fit-silhouette-rules.md) | Body-positive contract, fit-profile fields, R8 measurement-suggested fit |
| [`color-coordination-rules.md`](skills/wearly-styling-agent/color-coordination-rules.md) | Three skin-tone palettes, +8 / +4 / −10 scoring, 0-100 clamp |
| [`wear-history-rules.md`](skills/wearly-styling-agent/wear-history-rules.md) | Freshness tie-breaker, 0.4 floor, 3-day "let it breathe" recency window |
| [`shopping-gap-rules.md`](skills/wearly-styling-agent/shopping-gap-rules.md) | Qualified-gap rule, descriptive-not-promotional tone, "honest gaps over forced fits" |
| [`privacy-guidelines.md`](skills/wearly-styling-agent/privacy-guidelines.md) | Minimum-necessary access, no third parties (except unauthenticated weather), GDPR-spirit user rights |

Each rule pack ends with a *Source basis* footer that traces back to one of nine evidence categories in [`docs/evidence-and-references.md`](docs/evidence-and-references.md). The full citation chain is: **evidence category → rule pack → rule ID → reasoning line in the app**.

---

## Project structure

```
styling-agent/
├── app.py                       Streamlit web UI (Today, Planner, Wardrobe, Shop, Profile, Demo)
├── main.py                      CLI runner (calendar / everyday / compare modes)
├── styling_agent.py             Core agent — orchestrates the 7 steps, builds the reasoning trail
│
│  ── Runtime tools ──
├── calendar_tool.py             Read upcoming events (seed JSON)
├── calendar_import.py           .ics file + URL-subscription real-calendar import
├── weather_tool.py              Live weather (Open-Meteo) + seasonal fallback
├── wardrobe_tool.py             Filter wardrobe by occasion + season + rejections
├── color_tool.py                Skin-tone color-harmony scoring
├── history_tool.py              Wear history + freshness tie-breaker
├── fit_tool.py                  Fit profile + body-positive language contract
├── shopping_tool.py             Wishlist, favorite stores, gap-driven suggestions
├── graph_tool.py                pyvis-rendered reasoning graphs (schema + live-run)
├── routine_tool.py              Weekly routine fallback when no calendar present
├── link_import.py               Wardrobe-builder: parse a product URL into a closet item
├── backup_tool.py               Backup & restore across Streamlit Cloud restarts
├── compact_kg.py                Export one day's reasoning as a portable knowledge graph
├── wardrobe_query.py            Ask-your-wardrobe pre-baked queries
├── rule_refs.py                 Canonical registry tying reasoning lines to Skill rule slugs
│
│  ── Demo data (anonymized — "Demo User") ──
├── wardrobe.json                Wardrobe inventory seed
├── seed_calendar_events.json    Demo calendar events
├── seed_wear_history.json       Demo wear history (so freshness reasoning fires on fresh clones)
├── color_rules.json             Skin-tone color rules
├── demo_wardrobe.json           48-item one-click demo wardrobe loader catalog
│
│  ── Intelligent Book (MkDocs Material → GitHub Pages) ──
├── book/                        21+ chapters: Part I (Agent) + Part II (Styling Rules) + III (Evidence)
├── docs/                        Architecture, demo script, evidence, glossary, FAQ,
│                                references, audit doc, micro-sims, business model
├── graph/                       graph.json (reasoning) + learning-graph.json + schema.md
├── skills/wearly-styling-agent/ Skill package: 8 rule packs + SKILL.md + validator
├── scripts/                     stage_docs.py + per-chapter inserters
├── mkdocs.yml                   MkDocs Material config (custom Wearly theme)
├── book-metadata.yml            Canonical book metadata (level, author, course, version)
├── requirements-docs.txt        Build-only docs deps
│
│  ── CI / config ──
├── .streamlit/config.toml       Streamlit theme + server config
├── .github/workflows/           tests.yml (375 tests on push) + docs.yml (Pages deploy)
├── tests/                       375 unittest cases — agent smoke, fit, color, history,
│                                graph, rule-refs, documentation-integrity, tradeoff-gap-consistency
├── requirements.txt             Runtime deps (streamlit, pyvis, pillow, requests)
├── workflow_diagram.md          Agent decision flow
├── Wearly_Product_Brief.md      Full product vision
└── README.md                    This file
```

Per-user state files (`user_wardrobe.json`, `user_profile.json`, `wishlist.json`, `favorite_stores.json`, `routine.json`, `wear_history.json`, `calendar_events.json`, `calendar_subscription.json`) are `.gitignore`d — they hold each developer's real data and are never published.

---

## Limitations — honest scope notes

Wearly is a **single-user, rule-based prototype.** Things it deliberately does *not* do today:

- **No LLM in the runtime decision path.** Recommendations are produced by deterministic rules. This is a design choice (auditability + body-positive language contract) — see Chapter 04, *"Why rules, not ML."*
- **No learned models.** Wearly records explicit signals (wear count, rejections, profile edits) as state, but never trains a policy or updates weights. Adaptation happens through structured persistence, not gradient descent.
- **No image-based body classification.** Body-shape labels are user-*declared* preferences, never inferred from photos. The agent has no image classifier in the decision path.
- **No collaborative filtering.** Wearly is per-user; it never compares your closet to anyone else's.
- **No automated purchasing.** Shopping suggestions are descriptive, never transactional. The user is always the final reviewer.
- **No multi-day rotation planner.** Today's outfit is freshness-aware; planning across 3-7 days is a roadmap item.
- **No authentication.** The local Streamlit prototype is single-user with no login. Multi-user / family wardrobes need auth + per-user data isolation — see roadmap.

---

## Future roadmap

What the current prototype proves, the next layers can build on. Each item below sits **on top of** the current rule engine, not in place of it. The rule layer remains the safety + scoring substrate.

### 🤖 LLM layer over the Intelligent Book (RAG)

Wear­ly already exports a compact reasoning graph; the next step is letting the user **ask open-ended questions** over the book and the user's run history:

- *"Why does this silhouette work for my profile?"*
- *"What's the difference between a tradeoff and a qualified gap?"*
- *"Show me the rule behind today's color score."*

The Intelligent Book is already structured for RAG — chapters, glossary, FAQ, references, learning graph, audit doc. An LLM planner would orchestrate retrieval over those sources and call the existing rule engine for any *decision* (not language) that needs to stay deterministic.

### 🛍 LLM shopping agent for favorite stores

When the user has saved favorite stores (currently local-only state), an LLM agent could:

- Monitor the user's favorite-store catalogs for new arrivals.
- Read product pages, extract color / silhouette / fabric tags.
- Compare against the user's current wardrobe gaps and styling rules.
- Recommend specific pieces with explainable matches against the user's qualified gaps.

The current rule engine remains the *scoring + safety* layer: any LLM-suggested product still has to pass occasion rules, color score, fit alignment, and the body-positive contract before it can appear as a suggestion.

### 👨‍👩‍👧 Multi-user / family wardrobes

Wearly is single-user today. A family layer would add:

- Per-person fit profiles in one household account.
- Shared / borrowed pieces (a teen borrowing a parent's blazer).
- Parent-managed child wardrobes with their own modesty defaults.
- Cross-person rotation awareness (avoid recommending the same coat to two people in one week).

### 🧵 Fabric and material rules

Today's rules reason about garment type, color, formality, season, and silhouette. Fabric (linen, wool, cotton blends, technical performance fabrics) is a missing axis. A `fabric-rules.md` pack would add:

- Material × season alignment (linen for summer, wool for winter).
- Material × care alignment ("dry clean only" filtered when laundry constraints set).
- Material × occasion alignment (no jersey for formal events).
- Allergen / sensitivity respect (no wool when sensitivity declared).

### 🔒 Privacy and authentication for production

The prototype is **local-only by design**. A production version would add:

- User accounts (OAuth + per-user data isolation).
- Encrypted at-rest user data; opt-in cloud sync.
- GDPR/CCPA-aligned data rights: view, export, delete, object.
- Differential privacy if any cross-user analytics ever land.

Today's privacy stance is documented in [`book/10-privacy-security.md`](book/10-privacy-security.md) and the [`privacy-guidelines.md`](skills/wearly-styling-agent/privacy-guidelines.md) rule pack: minimum-necessary access, no third parties (the unauthenticated weather call is the only network egress), and no implicit data collection.

---

## How AI was used in building Wearly

This project was built with Claude (Anthropic) as a development partner — every line of code, every chapter, every rule pack was either written by or refined with Claude through iterative dialogue. The development log is itself an example of the agentic workflow Wearly demonstrates: structured context (the Intelligent Book), explicit goals (the SEIS 666 rubric and the body-positive language contract), tool use (file editing, test running, mkdocs build), and pushback-driven re-runs.

The **runtime decision engine is deterministic by design.** No LLM call sits between a user click and an outfit recommendation. The reasoning trail's text is generated by Python functions reading rule tables, not by language model inference. That's what makes every reasoning line auditable.

---

## Citation chain — end to end

Every line of the agent's reasoning trail can be traced from output to source:

```
verified evidence (citation [N])
   ⬇
evidence category (docs/evidence-and-references.md § 3.x)
   ⬇
rule pack (skills/wearly-styling-agent/*.md)
   ⬇
rule ID (R<N> heading)
   ⬇
slug in rule_refs.py (e.g. color#R2)
   ⬇
reasoning line in the app (carries [color-coordination-rules#R2])
```

The `tests/test_rule_refs.py` test asserts every slug resolves to a real rule heading. The `tests/test_documentation_integrity.py` test asserts the body-positive contract holds across every Markdown file. The full audit doc at [`docs/audit-2026-05.md`](docs/audit-2026-05.md) pins every consistency contract between the app and the book.

---

## Sample output

Running `python main.py` with a "Team Strategy Meeting" on the calendar produces:

```
📅 OCCASION
  Event:    Team Strategy Meeting
  Date:     2026-05-12  10:00 AM
  Type:     WORK

🌤 WEATHER
  Minneapolis, MN: 52°F, Partly Cloudy
  Advice: A light jacket or coat is recommended.

⚙️ AGENT WORKFLOW STEPS
  Step 1 [✓] Determine Occasion → Found: 'Team Strategy Meeting'
  Step 2 [✓] Load Style Profile → Owner: Demo User | warm olive | classic, elegant, minimal
  Step 3 [✓] Check Weather      → Live: Minneapolis 52°F partly cloudy
  Step 4 [✓] Filter Wardrobe    → 10 clothing, 4 shoes, 6 accessories for work/fall
  Step 5 [✓] Build Outfit       → 6 pieces selected
  Step 6 [✓] Check for Gaps     → Outfit complete
  Step 7 [✓] Color Check        → 100/100 — all colors align well for warm-olive skin

👗 YOUR OUTFIT
  • White Button-Down Blouse (white)
  • Black Tailored Trousers (black)
  • Black Pointed-Toe Heels (black)
  • Gold Hoop Earrings (gold)
  • Pearl Stud Earrings (white/gold)
  • Camel Wool Coat (camel)

💡 WHY THIS OUTFIT
  1. Selected White Button-Down Blouse for its business formality. [occasion-rules#R2]
  2. Selected Black Tailored Trousers to pair with the top.
  3. Added Black Pointed-Toe Heels appropriate for the occasion. [occasion-rules#R3]
  4. Added Gold Hoop Earrings.
  5. Added Camel Wool Coat — 52°F, light coat recommended. [weather-rules#R4]
  6. All colors align well for warm-olive skin tone. [color-coordination-rules#R2]
```

---

## License + course context

**Course:** SEIS 666 — Digital Transformation 2.0 with Generative AI
**Institution:** University of St. Thomas
**Semester:** Spring 2026
**Instructor:** Daniel Yarmoluk
**Framework reference:** Dan McCreary's [Intelligent Textbooks](https://dmccreary.github.io/intelligent-textbooks/) — Wearly's book is built to the Level-2 specification.

The book and code are released under **CC BY-NC-SA 4.0** for educational use. Demo data (seed wardrobe, sample calendar events, color rules) is fictional; any resemblance to real people's wardrobes is coincidental.

---

*Wearly — an agent you can argue with.*
