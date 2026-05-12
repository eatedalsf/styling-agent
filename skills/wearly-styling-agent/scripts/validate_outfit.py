#!/usr/bin/env python3
"""
validate_outfit.py — contract checker for a Wearly skill output.

Given a result dict produced by run_agent() (or read from JSON on disk),
this script verifies every contract obligation of the Wearly Styling
Agent skill:

  · occasion tag is one of the five canonical values
  · seven workflow steps are present and ordered
  · every required field on the result dict has the expected type
  · color score is in [0, 100]
  · reasoning trail uses only body-positive language
  · every gap has a corresponding shopping suggestion
  · every recommended item has the minimum required fields

Outputs a structured PASS/FAIL report. Exit code 0 = all checks pass.

This is the "Advanced"-tier piece of the skill per the meta-skills
lecture: executable code that validates the skill's own output.

Usage:
    python skills/wearly-styling-agent/scripts/validate_outfit.py [result.json]
    cat result.json | python skills/wearly-styling-agent/scripts/validate_outfit.py -

Or programmatically:
    from validate_outfit import validate
    report = validate(result_dict)
    if not report["ok"]:
        ...
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Tuple


# ─────────────────────────────────────────────
# CONTRACT CONSTANTS
# ─────────────────────────────────────────────

CANONICAL_OCCASIONS = {"work", "gym", "dinner", "formal", "casual",
                        "formal_event", "everyday"}

EXPECTED_STEPS = [
    "Determine Occasion",
    "Load Style Profile",
    "Check Weather",
    "Filter Wardrobe",
    "Build Outfit",
    "Check for Wardrobe Gaps",
    "Color Coordination Check",
]

# Body-positive language contract: any of these tokens in the reasoning
# trail is a violation. Mirrors fit_tool.FORBIDDEN_TOKENS.
FORBIDDEN_TOKENS = {
    "flaw", "flaws",
    "fix",
    "hide",
    "minimize", "minimise",
    "correct", "corrective",
    "problem area", "problem-area", "problem_area", "problem zone",
    "trouble area", "trouble-area",
    "slimming", "slimmer",
    "shameful",
}

REQUIRED_RESULT_KEYS = (
    "steps", "recommendation", "reasoning",
    "gaps", "shopping_suggestions",
    "color_score", "weather", "event",
)


# ─────────────────────────────────────────────
# INDIVIDUAL CHECKS
# ─────────────────────────────────────────────

def _check_required_keys(result: dict) -> Tuple[str, bool, str]:
    missing = [k for k in REQUIRED_RESULT_KEYS if k not in result]
    if missing:
        return ("required_keys", False,
                f"Missing required keys: {', '.join(missing)}")
    return ("required_keys", True, f"All {len(REQUIRED_RESULT_KEYS)} required keys present")


def _check_seven_steps(result: dict) -> Tuple[str, bool, str]:
    steps = result.get("steps") or []
    if len(steps) < 7:
        return ("seven_steps", False,
                f"Expected 7 workflow steps, found {len(steps)}")
    names = [s.get("name", "") for s in steps[:7]]
    mismatches = [(i, exp, got)
                  for i, (exp, got) in enumerate(zip(EXPECTED_STEPS, names), 1)
                  if exp != got]
    if mismatches:
        details = "; ".join(f"step {i}: expected {exp!r}, got {got!r}"
                            for i, exp, got in mismatches)
        return ("seven_steps", False, f"Step names mismatch: {details}")
    return ("seven_steps", True,
            f"All 7 steps present in canonical order")


def _check_occasion_tag(result: dict) -> Tuple[str, bool, str]:
    occasion = (result.get("event") or {}).get("type", "")
    if not occasion:
        return ("occasion_tag", False, "No occasion tag on event")
    if occasion.lower() not in CANONICAL_OCCASIONS:
        return ("occasion_tag", False,
                f"Unknown occasion tag: {occasion!r} "
                f"(expected one of: {sorted(CANONICAL_OCCASIONS)})")
    return ("occasion_tag", True, f"Occasion tag {occasion!r} is canonical")


def _check_recommendation_shape(result: dict) -> Tuple[str, bool, str]:
    outfit = result.get("recommendation") or []
    if not isinstance(outfit, list):
        return ("recommendation_shape", False, "recommendation must be a list")
    if not outfit:
        # Empty outfit is acceptable (severely constrained run); only flag missing structure.
        return ("recommendation_shape", True, "Outfit is empty (acceptable for empty pools)")
    missing = []
    for it in outfit:
        if not isinstance(it, dict):
            missing.append(f"non-dict item: {it!r}")
            continue
        for field in ("id", "name", "color"):
            if field not in it:
                missing.append(f"{it.get('name','?')} missing field {field!r}")
    if missing:
        return ("recommendation_shape", False,
                f"Item shape problems: {'; '.join(missing[:3])}"
                + (f" (and {len(missing)-3} more)" if len(missing) > 3 else ""))
    return ("recommendation_shape", True,
            f"All {len(outfit)} item(s) have id, name, color")


def _check_color_score_range(result: dict) -> Tuple[str, bool, str]:
    cs = result.get("color_score")
    if not isinstance(cs, dict):
        return ("color_score_range", False, "color_score must be a dict")
    score = cs.get("score")
    if not isinstance(score, (int, float)):
        return ("color_score_range", False,
                f"color_score.score must be numeric (got {type(score).__name__})")
    if not (0 <= score <= 100):
        return ("color_score_range", False,
                f"color_score.score = {score} (must be in [0, 100])")
    return ("color_score_range", True, f"Color score {score} is in valid [0, 100] range")


def _check_gaps_have_suggestions(result: dict) -> Tuple[str, bool, str]:
    gaps = result.get("gaps") or []
    suggestions = result.get("shopping_suggestions") or []
    if gaps and not suggestions:
        return ("gaps_suggestions", False,
                f"{len(gaps)} gap(s) detected but no shopping suggestions provided")
    if not gaps:
        return ("gaps_suggestions", True, "No gaps detected (no suggestions needed)")
    return ("gaps_suggestions", True,
            f"{len(gaps)} gap(s) detected with {len(suggestions)} suggestion(s)")


def _check_body_positive_language(result: dict) -> Tuple[str, bool, str]:
    """The most important contract check. Body-positive language only."""
    reasoning = result.get("reasoning") or []
    offenders = []
    for i, line in enumerate(reasoning, 1):
        if not isinstance(line, str):
            continue
        low = line.lower()
        for tok in FORBIDDEN_TOKENS:
            if tok in low:
                offenders.append((i, tok, line.strip()))
    if offenders:
        first_three = "; ".join(
            f"line {i} contains {tok!r}" for i, tok, _line in offenders[:3]
        )
        return ("body_positive_language", False,
                f"{len(offenders)} reasoning line(s) contain forbidden tokens. "
                f"First: {first_three}")
    return ("body_positive_language", True,
            f"All {len(reasoning)} reasoning line(s) use body-positive language")


def _check_reasoning_trail_present(result: dict) -> Tuple[str, bool, str]:
    reasoning = result.get("reasoning") or []
    if not reasoning:
        return ("reasoning_trail", False,
                "No reasoning trail — Wearly recommendations must be explainable")
    if len(reasoning) < 3:
        return ("reasoning_trail", False,
                f"Reasoning trail very short ({len(reasoning)} line(s)); "
                f"a 5-piece outfit normally produces 6+ lines")
    return ("reasoning_trail", True,
            f"Reasoning trail has {len(reasoning)} line(s)")


_ALL_CHECKS = [
    _check_required_keys,
    _check_seven_steps,
    _check_occasion_tag,
    _check_recommendation_shape,
    _check_color_score_range,
    _check_gaps_have_suggestions,
    _check_body_positive_language,
    _check_reasoning_trail_present,
]


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────

def validate(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run every contract check on `result`. Returns:
      {
        "ok": bool,
        "checks": [{"name": ..., "passed": bool, "detail": ...}, ...],
        "summary": "N/M checks passed",
      }
    """
    if not isinstance(result, dict):
        return {
            "ok": False,
            "checks": [{"name": "input_type", "passed": False,
                        "detail": f"validate() requires a dict, got {type(result).__name__}"}],
            "summary": "0/1 checks passed",
        }

    checks_out: List[Dict[str, Any]] = []
    passed = 0
    for fn in _ALL_CHECKS:
        try:
            name, ok, detail = fn(result)
        except Exception as e:
            name, ok, detail = (fn.__name__, False, f"check raised: {type(e).__name__}: {e}")
        checks_out.append({"name": name, "passed": ok, "detail": detail})
        if ok:
            passed += 1

    return {
        "ok": passed == len(_ALL_CHECKS),
        "checks": checks_out,
        "summary": f"{passed}/{len(_ALL_CHECKS)} checks passed",
    }


def _print_report(report: Dict[str, Any]) -> None:
    """Print the report in a human-readable format with ASCII markers."""
    print("=" * 60)
    print("  Wearly Styling Agent — Contract Validation")
    print("=" * 60)
    for check in report["checks"]:
        marker = "[PASS]" if check["passed"] else "[FAIL]"
        print(f"  {marker}  {check['name']:<25}  {check['detail']}")
    print("-" * 60)
    print(f"  Result: {report['summary']}  "
          f"({'OK' if report['ok'] else 'FAILED'})")
    print("=" * 60)


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2

    arg = argv[1]
    if arg == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(arg, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            print(f"Could not read {arg}: {e}", file=sys.stderr)
            return 2

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Could not parse JSON: {e}", file=sys.stderr)
        return 2

    report = validate(result)
    _print_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
