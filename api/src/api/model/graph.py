from __future__ import annotations
from typing import Any, Dict, Iterator, List, Optional

from .node import Node
from .edge import Edge


class Graph:
    def __init__(self, graph_id: str, name: str = ""):
        self.graph_id: str = graph_id
        self.name: str = name

        self._nodes: Dict[str, Node] = {}
        self._edges: Dict[str, Edge] = {}

    def add_node(self, node: Node) -> None:
        if not isinstance(node, Node):
            raise TypeError("Argument must be an instance of Node class.")
        self._nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)

    def get_all_nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node_count(self) -> int:
        return len(self._nodes)

    def nodes(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def add_edge(self, edge: Edge) -> None:
        if not isinstance(edge, Edge):
            raise TypeError("Argument must be an instance of Edge class.")
        if edge.source.node_id not in self._nodes:
            raise ValueError(
                f"Source node '{edge.source.node_id}' is not in the graph. "
                f"First add the node with add_node()."
            )
        if edge.target.node_id not in self._nodes:
            raise ValueError(
                f"Target node '{edge.target.node_id}' is not in the graph. "
                f"First add the node with add_node()."
            )
        self._edges[edge.edge_id] = edge

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> None:
        self._edges.pop(edge_id, None)

    def get_all_edges(self) -> List[Edge]:
        return list(self._edges.values())

    def has_edge(self, edge_id: str) -> bool:
        return edge_id in self._edges

    def edge_count(self) -> int:
        return len(self._edges)

    def edges(self) -> Iterator[Edge]:
        return iter(self._edges.values())

    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        return [
            edge for edge in self._edges.values()
            if edge.source.node_id == node_id
            or edge.target.node_id == node_id
        ]

    def get_outgoing_edges(self, node_id: str) -> List[Edge]:
        result = []
        for edge in self._edges.values():
            if edge.source.node_id == node_id:
                result.append(edge)
            elif not edge.directed and edge.target.node_id == node_id:
                result.append(edge)
        return result

    def get_neighbors(self, node_id: str) -> List[Node]:
        seen: set = set()
        neighbors: List[Node] = []

        for edge in self._edges.values():
            neighbor = None
            if edge.source.node_id == node_id:
                neighbor = edge.target
            elif not edge.directed and edge.target.node_id == node_id:
                neighbor = edge.source

            if neighbor is not None and neighbor.node_id not in seen:
                seen.add(neighbor.node_id)
                neighbors.append(neighbor)

        return neighbors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "edges": [edge.to_dict() for edge in self._edges.values()],
        }

    def is_empty(self) -> bool:
        return len(self._nodes) == 0

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()

    def __repr__(self) -> str:
        return (
            f"Graph("
            f"id={self.graph_id!r}, "
            f"name={self.name!r}, "
            f"nodes={self.node_count()}, "
            f"edges={self.edge_count()}"
            f")"
        )

    def __len__(self) -> int:
        return self.node_count()