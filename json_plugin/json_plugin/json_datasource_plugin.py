import json
import os
import sys
from typing import Any, Dict, List

from api.model.edge import Edge
from api.model.graph import Graph
from api.model.node import Node, parse_attribute_value
from api.plugin.plugin import DataSourcePlugin, PluginParameter


class JsonDataSource(DataSourcePlugin):
    """
    Data source plugin for parsing nested JSON into a Graph object.

    The JSON file should represent nodes as objects with required 'id' field.
    Nested objects are created as child nodes with edges connecting them.
    The file must contain a single root object.
    The load() function takes the filename of the JSON file that is in platform data folder.
    Node IDs are taken from the 'id' field and must be unique across the entire file.

    Expected node shape:
    {
      "id": "id1",
      "... any attributes ...": "...",
      "<any_key>": [ ... child node objects ... ]   <- last key is always children
    }

    Rules:
    1. Each object must have a non-empty "id".
    2. The LAST key in the object, if it's a list of objects, is treated as children
       and creates directed edges parent -> child. The key name does not matter.
    3. All other primitive fields are node attributes.
    4. String attributes are parsed with parse_attribute_value (int/float/date fallback).
    5. Allowed attribute types: int, float, str, date (ISO format, e.g., 2026-03-12).
    6. None, empty strings, and nested objects/lists (except children) are ignored as attributes.
    7. Boolean attributes are not supported - use 0/1 integers instead.

    Expected JSON structure:

    {
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

    Example interpretation:
    - Root node has attributes 'name' and 'created', and two child nodes 'child1' and 'child2'.
    - 'child1' has attributes 'value' and 'description', and a child node 'grandchild1'.
    - Edges are created: root -> child1, root -> child2, child1 -> grandchild1.
    """

    def __init__(self):
        """
        Initializes the JsonDataSource plugin.

        Sets up an empty Graph and counters for generating unique edge IDs.
        Node IDs are taken directly from the JSON 'id' field, so no mapping is needed.
        """
        self._graph: Graph = Graph("why_does_the_graph_need_an_id", "json_graph")
        self._node_counter = 1
        self._edge_counter = 1

    def get_name(self) -> str:
        """
        Returns the human-readable name of the plugin.

        Returns:
            str: Name of the plugin.
        """
        return "JsonDataSource"

    def get_parameters(self) -> List[PluginParameter]:
        """
        Returns the list of input parameters required by the plugin.

        This is used by the platform to generate input forms automatically.

        Returns:
            List[PluginParameter]: List containing a single parameter for the JSON file name.
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
        Loads and parses the JSON file into a Graph object.

        Args:
            params (Dict[str, Any]): Dictionary containing plugin parameters. Must contain 'file_name'.

        Returns:
            Graph: The populated graph representing the JSON structure.

        Raises:
            ValueError: If root JSON value is not an object, or if nodes have missing/duplicate IDs.
        """
        self._graph = Graph(params["file_name"], "json_graph")
        self._node_counter = 1
        self._edge_counter = 1

        data_dir = os.path.join(sys.prefix, "data")
        file_path = os.path.join(data_dir, params["file_name"])

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Root JSON value must be an object representing a node.")

        self._build_node_and_add_to_graph(data)
        return self._graph

    def _build_node_and_add_to_graph(self, json_node: Dict[str, Any]) -> Node:
        """
        Recursively converts a JSON object into a Node and adds it to the graph.

        The last key in the object, if it's a list of objects, is treated as children.
        All other keys (except 'id' and the children key) become node attributes.

        Args:
            json_node (Dict[str, Any]): The JSON object to convert.

        Returns:
            Node: The created Node object corresponding to this JSON object.

        Raises:
            ValueError: If the input is not a dictionary or if node ID is missing/invalid.
        """
        if not isinstance(json_node, dict):
            raise ValueError("Each node must be a JSON object.")

        node_id = str(json_node.get("id", "")).strip()
        if not node_id:
            raise ValueError("Each JSON node must contain a non-empty 'id' field.")

        if self._graph.has_node(node_id):
            return self._graph.get_node(node_id)

        node = Node(node_id)
        self._graph.add_node(node)

        keys = list(json_node.keys())
        last_key = keys[-1] if keys else None
        last_value = json_node.get(last_key)

        children = []
        children_key = None
        if (
            last_key is not None
            and last_key != "id"
            and isinstance(last_value, list)
            and all(isinstance(i, dict) for i in last_value)
        ):
            children = last_value
            children_key = last_key

        for key, value in json_node.items():
            if key in {"id"} or key == children_key:
                continue
            converted = self._convert_attribute_value(value)
            if converted is None:
                continue
            node.set_attribute(key, converted)

        for child_json in children:
            child_node = self._build_node_and_add_to_graph(child_json)
            self._build_edge_and_add_to_graph(node, child_node)

        return node

    def _extract_node_id(self, json_node: Dict[str, Any]) -> str:
        """
        Extracts and validates the node ID from a JSON object.

        Args:
            json_node (Dict[str, Any]): The JSON object containing an 'id' field.

        Returns:
            str: The validated node ID.

        Raises:
            ValueError: If ID is missing, empty, or duplicates an existing node ID.
        """
        raw_id = json_node.get("id")
        if raw_id is None or (isinstance(raw_id, str) and raw_id.strip() == ""):
            raise ValueError("Each JSON node must contain a non-empty 'id' field.")

        node_id = str(raw_id)
        if self._graph.has_node(node_id):
            raise ValueError(f"Duplicate node id found in JSON: {node_id!r}")
        return node_id

    def _convert_attribute_value(self, value: Any):
        """
        Converts a JSON value to an appropriate attribute type.

        Args:
            value (Any): The JSON value to convert.

        Returns:
            The converted value, or None if the value should be ignored.

        Raises:
            TypeError: If boolean value is encountered (use 0/1 integers instead).
        """
        if value is None:
            return None
        if isinstance(value, bool):
            raise TypeError("Boolean attributes are not supported. Use int(0 or 1) instead.")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            return parse_attribute_value(stripped)
        if isinstance(value, (dict, list)):
            return None
        return str(value)

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