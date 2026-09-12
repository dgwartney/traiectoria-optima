"""The whole route network as one batched, deduplicated layer."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .geodesic import Geodesic
from .layer import MapLayer
from .palette import Palette


class NetworkLayer(MapLayer):
    """Every route in a catalog, as a single `GeoJson` layer.

    Folium emits a JavaScript statement per `PolyLine`, so drawing the world
    network one line at a time costs 109 MB of saved HTML against this class's
    4.6 MB. The saving is entirely in how the geometry is packaged and in
    drawing each city pair once -- not in drawing less. Three contributions,
    all measured in `docs/visualization.md`:

    - one `GeoJson` instead of N `PolyLine`s: 109.21 MB -> 38.82 MB
    - 6 interpolated segments instead of 24: -> 17.92 MB
    - one feature per airport pair instead of per route row: -> 4.61 MB

    The layer starts hidden. That is not only about size: the context buries
    the answer it sits under, and the reader can switch it on when the
    question is "what else was available?".
    """

    def __init__(
        self,
        routes: Iterable,
        geodesic: Optional[Geodesic] = None,
        palette: Optional[Palette] = None,
        *,
        name: str = "All routes",
        decimals: int = 3,
        weight: float = 1.0,
        opacity: float = 0.3,
    ) -> None:
        """Create a network layer.

        Args:
            routes: `Route` objects to draw. Collapsed to distinct airport
                pairs at build time.
            geodesic: Interpolator. Defaults to 6 segments, which is
                indistinguishable from 24 at this line weight.
            palette: Colours to draw with. Uses the scenery colour, never a
                series slot.
            name: Label for the layer control.
            decimals: Coordinate rounding. Three places is about 110 m.
            weight: Line width in pixels.
            opacity: Line opacity, low so the context recedes.
        """
        self._routes = tuple(routes)
        self._geodesic = geodesic or Geodesic(segments=6)
        self._palette = palette or Palette()
        self._name = name
        self._decimals = decimals
        self._weight = weight
        self._opacity = opacity
        self._drawn: List[List[float]] = []

    def name(self) -> str:
        """Return the label shown in the layer control."""
        return self._name

    def show(self) -> bool:
        """Report that this layer starts switched off."""
        return False

    def drawn_points(self) -> Sequence[Sequence[float]]:
        """Return every `[lat, lon]` drawn, longitudes as drawn."""
        return self._drawn

    def distinct_pairs(self) -> Dict[Tuple[str, str], Any]:
        """Collapse route rows to one per unordered airport pair.

        The route table is keyed by flight number, so the committed world
        snapshot's 66,332 rows are only 18,814 pairs. Drawing per row paints
        the same line three or four times over -- paying for it in file size
        each time, and darkening it on screen in a way that misrepresents the
        geometry. Collapsing is both the cheaper and the more truthful choice.

        Returns:
            Mapping of sorted `(origin, destination)` IATA pair to one
            representative `Route`.
        """
        seen: Dict[Tuple[str, str], Any] = {}
        for route in self._routes:
            key = tuple(
                sorted((route.origin.iata_code, route.destination.iata_code))
            )
            seen.setdefault(key, route)
        return seen

    def build(self, folium: Any) -> Any:
        """Build one `GeoJson` layer covering every distinct pair.

        Args:
            folium: The folium module.

        Returns:
            A `folium.GeoJson`.
        """
        self._drawn = []
        features = []

        for key, route in self.distinct_pairs().items():
            points = self._geodesic.between(route.origin, route.destination)
            self._collect(points, self._drawn)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        # GeoJSON is [lon, lat]; folium.PolyLine takes
                        # [lat, lon]. Easiest thing here to get backwards,
                        # and the hardest to see once it is wrong.
                        "coordinates": [
                            [
                                round(longitude, self._decimals),
                                round(latitude, self._decimals),
                            ]
                            for latitude, longitude in points
                        ],
                    },
                    "properties": {
                        "label": "-".join(key),
                        "km": round(route.distance_km),
                    },
                }
            )

        style = {
            "color": self._palette.context(),
            "weight": self._weight,
            "opacity": self._opacity,
        }
        return folium.GeoJson(
            {"type": "FeatureCollection", "features": features},
            name=self.name(),
            show=self.show(),
            style_function=lambda _feature: style,
            # Batching does not cost the per-route tooltip, which is the
            # obvious worry about collapsing into one layer.
            tooltip=folium.GeoJsonTooltip(fields=["label", "km"]),
        )
