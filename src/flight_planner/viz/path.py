"""One answer -- a sequence of legs -- as a highlighted path."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .geodesic import Geodesic
from .layer import MapLayer
from .palette import Palette


class PathLayer(MapLayer):
    """A route's legs as a highlighted polyline per leg.

    Deliberately *not* batched the way `NetworkLayer` is. A path is a handful
    of legs, each with its own tooltip, and the count is small enough that one
    `PolyLine` each costs nothing -- while giving every leg its own hover
    label, which a single feature could not.

    The layer name carries the finding: `"Dijkstra (8,072 km)"`, and when
    built from a `SearchResult`, `"Dijkstra (8,072 km, 746 expanded)"`. A
    legend that restates the answer is worth more than one naming a colour.
    """

    def __init__(
        self,
        legs: Sequence,
        geodesic: Optional[Geodesic] = None,
        palette: Optional[Palette] = None,
        *,
        name: Optional[str] = None,
        weight: float = 3.5,
        opacity: float = 0.9,
        annotation: str = "",
    ) -> None:
        """Create a path layer.

        Args:
            legs: `Route` objects in travel order.
            geodesic: Interpolator. Defaults to 24 segments -- a path is drawn
                thick enough that a coarser curve shows its faceting.
            palette: Colours to draw with. `name` keys the series colour.
            name: Layer label. Defaults to the airport codes along the path.
            weight: Line width in pixels.
            opacity: Line opacity.
            annotation: Extra text for the label, e.g. `"746 expanded"`.
        """
        self._legs = tuple(legs)
        self._geodesic = geodesic or Geodesic(segments=24)
        self._palette = palette or Palette()
        self._name = name
        self._weight = weight
        self._opacity = opacity
        self._annotation = annotation
        self._drawn: List[List[float]] = []

    @classmethod
    def from_result(
        cls,
        result: Any,
        palette: Optional[Palette] = None,
        *,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> "PathLayer":
        """Create a path layer from a `SearchResult`, keeping its counters.

        The counters are what the project's central claim is about -- A*
        reaching the same answer while expanding far fewer nodes -- so a layer
        built this way says so in the legend.

        Args:
            result: A `SearchResult`, or anything with `.path` and optionally
                `.nodes_expanded`.
            palette: Colours to draw with.
            name: Layer label, usually the algorithm name.
            **kwargs: Passed through to `__init__`.

        Returns:
            A `PathLayer` over `result.path`.
        """
        expanded = getattr(result, "nodes_expanded", None)
        annotation = f"{expanded:,} expanded" if expanded is not None else ""
        return cls(
            result.path, palette=palette, name=name, annotation=annotation, **kwargs
        )

    def name(self) -> str:
        """Return the label shown in the layer control.

        A named layer is prefixed with the pair it answers -- `"HNL-BDL ·
        Dijkstra (8,072 km, 1,019 expanded)"`. Without it, a map comparing
        algorithms over *two* pairs shows `"Dijkstra"` twice and `"BFS"` twice,
        and the only thing telling the duplicates apart is a kilometre figure
        the reader would have to already know the answer to. The endpoints are
        also what the layers of one comparison share, so leading with them
        groups each pair's layers together as the eye runs down the control.

        The pair is the endpoints, not every stop: intermediate airports differ
        per algorithm, which would break that grouping, and they are already in
        each leg's own hover tooltip. An *unnamed* layer gets no prefix,
        because its fallback name is the airport codes and `"SFO-BOS ·
        SFO-DEN-BOS"` says it twice.

        Returns:
            The given name prefixed by its endpoints, or the airport codes
            along the path, followed by the kilometre total and any annotation.
        """
        label = f"{self._pair()} · {self._name}" if self._name and self._legs else (
            self._name or self._codes()
        )
        parts = [f"{self.distance_km():,.0f} km"] if self._legs else []
        if self._annotation:
            parts.append(self._annotation)
        return f"{label} ({', '.join(parts)})" if parts else label

    def _pair(self) -> str:
        """Return the endpoints of the whole path, e.g. `SFO-BOS`."""
        return (
            f"{self._legs[0].origin.iata_code}-"
            f"{self._legs[-1].destination.iata_code}"
        )

    def distance_km(self) -> float:
        """Return the total distance along the path."""
        return sum(leg.distance_km for leg in self._legs)

    def drawn_points(self) -> Sequence[Sequence[float]]:
        """Return every `[lat, lon]` drawn, longitudes as drawn.

        For a leg crossing the antimeridian these run past ±180, which is what
        `RouteMap` needs in order to frame the line rather than exclude it.
        """
        return self._drawn

    def build(self, folium: Any) -> Any:
        """Build a feature group of one polyline per leg.

        Args:
            folium: The folium module.

        Returns:
            A `folium.FeatureGroup`.
        """
        group = folium.FeatureGroup(name=self.name(), show=self.show())
        colour = self._colour()
        self._drawn = []
        previous_end = None

        for leg in self._legs:
            points = self._geodesic.between(leg.origin, leg.destination)
            points = self._join(points, previous_end)
            previous_end = points[-1][1]
            self._collect(points, self._drawn)
            folium.PolyLine(
                points,
                color=colour,
                weight=self._weight,
                opacity=self._opacity,
                tooltip=(
                    f"{leg.origin.iata_code}-{leg.destination.iata_code} "
                    f"{leg.distance_km:,.0f} km"
                ),
            ).add_to(group)

        return group

    @staticmethod
    def _join(points, previous_end):
        """Shift a leg into the same copy of the world as the leg before it.

        `Geodesic` unwraps within one leg, starting from that leg's own origin.
        A path made of several legs therefore arrives in pieces that are each
        continuous but not continuous with each other: SYD→LAX unwraps to end
        at 241.6°, and LAX→JFK then starts again at its raw −118.4°, a 360°
        jump. Leaflet draws that as a line back across the map, and the map
        frames itself over 404° of longitude.

        Args:
            points: One leg's `[lat, lon]` points, already unwrapped.
            previous_end: Longitude the previous leg finished at, or `None`
                for the first leg.

        Returns:
            The same points, shifted by a whole number of turns so the leg
            begins within 180° of where the last one ended.
        """
        if previous_end is None or not points:
            return points
        turns = round((previous_end - points[0][1]) / 360)
        if not turns:
            return points
        shift = turns * 360
        return [[latitude, longitude + shift] for latitude, longitude in points]

    def _codes(self) -> str:
        """Return the airport codes along the path, e.g. `SFO-DEN-BOS`."""
        if not self._legs:
            return "Path"
        return "-".join(
            [self._legs[0].origin.iata_code]
            + [leg.destination.iata_code for leg in self._legs]
        )

    def _colour(self) -> str:
        """Return the palette colour for this layer's name.

        A path named for something that is not an algorithm -- `"Great
        circle"`, say -- is legitimate, so an unknown name falls back to the
        scenery colour rather than raising. `Palette.series` still raises for
        callers asking for a series colour directly, which is where a typo in
        an algorithm name actually matters.
        """
        try:
            return self._palette.series(self._name) if self._name else (
                self._palette.context()
            )
        except KeyError:
            return self._palette.context()
