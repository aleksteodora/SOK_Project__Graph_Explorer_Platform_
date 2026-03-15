import unittest
from unittest.mock import patch, mock_open
import json
from json_plugin.json_plugin.json_datasource_plugin import JsonDataSource

TEST_JSON = {
    "id": "root",
    "name": "Root Node",
    "created": "2026-03-13",
    "children": [
        {
            "id": "child1",
            "value": 42,
            "description": "First child",
            "subchildren": [
                {
                    "id": "grandchild1",
                    "active": 1
                }
            ]
        },
        {
            "id": "child2",
            "value": 3.14
        }
    ]
}

TEST_JSON_NO_CHILDREN = {
    "id": "root",
    "name": "Simple Root",
    "value": 100
}

TEST_JSON_MULTIPLE_CHILDREN = {
    "id": "parent",
    "title": "Parent Node",
    "items": [
        {"id": "child1", "data": "first"},
        {"id": "child2", "data": "second"},
        {"id": "child3", "data": "third"}
    ]
}

TEST_JSON_DEEP_NESTING = {
    "id": "level1",
    "name": "Level 1",
    "children": [
        {
            "id": "level2",
            "name": "Level 2",
            "children": [
                {
                    "id": "level3",
                    "name": "Level 3",
                    "children": [
                        {
                            "id": "level4",
                            "name": "Level 4",
                            "value": 42
                        }
                    ]
                }
            ]
        }
    ]
}

TEST_JSON_WITH_TYPES = {
    "id": "types",
    "string": "text",
    "integer": 100,
    "float": 3.14159,
    "date": "2026-03-13",
    "empty_string": "",
    "null_value": None,
    "ignored_object": {"should": "be ignored"},
    "ignored_list": [1, 2, 3],
    "children": []
}

TEST_JSON_DUPLICATE_IDS = {
    "id": "same",
    "children": [
        {"id": "same", "value": 1},
        {"id": "different", "value": 2}
    ]
}

TEST_JSON_MISSING_ID = {
    "name": "No ID Here",
    "value": 42
}

TEST_JSON_EMPTY_ID = {
    "id": "",
    "name": "Empty ID"
}

TEST_JSON_BOOLEAN = {
    "id": "bool_test",
    "active": True,
    "completed": False
}

TEST_JSON_ARRAY_AS_ROOT = [{"id": "node1"}, {"id": "node2"}]

TEST_JSON_SELF_REFERENCE = {
    "id": "self",
    "ref": "self",
    "value": 10
}

def make_graph(json_data):
    mock_file = mock_open(read_data=json.dumps(json_data))
    with patch("builtins.open", mock_file):
        ds = JsonDataSource()
        return ds.load({"file_name": "fake.json"})

class TestJsonDataSourceNodes(unittest.TestCase):

    def test_node_count(self):
        graph = make_graph(TEST_JSON)
        nodes = list(graph.nodes())
        self.assertEqual(len(nodes), 4)

    def test_node_attributes_root(self):
        graph = make_graph(TEST_JSON)
        root = graph.get_node("root")
        self.assertEqual(root.get_attribute("name"), "Root Node")
        from datetime import date
        self.assertIsInstance(root.get_attribute("created"), date)
        self.assertEqual(str(root.get_attribute("created")), "2026-03-13")

    def test_node_attributes_child1(self):
        graph = make_graph(TEST_JSON)
        child1 = graph.get_node("child1")
        self.assertEqual(child1.get_attribute("value"), 42)
        self.assertEqual(child1.get_attribute("description"), "First child")

    def test_node_attributes_child2(self):
        graph = make_graph(TEST_JSON)
        child2 = graph.get_node("child2")
        self.assertEqual(child2.get_attribute("value"), 3.14)

    def test_node_attributes_grandchild(self):
        graph = make_graph(TEST_JSON)
        grandchild = graph.get_node("grandchild1")
        self.assertEqual(grandchild.get_attribute("active"), 1)

    def test_no_children_single_node(self):
        graph = make_graph(TEST_JSON_NO_CHILDREN)
        nodes = list(graph.nodes())
        self.assertEqual(len(nodes), 1)
        root = graph.get_node("root")
        self.assertEqual(root.get_attribute("name"), "Simple Root")
        self.assertEqual(root.get_attribute("value"), 100)

class TestJsonDataSourceEdges(unittest.TestCase):

    def test_parent_child_edges_count(self):
        graph = make_graph(TEST_JSON)
        edges = list(graph.edges())
        self.assertEqual(len(edges), 3)

    def test_root_to_child1_edge(self):
        graph = make_graph(TEST_JSON)
        root = graph.get_node("root")
        child1 = graph.get_node("child1")
        edges = list(graph.edges())
        self.assertTrue(any(e.source == root and e.target == child1 for e in edges))

    def test_root_to_child2_edge(self):
        graph = make_graph(TEST_JSON)
        root = graph.get_node("root")
        child2 = graph.get_node("child2")
        edges = list(graph.edges())
        self.assertTrue(any(e.source == root and e.target == child2 for e in edges))

    def test_child1_to_grandchild_edge(self):
        graph = make_graph(TEST_JSON)
        child1 = graph.get_node("child1")
        grandchild = graph.get_node("grandchild1")
        edges = list(graph.edges())
        self.assertTrue(any(e.source == child1 and e.target == grandchild for e in edges))

    def test_multiple_children_to_same_parent(self):
        graph = make_graph(TEST_JSON_MULTIPLE_CHILDREN)
        parent = graph.get_node("parent")
        edges = list(graph.edges())
        child_edges = [e for e in edges if e.source == parent]
        self.assertEqual(len(child_edges), 3)

    def test_deep_nesting_edges(self):
        graph = make_graph(TEST_JSON_DEEP_NESTING)
        edges = list(graph.edges())
        self.assertEqual(len(edges), 3)

