"""
rule_refs.py — the canonical registry of Skill rule citations.

This module is Wearly's single source of truth for *which rule drove
which line* in the agent's reasoning trail. Every rule citation the
agent emits comes from `cite(slug)`; every slug declared here points
to a real `## R<N>` heading in a file under `skills/wearly-styling-agent/`.

Why this exists:

- The Skill rule packs (`skills/wearly-styling-agent/*.md`) already
  carry numbered rules (R1, R2, ...) with prose. But until now, the
  agent's reasoning lines didn't *cite* those rule IDs — a user
  reading a recommendation couldn't trace a line back to its rule.
- `docs/evidence-and-references.md` documents the evidence categories
  each rule pack draws on. The chain "evidence category -> rule pack
  -> rule ID -> reasoning line" is now closed by this registry.
- A documentation-integrity test asserts that every slug here resolves
  to an actual rule heading in the corresponding skill file. If a
  Skill rule is renumbered or removed, the test fails immediately —
  citations cannot silently drift.

This module has NO runtime dependencies on agent code. The agent
imports `cite()`; the test module imports the `RULES` dict.
"""

from __future__ import annotations

from typing import Dict, NamedTuple


class _Rule(NamedTuple):
    """A canonical rule citation.

    Attributes:
        skill_file: filename under skills/wearly-styling-agent/.
        rule_id:    the R<N> identifier exactly as it appears in the
                    file's `## R<N> -- ...` heading.
        summary:    short, body-positive one-liner kept in sync with
                    the rule's intent. Used as hover-text in any UI
                    layer that surfaces citations.
    """

    skill_file: str
    rule_id: str
    summary: str


# Canonical rule registry. Keys are stable slugs of the form
# "<pack>#R<N>" where <pack> is the skill filename minus "-rules.md".
# Order matches the seven-step workflow.
RULES: Dict[str, _Rule] = {
    # Step 1 -- occasion mapping ------------------------------------
    "occasion#R1": _Rule(
        skill_file="occasion-rules.md",
        rule_id="R1",
        summary="Map free-text occasion to one of five canonical tags.",
    ),
    "occasion#R2": _Rule(
        skill_file="occasion-rules.md",
        rule_id="R2",
        summary="Required piece-types per occasion drive the gap check.",
    ),
    "occasion#R3": _Rule(
        skill_file="occasion-rules.md",
        rule_id="R3",
        summary="Dress-vs-separates branching for formal and dinner occasions.",
    ),
    "occasion#R4": _Rule(
        skill_file="occasion-rules.md",
        rule_id="R4",
        summary="Accessory cap of two.",
    ),

    # Step 3 / 5 -- weather + outerwear -----------------------------
    "weather#R1": _Rule(
        skill_file="weather-rules.md",
        rule_id="R1",
        summary="Temperature bands map to layer advice.",
    ),
    "weather#R4": _Rule(
        skill_file="weather-rules.md",
        rule_id="R4",
        summary="Outerwear is injected only when temp < 60 F and an "
                "occasion-matching outer piece exists.",
    ),
    "weather#R6": _Rule(
        skill_file="weather-rules.md",
        rule_id="R6",
        summary="On weather-fetch failure, fall back to a seasonal estimate.",
    ),

    # Step 4 -- wardrobe filtering ---------------------------------
    "wardrobe#R3": _Rule(
        skill_file="wardrobe-filtering-rules.md",
        rule_id="R3",
        summary="Combined occasion-tag + season filter.",
    ),
    "wardrobe#R5": _Rule(
        skill_file="wardrobe-filtering-rules.md",
        rule_id="R5",
        summary="Items in rejected_ids are excluded from candidate pools.",
    ),

    # Step 5 -- fit / silhouette -----------------------------------
    "fit#R1": _Rule(
        skill_file="fit-silhouette-rules.md",
        rule_id="R1",
        summary="Body-positive language is a contract; styling reasoning frames "
                "features as honored, not as targets for change.",
    ),
    "fit#R2": _Rule(
        skill_file="fit-silhouette-rules.md",
        rule_id="R2",
        summary="Fit-profile fields are optional; missing fields skip the note.",
    ),

    # Step 5 -- wear history ---------------------------------------
    "history#R2": _Rule(
        skill_file="wear-history-rules.md",
        rule_id="R2",
        summary="Freshness score is a tie-breaker with a 0.4 floor.",
    ),
    "history#R4": _Rule(
        skill_file="wear-history-rules.md",
        rule_id="R4",
        summary="Recently-worn pieces get a transparent reasoning note.",
    ),

    # Step 6 -- shopping gaps --------------------------------------
    "shopping#R1": _Rule(
        skill_file="shopping-gap-rules.md",
        rule_id="R1",
        summary="A required piece-type missing from the outfit is a gap.",
    ),
    "shopping#R2": _Rule(
        skill_file="shopping-gap-rules.md",
        rule_id="R2",
        summary="Cold weather without occasion-matching outerwear is a gap.",
    ),
    "shopping#R3": _Rule(
        skill_file="shopping-gap-rules.md",
        rule_id="R3",
        summary="Suggestions are descriptive (never promotional).",
    ),
    "shopping#R5": _Rule(
        skill_file="shopping-gap-rules.md",
        rule_id="R5",
        summary="Tone: 'would round out your wardrobe', not 'you need'.",
    ),

    # Step 7 -- color coordination ---------------------------------
    "color#R1": _Rule(
        skill_file="color-coordination-rules.md",
        rule_id="R1",
        summary="Three skin-tone palettes inform the score.",
    ),
    "color#R2": _Rule(
        skill_file="color-coordination-rules.md",
        rule_id="R2",
        summary="Base 60, +8 best / +4 good / -10 avoid, clamped to 0-100.",
    ),
    "color#R5": _Rule(
        skill_file="color-coordination-rules.md",
        rule_id="R5",
        summary="Unknown skin tone returns a neutral score with a clear note.",
    ),
}


def cite(slug: str) -> str:
    """Return a compact citation tag for appending to a reasoning line.

    Example::

        reasoning.append(
            f"Selected '{dress['name']}' for this formal occasion. "
            + cite('occasion#R3')
        )

    Produces a trailing token like ``[occasion-rules#R3]`` that the UI
    can detect and turn into a deep link to the rule.

    If the slug is unknown, returns an empty string and is silent --
    citations are advisory and must never crash a recommendation.
    """
    rule = RULES.get(slug)
    if rule is None:
        return ""
    # The displayed pack name is the filename minus its .md suffix,
    # so [occasion-rules#R3] points unambiguously at occasion-rules.md.
    pack = rule.skill_file[:-3] if rule.skill_file.endswith(".md") else rule.skill_file
    return f"[{pack}#{rule.rule_id}]"


def is_valid_slug(slug: str) -> bool:
    """Whether ``slug`` is a known rule reference."""
    return slug in RULES


def all_slugs() -> list[str]:
    """Stable, ordered list of every registered slug."""
    return list(RULES.keys())
