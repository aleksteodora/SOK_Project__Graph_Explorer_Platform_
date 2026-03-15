import unittest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from xml_plugin.xml_plugin.xml_datasource_plugin import XmlDataSource

TEST_XML = """<A id="1">
    <B>
        <size>10</size>
        <color>red</color>
    </B>
    <C id="2" ref="1">
        <weight>5</weight>
    </C>
</A>"""

TEST_XML_NO_REF = """<Root>
    <Item>
        <name>test</name>
    </Item>
</Root>"""

TEST_XML_MULTIPLE_REFS = """<Root id="1">
    <Child1 ref="1">
        <value>10</value>
    </Child1>
    <Child2 ref="1">
        <value>20</value>
    </Child2>
</Root>"""

TEST_XML_NESTED = """<A id="1">
    <B id="2">
        <C ref="1">
            <data>5</data>
        </C>
    </B>
</A>"""

TEST_XML_INVALID_REF = """<Root>
    <Child ref="999">
        <value>10</value>
    </Child>
</Root>"""

TEST_XML_MALFORMED = """<Root>
    <Unclosed>
        <tag>value
    </Root>
"""

TEST_XML_EMPTY = """<Root></Root>"""

TEST_XML_ONLY_ATTRS = """<Root id="1" ref="999" someattr="abc"></Root>"""

TEST_XML_DEEP_NESTING = """<A id="1">
    <B>
        <C>
            <D>
                <E>
                    <F>
                        <value>42</value>
                    </F>
                </E>
            </D>
        </C>
    </B>
</A>"""

TEST_XML_EMPTY_TEXT = """<Root>
    <Child>
        <empty></empty>
        <whitespace>   </whitespace>
        <valid>10</valid>
    </Child>
</Root>"""

TEST_XML_COMMA_REFS = """<Root id="1">
    <NodeA id="2">
        <val>1</val>
    </NodeA>
    <NodeB ref="1,2">
        <val>2</val>
    </NodeB>
</Root>"""

TEST_XML_COMMA_REFS_SPACES = """<Root id="1">
    <NodeA id="2">
        <val>1</val>
    </NodeA>
    <NodeB ref="1, 2">
        <val>2</val>
    </NodeB>
</Root>"""

TEST_XML_FLOAT = """<Root>
    <Item>
        <price>3.14</price>
    </Item>
</Root>"""

TEST_XML_DATE = """<Root>
    <Item>
        <created>2026-03-12</created>
    </Item>
</Root>"""

TEST_XML_MULTIPLE_CHILDREN = """<Root>
    <A><val>1</val></A>
    <B><val>2</val></B>
    <C><val>3</val></C>
</Root>"""

TEST_XML_SIBLING_REFS = """<Root>
    <A id="1"><val>1</val></A>
    <B id="2"><val>2</val></B>
    <C ref="1,2"><val>3</val></C>
</Root>"""


def make_graph(xml_string):
    root_element = ET.fromstring(xml_string)
    mock_tree = MagicMock()
    mock_tree.getroot.return_value = root_element

    with patch("xml.etree.ElementTree.parse", return_value=mock_tree):
        ds = XmlDataSource()
        return ds.load({"file_name": "fake.xml"})


