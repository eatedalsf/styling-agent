#!/usr/bin/env python3
"""
generate_wearly_kg.py — build the Wearly Knowledge Graph JSON.

The Wearly Knowledge Graph is the THIRD interactive graph the project
ships, distinct from both the Learning Graph (reader concepts) and the
Reasoning Graph (one-recommendation explanation). It models the
*reusable domain knowledge and user-pattern knowledge* the agent can
reason over.

Three layers, in one JSON file:

  1. DOMAIN — User, FitProfile, SkinTonePalette, OccasionType,
     WeatherCondition, WardrobeItemType, ColorFamily, RulePack, and
     the rule packs' rule headings. Static. Sourced from styling_agent
     constants, color_rules.json, rule_refs.py, and the skill files.
  2. USER_BEHAVIOR — WardrobeItem, WishlistItem, FavoriteStore,
     OutfitRecommendation-as-type, Feedback-as-type. Sourced from the
     seed wardrobe (anonymized "Demo User") and seed wear history.
  3. RUNTIME — WorkflowStep (1..7) and the typed edges that connect
     rule packs to the steps they power.

Generation is deterministic (same inputs -> identical JSON).

Public-safety contract:

  By default this script reads ONLY committed seed data:
    - wardrobe.json (anonymized seed wardrobe)
    - seed_wear_history.json (committed demo wear history)
    - seed_calendar_events.json (committed demo events)
    - color_rules.json
    - rule_refs.py (the canonical rule registry)
    - styling_agent.OCCASION_TAG_MAP / REQUIRED_PIECES

  With --include-user (developer-only), it ALSO reads the gitignored
  per-user overlays (user_wardrobe.json, wear_history.json) so the
  developer can see THEIR own usage-weighted graph locally. The
  committed JSON in graph/wearly-knowledge-graph.json is always built
  from seed data; the developer's local exploration of the
  --include-user view is private.

Usage:
  python scripts/generate_wearly_kg.py                  # seed-only (public)
  python scripts/generate_wearly_kg.py --include-user   # local overlay
  python scripts/generate_wearly_kg.py --output other.json
"""
from __future__ import annotations
import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List, Optional


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────
# Static domain vocabularies
# ─────────────────────────────────────────────

# Color families collapse the long color list into a small set the
# graph can show as nodes without 50 leaf colors. Each named color in
# wardrobe.json + color_rules.json maps to one family.
COLOR_FAMILIES: Dict[str, List[str]] = {
    "warm-neutral": ["cream", "camel", "tan", "warm white", "beige", "stone"],
    "cool-neutral": ["white", "silver", "pearl", "ice blue", "cool grey", "grey"],
    "deep-neutral": ["black", "charcoal", "chocolate brown", "navy"],
    "warm-rich":   ["terracotta", "burnt orange", "rust", "burgundy",
                    "olive", "deep teal", "mustard", "gold"],
    "cool-rich":   ["cobalt", "emerald", "royal blue", "deep purple",
                    "plum", "raspberry"],
    "soft":        ["blush", "sage green", "nude", "lavender", "pink",
                    "dusty pink"],
    "indigo":      ["indigo", "denim"],
}

# Layer / temperature bands the agent uses at runtime.
WEATHER_CONDITIONS = [
    {"id": "weather:cold",      "label": "Cold (<40°F)",   "band": "lt40",   "layer": "heavy outerwear"},
    {"id": "weather:cool",      "label": "Cool (40–59°F)", "band": "40-59",  "layer": "light outerwear"},
    {"id": "weather:mild",      "label": "Mild (60–74°F)", "band": "60-74",  "layer": "no outerwear"},
    {"id": "weather:warm",      "label": "Warm (75–84°F)", "band": "75-84",  "layer": "lightweight"},
    {"id": "weather:hot",       "label": "Hot (≥85°F)",    "band": "ge85",   "layer": "lightweight, breathable"},
]

# Seven workflow steps — the same audit log the agent emits at runtime.
WORKFLOW_STEPS = [
    ("step:1", "1 · Determine Occasion"),
    ("step:2", "2 · Load Style Profile"),
    ("step:3", "3 · Check Weather"),
    ("step:4", "4 · Filter Wardrobe"),
    ("step:5", "5 · Build Outfit"),
    ("step:6", "6 · Check for Wardrobe Gaps"),
    ("step:7", "7 · Color Coordination Check"),
]

