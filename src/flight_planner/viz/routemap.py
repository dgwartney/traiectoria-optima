"""Composes layers into one folium map, and frames it on what was drawn."""

from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

from .airports import AirportLayer
from .geodesic import Geodesic
from .layer import MapLayer
from .network import NetworkLayer
from .palette import Palette
from .path import PathLayer

# Every style in these families renders either an `API KEY REQUIRED` watermark
# across each tile (Carto) or HTTP 401 for every tile request (Stadia), as of
# folium 0.20.0. Refused at construction rather than discovered after a map is
# already in a report. `xyzservices` reports the Stadia providers as needing no
# token, so provider metadata is not a substitute for fetching a tile.
KEYED_TILE_FAMILIES = ("cartodb", "carto", "stadia", "stamen")

# THE SECOND TILE TRAP, and the one that is not about keys at all.
#
# `OpenStreetMap` needs no API key, which is why it is the default above -- but
# it does need the request to be attributable. OSM's tile usage policy blocks
# traffic it cannot tie to an identified app, and it enforces that on the
# `Referer` header: a page served over HTTP sends one and gets real tiles,
# while the *same file opened from `file://`* sends none and gets a tile
# reading `403 / Access blocked / App is not following the tile usage policy`.
#
# That block arrives as **HTTP 200 with a PNG body**, so nothing raises,
# nothing logs, and the map renders perfectly with every tile replaced by a
# notice. It cannot be caught by checking status codes; only by looking.
#
# The consequence for this project: a *committed* map that a reader opens by
# double-clicking has no `Referer` and so cannot use OSM. Esri's World Light
# Gray Base needs neither a key nor a referer, and being a desaturated canvas
# it also keeps a basemap from competing with the arcs drawn on it. Measured
# 2026-09-15: a generic-browser-UA request with no `Referer` returns a real
# tile from Esri and the block notice from OSM.
#
# NOT VERIFIED: whether Esri's terms of service permit this use outside their
# own SDKs. It demonstrably works; that is a different claim from being
# allowed, and this file is the wrong place to guess at the difference. See
# `docs/visualization.md` section 9.
ESRI_LIGHT_GRAY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
    "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)
ESRI_LIGHT_GRAY_ATTRIBUTION = (
    "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
)

# A world view, used only until something is drawn and the bounds take over.
DEFAULT_LOCATION = (20.0, 0.0)
DEFAULT_ZOOM = 2


