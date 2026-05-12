# 02 · The user problem

## The fifteen-minute closet

Most people spend somewhere around **fifteen minutes** every morning standing in front of their closet. The decision is small, the friction is significant: the user juggles four streams of context at once —

1. **What's on the calendar today?** A client meeting reads differently than a gym session.
2. **What's the weather?** Step outside underdressed and the whole day reads wrong.
3. **What's in the closet, and what fits the occasion?** Half the items don't suit today, half are in the laundry.
4. **What flatters me?** Color, fit, body shape, modesty preferences, comfort.

A chatbot can answer one of these. A human stylist can hold all four at once but isn't in the user's closet every morning. A structured agent that *reasons through all four* is the missing thing.

## The cost of the decision

| Cost | Manual planning | Wearly |
|---|---|---|
| Time per outfit | ~15 minutes | ~3 seconds |
| Weather check | Often forgotten | Automatic |
| Calendar awareness | Manual lookup | Automatic |
| Color coordination | Guesswork | 0–100 score with per-item flags |
| Reasoning | Invisible (gut feel) | A numbered trail you can read |
| Confidence | Low–medium | High (the agent can defend every choice) |
| Reusability | Re-done from scratch every morning | The closet learns over time |

## The user's mental moments

Three moments shape the design:

1. **"I have ninety seconds before I need to leave."** The home must produce a recommendation in one tap.
2. **"I don't like this — but I can't articulate why."** Reject with a reason. The agent re-runs and explains the swap.
3. **"Does this work today?"** Color score, weather note, and occasion match — visible at a glance.

The product solves these moments. Everything else is decoration.

## Out of scope

Wearly does *not* try to solve:

- the user's *body image* — the language stays body-positive and never recommends "hiding" or "fixing" a feature;
- the user's *self-expression journey* — it surfaces preferences they've already declared, not a personality test;
- the user's *budget optimization* — shopping suggestions exist only when there's a genuine gap.

The problem space is bounded on purpose. Within those bounds, the product is meant to feel inevitable.