# Which rule pack powers which workflow step. Sourced from the skill
# rule files' Source basis footers + the rule_refs.py organization.
PACK_POWERS_STEP: List[tuple[str, str]] = [
    ("pack:occasion-rules",              "step:1"),
    ("pack:fit-silhouette-rules",        "step:2"),
    ("pack:weather-rules",               "step:3"),
    ("pack:wardrobe-filtering-rules",    "step:4"),
    ("pack:occasion-rules",              "step:5"),
    ("pack:wear-history-rules",          "step:5"),
    ("pack:fit-silhouette-rules",        "step:5"),
    ("pack:shopping-gap-rules",          "step:6"),
    ("pack:color-coordination-rules",    "step:7"),
]

# Node-type styling (vis-network attributes) per ontology entity.
NODE_TYPE_STYLES: Dict[str, Dict[str, Any]] = {
    # ── DOMAIN layer ──
    "User":              {"shape": "diamond", "color": "#1C1917", "border": "#1C1917", "size": 32, "font_color": "#FFFFFF"},
    "FitProfile":        {"shape": "box",     "color": "#FAF3EE", "border": "#9F5A36", "size": 22},
    "SkinTonePalette":   {"shape": "box",     "color": "#F4EFE8", "border": "#A85A3C", "size": 22},
    "OccasionType":      {"shape": "box",     "color": "#F5EDE3", "border": "#C17F5A", "size": 26},
    "WeatherCondition":  {"shape": "box",     "color": "#FDFAF7", "border": "#7C6F64", "size": 22},
    "WardrobeItemType":  {"shape": "box",     "color": "#EFE3CC", "border": "#7C6F64", "size": 22},
    "ColorFamily":       {"shape": "dot",     "color": "#FAF3EE", "border": "#9F5A36", "size": 20},
    "RulePack":          {"shape": "hexagon", "color": "#FDFAF7", "border": "#1C1917", "size": 24},
    "Rule":              {"shape": "dot",     "color": "#F5F0E9", "border": "#A8937E", "size": 16},
    "WorkflowStep":      {"shape": "ellipse", "color": "#F8F4ED", "border": "#1C1917", "size": 22},

    # ── USER_BEHAVIOR layer ──
    "WardrobeItem":      {"shape": "dot",     "color": "#F5EDE3", "border": "#A8937E", "size": 18},
    "WishlistItem":      {"shape": "triangle","color": "#FDF3EE", "border": "#9F5A36", "size": 18},
    "FavoriteStore":     {"shape": "star",    "color": "#FAF3EE", "border": "#C17F5A", "size": 18},

    # ── RUNTIME-archetype layer ──
    "OutfitRecommendation": {"shape": "diamond", "color": "#FDFAF7", "border": "#1C1917", "size": 26},
    "WardrobeGap":          {"shape": "triangleDown", "color": "#FDF3EE", "border": "#B91C1C", "size": 22},
    "ShoppingSuggestion":   {"shape": "triangleDown", "color": "#FDF3EE", "border": "#7C6F64", "size": 18},
    "Feedback":             {"shape": "square", "color": "#EFE3CC", "border": "#7C6F64", "size": 18},
}

