import pytest
from api import Graph, Node, Edge
from datetime import date

def test_node_creation():
    n = Node("1", {"name": "Alice", "age": 30})
    assert n.node_id == "1"
    assert n.get_attribute("name") == "Alice"
    assert n.get_attribute("age") == 30

def test_node_invalid_type():
    with pytest.raises(TypeError):
        Node("1", {"tags": [1, 2, 3]})

def test_node_bool_blocked():
    with pytest.raises(TypeError):
        Node("1", {"active": True})

def test_graph_add_edge_without_nodes():
    g = Graph("g1", "Test")
    n1 = Node("1", {"name": "Alice"})
    n2 = Node("2", {"name": "Bob"})
    g.add_node(n1)
    with pytest.raises(ValueError):
        g.add_edge(Edge("e1", n1, n2))  # n2 nije u grafu