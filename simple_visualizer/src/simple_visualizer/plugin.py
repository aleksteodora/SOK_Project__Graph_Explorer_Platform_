from __future__ import annotations
import json
from api import Graph, VisualizerPlugin


class SimpleVisualizerPlugin(VisualizerPlugin):
    """
    Simple visualizer — displays each node as a circle with a single label.

    The label is the first attribute value of the node, or the node_id
    if the node has no attributes.

    Uses D3.js force layout. Returns an HTML <script> string that
    the Django/Flask template injects into the page. At the end,
    calls GraphVisualizer.mount(svg.node(), sim) so the platform
    can attach the SVG to the correct container.
    """

    def get_name(self) -> str:
        return "Simple"

    def get_parameters(self):
        return []

    def render(self, graph: Graph) -> str:
        nodes, links = self._build_data(graph)
        nodes_json = json.dumps(nodes)
        links_json = json.dumps(links)

        return f"""
<script>
(function () {{

  const nodes = {nodes_json};
  const links = {links_json};

  const radius = 30;

  const svg = d3.create("svg")
    .attr("width", 800)
    .attr("height", 600);

  // Arrow marker for directed edges
  svg.append("defs").append("marker")
    .attr("id", "arrow")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", radius + 10)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#999");

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(120))
    .force("charge", d3.forceManyBody().strength(-350))
    .force("collide", d3.forceCollide(radius + 10))
    .force("center", d3.forceCenter(400, 300));

  const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("class", "link")
    .attr("stroke", "#999")
    .attr("stroke-width", 2)
    .attr("marker-end", d => d.directed ? "url(#arrow)" : null);

  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", "node");

  node.append("circle")
    .attr("r", radius)
    .attr("fill", "#5B9BD5")
    .attr("stroke", "#2E75B6")
    .attr("stroke-width", 2);

  node.append("text")
    .attr("text-anchor", "middle")
    .attr("dominant-baseline", "central")
    .attr("font-size", 12)
    .attr("font-family", "sans-serif")
    .attr("fill", "#FFF")
    .attr("stroke", "#000")
    .attr("stroke-width", 0.5)
    .attr("pointer-events", "none")
    .text(d => d.label);

  sim.on("tick", () => {{
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d => `translate(${{d.x}}, ${{d.y}})`);
  }});

  GraphVisualizer.mount(svg.node(), sim);

}})();
</script>
"""

    def _build_data(self, graph: Graph):
        """
        Converts Graph to D3-compatible nodes and links.

        Node label is the first attribute value, or node_id if no attributes.
        Link source/target reference node_id strings.
        """
        nodes = []
        for node in graph.get_all_nodes():
            if node.attributes:
                first_value = next(iter(node.attributes.values()))
                label = str(first_value)
            else:
                label = node.node_id

            nodes.append({
                "id":    node.node_id,
                "label": label,
            })

        links = []
        for edge in graph.get_all_edges():
            links.append({
                "source":   edge.source.node_id,
                "target":   edge.target.node_id,
                "directed": edge.directed,
            })

        return nodes, links