class RouteMap:
    """A folium map built up in named, toggleable layers.

    Each fluent call appends one `MapLayer`; `finish()` builds them, frames the
    map on every point they drew, and attaches the layer control. The value of
    a notebook cell renders directly, so the common case never has to remember
    `finish()`.

    Attributes:
        tiles: Basemap style. Only `OpenStreetMap` works without an API key.
        layers: The `MapLayer` objects added so far, in order.
    """

    def __init__(
        self,
        tiles: str = "OpenStreetMap",
        palette: Optional[Palette] = None,
        *,
        attribution: Optional[str] = None,
        basemap_name: Optional[str] = None,
        path_segments: int = 24,
        context_segments: int = 6,
    ) -> None:
        """Create an empty map.

        Args:
            tiles: Basemap style, or a tile URL template such as
                `ESRI_LIGHT_GRAY`. The default needs no API key but *does*
                need a `Referer`, so a map saved for a reader to open from
                `file://` should pass `ESRI_LIGHT_GRAY` instead -- see the
                comment on that constant.
            palette: Colours for every layer added. Defaults to the light
                surface, which is what the report and GitHub use.
            attribution: Credit line for a tile URL template. Required by
                folium for anything that is not a named style, and required
                by every tile provider's terms regardless.
            basemap_name: Label for the basemap in the layer control. Worth
                setting whenever `tiles` is a URL template, because folium
                otherwise labels it with the entire URL.
            path_segments: Interpolation for `path()` layers. A thick line
                shows its faceting, so it gets the finer curve.
            context_segments: Interpolation for `routes()` layers, where 6 is
                indistinguishable from 24 and 2.2x smaller.

        Raises:
            ValueError: If `tiles` names a style that needs an API key, or if
                a tile URL template is passed with no attribution.
        """
        self._reject_keyed_tiles(tiles)
        self._reject_unattributed_tiles(tiles, attribution)
        self.tiles = tiles
        self.attribution = attribution
        self.basemap_name = basemap_name or (
            tiles if isinstance(tiles, str) and "{z}" not in tiles else "Basemap"
        )
        self.layers: List[MapLayer] = []
        self._palette = palette or Palette()
        self._path_geodesic = Geodesic(segments=path_segments)
        self._context_geodesic = Geodesic(segments=context_segments)
        self._drawn: List[List[float]] = []
        self._map = None

    @staticmethod
    def _reject_keyed_tiles(tiles: str) -> None:
        """Refuse tile styles that render a watermark or 401 without a key."""
        if not isinstance(tiles, str):
            return
        lowered = tiles.lower()
        if any(family in lowered for family in KEYED_TILE_FAMILIES):
            raise ValueError(
                f"{tiles!r} needs an API key: Carto styles render an "
                "'API KEY REQUIRED' watermark across every tile and Stadia "
                "styles return HTTP 401. Use 'OpenStreetMap', or pass a "
                "folium.TileLayer carrying your own key."
            )

    @staticmethod
    def _reject_unattributed_tiles(
        tiles: str, attribution: Optional[str]
    ) -> None:
        """Refuse a tile URL template with no credit line.

        folium raises deep inside `Map` for this, by which point the message
        says nothing about which call was wrong. Refused here instead, and
        refused rather than defaulted because inventing a credit line for
        someone else's tiles is worse than failing.
        """
        if not isinstance(tiles, str) or attribution:
            return
        if "{z}" in tiles or "//" in tiles:
            raise ValueError(
                f"{tiles!r} is a tile URL template, so it needs an "
                "attribution= credit line. Every provider's terms require "
                "one; pass ESRI_LIGHT_GRAY_ATTRIBUTION with ESRI_LIGHT_GRAY."
            )

    # --- building -------------------------------------------------------

    def add(self, layer: MapLayer) -> "RouteMap":
        """Add a pre-built layer.

        Args:
            layer: Any `MapLayer`.

        Returns:
            This map, for chaining.
        """
        self.layers.append(layer)
        self._map = None
        return self

    def airports(self, airports: Iterable, **kwargs: Any) -> "RouteMap":
        """Add an airport marker layer.

        Args:
            airports: `Airport` objects to draw.
            **kwargs: Passed to `AirportLayer`.

        Returns:
            This map, for chaining.
        """
        return self.add(AirportLayer(airports, self._palette, **kwargs))

    def routes(self, routes: Iterable, **kwargs: Any) -> "RouteMap":
        """Add the whole-network context layer, switched off.

        Args:
            routes: `Route` objects to draw.
            **kwargs: Passed to `NetworkLayer`.

        Returns:
            This map, for chaining.
        """
        kwargs.setdefault("geodesic", self._context_geodesic)
        return self.add(NetworkLayer(routes, palette=self._palette, **kwargs))

    def path(self, legs: Sequence, **kwargs: Any) -> "RouteMap":
        """Add a highlighted path layer.

        Args:
            legs: `Route` objects in travel order.
            **kwargs: Passed to `PathLayer`, notably `name`, which keys the
                palette and labels the layer control.

        Returns:
            This map, for chaining.
        """
        kwargs.setdefault("geodesic", self._path_geodesic)
        return self.add(PathLayer(legs, palette=self._palette, **kwargs))

    def result(self, search_result: Any, **kwargs: Any) -> "RouteMap":
        """Add a path layer from a `SearchResult`, keeping its counters.

        Args:
            search_result: A `SearchResult`, or anything with `.path`.
            **kwargs: Passed to `PathLayer.from_result`.

        Returns:
            This map, for chaining.
        """
        kwargs.setdefault("geodesic", self._path_geodesic)
        return self.add(
            PathLayer.from_result(search_result, palette=self._palette, **kwargs)
        )

    # --- finishing ------------------------------------------------------

    def finish(self) -> Any:
        """Build every layer, frame the map, and attach the layer control.

        Idempotent: calling it twice rebuilds rather than stacking duplicate
        layers, so a notebook can render the same object repeatedly.

        Returns:
            The `folium.Map`.
        """
        folium = _folium()
        # A URL template has to be wrapped in a `TileLayer` to get a readable
        # label. `folium.Map` builds its own `TileLayer` internally and names
        # it from the tile string, so a `name=` passed to `Map` is silently
        # ignored -- it lands in `**kwargs`, renders somewhere harmless, and
        # leaves the whole tile URL sitting in the layer control, which on a
        # faceted map is the legend. `Map` does accept a prebuilt `TileLayer`,
        # and that is the supported way to name one.
        #
        # A named style keeps the original code path exactly, so every map
        # that predates this renders unchanged.
        tiles: Any = self.tiles
        if self.attribution is not None:
            tiles = folium.TileLayer(
                tiles=self.tiles,
                attr=self.attribution,
                name=self.basemap_name,
            )

        self._map = folium.Map(
            tiles=tiles,
            location=list(DEFAULT_LOCATION),
            zoom_start=DEFAULT_ZOOM,
        )
        self._drawn = []

        built = [(layer, layer.build(folium)) for layer in self.layers]

        # Lines are drawn in unwrapped longitude space, so markers have to be
        # moved into the same frame or they land in a different copy of the
        # world and fall outside a map framed past +/-180.
        line_points = [
            point
            for layer, _ in built
            if not isinstance(layer, AirportLayer)
            for point in layer.drawn_points()
        ]
        centre = self._centre(line_points)

        for layer, obj in built:
            if isinstance(layer, AirportLayer) and centre is not None:
                self._align_markers(obj, centre)
            self._map.add_child(obj)
            self._drawn.extend(
                self._aligned(layer, layer.drawn_points(), centre)
            )

        bounds = self.bounds()
        if bounds is not None:
            self._map.fit_bounds(bounds, padding=(20, 20))
        folium.LayerControl(collapsed=False).add_to(self._map)
        return self._map

    def bounds(self) -> Optional[List[List[float]]]:
        """Return the bounding box of everything drawn, or `None` if nothing was.

        Computed from the points the layers reported drawing rather than from
        airport positions. For a dateline route those differ: the drawn line
        runs past +180, and a box built from the endpoints would span the wrong
        way round the planet and exclude the line entirely.

        Returns:
            `[[south, west], [north, east]]`, or `None` for an empty map.
        """
        if not self._drawn:
            return None
        latitudes = [latitude for latitude, _ in self._drawn]
        longitudes = [longitude for _, longitude in self._drawn]
        return [
            [min(latitudes), min(longitudes)],
            [max(latitudes), max(longitudes)],
        ]

    def drawn_points(self) -> Sequence[Sequence[float]]:
        """Return every point drawn, in the frame the map was fitted to."""
        return self._drawn

    @staticmethod
    def _centre(line_points: Sequence[Sequence[float]]) -> Optional[float]:
        """Return the mid-longitude of everything the line layers drew.

        Args:
            line_points: Points from every non-marker layer.

        Returns:
            The midpoint of their longitude range, or `None` if no lines were
            drawn -- in which case markers have nothing to align to and keep
            their own coordinates.
        """
        if not line_points:
            return None
        longitudes = [longitude for _, longitude in line_points]
        return (min(longitudes) + max(longitudes)) / 2

    @staticmethod
    def _nearest_copy(longitude: float, centre: float) -> float:
        """Return the copy of `longitude` closest to `centre`.

        Longitude repeats every 360°, so a marker at −73.8° and one at 286.2°
        are the same place in different copies of the world. Leaflet draws
        each where it is told, so a marker has to be moved into the copy the
        lines were drawn in or it lands off the edge of the frame.

        Choosing the *nearest* copy rather than applying one global shift is
        what makes a multi-leg dateline path work: SYD stays at 151.2° while
        JFK moves to 286.2°, because those are the copies nearest the route.

        Args:
            longitude: The marker's own longitude.
            centre: Mid-longitude of the drawn lines.

        Returns:
            `longitude` plus a whole number of turns.
        """
        return longitude + 360 * round((centre - longitude) / 360)

    @classmethod
    def _aligned(cls, layer, points, centre: Optional[float]) -> List[List[float]]:
        """Return points in the map's frame, moving markers if needed."""
        if centre is None or not isinstance(layer, AirportLayer):
            return [[latitude, longitude] for latitude, longitude in points]
        return [
            [latitude, cls._nearest_copy(longitude, centre)]
            for latitude, longitude in points
        ]

    @classmethod
    def _align_markers(cls, group: Any, centre: float) -> None:
        """Move a feature group's markers into the copy of the world the lines are in.

        Args:
            group: A built `folium.FeatureGroup` of `CircleMarker`s.
            centre: Mid-longitude of the drawn lines.
        """
        for child in group._children.values():
            location = getattr(child, "location", None)
            if not location:
                continue
            latitude, longitude = location[0], location[1]
            child.location = [latitude, cls._nearest_copy(longitude, centre)]

    def _repr_html_(self) -> str:
        """Render as the value of a notebook cell, finishing first."""
        return self.finish()._repr_html_()

    # --- named constructors ---------------------------------------------

    @classmethod
    def compare(
        cls,
        planner: Any,
        origin: Any,
        destination: Any,
        algorithms: Mapping[str, Any],
        *,
        context: Any = None,
        palette: Optional[Palette] = None,
        **kwargs: Any,
    ) -> "RouteMap":
        """Draw one pair under several algorithms, one coloured layer each.

        The 80% case in an experiment notebook, and the picture at the top of
        `docs/visualization.md`.

        Args:
            planner: The `FlightPlanner` to query.
            origin: Origin `Airport` or IATA code.
            destination: Destination `Airport` or IATA code.
            algorithms: Mapping of label to `PathfindingAlgorithm`. The label
                keys the palette, so `"Dijkstra"` and `"A*"` get the same
                colours here as in the committed charts.
            context: Optional object exposing `.routes`, drawn as a
                `NetworkLayer` switched off.
            palette: Colours to draw with.
            **kwargs: Passed to `__init__`.

        Returns:
            A `RouteMap` with one airport layer, one path layer per algorithm,
            and optionally the network underneath.
        """
        route_map = cls(palette=palette, **kwargs)
        endpoints = [
            cls._airport(planner, origin),
            cls._airport(planner, destination),
        ]

        if context is not None:
            route_map.routes(context.routes)

        route_map.airports(endpoints)
        for label, algorithm in algorithms.items():
            route_map.path(
                cls._legs(planner, origin, destination, algorithm), name=label
            )
        return route_map

    @classmethod
    def network(
        cls,
        catalog: Any,
        *,
        palette: Optional[Palette] = None,
        airports: bool = True,
        **kwargs: Any,
    ) -> "RouteMap":
        """Draw a whole catalog: every airport, and every route as context.

        Args:
            catalog: Object exposing `.airports` and `.routes`.
            palette: Colours to draw with.
            airports: Whether to draw the airport markers too.
            **kwargs: Passed to `__init__`.

        Returns:
            A `RouteMap` of the whole network.
        """
        route_map = cls(palette=palette, **kwargs)
        route_map.routes(catalog.routes, name="All routes")
        if airports:
            route_map.airports(catalog.airports)
        return route_map

    @staticmethod
    def _airport(planner: Any, airport_or_code: Any):
        """Resolve an `Airport` or IATA code against a planner.

        Args:
            planner: The `FlightPlanner` to look the code up in.
            airport_or_code: An `Airport`, or a 3-letter IATA code.

        Returns:
            The `Airport`.

        Raises:
            KeyError: If the code is not in the planner.
        """
        if isinstance(airport_or_code, str):
            return planner.iata_lookup[airport_or_code.strip().upper()]
        return airport_or_code

    @staticmethod
    def _legs(planner: Any, origin: Any, destination: Any, algorithm: Any):
        """Return the legs one algorithm finds for a pair.

        Uses `search_route` when the planner offers it, so the counters are
        available where they exist, and falls back to `find_shortest_route`,
        which is what `main` has. Either way the legs are the same.
        """
        if hasattr(planner, "search_route"):
            return planner.search_route(origin, destination, algorithm).path
        _cost, legs = planner.find_shortest_route(origin, destination, algorithm)
        return legs


def _folium():
    """Return the folium module, or explain how to install it.

    Imported here rather than at module scope: the package does not depend on
    folium, and nothing should fail until a caller actually asks for a map.
    The message is written for the person who will see it, which is someone
    sitting in a notebook cell -- so it names both packages, gives the `%pip`
    form first, and says to restart the kernel.
    """
    try:
        import folium
    except ModuleNotFoundError as error:  # pragma: no cover - env specific
        raise ModuleNotFoundError(
            "Drawing maps needs folium and pyproj, which are not part of the "
            "flight_planner package.\n"
            "  In a notebook (Colab or Jupyter), run in a cell:\n"
            "      %pip install folium pyproj\n"
            "  In a checkout of this repository:\n"
            "      uv sync --group notebooks\n"
            "Then restart the kernel and re-run this cell."
        ) from error
    return folium
