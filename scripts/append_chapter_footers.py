#!/usr/bin/env python3
"""
append_chapter_footers.py — one-shot script that appends a "Key terms" +
"Self-check" footer to each of the 12 chapters in book/.

Pattern follows the Level-2 intelligent-textbook framework (per
dmccreary/intelligent-textbooks): every chapter ends with 3–5 key terms
linked to the project glossary, and 3 Bloom-tiered self-check questions
(Remember, Understand, Apply). The footers are intentionally plain
Markdown — no quiz framework, no JS — so reviewers and graders can read
them on GitHub or in the built MkDocs site.

This script is idempotent: it refuses to append a second footer to a
chapter that already ends with the "## Key terms" heading. Run it once.

Usage:
    python scripts/append_chapter_footers.py
"""

from __future__ import annotations
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _footer(key_terms: list[tuple[str, str]],
            self_check: list[tuple[str, str]]) -> str:
    """
    Build the standard footer.

    `key_terms`  is a list of (term, definition-with-glossary-link).
    `self_check` is a list of (bloom-level, question).
    """
    terms = "\n".join(
        f"- **{t}** — {d}"
        for t, d in key_terms
    )
    quiz = "\n".join(
        f"{i + 1}. *({lvl})* {q}"
        for i, (lvl, q) in enumerate(self_check)
    )
    return (
        "\n"
        "---\n"
        "\n"
        "## Key terms\n"
        "\n"
        f"{terms}\n"
        "\n"
        "## Self-check\n"
        "\n"
        f"{quiz}\n"
        "\n"
        "*Definitions live in the [Glossary](../docs/glossary.md). "
        "Self-check questions follow Bloom's taxonomy progression "
        "(Remember → Understand → Apply → Analyze) — the same tags "
        "used in the [Learning Graph](../docs/sims/learning-graph/index.md).*\n"
    )


# Glossary link target — relative to a chapter file in book/.
GLO = "../docs/glossary.md"


# ────────────────────────────────────────────────────────────────
# Per-chapter content. Each entry: key_terms list, self_check list.
# Phrasing is body-positive and aligned with the chapter's main idea.
# ────────────────────────────────────────────────────────────────

