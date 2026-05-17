# 03 · Agent workflow

*The app runs this loop every time you tap "Plan today's outfit"; this chapter explains why the seven steps are shaped the way they are.*

> Each step consumes a piece of styling knowledge taught in Part II:
> Step 1 reads occasion ([§S3](S3-occasion-and-context.md)),
> Step 3 reads weather ([§S4](S4-weather-and-layering.md)),
> Step 5 builds the outfit ([§S5](S5-wardrobe-construction.md))
> using rotation ([§S6](S6-rotation-and-freshness.md)),
> Step 6 detects gaps ([§S7](S7-honest-gaps.md)),
> and Step 7 scores color ([§S1](S1-color-and-skin-tone.md)).

This is the most important chapter. It documents the seven-step reasoning loop that runs every time the user taps **"Plan today's outfit →"**.

The implementation lives in `styling_agent.py` · `run_agent()`. The per-step decision flow is in `workflow_diagram.md`. This chapter explains *why* the workflow is shaped the way it is.

---

## The seven steps

```
1. Determine Occasion        ← read calendar (or accept free-text request)
2. Load Style Profile        ← read owner: skin tone, body shape, style prefs
3. Check Weather             ← live Open-Meteo with seasonal fallback
4. Filter Wardrobe           ← occasion + season + (rejected items excluded)
5. Build Outfit              ← dress vs separates; activewear; outerwear if cold
6. Check for Wardrobe Gaps   ← detect missing required pieces
7. Color Coordination Check  ← 0–100 score against skin tone
```

Every step appends a record to `result["steps"]` with status `ok`, `fallback`, `gap_found`, or `error`. The UI renders that audit log in the **"Agent Workflow — 7 Steps"** expander, so the user can see the agent's run even after the outfit is rendered.

---

## Why seven, and why this order

### 1. Determine occasion *before anything else*

The occasion is the strongest signal — formal, work, gym, casual, dinner. Every later step depends on it. Reversing the order (filter wardrobe first, then pick occasion) would over-filter and lose context.

### 2. Load the style profile *before fetching weather*

Profile is local and instant; weather is a network call. If profile loading fails, we want to know before paying the latency of a network round-trip.

### 3. Weather third

Weather is a network call. The agent is forgiving: any exception in `weather_tool.get_weather()` returns a seasonal estimate, marked as a fallback, so the demo never breaks because of a flaky connection.

### 4. Filter wardrobe fourth

Filter happens after we know the occasion *and* the season (derived from temperature). This is where the **reject context** is applied: if the user has rejected items, they're excluded from the candidate pool here.

### 5. Build outfit fifth — with branching logic

This is the most rule-heavy step:

- **Formal or dinner with at least `smart_casual` formality** → prefer a dress.
- **Gym** → activewear pieces (up to two).
- **Everything else** → top + bottom.
- **Add shoes**, then up to two accessories.
- **Below 60°F** → add outerwear, but only an occasion-appropriate one. Don't slap a work coat onto a gym fit.

If no occasion-appropriate outerwear exists in the wardrobe, the agent **skips the layer and adds a wardrobe gap** rather than forcing a wrong-style piece. That's a deliberate "respect the user's taste" call.

### 6. Gap check sixth

Some occasions have required piece-type sets — e.g., "work" needs `top + bottom`, "formal" needs a `dress`. Step 6 runs `check_gaps(outfit, required)` and surfaces shopping suggestions for whatever's missing.

### 7. Color check last

Once the outfit is built, score it against the owner's skin tone. The score is 0–100, starts at 60, +8 for "best" colors, +4 for "good," −10 for "avoid." Per-item flags surface in the UI. Notes from the skin-tone profile are appended to the reasoning trail.

---

## The reasoning trail

Every step contributes to a single `result["reasoning"]` list of plain-English sentences. The UI renders this as a numbered list. This is the **explainability core** of the product — without it, the agent looks like a black box; with it, every decision is auditable.

Sample reasoning trail (work occasion, fall, 58°F):

```
1. Selected top: 'White Button-Down Blouse' for its business formality.
2. Selected bottom: 'Black Tailored Trousers' to pair with the top.
3. Added shoes: 'Black Pointed-Toe Heels' appropriate for the occasion.
4. Added accessory: 'Gold Hoop Earrings'.
5. Added accessory: 'Pearl Stud Earrings'.
6. Added 'Camel Wool Coat' as outerwear — temperature is 58°F and a light coat is recommended.
7. ✓ White Button-Down Blouse (white) — excellent color for your skin tone.
   (… one line per item …)
13. Warm earth tones are most flattering. Gold jewelry enhances warm undertones.
```

The reasoning trail is **append-only within a single run**, and it accumulates rejection notes when the user has used reject & regenerate.

---

## Reject & regenerate

When the user pushes back on an item (Today → "Not quite right?" → multiselect + reason → Regenerate):

1. `run_agent()` is called with `rejected_ids` and `rejection_reasons`.
2. Step 4 excludes any rejected item from the wardrobe pool. Step 4's `output` notes the exclusion count.
3. Step 5 *prepends* a `"Skipping '{name}' — you flagged it as: {reason}"` line to the reasoning trail for each rejection.
4. The result dict carries `rejected_context: {ids, reasons}` so the UI can render the **"What changed in this run"** banner.

This is the single feature that most demonstrates Wearly's **agentic** behavior. The user *argues with the system*, the system *responds*, and both sides of that conversation are visible in the reasoning trail.

---

## Failure modes

| Step | Failure | Behavior |
|---|---|---|
| 1 | No upcoming events | Falls back to casual everyday |
| 2 | Wardrobe / profile file missing | Hard stop with clear error |
| 3 | Network unavailable | Seasonal estimate; agent continues |
| 4 | Wardrobe file missing | Hard stop with clear error |
| 5 | No occasion-appropriate outerwear at low temp | Skip outerwear, add a wardrobe gap |
| 5 | Rejected items deplete the pool | Best-available outfit; gap-check picks up missing requirements |
| 7 | Unknown skin tone | Universal safe palette |

Every failure mode is tested in `tests/test_agent_smoke.py` or `tests/test_tools.py`.

---

## Where to verify

- The code: `styling_agent.py`.
- The decision flow: `workflow_diagram.md`.
- The system snapshot: `docs/architecture.md`.
- Run it yourself: `streamlit run app.py` → tap **Plan today's outfit**.

---

## Key terms

- **Seven-step workflow** — determine occasion → load profile → check weather → filter wardrobe → build outfit → check gaps → score color ([glossary](../docs/glossary.md)).
- **Reject & regenerate** — the agentic loop where a rejection becomes a constraint for the next run ([glossary](../docs/glossary.md)).
- **Citation chip** — the `[pack#R<N>]` tag appended to a reasoning line, resolvable via `rule_refs.py` ([glossary](../docs/glossary.md)).
- **Result-dict contract** — the single boundary between the agent and the UI ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* List the seven steps in order.
2. *(Understand)* Why does Step 2 (load profile) come *before* Step 4 (filter wardrobe), rather than after?
3. *(Apply)* A user rejects the recommendation citing fit. Trace which steps re-run and which inputs change.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze).*
