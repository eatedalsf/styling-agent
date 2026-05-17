# S5 · Wardrobe construction

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains the structural decisions Wearly makes when it assembles an outfit from a candidate pool.*

## The concept

After Step 4 has filtered the closet to a candidate pool that matches
the occasion and the season, Step 5 has to *build* one outfit from
it. Three structural rules govern construction:

### 1. Required pieces — what the outfit must contain

Every occasion declares a minimum type-set (see
[§S3 · Occasion and context](S3-occasion-and-context.md)). The
agent's job is to fill each required slot with one item from the
candidate pool. If a slot can't be filled, that's a *wardrobe gap*
handed to Step 6 (see [§S7 · Honest gaps](S7-honest-gaps.md)).

### 2. Dress vs. separates — the branching choice

The most consequential branch in outfit construction is *dress* vs.
*top + bottom*. For *formal* occasions (and sometimes *dinner*),
Wearly prefers a dress when one exists in the candidate pool —
because the styling literature treats dresses as a single-decision
solution to formal events, and because rejecting a dress in favor of
two separates inflates the chance of mismatch (color, formality, fit).

The branch is rule-based and inspectable — every dress-vs-separates decision cites a named rule in the reasoning trail. If no dress survives Step 4's
filter, the agent falls through to top + bottom; if a dress exists
but the user has previously rejected dresses for this occasion, the
agent also falls through.

### 3. The accessory cap of two

Wearly's rule pack caps accessories at **two per outfit**. The cap is
a styling convention — "edit the look" — and a UX one: more than two
accessories crowds the reasoning trail with notes the user can't act
on. The cap can be overridden in a future personalization pass; today
it's a hard rule.

## The outfit-as-typed-set view

The framing that makes the rules above coherent is **outfit as a
typed set**:

```
Outfit = {top, bottom, shoes, accessory*}     # separates branch
       | {dress, shoes, accessory*}           # dress branch
       | {top, bottom, shoes, outerwear, accessory*}   # cold-weather variant
```

Every item carries a type, and the outfit is a set of items whose
types satisfy the occasion's `REQUIRED_PIECES`. This is the same
*type-aware* framing the academic literature uses for outfit
compatibility — see [References [3]](../docs/references.md) (Vasileva
et al. 2018) — only Wearly does it deterministically rather than by
learning type embeddings.

## Why deterministic branching over scoring

A *scored* outfit construction would compare every dress-vs-separates
candidate by a single number and pick the winner. Wearly does not do
this:

1. **Scoring hides the why.** A user who asks "why this dress, not
   that one?" wants to read the rule, not see a difference of 0.04 in
   a learned compatibility score.
2. **The branching points are the styling decisions.** Dress vs.
   separates *is* the question; reducing it to a continuous score
   throws away the explanation surface that makes the agent useful.
3. **The reasoning trail can name the branch.** *"Picked a dress
   because formal occasions prefer dresses when one is available"* is
   a sentence; a learned score is a number.

The trade-off, as in [§S1](S1-color-and-skin-tone.md) and
[§S4](S4-weather-and-layering.md), is that the agent cannot reason
about cases the branches don't cover. A separates outfit that
*outperforms* a dress for a specific formal context is invisible to
this version of the agent. That's a roadmap item.

## Where this knowledge comes from

- **Type-aware outfit construction.** Vasileva et al. (2018) —
  type-aware embeddings show that conditioning on garment type
  improves compatibility prediction. Wearly's `REQUIRED_PIECES` map
  encodes the same axis without a learned model.
  ⟶ [References [3]](../docs/references.md).
- **Outfit as a set with constraints.** Han et al. (2017) —
  outfit-as-sequence under a learnable distribution. Wearly's
  branching is the rule-based alternative the paper positions itself
  against. ⟶ [References [2]](../docs/references.md).
- **Recommender-systems framing.** Ricci, Rokach & Shapira (2022) —
  content-based recommendation is one of the named families; Wearly's
  rule layer is one of its purest forms.
  ⟶ [References [1]](../docs/references.md).

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md) — R3 (dress-vs-separates), R4 (accessory cap); [`wardrobe-filtering-rules.md`](../skills/wearly-styling-agent/wardrobe-filtering-rules.md) — R3 (occasion-season filter) |
| **Runtime code** | `styling_agent._build_outfit()`, `wardrobe_tool.filter_items_by_occasion()` |
| **Agent step** | Step 5 (build outfit) |
| **Where it surfaces** | The outfit grid + the *"picked a dress because formal occasions prefer dresses"* reasoning line |
| **Part I chapter** | [Chapter 05 · Wardrobe intelligence](05-wardrobe-intelligence.md) and [Chapter 03 · Agent workflow](03-agent-workflow.md) (Step 5) |
| **MicroSim** | *(none yet — candidate for a future sim that walks the dress / separates / cold-weather branches)* |

---

## Key terms

- **Required pieces** — the minimum type-set for an occasion. See [Glossary](../docs/glossary.md).
- **Outfit construction** — Step 5 of the workflow. See [Glossary](../docs/glossary.md).
- **Accessory cap** — Wearly's rule that an outfit carries at most two accessories.

## Self-check

1. *(Remember)* What is Wearly's accessory cap per outfit?
2. *(Understand)* Why is dress-vs-separates a *branch* rather than a *score*?
3. *(Apply)* Given a 55°F dinner event for a user with no dress in the closet, list the type-set the agent will build, in order.
