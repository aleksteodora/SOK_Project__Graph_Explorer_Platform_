from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from datetime import date

AttributeValue = Union[int, float, str, date]
ALLOWED_TYPES = (int, float, str, date)

def validate_attribute_value(key: str, value: Any) -> AttributeValue:
    if isinstance(value, bool):
        raise TypeError(
            f"Attribute '{key}': boolean is not allowed. "
            f"Use int(0 or 1) instead. Received: {value!r}"
        )
    if not isinstance(value, ALLOWED_TYPES):
        raise TypeError(
            f"Attribute '{key}': type '{type(value).__name__}' is not allowed. "
            f"Allowed types: int, float, str, date. Received: {value!r}"
        )
    return value

class Node:
    def __init__(
        self,
        node_id: str,
        attributes: Optional[Dict[str, AttributeValue]] = None
    ):
        if not node_id or not isinstance(node_id, str):
            raise ValueError("node_id must be a non-empty string.")

        self.node_id: str = node_id
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

    def attribute_names(self) -> List[str]:
        return list(self.attributes.keys())

    def matches_search(self, query: str) -> bool:
        q = query.lower()
        for key, value in self.attributes.items():
            if q in key.lower():
                return True
            if q in str(value).lower():
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        serialized = {}
        for key, value in self.attributes.items():
            serialized[key] = value.isoformat() if isinstance(value, date) else value

        return {
            "node_id": self.node_id,
            "attributes": serialized
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __repr__(self) -> str:
        return f"Node(id={self.node_id!r}, attributes={self.attributes})"