# Edge-type catalog. Each entry: (id, label, source_types, target_types, layer).
EDGE_TYPES: List[Dict[str, Any]] = [
    # User-centric ownership
    {"id": "HAS_PROFILE",        "label": "has profile",        "layer": "domain",
     "source_types": ["User"],   "target_types": ["FitProfile"]},
    {"id": "HAS_SKIN_TONE",      "label": "has skin tone",      "layer": "domain",
     "source_types": ["User"],   "target_types": ["SkinTonePalette"]},
    {"id": "OWNS",               "label": "owns",               "layer": "user_behavior",
     "source_types": ["User"],   "target_types": ["WardrobeItem"]},
    {"id": "HAS_FAVORITE_STORE", "label": "has favorite store", "layer": "user_behavior",
     "source_types": ["User"],   "target_types": ["FavoriteStore"]},
    {"id": "HAS_WISHLIST_ITEM",  "label": "wishes for",         "layer": "user_behavior",
     "source_types": ["User"],   "target_types": ["WishlistItem"]},
    {"id": "PREFERS",            "label": "prefers",            "layer": "user_behavior",
     "source_types": ["User"],   "target_types": ["ColorFamily"]},

    # Occasion knowledge
    {"id": "REQUIRES",           "label": "requires",           "layer": "domain",
     "source_types": ["OccasionType"], "target_types": ["WardrobeItemType"]},
    {"id": "USES_RULE",          "label": "uses rule",          "layer": "domain",
     "source_types": ["OccasionType", "WeatherCondition"], "target_types": ["RulePack"]},

    # Wardrobe item classification
    {"id": "HAS_TYPE",           "label": "is a",               "layer": "user_behavior",
     "source_types": ["WardrobeItem"], "target_types": ["WardrobeItemType"]},
    {"id": "HAS_COLOR",          "label": "has color family",   "layer": "user_behavior",
     "source_types": ["WardrobeItem", "WishlistItem"], "target_types": ["ColorFamily"]},
    {"id": "SUITABLE_FOR",       "label": "suitable for",       "layer": "user_behavior",
     "source_types": ["WardrobeItem"], "target_types": ["OccasionType"]},

    # Profile / palette
    {"id": "SHAPES_FIT_FOR",     "label": "shapes fit for",     "layer": "domain",
     "source_types": ["FitProfile"], "target_types": ["WardrobeItemType"]},
    {"id": "EVALUATES",          "label": "evaluates",          "layer": "domain",
     "source_types": ["Rule"], "target_types": ["SkinTonePalette", "WardrobeItemType"]},
    {"id": "CONTAINS_RULE",      "label": "contains",           "layer": "domain",
     "source_types": ["RulePack"], "target_types": ["Rule"]},

    # Runtime archetype links
    {"id": "POWERS",             "label": "powers",             "layer": "runtime",
     "source_types": ["RulePack"], "target_types": ["WorkflowStep"]},
    {"id": "PRODUCES",           "label": "produces",           "layer": "runtime",
     "source_types": ["WorkflowStep"], "target_types": ["OutfitRecommendation", "WardrobeGap", "ShoppingSuggestion"]},
    {"id": "CONTAINS_ITEM",      "label": "contains",           "layer": "runtime",
     "source_types": ["OutfitRecommendation"], "target_types": ["WardrobeItem"]},
    {"id": "FLAGS_GAP",          "label": "flags gap",          "layer": "runtime",
     "source_types": ["OutfitRecommendation"], "target_types": ["WardrobeGap"]},
    {"id": "SUGGESTS",           "label": "suggests",           "layer": "runtime",
     "source_types": ["WardrobeGap"], "target_types": ["ShoppingSuggestion"]},
    {"id": "REJECTS",            "label": "rejects",            "layer": "runtime",
     "source_types": ["Feedback"], "target_types": ["WardrobeItem"]},
    {"id": "WISHLIST_CLOSES_GAP", "label": "closes gap",        "layer": "runtime",
     "source_types": ["WishlistItem"], "target_types": ["WardrobeGap"]},
]


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _classify_color(color: str) -> str:
    """Map a raw color name to a ColorFamily id."""
    c = (color or "").lower().strip()
    if not c:
        return "color-family:unknown"
    # multi-word colors ("white/gold") fall into the first part
    head = c.split("/")[0].strip()
    for family, members in COLOR_FAMILIES.items():
        if head in members or any(m in head for m in members):
            return f"color-family:{family}"
        # contained-by check ("warm white" -> "warm-neutral")
        if any(member in head or head in member for member in members):
            return f"color-family:{family}"
    return "color-family:other"


def _slug(s: str) -> str:
    return (s or "").lower().replace(" ", "-").replace("_", "-")


def _now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


# ─────────────────────────────────────────────
# Builders
# ─────────────────────────────────────────────

