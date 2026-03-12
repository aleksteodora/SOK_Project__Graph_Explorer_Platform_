import pytest
from api import Graph, Node, Edge
from simple_visualizer import SimpleVisualizerPlugin


@pytest.fixture
def plugin():
    return SimpleVisualizerPlugin()


@pytest.fixture
def graph():
    g = Graph("g1", "Test")
    n1 = Node("1", {"name": "Alice", "age": 30})
    n2 = Node("2", {"name": "Bob",   "age": 22})
    n3 = Node("3", {})  # bez atributa
    for n in [n1, n2, n3]: g.add_node(n)
    g.add_edge(Edge("e1", n1, n2, directed=True))
    g.add_edge(Edge("e2", n2, n3, directed=False))
    return g


def test_get_name(plugin):
    assert plugin.get_name() == "Simple"

def test_node_label_is_first_attribute(plugin, graph):
    nodes, _ = plugin._build_data(graph)
    alice = next(n for n in nodes if n["id"] == "1")
    assert alice["label"] == "Alice"

def test_node_label_fallback_to_id(plugin, graph):
    nodes, _ = plugin._build_data(graph)
    empty = next(n for n in nodes if n["id"] == "3")
    assert empty["label"] == "3"

def test_node_count(plugin, graph):
    nodes, _ = plugin._build_data(graph)
    assert len(nodes) == 3

def test_link_count(plugin, graph):
    _, links = plugin._build_data(graph)
    assert len(links) == 2

def test_directed_edge(plugin, graph):
    _, links = plugin._build_data(graph)
    e1 = next(l for l in links if l["source"] == "1")
    assert e1["directed"] is True

def test_undirected_edge(plugin, graph):
    _, links = plugin._build_data(graph)
    e2 = next(l for l in links if l["source"] == "2")
    assert e2["directed"] is False

def test_render_returns_script_tag(plugin, graph):
    html = plugin.render(graph)
    assert "<script>" in html
    assert "GraphVisualizer.mount" in html

def test_render_contains_node_data(plugin, graph):
    html = plugin.render(graph)
    assert "Alice" in html