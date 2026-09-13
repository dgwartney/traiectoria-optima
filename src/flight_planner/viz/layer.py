"""The interface every drawable map layer implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Sequence


class MapLayer(ABC):
    """One named, toggleable layer on a `RouteMap`.

    Subclasses decide what they draw and how they package it: `PathLayer`
    emits a `PolyLine` per leg because each leg has its own tooltip and there
    are only a few, while `NetworkLayer` collapses thousands of routes into a
    single `GeoJson`. Same interface, different `build`, and no size threshold
    branching anywhere.

    `drawn_points` is not incidental. Great-circle geometry crossing the
    antimeridian is drawn with longitudes carried past ±180, which puts it
    *outside* the bounding box of its own endpoints -- so a map that framed
    itself on airport positions would frame the line out of view. A layer that
    cannot report what it drew cannot be framed correctly, so the interface
    requires it.
    """

    @abstractmethod
    def name(self) -> str:
        """Return the label shown in the layer control.

        Returns:
            Human-readable name. Implementations are encouraged to carry the
            finding -- `"Dijkstra (8,072 km)"` rather than `"Dijkstra"` -- so
            the legend states the result instead of naming a colour.
        """
        raise NotImplementedError

    @abstractmethod
    def build(self, folium: Any) -> Any:
        """Build the folium object to add to the map.

        Args:
            folium: The folium module itself, passed in rather than imported,
                so the lazy-import guard lives in exactly one place and a test
                can build a layer without the package-level import dance.

        Returns:
            A folium object accepted by `Map.add_child`.
        """
        raise NotImplementedError

    @abstractmethod
    def drawn_points(self) -> Sequence[Sequence[float]]:
        """Return every `[lat, lon]` this layer actually drew.

        Called after `build`. Longitudes are as drawn, which for a dateline
        route means outside `[-180, 180]`.

        Returns:
            Sequence of `[lat, lon]` pairs, empty before `build` runs.
        """
        raise NotImplementedError

    def show(self) -> bool:
        """Report whether the layer starts visible.

        Returns:
            `True`. Overridden by `NetworkLayer`, whose context is rarely what
            the experiment is about.
        """
        return True

    @staticmethod
    def _collect(points: Sequence[Sequence[float]], into: List[List[float]]) -> None:
        """Accumulate drawn points onto a layer's own list."""
        into.extend([latitude, longitude] for latitude, longitude in points)
