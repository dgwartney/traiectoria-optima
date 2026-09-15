"""Faceted carrier maps for the `us-route-map` experiment.

One switchable layer per airline over the United States, Alaska, Hawaii and
Puerto Rico. Everything here is a thin arrangement of `flight_planner.viz` --
the faceting is `Catalog.airline()` for the filter, one `NetworkLayer` per
carrier for the drawing, and folium's own `LayerControl` for the checkboxes.
That is the point of the experiment: the layer system already supported this,
and nothing needed inventing beyond a colour table.

Lives beside the notebook rather than in the package, following
`experiments/search-cost/plots.py`: deliverable figures are an experiment's
business, and `flight_planner` must not grow a folium dependency.

Two things here are not arrangement and are worth knowing about:

- `uncovered_routes` decides what the thirteenth layer holds. It is the pairs
  *no* named carrier serves, not every pair the unnamed carriers fly -- see its
  docstring for why that distinction matters to the picture.
- `palette_contrast` measures the carrier palette rather than asserting it.
  The repository's existing series-palette numbers came from an external
  checker with no committed script, so this implements the measurement instead
  of citing it.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from flight_planner.viz import (
    ESRI_LIGHT_GRAY,
    ESRI_LIGHT_GRAY_ATTRIBUTION,
    MapExporter,
    Palette,
    RouteMap,
)

# Carrier layers are findings, not scenery, so they are drawn heavier and more
# opaque than `NetworkLayer`'s backdrop defaults (weight 1.0, opacity 0.3).
# With twelve layers on at once the lines still have to be individually
# followable, which is what stopped this going heavier still.
CARRIER_WEIGHT = 1.6
CARRIER_OPACITY = 0.75

# The bucket layer keeps the backdrop treatment: it is context.
OTHER_WEIGHT = 1.0
OTHER_OPACITY = 0.35

# Regions drawn off the continental map. Named here because "the lower 48" has
# to be spelled out as data: Puerto Rico's `iso_region` is the odd literal
# `PR-U-A`, not a `PR-*` pattern worth matching on.
OFFSHORE_REGIONS = ("US-AK", "US-HI", "PR-U-A")


def pair_key(route: Any) -> Tuple[str, str]:
    """Return a route's unordered airport pair.

    Matches `NetworkLayer.distinct_pairs`, which collapses the route table's
    flight-numbered rows to one drawable arc per city pair. Counting anything
    else here would report numbers the map does not draw.

    Args:
        route: A `Route`.

    Returns:
        The sorted `(origin, destination)` IATA pair.
    """
    return tuple(sorted((route.origin.iata_code, route.destination.iata_code)))


def carrier_pairs(catalog: Any, code: str) -> set:
    """Return the distinct airport pairs one carrier serves.

    Args:
        catalog: The `Catalog` to narrow.
        code: IATA airline code.

    Returns:
        Set of sorted IATA pairs.
    """
    return {pair_key(route) for route in catalog.airline(code).routes}


def carrier_pair_counts(catalog: Any, codes: Iterable[str]) -> Dict[str, int]:
    """Count distinct pairs per carrier, largest first.

    Args:
        catalog: The `Catalog` to narrow.
        codes: IATA airline codes.

    Returns:
        Mapping of code to pair count, ordered descending by count.
    """
    counts = {code: len(carrier_pairs(catalog, code)) for code in codes}
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


def uncovered_routes(catalog: Any, codes: Iterable[str]) -> List[Any]:
    """Return one route per pair that none of `codes` serves.

    Why not simply "every route flown by the other carriers": most pairs a
    small carrier flies are also flown by a major, so drawing all of them would
    repaint arcs already on screen -- darkening lines in a way that
    misrepresents the geometry, which is the same mistake
    `NetworkLayer.distinct_pairs` exists to prevent one level down.

    Taking only the uncovered pairs makes the thirteen layers a partition: in
    aggregate they cover every pair in the catalog exactly once. That is a
    property worth having, because it means the bucket's size answers "how much
    of this network do the twelve majors miss?" rather than an arithmetic
    accident.

    Args:
        catalog: The `Catalog` to search.
        codes: IATA airline codes considered covered.

    Returns:
        One representative `Route` per uncovered pair.
    """
    covered = set()
    for code in codes:
        covered |= carrier_pairs(catalog, code)

    representatives: Dict[Tuple[str, str], Any] = {}
    for route in catalog.routes:
        key = pair_key(route)
        if key not in covered:
            representatives.setdefault(key, route)
    return list(representatives.values())


def layer_label(
    code: str, name: str, pairs: int, defunct: Sequence[str] = ()
) -> str:
    """Return the layer-control label for a carrier.

    The layer control is this map's only legend, so the label carries the
    finding rather than naming a colour -- the same convention
    `PathLayer.name()` follows when it reports a distance. `[defunct]` marks a
    carrier that no longer operates, so the data's vintage is legible on the
    map itself and not only in `experiment.toml`.

    Args:
        code: IATA airline code.
        name: Carrier name.
        pairs: Distinct pairs the carrier serves.
        defunct: Codes to mark as no longer operating.

    Returns:
        A label such as `"American (AA) - 718 routes"`.
    """
    mark = " [defunct]" if code in defunct else ""
    return f"{name} ({code}){mark} - {pairs:,} routes"


def is_offshore(airport: Any) -> bool:
    """Report whether an airport sits outside the continental United States.

    Args:
        airport: An `Airport`.

    Returns:
        `True` for Alaska, Hawaii and Puerto Rico.
    """
    return airport.region in OFFSHORE_REGIONS


def continental(routes: Iterable[Any]) -> List[Any]:
    """Keep only routes with both ends in the continental United States.

    Used for the lower-48 still. `RouteMap` frames itself on what was drawn, so
    dropping the offshore arcs is all it takes to reframe -- no bounds override
    is needed anywhere.

    Args:
        routes: `Route` objects.

    Returns:
        The continental subset.
    """
    return [
        route
        for route in routes
        if not is_offshore(route.origin) and not is_offshore(route.destination)
    ]


def faceted_map(
    catalog: Any,
    carriers: Mapping[str, str],
    *,
    defunct: Sequence[str] = (),
    other_label: Optional[str] = None,
    mode: str = "light",
    only: Optional[Sequence[str]] = None,
    lower_48: bool = False,
    airports: bool = True,
) -> RouteMap:
    """Build the faceted carrier map.

    The whole experiment in one function, and deliberately short: the filter is
    `Catalog.airline()`, the drawing is one `NetworkLayer` per carrier, and the
    checkboxes are folium's `LayerControl`, which `RouteMap.finish()` already
    attaches.

    Args:
        catalog: The `Catalog` to draw.
        carriers: Mapping of IATA code to carrier name, in legend order.
        defunct: Codes to mark as no longer operating.
        other_label: Label for the uncovered-pairs bucket. Omitted if `None`.
        mode: Palette surface, `"light"` or `"dark"`.
        only: Draw just these carriers, switched on. `None` draws all of
            `carriers`. This is what a still image of one or two carriers uses
            -- the interactive map needs no such argument, because unchecking
            a box is the same operation.
        lower_48: Drop routes touching Alaska, Hawaii or Puerto Rico, which
            reframes the map on the continental United States.
        airports: Whether to add the airport marker layer.

    Returns:
        An unfinished `RouteMap`. The caller renders, exports or measures it.
    """
    palette = Palette(mode)
    # Esri's gray canvas rather than the package default of OpenStreetMap, for
    # two reasons and the first is a bug this experiment hit.
    #
    # OSM needs no API key but does need a `Referer`. This experiment's
    # deliverable is a *committed* file a reader opens by double-clicking, and
    # `file://` sends no `Referer`, so OSM replaced every tile with a `403 /
    # Access blocked` notice -- served as HTTP 200, so nothing raised and the
    # map rendered perfectly with the basemap reading "Access blocked". It
    # went unnoticed because the map was first checked over localhost, which
    # *does* send a `Referer`.
    #
    # Second, and a genuine improvement rather than a workaround: a
    # desaturated canvas keeps the basemap from competing with the arcs. On
    # OSM's colourful base, four carrier hues fight green landmass and blue
    # water for the reader's attention.
    route_map = RouteMap(
        tiles=ESRI_LIGHT_GRAY,
        attribution=ESRI_LIGHT_GRAY_ATTRIBUTION,
        basemap_name="Esri light gray",
        palette=palette,
    )
    selected = list(only) if only is not None else list(carriers)

    # Largest first, so the smallest carrier is added last and lands on top.
    # Leaflet paints in insertion order, so drawing WN's 570 arcs before AA's
    # 718 buries WN entirely -- the two-carrier comparison stills were
    # unreadable until this was ordered rather than left to dict order.
    drawn = sorted(
        selected, key=lambda code: -len(carrier_pairs(catalog, code))
    )

    if airports:
        markers = [
            airport
            for airport in catalog.airports
            if not (lower_48 and is_offshore(airport))
        ]
        # Switched off by default: 473 markers bury the arcs they sit on, and
        # the arcs are the finding. `AirportLayer` has no `show` argument, so
        # this is built directly rather than through `RouteMap.airports()`.
        route_map.add(
            _airport_layer(markers, palette, f"Airports ({len(markers):,})")
        )

    for code in drawn:
        routes = catalog.airline(code).routes
        if lower_48:
            routes = continental(routes)
        if not routes:
            continue
        pairs = len({pair_key(route) for route in routes})
        route_map.routes(
            routes,
            name=layer_label(code, carriers[code], pairs, defunct),
            colour=palette.carrier(code),
            dash_array=palette.carrier_dash(code),
            show=True,
            weight=CARRIER_WEIGHT,
            opacity=CARRIER_OPACITY,
        )

    if other_label is not None and only is None:
        others = uncovered_routes(catalog, carriers)
        if lower_48:
            others = continental(others)
        if others:
            route_map.routes(
                others,
                name=f"{other_label} - {len(others):,} routes",
                show=False,
                weight=OTHER_WEIGHT,
                opacity=OTHER_OPACITY,
            )

    return route_map


def _airport_layer(airports: Sequence[Any], palette: Palette, name: str):
    """Return an airport layer that starts switched off.

    `AirportLayer.show()` returns `True` and takes no argument, so rather than
    widen the package's API for one caller, this subclasses it here. The
    experiment is the right place for a preference that is this experiment's
    alone.

    Args:
        airports: `Airport` objects to draw.
        palette: Colours to draw with.
        name: Label for the layer control.

    Returns:
        A `MapLayer`.
    """
    from flight_planner.viz import AirportLayer

    class _HiddenAirportLayer(AirportLayer):
        """Airport markers, switched off until the reader asks for them."""

        def show(self) -> bool:
            """Report that this layer starts switched off."""
            return False

    return _HiddenAirportLayer(airports, palette, name=name, radius=3)


# --- output ----------------------------------------------------------------


def write_interactive(route_map: RouteMap, destination: Path) -> Path:
    """Save the interactive map as self-contained HTML.

    The experiment's headline deliverable: `MapExporter.html()` needs only
    folium, so this works anywhere the notebook does, including Colab.

    Args:
        route_map: The map to save.
        destination: Output path. Parent directories are created.

    Returns:
        The path written.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    return MapExporter().html(route_map, destination)


