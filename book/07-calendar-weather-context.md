# 07 · Calendar & weather context

Two external context streams enter the agent every run. This chapter documents both.

## Calendar

### Today: mock JSON

The prototype reads `calendar_events.json` — a list of 6 demo events spanning a week. Each event has:

```json
{
  "id": "EVT001",
  "title": "Team Strategy Meeting",
  "date": "2026-05-12",
  "time": "10:00 AM",
  "type": "work",
  "formality": "business",
  "notes": "Presenting quarterly results to senior leadership"
}
```

`calendar_tool.get_upcoming_events(days_ahead=7)` filters to the next N days and returns the next chronological event.

### Production: real calendars

The architecture is **calendar-source-agnostic**. The agent only depends on the shape of an event. To swap in a real source we replace the body of `get_upcoming_events()`:

| Source | Implementation path |
|---|---|
| Google Calendar | OAuth flow, `google-api-python-client`, fetch primary calendar, map fields. |
| Apple Calendar | No public API on iOS. Prototype uses `.ics` upload; production needs a native app or CalDAV. |
| Outlook 365 | Microsoft Graph API, similar OAuth pattern. |
| `.ics` upload | A small stdlib parser; suitable for the prototype today. |

A future `wearly/lib/ics_import.py` will accept an uploaded `.ics`, extract events for the next seven days, and write them into the same shape that `calendar_events.json` uses today. No agent changes needed.

### Privacy

Calendar data never leaves the device in the prototype. Production would store events server-side per user, encrypted at rest, with explicit revocable consent.

---

## Weather

### Today: live Open-Meteo

`weather_tool.get_weather()` calls `api.open-meteo.com/v1/forecast`. No API key, no rate-limit issues for the demo. The default location is hard-coded to Minneapolis (44.9778, -93.2650) — production lets the user pick a city or opt in to geolocation.

The tool returns:

```python
{
  "city": "Minneapolis, MN",
  "temp_f": 58.0,
  "feels_like_f": 49.0,
  "condition": "Partly Cloudy",
  "wind_mph": 13.8,
  "precip_chance_pct": 5,
  "layer_advice": "A light jacket or trench coat is recommended."
}
```

`layer_advice` is generated from `temp_f`, `precip_chance_pct`, and `wind_mph` via simple thresholds:

| Temp | Advice |
|---|---|
| < 32°F | "Heavy coat, scarf, and gloves are essential." |
| < 45°F | "Wear a warm coat." |
| < 58°F | "A light jacket or trench coat is recommended." |
| < 70°F | "Light layers work well — a cardigan or blazer is enough." |
| ≥ 70°F | "No coat needed. Light, breathable clothing is ideal." |

Plus precipitation and wind addenda when thresholds are crossed.

### The fallback path

If the network call raises *any* exception (timeout, DNS, blocked, rate-limited), the tool returns a deterministic seasonal estimate:

```python
{ "temp_f": 52, "condition": "Partly Cloudy", "layer_advice": "A light jacket or coat is recommended.", ... }
```

The result dict includes a `"error"` string explaining the fallback. The UI surfaces this as a fallback status on the workflow card. The demo never breaks because of a network blip.

### Privacy

Location is a single lat/lon used only for the weather call. Open-Meteo doesn't require an account. No reverse geocoding is performed; the city name is a display string only.

---

## How calendar + weather drive the outfit

| Input | Influences |
|---|---|
| Event type | Occasion tag → wardrobe pool |
| Event formality | Dress-vs-separates branching, accessory choice |
| Temperature | Season (used in pool filter), outerwear inclusion |
| Condition | Layer advice surfaced in the UI; future: fabric choice |
| Wind | Layer advice; future: flow-fabric avoidance |
| Precip% | Layer advice; future: waterproof outerwear preference |

The connection between context and recommendation is **explicit in the reasoning trail**. Open the **"Full Agent Reasoning"** expander on any outfit result and you'll see lines that name temperature and weather as drivers — not just "outerwear added" but "outerwear added because it's 58°F."

## Where to verify

- The mock data: `calendar_events.json`.
- The calendar tool: `calendar_tool.py`.
- The weather tool: `weather_tool.py`.
- The agent step that consumes both: `styling_agent.py` (steps 1 and 3).
