"""
Tests for the canonical rule-citation registry (rule_refs.py).

The registry exists to make the chain
    evidence category -> rule pack -> rule ID -> reasoning line
verifiable end-to-end. These tests guard the two failure modes:

1. A slug points at a rule that does not exist in the Skill files
   (rename / renumber drift).
2. The agent's reasoning trail loses all rule citations
   (regression where the cite() wrapper silently degrades).

Run with:
    python -m unittest tests.test_rule_refs
"""

import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import rule_refs  # noqa: E402  (path setup above)


_SKILL_DIR = os.path.join(_ROOT, "skills", "wearly-styling-agent")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestRegistryStructure(unittest.TestCase):
    """Static shape of the registry."""

    def test_registry_non_empty(self):
        self.assertGreater(len(rule_refs.RULES), 0,
                           "rule_refs.RULES must declare at least one rule.")

    def test_every_slug_well_formed(self):
        """Slugs follow the form '<pack>#R<N>'."""
        bad = [s for s in rule_refs.RULES
               if not re.match(r"^[a-z]+#R\d+$", s)]
        self.assertEqual(bad, [],
                         f"Malformed slug(s) in rule_refs.RULES: {bad}")

    def test_every_rule_summary_is_body_positive(self):
        """Registry summaries themselves must not contain forbidden tokens.

        Wearly's body-positive language contract applies to anything
        the agent might surface — including hover-text from this
        registry. The forbidden set is sourced from fit_tool so this
        test cannot drift out of sync with the runtime check.
        """
        from fit_tool import FORBIDDEN_TOKENS
        offenders = []
        for slug, rule in rule_refs.RULES.items():
            text = rule.summary.lower()
            hit = {tok for tok in FORBIDDEN_TOKENS if tok in text}
            if hit:
                offenders.append((slug, hit))
        self.assertEqual(offenders, [],
                         f"Registry summaries contain forbidden tokens: {offenders}")


class TestSlugsResolveToSkillRules(unittest.TestCase):
    """Every slug points to a real `## R<N>` heading in its skill file."""

    def test_each_slug_resolves(self):
        missing = []
        for slug, rule in rule_refs.RULES.items():
            path = os.path.join(_SKILL_DIR, rule.skill_file)
            if not os.path.exists(path):
                missing.append(f"{slug} -> {rule.skill_file} (file missing)")
                continue
            text = _read(path)
            # Heading form in the skill files: "## R3 — <title>" or
            # "## R3 - <title>". Match the rule_id at a heading boundary.
            pat = rf"^##\s+{re.escape(rule.rule_id)}(?:\s|$|—|-)"
            if not re.search(pat, text, re.MULTILINE):
                missing.append(f"{slug} -> {rule.skill_file} (heading '{rule.rule_id}' not found)")
        self.assertEqual(missing, [],
                         "rule_refs.RULES entries that no longer resolve:\n"
                         + "\n".join("  - " + m for m in missing))


class TestCiteHelper(unittest.TestCase):
    """The cite() helper formats tags consistently and never crashes."""

    def test_known_slug_returns_bracketed_tag(self):
        tag = rule_refs.cite("occasion#R3")
        self.assertEqual(tag, "[occasion-rules#R3]")

    def test_unknown_slug_returns_empty_string(self):
        # cite() must be silent on misses — citations are advisory.
        self.assertEqual(rule_refs.cite("does-not-exist#R99"), "")
        self.assertEqual(rule_refs.cite(""), "")

    def test_is_valid_slug(self):
        self.assertTrue(rule_refs.is_valid_slug("occasion#R3"))
        self.assertFalse(rule_refs.is_valid_slug("nope#R1"))


class TestAgentReasoningCitesRules(unittest.TestCase):
    """The runtime contract: the agent's reasoning trail cites at least
    one rule for every default occasion. Without this, the registry is
    a documentation exercise rather than a runtime source of truth."""

    @classmethod
    def setUpClass(cls):
        # Snapshot wear_history.json so the smoke run is deterministic.
        from history_tool import HISTORY_PATH
        cls._history_path = HISTORY_PATH
        cls._history_backup = None
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                cls._history_backup = f.read()
        import json
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"history": {}}, f)

    @classmethod
    def tearDownClass(cls):
        if cls._history_backup is not None:
            with open(cls._history_path, "w", encoding="utf-8") as f:
                f.write(cls._history_backup)

    def test_reasoning_trail_contains_at_least_one_citation(self):
        from styling_agent import run_agent

        citation_re = re.compile(r"\[[a-z-]+#R\d+\]")
        offenders = []
        for occasion in ("work", "dinner", "gym", "casual"):
            result = run_agent(mode="everyday", everyday_request=occasion)
            joined = " | ".join(result.get("reasoning", []))
            if not citation_re.search(joined):
                offenders.append((occasion, joined))
        self.assertEqual(
            offenders, [],
            "Reasoning trail produced no rule citations for occasion(s):\n"
            + "\n".join(f"  - {o[0]}: {o[1][:200]}..." for o in offenders),
        )


if __name__ == "__main__":
    unittest.main()
