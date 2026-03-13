from __future__ import annotations
import json
from api import Graph, VisualizerPlugin


class BlockVisualizerPlugin(VisualizerPlugin):
    """
    Block visualizer — displays each node as a rectangle with all
    attributes listed inside it.

    Uses D3.js force layout. Returns an HTML <script> string that
    the Django/Flask template injects into the page. At the end,
    calls GraphVisualizer.mount(svg.node(), sim) so the platform
    can attach the SVG to the correct container.
    """

    def get_name(self) -> str:
        return "Block"

    def render(self, graph: Graph) -> str:
        nodes, links = self._build_data(graph)
        nodes_json = json.dumps(nodes)
        links_json = json.dumps(links)

        return f"""
<script>
(function () {{

  const nodes = {nodes_json};
  const links = {links_json};

  const rectWidth  = 160;
  const lineHeight = 18;

  // Each node rect height depends on number of attribute lines
  function rectHeight(d) {{
    return 28 + d.attrs.length * lineHeight;
  }}

  const svg = d3.create("svg")
    .attr("width", 800)
    .attr("height", 600);

  // Arrow marker for directed edges
  svg.append("defs").append("marker")
    .attr("id", "arrow-block")
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 10)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", "#999");

  const sim = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(180))
    .force("charge", d3.forceManyBody().strength(-500))
    .force("collide", d3.forceCollide(100))
    .force("center", d3.forceCenter(400, 300));

  const link = svg.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("class", "link")
    .attr("stroke", "#999")
    .attr("stroke-width", 2)
    .attr("marker-end", d => d.directed ? "url(#arrow-block)" : null);

  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", "node");

  // Rectangle background
  node.append("rect")
    .attr("width", rectWidth)
    .attr("height", d => rectHeight(d))
    .attr("rx", 6)
    .attr("ry", 6)
    .attr("fill", "#87CEEB")
    .attr("stroke", "#2E75B6")
    .attr("stroke-width", 1.5);

  // Header line separator
  node.append("line")
    .attr("x1", 0)
    .attr("y1", 24)
    .attr("x2", rectWidth)
    .attr("y2", 24)
    .attr("stroke", "#2E75B6")
    .attr("stroke-width", 1);

  // Node id / name in header
  node.append("text")
    .attr("x", rectWidth / 2)
    .attr("y", 16)
    .attr("text-anchor", "middle")
    .attr("font-size", 13)
    .attr("font-weight", "bold")
    .attr("font-family", "sans-serif")
    .attr("fill", "#000")
    .attr("pointer-events", "none")
    .text(d => d.label);

  // Attribute lines
  node.each(function(d) {{
    d.attrs.forEach((attr, i) => {{
      d3.select(this).append("text")
        .attr("x", 8)
        .attr("y", 28 + lineHeight * i + 13)
        .attr("font-size", 11)
        .attr("font-family", "sans-serif")
        .attr("fill", "#000")
        .attr("pointer-events", "none")
        .text(attr);
    }});
  }});

  sim.on("tick", () => {{
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d =>
      `translate(${{d.x - rectWidth / 2}}, ${{d.y - rectHeight(d) / 2}})`
    );
  }});

  GraphVisualizer.mount(svg.node(), sim);

}})();
</script>
"""

    def _build_data(self, graph: Graph):
        """
        Converts Graph to D3-compatible nodes and links.

        Each node gets:
          - id: node_id string
          - label: first attribute value or node_id if no attributes
          - attrs: list of "key: value" strings for all attributes

        Links reference node_id strings.
        """
        nodes = []
        for node in graph.get_all_nodes():
            attrs = [
                f"{k}: {v}"
                for k, v in node.attributes.items()
            ]

            if node.attributes:
                label = str(next(iter(node.attributes.values())))
            else:
                label = node.node_id

            nodes.append({
                "id":    node.node_id,
                "label": label,
                "attrs": attrs,
            })

        links = []
        for edge in graph.get_all_edges():
            links.append({
                "source":   edge.source.node_id,
                "target":   edge.target.node_id,
                "directed": edge.directed,
            })

        return nodes, links