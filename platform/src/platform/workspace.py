from __future__ import annotations
from typing import Any, Dict, List, Optional

from api import Graph, DataSourcePlugin, VisualizerPlugin
from .graph_service import GraphService, FilterParseError, FilterTypeError


class Workspace:
    """
    Represents a single user workspace.

    A workspace holds:
    - The base graph (loaded from a data source, never modified)
    - The current graph (result of applied search/filter operations)
    - The active data source plugin
    - The active visualizer plugin
    - The query history (list of applied searches and filters)

    The platform can hold multiple workspaces simultaneously.
    Django/Flask views create and manage Workspace instances.
    """

    def __init__(self, workspace_id: str, name: str = ""):
        self.workspace_id: str = workspace_id
        self.name: str = name

        self._base_graph:  Optional[Graph] = None
        self._graph:       Optional[Graph] = None
        self._data_source: Optional[DataSourcePlugin] = None
        self._visualizer:  Optional[VisualizerPlugin] = None

        self._queries: List[Dict[str, Any]] = []

    def set_data_source(self, plugin: DataSourcePlugin) -> None:
        if not isinstance(plugin, DataSourcePlugin):
            raise TypeError("Expected a DataSourcePlugin instance.")
        self._data_source = plugin

    def set_visualizer(self, plugin: VisualizerPlugin) -> None:
        if not isinstance(plugin, VisualizerPlugin):
            raise TypeError("Expected a VisualizerPlugin instance.")
        self._visualizer = plugin

    def load_and_render(self, params: Dict[str, Any]) -> str:
        """
        Loads a graph from the active data source plugin and renders it.
        Resets all previously applied queries.
        """
        self._require_data_source()
        self._require_visualizer()

        self._base_graph = self._data_source.load(params)
        self._graph = self._base_graph
        self._queries = []

        return self._visualizer.render(self._graph)

    def render(self) -> str:
        """Re-renders the current graph without reloading data."""
        self._require_visualizer()
        self._require_graph()
        return self._visualizer.render(self._graph)

    def apply_query(self, query: Dict[str, Any]) -> str:
        """
        Applies a search or filter query on top of the current graph.
        Queries are cumulative — each one narrows the current graph further.
        The base graph is never modified.
        """
        self._require_visualizer()
        self._require_graph()

        query_type = query.get("type")

        if query_type == "search":
            text = query.get("text", "")
            self._graph = GraphService.search(self._graph, text)

        elif query_type == "filter":
            expression = query.get("expression", "")
            self._graph = GraphService.filter(self._graph, expression)

        else:
            raise ValueError(
                f"Unknown query type: '{query_type}'. "
                f"Expected 'search' or 'filter'."
            )

        self._queries.append(query)
        return self._visualizer.render(self._graph)

    def undo_query(self) -> str:
        """Removes the last applied query and rebuilds the graph from scratch."""
        self._require_visualizer()
        self._require_graph()

        if not self._queries:
            raise WorkspaceError("No queries to undo.")

        self._queries.pop()
        self._rebuild_graph()
        return self._visualizer.render(self._graph)

    def reset(self) -> str:
        """Clears all applied queries and returns to the base graph."""
        self._require_visualizer()
        self._require_graph()

        self._queries = []
        self._graph = self._base_graph
        return self._visualizer.render(self._graph)

    def _rebuild_graph(self) -> None:
        """Replays all queries from scratch on the base graph."""
        current = self._base_graph
        for query in self._queries:
            if query["type"] == "search":
                current = GraphService.search(current, query["text"])
            elif query["type"] == "filter":
                current = GraphService.filter(current, query["expression"])
        self._graph = current

    def execute_cli(self, command: str) -> str:
        """Executes a CLI command on the base graph."""
        from .cli import CLI, InvalidCommandError

        self._require_graph()

        result = CLI.parse_command(self._base_graph, command)

        if result.startswith("__search__:"):
            text = result[len("__search__:"):]
            return self.apply_query({"type": "search", "text": text})

        if result.startswith("__filter__:"):
            expression = result[len("__filter__:"):]
            return self.apply_query({"type": "filter", "expression": expression})

        self._rebuild_graph()
        return result


    @property
    def graph(self) -> Optional[Graph]:
        """The current (possibly filtered) graph."""
        return self._graph

    @property
    def base_graph(self) -> Optional[Graph]:
        """The original unmodified graph as loaded by the data source."""
        return self._base_graph

    @property
    def queries(self) -> List[Dict[str, Any]]:
        """Read-only list of applied queries."""
        return list(self._queries)

    @property
    def data_source(self) -> Optional[DataSourcePlugin]:
        return self._data_source

    @property
    def visualizer(self) -> Optional[VisualizerPlugin]:
        return self._visualizer

    def is_loaded(self) -> bool:
        return self._graph is not None

    def _require_data_source(self) -> None:
        if self._data_source is None:
            raise WorkspaceError(
                "No data source plugin selected. "
                "Call set_data_source() first."
            )

    def _require_visualizer(self) -> None:
        if self._visualizer is None:
            raise WorkspaceError(
                "No visualizer plugin selected. "
                "Call set_visualizer() first."
            )

    def _require_graph(self) -> None:
        if self._graph is None:
            raise WorkspaceError(
                "No graph loaded. "
                "Call load_and_render() first."
            )

    def __repr__(self) -> str:
        return (
            f"Workspace("
            f"id={self.workspace_id!r}, "
            f"name={self.name!r}, "
            f"loaded={self.is_loaded()}, "
            f"queries={len(self._queries)}"
            f")"
        )


class WorkspaceError(Exception):
    """Raised when a workspace operation cannot be performed."""
    pass