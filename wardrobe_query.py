"""
wardrobe_query.py — small natural-language-ish query layer over the wardrobe.

Pattern borrowed from a classmate's project (the dream-journal app's "what
did I dream about when anxious?" knowledge-graph traversal): a structured
domain dataset is more useful when you can *ask it questions*, not just
visualize it. These five helpers each answer one common question about
the user's closet, with deterministic logic over the merged wardrobe and
the wear-history file.

Each function returns a uniform shape::

    {
        "question": "human-readable phrasing of the query",
        "items":    [item dicts ...],
        "summary":  "short body-positive plain-English summary",
        "rule":     "[skill-rule-pack#R<N>]"   # citation tag
    }

No LLM is called. The Streamlit UI surfaces these as canned buttons and
displays the result with the same item-card style used elsewhere.
"""

from __future__ import annotations

from typing import List

from wardrobe_tool import get_wardrobe
from history_tool import get_history, days_since_last_worn
from rule_refs import cite


def _all_items(wardrobe: dict) -> List[dict]:
    return (
        list(wardrobe.get("clothing", []))
        + list(wardrobe.get("shoes", []))
        + list(wardrobe.get("accessories", []))
    )


def items_not_worn_in_days(n: int = 30) -> dict:
    """Items the user owns but hasn't worn in at least N days
    (including items never worn). Useful for nudging rotation."""
    res = get_wardrobe()
    if not res.get("success"):
        return {"question": f"items not worn in {n}+ days",
                "items": [], "summary": "Wardrobe unavailable.", "rule": ""}
    history = get_history().get("history", {})
    out = []
    for item in _all_items(res["wardrobe"]):
        iid = item.get("id", "")
        if not iid:
            continue
        days = days_since_last_worn(iid, history)
        worn = history.get(iid, {}).get("worn_count", 0)
        if worn == 0 or (isinstance(days, int) and days >= n):
            out.append(item)
    summary = (
        f"{len(out)} item{'s' if len(out) != 1 else ''} in your closet "
        f"haven't been worn in the last {n} days — worth bringing back into rotation."
    )
    return {
        "question": f"What have I not worn in the last {n} days?",
        "items": out,
        "summary": summary,
        "rule": cite("history#R4"),
    }


def items_by_color(color: str) -> dict:
    """Items whose color name matches (case-insensitive substring)."""
    res = get_wardrobe()
    color = (color or "").strip().lower()
    if not res.get("success") or not color:
        return {"question": f"items by color: {color}",
                "items": [], "summary": "Wardrobe unavailable or no color given.", "rule": ""}
    out = [
        i for i in _all_items(res["wardrobe"])
        if color in (i.get("color", "") or "").lower()
    ]
    summary = (
        f"{len(out)} item{'s' if len(out) != 1 else ''} in your closet "
        f"contain the color \"{color}\"."
    )
    return {
        "question": f"What do I own in {color}?",
        "items": out,
        "summary": summary,
        "rule": cite("color#R1"),
    }


def most_worn(n: int = 5) -> dict:
    """The top N most-worn items by worn_count (descending)."""
    res = get_wardrobe()
    if not res.get("success"):
        return {"question": f"top {n} most-worn",
                "items": [], "summary": "Wardrobe unavailable.", "rule": ""}
    history = get_history().get("history", {})
    items = []
    for item in _all_items(res["wardrobe"]):
        iid = item.get("id", "")
        worn = history.get(iid, {}).get("worn_count", 0)
        items.append((worn, item))
    items.sort(key=lambda t: -t[0])
    out = [it for w, it in items[:n] if w > 0]
    summary = (
        f"Your {len(out)} most-loved piece{'s' if len(out) != 1 else ''} "
        f"by confirmed wear count."
        if out else
        "No wear history yet — confirm an outfit to start building this list."
    )
    return {
        "question": f"What are my {n} most-worn pieces?",
        "items": out,
        "summary": summary,
        "rule": cite("history#R2"),
    }


def count_by_type() -> dict:
    """Distribution of items by type — a small picture of wardrobe shape."""
    res = get_wardrobe()
    if not res.get("success"):
        return {"question": "how is my wardrobe distributed by type?",
                "items": [], "summary": "Wardrobe unavailable.", "rule": ""}
    counts: dict = {}
    for item in _all_items(res["wardrobe"]):
        t = item.get("type", "other")
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values())
    summary = (
        "Wardrobe distribution: "
        + ", ".join(f"{t}={n}" for t, n in sorted(counts.items()))
        + f" (total {total})."
    )
    # Return per-type representative items for the UI.
    items_seen: dict = {}
    for item in _all_items(res["wardrobe"]):
        t = item.get("type", "other")
        if t not in items_seen:
            items_seen[t] = item
    representatives = list(items_seen.values())
    return {
        "question": "How is my wardrobe distributed by type?",
        "items": representatives,
        "summary": summary,
        "rule": cite("wardrobe#R3"),
        "counts": counts,
    }


def items_for_occasion(occasion_tag: str, season: str = "all") -> dict:
    """Items that match a given occasion + season — the same filter the
    agent uses internally, surfaced as a query."""
    from wardrobe_tool import filter_items_by_occasion
    res = filter_items_by_occasion(occasion_tag, season)
    out = (
        list(res.get("clothing", []))
        + list(res.get("shoes", []))
        + list(res.get("accessories", []))
    )
    summary = (
        f"{len(out)} item{'s' if len(out) != 1 else ''} match "
        f"{occasion_tag!r} in {season} season — the candidate pool the agent "
        f"would draw from at Step 4."
    )
    return {
        "question": f"What in my closet would the agent consider for a {occasion_tag} occasion?",
        "items": out,
        "summary": summary,
        "rule": cite("wardrobe#R3"),
    }


# Canonical list of pre-baked queries the UI exposes as buttons.
CANNED_QUERIES = [
    ("Worn 30+ days ago",         lambda: items_not_worn_in_days(30)),
    ("Most-loved pieces",         lambda: most_worn(5)),
    ("Wardrobe shape",            lambda: count_by_type()),
    ("Work-ready pieces",         lambda: items_for_occasion("work")),
    ("Casual-ready pieces",       lambda: items_for_occasion("casual")),
]
