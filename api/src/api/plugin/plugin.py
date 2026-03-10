from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..model.graph import Graph


class PluginParameter:
    """
    Describes a single input parameter that a plugin requires from the user.

    The platform uses this list to automatically generate an HTML form
    for the plugin — no hardcoded forms needed in Django or Flask views.
    """

    def __init__(
        self,
        name: str,
        label: str,
        required: bool = True,
        default: Any = None
    ):
        self.name: str = name
        self.label: str = label
        self.required: bool = required
        self.default: Any = default

    def __repr__(self) -> str:
        return (
            f"PluginParameter(name={self.name!r}, label={self.label!r}, "
            f"required={self.required}, default={self.default!r})"
        )


class DataSourcePlugin(ABC):
    """
    Abstract base class for all data source plugins.

    A data source plugin is responsible for reading data from some source
    (JSON file, XML file, CSV file, database, API...) and returning a
    populated Graph object.

    The plugin knows nothing about how the graph will be visualized or
    how it will be displayed in the browser — that is the visualizer's job.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the human-readable name of this plugin."""
        pass

    @abstractmethod
    def get_parameters(self) -> List[PluginParameter]:
        """Returns the list of parameters this plugin needs from the user."""
        pass

    @abstractmethod
    def load(self, params: Dict[str, Any]) -> Graph:
        """Reads data from the source and returns a populated Graph."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.get_name()!r})"


class VisualizerPlugin(ABC):
    """
    Abstract base class for all visualizer plugins.

    A visualizer plugin receives a Graph object and returns a complete
    HTML string that renders the graph visually in the browser.

    The HTML string is injected directly into the Django/Flask template.
    It typically contains an inline <script> with D3.js or similar.

    The plugin knows nothing about where the data came from — it only
    knows how to draw a Graph object.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Returns the human-readable name of this visualizer."""
        pass

    @abstractmethod
    def render(self, graph: Graph) -> str:
        """Renders the graph and returns a complete HTML string."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.get_name()!r})"