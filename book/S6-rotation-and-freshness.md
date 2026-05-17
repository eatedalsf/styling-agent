# S6 · Rotation and freshness

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains how Wearly keeps a wardrobe in rotation without ever exiling a well-loved item.*

## The concept

A working wardrobe is one whose pieces are *worn*. Two failure modes
break that:

- **Stagnation.** The same five items get worn every week; everything
  else sits unused. The closet behaves like a small wardrobe even
  though the inventory is large.
- **Exile.** A favorite shirt gets recommended so many times that an
  optimization metric — "vary the recommendations" — pushes it
  permanently off the candidate list. The wearer loses access to a
  piece they actually love.

Wearly's rotation rule is built to address the first without causing
the second.

### The freshness formula

```
freshness = 1.0
          − 0.25 × min(worn_count, 4) / 4    # frequency penalty
          − 0.25 if days_since_last_worn < 3 # recency penalty
freshness = clamp(freshness, 0.40, 1.00)
```

Two signals, both capped:

- **Frequency penalty** scales linearly from 0 wears to 4 wears and
  then *stops*. A piece worn 100 times receives the same frequency
  penalty as a piece worn 4 times.
- **Recency penalty** is binary: it applies inside a 3-day window and
  vanishes the moment the window passes.

And the floor is the rule that prevents exile:

- **Freshness ≥ 0.40, always.** Even at maximum penalty, the score
  never drops below 0.40. A much-loved piece is never pushed out of
  rotation.

### The role in selection

Freshness is a **tie-breaker, never a filter.** At Step 5, after the
candidate pool is set, items within each type are sorted by
descending freshness. Higher freshness = picked sooner *when the two
candidates are otherwise equivalent.* Its contribution to the
selection score is `0.4 × freshness`, which is small enough never to
override a formality mismatch but large enough to break ties between
two equally-eligible items.

A separate reasoning line surfaces when an item has been resting:
*"you haven't worn this in 42 days — bringing it back today"* fires
when `worn_count ≥ 1` and `days_since_last ≥ 30`. That's an
explanation surface, not a separate scoring axis.

## Why a tie-breaker, not a filter

A *filter* applied earlier in the pipeline would exclude items below
some freshness threshold from Step 4's candidate pool. The agent
would never see them; the user would never get to wear them.

Wearly's choice is the opposite. Every eligible item stays in the
pool. Freshness only matters when the rest of the rules return a tie
— same occasion, same formality, same color tier. That preserves the
**0.40 floor** as a real guarantee rather than a number that happens
to not crash the math.

## Where this knowledge comes from

- **Explicit vs. implicit feedback framing.** Hu, Koren & Volinsky
  (2008) is the canonical text on the distinction between user
  signals that are *given* (a wear-confirmation, a reject) and
  signals that are *observed* (clicks, dwell time). Wearly uses *only
  explicit* feedback — `worn_count` increments when the user taps
  "wear this today," never when they merely view it.
  ⟶ [References [11]](../docs/references.md).
- **Wardrobe-utilization framing.** Sustainable-fashion literature
  (often appearing under terms like *Project 333* or
  *cost-per-wear*) treats rotation as a wardrobe-design problem, not
  a recommender-system problem. Wearly's frequency cap at four wears
  is a design-informed approximation of that framing; no specific
  peer-reviewed source has been verified yet — see
  [docs/evidence-and-references § 3.7](../docs/evidence-and-references.md).

## What this rule deliberately does not model

- **Wear context.** A blouse worn five times to work is treated the
  same as a blouse worn five times to dinner, even though their
  rotation patterns may be different.
- **Laundry state.** Wearly does not know if a piece is currently in
  the laundry; the rotation rule assumes availability.
- **Seasonal hibernation.** A winter coat worn six times last December
  has a high `worn_count` but is effectively absent from the May
  candidate pool because Step 4's seasonal filter excludes it. The
  frequency penalty doesn't reset between seasons.

These are deliberate scope choices. The rotation rule is focused:
one freshness score, one floor, one tie-breaker — every decision
visible in the reasoning trail.

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`wear-history-rules.md`](../skills/wearly-styling-agent/wear-history-rules.md) — R2 (freshness as tie-breaker with 0.4 floor), R4 (rest-period reasoning note) |
| **Runtime code** | `history_tool.get_freshness()`, `history_tool.days_since_last_worn()`, `styling_agent._score_main_piece()` |
| **Agent step** | Step 5 (build outfit), tie-breaker only |
| **Where it surfaces** | The freshness pill on each card; the *"haven't worn in 42 days"* reasoning line |
| **Part I chapter** | [Chapter 05 · Wardrobe intelligence](05-wardrobe-intelligence.md) |
| **MicroSim** | [Wear-history freshness](../docs/sims/freshness/index.md) — the floor is visible as the slider refuses to drop below 0.40 |

---

## Key terms

- **Wear history** — per-item `worn_count` and `last_worn_date`, written only on explicit confirmation. See [Glossary](../docs/glossary.md).
- **Freshness score** — a 0.40–1.00 value combining frequency + recency. See [Glossary](../docs/glossary.md).

## Self-check

1. *(Remember)* What is the floor on the freshness score, and at which `worn_count` value does the frequency penalty stop growing?
2. *(Understand)* Why is freshness a tie-breaker rather than a filter — what would change if it were applied earlier in the pipeline?
3. *(Apply)* A user wore their navy blazer once, five days ago. Compute the freshness by hand, naming each penalty that does and does not apply.
