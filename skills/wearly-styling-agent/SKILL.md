# Wearly Styling Agent — Skill Package

> A reusable, structured rule package for a personal styling agent.
> Inspired by [Agent Skills](https://agentskills.io/home) and [Meta-Skills](https://dmccreary.github.io/prompt-class/lectures/meta-skills/).

This package documents the **decision logic** behind Wearly's recommendations, organized so it can be loaded into a new agent shell without re-deriving the rules.

---

## What this skill does

Given:

- a `User` with a fit profile (skin tone required; body shape, modesty, comfort optional),
- the user's `wardrobe` (items with type, color, formality, season, tags),
- the day's `occasion` (calendar event or free-text request),
- the day's `weather` (temperature, condition, precipitation, wind),
- optionally, prior `rejection feedback`,

the skill produces:

- an `OutfitRecommendation` (3–6 items from the wardrobe),
- a `reasoning trail` (one line per decision, end-to-end),
- a `color_score` (0–100 against skin tone),
- a `gap list` and `shopping_suggestions` when pieces are missing.

---

## Rule packs included

| File | Covers |
|---|---|
| [occasion-rules.md](occasion-rules.md) | Mapping free-text occasions to canonical tags; required piece-types per occasion |
| [weather-rules.md](weather-rules.md) | Temperature → layer advice; outerwear injection thresholds |
| [fit-silhouette-rules.md](fit-silhouette-rules.md) | Body-positive fit logic; preferred fit / silhouette / modesty constraints |
| [wardrobe-filtering-rules.md](wardrobe-filtering-rules.md) | Occasion tag matching, season filtering, pool relaxation |
| [color-coordination-rules.md](color-coordination-rules.md) | Skin-tone palettes, scoring formula, per-item flag thresholds |
| [wear-history-rules.md](wear-history-rules.md) | Freshness scoring, rotation logic |
| [shopping-gap-rules.md](shopping-gap-rules.md) | Gap detection, occasion-specific suggestion templates |
| [privacy-guidelines.md](privacy-guidelines.md) | Data handling commitments |

---

## How to use this skill

### As a developer

Each rule file documents a small, inspectable rule system that lives in the codebase:

- Occasion rules → `styling_agent.py` `OCCASION_TAG_MAP`, `REQUIRED_PIECES`.
- Weather rules → `weather_tool.py` `_get_layering_advice()`, `styling_agent.py` outerwear injection.
- Fit / silhouette → `wardrobe.json` owner block, Phase 3 fit_tool.
- Wardrobe filter → `wardrobe_tool.filter_items_by_occasion()`.
- Color rules → `color_rules.json`, `color_tool.score_outfit_colors()`.
- Wear history → Phase 4 `history_tool`.
- Shopping gaps → `styling_agent.py` `SHOPPING_SUGGESTIONS`.

When the rules change, both the code and the matching rule file change together. The rule files are the canonical specification; the code is the implementation.

### As a model

A future agent loading this skill into context can reproduce Wearly's reasoning by:

1. Following each rule pack in the order of the seven-step workflow.
2. Citing the relevant rule by ID in its reasoning trail (`color-coordination-rules.md#R3`).
3. Falling back to the **privacy guidelines** when any user-data question arises.

---

## Reasoning discipline

All Wearly skill output obeys three rules:

1. **Cite the rule.** No magic recommendations. Every decision points back to an inspectable rule.
2. **Surface the why.** A user reading the reasoning trail must be able to find each rule that drove each line.
3. **Respect the user.** Body-positive language. No corrective vocabulary. Honest gaps over forced pieces.

---

## Scope boundary

This skill does **not** cover:

- product photography or visual analysis (Phase 4 photo pipeline).
- product catalog scraping (Phase 5).
- collaborative filtering across users (out of scope).
- LLM-based outfit generation (deliberately not in v1 — see `book/04-styling-knowledge-base.md`).

If an agent tries to use this skill for any of the above, it should refuse and route the user back to a feature flag or roadmap entry.
