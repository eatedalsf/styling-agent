---
name: wearly-styling-agent
description: |
  Recommend a complete outfit (top, bottom or dress, shoes, accessories, optional outerwear) for a person on a specific day, given their wardrobe, fit profile, calendar event, current weather, and any past wear history or rejection feedback. Use this skill when the request is to plan what to wear for an occasion — formal, work, dinner, gym, casual — and the user expects a personalized, explainable recommendation rather than a generic suggestion. Produces a numbered reasoning trail, a 0–100 color-harmony score with per-item flags, and a list of wardrobe gaps with descriptive (non-promotional) shopping suggestions. Do NOT trigger this skill for generic fashion-trend questions, body-image judgment, or weight-loss styling requests. Language is body-positive by contract: never frame body features as flaws.
version: "0.4.0"
license: "MIT"
author: "Wearly project (eatedalsf)"
homepage: "https://eatedalsf.github.io/styling-agent/skills/wearly-styling-agent/SKILL/"
repository: "https://github.com/eatedalsf/styling-agent"
tags:
  - styling
  - personal-styling
  - wardrobe
  - recommender
  - agentic-ai
  - body-positive
  - explainable-ai
---

# Wearly Styling Agent — Skill Package

> A reusable, structured rule package for a personal styling agent.
> Conforms to the [Agent Skills](https://agentskills.io/home) standard and is informed by the [Meta-Skills](https://dmccreary.github.io/prompt-class/lectures/meta-skills/) lecture's progression: Basic → Intermediate → Advanced. This package currently sits at the **Advanced** tier — decision trees, validation rules, reference files, AND executable scripts.

---

## When to use this skill

**Trigger this skill when:**

- A user asks "what should I wear" for a specific occasion (work, dinner, gym, formal event, casual day, travel).
- The request is for an outfit recommendation grounded in the user's actual closet, calendar, weather, and personal preferences — not a generic fashion opinion.
- The user wants to **understand** the recommendation — every line of the reasoning trail should be auditable.
- The user wants to push back on a recommendation (reject one or more items with a reason) and get a regenerated outfit that surfaces what changed and why.

**Do NOT trigger this skill when:**

- The request is for generic fashion trends, runway commentary, or aesthetic education.
- The user asks for body-image judgment (e.g., language framed as needing correction). The skill refuses and surfaces a clear message — see [`privacy-guidelines.md`](privacy-guidelines.md) R8.
- The user is asking for shopping recommendations independent of an occasion or a detected wardrobe gap (use a shopping skill instead).
- The user wants the agent to scrape live retailer pages or perform image classification — see Scope Boundary below.

---

## Inputs

Required:

- `User` with at least a `name` and `skin_tone`.
- `wardrobe` — collection of items, each with `id`, `type`, `name`, `color`, `formality`, `season[]`, `tags[]`.
- One of:
  - `calendar_event` (with `title`, `date`, `time`, `type`, `formality`, optional `notes`), OR
  - `everyday_request` — free-text occasion description.

Optional:

- `weather` — auto-fetched from Open-Meteo if absent.
- `fit_profile` — `body_shape`, `preferred_fit`, `modesty_preference`, `comfort_needs`, `style_goals`, `highlight_features`, `balance_areas`.
- `wear_history` — `{item_id: {worn_count, last_worn_date, last_event}}`.
- `rejected_ids` and `rejection_reasons` — when the user has pushed back on a prior recommendation.
- `favorite_stores` — names of retailers the user prefers; used to make gap suggestions store-aware.

---

## Outputs

A result dict carrying:

- `recommendation` — ordered list of wardrobe items chosen for the occasion.
- `reasoning` — numbered list of explanation strings, one per decision (Step 5 pick, freshness note, fit-alignment note, color harmony note, gap suggestion).
- `gaps` — missing piece types (e.g. `["outerwear"]`).
- `shopping_suggestions` — descriptive, never promotional. Augmented with favorite-store hints when available.
- `color_score` — `{score: 0–100, notes[], flags[]}`.
- `weather`, `event`, `profile`, `rejected_context` — context echoed so callers can audit.
- `steps` — workflow audit log (7 steps).
- `error` — null on success.

---

## Procedure (the seven-step workflow)

Each step is a decision point with its own rule pack. Full per-rule detail in the linked reference files.

1. **Determine occasion** — map a calendar event or free-text request to one of the five canonical tags (`work`, `gym`, `dinner`, `formal`, `casual`) using [`occasion-rules.md`](occasion-rules.md).
2. **Load style profile** — read the user's `User` block + `fit_profile` overlay. Body-positive language only — see [`fit-silhouette-rules.md`](fit-silhouette-rules.md) R1.
3. **Check weather** — fetch live weather, fall back to a seasonal estimate on any failure. Map temperature → season + layer advice via [`weather-rules.md`](weather-rules.md).
4. **Filter wardrobe** — match each candidate against the occasion tag and the derived season; exclude any items in `rejected_ids`. See [`wardrobe-filtering-rules.md`](wardrobe-filtering-rules.md).
5. **Build outfit** — apply the dress-vs-separates branching, activewear branching for gym, freshness tie-breaker, fit-alignment notes, and conditional outerwear injection. See [`occasion-rules.md`](occasion-rules.md) R3, [`weather-rules.md`](weather-rules.md) R4, [`wear-history-rules.md`](wear-history-rules.md), and [`fit-silhouette-rules.md`](fit-silhouette-rules.md).
6. **Check wardrobe gaps** — compare the built outfit against the occasion's required-piece set. Generate descriptive shopping suggestions augmented with the user's favorite stores. See [`shopping-gap-rules.md`](shopping-gap-rules.md).
7. **Score color coordination** — score every outfit item against the user's skin-tone palette. Return a 0–100 score with per-item flags. See [`color-coordination-rules.md`](color-coordination-rules.md).

The reject-and-regenerate loop is the skill's "agent, not chatbot" signal: when the user supplies `rejected_ids` + `rejection_reasons`, Step 4 excludes them, Step 5 prepends a reasoning line per rejection ("Skipping 'X' — you flagged it as: Y"), and the new outfit is auditable line-by-line.

---

## Rule packs (references)

Detailed knowledge is delegated to per-rule reference files so the SKILL.md stays scannable.

| Rule pack | Topic |
|---|---|
| [`occasion-rules.md`](occasion-rules.md) | Free-text occasion → canonical tag; required pieces; dress branching; accessory cap |
| [`weather-rules.md`](weather-rules.md) | Temperature/precip/wind → layer advice; outerwear injection; fallback path |
| [`fit-silhouette-rules.md`](fit-silhouette-rules.md) | Body-positive language CONTRACT; modesty / comfort / fit preferences |
| [`wardrobe-filtering-rules.md`](wardrobe-filtering-rules.md) | Tag match, season filter, pool relaxation, rejection exclusion |
| [`color-coordination-rules.md`](color-coordination-rules.md) | Skin-tone palettes; +8/+4/−10 scoring formula; per-item flags |
| [`wear-history-rules.md`](wear-history-rules.md) | Freshness score (0.4 floor); tie-breaker semantics |
| [`shopping-gap-rules.md`](shopping-gap-rules.md) | Required-piece gap detection; outerwear gap path; descriptive (non-promotional) suggestions |
| [`privacy-guidelines.md`](privacy-guidelines.md) | Data handling, refusal triggers, body-positive language enforcement |

Each rule pack ends with a *Source basis* footer linking back to [`docs/evidence-and-references.md`](https://eatedalsf.github.io/styling-agent/docs/evidence-and-references/) for the canonical sourcing.

---

## Scripts (validation + introspection)

| Script | Purpose |
|---|---|
| [`scripts/validate_outfit.py`](https://github.com/eatedalsf/styling-agent/blob/main/skills/wearly-styling-agent/scripts/validate_outfit.py) | Stand-alone validator: given a result dict, verify each rule pack's contract is upheld (occasion tag valid, required pieces present, color score in range, reasoning trail body-positive). Returns a structured PASS / FAIL report. Run as `python skills/wearly-styling-agent/scripts/validate_outfit.py path/to/result.json`. |

The script makes this an **Advanced**-tier skill per the meta-skills lecture: reference files PLUS executable code.

---

## Reasoning discipline

All Wearly skill output obeys four contract rules:

1. **Cite the rule.** No magic recommendations. Every decision points back to an inspectable rule.
2. **Surface the why.** A user reading the reasoning trail must find each rule that drove each line.
3. **Respect the user.** Body-positive language. No corrective vocabulary. Honest gaps over forced pieces.
4. **Styling is not an exact science.** The skill says *"tends to work well,"* never *"is correct."*

The body-positive contract is enforced *twice*:

- At runtime, `fit_tool.check_reasoning_for_forbidden_language()` scans the reasoning trail for tokens in `FORBIDDEN_TOKENS` (`flaw / fix / hide / minimize / correct / problem area / slimming / shameful`).
- At documentation-build time, `tests/test_documentation_integrity.py` asserts the trail produced by representative scenarios is clean.

---

## Scope boundary — what this skill does NOT do

| Out-of-scope task | Why it's excluded |
|---|---|
| Image-based body classification | Body-shape labels are *user-declared proportion preferences*, not classifications Wearly computes. See [`fit-silhouette-rules.md`](fit-silhouette-rules.md) R7 + [`docs/evidence-and-references.md` §4](https://eatedalsf.github.io/styling-agent/docs/evidence-and-references/#4-body-shape-framing-—-a-deliberate-note). |
| Image-based garment classification | Heavy ML dependency; prototype uses Pillow color extraction only — see [`book/05-wardrobe-intelligence.md`](https://eatedalsf.github.io/styling-agent/book/05-wardrobe-intelligence/). |
| Live retailer product catalog lookup | No paid APIs in the prototype. Favorite stores are personalization hints, not commerce. |
| Collaborative filtering across users | Single-user prototype by design. Privacy-respecting. |
| Body-image / weight-loss styling | Refusal — see [`privacy-guidelines.md`](privacy-guidelines.md) R8. |
| Replacing a human stylist's judgment | Wearly augments; the user remains the final reviewer. |

If a caller tries to use this skill for any of the above, the skill should **refuse with a clear message** and route the user back to a roadmap entry (see `book/11-product-roadmap.md`).

---

## Loading this skill (progressive disclosure)

Per the Agent Skills standard:

1. **Discovery** — an agent inspecting available skills reads only this skill's `name` and `description` (the YAML frontmatter at the top of this file). That's enough to know when the skill applies.
2. **Activation** — when a task matches the description, the agent reads the full `SKILL.md` (this file).
3. **Execution** — the agent follows the seven-step procedure, loading individual rule packs (`*.md`) and `scripts/validate_outfit.py` on demand.

Reference files load only when their rule applies, so the skill stays cheap to keep loaded across many agent runs.

---

## Versioning

This skill follows [Semantic Versioning](https://semver.org/). Breaking changes to the result-dict contract, the rule pack vocabularies, or the procedure order bump the major version. Adding a new optional field or a new rule bumps the minor version. Wording clarifications bump the patch version.

Current: **0.4.0** — Added the Wear History tie-breaker, the Fit Profile alignment notes, the body-positive language contract enforcement, and the Wishlist + Favorite Stores integration.

---

## See also

- **Live app:** <https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/>
- **Intelligent Book:** <https://eatedalsf.github.io/styling-agent/>
- **Evidence + references:** <https://eatedalsf.github.io/styling-agent/docs/evidence-and-references/>
- **Knowledge graph schema:** <https://eatedalsf.github.io/styling-agent/graph/schema/>
- **Agent Skills standard:** <https://agentskills.io/home>
- **Meta-Skills lecture:** <https://dmccreary.github.io/prompt-class/lectures/meta-skills/>