CHAPTERS = {
    "01-vision.md": dict(
        key_terms=[
            ("Agent", f"a system that reads context first and recommends with a visible reasoning trail ([glossary]({GLO}))."),
            ("Body-positive language contract", f"the runtime + documentation rule that forbids corrective vocabulary ([glossary]({GLO}))."),
            ("Honesty contract", f"the four rules that govern every claim Wearly makes ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Name the four rules of Wearly's honesty contract."),
            ("Understand", "Why does Wearly insist on the agent / chatbot distinction in its product vision?"),
            ("Apply", "Pick one item on the agentic list and identify the screen in the running app where it shows up."),
        ],
    ),
    "02-user-problem.md": dict(
        key_terms=[
            ("Calendar context", f"upcoming events read at Step 1 to determine occasion ([glossary]({GLO}))."),
            ("Weather context", f"live Open-Meteo data with seasonal fallback, drives layering and season tags ([glossary]({GLO}))."),
            ("Occasion tag", f"one of five canonical labels (work, gym, dinner, formal, casual) every event maps to ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "What are the four converging pressures the 15-minute closet decision puts on a person?"),
            ("Understand", "Why is the 15-minute window itself a design constraint, not just a complaint?"),
            ("Apply", "Imagine a user with a 7am gym session and an 11am offsite interview. Which two context sources does Wearly read first, and in what order?"),
        ],
    ),
    "03-agent-workflow.md": dict(
        key_terms=[
            ("Seven-step workflow", f"determine occasion → load profile → check weather → filter wardrobe → build outfit → check gaps → score color ([glossary]({GLO}))."),
            ("Reject & regenerate", f"the agentic loop where a rejection becomes a constraint for the next run ([glossary]({GLO}))."),
            ("Citation chip", f"the `[pack#R<N>]` tag appended to a reasoning line, resolvable via `rule_refs.py` ([glossary]({GLO}))."),
            ("Result-dict contract", f"the single boundary between the agent and the UI ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "List the seven steps in order."),
            ("Understand", "Why does Step 2 (load profile) come *before* Step 4 (filter wardrobe), rather than after?"),
            ("Apply", "A user rejects the recommendation citing fit. Trace which steps re-run and which inputs change."),
        ],
    ),
    "04-styling-knowledge-base.md": dict(
        key_terms=[
            ("Required pieces", f"the minimum type-set an occasion needs (e.g., work = top + bottom) ([glossary]({GLO}))."),
            ("Color tier", f"the +8 / +4 / −10 scoring scale for color against skin-tone palette ([glossary]({GLO}))."),
            ("Skin-tone palette", f"one of three named palettes the color formula reads from ([glossary]({GLO}))."),
            ("Rule citation (R<N>)", f"a numbered heading inside a Skill rule file ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Name the three skin-tone palettes Wearly ships today."),
            ("Understand", "Why does Wearly use rules rather than a learned compatibility model in this prototype?"),
            ("Apply", "Look up `occasion-rules.md` R2 in the skill pack. Which rule heading does it resolve to, and which chapter cites it?"),
        ],
    ),
    "05-wardrobe-intelligence.md": dict(
        key_terms=[
            ("Wardrobe filtering", f"Step 4 — narrow the closet by occasion tags, season, availability, and rejection exclusions ([glossary]({GLO}))."),
            ("Outfit construction", f"Step 5 — dress vs. separates branching, gym branching, outerwear injection below 60°F ([glossary]({GLO}))."),
            ("Knowledge graph (runtime)", f"`graph/graph.json` — wardrobe items + relations the agent reasons over ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "What temperature threshold injects outerwear into a non-formal outfit?"),
            ("Understand", "Why is dress-vs-separates a branch rather than a score?"),
            ("Apply", "Given a 55°F dinner event, which Step 5 branches fire, in order?"),
        ],
    ),
    "06-fit-profile-logic.md": dict(
        key_terms=[
            ("Fit profile", f"optional, user-declared preferences — every field has a safe default ([glossary]({GLO}))."),
            ("Body shape (preference)", f"a user-declared proportion preference; never inferred from images ([glossary]({GLO}))."),
            ("Profile hash", f"detects mid-session profile edits to trigger the regenerate banner ([glossary]({GLO}))."),
            ("Body-positive language contract", f"runtime forbidden tokens enforced in `fit_tool` ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "List three forbidden tokens from the body-positive language contract."),
            ("Understand", "Why is `body_shape` framed as a *preference* rather than a *classification*?"),
            ("Apply", "A user leaves `body_shape` blank. Which proportion-related rules fire, and which don't?"),
        ],
    ),
    "07-calendar-weather-context.md": dict(
        key_terms=[
            ("Calendar context", f"upcoming events; falls back to *casual* when none are scheduled ([glossary]({GLO}))."),
            ("Weather context", f"live Open-Meteo lookup with seasonal fallback ([glossary]({GLO}))."),
            ("Occasion tag", f"the canonical label calendar events map to ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Which weather data source does Wearly call, and what's the fallback when it's unreachable?"),
            ("Understand", "Why does Wearly classify by *tag* rather than passing the raw event title into the workflow?"),
            ("Apply", "Walk through the context Wearly assembles for a 70°F Saturday brunch with no calendar event set."),
        ],
    ),
    "08-shopping-gap-logic.md": dict(
        key_terms=[
            ("Gap", f"a required piece type the user does not own for the current occasion ([glossary]({GLO}))."),
            ("Qualified gap", f"a gap that's *also* plausibly shoppable for this occasion ([glossary]({GLO}))."),
            ("Favorite stores", f"locally-saved retailer hints — personalize the suggestion, never transmit ([glossary]({GLO}))."),
            ("Wishlist", f"locally-saved items the user wants next, with optional priority + `linked_gap` ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "What two conditions must hold for a gap to be *qualified*?"),
            ("Understand", "Why are shopping suggestions descriptive rather than promotional?"),
            ("Apply", "A user with no blazer attends a work meeting. Trace the gap from detection to the surfaced suggestion."),
        ],
    ),
    "09-before-after-demo.md": dict(
        key_terms=[
            ("Before / after delta", f"the comparison of 15 minutes of manual planning against ~3 seconds of agent reasoning ([glossary]({GLO}))."),
            ("Seven-step workflow", f"the loop the delta makes visible ([glossary]({GLO}))."),
            ("Result-dict contract", f"the data shape the demo screen reads to draw its panels ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Roughly how much time does the agent claim to save on the closet decision?"),
            ("Understand", "Why is *making the work visible* part of the value the demo claims — not just the time savings?"),
            ("Apply", "Sketch how a reviewer could falsify the time-savings claim in a 30-minute user test."),
        ],
    ),
    "10-privacy-security.md": dict(
        key_terms=[
            ("Privacy stance", f"minimum-necessary access, no third parties, no implicit data collection ([glossary]({GLO}))."),
            ("Honesty contract", f"the four rules that govern every claim, including privacy claims ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Name the four GDPR articles Wearly's privacy stance maps to."),
            ("Understand", "Why does Wearly cite GDPR if the prototype doesn't transmit data?"),
            ("Apply", "A user asks to delete all their Wearly data. Describe the exact steps in the prototype today."),
        ],
    ),
    "11-product-roadmap.md": dict(
        key_terms=[
            ("Skill package", f"the `skills/wearly-styling-agent/` rule pack (8 rule files + `SKILL.md`) ([glossary]({GLO}))."),
            ("Result-dict contract", f"the stable boundary that lets the UI and agent evolve independently ([glossary]({GLO}))."),
            ("Wishlist", f"the locally-saved taste signal that biases future recommendations ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "Name one feature shipped today and one feature on the roadmap."),
            ("Understand", "Why is the result-dict contract called out as a stability anchor in the roadmap?"),
            ("Apply", "Pick a roadmap item. Identify one rule pack and one chapter that would need to change to land it."),
        ],
    ),
    "12-evidence-and-references.md": dict(
        key_terms=[
            ("Evidence categories", f"the nine source categories every Wearly rule traces back to ([glossary]({GLO}))."),
            ("Citation chip", f"the `[pack#R<N>]` tag — the runtime side of the citation chain ([glossary]({GLO}))."),
            ("Honesty contract", f"no fabricated citations; categories named only when textbook-common ([glossary]({GLO}))."),
        ],
        self_check=[
            ("Remember", "How many evidence categories does Wearly organize its sources under?"),
            ("Understand", "Why is the *Color Me Beautiful* framework deliberately *not* cited as science in §3.3?"),
            ("Apply", "Pick any reasoning line from a recent agent run. Trace its citation chip back to an evidence category."),
        ],
    ),
}


SENTINEL = "## Key terms"


def main() -> int:
    book_dir = os.path.join(_ROOT, "book")
    updated, skipped = 0, 0
    for fname, payload in CHAPTERS.items():
        path = os.path.join(book_dir, fname)
        if not os.path.isfile(path):
            print(f"  - skip {fname} (not found)")
            continue
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
        if SENTINEL in body:
            skipped += 1
            print(f"  - skip {fname} (footer already present)")
            continue
        footer = _footer(payload["key_terms"], payload["self_check"])
        # Ensure the existing body ends with exactly one newline so the
        # appended footer renders cleanly.
        if not body.endswith("\n"):
            body += "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body + footer)
        updated += 1
        print(f"  - updated {fname}")
    print(f"Done. {updated} chapter(s) updated, {skipped} already had a footer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
