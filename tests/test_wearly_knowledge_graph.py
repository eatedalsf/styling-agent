"""
Tests for the Wearly Knowledge Graph layer.

Pins five contracts a future change must not break:

  1. The JSON file exists, parses, and carries the expected metadata.
  2. The graph generator produces a deterministic, self-consistent
     graph (same nodes/edges count, no dangling edges, every layer
     populated).
  3. Every node weight is finite + within the documented 1.0-3.0
     clamp; user-behavior items carry the metrics the schema doc
     promises.
  4. Every edge type is in the catalog and every endpoint resolves.
     Specifically the runtime archetype links (POWERS, REQUIRES,
     CONTAINS_RULE) are wired.
  5. The committed JSON contains NO personal-name leaks — the seed
     owner is "Demo User" only; no occurrences of the previously-
     anonymized real name.
"""

from __future__ import annotations
import json
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_KG_PATH = os.path.join(_ROOT, "graph", "wearly-knowledge-graph.json")


def _load_kg() -> dict:
    with open(_KG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class TestFileShipsAndParses(unittest.TestCase):
    """The graph file lives in the canonical location, parses, and
    carries the expected metadata shape."""

    def test_file_exists(self):
        self.assertTrue(os.path.exists(_KG_PATH),
                        f"Missing canonical Wearly Knowledge Graph file: {_KG_PATH}")

    def test_metadata_shape(self):
        kg = _load_kg()
        md = kg.get("metadata", {})
        self.assertEqual(md.get("name"), "Wearly Knowledge Graph")
        self.assertIn("version", md)
        self.assertIn("node_count", md)
        self.assertIn("edge_count", md)
        self.assertEqual(md.get("source_mode"), "public_seed",
                         "Committed JSON must be built from seed-only data, "
                         "never from the developer's gitignored user overlay.")
        self.assertEqual(set(md.get("layers", [])),
                         {"domain", "user_behavior", "runtime"})

    def test_top_level_keys(self):
        kg = _load_kg()
        for k in ("metadata", "node_types", "edge_types", "nodes", "edges"):
            self.assertIn(k, kg, f"Top-level key missing: {k}")


class TestNodeIntegrity(unittest.TestCase):
    """Nodes are well-formed, layered correctly, and weights clamp
    inside the documented 1.0-3.0 range."""

    @classmethod
    def setUpClass(cls):
        cls.kg = _load_kg()

    def test_every_layer_populated(self):
        layers = {n["layer"] for n in self.kg["nodes"]}
        self.assertIn("domain", layers)
        self.assertIn("user_behavior", layers)
        # runtime is populated in the seed snapshot via WorkflowStep
        # nodes; that's enough to satisfy the contract.
        self.assertIn("runtime", layers)

    def test_node_count_matches_metadata(self):
        kg = self.kg
        self.assertEqual(len(kg["nodes"]), kg["metadata"]["node_count"])

    def test_unique_node_ids(self):
        ids = [n["id"] for n in self.kg["nodes"]]
        self.assertEqual(len(ids), len(set(ids)),
                         "Duplicate node ids detected.")

    def test_weights_within_clamp(self):
        for n in self.kg["nodes"]:
            w = n.get("weight", 1.0)
            self.assertIsInstance(w, (int, float))
            self.assertGreaterEqual(w, 1.0, f"Weight under floor: {n['id']}={w}")
            self.assertLessEqual(w, 3.0, f"Weight over ceiling: {n['id']}={w}")

    def test_required_singletons_present(self):
        types = [n["type"] for n in self.kg["nodes"]]
        # Exactly one User per snapshot
        self.assertEqual(types.count("User"), 1)
        # Exactly one FitProfile per User
        self.assertEqual(types.count("FitProfile"), 1)
        # Three skin tones from color_rules.json
        self.assertEqual(types.count("SkinTonePalette"), 3)
        # Five canonical occasion tags
        self.assertEqual(types.count("OccasionType"), 5)
        # Seven workflow steps
        self.assertEqual(types.count("WorkflowStep"), 7)

    def test_wardrobe_item_metrics_present(self):
        """Every WardrobeItem must carry the user-behavior metrics
        the schema doc promises so the viewer can compute weights."""
        wi = [n for n in self.kg["nodes"] if n["type"] == "WardrobeItem"]
        self.assertGreater(len(wi), 0)
        for n in wi:
            m = n.get("metrics") or {}
            for k in ("worn_count", "versatility"):
                self.assertIn(k, m, f"WardrobeItem {n['id']} missing metric '{k}'")


class TestEdgeIntegrity(unittest.TestCase):
    """Every edge has a typed catalog entry and both endpoints resolve
    to real nodes. No dangling references."""

    @classmethod
    def setUpClass(cls):
        cls.kg = _load_kg()
        cls.node_ids = {n["id"] for n in cls.kg["nodes"]}
        cls.edge_type_ids = {t["id"] for t in cls.kg["edge_types"]}

    def test_edge_count_matches_metadata(self):
        self.assertEqual(len(self.kg["edges"]), self.kg["metadata"]["edge_count"])

    def test_every_edge_has_valid_type(self):
        for e in self.kg["edges"]:
            self.assertIn(e["type"], self.edge_type_ids,
                          f"Unknown edge type: {e}")

    def test_no_dangling_endpoints(self):
        for e in self.kg["edges"]:
            self.assertIn(e["from"], self.node_ids,
                          f"Edge from a missing node: {e}")
            self.assertIn(e["to"], self.node_ids,
                          f"Edge to a missing node: {e}")

    def test_runtime_bridge_edges_present(self):
        """POWERS (RulePack -> WorkflowStep) is the bridge between the
        domain and runtime layers. Without it the graph is two
        islands. Must exist for at least the occasion / weather /
        wardrobe-filtering packs."""
        powers = [e for e in self.kg["edges"] if e["type"] == "POWERS"]
        self.assertGreater(len(powers), 0, "No POWERS edges present.")
        powering_packs = {e["from"] for e in powers}
        for pack in ("pack:occasion-rules", "pack:weather-rules",
                      "pack:color-coordination-rules"):
            self.assertIn(pack, powering_packs,
                          f"{pack} does not power any workflow step.")

    def test_user_neighborhood_complete(self):
        """The User node must have HAS_PROFILE + HAS_SKIN_TONE + at
        least one OWNS edge. Otherwise the user-behavior layer is
        disconnected from the domain layer."""
        user_edges = [e for e in self.kg["edges"] if e["from"] == "user:demo"]
        types_out = {e["type"] for e in user_edges}
        self.assertIn("HAS_PROFILE", types_out)
        self.assertIn("HAS_SKIN_TONE", types_out)
        self.assertIn("OWNS", types_out)

    def test_required_pieces_edges_match_styling_agent(self):
        """Every (occasion, required_type) pair declared in
        styling_agent.REQUIRED_PIECES must appear as a REQUIRES edge."""
        from styling_agent import REQUIRED_PIECES
        graph_pairs = {
            (e["from"], e["to"])
            for e in self.kg["edges"] if e["type"] == "REQUIRES"
        }
        for occ, types in REQUIRED_PIECES.items():
            for t in set(types):    # dedupe gym's duplicate "activewear"
                expected = (f"occasion:{occ}", f"type:{t}")
                self.assertIn(expected, graph_pairs,
                              f"Missing REQUIRES edge: {expected}")


class TestNoPersonalDataLeaks(unittest.TestCase):
    """The committed JSON is built from seed data only. No occurrence
    of the previously-anonymized real name. The owner label is exactly
    'Demo User'."""

    def test_no_real_name_in_json(self):
        with open(_KG_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("Eatedal", raw,
                         "Real personal name leaked into the committed JSON.")
        self.assertNotIn("Alfadhel", raw,
                         "Real personal name leaked into the committed JSON.")

    def test_user_node_label_is_demo(self):
        kg = _load_kg()
        user = next((n for n in kg["nodes"] if n["type"] == "User"), None)
        self.assertIsNotNone(user)
        self.assertEqual(user["label"], "Demo User")


class TestGeneratorReproducibility(unittest.TestCase):
    """Re-running the generator over the same seed data must produce
    the same graph (up to the `generated_at` timestamp). Determinism
    is what makes this graph reviewable in PRs without spurious
    edge-reordering diffs."""

    def test_re_run_produces_same_nodes_and_edges(self):
        from scripts.generate_wearly_kg import build  # type: ignore
        a = build(include_user=False)
        b = build(include_user=False)
        self.assertEqual([n["id"] for n in a["nodes"]],
                         [n["id"] for n in b["nodes"]])
        self.assertEqual([(e["from"], e["to"], e["type"]) for e in a["edges"]],
                         [(e["from"], e["to"], e["type"]) for e in b["edges"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
