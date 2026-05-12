# Wear history rules

How worn-count and last-worn date influence outfit choice. Phase 4. Today's prototype carries a small first-pass implementation as a foundation.

## R1 — Data shape

`data/wear_history.json` (created in Phase 4):

```json
{
  "C001": { "worn_count": 7, "last_worn_date": "2026-05-10", "last_event": "Team Strategy Meeting" },
  "C006": { "worn_count": 12, "last_worn_date": "2026-05-11", "last_event": "Dinner with Clients" }
}
```

Keyed by wardrobe item `id`. Items not in the dict are treated as **fresh** (never worn).

## R2 — Freshness score

For each item:

```
freshness = 1.0   # never-worn baseline

if item in history:
    # Decay by both frequency and recency
    days_since_last = (today - last_worn_date).days
    freshness -= 0.25 * min(worn_count, 4) / 4      # frequency penalty
    freshness -= 0.25 if days_since_last < 3 else 0  # recency penalty

freshness = clamp(0.4, 1.0)
```

The floor of 0.4 prevents a much-loved piece from being permanently exiled.

## R3 — Tie-breaker, not a filter

Freshness is a **tie-breaker** within the outfit builder, not a filter. Two equally-eligible items at the same step → prefer the fresher one.

A user's favorite piece is still allowed. The agent doesn't pretend the user doesn't have favorites; it just spreads the love.

## R4 — Recently-worn note

If the chosen item has been worn within the last 3 days, surface it in the reasoning trail:

> *"Selected '{name}' — you've worn this recently, but it's the strongest fit for today's occasion."*

This is **honest narration**, not an apology. The user might genuinely want to wear it again.

## R5 — Underused-item nudge

If a high-quality item hasn't been worn in 45+ days and would be eligible today, surface it:

> *"Considered '{name}' — you haven't worn it in a while and it would suit today's occasion."*

The agent doesn't *automatically* swap it in — it surfaces the option. The user can ask to regenerate with that item if they want.

## R6 — Confirmation triggers a write

When the user confirms an outfit (a future "Wear today" button on the outfit screen), `history_tool.record_wear(item_ids, event)` increments `worn_count` and updates `last_worn_date` for every item in the accepted outfit.

The agent never writes to wear history without explicit user confirmation. A user can ignore the recommendation entirely and the history stays unchanged.

## R7 — Privacy

Wear history is purely local in the prototype. In production it lives encrypted per-user and is deletable in one tap. The system does not surface aggregated wear-history insights ("you wear black 80% of the time") without opt-in — wear history is decision data, not feedback for the user.
