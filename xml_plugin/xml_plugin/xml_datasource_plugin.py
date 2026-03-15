import datetime
from typing import List, Dict, Any
import os, sys
import xml.etree.ElementTree as et

from api import parse_attribute_value
from api import DataSourcePlugin, PluginParameter
from api import Graph
from api import Node
from api import Edge


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
        """
        Initializes the XmlDataSource plugin.

        Sets up an empty Graph, counters for generating unique node/edge IDs,
        and mappings to track XML node IDs and references for edges.
        """
        self._graph: Graph = Graph("why_does_the_graph_need_an_id", "xml_graph")
        self._node_counter = 1
        self._edge_counter = 1
        self._file_id_node_map: Dict[str, Node] = {}
        self._node_file_id_reference_map: Dict[Node, List[str]] = {}

    def get_name(self) -> str:
        """
        Returns the human-readable name of the plugin.

        Returns:
            str: Name of the plugin.
        """
        return "XmlDataSource"

    def get_parameters(self) -> List[PluginParameter]:
        """
        Returns the list of input parameters required by the plugin.

        This is used by the platform to generate input forms automatically.

        Returns:
            List[PluginParameter]: List containing a single parameter for the XML file name.
        """
        return [PluginParameter(
            name="file_name",
            label="Full name of the file in the platform data directory",
            required=True
        )]

    def load(self, params: Dict[str, Any]) -> Graph:
        """
        Loads and parses the XML file into a Graph object.

        Args:
            params (Dict[str, Any]): Dictionary containing plugin parameters. Must contain 'file_name'.

        Returns:
            Graph: The populated graph representing the XML structure.
        """
        # Reset graph and counters
        self._graph = Graph(params["file_name"], "xml_graph")
        self._node_counter = 1
        self._edge_counter = 1
        self._file_id_node_map = {}
        self._node_file_id_reference_map = {}

        # Build absolute file path
        data_dir = os.path.join(sys.prefix, 'data')
        file_path = os.path.join(data_dir, params["file_name"])

        # Parse XML
        tree = et.parse(file_path)
        root = tree.getroot()

        # Build nodes recursively
        self._build_node_and_add_to_graph(root)
        self._connect_references()
        return self._graph

    def _build_node_and_add_to_graph(self, xml_node: et.Element) -> Node:
        """
        Recursively converts an XML element into a Node and adds it to the graph.

        Child elements are either added as attributes (if leaf) or as child nodes (creating edges).

        Args:
            xml_node (et.Element): The XML element to convert.

        Returns:
            Node: The created Node object corresponding to this XML element.
        """
        file_id = xml_node.attrib.get("id")
        referenced_ids = None
        if xml_node.attrib.get("ref"):
            referenced_ids = [r.strip() for r in xml_node.attrib.get("ref").split(",")]

        node = Node(str(self._node_counter))
        node.set_attribute("name", xml_node.tag)
        self._graph.add_node(node)
        self._node_counter += 1

        for child in xml_node:
            if len(child):
                # Child has its own children → create edge to child node
                self._build_edge_and_add_to_graph(node, self._build_node_and_add_to_graph(child))
            elif child.text and child.text.strip() != "":
                # Leaf node → treat as attribute
                node.set_attribute(child.tag, parse_attribute_value(child.text.strip()))

        if file_id:
            self._file_id_node_map[file_id] = node

        if referenced_ids:
            self._node_file_id_reference_map[node] = referenced_ids

        return node

    def _build_edge_and_add_to_graph(self, src: Node, des: Node) -> Edge:
        """
        Creates an Edge from src to des and adds it to the graph.

        Args:
            src (Node): The source node.
            des (Node): The target node.

        Returns:
            Edge: The created Edge object.
        """
        edge = Edge(str(self._edge_counter), src, des)
        self._graph.add_edge(edge)
        self._edge_counter += 1
        return edge

    def _connect_references(self):
        """
        Connects nodes that reference other nodes using the 'ref' attribute.

        For each node with a reference, looks up the target node by its 'id'
        and creates an edge from the referencing node to the target node.
        """
        for parent in self._node_file_id_reference_map.keys():
            for ref in self._node_file_id_reference_map[parent]:
                child = self._file_id_node_map.get(ref)
                if not child:
                    continue
                self._build_edge_and_add_to_graph(parent, child)