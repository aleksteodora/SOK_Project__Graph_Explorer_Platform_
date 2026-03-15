import csv
import io
import unittest
from unittest.mock import mock_open, patch

from csv_plugin.csv_plugin.csv_datasource_plugin import CsvDataSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_csv(rows: list[dict], fieldnames: list[str] | None = None) -> str:
    """Serializes a list of dicts to a CSV string with a header row."""
    if not rows:
        return ""
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def make_graph(csv_string: str):
    """Loads a Graph from a raw CSV string by mocking the file open call."""
    mock_file = mock_open(read_data=csv_string)
    with patch("builtins.open", mock_file):
        ds = CsvDataSource()
        return ds.load({"file_name": "fake.csv"})


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

CSV_BASIC = build_csv([
    {"id": "root",       "parent_id": "",      "name": "Root Node", "value": "100",  "created": "2026-03-12"},
    {"id": "child1",     "parent_id": "root",  "name": "Child One", "value": "42",   "created": "2026-01-15"},
    {"id": "child2",     "parent_id": "root",  "name": "Child Two", "value": "3.14", "created": ""},
    {"id": "grandchild1","parent_id": "child1","name": "Grandchild","value": "7",    "created": ""},
])

CSV_NO_PARENT = build_csv([
    {"id": "root",  "name": "Root", "value": "1"},
    {"id": "alpha", "name": "A",    "value": "2"},
    {"id": "beta",  "name": "B",    "value": "3"},
])

CSV_INVALID_PARENT = build_csv([
    {"id": "orphan", "parent_id": "nonexistent", "name": "Orphan"},
])

CSV_DUPLICATE_IDS = build_csv([
    {"id": "same", "parent_id": "",     "value": "1"},
    {"id": "same", "parent_id": "",     "value": "2"},   # duplicate — skipped
    {"id": "other","parent_id": "same", "value": "3"},
])

CSV_MISSING_ID = build_csv([
    {"id": "",     "name": "No ID Here"},
    {"id": "valid","name": "Valid"},
])

CSV_EMPTY_CELLS = build_csv([
    {"id": "node", "parent_id": "", "a": "10", "b": "", "c": "   ", "d": "hello"},
])

CSV_DEEP = build_csv([
    {"id": "l1", "parent_id": "",   "depth": "1"},
    {"id": "l2", "parent_id": "l1", "depth": "2"},
    {"id": "l3", "parent_id": "l2", "depth": "3"},
    {"id": "l4", "parent_id": "l3", "depth": "4"},
    {"id": "l5", "parent_id": "l4", "depth": "5"},
])

CSV_MULTIPLE_CHILDREN = build_csv([
    {"id": "parent", "parent_id": "",       "label": "Parent"},
    {"id": "c1",     "parent_id": "parent", "label": "C1"},
    {"id": "c2",     "parent_id": "parent", "label": "C2"},
    {"id": "c3",     "parent_id": "parent", "label": "C3"},
])

CSV_TYPES = build_csv([
    {"id": "types", "parent_id": "",
     "int_val": "42", "float_val": "3.14", "str_val": "hello",
     "date_val": "2026-03-12", "empty_val": "", "whitespace_val": "   "},
])

CSV_SELF_REF = build_csv([
    {"id": "self", "parent_id": "self", "value": "5"},
])

CSV_EMPTY = "id,parent_id,name\n"   # header only, no data rows

CSV_NO_PARENT_COL = build_csv([
    {"id": "a", "name": "Alpha"},
    {"id": "b", "name": "Beta"},
])

CSV_MULTIPLE_ROOTS = build_csv([
    {"id": "root1", "parent_id": "",      "label": "Root 1"},
    {"id": "root2", "parent_id": "",      "label": "Root 2"},
    {"id": "child", "parent_id": "root1", "label": "Child"},
])


# ===========================================================================
# Test suites
# ===========================================================================

