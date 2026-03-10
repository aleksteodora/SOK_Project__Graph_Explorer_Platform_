from __future__ import annotations
from typing import Dict, List
from importlib.metadata import entry_points

from api import DataSourcePlugin, VisualizerPlugin


class PluginRegistry:

    DATA_SOURCE_GROUP = "graph.data_source"
    VISUALIZER_GROUP  = "graph.visualizer"

    def __init__(self):
        self._data_sources: Dict[str, DataSourcePlugin] = {}
        self._visualizers:  Dict[str, VisualizerPlugin] = {}

    def load(self) -> None:
        self._data_sources = self._load_group(
            self.DATA_SOURCE_GROUP, DataSourcePlugin
        )
        self._visualizers = self._load_group(
            self.VISUALIZER_GROUP, VisualizerPlugin
        )

    def _load_group(
        self,
        group: str,
        expected_type: type
    ) -> Dict[str, object]:
        loaded = {}

        eps = entry_points(group=group)
        for ep in eps:
            try:
                plugin_class = ep.load()
                if not issubclass(plugin_class, expected_type):
                    print(
                        f"[PluginRegistry] Warning: '{ep.name}' in group "
                        f"'{group}' does not subclass {expected_type.__name__}. "
                        f"Skipping."
                    )
                    continue
                loaded[ep.name] = plugin_class()
            except Exception as e:
                print(
                    f"[PluginRegistry] Warning: failed to load plugin "
                    f"'{ep.name}' from group '{group}': {e}"
                )

        return loaded

    def get_data_sources(self) -> List[DataSourcePlugin]:
        return list(self._data_sources.values())

    def get_data_source(self, name: str) -> DataSourcePlugin:
        if name not in self._data_sources:
            available = list(self._data_sources.keys())
            raise KeyError(
                f"Data source plugin '{name}' not found. "
                f"Available: {available}"
            )
        return self._data_sources[name]

    def get_data_source_names(self) -> List[str]:
        return list(self._data_sources.keys())

    def get_visualizers(self) -> List[VisualizerPlugin]:
        return list(self._visualizers.values())

    def get_visualizer(self, name: str) -> VisualizerPlugin:
        if name not in self._visualizers:
            available = list(self._visualizers.keys())
            raise KeyError(
                f"Visualizer plugin '{name}' not found. "
                f"Available: {available}"
            )
        return self._visualizers[name]

    def get_visualizer_names(self) -> List[str]:
        return list(self._visualizers.keys())

    def __repr__(self) -> str:
        return (
            f"PluginRegistry("
            f"data_sources={self.get_data_source_names()}, "
            f"visualizers={self.get_visualizer_names()}"
            f")"
        )