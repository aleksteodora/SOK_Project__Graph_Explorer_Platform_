import datetime
from typing import List, Dict, Any
import os, sys
import xml.etree.ElementTree as et

from api.src.api.model.node import parse_attribute_value
from api.src.api.plugin.plugin import DataSourcePlugin, PluginParameter
from api.src.api.model.graph import Graph, Node, Edge
import api.src.api.model.graph as g


class XmlDataSource(DataSourcePlugin):
    """
        Data source plugin for parsing XML files into a Graph object.

        The XML file should represent nodes as tags and attributes as child tags with text.
        Nodes can reference other nodes using 'ref' attributes to create edges.
        The file must have a root element.
        The load() function takes the filename of the XML file that is in platform data folder.
        The id attribute is optional and is used solely for the purpose of referencing inside the file itself.
        New ids are generated for each tag automatically.

        Rules:
        1. Every node can have an optional 'id' attribute. This is used for referencing other nodes.
        2. Nodes may have child nodes; these create direct edges in the graph.
        3. Leaf child tags without children are treated as attributes of their parent node.
        4. Nodes that reference another node should use the 'ref' attribute pointing to the target node's 'id'.
        5. Allowed attribute types: int, float, str, date (ISO format, e.g., 2026-03-12).
        6. Empty text or missing attributes are ignored.

        Expected XML structure:

        <root id="root_id">
            <NodeA id="1">
                <attribute1>value1</attribute1>
                <attribute2>42</attribute2>
                <ChildNode>
                    <attributeX>valueX</attributeX>
                </ChildNode>
            </NodeA>
            <NodeB ref="1">
                <attributeY>2026-03-12</attributeY>
            </NodeB>
        </root>

        Example interpretation:
        - NodeA (id="1") has attributes 'attribute1' and 'attribute2', and a child node 'ChildNode'.
        - NodeB references NodeA via ref="1" and has attribute 'attributeY'.
    """
    def __init__(self):
        self._graph: Graph = Graph("why_does_the_graph_need_an_id", "xml_graph")
        self._node_counter = 1
        self._edge_counter = 1
        self._file_id_node_map: Dict[str, Node] = {}
        self._node_file_id_reference_map: Dict[Node, str] = {}

    def get_name(self) -> str:
        return "XmlDataSource"

    def get_parameters(self) -> List[PluginParameter]:
        return [PluginParameter(name="file_name", label="Full name of the file in the platform data directory", required=True)]

    def load(self, params: Dict[str, Any]) -> Graph:
        self._graph = Graph(params["file_name"], "xml_graph")
        self._node_counter = 1
        self._edge_counter = 1
        self._file_id_node_map = {}
        self._node_file_id_reference_map = {}

        data_dir = os.path.join(sys.prefix, 'data')
        file_path = os.path.join(data_dir, params["file_name"])
        tree = et.parse(file_path)
        root = tree.getroot()
        self._build_node_and_add_to_graph(root)
        self._connect_references()
        return self._graph

    def _build_node_and_add_to_graph(self, xml_node: et.Element) -> Node:
        file_id = xml_node.attrib.get("id")
        referenced_id = xml_node.attrib.get("ref")
        node = Node(str(self._node_counter))
        self._graph.add_node(node)
        self._node_counter += 1
        for child in xml_node:
            if len(child):
                self._build_edge_and_add_to_graph(node, self._build_node_and_add_to_graph(child))
            elif child.text and child.text.strip() != "":
                node.set_attribute(child.tag, parse_attribute_value(child.text.strip()))

        if file_id:
            self._file_id_node_map[file_id] = node

        if referenced_id:
            self._node_file_id_reference_map[node] = referenced_id

        return node

    def _build_edge_and_add_to_graph(self, src:Node, des:Node) -> Edge:
        edge = Edge(str(self._edge_counter), src, des)
        self._graph.add_edge(edge)
        self._edge_counter += 1
        return edge

    def _connect_references(self):
        for parent in self._node_file_id_reference_map.keys():
            child = self._file_id_node_map.get(self._node_file_id_reference_map[parent])
            if not child:
                continue
            self._build_edge_and_add_to_graph(parent, child)
