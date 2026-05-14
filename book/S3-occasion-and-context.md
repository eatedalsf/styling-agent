# S3 · Occasion and context

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains why Wearly classifies events into five canonical occasions and how free-text and calendar entries map onto that vocabulary.*

## The concept

Wearly classifies every event into exactly **one of five occasion tags**:

| Tag | Examples |
|---|---|
| **work** | meetings, presentations, conferences, the office. |
| **gym** | workouts, yoga, training sessions. |
| **dinner** | restaurant dinners, dates, drinks. |
| **formal** | weddings, galas, black-tie events, interviews. |
| **casual** | weekends, errands, brunch, friends — the default when nothing else fits. |

Why these five? Because they are the smallest set that produces
distinguishable styling outcomes. A taxonomy with twenty tags would
ask the user (or the calendar parser) to make distinctions the rule
layer can't act on. A taxonomy with two tags ("formal" vs.
"informal") collapses the gym and the formal-gala cases into the same
rule branches. Five is the minimum that triggers genuinely different
behavior — gym needs activewear, formal needs a dress (or formal
separates), work needs a top + bottom, etc.

Each tag declares its **required pieces** — the minimum type-set the
outfit must contain:

```python
REQUIRED_PIECES = {
    "work":    {"top", "bottom"},
    "gym":     {"top", "bottom"},        # activewear-tagged
    "dinner":  {"top", "bottom"},        # or "dress" via S3 branching
    "formal":  {"dress"},                # or formal "top" + "bottom"
    "casual":  {"top", "bottom"},
}
```

A type missing from the candidate pool is what Step 6 detects as a
*wardrobe gap* (see [§S7 · Honest gaps](S7-honest-gaps.md)).

The mapping from free-text events to tags is rule-based, not learned.
A calendar entry titled *"Investor pitch"* maps to *work*; *"Sarah's
wedding"* maps to *formal*; *"Gym class"* maps to *gym*. The agent
falls back to *casual* whenever no signal in the event title resolves.

## Where this knowledge comes from

- **Outfit-as-typed-set framing.** Vasileva et al. (2018) formalized
  the *type-aware* axis of outfit compatibility — that a top, a
  bottom, and a shoe are different kinds of things that combine under
  different constraints. Wearly's `REQUIRED_PIECES` table uses that
  exact axis, deterministically rather than learned.
  ⟶ [References [3]](../docs/references.md).
- **Occasion-conditioned recommendation.** Han et al. (2017) treat an
  outfit as a sequence whose distribution depends on the wearer and
  the context. Wearly's occasion tag plays the same role — it's the
  context that conditions which rule branches fire.
  ⟶ [References [2]](../docs/references.md).

## Trade-offs of a five-tag taxonomy

- **Niche occasions collapse.** A semi-formal cocktail party usually
  ends up tagged *dinner*; a beach wedding ends up tagged *formal*.
  The taxonomy doesn't capture those niches at runtime; the rule
  layer compensates with weather and modesty preferences when those
  are set.
- **The taxonomy is opinionated about formality.** *Work* is
  business-casual by default, not boardroom-formal; *formal* always
  triggers the dress-vs-separates branch in [§S5](S5-wardrobe-construction.md).
  The user can override at the request-text level.
- **The mapping is auditable.** Because the mapping is rules, not a
  classifier, a misclassification is a fixable bug, not an opaque
  inference error.

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md) — R1 (canonical tags), R2 (required pieces), R3 (dress-vs-separates), R4 (accessory cap of two) |
| **Runtime code** | `occasion_tool.classify_occasion()` |
| **Agent step** | Step 1 (determine occasion) |
| **Where it surfaces** | The occasion chip at the top of the reasoning trail; the gap notes at Step 6 |
| **Part I chapter** | [Chapter 03 · Agent workflow](03-agent-workflow.md) (Step 1) and [Chapter 04 · Styling knowledge base](04-styling-knowledge-base.md) |
| **MicroSim** | *(none yet — candidate for a future sim that maps free-text events onto tags)* |

---

## Key terms

- **Occasion tag** — one of *work, gym, dinner, formal, casual*. See [Glossary](../docs/glossary.md).
- **Required pieces** — the minimum type-set an occasion needs. See [Glossary](../docs/glossary.md).
- **Calendar context** — upcoming events read at Step 1; falls back to *casual* when none. See [Glossary](../docs/glossary.md).

## Self-check

1. *(Remember)* Name the five canonical occasion tags.
2. *(Understand)* Why five tags rather than two or twenty?
3. *(Apply)* A calendar event titled *"Coffee with Maya"* with no other context. Which tag does the agent assign, and which `REQUIRED_PIECES` set does that trigger?
