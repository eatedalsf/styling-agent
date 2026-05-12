# Weather rules

Temperature, precipitation, and wind → layer advice and outerwear inclusion. Implemented in `weather_tool.py` and `styling_agent.py`.

## R1 — Temperature → layer advice

| Temperature | Layer advice |
|---|---|
| < 32°F | Heavy coat, scarf, and gloves are essential. |
| < 45°F | Wear a warm coat. |
| < 58°F | A light jacket or trench coat is recommended. |
| < 70°F | Light layers work well — a cardigan or blazer is enough. |
| ≥ 70°F | No coat needed. Light, breathable clothing is ideal. |

## R2 — Precipitation → addendum

| Precip chance | Addendum |
|---|---|
| > 50% | Rain is likely — consider waterproof outerwear or an umbrella. |
| 25%–50% | Some rain possible — bring an umbrella just in case. |
| ≤ 25% | (no addendum) |

## R3 — Wind → addendum

| Wind speed | Addendum |
|---|---|
| > 20 mph | It's windy — avoid flowing or very lightweight fabrics outdoors. |
| ≤ 20 mph | (no addendum) |

## R4 — Outerwear injection

When `temp < 60°F`:

1. Look for outerwear matching the **current occasion** in the wardrobe pool.
2. If found, add it. Reasoning line: *"Added '{name}' as outerwear — temperature is {temp}°F and {layer_advice}"*.
3. If not found, **do not** force a wrong-style coat onto the outfit. Skip the layer and add `outerwear` to the gap list with an occasion-specific shopping suggestion.

This rule was added specifically to prevent a gym outfit from getting a formal work coat. The fallback is honesty (a gap), not a forced fit.

## R5 — Temperature → season mapping

| Temperature | Season (used in wardrobe filter) |
|---|---|
| < 40°F | winter |
| < 58°F | fall |
| < 75°F | spring |
| ≥ 75°F | summer |

## R6 — Fallback

If the weather API errors for any reason, fall back to a seasonal estimate (52°F, partly cloudy, light jacket advice) and mark the step status `fallback`. The agent continues; the user sees a calm note that an estimate is being used.

---

## Source basis

**Primary category:** Outfit compatibility (`docs/evidence-and-references.md` §3.2).
**Current basis:** Industry layering practice + common-sense temperature thresholds. Open-Meteo as the data source is a verified public, no-key, freely-licensed API. The temperature → layer-advice mapping is design-informed (calibrated for the prototype), not derived from a published comfort-temperature study.
