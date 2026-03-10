from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import date

from .node import Node, validate_attribute_value, AttributeValue

class Edge:
    def __init__(
        self,
        edge_id: str,
        source: Node,
        target: Node,
        directed: bool = True,
        attributes: Optional[Dict[str, AttributeValue]] = None
    ):
        if not edge_id or not isinstance(edge_id, str):
            raise ValueError("edge_id must be a non-empty string.")
        if not isinstance(source, Node):
            raise TypeError("source must be an instance of Node class.")
        if not isinstance(target, Node):
            raise TypeError("target must be an instance of Node class.")

        self.edge_id: str = edge_id
        self.source: Node = source
        self.target: Node = target
        self.directed: bool = directed
        self.attributes: Dict[str, AttributeValue] = {}

        for key, value in (attributes or {}).items():
            self.set_attribute(key, value)

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        validate_attribute_value(key, value)
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Optional[AttributeValue]:
        return self.attributes.get(key)

    def has_attribute(self, key: str) -> bool:
        return key in self.attributes

    def remove_attribute(self, key: str) -> None:
        self.attributes.pop(key, None)

    def to_dict(self) -> Dict[str, Any]:
        serialized = {}
        for key, value in self.attributes.items():
            serialized[key] = value.isoformat() if isinstance(value, date) else value

        return {
            "edge_id": self.edge_id,
            "source_id": self.source.node_id,
            "target_id": self.target.node_id,
            "directed": self.directed,
            "attributes": serialized
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return False
        return self.edge_id == other.edge_id

    def __hash__(self) -> int:
        return hash(self.edge_id)

    def __repr__(self) -> str:
        arrow = "→" if self.directed else "—"
        return f"Edge({self.edge_id!r}: {self.source.node_id} {arrow} {self.target.node_id})"