def build_domain_nodes(occasion_canonical: List[str],
                       skin_tones: List[str],
                       rule_packs: List[Dict[str, Any]],
                       rules: List[Dict[str, Any]],
                       item_types: List[str]) -> List[Dict[str, Any]]:
    """Static domain-layer nodes."""
    nodes: List[Dict[str, Any]] = []

    # SkinTonePalette (3, from color_rules.json)
    for skin in skin_tones:
        nodes.append({
            "id": f"skin:{_slug(skin)}",
            "type": "SkinTonePalette",
            "layer": "domain",
            "label": skin.title(),
            "weight": 1.0,
            "metrics": {},
        })

    # OccasionType
    for occ in occasion_canonical:
        nodes.append({
            "id": f"occasion:{occ}",
            "type": "OccasionType",
            "layer": "domain",
            "label": occ.capitalize(),
            "weight": 1.0,
            "metrics": {},
        })

    # WeatherCondition
    for w in WEATHER_CONDITIONS:
        nodes.append({
            "id": w["id"],
            "type": "WeatherCondition",
            "layer": "domain",
            "label": w["label"],
            "weight": 1.0,
            "metrics": {"layer_advice": w["layer"], "band": w["band"]},
        })

    # WardrobeItemType
    for t in item_types:
        nodes.append({
            "id": f"type:{t}",
            "type": "WardrobeItemType",
            "layer": "domain",
            "label": t.capitalize(),
            "weight": 1.0,
            "metrics": {},
        })

    # ColorFamily
    for family in COLOR_FAMILIES.keys():
        nodes.append({
            "id": f"color-family:{family}",
            "type": "ColorFamily",
            "layer": "domain",
            "label": family.replace("-", " ").title(),
            "weight": 1.0,
            "metrics": {"sample_colors": COLOR_FAMILIES[family][:4]},
        })

    # RulePack + individual Rule headings
    for pack in rule_packs:
        nodes.append({
            "id": pack["id"],
            "type": "RulePack",
            "layer": "domain",
            "label": pack["label"],
            "weight": 1.0,
            "metrics": {"file": pack["file"], "rule_count": pack["rule_count"]},
        })
    for rule in rules:
        nodes.append({
            "id": rule["id"],
            "type": "Rule",
            "layer": "domain",
            "label": rule["label"],
            "weight": 1.0,
            "metrics": {"slug": rule["slug"], "summary": rule["summary"]},
        })

    # WorkflowStep (in domain so they cluster cleanly)
    for sid, label in WORKFLOW_STEPS:
        nodes.append({
            "id": sid,
            "type": "WorkflowStep",
            "layer": "runtime",
            "label": label,
            "weight": 1.0,
            "metrics": {},
        })

    return nodes


