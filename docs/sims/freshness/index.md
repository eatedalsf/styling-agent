# Wear-history freshness — micro-sim

> **Learning objective.** After working through this sim, you will be
> able to explain why a much-loved item is never exiled from rotation,
> how the 0.4 floor and 3-day recency window cooperate, and where the
> score sits in the agent's selection logic (a tie-breaker, never a
> filter).
>
> **What you're looking at.** Wearly's tie-breaker for "should I pick
> this item today?" — a score in `[0.40, 1.00]` derived from two
> signals: how many times you've worn the piece, and how recently. The
> sim renders the actual formula from `history_tool.get_freshness`.
> Move the sliders; watch the score and the layer-by-layer breakdown.

<iframe
  src="main.html"
  width="100%"
  height="660"
  style="border: 1px solid #E8E0D8; border-radius: 6px;"
  loading="lazy"
  title="Wearly Freshness Score">
</iframe>

---

## The rule, in one paragraph

```
score = 1.0
       − 0.25 × min(worn_count, 4) / 4    # FREQUENCY  penalty, capped at worn_count=4
       − 0.25  if days_since_last < 3     # RECENCY    penalty, only inside the 3-day window
       clamped to [0.40, 1.00]
```

So:

- **A never-worn item is 1.00.** No penalty applied; the agent will reach for it first when there's a tie.
- **A piece you wore today** loses both penalties: a `-0.25` recency hit and (over time) a `-0.25` frequency hit. The floor catches the math at 0.40.
- **A piece you haven't worn in a month**, even if it has a high `worn_count`, climbs back up because the recency penalty falls off after 3 days.

The 3-day window is Wearly's "let it breathe" interval; the cap at `worn_count = 4` means after the fifth wear the frequency signal stops getting worse — it just sits at the same value. This is intentional: we don't want a much-loved black blouse to keep getting punished forever.

---

## How the agent uses this

This score is a **tie-breaker, never a filter.** When the agent has built the candidate pool (`filter_items_by_occasion`), it sorts items within each type — tops, bottoms, dresses, shoes, accessories — by descending freshness. Higher = picked sooner. The freshness contribution to the overall pick score is `0.4 × freshness` (see `_score_main_piece` in `styling_agent.py`); that's small enough to never override a formality mismatch, but big enough to break a tie between two equally-formal candidates.

The same number also drives the **reasoning trail line** "you haven't worn this in N days — bringing it back today" (fires when `worn_count ≥ 1` and `days_since_last ≥ 30`).

---

## Why a sim, not just docs

You can write "the freshness floor is 0.40" in prose and a reader will
skim past it. A slider that *visibly* refuses to drop below the floor —
even at `worn_count = 100, days = 0` — makes the contract real. The
intelligent-textbook pattern is: every rule the agent applies at
runtime is also a sim, not just a paragraph.

---

## What to notice

- **The floor holds.** Push `worn_count` to 100 with `days = 0` and the
  bar refuses to dip below 0.40. The clamp is the line.
- **Recency penalty is binary.** It's not a gradient — the −0.25 hit
  applies inside the 3-day window and disappears the moment
  `days_since_last` crosses 3.
- **Frequency penalty caps at 4 wears.** A fifth wear changes nothing
  about the score; a much-loved black blouse stops getting punished
  past that point.
- **A never-worn item is 1.00.** No penalty, no breakdown — the agent
  reaches for it first on ties.

## Try this

1. **Set worn_count = 0, days_since_last = 0.**
   **What you should see:** score = 1.00. No penalties apply when
   nothing has been worn yet — there's no recency *or* frequency signal
   to charge against.
2. **Set worn_count = 4, days_since_last = 2.**
   **What you should see:** both penalties fire (−0.25 frequency,
   −0.25 recency), score lands at 0.50 — clearly above the floor.
3. **Now slide days_since_last to 3.**
   **What you should see:** recency drops off, score jumps back to
   0.75. The 3-day window is a hard edge, not a gradient.
4. **Push worn_count to 100 with days = 0.**
   **What you should see:** the math wants to go below 0.40 but the
   bar clamps at exactly 0.40 — the rule's "no exile" guarantee.

## Self-check

1. *(Remember)* What is the floor on the freshness score, and at which
   `worn_count` value does the frequency penalty stop growing?
2. *(Understand)* Why is freshness a *tie-breaker* rather than a
   filter — what would change if it were applied earlier in Step 4?
3. *(Apply)* A user wore their navy blazer once, 5 days ago. Compute
   the freshness by hand and explain which penalties apply.

## Linked concept

- *Learning-graph concept:* **[freshness score (0.4 floor)](../learning-graph/index.md)**
  (id `freshness-score`, Bloom level *Analyze*).
- *Rule citations:* `[wear-history-rules#R2]`,
  `[wear-history-rules#R4]` — see
  [`wear-history-rules.md`](../../../skills/wearly-styling-agent/wear-history-rules.md).
