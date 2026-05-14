"""
Tests for graph_tool.py — schema graph + live-run reasoning graph.

These are render-smoke tests: HTML is generated, key markers appear,
no exceptions raised on edge-case inputs. We deliberately do NOT
inspect the generated vis-network JavaScript internals — pyvis owns
that contract, not Wearly.

Run with:
    python -m unittest tests.test_graph_tool
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Skip the entire module if pyvis isn't installed in this environment.
# This is the right call on CI and on Streamlit Cloud (where pyvis IS
# installed via requirements.txt), and lets the local dev experience
# stay graceful if someone runs the suite before installing deps.
try:
    import pyvis  # noqa: F401
    _PYVIS_AVAILABLE = True
except ImportError:
    _PYVIS_AVAILABLE = False


@unittest.skipUnless(_PYVIS_AVAILABLE, "pyvis not installed")
class TestSchemaGraph(unittest.TestCase):

    def test_renders_html(self):
        from graph_tool import render_schema_graph_html
        html = render_schema_graph_html()
        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 1000, "HTML should be substantial")

    def test_contains_visnetwork(self):
        from graph_tool import render_schema_graph_html
        html = render_schema_graph_html()
        # pyvis bundles vis-network inline when cdn_resources='in_line'.
        self.assertIn("vis-network", html.lower(),
                      "HTML should bundle vis-network.js inline")

    def test_includes_core_entity_types(self):
        from graph_tool import render_schema_graph_html
        html = render_schema_graph_html()
        # Sample of entity labels we know are in graph.json.
        for label in ("Eatedal", "OutfitRecommendation",
                      "Team Strategy Meeting", "Minneapolis"):
            self.assertIn(label, html,
                          f"Schema graph should mention '{label}' from graph.json")

    def test_summary_counts(self):
        from graph_tool import schema_graph_summary
        s = schema_graph_summary()
        # The committed graph.json has 16 entities + 39 edges.
        self.assertGreaterEqual(s["entities"], 10)
        self.assertGreaterEqual(s["edges"], 20)


@unittest.skipUnless(_PYVIS_AVAILABLE, "pyvis not installed")
class TestRunGraph(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Snapshot + reset wear history so this test class isn't flaky
        # against developer exploration (same pattern as test_fit_profile).
        try:
            from history_tool import HISTORY_PATH
            cls._history_path = HISTORY_PATH
            cls._history_original = None
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                    cls._history_original = f.read()
            with open(HISTORY_PATH, "w", encoding="utf-8") as f:
                import json as _json
                _json.dump({"history": {}}, f)
        except Exception:
            cls._history_path = None
            cls._history_original = None

    @classmethod
    def tearDownClass(cls):
        if cls._history_path and cls._history_original is not None:
            with open(cls._history_path, "w", encoding="utf-8") as f:
                f.write(cls._history_original)

    def _agent_result(self):
        from styling_agent import run_agent
        return run_agent(mode="everyday", everyday_request="work")

    def test_renders_html_from_real_result(self):
        from graph_tool import render_run_graph_html
        html = render_run_graph_html(self._agent_result())
        self.assertIsInstance(html, str)
        self.assertIn("vis-network", html.lower())
        self.assertGreater(len(html), 1000)

    def test_includes_user_and_outfit_nodes(self):
        from graph_tool import render_run_graph_html
        html = render_run_graph_html(self._agent_result())
        # The User node is labelled with the owner's name.
        self.assertIn("Eatedal", html)
        # The Outfit centerpiece carries piece count.
        self.assertIn("Outfit", html)

    def test_includes_actual_item_names(self):
        from graph_tool import render_run_graph_html
        result = self._agent_result()
        html = render_run_graph_html(result)
        # At least one of the recommended item names should appear in
        # the rendered HTML.
        names = [i.get("name", "") for i in result.get("recommendation", [])]
        self.assertTrue(
            any(n and n in html for n in names),
            f"None of the recommended items showed up in the graph: {names}",
        )

    def test_summary_matches_result_shape(self):
        from graph_tool import run_graph_summary
        result = self._agent_result()
        s = run_graph_summary(result)
        self.assertEqual(s["items"], len(result.get("recommendation", [])))
        self.assertEqual(s["gaps"], len(result.get("gaps", [])))

    def test_empty_result_renders_cleanly(self):
        from graph_tool import render_run_graph_html
        html = render_run_graph_html({})
        self.assertIsInstance(html, str)
        self.assertIn("vis-network", html.lower())

    def test_none_input_does_not_crash(self):
        from graph_tool import render_run_graph_html
        html = render_run_graph_html(None)
        self.assertIsInstance(html, str)
        # No raise; renders a friendly message.

    def test_result_with_gaps_renders_gap_nodes(self):
        from graph_tool import render_run_graph_html
        from styling_agent import run_agent
        # Gym occasion in cool weather → outerwear gap path. Mock the
        # weather so this test is deterministic.
        from unittest import mock
        cold = {
            "success": True, "error": None,
            "weather": {"city": "Test", "temp_f": 50, "feels_like_f": 47,
                        "condition": "Partly Cloudy", "wind_mph": 6,
                        "precip_chance_pct": 10, "layer_advice": "Light jacket."},
        }
        with mock.patch("styling_agent.get_weather", return_value=cold):
            r = run_agent(mode="everyday", everyday_request="gym")
        html = render_run_graph_html(r)
        self.assertIn("outerwear", html.lower())

    def test_result_with_rejection_renders_feedback_node(self):
        from graph_tool import render_run_graph_html
        from styling_agent import run_agent
        baseline = run_agent(mode="everyday", everyday_request="work")
        first = baseline["recommendation"][0]
        regen = run_agent(
            mode="everyday", everyday_request="work",
            rejected_ids=[first["id"]],
            rejection_reasons=[{
                "item_id": first["id"],
                "item_name": first["name"],
                "reason": "Wore it recently",
            }],
        )
        html = render_run_graph_html(regen)
        self.assertIn("Wore it recently", html)


@unittest.skipIf(not _PYVIS_AVAILABLE, "pyvis not installed")
class TestFreezeAfterStabilization(unittest.TestCase):
    """The rendered HTML must include the freeze-after-stabilization
    snippet so the graph stops animating once layout settles."""

    def test_run_graph_includes_freeze_snippet(self):
        from styling_agent import run_agent
        from graph_tool import render_run_graph_html
        r = run_agent(mode="everyday", everyday_request="casual")
        html = render_run_graph_html(r)
        self.assertIn("wearly:freeze-after-stabilize", html,
            "Run graph must inject the freeze-after-stabilization snippet")
        self.assertIn("stabilizationIterationsDone", html,
            "Snippet must listen for the vis.js stabilization event")
        self.assertIn("physics: {enabled: false}", html,
            "Snippet must disable physics on stabilization")

    def test_run_graph_includes_fit_to_view_call(self):
        """After freeze, the snippet must center+fit nodes so the graph
        opens visibly inside the canvas rather than cropped."""
        from styling_agent import run_agent
        from graph_tool import render_run_graph_html
        r = run_agent(mode="everyday", everyday_request="casual")
        html = render_run_graph_html(r)
        self.assertIn("network.fit", html,
            "Snippet must call network.fit() to center the graph")
        self.assertIn("afterDrawing", html,
            "Snippet must also fit on first draw for layout consistency")


if __name__ == "__main__":
    unittest.main(verbosity=2)
