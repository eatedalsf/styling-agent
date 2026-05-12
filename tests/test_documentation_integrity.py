"""
Documentation integrity tests for the evidence-and-references pass.

Verifies the references infrastructure stays coherent across the
codebase: the canonical doc exists, the Intelligent Book chapter
exists and is linked from the index, every Skill rule pack carries
a "Source basis" footer, and the body-positive language contract is
enforced against the agent's reasoning trail (which is the runtime
contract — documentation discussing the forbidden tokens is fine
and expected).

Run with:
    python -m unittest tests.test_documentation_integrity
"""

import os
import re
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


_SKILL_RULE_FILES = [
    "occasion-rules.md",
    "weather-rules.md",
    "fit-silhouette-rules.md",
    "wardrobe-filtering-rules.md",
    "color-coordination-rules.md",
    "wear-history-rules.md",
    "shopping-gap-rules.md",
    "privacy-guidelines.md",
]


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestEvidenceDocumentExists(unittest.TestCase):
    """The canonical references document and its book chapter exist."""

    def test_canonical_references_doc_exists(self):
        path = os.path.join(_ROOT, "docs", "evidence-and-references.md")
        self.assertTrue(os.path.exists(path),
                        f"Canonical references doc missing: {path}")

    def test_book_chapter_12_exists(self):
        path = os.path.join(_ROOT, "book", "12-evidence-and-references.md")
        self.assertTrue(os.path.exists(path),
                        f"Book chapter 12 missing: {path}")

    def test_book_index_references_chapter_12(self):
        index = _read(os.path.join(_ROOT, "book", "index.md"))
        self.assertIn("12-evidence-and-references.md", index,
                      "book/index.md should reference chapter 12.")
        self.assertIn("Evidence and references", index,
                      "book/index.md should name the chapter.")


class TestSkillRulePacksHaveSourceBasis(unittest.TestCase):
    """Every Skill rule pack ends with a 'Source basis' footer that
    points to the canonical references document."""

    def test_each_rule_pack_has_source_basis_section(self):
        skills_dir = os.path.join(_ROOT, "skills", "wearly-styling-agent")
        missing = []
        for fname in _SKILL_RULE_FILES:
            path = os.path.join(skills_dir, fname)
            if not os.path.exists(path):
                missing.append(f"{fname} (file missing)")
                continue
            text = _read(path)
            if "## Source basis" not in text:
                missing.append(f"{fname} (no '## Source basis' section)")
        self.assertEqual(missing, [],
                         "Skill rule packs missing Source basis footers:\n" +
                         "\n".join("  - " + m for m in missing))

    def test_each_rule_pack_references_evidence_doc(self):
        skills_dir = os.path.join(_ROOT, "skills", "wearly-styling-agent")
        missing = []
        for fname in _SKILL_RULE_FILES:
            path = os.path.join(skills_dir, fname)
            if not os.path.exists(path):
                continue
            text = _read(path)
            if "evidence-and-references.md" not in text:
                missing.append(fname)
        self.assertEqual(missing, [],
                         "Skill rule packs not linking to the canonical "
                         "references doc:\n" +
                         "\n".join("  - " + m for m in missing))


class TestCanonicalDocStructure(unittest.TestCase):
    """The canonical references doc has all nine source categories
    documented and a verification status section."""

    @classmethod
    def setUpClass(cls):
        cls._text = _read(os.path.join(_ROOT, "docs", "evidence-and-references.md"))

    def test_has_all_nine_categories(self):
        category_headers = [
            "3.1 Fashion recommender systems",
            "3.2 Outfit compatibility",
            "3.3 Color harmony",
            "3.4 Body-shape-aware",
            "3.5 Explainable recommendation",
            "3.6 Human-centered AI",
            "3.7 Wardrobe management",
            "3.8 Personalization and user feedback",
            "3.9 Privacy and personal data",
        ]
        missing = [h for h in category_headers if h not in self._text]
        self.assertEqual(missing, [],
                         f"Canonical doc missing category headers: {missing}")

    def test_has_verification_status_section(self):
        self.assertIn("Verification status", self._text)
        self.assertIn("[to verify]", self._text,
                      "Doc should explicitly mark pending items as [to verify].")

    def test_has_honesty_contract_section(self):
        self.assertIn("honesty contract", self._text.lower())
        # Each of the four contract rules should appear in some form.
        self.assertIn("not an exact science", self._text.lower())
        self.assertIn("body-positive", self._text.lower())
        # Don't lock in exact phrasing of remaining rules.

    def test_has_body_shape_framing_section(self):
        # Section 4 in the doc explicitly frames body-shape categories
        # as industry heuristic, not scientific taxonomy.
        self.assertIn("industry heuristic", self._text.lower())
        self.assertIn("scientific taxonomy", self._text.lower())


class TestAgentReasoningStaysBodyPositive(unittest.TestCase):
    """Runtime contract: the agent's reasoning output never contains
    forbidden body-language tokens. This is the contract that actually
    affects users (documentation discussing the forbidden tokens is
    fine and expected)."""

    def test_default_run_reasoning_is_clean(self):
        from fit_tool import check_reasoning_for_forbidden_language
        from styling_agent import run_agent

        # Save & restore wear_history.json so this test isn't flaky
        # against developer exploration. Match the pattern used in
        # test_fit_profile.py's _ProfileSnapshotMixin.
        from history_tool import HISTORY_PATH
        original = None
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                original = f.read()
        try:
            import json
            with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                json.dump({"history": {}}, f)

            for occasion in ("work", "dinner", "gym", "casual"):
                result = run_agent(mode="everyday", everyday_request=occasion)
                offenders = check_reasoning_for_forbidden_language(
                    result.get("reasoning", []))
                self.assertEqual(
                    offenders, set(),
                    f"Agent reasoning for '{occasion}' contains forbidden "
                    f"body-language tokens: {offenders}\n"
                    f"Trail: {result.get('reasoning')}",
                )
        finally:
            if original is not None:
                with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                    f.write(original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
