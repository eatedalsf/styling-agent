"""
Tool 3: Wardrobe Reader
Reads wardrobe inventory and filters items by formality, season, and occasion tags.
"""

import json
import os


def _find_data_file(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "data", filename),
        os.path.join(here, "..", filename),
        os.path.join(here, filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


DATA_PATH = _find_data_file("wardrobe.json")


def get_wardrobe() -> dict:
    try:
        with open(DATA_PATH, "r") as f:
            return {"success": True, "wardrobe": json.load(f), "error": None}
    except FileNotFoundError:
        return {"success": False, "wardrobe": None, "error": "Wardrobe data file not found."}
    except json.JSONDecodeError:
        return {"success": False, "wardrobe": None, "error": "Wardrobe data is malformed."}


def get_owner_profile() -> dict:
    result = get_wardrobe()
    if not result["success"]:
        return result
    return {"success": True, "profile": result["wardrobe"]["owner"], "error": None}


def filter_items_by_occasion(occasion_tag: str, season: str = "all") -> dict:
    result = get_wardrobe()
    if not result["success"]:
        return result

    wardrobe = result["wardrobe"]
    tag = occasion_tag.lower()

    def matches(item):
        item_tags = [t.lower() for t in item.get("tags", [])]
        item_seasons = [s.lower() for s in item.get("season", ["all"])]
        tag_match = tag in item_tags or any(tag in t for t in item_tags)
        season_match = "all" in item_seasons or season.lower() in item_seasons or season == "all"
        return tag_match and season_match

    clothing = [i for i in wardrobe.get("clothing", []) if matches(i)]
    shoes = [i for i in wardrobe.get("shoes", []) if matches(i)]
    accessories = [i for i in wardrobe.get("accessories", []) if matches(i)]

    if not clothing:
        clothing = [i for i in wardrobe.get("clothing", []) if tag in [t.lower() for t in i.get("tags", [])]]

    return {
        "success": True,
        "error": None,
        "clothing": clothing,
        "shoes": shoes,
        "accessories": accessories,
        "occasion_tag": occasion_tag
    }


def check_gaps(outfit_pieces: list, required_types: list) -> list:
    covered = {piece.get("type", "").lower() for piece in outfit_pieces}
    missing = [t for t in required_types if t.lower() not in covered]
    return missing