def write_stills(
    catalog: Any,
    carriers: Mapping[str, str],
    focus: Mapping[str, Sequence[str]],
    *,
    defunct: Sequence[str] = (),
    other_label: Optional[str] = None,
    report_dir: Path,
    slides_dir: Path,
) -> Dict[str, List[Path]]:
    """Render the PNG stills into both image directories.

    One light PNG goes to both destinations rather than a dark/light pair --
    the exception `experiments/route-map` documents, because no keyless dark
    basemap exists and `RouteMap` refuses the ones that need an API key.

    Each still is rendered **once** and copied, not rendered twice. Screenshot
    output is not byte-deterministic: rendering the same map twice produced
    files 25 bytes apart, because basemap tiles arrive and labels settle on
    their own schedule. `tests/experiments/test_figures.py` requires the two
    copies to be byte-identical, so copying is what makes that contract
    honest rather than flaky.

    Args:
        catalog: The `Catalog` to draw.
        carriers: Mapping of IATA code to carrier name.
        focus: Mapping of still name to the carrier codes it shows. A name of
            `"all"` is reserved for the every-carrier view.
        defunct: Codes to mark as no longer operating.
        other_label: Label for the uncovered-pairs bucket.
        report_dir: Where the report's copy goes.
        slides_dir: Where the deck's copy goes.

    Returns:
        Mapping of still name to the paths written, both directories each.
    """
    exporter = MapExporter()
    written: Dict[str, List[Path]] = {}

    # The airport layer is omitted from the focus stills, and that is about
    # framing rather than clutter -- it is switched off in every view anyway.
    # `RouteMap.bounds()` is the union of what *every* layer drew, visible or
    # not, so a hidden 473-airport layer pins each still to the full
    # Aleutians-to-Culebra box and a single-carrier map comes out as zoomed
    # out as the whole network. Dropping the layer lets `fit_bounds` frame the
    # arcs the still is actually about. The interactive map keeps it, because
    # there the reader wants to switch it on.
    views: Dict[str, Dict[str, Any]] = {
        "all": {"only": None, "lower_48": False},
        "lower-48": {"only": None, "lower_48": True},
    }
    for label, codes in focus.items():
        views[label] = {
            "only": list(codes),
            "lower_48": False,
            "airports": False,
        }

    for label, options in views.items():
        route_map = faceted_map(
            catalog,
            carriers,
            defunct=defunct,
            other_label=other_label,
            **options,
        )
        stem = f"us-route-map-{label}"
        report_dir.mkdir(parents=True, exist_ok=True)
        slides_dir.mkdir(parents=True, exist_ok=True)

        rendered = exporter.png(route_map, report_dir / f"{stem}.png")
        copy = slides_dir / f"{stem}.png"
        shutil.copyfile(rendered, copy)
        written[label] = [rendered, copy]

    return written


