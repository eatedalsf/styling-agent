# Wearly — Architecture

> Snapshot of the current Wearly prototype as of Phase 2.
> Supplements `workflow_diagram.md` (which documents the agent's decision flow)
> with a system-level view of code, data, surfaces, and dependencies.

---

## 1. System overview

Wearly is a single-process Python application with two user-facing surfaces and one deterministic reasoning core.

```
┌────────────────────────────────────────────────────────────────────┐
│  USER SURFACES                                                     │
│  ┌───────────────────────┐         ┌──────────────────────────┐    │
│  │   CLI                 │         │   Streamlit web UI       │    │
│  │   main.py             │         │   app.py                 │    │
│  │   --everyday / --     │         │   Section nav · home ·   │    │
│  │   compare / calendar  │         │   today · wardrobe ·     │    │
│  │                       │         │   profile · before/after │    │
│  └──────────┬────────────┘         └────────────┬─────────────┘    │
│             │                                   │                  │
│             ▼                                   ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │   AGENT CORE                                                 │  │
│  │   styling_agent.py · run_agent(mode, everyday_request,       │  │
│  │                                rejected_ids, rejection_…)    │  │
│  │   Seven-step deterministic workflow.                         │  │
│  └──────────┬───────────────────────────────────────────────────┘  │
│             │                                                      │
│             ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │   TOOLS                                                      │  │
│  │   calendar_tool · weather_tool · wardrobe_tool · color_tool  │  │
│  └──────────┬───────────────────────────────────────────────────┘  │
│             │                                                      │
│             ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │   DATA                                                       │  │
│  │   calendar_events.json · wardrobe.json · color_rules.json    │  │
│  │   Open-Meteo API (live, with seasonal fallback)              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Repository layout (current, flat)

```
styling-agent/
├── main.py                              # CLI entry
├── app.py                               # Streamlit web entry — full UI
├── styling_agent.py                     # Agent orchestration (7-step workflow)
├── calendar_tool.py                     # Tool 1: calendar events from JSON
├── weather_tool.py                      # Tool 2: live Open-Meteo + fallback
├── wardrobe_tool.py                     # Tool 3: wardrobe + owner profile
├── color_tool.py                        # Tool 4: skin-tone color scoring
├── wardrobe.json                        # Owner + clothing/shoes/accessories
├── calendar_events.json                 # Mock upcoming events
├── color_rules.json                     # Per-skin-tone palettes
├── requirements.txt                     # streamlit
├── .streamlit/config.toml               # Brand theme + Cloud headers
├── .gitignore
├── README.md
├── workflow_diagram.md                  # Per-step agent decision flow
├── Wearly_Product_Brief.md              # Product vision (source of truth)
├── Wearly_References_and_Course_Context.md  # Course/reference canon
├── docs/
│   ├── architecture.md                  # This file
│   └── demo_script.md                   # 10-min demo skeleton
└── tests/
    ├── test_agent_smoke.py              # End-to-end agent tests
    ├── test_tools.py                    # Per-tool tests
    └── test_data_integrity.py           # JSON shape + ID uniqueness
```

The repo is intentionally flat for now. The Master Implementation Plan's restructure into `wearly/`, `wearly/tools/`, `wearly/ui/`, `wearly/lib/`, `book/`, `graph/`, `skills/` is deferred until the data-model split in a later phase makes the package boundary unavoidable. Flat keeps cognitive overhead low while the product surface is still evolving.

---

## 3. Agent core — `styling_agent.py`

The single entry point is:

```python
run_agent(
    mode: str = "calendar",
    everyday_request: str | None = None,
    rejected_ids: list[str] | None = None,
    rejection_reasons: list[dict] | None = None,
) -> dict
```

It runs the seven-step workflow documented in `workflow_diagram.md`. The result dict contract is:

| Key | Type | Used by |
|---|---|---|
| `steps` | list of `{step, name, status, output}` | Workflow expander |
| `recommendation` | list of wardrobe item dicts | Outfit card |
| `reasoning` | list of strings | Reasoning expander |
| `gaps` | list of strings | Wardrobe-gap alert |
| `shopping_suggestions` | list of strings | Gap-suggestions list |
| `color_score` | `{score, notes, flags}` | Color harmony card |
| `weather` | weather dict | Weather card |
| `event` | event dict | Occasion card |
| `profile` | owner profile dict | Color card (skin tone display) |
| `rejected_context` | `{ids, reasons}` | "What changed" banner |
| `error` | string or None | Error display |

This contract is the only contract between agent and UI. Both `main.py` and `app.py` consume it; both tests in `tests/test_agent_smoke.py` assert against it.

### Reject & regenerate

If `rejected_ids` are supplied, Step 4 (wardrobe filter) drops them from every pool. Step 5 prepends one `"Skipping 'X' — you flagged it as: Y"` line per rejection reason to the reasoning trail. Step 4's `output` notes the exclusion count. This is the agent-not-chatbot signal: the user can push back with a reason, the agent re-runs, and the change is explained.

---

## 4. Tools — boundary contracts

| Tool | File | Reads | Returns |
|---|---|---|---|
| Calendar | `calendar_tool.py` | `calendar_events.json` | `{success, events, error}` |
| Weather | `weather_tool.py` | Open-Meteo API (`api.open-meteo.com`) | `{success, weather, error}` — never raises; falls back to a seasonal estimate on any network error |
| Wardrobe | `wardrobe_tool.py` | `wardrobe.json` | `get_wardrobe()`, `get_owner_profile()`, `filter_items_by_occasion(tag, season)`, `check_gaps(outfit, required)` |
| Color | `color_tool.py` | `color_rules.json` | `get_color_rules(skin_tone)`, `score_outfit_colors(items, skin_tone)` — returns score 0–100 + flags |

Every tool uses a `_find_data_file()` helper that searches three candidate paths (`../data/`, `..`, same dir), so the flat layout works today and the structured layout will work later without code changes.

---

## 5. UI surfaces

### 5.1 CLI — `main.py`

- Argparse front end: `python main.py`, `python main.py --everyday "gym"`, `python main.py --compare`.
- Reconfigures stdout to UTF-8 on Windows consoles using legacy codepages (so box-drawing and emoji don't crash on cp1256 / cp1252).
- Pretty-prints the agent's result dict with ANSI colors.

### 5.2 Streamlit web app — `app.py`

Single-file Streamlit module. Structure inside:

```
[ page config + heavy CSS block ]
[ session-state init + helpers ]
[ top app bar: wordmark · "Prototype" tag · profile chip ]
[ section nav row: Home · Today · Wardrobe · Profile · Before/After ]
[ sidebar: collapsed, secondary controls only ]
[ section renderers:
    _render_home()
    _render_today()
    _render_wardrobe()  # coming-soon stub
    _render_profile()   # mock profile from wardrobe.json
    _render_demo()      # before/after comparison + live agent run
    _render_outfit_result()  # shared by Today + Demo
]
[ section router: dispatches on st.session_state["section"] ]
```

State is held in `st.session_state`:

| Key | Purpose |
|---|---|
| `section` | Current visible screen (`home` / `today` / `wardrobe` / `profile` / `demo`) |
| `result` | Most recent agent output dict |
| `last_run` | `{mode, everyday_request}` of the most recent invocation — used by Regenerate |
| `rejected_ids` | Item IDs the user has rejected this session |
| `rejection_reasons` | Parallel list of `{item_id, item_name, reason}` |
| `signed_in` | Mock flag — always True; real auth is future work |
| `everyday_choice` | Sidebar selectbox state |

Every agent invocation goes through `_run_and_store()`, which records `last_run` so the Regenerate button can replay the same mode with accumulated rejection context.

---

## 6. Visual system

| Token | Hex | Role |
|---|---|---|
| Paper | `#F8F4ED → #F4EDE3` | Page background (subtle vertical gradient) |
| Card surface | `#FDFAF7` | Cards, sidebar, pills |
| Divider | `#EDE5DC` / `#E8E0D8` | Borders, dividers, subtle outlines |
| Ink | `#1C1917` | Headlines, body text on cards |
| Body | `#4A3D36` / `#7C6F64` | Secondary text |
| Eyebrow | `#A8937E` / `#B8A99A` | Small-caps labels |
| Accent — primary | `#C17F5A` | Primary CTA, terracotta wordmark mark, accent strip on Today card |
| Accent — deep | `#9F5A36` | Strong score color, "After" comparison column label |
| Accent — warm warning | `#8A4A20` | Color flag text |
| Warm muted | `#FAF3EE` | "After" comparison column, event-type pill background |

Fonts: `DM Serif Display` for marquees, `DM Sans` for body. No system fonts used.

No emoji are rendered in the product UI. Outfit items use real color swatches (16px circles filled with the garment's display hex via the `COLOR_HEX` mapping in `app.py`). The agent-process row uses numbered pills (`01 Calendar → 05 Outfit`).

---

## 7. Data files

### `wardrobe.json`
Top-level keys: `owner` (name, body_shape, skin_tone, style_preferences, preferred_fit), `clothing` (16 items), `shoes` (5 items), `accessories` (6 items). Every item has `id`, `name`, plus type/color/formality/season/tags as appropriate. All IDs are unique (asserted by `test_data_integrity.py`).

### `calendar_events.json`
List of 6 demo events spanning 2026-05-12 → 2026-05-17, covering all five occasion types (work, dinner, gym, casual, formal_event). Each event has `id`, `title`, `date` (YYYY-MM-DD), `time`, `type`, `formality`, `notes`.

### `color_rules.json`
Per-skin-tone palettes: `best_colors`, `good_colors`, `avoid_colors`, `metal_preference`, `notes`. Currently three tones: `warm olive`, `cool fair`, `deep warm`.

---

## 8. Dependencies

| Layer | Dependency | Why |
|---|---|---|
| Runtime | `streamlit>=1.30` | Web UI. Declared in `requirements.txt`. |
| Runtime | Python stdlib | Everything else — `urllib`, `json`, `datetime`, `argparse`, `os`, `sys`. |
| External | Open-Meteo (no key) | Live weather. Graceful seasonal fallback on any error. |
| Test | Python stdlib `unittest` | No third-party test framework needed. Pytest will discover the same tests if installed. |
| Deploy | Streamlit Community Cloud | `.streamlit/config.toml` is preconfigured (`headless = true`). |

No paid APIs, no secrets, no authentication. The "profile" surface is a mock read-only display sourced from `wardrobe.json`.

---

## 9. Error handling

| Failure | Behavior |
|---|---|
| Calendar JSON missing | Tool returns `success=False` with error string; agent step 1 falls back to casual everyday. |
| Calendar empty (no events in window) | Step 1 falls back to casual everyday; the home today-card shows a friendly empty state. |
| Weather API blocked / slow | `weather_tool` catches all exceptions, returns a seasonal estimate, logs the error in the result dict. UI shows the estimate; CLI notes the fallback. |
| Wardrobe JSON missing | Hard stop at step 4 with a clear error message. |
| Color rules missing skin tone | Falls back to a universal safe palette. |
| Unknown everyday occasion string | Maps to "casual". |
| Outerwear needed but none occasion-appropriate | Skips outerwear; adds a wardrobe-gap entry with a shopping suggestion. |
| Rejected items deplete the pool | Agent still produces the best-available outfit; gap detection catches missing required pieces. |

---

## 10. What's deliberately not here yet

Documented as future work in `Wearly_Product_Brief.md`:

- Real Google / Apple calendar integration (mock JSON only today).
- Real auth — profile is read-only mock.
- Wardrobe builder (photo upload, URL import, background removal).
- Wear history rotation.
- Shopping integration with favorite stores.
- Multi-user / family profiles.
- Intelligent Book, Knowledge Graph, Skills package.
- Repository restructure into `wearly/` subpackages.
- CI pipeline (tests exist but no GitHub Actions yet).

These are visible-but-stubbed in the UI (Wardrobe coming-soon screen, Profile disabled "Sign in" buttons) so the roadmap is part of the experience rather than hidden.
