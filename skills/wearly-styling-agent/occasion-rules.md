# Occasion rules

Mapping free-text occasions to canonical tags; required piece-types per occasion. Implemented in `styling_agent.py`.

## R1 — Tag mapping

| Free text | Canonical tag |
|---|---|
| `work`, `business`, `meeting` | `work` |
| `gym`, `workout`, `yoga`, `running` | `gym` |
| `dinner`, `restaurant`, `date` | `dinner` |
| `formal_event`, `gala`, `formal` | `formal` |
| `casual`, `weekend`, `brunch`, `everyday` | `casual` |

Unknown free-text → `casual` (safe default).

## R2 — Required piece-types

| Occasion | Required pieces |
|---|---|
| `work` | `top` + `bottom` |
| `dinner` | `top` + `bottom` *(unless a dress is preferred)* |
| `gym` | two `activewear` pieces |
| `formal` | `dress` |
| `casual` | `top` + `bottom` |

Step 6 checks the built outfit against this list. Missing required pieces become gaps.

## R3 — Dress-vs-separates branching

If `occasion ∈ {formal, dinner}` AND `formality ≥ smart_casual`:
- Prefer a dress from the wardrobe pool.
- For `formality = formal`, sort dresses to prefer `formality = formal` first.

Otherwise, build top + bottom (or two activewear pieces for gym).

## R4 — Accessory cap

Add up to **two** accessories from the pool. Never more — over-accessorizing is the most common visual misstep in algorithmically-built outfits.