# --- palette measurement ---------------------------------------------------

# Viénot, Brettel & Mollon (1999) dichromat simulation, in linear sRGB via
# LMS. Protanopia and deuteranopia are the published projections; tritanopia
# uses the same construction on the S axis. Enough to answer "can these twelve
# lines be told apart", which is the question the palette has to survive.
_RGB_TO_LMS = (
    (17.8824, 43.5161, 4.11935),
    (3.45565, 27.1554, 3.86714),
    (0.0299566, 0.184309, 1.46709),
)
_LMS_TO_RGB = (
    (0.0809444479, -0.130504409, 0.116721066),
    (-0.0102485335, 0.0540193266, -0.113614708),
    (-0.000365296938, -0.00412161469, 0.693511405),
)
_DICHROMAT = {
    "protanopia": ((0.0, 2.02344, -2.52581), 0),
    "deuteranopia": ((0.494207, 0.0, 1.24827), 1),
    "tritanopia": ((-0.395913, 0.801109, 0.0), 2),
}

# D65 white point, for the XYZ -> Lab step.
_WHITE = (0.95047, 1.0, 1.08883)


def _linear(channel: float) -> float:
    """Undo the sRGB transfer function for one channel in `[0, 1]`."""
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _hex_to_linear(colour: str) -> Tuple[float, float, float]:
    """Convert a hex colour to linear-light RGB.

    Args:
        colour: A `#rrggbb` string.

    Returns:
        Linear RGB in `[0, 1]`.

    Raises:
        ValueError: If the string is not a 6-digit hex colour. Named CSS
            colours are refused rather than guessed at, because the only one
            in this project's tables is the airport scenery colour and it is
            not part of any measured set.
    """
    text = colour.lstrip("#")
    if len(text) != 6:
        raise ValueError(
            f"{colour!r} is not a 6-digit hex colour; measurement covers the "
            "carrier table, whose entries are all hex"
        )
    values = tuple(int(text[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(_linear(value) for value in values)


def _apply(matrix: Sequence[Sequence[float]], vector: Sequence[float]):
    """Multiply a 3x3 matrix by a 3-vector."""
    return tuple(sum(row[i] * vector[i] for i in range(3)) for row in matrix)


def simulate(colour: str, deficiency: str) -> Tuple[float, float, float]:
    """Return a colour as seen with one form of dichromacy, in linear RGB.

    Args:
        colour: A `#rrggbb` string.
        deficiency: `"protanopia"`, `"deuteranopia"` or `"tritanopia"`.

    Returns:
        Linear RGB as the dichromat sees it.

    Raises:
        KeyError: If the deficiency is not one of the three simulated.
    """
    coefficients, axis = _DICHROMAT[deficiency]
    lms = list(_apply(_RGB_TO_LMS, _hex_to_linear(colour)))
    others = [i for i in range(3) if i != axis]
    lms[axis] = sum(coefficients[i] * lms[i] for i in others)
    return _apply(_LMS_TO_RGB, lms)


def _to_lab(rgb: Sequence[float]) -> Tuple[float, float, float]:
    """Convert linear sRGB to CIELAB under D65."""
    matrix = (
        (0.4124564, 0.3575761, 0.1804375),
        (0.2126729, 0.7151522, 0.0721750),
        (0.0193339, 0.1191920, 0.9503041),
    )
    clamped = [min(1.0, max(0.0, channel)) for channel in rgb]
    xyz = _apply(matrix, clamped)

    def f(value: float) -> float:
        if value > 0.008856:
            return value ** (1 / 3)
        return 7.787 * value + 16 / 116

    fx, fy, fz = (f(xyz[i] / _WHITE[i]) for i in range(3))
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _delta_e(first: Sequence[float], second: Sequence[float]) -> float:
    """Return the CIE76 colour difference between two Lab values."""
    return math.sqrt(sum((first[i] - second[i]) ** 2 for i in range(3)))


def palette_contrast(mode: str = "light") -> Dict[str, Any]:
    """Measure the carrier palette's separation, normal and dichromat.

    Measures rather than asserts, and the measurement earned its keep: it
    refuted the palette's first design, in which six hues over two dash
    patterns left vermillion and reddish purple at ΔE 0.9 under tritanopia.
    See `CARRIER_COLOURS` for what that changed.

    What the current table guarantees is a property of *same-stroke* pairs.
    Four hues carry twelve carriers, so a hue is shared by three carriers by
    construction and their ΔE is 0 -- they are told apart by stroke, exactly as
    a chart series is told apart by marker as well as hue. Two carriers a
    reader must separate by colour alone are two carriers drawn with the same
    dash, and that is the set this reports on.

    CIE76 over a Viénot-Brettel-Mollon dichromat simulation, both implemented
    above. The series palette's committed figures came from an external checker
    with no script in this repository, so its numbers and these are not
    directly comparable.

    Args:
        mode: Palette surface, `"light"` or `"dark"`.

    Returns:
        Mapping with `mode`; `worst_same_stroke`, the worst ΔE between two
        carriers sharing a dash pattern, under normal vision and under each
        simulated deficiency; and `strokes`, the carriers in each dash class.
    """
    from flight_planner.viz.palette import CARRIER_COLOURS, CARRIER_DASHES

    table = CARRIER_COLOURS[mode]
    codes = list(table)

    strokes: Dict[str, List[str]] = {}
    for code in codes:
        strokes.setdefault(CARRIER_DASHES.get(code, "solid"), []).append(code)

    comparable = [
        (a, b)
        for members in strokes.values()
        for index, a in enumerate(members)
        for b in members[index + 1 :]
    ]

    views: Dict[str, Any] = {"normal": _hex_to_linear}
    for deficiency in _DICHROMAT:
        views[deficiency] = lambda colour, kind=deficiency: simulate(
            colour, kind
        )

    worst: Dict[str, Any] = {}
    for label, view in views.items():
        labs = {code: _to_lab(view(table[code])) for code in codes}
        code_a, code_b = min(
            comparable, key=lambda pair: _delta_e(labs[pair[0]], labs[pair[1]])
        )
        worst[label] = {
            "delta_e": round(_delta_e(labs[code_a], labs[code_b]), 1),
            "pair": [code_a, code_b],
        }

    return {
        "mode": mode,
        "worst_same_stroke": worst,
        "strokes": strokes,
    }
