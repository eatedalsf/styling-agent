# Wear-history freshness — micro-sim

> **What you're looking at.** Wearly's tie-breaker for "should I pick this item today?" A score in `[0.40, 1.00]` derived from two signals: how many times you've worn the piece, and how recently. The agent uses this only to break ties between otherwise-equally-eligible items — a much-loved favorite never gets exiled (the floor is 0.40), and a fresh alternative wins when the two are equivalent on every other axis.
>
> The sim renders the actual formula from `history_tool.get_freshness`. Move the sliders, watch the score and the layer-by-layer breakdown.

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

You can write "the freshness floor is 0.40" in prose and reviewers will read past it. A slider that *visibly* refuses to drop below the floor — even at worn_count = 100, days = 0 — makes the contract real. The intelligent-textbook pattern is: every important rule earns a micro-sim, not just a paragraph.
