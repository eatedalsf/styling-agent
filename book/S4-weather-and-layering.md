# S4 · Weather and layering

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains how temperature shapes the outfit and why Wearly's layering rules are bands rather than continuous functions.*

## The concept

Weather enters the outfit decision through two channels:

1. **Temperature → layering thresholds.** Below specific cut-offs the
   agent injects outerwear or switches to heavier fabrics.
2. **Temperature → season tag.** Each item carries a season set
   (`spring`, `summer`, `fall`, `winter`, or `all`); the season tag
   derived from the current temperature filters the candidate pool at
   Step 4.

The temperature bands Wearly uses:

| Range | Layer guidance | Season tag |
|---|---|---|
| < 40°F | Heavy outerwear required; layering encouraged | winter |
| 40–59°F | Light outerwear injected when an occasion-matching piece exists | fall |
| 60–74°F | No outerwear; long-sleeve or short-sleeve as the wearer prefers | spring |
| 75–84°F | Lightweight, breathable fabrics preferred | summer |
| ≥ 85°F | Lightweight is the default; the agent flags heavy items as a mismatch | summer |

The **<60°F outerwear threshold** is the most visible rule. Below 60,
the agent looks for an outer piece in the candidate pool whose tags
match the current occasion. If none exists, that becomes a
[*qualified gap*](S7-honest-gaps.md) — descriptive shopping
suggestion only, never a forced fit.

## Live weather vs. seasonal fallback

The agent calls **Open-Meteo** at runtime — an unauthenticated weather
API. If the call fails or the user is offline, the agent falls back
to a **seasonal estimate** based on the month of the current date.
The fallback is conservative: it picks the milder end of the seasonal
range so the agent never recommends a coat when the actual weather
might not warrant it.

The fallback is documented as a *transparent degradation* in the
reasoning trail — *"using seasonal estimate (October ≈ 55°F)"* —
because hiding the degradation would violate the honesty contract.

## Why bands, not a continuous function

A continuous function ("for every 1°F drop, add 0.07 of an outerwear
unit") would let the agent reason about more cases. It would also be
much harder to audit. Bands are auditable: a user sees that 58°F sits
in the *light outerwear* band and the rule fires; 62°F sits in the
*no outerwear* band and the rule doesn't. The boundary cases (59 vs.
60, 39 vs. 40) are deliberately small in number so they can be
reviewed.

The cost is the obvious one: a 60°F day with high wind reads, to the
agent, like any other 60°F day. The agent doesn't reason about wind
or humidity today; that's a roadmap item in
[Chapter 11](11-product-roadmap.md), not a current rule.

## Where this knowledge comes from

Layering thresholds are general practice in apparel guidance — there
is no foundational paper to cite for "below 60°F, add a jacket." The
threshold itself is a design choice; the rule pack documents it
explicitly so a future contributor can adjust it without guessing
where the number came from.

The framing of weather as *context that conditions* the recommendation
(rather than a feature that drives a score) is the same framing used
in human-centered-AI guidance more broadly — see
[References [9]](../docs/references.md) (Amershi et al. 2019,
*"Make clear what the system can do"*). The temperature band is the
system *telling* the wearer how it interpreted the day; that's an
explanation surface, not a hidden weighting.

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`weather-rules.md`](../skills/wearly-styling-agent/weather-rules.md) — R1 (temperature bands), R4 (outerwear injection threshold), R6 (seasonal fallback) |
| **Runtime code** | `weather_tool.get_weather_for_date()`, `styling_agent._inject_outerwear()` |
| **Agent step** | Step 3 (check weather), Step 5 (build outfit) |
| **Where it surfaces** | The weather chip + the *"injecting light outerwear because temp is 55°F"* reasoning line |
| **Part I chapter** | [Chapter 07 · Calendar & weather context](07-calendar-weather-context.md) |
| **MicroSim** | *(none yet — candidate for a future sim that maps temperatures onto layers)* |

---

## Key terms

- **Weather context** — live Open-Meteo data with seasonal fallback. See [Glossary](../docs/glossary.md).
- **Layer threshold** — the temperature cut-offs (<40, <60, 60–74, 75–84, ≥85°F) that drive outerwear and season filtering.
- **Seasonal fallback** — the conservative seasonal estimate used when the live API is unreachable.

## Self-check

1. *(Remember)* What is the temperature threshold that triggers outerwear injection in Wearly today?
2. *(Understand)* Why does Wearly use temperature bands rather than a continuous function?
3. *(Apply)* It's 55°F and the user has no outerwear tagged *work*. What does the agent surface, and why is it not a forced fit?
