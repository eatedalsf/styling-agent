# 09 · Before / after demo

The single most important visual moment in the 10-minute presentation.

## The framing

**Before** is the world where the user manually plans every outfit — 15 minutes per morning, no weather check, color coordination by gut feel, no reasoning visible.

**After** is the same morning with Wearly — three seconds, full context awareness, a 0–100 color score, every choice explained.

In the Streamlit app, the **Before / After** section nav pill renders the comparison side-by-side and includes a **See it live →** button that runs the agent in real time.

## The comparison table

Eight rows. Designed to be readable in one glance:

| Dimension | Before — Manual Planning | After — Wearly |
|---|---|---|
| Time to decide | ~15 minutes | ~3 seconds |
| Weather check | Often forgotten | Automatic (live API) |
| Color coordination | Guesswork | 0–100 score |
| Calendar awareness | Manual lookup | Automatic |
| Season awareness | Mental model | Data-driven |
| Reasoning | Invisible | Fully explained |
| Confidence | Low–medium | High (structured) |
| Coat reminder | Missed it | Included |

The "Coat reminder · Missed it / Included" row is small but it lands the point: a chatbot wouldn't have noticed the weather. The agent does.

## Visual choices

The two columns share the warm palette — **no green for "after"**, just a deeper terracotta border to indicate emphasis. The previous design used green, which broke palette unity; the current design keeps the comparison inside the same emotional register and lets the **content** carry the contrast.

## The live moment

Inside the same screen, **See it live →** runs the agent and renders a full outfit result *immediately below* the comparison. This is critical:

1. The audience sees the abstract claim (the table).
2. The audience sees the concrete result (the agent's actual output, with a reasoning trail).
3. The two are next to each other on one screen, with no navigation.

Nothing on this screen requires the user to imagine. Everything they see is real.

## The 10-minute demo arc

Per `docs/demo_script.md`:

1. **Hook / problem** (45s) — the 15-minute closet.
2. **What Wearly is** (45s) — an agent, not a chatbot.
3. **Before / After** (90s) — *this chapter's screen*.
4. **Calendar + weather reasoning** (90s).
5. **Wardrobe + color reasoning** (90s).
6. **Error handling / wardrobe gaps** (60s).
7. **Future roadmap** (90s).
8. **Closing** (30s).

The Before / After screen earns 90 seconds in a 600-second talk — about 15% of the budget. It's worth that share.

## Where to verify

- The screen: `app.py` → `_render_demo()`.
- The narrative: `docs/demo_script.md`.
- The data behind the "live" moment: any of the smoke tests in `tests/test_agent_smoke.py`.
