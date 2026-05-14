# 06 · Fit-profile logic

*The app reads the fit profile every run; this chapter explains how body-positive personalization is encoded and enforced.*

> The *styling knowledge* behind this chapter lives in Part II:
> [§S2 · Silhouette and fit](S2-silhouette-and-fit.md) explains why
> proportion-related styling enters the agent as user-declared
> preference, never as classification;
> [§S8 · Body-positive framing as a discipline](S8-body-positive-framing.md)
> explains the language contract enforced in code.

This is the **body-positive** chapter. The language and the logic both matter — the way Wearly talks about the user's body is part of the product.

## What the fit profile is

Today, the owner block in `wardrobe.json` carries:

- `name`
- `body_shape`
- `skin_tone`
- `style_preferences` (list of strings: `classic`, `elegant`, `minimal` …)
- `preferred_fit` (`tailored`, `relaxed`, etc.)

Phase 3 splits this out into a dedicated `data/fit_profile.json` with optional fields:

| Field | Optional? | Purpose |
|---|---|---|
| `height` | Yes | Hemline rules, full-length-pant proportions |
| `shoulder_width` | Yes | Sleeve and shoulder structure choices |
| `bust`, `waist`, `hips`, `inseam` | Yes | Drape and proportion logic |
| `preferred_fit` | Yes | Tailored vs relaxed vs structured |
| `modesty_preference` | Yes | Coverage on top, hemline rules |
| `comfort_needs` | Yes | Fabric softness, no-stiff-collar flags |
| `style_goals` | Yes | "Elevate," "modernize," "stay timeless" |
| `highlight_features` | Yes | Areas the user wants to draw attention to |
| `balance_areas` | Yes | Areas the user wants to bring into proportion |

**Every field is optional. The agent works with whatever the user shares.**

## Body-positive language is a contract, not a wish

The product brief commits to this and the agent enforces it:

> The language must be body-positive. Never describe body features as flaws.

Concretely:

- **Use**: *highlight preferred features*, *balance proportions*, *support the user's preferred silhouette*, *improve comfort*, *increase confidence*.
- **Never use**: *hide*, *flatter the flaw of*, *fix*, *minimize*, *correct*, *problem area*.

The forbidden vocabulary is a guardrail. A future test will scan the reasoning trail for forbidden tokens and fail the build if any appear.

## Why this matters for the product

Most styling apps inherit the body language of mid-2000s fashion magazines. Wearly explicitly rejects that voice. The decision is:

1. **Ethical.** Bodies aren't problems to be solved.
2. **Commercial.** A premium brand that respects the user *as they are* earns trust that a corrective brand can't.
3. **Technical.** Phrases like *"hides the waist"* don't translate to rules. *"Supports your preferred silhouette"* does — it maps to a known set of proportion-preserving choices.

## What's wired today vs what's coming

Today (Phase 2):

- Skin tone is wired into Step 7 (color scoring) and surfaces in the Profile screen.
- Body shape, style preferences, preferred fit are visible in the Profile screen but **not yet wired into the outfit builder**.

Phase 3 wiring plan:

- `fit_tool.py` exposes `get_fit_profile()` and `apply_fit_constraints(outfit, profile)`.
- Step 5 (build outfit) consults the fit profile when ordering candidate items: a tailored preference prefers structured pieces over drapey ones; a modesty preference filters out high necklines or short hemlines.
- Reasoning lines surface fit decisions: *"Selected the silk blouse — its drape supports your preferred silhouette."*

## On body-shape categories — a deliberate framing

The `owner.body_shape` field in `wardrobe.json` accepts labels like `"hourglass"`, `"pear"`, `"apple"`, `"rectangle"`, `"inverted triangle"`. These are **industry heuristics, not scientific taxonomy.** They have no agreed academic standing.

Wearly handles this carefully:

- The agent **never analyzes images** to infer a body shape. There is no image classifier, no body-detection model, no measurement extraction.
- A body-shape label is treated as a **user-declared proportion preference** — a proxy for a small set of proportion-related styling rules, not a claim about the user's body.
- The user can leave `body_shape` blank, and no proportion-rule fires. Wearly works fine without it.
- User-facing copy is calibrated: *"if you've shared a body shape preference,"* not *"based on your body type."*

The body-positive language contract enforces this through `fit_tool.FORBIDDEN_TOKENS` at runtime and through `tests/test_documentation_language.py` across documentation.

For the full evidence framing — what category supports the fit logic and what's still pending verification — see [`docs/evidence-and-references.md`](../docs/evidence-and-references.md) §3.4 and §4.

## Where to verify

- Today's fit data: `wardrobe.json` → `owner` block.
- The Profile screen: `app.py` → `_render_profile()`.
- The body-positive contract: `fit_tool.FORBIDDEN_TOKENS` + `tests/test_documentation_language.py`.
- Phase 3 data plan: `Wearly_Product_Brief.md` §7.5.
- Canonical sourcing: `docs/evidence-and-references.md`.

---

## Key terms

- **Fit profile** — optional, user-declared preferences — every field has a safe default ([glossary](../docs/glossary.md)).
- **Body shape (preference)** — a user-declared proportion preference; never inferred from images ([glossary](../docs/glossary.md)).
- **Profile hash** — detects mid-session profile edits to trigger the regenerate banner ([glossary](../docs/glossary.md)).
- **Body-positive language contract** — runtime forbidden tokens enforced in `fit_tool` ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* List three forbidden tokens from the body-positive language contract.
2. *(Understand)* Why is `body_shape` framed as a *preference* rather than a *classification*?
3. *(Apply)* A user leaves `body_shape` blank. Which proportion-related rules fire, and which don't?

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
