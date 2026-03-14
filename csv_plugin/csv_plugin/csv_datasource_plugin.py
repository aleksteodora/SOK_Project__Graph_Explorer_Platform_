import csv
import os
import sys
from typing import Any, Dict, List

from api.model.edge import Edge
from api.model.graph import Graph
from api.model.node import Node, parse_attribute_value
from api.plugin.plugin import DataSourcePlugin, PluginParameter


class CsvDataSource(DataSourcePlugin):
    """
    Data source plugin for parsing CSV files into a Graph object.

    Each row in the CSV represents a node. The file must have a header row.
    The 'id' column is required and must be unique across all rows.
    The optional 'parent_id' column creates a directed edge from the parent node to this node.
    All other columns are treated as node attributes.
    The load() function takes the filename of the CSV file that is in the platform data folder.

    Rules:
    1. The CSV file must have a header row.
    2. Each row must have a non-empty 'id' field — this is the node identifier.
    3. If a row has a non-empty 'parent_id' that matches another row's 'id',
       a directed edge is created: parent → child.
    4. If 'parent_id' points to a non-existent 'id', the reference is silently ignored.
    5. Empty cells are ignored and do not become node attributes.
    6. Attribute types are inferred automatically: int, float, date (ISO format), or str.
    7. Allowed attribute types: int, float, str, date (ISO format, e.g., 2026-03-12).
    8. Duplicate 'id' values: the first occurrence is kept; subsequent rows with
       the same 'id' are silently skipped.

    Expected CSV structure:

        id,parent_id,name,value,created
        root,,Root Node,100,2026-03-12
        child1,root,Child One,42,2026-01-15
        child2,root,Child Two,3.14,
        grandchild1,child1,Grandchild,7,

    Example interpretation:
    - 'root' has no parent; attributes: name="Root Node", value=100, created=2026-03-12.
    - 'child1' and 'child2' are children of 'root' (edges: root→child1, root→child2).
    - 'grandchild1' is a child of 'child1' (edge: child1→grandchild1).
    """

    # Column names with special meaning — never treated as attributes
    _RESERVED_COLUMNS = {"id", "parent_id"}

    def __init__(self):
        """
        Initializes the CsvDataSource plugin.

        Sets up an empty Graph and a counter for generating unique edge IDs.
        Node IDs are taken directly from the CSV 'id' column, so no separate
        mapping is needed.
        """
        self._graph: Graph = Graph("why_does_the_graph_need_an_id", "csv_graph")
        self._edge_counter = 1

    def get_name(self) -> str:
        """
        Returns the human-readable name of the plugin.

        Returns:
            str: Name of the plugin.
        """
        return "CsvDataSource"

    def get_parameters(self) -> List[PluginParameter]:
        """
        Returns the list of input parameters required by the plugin.

        This is used by the platform to generate input forms automatically.

        Returns:
            List[PluginParameter]: List containing a single parameter for the CSV file name.
        """
        return [
            PluginParameter(
                name="file_name",
                label="Full name of the file in the platform data directory",
                required=True,
            )
        ]

    def load(self, params: Dict[str, Any]) -> Graph:
        """
        Loads and parses the CSV file into a Graph object.

        Performs two passes over the rows:
        1. First pass — creates all nodes and their attributes.
        2. Second pass — resolves 'parent_id' references and creates edges.

        Args:
            params (Dict[str, Any]): Dictionary containing plugin parameters.
                Must contain 'file_name'.

        Returns:
            Graph: The populated graph representing the CSV structure.

        Raises:
            ValueError: If a row is missing a non-empty 'id' field.
            FileNotFoundError: If the specified CSV file does not exist.
        """
        self._graph = Graph(params["file_name"], "csv_graph")
        self._edge_counter = 1

        data_dir = os.path.join(sys.prefix, "data")
        file_path = os.path.join(data_dir, params["file_name"])

        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # First pass: build all nodes
        for row in rows:
            self._build_node_and_add_to_graph(row)

        # Second pass: connect nodes via parent_id
        self._connect_parents(rows)

        return self._graph

    def _build_node_and_add_to_graph(self, row: Dict[str, str]) -> Node:
        """
        Converts a single CSV row into a Node and adds it to the graph.

        Skips the row silently if a node with the same 'id' already exists
        (i.e., duplicate IDs are handled by keeping the first occurrence).

        Args:
            row (Dict[str, str]): A dictionary representing one CSV row,
                keyed by column header names.

        Returns:
            Node: The created (or pre-existing) Node for this row's 'id'.

        Raises:
            ValueError: If the row's 'id' cell is missing or empty.
        """
        node_id = str(row.get("id") or "").strip()
        if not node_id:
            raise ValueError(
                "Each CSV row must have a non-empty 'id' field."
            )

        # Duplicate id → silently return the existing node (first-wins policy)
        if self._graph.has_node(node_id):
            return self._graph.get_node(node_id)

        node = Node(node_id)
        self._graph.add_node(node)

        for key, value in row.items():
            if key in self._RESERVED_COLUMNS:
                continue
            if value is None or str(value).strip() == "":
                continue
            node.set_attribute(key, parse_attribute_value(str(value).strip()))

        return node

    def _connect_parents(self, rows: List[Dict[str, str]]) -> None:
        """
        Creates edges based on 'parent_id' references in each row.

        For each row that contains a non-empty 'parent_id', looks up both
        the parent node and the child node in the graph, then creates a
        directed edge from parent to child. Invalid references (pointing to
        an 'id' that does not exist in the graph) are silently ignored.

        Args:
            rows (List[Dict[str, str]]): All rows from the CSV file.
        """
        for row in rows:
            parent_id = str(row.get("parent_id") or "").strip()
            child_id = str(row.get("id") or "").strip()

            if not parent_id or not child_id:
                continue

            if not self._graph.has_node(parent_id) or not self._graph.has_node(child_id):
                continue

            parent = self._graph.get_node(parent_id)
            child = self._graph.get_node(child_id)
            self._build_edge_and_add_to_graph(parent, child)

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