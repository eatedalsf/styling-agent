# Fit & silhouette rules

Body-positive fit logic. Today, partial wiring (skin tone in Step 7); Phase 3 completes the wiring.

## R1 — Body-positive language is a contract

**Use** these verbs in reasoning lines:
- highlight (preferred features)
- balance (proportions)
- support (preferred silhouette)
- improve (comfort)
- increase (confidence)

**Never use** these verbs:
- hide
- flatter the flaw of
- fix
- minimize
- correct
- (anything labeling a body feature as a problem)

A future test will scan the reasoning trail for forbidden tokens and fail the build if any appear.

## R2 — Optional fields, work-with-what's-given

The fit profile (Phase 3 `fit_profile.json`) has every measurement field optional. The agent works with whatever the user shares:

| Field | If provided, drives |
|---|---|
| `height` | Hemline rules, full-length-pant proportions |
| `shoulder_width` | Sleeve and shoulder structure choices |
| `bust`, `waist`, `hips`, `inseam` | Drape and proportion logic |
| `preferred_fit` | Tailored / relaxed / structured preference |
| `modesty_preference` | Coverage on top, hemline rules |
| `comfort_needs` | Fabric softness, no-stiff-collar flags |
| `style_goals` | Aesthetic prioritization (elevated, modernized, timeless) |
| `highlight_features` | Areas to draw attention to |
| `balance_areas` | Areas to bring into proportion |

When a field is missing, that constraint is not applied. No default values are inferred about the user's body.

## R3 — Modesty preference

If `modesty_preference = "moderate"` or `"high"`:
- Filter out tops with deep necklines, sleeveless tops *(unless explicitly tagged as user-accepted)*, very short hemlines.
- Surface in the reasoning trail: *"Selected '{name}' — its coverage supports your stated modesty preference."*

## R4 — Comfort preference

If `comfort_needs` includes `"no stiff collars"` or similar:
- Filter or deprioritize items tagged with the relevant fabric/construction property.
- Don't substitute comfort silently — the reasoning trail explains the trade-off.

## R5 — Preferred fit

A user's `preferred_fit` (tailored / relaxed / structured) is a strong tiebreaker between candidate items of equivalent occasion and color score.

## R6 — Style preferences as personality, not as filter

`style_preferences` like `classic`, `elegant`, `minimal` are NOT used to filter — they're used to **prefer** items tagged with those qualities when ranking candidates. A user who declares "minimal" gets a less-busy outfit; they don't get items removed from their own wardrobe.

## R7 — Color is the most-wired piece today

Skin tone is the only fit-profile field already wired into the agent. Step 7 uses it for the 0–100 color harmony score with per-item flags. The remaining fit rules are documented here and live in the codebase as Phase 3 work.

## R8 — Measurement-derived suggestions are preference-based, never prescriptive

When the user provides bust / waist / hip measurements, Wearly *may* surface a small set of preference-based styling suggestions derived from the predicted body-shape category. These suggestions are an opt-in helper for the Profile screen — they are never auto-applied, never appear in agent reasoning without the user confirming them, and never frame a body feature as something to fix.

**Mapping (industry heuristic, body-positive framing):**

| Predicted shape | Areas the user *may* choose to highlight | Areas the user *may* choose to balance | Fit preferences commonly associated |
|---|---|---|---|
| `hourglass` | waist, neckline | (proportions are already balanced — no suggestion) | tailored, fitted, structured |
| `pear` | neckline, shoulders, upper body | hips (via upper-body interest, not concealment) | structured upper, fluid lower |
| `apple` (round midsection) | neckline, legs, collarbone | midsection (via vertical lines and length) | relaxed, fluid |
| `rectangle` (column) | collarbone, waist, neckline | waist (via waist-defining cuts) | structured, tailored |
| `inverted triangle` | waist, hips, legs | shoulders (via lower-body interest, not concealment) | fluid upper, structured lower |
| `athletic` (default fallback) | (no specific suggestion — user choice) | (no specific suggestion — user choice) | (no suggestion) |

**Preferred-fit from waist definition (weak heuristic):**
- `waist_definition ≥ 8 in` → `tailored` or `structured` may suit (waist seaming reads as intentional)
- `waist_definition < 4 in` → `relaxed` or `fluid` may suit (drape reads more naturally)
- otherwise → no preferred-fit suggestion

**Style goals & comfort needs are NEVER inferred from measurements.** They are personal expression and must come from the user directly.

**UX contract (enforced in `profile_inference.suggest_profile_from_measurements`):**
1. The user must explicitly click "Analyze measurements" — suggestions are never computed silently.
2. Each suggestion shows the rule citation `[fit-silhouette-rules#R8]` so the user can read this section.
3. Suggestions never overwrite user-confirmed profile fields. If `body_shape` is already set with `_body_shape_source: "user"`, the suggestion is shown as a comparison but the user-confirmed value is preserved unless the user clicks "Apply suggestions".
4. Every suggestion uses body-positive verbs only (highlight, balance, support). Forbidden tokens (`hide`, `fix`, `minimize`, `correct`, `flaw`, `slimming`) are blocked by `fit_tool.check_value_for_forbidden_language` at write time.
5. The suggestion panel surfaces a confidence label (high / medium / low / weak heuristic) for each field so the user can weigh it.

**Why this is a rule, not invented styling advice:**
The shape → balance / highlight mappings are widely-documented industry heuristics found in the styling literature surveyed in `docs/evidence-and-references.md` §3.4. Wearly's contribution is the **framing** (user-declared proportion preferences, never image-inferred, always editable, body-positive language) — not the proportion suggestions themselves. The Hokka (2024) reference makes explicit that a small set of shape categories is a documented limitation of inclusive design, so Wearly surfaces these mappings as preference-based options rather than prescriptive advice.

---

## Source basis

**Primary category:** Body-shape-aware / fit-aware styling (`docs/evidence-and-references.md` §3.4).
**Secondary:** Human-centered AI (§3.6).
**Current basis:** Industry fit heuristics + the body-positive language contract, enforced at runtime by `fit_tool.check_reasoning_for_forbidden_language()`.
**Important framing:** The body-shape category labels (`hourglass / pear / apple / etc.`) are **industry heuristics, not scientific taxonomy.** Wearly treats them as user-declared proportion preferences — a proxy for a small set of proportion-related styling rules, never as a claim about the user's body. See `docs/evidence-and-references.md` §4 and `book/06-fit-profile-logic.md`.
**Verified citation:** Hokka, J. (2024). "Gender and the Diversity of the Human Body as Challenges for the Inclusive Design of Wearable Technology." *Fashion Practice* 16(1). DOI: 10.1080/17569370.2023.2250153. Cited for the inclusive-design framing — body diversity is a documented challenge for prescriptive design, supporting Wearly's treatment of body-shape labels as user-declared rather than computed.
