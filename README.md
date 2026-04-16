# AI Personal Styling Agent
**SEIS 666 — Digital Transformation 2.0 | Spring 2026**
**Track B: Agentic AI System**

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

**Requirements:** Python 3.8+ (no external packages needed — uses only the standard library)

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
```

---

## Project Structure

```
styling-agent/
│
├── main.py                     ← Run this. CLI interface + before/after demo
│
├── agent/
│   └── styling_agent.py        ← Core agent logic. Orchestrates all tools.
│
├── tools/
│   ├── calendar_tool.py        ← Tool 1: Reads upcoming calendar events
│   ├── weather_tool.py         ← Tool 2: Fetches real weather (Open-Meteo API)
│   ├── wardrobe_tool.py        ← Tool 3: Filters wardrobe by occasion + season
│   └── color_tool.py           ← Tool 4: Scores outfit colors vs. skin tone
│
├── data/
│   ├── wardrobe.json           ← Wardrobe inventory (clothing, shoes, accessories)
│   ├── calendar_events.json    ← Mock calendar events
│   └── color_rules.json        ← Skin-tone color coordination rules
│
├── docs/
│   └── workflow_diagram.md     ← Agent decision flow documentation
│
└── README.md                   ← This file
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

- Connect to real Google Calendar API (replace mock JSON)
- Build a web UI with Streamlit for wardrobe photo uploads
- Add shopping integration (e.g., Nordstrom / ASOS product search)
- Add Claude API for natural-language outfit explanations
- Support multiple outfit options (top 3 recommendations)
- Add user feedback loop to learn preferences over time

---

*SEIS 666 — Digital Transformation 2.0 with Generative AI*
*University of St. Thomas | Spring 2026*
*Instructor: Daniel Yarmoluk*