class TestJsonDataSourceReturnType(unittest.TestCase):

    def test_load_returns_graph(self):
        from api.model.graph import Graph
        graph = make_graph(TEST_JSON)
        self.assertIsInstance(graph, Graph)

    def test_nodes_returns_iterable(self):
        graph = make_graph(TEST_JSON)
        self.assertTrue(hasattr(graph.nodes(), "__iter__"))

    def test_edges_returns_iterable(self):
        graph = make_graph(TEST_JSON)
        self.assertTrue(hasattr(graph.edges(), "__iter__"))

class TestJsonDataSourceEdgeCases(unittest.TestCase):

    def test_attribute_type_conversion(self):
        graph = make_graph(TEST_JSON_WITH_TYPES)
        node = graph.get_node("types")

        from datetime import date

        self.assertIsInstance(node.get_attribute("string"), str)
        self.assertIsInstance(node.get_attribute("integer"), int)
        self.assertIsInstance(node.get_attribute("float"), float)
        self.assertIsInstance(node.get_attribute("date"), date)

        self.assertEqual(node.get_attribute("string"), "text")
        self.assertEqual(node.get_attribute("integer"), 100)
        self.assertEqual(node.get_attribute("float"), 3.14159)
        self.assertEqual(str(node.get_attribute("date")), "2026-03-13")

    def test_empty_string_ignored(self):
        graph = make_graph(TEST_JSON_WITH_TYPES)
        node = graph.get_node("types")
        self.assertNotIn("empty_string", node.attributes)

    def test_null_value_ignored(self):
        graph = make_graph(TEST_JSON_WITH_TYPES)
        node = graph.get_node("types")
        self.assertNotIn("null_value", node.attributes)

    def test_object_ignored_as_attribute(self):
        graph = make_graph(TEST_JSON_WITH_TYPES)
        node = graph.get_node("types")
        self.assertNotIn("ignored_object", node.attributes)

    def test_list_ignored_as_attribute(self):
        graph = make_graph(TEST_JSON_WITH_TYPES)
        node = graph.get_node("types")
        self.assertNotIn("ignored_list", node.attributes)

    def test_duplicate_ids_raises_error(self):
        graph = make_graph(TEST_JSON_DUPLICATE_IDS)
        nodes = list(graph.nodes())
        self.assertEqual(len(nodes), 2)

    def test_missing_id_raises_error(self):
        with self.assertRaises(ValueError) as context:
            make_graph(TEST_JSON_MISSING_ID)
        self.assertIn("non-empty 'id'", str(context.exception))

    def test_empty_id_raises_error(self):
        with self.assertRaises(ValueError) as context:
            make_graph(TEST_JSON_EMPTY_ID)
        self.assertIn("non-empty 'id'", str(context.exception))

    def test_boolean_raises_type_error(self):
        with self.assertRaises(TypeError) as context:
            make_graph(TEST_JSON_BOOLEAN)
        self.assertIn("Boolean attributes are not supported", str(context.exception))

    def test_array_as_root_raises_error(self):
        with self.assertRaises(ValueError) as context:
            make_graph(TEST_JSON_ARRAY_AS_ROOT)
        self.assertIn("Root JSON value must be an object", str(context.exception))

    def test_empty_children_list(self):
        json_data = {"id": "root", "name": "test", "children": []}
        graph = make_graph(json_data)
        nodes = list(graph.nodes())
        edges = list(graph.edges())
        self.assertEqual(len(nodes), 1)
        self.assertEqual(len(edges), 0)

    def test_self_reference_no_cycle(self):
        graph = make_graph(TEST_JSON_SELF_REFERENCE)
        node = graph.get_node("self")
        edges = list(graph.edges())
        self.assertEqual(len(edges), 0)

    def test_non_last_key_as_children_ignored(self):
        json_data = {
            "id": "root",
            "children": [{"id": "child1"}],
            "last_key": "should not be children"
        }
        graph = make_graph(json_data)
        child = graph.get_node("child1")
        edges = list(graph.edges())
        self.assertEqual(len(edges), 0)
        root = graph.get_node("root")
        self.assertEqual(root.get_attribute("last_key"), "should not be children")

    def test_multiple_list_keys_only_last_is_children(self):
        json_data = {
            "id": "root",
            "first_list": [1, 2, 3],
            "second_list": [{"id": "child1"}, {"id": "child2"}]
        }
        graph = make_graph(json_data)
        self.assertIsNotNone(graph.get_node("child1"))
        self.assertIsNotNone(graph.get_node("child2"))
        root = graph.get_node("root")
        self.assertEqual(root.get_attribute("first_list"), None)

if __name__ == "__main__":
    unittest.main()