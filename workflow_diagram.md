# Agent Decision Flow — AI Personal Styling Agent

## Input Modes

```
User Input
    │
    ├── mode = "calendar"      → Read next event from calendar_events.json
    │                            (Tool 1: calendar_tool)
    │
    └── mode = "everyday"      → Accept text request: "gym", "work", "dinner", etc.
                                  Map to occasion type via OCCASION_TAG_MAP
```

## Core 7-Step Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Determine Occasion                                  │
│  Tool: calendar_tool (calendar mode) or text mapping        │
│  Output: occasion dict {type, formality, date, notes}       │
│  Error: fallback to "casual" if no events found             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 2: Load Style Profile                                  │
│  Tool: wardrobe_tool → get_owner_profile()                  │
│  Output: name, body_shape, skin_tone, style_preferences     │
│  Error: hard stop if profile file missing                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 3: Check Weather                                       │
│  Tool: weather_tool → Open-Meteo API (no key required)      │
│  Output: temp_f, condition, wind, precip%, layer_advice     │
│  Error: fallback to seasonal estimate — agent continues     │
│  Decision: sets `season` variable for wardrobe filtering    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 4: Filter Wardrobe                                     │
│  Tool: wardrobe_tool → filter_items_by_occasion()           │
│  Input: occasion_tag + season                               │
│  Output: clothing[], shoes[], accessories[] candidate pools │
│  Error: hard stop if wardrobe file missing                  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 5: Build Outfit                                        │
│  Decision tree:                                             │
│                                                             │
│  Is occasion formal or dinner AND formality >= smart_casual?│
│    YES → look for a dress first                             │
│    NO  → skip to top+bottom logic                           │
│                                                             │
│  Is occasion = gym?                                         │
│    YES → select activewear items (up to 2)                  │
│    NO  → select top + bottom                                │
│                                                             │
│  Add shoes (first matching item from pool)                  │
│  Add accessories (up to 2)                                  │
│  Is temp < 60°F? → Add outerwear                           │
│                                                             │
│  Output: outfit[] — list of selected item dicts             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 6: Check for Wardrobe Gaps                             │
│  Tool: wardrobe_tool → check_gaps()                         │
│  Input: outfit[], REQUIRED_PIECES[occasion_tag]             │
│  Output: gaps[] — list of missing garment types             │
│  If gaps found:                                             │
│    → Add gap to result                                      │
│    → Add shopping_suggestions from SHOPPING_SUGGESTIONS map │
│    → Add explanation to reasoning[]                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  STEP 7: Color Coordination Check                            │
│  Tool: color_tool → score_outfit_colors()                   │
│  Input: outfit[], owner skin_tone                           │
│  Output: score (0–100), notes[], flags[]                    │
│  Scoring: +8 for best colors, +4 for good, -10 for avoid    │
│  All notes and flags appended to reasoning[]                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  FINAL RESULT                                                │
│  {                                                          │
│    recommendation: outfit[],                                │
│    reasoning: string[],      ← full explainability trail   │
│    gaps: string[],                                          │
│    shopping_suggestions: string[],                          │
│    color_score: {score, notes, flags},                      │
│    weather: weather dict,                                   │
│    event: occasion dict,                                    │
│    steps: step_log[]         ← workflow audit trail         │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

## Error Handling Summary

| Step | Failure Mode | Response |
|------|-------------|----------|
| Step 1 | No calendar events | Fallback to casual default |
| Step 2 | Profile file missing | Hard stop with error message |
| Step 3 | Weather API blocked | Seasonal fallback, continues |
| Step 4 | Wardrobe file missing | Hard stop with error message |
| Step 5 | No clothing in pool | Empty outfit, flagged in output |
| Step 6 | Missing required pieces | Gaps flagged, shopping suggested |
| Step 7 | Unknown skin tone | Universal palette fallback |

## Data Flow Summary

```
calendar_events.json  →  calendar_tool    →  occasion context
weather API           →  weather_tool     →  temp, condition, advice
wardrobe.json         →  wardrobe_tool    →  filtered clothing pools
color_rules.json      →  color_tool       →  score + flags
                                               ↓
                               styling_agent.py orchestrates all
                                               ↓
                                    main.py displays result
```