def build_user_behavior_nodes(owner: Dict[str, Any],
                              wardrobe_items: List[Dict[str, Any]],
                              wear_history: Dict[str, Any],
                              wishlist_items: List[Dict[str, Any]],
                              favorite_stores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """User-behavior-layer nodes: User, FitProfile, WardrobeItem, etc.

    Node weight is derived from observed usage signals so the visualizer
    can size each node to encode its importance:

      WardrobeItem.weight = 1.0 + 0.20 × worn_count (capped)
      WardrobeItemType / OccasionType / ColorFamily weights are
      aggregated below by the cross-link computation step.
    """
    nodes: List[Dict[str, Any]] = []

    # User (the owner of this graph instance — anonymized seed)
    user_name = owner.get("name", "Demo User")
    nodes.append({
        "id": "user:demo",
        "type": "User",
        "layer": "domain",
        "label": user_name,
        "weight": 1.0,
        "metrics": {"item_count": len(wardrobe_items)},
    })

    # FitProfile
    nodes.append({
        "id": "fit:demo",
        "type": "FitProfile",
        "layer": "domain",
        "label": f"{owner.get('body_shape','—')} · {owner.get('preferred_fit','—')}",
        "weight": 1.0,
        "metrics": {
            "body_shape":         owner.get("body_shape"),
            "preferred_fit":      owner.get("preferred_fit"),
            "modesty_preference": owner.get("modesty_preference"),
            "style_preferences":  owner.get("style_preferences"),
        },
    })

    # WardrobeItem nodes
    for it in wardrobe_items:
        iid = it.get("id") or it.get("name") or "?"
        h = wear_history.get(iid, {}) if isinstance(wear_history, dict) else {}
        worn = int(h.get("worn_count", 0) or 0)
        # Versatility = count of distinct occasion tags the item carries
        tags = [t.lower() for t in (it.get("tags") or [])]
        versatility = len({t for t in tags if t in {
            "work", "gym", "dinner", "formal", "casual",
            "smart_casual", "athletic", "weekend", "evening", "date"
        }})
        # Importance weight (clamped 1.0–2.5)
        weight = round(1.0 + min(1.5, 0.20 * worn + 0.10 * versatility), 2)
        nodes.append({
            "id": f"item:{iid}",
            "type": "WardrobeItem",
            "layer": "user_behavior",
            "label": it.get("name", iid),
            "weight": weight,
            "metrics": {
                "color":        it.get("color"),
                "type":         it.get("type"),
                "formality":    it.get("formality"),
                "tags":         tags,
                "worn_count":   worn,
                "last_worn":    h.get("last_worn_date"),
                "versatility":  versatility,
            },
        })

    # FavoriteStore (public-safe seed has none; user overlay may add)
    for store in favorite_stores or []:
        sid = store.get("id") or _slug(store.get("name", "store"))
        nodes.append({
            "id": f"store:{sid}",
            "type": "FavoriteStore",
            "layer": "user_behavior",
            "label": store.get("name", "Store"),
            "weight": 1.0 + 0.05 * float(store.get("times_chosen", 0) or 0),
            "metrics": {"city": store.get("city"), "tags": store.get("tags")},
        })

    # WishlistItem
    for item in wishlist_items or []:
        wid = item.get("id") or _slug(item.get("name", "wish"))
        nodes.append({
            "id": f"wishlist:{wid}",
            "type": "WishlistItem",
            "layer": "user_behavior",
            "label": item.get("name", "Wishlist item"),
            "weight": 1.0,
            "metrics": {
                "category":      item.get("category"),
                "priority":      item.get("priority"),
                "linked_gap":    item.get("linked_gap"),
                "color":         item.get("color"),
                "tags":          item.get("tags"),
            },
        })

    return nodes


def build_edges(nodes: List[Dict[str, Any]],
                wardrobe_items: List[Dict[str, Any]],
                wishlist_items: List[Dict[str, Any]],
                occasion_canonical: List[str],
                required_pieces: Dict[str, List[str]],
                color_rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Typed edges across all three layers.

    The edge list is deterministic (sorted at the end) and uses string
    type identifiers from EDGE_TYPES so the visualizer can group them.
    """
    edges: List[Dict[str, Any]] = []
    nodes_by_id = {n["id"]: n for n in nodes}

    def _add(src: str, type_: str, tgt: str, weight: float = 1.0,
             metadata: Optional[Dict[str, Any]] = None):
        if src in nodes_by_id and tgt in nodes_by_id:
            edges.append({"from": src, "to": tgt, "type": type_,
                          "weight": round(weight, 3),
                          "metadata": metadata or {}})

    # User → fit / skin tone / favorite stores / wishlist
    _add("user:demo", "HAS_PROFILE", "fit:demo")
    # The owner's skin tone — look up the matching palette node.
    owner_skin = next(
        (n for n in nodes if n["type"] == "SkinTonePalette"
         and (n.get("label") or "").lower() == (nodes_by_id["fit:demo"]["metrics"].get("body_shape") or "")),
        None,
    )
    # Fallback: use the first palette (warm olive in the seed)
    skin_node = next((n for n in nodes if n["type"] == "SkinTonePalette"
                       and n["label"].lower() == "warm olive"), None)
    if skin_node:
        _add("user:demo", "HAS_SKIN_TONE", skin_node["id"])

    # User → WardrobeItem (OWNS) — primary edge per item
    for it in wardrobe_items:
        iid = it.get("id") or it.get("name") or "?"
        _add("user:demo", "OWNS", f"item:{iid}")

    # User → FavoriteStore, WishlistItem
    for n in nodes:
        if n["type"] == "FavoriteStore":
            _add("user:demo", "HAS_FAVORITE_STORE", n["id"])
        if n["type"] == "WishlistItem":
            _add("user:demo", "HAS_WISHLIST_ITEM", n["id"])

    # OccasionType → required WardrobeItemType
    for occ, types in required_pieces.items():
        for t in types:
            _add(f"occasion:{occ}", "REQUIRES", f"type:{t}",
                 weight=1.0, metadata={"required": True})

    # OccasionType → rule pack (occasion-rules powers every occasion)
    for occ in occasion_canonical:
        _add(f"occasion:{occ}", "USES_RULE", "pack:occasion-rules")

    # WeatherCondition → weather-rules pack
    for w in WEATHER_CONDITIONS:
        _add(w["id"], "USES_RULE", "pack:weather-rules")

    # WardrobeItem → type / color family / occasion
    for it in wardrobe_items:
        iid = it.get("id") or it.get("name") or "?"
        node_id = f"item:{iid}"

        # Type
        t = (it.get("type") or "").lower().strip()
        if t:
            _add(node_id, "HAS_TYPE", f"type:{t}")

        # Color family
        family_id = _classify_color(it.get("color", ""))
        # color-family:other / unknown won't have a node — only emit if it does
        _add(node_id, "HAS_COLOR", family_id)

        # Suitable-for occasion
        canonical = set()
        for tag in (it.get("tags") or []):
            tag_lc = tag.lower()
            # Map tag → canonical occasion (work, gym, etc.)
            from styling_agent import OCCASION_TAG_MAP  # type: ignore
            occ = OCCASION_TAG_MAP.get(tag_lc)
            if occ:
                canonical.add(occ)
        for occ in canonical:
            _add(node_id, "SUITABLE_FOR", f"occasion:{occ}")

    # Wishlist → color family + linked gap (gap node not present yet —
    # we model the LINK to a WardrobeGap type rather than a specific instance)
    for w in wishlist_items or []:
        wid = w.get("id") or _slug(w.get("name", "wish"))
        node_id = f"wishlist:{wid}"
        if w.get("color"):
            _add(node_id, "HAS_COLOR", _classify_color(w["color"]))

    # RulePack → Rule (containment)
    for n in nodes:
        if n["type"] != "Rule":
            continue
        slug = n["metrics"].get("slug", "")
        if "#" not in slug:
            continue
        pack_name = slug.split("#")[0]
        _add(f"pack:{pack_name}", "CONTAINS_RULE", n["id"])

    # RulePack → WorkflowStep (POWERS)
    for pack_id, step_id in PACK_POWERS_STEP:
        _add(pack_id, "POWERS", step_id)

    # Color rules → skin tone (the runtime relationship)
    for n in nodes:
        if n["type"] != "Rule":
            continue
        slug = n["metrics"].get("slug", "")
        if slug.startswith("color#"):
            for skin in nodes:
                if skin["type"] == "SkinTonePalette":
                    _add(n["id"], "EVALUATES", skin["id"], weight=0.5)

    # Fit rules → garment-only item types (R1 / R2 / R8)
    for n in nodes:
        if n["type"] != "Rule":
            continue
        slug = n["metrics"].get("slug", "")
        if slug.startswith("fit#"):
            for it_type in ("top", "bottom", "dress", "outerwear", "activewear"):
                _add(n["id"], "EVALUATES", f"type:{it_type}", weight=0.4)

    # Sort for determinism
    edges.sort(key=lambda e: (e["from"], e["type"], e["to"]))
    return edges


def aggregate_weights(nodes: List[Dict[str, Any]],
                      edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Roll WardrobeItem.weight up into ColorFamily / WardrobeItemType /
    OccasionType nodes so categories visibly scale with how much actual
    user activity lives behind them."""
    by_id = {n["id"]: n for n in nodes}
    # For each item, distribute its weight to its connected family/type/occ.
    for e in edges:
        if e["type"] in ("HAS_COLOR", "HAS_TYPE", "SUITABLE_FOR"):
            src = by_id.get(e["from"])
            tgt = by_id.get(e["to"])
            if not src or not tgt:
                continue
            if src["type"] == "WardrobeItem":
                tgt["weight"] = round(tgt.get("weight", 1.0) +
                                       0.10 * src.get("weight", 1.0), 3)
                tgt["metrics"].setdefault("item_count", 0)
                tgt["metrics"]["item_count"] += 1
    # Clamp final weights so a popular category doesn't blow out the viewer.
    for n in nodes:
        n["weight"] = max(1.0, min(3.0, round(float(n.get("weight", 1.0)), 3)))
    return nodes


# ─────────────────────────────────────────────
# Source-data loaders
# ─────────────────────────────────────────────

def _load_rule_packs_and_rules():
    """Extract rule-pack + rule nodes from the rule_refs registry."""
    sys.path.insert(0, _ROOT)
    import rule_refs  # type: ignore
    packs: Dict[str, Dict[str, Any]] = {}
    rules: List[Dict[str, Any]] = []
    for slug, rule in rule_refs.RULES.items():
        pack_name = rule.skill_file[:-3] if rule.skill_file.endswith(".md") else rule.skill_file
        if pack_name not in packs:
            packs[pack_name] = {
                "id":         f"pack:{pack_name}",
                "label":      pack_name.replace("-", " ").title(),
                "file":       rule.skill_file,
                "rule_count": 0,
            }
        packs[pack_name]["rule_count"] += 1
        rules.append({
            "id":      f"rule:{pack_name}-{rule.rule_id}",
            "label":   f"{pack_name} · {rule.rule_id}",
            "slug":    slug,
            "summary": rule.summary,
        })
    return list(packs.values()), rules


def load_seed_sources(include_user: bool = False):
    """Read all source data files. Returns a dict ready for the builders."""
    # Wardrobe (seed always, overlay optional)
    seed = _load_json(os.path.join(_ROOT, "wardrobe.json"), default={}) or {}
    overlay = (_load_json(os.path.join(_ROOT, "user_wardrobe.json"), default={})
                if include_user else None) or {}
    sections = ("clothing", "shoes", "accessories")
    items = []
    for s in sections:
        for it in (seed.get(s) or []):
            it = dict(it)
            it.setdefault("type", s.rstrip("s"))   # shoes -> shoe, accessories -> accessorie
            if s == "shoes":   it["type"] = "shoes"
            if s == "accessories": it["type"] = "accessory"
            items.append(it)
        if include_user:
            for it in (overlay.get(s) or []):
                it = dict(it)
                it.setdefault("type", s.rstrip("s"))
                if s == "shoes":   it["type"] = "shoes"
                if s == "accessories": it["type"] = "accessory"
                items.append(it)

    # Wear history: seed always
    seed_hist = _load_json(os.path.join(_ROOT, "seed_wear_history.json"),
                            default={}) or {}
    hist = dict(seed_hist.get("history", {}) or {})
    if include_user:
        usr_hist = _load_json(os.path.join(_ROOT, "wear_history.json"),
                              default={}) or {}
        hist.update((usr_hist.get("history") or {}))

    # Wishlist + favorite stores: seed has none committed; overlay only.
    wishlist = []
    fav_stores = []
    if include_user:
        wishlist = (_load_json(os.path.join(_ROOT, "wishlist.json"),
                                default={}) or {}).get("items", []) or []
        fs_blob = _load_json(os.path.join(_ROOT, "favorite_stores.json"),
                              default={}) or {}
        # favorite_stores.json shape can be {"stores": [...]} or just a list
        fav_stores = fs_blob.get("stores", fs_blob if isinstance(fs_blob, list) else []) or []

    # Color rules → skin tones
    color_rules = _load_json(os.path.join(_ROOT, "color_rules.json"), default={}) or {}
    skin_tones = list(color_rules.keys())

    # Occasion / piece tables
    sys.path.insert(0, _ROOT)
    from styling_agent import OCCASION_TAG_MAP, REQUIRED_PIECES  # type: ignore
    occasion_canonical = sorted(set(OCCASION_TAG_MAP.values()))

    # Item-type universe (from all items + the REQUIRED_PIECES table)
    item_types = sorted(set(
        list({it.get("type", "") for it in items if it.get("type")}) +
        [t for typeset in REQUIRED_PIECES.values() for t in typeset]
    ))

    return {
        "owner":              seed.get("owner") or {},
        "items":              items,
        "wear_history":       hist,
        "wishlist":           wishlist,
        "favorite_stores":    fav_stores,
        "skin_tones":         skin_tones,
        "color_rules":        color_rules,
        "occasion_canonical": occasion_canonical,
        "required_pieces":    REQUIRED_PIECES,
        "item_types":         item_types,
    }


# ─────────────────────────────────────────────
# Top-level
# ─────────────────────────────────────────────

def build(include_user: bool = False) -> Dict[str, Any]:
    src = load_seed_sources(include_user=include_user)
    rule_packs, rules = _load_rule_packs_and_rules()

    domain_nodes = build_domain_nodes(
        occasion_canonical=src["occasion_canonical"],
        skin_tones=src["skin_tones"],
        rule_packs=rule_packs,
        rules=rules,
        item_types=src["item_types"],
    )
    user_nodes = build_user_behavior_nodes(
        owner=src["owner"],
        wardrobe_items=src["items"],
        wear_history=src["wear_history"],
        wishlist_items=src["wishlist"],
        favorite_stores=src["favorite_stores"],
    )
    all_nodes = domain_nodes + user_nodes

    edges = build_edges(
        nodes=all_nodes,
        wardrobe_items=src["items"],
        wishlist_items=src["wishlist"],
        occasion_canonical=src["occasion_canonical"],
        required_pieces=src["required_pieces"],
        color_rules=src["color_rules"],
    )

    all_nodes = aggregate_weights(all_nodes, edges)

    # Sort for stable diffs across runs.
    all_nodes.sort(key=lambda n: (n["layer"], n["type"], n["id"]))

    return {
        "metadata": {
            "version":      "0.1.0",
            "name":         "Wearly Knowledge Graph",
            "description":  ("Three-layer structured-knowledge graph "
                             "modeling Wearly's domain rules, user "
                             "behavior, and runtime archetypes. "
                             "Distinct from the Learning Graph "
                             "(reader concepts) and the Reasoning "
                             "Graph (one-recommendation explanation)."),
            "node_count":   len(all_nodes),
            "edge_count":   len(edges),
            "layers":       ["domain", "user_behavior", "runtime"],
            "generated_from": [
                "wardrobe.json", "seed_wear_history.json",
                "color_rules.json", "rule_refs.py", "styling_agent",
            ] + (["user_wardrobe.json", "wear_history.json",
                   "wishlist.json", "favorite_stores.json"]
                  if include_user else []),
            "generated_at": _now_iso(),
            "source_mode":  "user_overlay" if include_user else "public_seed",
            "rendered_by":  "vis-network.js",
        },
        "node_types": [
            {"id": t, "category": _style_category_for(t),
             "shape": s["shape"], "color": s["color"],
             "border": s["border"], "base_size": s["size"],
             **({"font_color": s["font_color"]} if "font_color" in s else {})}
            for t, s in NODE_TYPE_STYLES.items()
        ],
        "edge_types": EDGE_TYPES,
        "nodes":      all_nodes,
        "edges":      edges,
    }


def _style_category_for(node_type: str) -> str:
    if node_type in ("WardrobeItem", "WishlistItem", "FavoriteStore"):
        return "user_behavior"
    if node_type in ("OutfitRecommendation", "WardrobeGap",
                     "ShoppingSuggestion", "Feedback", "WorkflowStep"):
        return "runtime"
    return "domain"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--include-user", action="store_true",
                    help="Also read the gitignored user overlay files "
                         "(local-only; never used for the committed JSON).")
    ap.add_argument("--output",
                    default=os.path.join(_ROOT, "graph",
                                          "wearly-knowledge-graph.json"),
                    help="Output path (default: graph/wearly-knowledge-graph.json)")
    args = ap.parse_args()

    graph = build(include_user=args.include_user)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
        f.write("\n")

    md = graph["metadata"]
    print(f"Wrote {args.output}")
    print(f"  source_mode: {md['source_mode']}")
    print(f"  nodes:       {md['node_count']}")
    print(f"  edges:       {md['edge_count']}")
    print(f"  layers:      {md['layers']}")
    if args.include_user:
        print("  ⚠ user overlay included — DO NOT commit this output.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