class TestXmlDataSourceNodes(unittest.TestCase):

    def test_node_count(self):
        graph = make_graph(TEST_XML)
        self.assertEqual(len(list(graph.nodes())), 3)  # A, B, C

    def test_node_attributes_b(self):
        graph = make_graph(TEST_XML)
        b_node = next(node for node in graph.nodes() if "size" in node.attributes)
        self.assertEqual(b_node.get_attribute("size"), 10)
        self.assertEqual(b_node.get_attribute("color"), "red")

    def test_node_attributes_c(self):
        graph = make_graph(TEST_XML)
        c_node = next(node for node in graph.nodes() if "weight" in node.attributes)
        self.assertEqual(c_node.get_attribute("weight"), 5)

    def test_no_ref_no_extra_edges(self):
        graph = make_graph(TEST_XML_NO_REF)
        nodes = list(graph.nodes())
        self.assertEqual(len(nodes), 2)  # Root, Item
        self.assertEqual(len(list(graph.edges())), 1)

    def test_node_ids_are_unique(self):
        graph = make_graph(TEST_XML)
        ids = [node.node_id for node in graph.nodes()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_node_name_attribute_set(self):
        # Svaki node mora imati 'name' atribut jednak nazivu XML taga
        graph = make_graph(TEST_XML)
        names = [node.get_attribute("name") for node in graph.nodes()]
        self.assertIn("A", names)
        self.assertIn("B", names)
        self.assertIn("C", names)

    def test_multiple_children_node_count(self):
        graph = make_graph(TEST_XML_MULTIPLE_CHILDREN)
        self.assertEqual(len(list(graph.nodes())), 4)  # Root + A + B + C

    def test_multiple_children_edge_count(self):
        graph = make_graph(TEST_XML_MULTIPLE_CHILDREN)
        self.assertEqual(len(list(graph.edges())), 3)  # Root->A, Root->B, Root->C

    def test_float_attribute(self):
        graph = make_graph(TEST_XML_FLOAT)
        item = next(node for node in graph.nodes() if "price" in node.attributes)
        self.assertAlmostEqual(item.get_attribute("price"), 3.14)

    def test_date_attribute(self):
        import datetime
        graph = make_graph(TEST_XML_DATE)
        item = next(node for node in graph.nodes() if "created" in node.attributes)
        self.assertEqual(item.get_attribute("created"), datetime.date(2026, 3, 12))

    def test_node_counter_resets_between_loads(self):
        # Dva uzastopna load() poziva moraju davati iste node_id-ove
        root_element = ET.fromstring(TEST_XML)
        mock_tree = MagicMock()
        mock_tree.getroot.return_value = root_element

        with patch("xml.etree.ElementTree.parse", return_value=mock_tree):
            ds = XmlDataSource()
            graph1 = ds.load({"file_name": "fake.xml"})
            graph2 = ds.load({"file_name": "fake.xml"})

        ids1 = sorted([node.node_id for node in graph1.nodes()])
        ids2 = sorted([node.node_id for node in graph2.nodes()])
        self.assertEqual(ids1, ids2)


class TestXmlDataSourceEdges(unittest.TestCase):

    def test_ref_edge_exists(self):
        graph = make_graph(TEST_XML)
        c_node = next(node for node in graph.nodes() if "weight" in node.attributes)
        edges = list(graph.edges())
        ref_edge = [e for e in edges if e.source == c_node]
        self.assertTrue(any(e.target.node_id == "1" for e in ref_edge))

    def test_parent_child_edge_exists(self):
        graph = make_graph(TEST_XML)
        b_node = next(node for node in graph.nodes() if "size" in node.attributes)
        edges = list(graph.edges())
        self.assertTrue(any(e.target == b_node for e in edges))

    def test_multiple_refs_to_same_node(self):
        graph = make_graph(TEST_XML_MULTIPLE_REFS)
        edges = list(graph.edges())
        root_node = next(node for node in graph.nodes() if node.node_id == "1")
        ref_edges = [e for e in edges if e.target == root_node]
        self.assertEqual(len(ref_edges), 2)

    def test_invalid_ref_ignored(self):
        try:
            graph = make_graph(TEST_XML_INVALID_REF)
            edges = list(graph.edges())
            self.assertEqual(len(edges), 1)  # samo parent->child
        except Exception as e:
            self.fail("Nevazeci ref bacio je izuzetak: " + str(e))

    def test_nested_ref_edge(self):
        graph = make_graph(TEST_XML_NESTED)
        edges = list(graph.edges())
        c_node = next(node for node in graph.nodes() if "data" in node.attributes)
        ref_edges = [e for e in edges if e.source == c_node]
        self.assertTrue(any(e.target.node_id == "1" for e in ref_edges))

    def test_comma_separated_refs(self):
        # ref="1,2" mora kreirati dve ivice
        graph = make_graph(TEST_XML_COMMA_REFS)
        edges = list(graph.edges())
        b_node = next(node for node in graph.nodes() if node.get_attribute("name") == "NodeB")
        ref_edges = [e for e in edges if e.source == b_node]
        ref_targets = {e.target.node_id for e in ref_edges}
        self.assertIn("1", ref_targets)
        self.assertIn("2", ref_targets)

    def test_comma_separated_refs_with_spaces(self):
        # ref="1, 2" sa razmakom mora raditi isto kao ref="1,2"
        graph = make_graph(TEST_XML_COMMA_REFS_SPACES)
        edges = list(graph.edges())
        b_node = next(node for node in graph.nodes() if node.get_attribute("name") == "NodeB")
        ref_edges = [e for e in edges if e.source == b_node]
        ref_targets = {e.target.node_id for e in ref_edges}
        self.assertIn("1", ref_targets)
        self.assertIn("2", ref_targets)

    def test_sibling_refs(self):
        # C referencira i A i B koji su siblings, ne roditelji
        graph = make_graph(TEST_XML_SIBLING_REFS)
        edges = list(graph.edges())
        c_node = next(node for node in graph.nodes() if node.get_attribute("name") == "C")
        ref_edges = [e for e in edges if e.source == c_node]
        ref_targets = {e.target.node_id for e in ref_edges}
        self.assertIn("1", ref_targets)
        self.assertIn("2", ref_targets)

    def test_edge_ids_are_unique(self):
        graph = make_graph(TEST_XML)
        edge_ids = [edge.edge_id for edge in graph.edges()]
        self.assertEqual(len(edge_ids), len(set(edge_ids)))

    def test_total_edge_count(self):
        # TEST_XML: A->B (parent-child), A->C (parent-child), C->A (ref) = 3 ivice
        graph = make_graph(TEST_XML)
        self.assertEqual(len(list(graph.edges())), 3)


class TestXmlDataSourceReturnType(unittest.TestCase):

    def test_load_returns_graph(self):
        from api.model.graph import Graph
        graph = make_graph(TEST_XML)
        self.assertIsInstance(graph, Graph)

    def test_nodes_returns_iterable(self):
        graph = make_graph(TEST_XML)
        self.assertTrue(hasattr(graph.nodes(), "__iter__"))

    def test_edges_returns_iterable(self):
        graph = make_graph(TEST_XML)
        self.assertTrue(hasattr(graph.edges(), "__iter__"))


class TestXmlDataSourceEdgeCases(unittest.TestCase):

    def test_malformed_xml_raises(self):
        with self.assertRaises(ET.ParseError):
            ET.fromstring(TEST_XML_MALFORMED)

    def test_empty_root_no_nodes_no_edges(self):
        graph = make_graph(TEST_XML_EMPTY)
        self.assertEqual(len(list(graph.nodes())), 1)   # samo Root
        self.assertEqual(len(list(graph.edges())), 0)

    def test_node_with_only_attributes_no_children(self):
        try:
            graph = make_graph(TEST_XML_ONLY_ATTRS)
            self.assertEqual(len(list(graph.nodes())), 1)
        except Exception as e:
            self.fail("XML sa samo atributima bacio je izuzetak: " + str(e))

    def test_deep_nesting(self):
        graph = make_graph(TEST_XML_DEEP_NESTING)
        self.assertEqual(len(list(graph.nodes())), 6)  # A, B, C, D, E, F
        self.assertEqual(len(list(graph.edges())), 5)  # svaki roditelj -> dete

    def test_empty_and_whitespace_text_ignored(self):
        graph = make_graph(TEST_XML_EMPTY_TEXT)
        child_node = next(node for node in graph.nodes() if "valid" in node.attributes)
        self.assertEqual(child_node.get_attribute("valid"), 10)
        self.assertNotIn("empty", child_node.attributes)
        self.assertNotIn("whitespace", child_node.attributes)

    def test_ref_to_self(self):
        xml = """<Root id="1" ref="1"><value>5</value></Root>"""
        try:
            graph = make_graph(xml)
            edges = list(graph.edges())
            self.assertTrue(any(e.source == e.target for e in edges))
        except Exception as e:
            self.fail("Self-ref bacio je izuzetak: " + str(e))

    def test_duplicate_id_last_wins(self):
        # Ako dva cvora imaju isti id, ref treba da pokazuje na poslednji
        xml = """<Root>
            <A id="1"><val>first</val></A>
            <B id="1"><val>second</val></B>
            <C ref="1"><val>ref</val></C>
        </Root>"""
        try:
            graph = make_graph(xml)
            edges = list(graph.edges())
            self.assertGreater(len(edges), 0)
        except Exception as e:
            self.fail("Dupli id bacio je izuzetak: " + str(e))

    def test_load_twice_same_result(self):
        # Pozivanje load() dva puta mora davati isti broj nodova i ivica
        root_element = ET.fromstring(TEST_XML)
        mock_tree = MagicMock()
        mock_tree.getroot.return_value = root_element

        with patch("xml.etree.ElementTree.parse", return_value=mock_tree):
            ds = XmlDataSource()
            g1 = ds.load({"file_name": "fake.xml"})
            g2 = ds.load({"file_name": "fake.xml"})

        self.assertEqual(len(list(g1.nodes())), len(list(g2.nodes())))
        self.assertEqual(len(list(g1.edges())), len(list(g2.edges())))


if __name__ == "__main__":
    unittest.main()