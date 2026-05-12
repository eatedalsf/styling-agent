# 06 · Fit-profile logic

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

## Where to verify

- Today's fit data: `wardrobe.json` → `owner` block.
- The Profile screen: `app.py` → `_render_profile()`.
- Phase 3 data plan: `Wearly_Product_Brief.md` §7.5.
