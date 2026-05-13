# Wearly AI
*Your style, reasoned.*

[![tests](https://github.com/eatedalsf/styling-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/eatedalsf/styling-agent/actions/workflows/tests.yml)
[![docs](https://github.com/eatedalsf/styling-agent/actions/workflows/docs.yml/badge.svg)](https://github.com/eatedalsf/styling-agent/actions/workflows/docs.yml)

**SEIS 666 — Digital Transformation 2.0 | Spring 2026**
**Track B: Agentic AI System**

A mobile-first, clean-luxury personal styling agent that recommends complete outfits using your calendar, real-time weather, wardrobe, and color profile — with full reasoning at every step.

<!-- HERO BLOCK — the live-demo button is wired to the deployed Streamlit
     Cloud app. To add a hero screenshot, drop a PNG at docs/assets/hero.png
     and uncomment the <img> line below. -->

### 🔗 [**Open the live app →**](https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/) · 📖 [**Read the Intelligent Book →**](https://eatedalsf.github.io/styling-agent/)

> **Live demo:** <https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/> — hosted on Streamlit Community Cloud. No install, no signup.
>
> **Intelligent Book:** <https://eatedalsf.github.io/styling-agent/> — companion documentation site built with MkDocs Material. The agent's design principles, evidence categories, skill rules, knowledge-graph schema, and architecture, all searchable in one place.
<!-- > ![Wearly home — hero screenshot](docs/assets/hero.png) -->

**Why Wearly is an agent, not a chatbot**
- 📅 Reads your **calendar** and turns the next event into a styling occasion.
- 🌤 Weighs the **weather** — temperature, precipitation, wind — to choose layers and fabrics.
- 👗 Filters your real **closet** by occasion, season, and what you've already worn.
- 🎨 Scores **color harmony** against your skin tone with a 0–100 score and per-item flags.
- 💡 **Explains every choice** — every recommendation comes with a numbered reasoning trail.
- ✕ **Reject & regenerate.** Push back on any item with a reason; the agent re-runs and tells you what changed.

---

## What This Is

An AI-powered personal styling agent that recommends complete outfits by combining:
- Your **calendar** (upcoming events)
- Real-time **weather** data
- Your **wardrobe inventory** (clothing, shoes, accessories)
- **Skin-tone color coordination** rules
- **Body shape and style preferences**

The agent follows a structured 7-step workflow, makes decisions at each step, handles errors gracefully, and explains every recommendation it makes.

---

## How to Run It

**Requirements:** Python 3.8+. The core agent uses only the standard library. The optional Streamlit web UI needs one extra package — install it with:

```bash
pip install -r requirements.txt
```

```bash
# Clone or copy the project folder, then:
cd styling-agent

# Option 1: Auto-read next calendar event
python main.py

# Option 2: Everyday outfit request
python main.py --everyday "gym"
python main.py --everyday "work"
python main.py --everyday "dinner"
python main.py --everyday "formal gala"
python main.py --everyday "weekend brunch"

# Option 3: Before/After comparison demo (best for presenting)
python main.py --compare

# Option 4: Streamlit web UI
streamlit run app.py
```

---

## Deploy

✅ **This app is live at <https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/>** — hosted on Streamlit Community Cloud, redeployed automatically on every push.

The brand theme, mobile-first layout, and runtime config are picked up automatically from `.streamlit/config.toml`. No environment variables required — the live weather call uses Open-Meteo (no API key).

> **The hosted URL is the canonical demo surface.** Local install instructions above remain available for offline review.

### Reproduce this deployment

To redeploy a fork:

1. Push this repository to your GitHub account.
2. Go to <https://share.streamlit.io>, sign in with GitHub, and click **New app**.
3. Select your repository, the branch you want to deploy, and entry-point `app.py`.
4. Click **Deploy** — first build takes ~2 minutes; every subsequent push redeploys automatically.

---

## Project Status

| Phase | Title | State |
|---|---|---|
| 0 | Foundation reliability | ✅ Shipped |
| 1 | Rebrand + demo polish | ✅ Shipped |
| 2 | Mobile-first UI shell + section nav + profile | ✅ Shipped |
| 4 *(partial)* | Reject & regenerate — the agent-not-chatbot moment | ✅ Shipped |
| 6 | Intelligent Book + Knowledge Graph + Agent Skill package | ✅ Shipped |
| 7 *(partial)* | Smoke tests (32) + architecture doc + GitHub Actions CI | ✅ Shipped |
| 3 | Data-model split + fit-tool wiring | ⏳ Deferred (Profile screen reads `wardrobe.json` directly) |
| 4 *(remaining)* | Wardrobe builder (photo / URL import) + wear-history rotation | ⏳ Deferred |
| 5 | Shopping + wishlist + favorite stores | ⏳ Deferred |

See `Wearly_Product_Brief.md` for the full vision and `book/` for the Intelligent Book chapters that document the agent's reasoning. The Master Implementation Plan is maintainer-local.

---

## Project Structure

The repository uses a flat layout — all source, data, and docs sit at the project root. Per-user runtime state (`calendar_events.json`, `wear_history.json`, `user_profile.json`, `wishlist.json`, etc.) is gitignored; only the `seed_*.json` files are committed so a fresh clone runs cleanly.

```
styling-agent/
├── main.py                  ← CLI runner (calendar / everyday / compare modes)
├── app.py                   ← Streamlit web UI (Today, Planner, Wardrobe, Shop, Profile, Demo)
├── styling_agent.py         ← Core agent. Orchestrates all tools, builds the reasoning trail.
│
│  ── Tools ──
├── calendar_tool.py         ← Tool 1: Reads upcoming calendar events (seed JSON)
├── calendar_import.py       ← Tool 1b: .ics file + URL-subscription real-calendar import
├── weather_tool.py          ← Tool 2: Live weather (Open-Meteo API)
├── wardrobe_tool.py         ← Tool 3: Wardrobe filtering by occasion + season
├── color_tool.py            ← Tool 4: Skin-tone color-harmony scoring
├── history_tool.py          ← Tool 5: Wear history (freshness tie-breaker)
├── fit_tool.py              ← Tool 6: Fit profile + body-positive language contract
├── shopping_tool.py         ← Tool 7: Wishlist, favorite stores, gap-driven suggestions
├── graph_tool.py            ← Tool 8: pyvis-rendered reasoning graph
├── routine_tool.py          ← Tool 9: Weekly routine fallback when no calendar present
├── link_import.py           ← Wardrobe-builder: parse a product URL into a closet item
├── backup_tool.py           ← Backup & restore (persistence across Streamlit Cloud restarts)
├── compact_kg.py            ← Export one day's reasoning as a portable knowledge graph
├── wardrobe_query.py        ← Ask-your-wardrobe pre-baked queries
├── rule_refs.py             ← Canonical registry tying reasoning lines to Skill rule slugs
│
│  ── Data ──
├── wardrobe.json            ← Wardrobe inventory (seed)
├── seed_calendar_events.json← Demo calendar events
├── seed_wear_history.json   ← Demo wear history (so freshness reasoning fires on fresh clones)
├── color_rules.json         ← Skin-tone color coordination rules
│
│  ── Documentation site (MkDocs Material → GitHub Pages) ──
├── book/                    ← 13 Intelligent Book chapters
├── docs/                    ← Architecture, demo script, evidence + references, business model,
│                              Track B evaluation, micro-sims (color harmony, KG, learning graph)
├── graph/                   ← graph.json + learning-graph.json + schema.md + render.md
├── skills/wearly-styling-agent/ ← Skill package (Advanced tier): 8 rule packs + validator
├── scripts/stage_docs.py    ← Copies Markdown into _docs_build/ for MkDocs to consume
├── mkdocs.yml               ← MkDocs Material config
├── requirements-docs.txt    ← Build-only docs deps (never installed on Streamlit Cloud)
│
│  ── Runtime / CI / config ──
├── .streamlit/config.toml   ← Streamlit Cloud theme + server config
├── .github/workflows/       ← tests.yml + docs.yml (matrix tests, Pages deploy)
├── tests/                   ← 237 unittest cases
├── requirements.txt         ← Runtime deps (Streamlit, pyvis)
├── workflow_diagram.md      ← Agent decision flow
├── Wearly_Product_Brief.md  ← Full product vision
└── README.md                ← This file
```

---

## The 7-Step Agent Workflow

```
Step 1: Determine Occasion
   → Reads next calendar event OR accepts an everyday request
   → Maps it to an occasion type (work / gym / dinner / formal / casual)

Step 2: Load Style Profile
   → Reads owner's body shape, skin tone, and style preferences

Step 3: Check Weather (Tool 2)
   → Fetches live weather from Open-Meteo API
   → Falls back to seasonal estimate if network is unavailable
   → Translates temperature + conditions into layering advice

Step 4: Filter Wardrobe (Tool 3)
   → Filters clothing, shoes, accessories by occasion tag and season
   → Returns candidate pool for outfit building

Step 5: Build Outfit
   → Decides between dress vs. top+bottom based on occasion formality
   → Selects from candidate pool
   → Adds shoes and up to 2 accessories
   → Adds outerwear if temperature requires it

Step 6: Check for Wardrobe Gaps (Tool 3)
   → Verifies outfit has all required pieces for the occasion
   → If gaps found: flags them and suggests shopping items

Step 7: Color Coordination Check (Tool 4)
   → Scores every outfit item against skin-tone color rules
   → Flags items that are less flattering
   → Returns a 0–100 color harmony score
```

---

## External Tools

| Tool | What It Does | Real-World Version |
|---|---|---|
| `calendar_tool.py` | Reads upcoming events from JSON mock data | Google Calendar API / Outlook API |
| `weather_tool.py` | Fetches live weather from Open-Meteo (free, no key) | Already real — calls Open-Meteo |
| `wardrobe_tool.py` | Filters wardrobe by occasion and season | Closet app / Airtable / Database |
| `color_tool.py` | Scores outfit colors against skin-tone rules | Style database / trained model |

---

## Error Handling

| Scenario | Behavior |
|---|---|
| No calendar events found | Graceful fallback to casual everyday recommendation |
| Weather API unavailable | Falls back to seasonal temperature estimate; continues normally |
| Wardrobe data file missing | Returns clear error message; stops workflow at Step 4 |
| Unknown occasion type | Maps to "casual" as safe default |
| Incomplete wardrobe (missing pieces) | Flags gap; provides shopping suggestions; still builds best available outfit |
| Unknown skin tone | Falls back to universal safe color palette |

---

## Before / After Comparison

| Dimension | Before (Manual) | After (Agent) |
|---|---|---|
| Time to decide | ~15 minutes | ~3 seconds |
| Weather check | Often forgotten | Automatic |
| Color coordination | Guesswork | Rule-based score (0–100) |
| Calendar awareness | Manual lookup | Automatic |
| Season awareness | Mental model | Data-driven |
| Reasoning | Invisible | Fully explained |
| Confidence | Low–Medium | High (structured) |

---

## Sample Output

Running `python main.py` with a "Team Strategy Meeting" on the calendar produces:

```
📅 OCCASION
  Event:    Team Strategy Meeting
  Date:     2026-04-16  10:00 AM
  Type:     WORK
  Notes:    Presenting quarterly results to senior leadership

🌤 WEATHER
  Minneapolis, MN: 52°F, Partly Cloudy
  Advice: A light jacket or coat is recommended.

⚙️ AGENT WORKFLOW STEPS
  Step 1 [✓] Determine Occasion → Found: 'Team Strategy Meeting'
  Step 2 [✓] Load Style Profile → Owner: Eatedal | warm olive | classic, elegant, minimal
  Step 3 [⚠] Check Weather     → Fallback estimate: 52°F (live API blocked in sandbox)
  Step 4 [✓] Filter Wardrobe   → 10 clothing, 4 shoes, 6 accessories for work/fall
  Step 5 [✓] Build Outfit      → 6 pieces selected
  Step 6 [✓] Check for Gaps    → Outfit complete
  Step 7 [✓] Color Check       → 100/100 — all colors excellent for warm olive skin

👗 YOUR OUTFIT
  • White Button-Down Blouse (white)
  • Black Tailored Trousers (black)
  • Black Pointed-Toe Heels (black)
  • Gold Hoop Earrings (gold)
  • Pearl Stud Earrings (white/gold)
  • Camel Wool Coat (camel)

💡 WHY THIS OUTFIT
  1. Selected White Button-Down Blouse for its business formality.
  2. Selected Black Tailored Trousers to pair with the top.
  3. Added Black Pointed-Toe Heels appropriate for the occasion.
  4. Added Gold Hoop Earrings.
  5. Added Camel Wool Coat — 52°F, light coat recommended.
  6. All colors excellent for warm olive skin tone.
```

---

## How AI Was Used in Development

This project was built with Claude (claude.ai) as a development partner:
- Designed the 7-step agent workflow structure
- Generated all Python code for tools and agent orchestration
- Wrote mock data files (wardrobe, calendar, color rules)
- Debugged tool integration and error handling
- Drafted this README and documentation

The AI-assisted development process is documented as part of the project. This is itself an example of agentic workflow — using AI as a structured collaborator, not just a search engine.

---

## Grading Alignment (Track B Rubric)

| Requirement | How This Project Satisfies It |
|---|---|
| Working agent | ✓ Runs from command line, produces recommendations end-to-end |
| 2+ external tools | ✓ 4 tools: calendar, weather (live API), wardrobe, color rules |
| Documented decision tree | ✓ 7-step workflow, documented in README and workflow_diagram.md |
| Error handling | ✓ Every tool handles failure gracefully with fallbacks |
| Before/after comparison | ✓ `--compare` flag shows full before/after; included in README |
| 10-min presentation | ✓ Run `python main.py --compare` for a live demo |

---

## Expansion Plan (Weeks 10–14)

- ✅ Real-calendar import — `.ics` upload + URL subscription (Google / Apple) shipped in `calendar_import.py`.
- ✅ Streamlit web UI with wardrobe photo + product-link import shipped in `app.py`, `link_import.py`.
- ✅ Shopping surface — wishlist, favorite stores, gap-driven suggestions shipped in `shopping_tool.py`.
- ✅ Reject-and-regenerate feedback loop shipped (`rejected_ids` / `rejection_reasons` in `run_agent`).
- ⏳ Connect Claude API for natural-language outfit narration.
- ⏳ Surface top-3 outfit alternatives instead of one.
- ⏳ Multi-day analytics on top of the compact-KG export.

---

*SEIS 666 — Digital Transformation 2.0 with Generative AI*
*University of St. Thomas | Spring 2026*
*Instructor: Daniel Yarmoluk*