class TestCsvDataSourceNodes(unittest.TestCase):

    def test_basic_node_count(self):
        graph = make_graph(CSV_BASIC)
        self.assertEqual(len(list(graph.nodes())), 4)

    def test_root_attributes(self):
        graph = make_graph(CSV_BASIC)
        root = graph.get_node("root")
        self.assertIsNotNone(root)
        self.assertEqual(root.get_attribute("name"), "Root Node")
        self.assertEqual(root.get_attribute("value"), 100)

        from datetime import date
        self.assertIsInstance(root.get_attribute("created"), date)
        self.assertEqual(str(root.get_attribute("created")), "2026-03-12")

    def test_child1_attributes(self):
        graph = make_graph(CSV_BASIC)
        node = graph.get_node("child1")
        self.assertEqual(node.get_attribute("value"), 42)
        self.assertEqual(node.get_attribute("name"), "Child One")

    def test_child2_float_attribute(self):
        graph = make_graph(CSV_BASIC)
        node = graph.get_node("child2")
        self.assertAlmostEqual(node.get_attribute("value"), 3.14)

    def test_grandchild_attributes(self):
        graph = make_graph(CSV_BASIC)
        node = graph.get_node("grandchild1")
        self.assertEqual(node.get_attribute("value"), 7)

    def test_node_ids_are_unique(self):
        graph = make_graph(CSV_BASIC)
        ids = [n.node_id for n in graph.nodes()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_parent_column_all_nodes_created(self):
        graph = make_graph(CSV_NO_PARENT_COL)
        self.assertEqual(len(list(graph.nodes())), 2)

    def test_multiple_roots(self):
        graph = make_graph(CSV_MULTIPLE_ROOTS)
        self.assertEqual(len(list(graph.nodes())), 3)

    def test_empty_file_no_nodes(self):
        graph = make_graph(CSV_EMPTY)
        self.assertEqual(len(list(graph.nodes())), 0)
        self.assertEqual(len(list(graph.edges())), 0)

    def test_deep_nesting_node_count(self):
        graph = make_graph(CSV_DEEP)
        self.assertEqual(len(list(graph.nodes())), 5)

    def test_attribute_type_int(self):
        graph = make_graph(CSV_TYPES)
        node = graph.get_node("types")
        self.assertIsInstance(node.get_attribute("int_val"), int)
        self.assertEqual(node.get_attribute("int_val"), 42)

    def test_attribute_type_float(self):
        graph = make_graph(CSV_TYPES)
        node = graph.get_node("types")
        self.assertIsInstance(node.get_attribute("float_val"), float)
        self.assertAlmostEqual(node.get_attribute("float_val"), 3.14)

    def test_attribute_type_str(self):
        graph = make_graph(CSV_TYPES)
        node = graph.get_node("types")
        self.assertIsInstance(node.get_attribute("str_val"), str)
        self.assertEqual(node.get_attribute("str_val"), "hello")

    def test_attribute_type_date(self):
        from datetime import date
        graph = make_graph(CSV_TYPES)
        node = graph.get_node("types")
        self.assertIsInstance(node.get_attribute("date_val"), date)
        self.assertEqual(str(node.get_attribute("date_val")), "2026-03-12")


class TestCsvDataSourceEdges(unittest.TestCase):

    def test_basic_edge_count(self):
        graph = make_graph(CSV_BASIC)
        self.assertEqual(len(list(graph.edges())), 3)

    def test_root_to_child1_edge(self):
        graph = make_graph(CSV_BASIC)
        root   = graph.get_node("root")
        child1 = graph.get_node("child1")
        edges  = list(graph.edges())
        self.assertTrue(any(e.source == root and e.target == child1 for e in edges))

    def test_root_to_child2_edge(self):
        graph = make_graph(CSV_BASIC)
        root   = graph.get_node("root")
        child2 = graph.get_node("child2")
        edges  = list(graph.edges())
        self.assertTrue(any(e.source == root and e.target == child2 for e in edges))

    def test_child1_to_grandchild_edge(self):
        graph = make_graph(CSV_BASIC)
        child1      = graph.get_node("child1")
        grandchild1 = graph.get_node("grandchild1")
        edges = list(graph.edges())
        self.assertTrue(any(e.source == child1 and e.target == grandchild1 for e in edges))

    def test_no_parent_column_no_edges(self):
        graph = make_graph(CSV_NO_PARENT_COL)
        self.assertEqual(len(list(graph.edges())), 0)

    def test_no_parent_id_values_no_edges(self):
        graph = make_graph(CSV_NO_PARENT)
        self.assertEqual(len(list(graph.edges())), 0)

    def test_invalid_parent_ref_ignored(self):
        try:
            graph = make_graph(CSV_INVALID_PARENT)
            self.assertEqual(len(list(graph.edges())), 0)
            self.assertEqual(len(list(graph.nodes())), 1)
        except Exception as e:
            self.fail(f"Invalid parent_id raised an exception: {e}")

    def test_multiple_children_edges(self):
        graph = make_graph(CSV_MULTIPLE_CHILDREN)
        parent = graph.get_node("parent")
        edges  = list(graph.edges())
        out_edges = [e for e in edges if e.source == parent]
        self.assertEqual(len(out_edges), 3)

    def test_deep_nesting_edge_count(self):
        graph = make_graph(CSV_DEEP)
        self.assertEqual(len(list(graph.edges())), 4)

    def test_deep_nesting_chain(self):
        graph = make_graph(CSV_DEEP)
        edges = list(graph.edges())
        pairs = [(e.source.node_id, e.target.node_id) for e in edges]
        self.assertIn(("l1", "l2"), pairs)
        self.assertIn(("l2", "l3"), pairs)
        self.assertIn(("l3", "l4"), pairs)
        self.assertIn(("l4", "l5"), pairs)

    def test_multiple_roots_correct_edges(self):
        graph = make_graph(CSV_MULTIPLE_ROOTS)
        root1 = graph.get_node("root1")
        child = graph.get_node("child")
        edges = list(graph.edges())
        self.assertEqual(len(edges), 1)
        self.assertTrue(any(e.source == root1 and e.target == child for e in edges))

    def test_self_reference_creates_self_loop(self):
        try:
            graph = make_graph(CSV_SELF_REF)
            edges = list(graph.edges())
            self.assertTrue(any(e.source == e.target for e in edges))
        except Exception as e:
            self.fail(f"Self-referencing parent_id raised an exception: {e}")


class TestCsvDataSourceReturnType(unittest.TestCase):

    def test_load_returns_graph(self):
        from api.model.graph import Graph
        graph = make_graph(CSV_BASIC)
        self.assertIsInstance(graph, Graph)

    def test_nodes_returns_iterable(self):
        graph = make_graph(CSV_BASIC)
        self.assertTrue(hasattr(graph.nodes(), "__iter__"))

    def test_edges_returns_iterable(self):
        graph = make_graph(CSV_BASIC)
        self.assertTrue(hasattr(graph.edges(), "__iter__"))


class TestCsvDataSourceEdgeCases(unittest.TestCase):

    def test_empty_and_whitespace_cells_ignored(self):
        graph = make_graph(CSV_EMPTY_CELLS)
        node = graph.get_node("node")
        self.assertEqual(node.get_attribute("a"), 10)
        self.assertEqual(node.get_attribute("d"), "hello")
        self.assertNotIn("b", node.attributes)
        self.assertNotIn("c", node.attributes)

    def test_missing_id_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            make_graph(CSV_MISSING_ID)
        self.assertIn("non-empty 'id'", str(ctx.exception))

    def test_duplicate_ids_first_wins(self):
        graph = make_graph(CSV_DUPLICATE_IDS)
        nodes = list(graph.nodes())
        # Only 2 unique nodes: "same" and "other"
        self.assertEqual(len(nodes), 2)
        same_node = graph.get_node("same")
        # First occurrence has value=1
        self.assertEqual(same_node.get_attribute("value"), 1)

    def test_reserved_columns_not_attributes(self):
        graph = make_graph(CSV_BASIC)
        for node in graph.nodes():
            self.assertNotIn("id",        node.attributes)
            self.assertNotIn("parent_id", node.attributes)

    def test_empty_csv_header_only(self):
        graph = make_graph(CSV_EMPTY)
        self.assertEqual(len(list(graph.nodes())), 0)
        self.assertEqual(len(list(graph.edges())), 0)

    def test_load_resets_state_between_calls(self):
        """Calling load() twice should not accumulate nodes/edges."""
        mock_file = mock_open(read_data=CSV_BASIC)
        with patch("builtins.open", mock_file):
            ds = CsvDataSource()
            ds.load({"file_name": "fake.csv"})
            graph = ds.load({"file_name": "fake.csv"})

        self.assertEqual(len(list(graph.nodes())), 4)
        self.assertEqual(len(list(graph.edges())), 3)

    def test_node_with_no_attributes_created(self):
        csv_str = build_csv([
            {"id": "bare", "parent_id": ""},
        ])
        graph = make_graph(csv_str)
        self.assertIsNotNone(graph.get_node("bare"))

    def test_large_number_of_nodes(self):
        rows = [{"id": f"node_{i}", "parent_id": f"node_{i-1}" if i > 0 else "", "value": str(i)}
                for i in range(100)]
        csv_str = build_csv(rows)
        graph = make_graph(csv_str)
        self.assertEqual(len(list(graph.nodes())), 100)
        self.assertEqual(len(list(graph.edges())), 99)

    def test_integer_id_treated_as_string(self):
        csv_str = build_csv([
            {"id": "1", "parent_id": "", "name": "One"},
            {"id": "2", "parent_id": "1", "name": "Two"},
        ])
        graph = make_graph(csv_str)
        self.assertIsNotNone(graph.get_node("1"))
        self.assertIsNotNone(graph.get_node("2"))
        self.assertEqual(len(list(graph.edges())), 1)


if __name__ == "__main__":
    unittest.main()