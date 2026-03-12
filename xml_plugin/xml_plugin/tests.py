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
        # jedina ivica je parent -> child, nema ref ivica
        self.assertEqual(len(list(graph.edges())), 1)

    def test_node_ids_are_unique(self):
        graph = make_graph(TEST_XML)
        ids = [node.node_id for node in graph.nodes()]
        self.assertEqual(len(ids), len(set(ids)))


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
        # mora postojati ivica koja vodi ka B
        self.assertTrue(any(e.target == b_node for e in edges))

    def test_multiple_refs_to_same_node(self):
        graph = make_graph(TEST_XML_MULTIPLE_REFS)
        edges = list(graph.edges())
        # i Child1 i Child2 imaju ref="1" -> Root, dakle 2 ref ivice + 2 parent->child
        root_node = next(node for node in graph.nodes() if node.node_id == "1")
        ref_edges = [e for e in edges if e.target == root_node]
        self.assertEqual(len(ref_edges), 2)

    def test_invalid_ref_ignored(self):
        # ref na nepostojeci id ne sme da baci gresku
        try:
            graph = make_graph(TEST_XML_INVALID_REF)
            edges = list(graph.edges())
            # ne sme postojati ivica ka nepostojecem cvoru
            self.assertEqual(len(edges), 1)  # samo parent->child
        except Exception as e:
            self.fail("Nevazeci ref bacio je izuzetak: " + str(e))

    def test_nested_ref_edge(self):
        graph = make_graph(TEST_XML_NESTED)
        edges = list(graph.edges())
        # C ima ref="1" -> A (node_id="1")
        c_node = next(node for node in graph.nodes() if "data" in node.attributes)
        ref_edges = [e for e in edges if e.source == c_node]
        self.assertTrue(any(e.target.node_id == "1" for e in ref_edges))


class TestXmlDataSourceReturnType(unittest.TestCase):

    def test_load_returns_graph(self):
        from api.src.api.model.graph import Graph
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
        # Nabudjeni XML treba da baci ParseError pre nego sto uopste stigne do nas
        with self.assertRaises(ET.ParseError):
            ET.fromstring(TEST_XML_MALFORMED)

    def test_empty_root_no_nodes_no_edges(self):
        graph = make_graph(TEST_XML_EMPTY)
        nodes = list(graph.nodes())
        edges = list(graph.edges())
        self.assertEqual(len(nodes), 1)   # samo Root
        self.assertEqual(len(edges), 0)

    def test_node_with_only_attributes_no_children(self):
        # Root ima id i ref ali nema child tagova — ne sme da pukne
        try:
            graph = make_graph(TEST_XML_ONLY_ATTRS)
            nodes = list(graph.nodes())
            self.assertEqual(len(nodes), 1)
        except Exception as e:
            self.fail("XML sa samo atributima bacio je izuzetak: " + str(e))

    def test_deep_nesting(self):
        # Duboko ugnjezdeni XML ne sme da pukne i mora da ima tacno 6 nodova
        graph = make_graph(TEST_XML_DEEP_NESTING)
        nodes = list(graph.nodes())
        self.assertEqual(len(nodes), 6)  # A, B, C, D, E, F
        edges = list(graph.edges())
        self.assertEqual(len(edges), 5)  # svaki roditelj -> dete

    def test_empty_and_whitespace_text_ignored(self):
        # Prazni i whitespace child tagovi ne smeju da postanu atributi
        graph = make_graph(TEST_XML_EMPTY_TEXT)
        child_node = next(node for node in graph.nodes() if "valid" in node.attributes)
        self.assertEqual(child_node.get_attribute("valid"), 10)
        self.assertNotIn("empty", child_node.attributes)
        self.assertNotIn("whitespace", child_node.attributes)

    def test_ref_to_self(self):
        # Node koji referencira samog sebe
        xml = """<Root id="1" ref="1"><value>5</value></Root>"""
        try:
            graph = make_graph(xml)
            edges = list(graph.edges())
            # mora postojati self-loop ivica
            self.assertTrue(any(e.source == e.target for e in edges))
        except Exception as e:
            self.fail("Self-ref bacio je izuzetak: " + str(e))

if __name__ == "__main__":
    unittest.main()