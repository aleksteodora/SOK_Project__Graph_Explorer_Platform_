from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from datetime import date
import re

from api import Graph, Node, AttributeValue, Edge


class GraphService:
    """
    Provides core operations for manipulating and querying graph structures.
    
    This service handles node and edge creation, modification, deletion,
    as well as filtering and searching functionality on graph instances.
    """
    
    @staticmethod
    def search(graph: Graph, query: str) -> Graph:
        """
        Searches for nodes in the graph that match the provided query string.
        Returns a new subgraph containing only nodes that match the search criteria
        and their connecting edges.
        """
        if not query.strip():
            return graph

        matching_nodes = [
            node for node in graph.get_all_nodes()
            if node.matches_search(query)
        ]

        return GraphService._build_subgraph(
            graph=graph,
            nodes=matching_nodes,
            graph_id=f"{graph.graph_id}_search",
            name=f"{graph.name} [search: {query}]"
        )

    @staticmethod
    def filter(graph: Graph, filter_expr: str) -> Graph:
        """
        Filters nodes in the graph based on attribute comparison criteria.
        Parses the filter expression, evaluates each node's attributes,
        and returns a new subgraph containing only nodes that satisfy the filter.
        """
        attr_name, comparator, raw_value = GraphService._parse_filter(filter_expr)

        matching_nodes = []
        for node in graph.get_all_nodes():
            node_value = node.get_attribute(attr_name)

            if node_value is None:
                continue

            typed_value = GraphService._coerce_value(raw_value, node_value)

            if GraphService._compare(node_value, comparator, typed_value):
                matching_nodes.append(node)

        return GraphService._build_subgraph(
            graph=graph,
            nodes=matching_nodes,
            graph_id=f"{graph.graph_id}_filter",
            name=f"{graph.name} [filter: {filter_expr}]"
        )

    @staticmethod
    def _parse_filter(filter_expr: str) -> Tuple[str, str, str]:
        """Parses a filter expression into attribute name, comparator, and value."""
        pattern = r'^\s*(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$'
        match = re.match(pattern, filter_expr.strip())

        if not match:
            raise FilterParseError(
                f"Invalid filter expression: '{filter_expr}'. "
                f"Expected format: '<attribute> <comparator> <value>'. "
                f"Example: 'age > 30' or 'name == Alice'."
            )

        return match.group(1), match.group(2), match.group(3)

    @staticmethod
    def _coerce_value(raw_value: str, reference: AttributeValue) -> AttributeValue:
        """
        Converts a string value to match the type of a reference attribute.
        Supports casting to int, float, date (ISO format), and string types.
        """
        try:
            if isinstance(reference, int):
                return int(raw_value)
            elif isinstance(reference, float):
                return float(raw_value)
            elif isinstance(reference, date):
                return date.fromisoformat(raw_value)
            else:
                return raw_value
        except (ValueError, TypeError) as e:
            raise FilterTypeError(
                f"Value '{raw_value}' cannot be cast to "
                f"'{type(reference).__name__}': {e}"
            )

    @staticmethod
    def _compare(
        node_value: AttributeValue,
        comparator: str,
        filter_value: AttributeValue
    ) -> bool:
        """Performs a comparison between two attribute values using the specified operator."""
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">":  lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "<":  lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
        }
        try:
            return ops[comparator](node_value, filter_value)
        except TypeError:
            raise FilterTypeError(
                f"Cannot compare '{node_value}' ({type(node_value).__name__}) "
                f"with '{filter_value}' ({type(filter_value).__name__})."
            )

    @staticmethod
    def _build_subgraph(
        graph: Graph,
        nodes: List[Node],
        graph_id: str,
        name: str
    ) -> Graph:
        """
        Constructs a new subgraph from a list of nodes and their connecting edges.
        Only edges where both source and target nodes are in the nodes list are included.
        """
        subgraph = Graph(graph_id=graph_id, name=name)

        node_ids = set()
        for node in nodes:
            subgraph.add_node(node)
            node_ids.add(node.node_id)

        for edge in graph.get_all_edges():
            if edge.source.node_id in node_ids and edge.target.node_id in node_ids:
                subgraph.add_edge(edge)

        return subgraph

    @staticmethod
    def create_node(
        graph: Graph,
        node_id: str,
        attributes: Optional[Dict[str, AttributeValue]] = None
    ) -> Node:
        """Creates and adds a new node to the graph."""
        if graph.has_node(node_id):
            raise ValueError(f"Node '{node_id}' already exists.")

        node = Node(node_id=node_id, attributes=attributes or {})
        graph.add_node(node)
        return node

    @staticmethod
    def edit_node(
        graph: Graph,
        node_id: str,
        attributes: Dict[str, AttributeValue]
    ) -> Node:
        """Updates the attributes of an existing node."""
        node = graph.get_node(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' does not exist.")

        for key, value in attributes.items():
            node.set_attribute(key, value)

        return node

    @staticmethod
    def delete_node(graph: Graph, node_id: str) -> None:
        """
        Removes a node from the graph.
        A node can only be deleted if it has no connected edges.
        """
        if not graph.has_node(node_id):
            raise ValueError(f"Node '{node_id}' does not exist.")

        edges = graph.get_edges_for_node(node_id)
        if edges:
            edge_ids = [e.edge_id for e in edges]
            raise ValueError(
                f"Node '{node_id}' cannot be deleted because it still has "
                f"connected edges: {edge_ids}. Delete the edges first."
            )

        graph.remove_node(node_id)

    @staticmethod
    def create_edge(
        graph: Graph,
        edge_id: str,
        source_id: str,
        target_id: str,
        directed: bool = True,
        attributes: Optional[Dict[str, AttributeValue]] = None
    ) -> Edge:
        """Creates and adds a new edge between two nodes."""
        if graph.has_edge(edge_id):
            raise ValueError(f"Edge '{edge_id}' already exists.")
        if not graph.has_node(source_id):
            raise ValueError(f"Source node '{source_id}' does not exist.")
        if not graph.has_node(target_id):
            raise ValueError(f"Target node '{target_id}' does not exist.")

        source = graph.get_node(source_id)
        target = graph.get_node(target_id)

        edge = Edge(
            edge_id=edge_id,
            source=source,
            target=target,
            directed=directed,
            attributes=attributes or {}
        )
        graph.add_edge(edge)
        return edge

    @staticmethod
    def edit_edge(
        graph: Graph,
        edge_id: str,
        attributes: Dict[str, AttributeValue]
    ) -> Edge:
        """Updates the attributes of an existing edge."""
        edge = graph.get_edge(edge_id)
        if edge is None:
            raise ValueError(f"Edge '{edge_id}' does not exist.")

        for key, value in attributes.items():
            edge.set_attribute(key, value)

        return edge

    @staticmethod
    def delete_edge(graph: Graph, edge_id: str) -> None:
        """Removes an edge from the graph."""
        if not graph.has_edge(edge_id):
            raise ValueError(f"Edge '{edge_id}' does not exist.")

        graph.remove_edge(edge_id)

    @staticmethod
    def clear_graph(graph: Graph) -> None:
        """Removes all nodes and edges from the graph, leaving it empty."""
        graph.clear()


class FilterParseError(Exception):
    """Raised when the filter expression has an invalid format."""
    pass


class FilterTypeError(Exception):
    """Raised when the filter value cannot be cast to the attribute's type."""
    pass