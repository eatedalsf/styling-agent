# S7 · Honest gaps

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains what counts as a wardrobe gap, when the agent surfaces one, and why the tone discipline matters more than the detection mechanic.*

## The concept

A **wardrobe gap** is a required piece-type the user does not own (or
does not currently have season-appropriate) for the occasion the
agent is reasoning about. Detection is mechanical:

```
for each required_type in REQUIRED_PIECES[occasion]:
    if no item in candidate_pool has type == required_type:
        gaps.append(required_type)
```

That's the easy part. The hard part is what happens *next*: how the
agent talks about the gap, and what it asks the user to do about it.

### The qualified-gap rule

A raw gap is not automatically surfaced. Wearly applies a second
check:

- **Is the missing piece plausibly shoppable for this occasion?**
  A user attending a one-off costume event isn't sensibly recommended
  a costume purchase. A user attending an office offsite without a
  blazer probably is.

A gap that passes the second check is a **qualified gap** (see the
[Glossary](../docs/glossary.md)). Only qualified gaps surface as
shopping suggestions; unqualified gaps surface in the reasoning trail
as honest scope notes but never as suggestions.

### The tone discipline

A qualified gap surfaces with a specific, body-positive tone:

> *"A camel-toned blazer would round out your work-wear options."*

It does **not** say:

- *"You need a blazer."* — implies the user has failed.
- *"You're missing a blazer."* — same implication, softer wording.
- *"Buy a blazer here →"* — promotional, transactional, not stylist
  language.

The wording rule is **descriptive, not promotional.** The tone is
that of a stylist friend pointing out a useful addition, not of a
recommendation engine routing the user to a purchase funnel.

## Why this discipline matters

There is a default failure mode in product recommenders: every gap
becomes a sales opportunity. The opposite failure mode is also real:
every gap gets hidden because the system doesn't want to seem
"pushy." Wearly takes a third position — **honest gaps over forced
fits.**

- **Honest gap.** *"We don't have a formal-tagged dress in your
  closet. A simple knee-length dress in a deep neutral would round
  out your formal options."* Surfaced once, with a reason.
- **Forced fit.** Wearly's *casual* black dress gets re-tagged
  *formal* under the hood because the system would rather recommend
  something than nothing. This is the failure mode Wearly explicitly
  refuses.

The forced fit is worse than the gap, because the user trusts the
agent less the next time. The honest gap is a trust-builder; it tells
the user the truth and gives them a clear, low-pressure path forward.

### The favorite-stores connection

If a user has saved retailer preferences (a *local-only* setting
inside the prototype), a qualified gap can be tagged with one of the
saved stores: *"Aritzia tends to carry a clean structured blazer in
this style."* That tag is a personalization, never a transmission —
the prototype does not contact those retailers.

## Where this knowledge comes from

- **Recommender systems as decision support, not sales channels.**
  Ricci, Rokach & Shapira (2022) frames recommendation as a
  multi-criteria decision-support task. Wearly's gap rule is the
  decision-support framing applied to wardrobe completeness rather
  than purchase.
  ⟶ [References [1]](../docs/references.md).
- **The Microsoft HCI guidelines for AI products.** Amershi et al.
  (2019) — "Convey the system's capabilities and limits clearly,"
  "Support efficient correction." A qualified gap with a body-positive
  tone is both — it tells the user what the agent can't fulfill *and*
  gives them a path to correct it.
  ⟶ [References [9]](../docs/references.md).
- **Google PAIR Guidebook on trust calibration.** PAIR frames trust
  as something built through honest acknowledgement of limits, not
  through over-promising. The qualified-gap rule is the
  trust-calibration choice in Wearly.
  ⟶ [References [10]](../docs/references.md).

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`shopping-gap-rules.md`](../skills/wearly-styling-agent/shopping-gap-rules.md) — R1 (a required-type miss is a gap), R2 (cold-weather outerwear), R3 (descriptive, never promotional), R5 (*"would round out your wardrobe"*, never *"you need"*) |
| **Runtime code** | `styling_agent._detect_gaps()`, `shopping_tool.get_favorite_stores()` |
| **Agent step** | Step 6 (check gaps) |
| **Where it surfaces** | The shopping-suggestion strip below the outfit grid; the *"would round out"* reasoning line |
| **Part I chapter** | [Chapter 08 · Shopping-gap logic](08-shopping-gap-logic.md) |
| **MicroSim** | *(none yet — candidate for a future sim that walks raw gap → qualified gap → tone-disciplined suggestion)* |

---

## Key terms

- **Gap** — a required piece-type the user does not own for the current occasion. See [Glossary](../docs/glossary.md).
- **Qualified gap** — a gap that's also plausibly shoppable for this occasion. See [Glossary](../docs/glossary.md).
- **Favorite stores** — locally-saved retailer hints used to personalize gap suggestions without transmission. See [Glossary](../docs/glossary.md).

## Self-check

1. *(Remember)* What two conditions must hold for a gap to be *qualified*?
2. *(Understand)* Why are shopping suggestions descriptive rather than promotional in Wearly?
3. *(Apply)* A user attends a work offsite and the closet has no blazer. Trace the gap from detection through qualification through the user-facing reasoning line.
