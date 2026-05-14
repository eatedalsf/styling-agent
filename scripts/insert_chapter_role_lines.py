#!/usr/bin/env python3
"""
insert_chapter_role_lines.py — adds a one-line italic role eyebrow
under each chapter's H1 heading.

The Wearly Intelligent Book is the learning and reference companion
for the styling-agent prototype. Each chapter explains a different
slice of the agent's reasoning. To keep that relationship visible
from any landing point, every chapter carries a single italic
"eyebrow" line right under its H1 that frames the chapter as part of
the reference layer:

    *The app does X; this chapter explains how / why.*

This script inserts that line exactly once per chapter. It is
idempotent — if the sentinel (the leading "*The app ") is already
present in the chapter, the script skips the file. Pattern mirrors
scripts/append_chapter_footers.py (the per-chapter Key-terms +
Self-check footer inserter).

Usage:
    python scripts/insert_chapter_role_lines.py
"""

from __future__ import annotations
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Per-chapter role eyebrow. Each line is under 20 words, italic,
# follows the shape "The app does X; this chapter explains how/why."
# Phrasing is body-positive and matches the canonical book-vs-app
# framing in book/index.md.
ROLE_LINES = {
    "01-vision.md":
        "*The app is the styling agent in motion; this chapter "
        "explains what it is, who it serves, and what it deliberately isn't.*",
    "02-user-problem.md":
        "*The app responds to a 15-minute closet decision; this "
        "chapter explains why that decision is the design constraint "
        "everything else follows.*",
    "03-agent-workflow.md":
        "*The app runs this loop every time you tap "
        "\"Plan today's outfit\"; this chapter explains why the seven "
        "steps are shaped the way they are.*",
    "04-styling-knowledge-base.md":
        "*The app applies these rules at runtime; this chapter is "
        "the reference layer that explains each rule pack and the "
        "data it reads.*",
    "05-wardrobe-intelligence.md":
        "*The app filters and builds outfits from this data model; "
        "this chapter explains how items become candidates and "
        "candidates become outfits.*",
    "06-fit-profile-logic.md":
        "*The app reads the fit profile every run; this chapter "
        "explains how body-positive personalization is encoded and "
        "enforced.*",
    "07-calendar-weather-context.md":
        "*The app reads two external context sources; this chapter "
        "explains how each one steers the recommendation.*",
    "08-shopping-gap-logic.md":
        "*The app surfaces gaps when an occasion needs a piece you "
        "don't own; this chapter explains the gap-detection logic "
        "and its body-positive tone rules.*",
    "09-before-after-demo.md":
        "*The app demonstrates the time delta in real time; this "
        "chapter explains what \"before / after\" means and what it "
        "doesn't claim.*",
    "10-privacy-security.md":
        "*The app keeps data local; this chapter explains the "
        "privacy stance the prototype implements today and what "
        "production would look like.*",
    "11-product-roadmap.md":
        "*The app is the prototype state; this chapter explains "
        "where the agent goes next and why each phase is ordered the "
        "way it is.*",
    "12-evidence-and-references.md":
        "*The app applies rules; this chapter explains the evidence "
        "base those rules trace back to and what still needs "
        "verification.*",
}


# A chapter is considered "already framed" if it already contains a
# line starting with "*The app " — the canonical sentinel. We match on
# that leading italic-marker + canonical opening to avoid both
# (a) duplicating the eyebrow on re-runs and (b) accidentally matching
# unrelated prose like a sentence that begins "The app".
SENTINEL_RE = re.compile(r"^\*The app ", re.MULTILINE)

# The H1 pattern for chapter pages: "# 01 · Product vision", etc.
# Group 1 is the heading line including its newline.
H1_RE = re.compile(r"^(# .+\n)", re.MULTILINE)


def _insert(body: str, eyebrow: str) -> str:
    """Insert `eyebrow` as the next non-blank line after the first H1.

    Produces:

        # 01 · Title

        *The app …; this chapter explains …*

        <existing first paragraph>
    """
    match = H1_RE.search(body)
    if not match:
        # No H1? Leave the file alone; a chapter without an H1 is a
        # bug we don't want to mask.
        return body
    insert_at = match.end()
    return body[:insert_at] + "\n" + eyebrow + "\n" + body[insert_at:]


def main() -> int:
    book_dir = os.path.join(_ROOT, "book")
    updated, skipped = 0, 0
    for fname, eyebrow in ROLE_LINES.items():
        path = os.path.join(book_dir, fname)
        if not os.path.isfile(path):
            print(f"  - skip {fname} (not found)")
            continue
        with open(path, "r", encoding="utf-8") as fh:
            body = fh.read()
        if SENTINEL_RE.search(body):
            skipped += 1
            print(f"  - skip {fname} (already framed)")
            continue
        new_body = _insert(body, eyebrow)
        if new_body == body:
            print(f"  - skip {fname} (no H1 found)")
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_body)
        updated += 1
        print(f"  - updated {fname}")
    print(f"Done. {updated} chapter(s) updated, {skipped} already framed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
