"""Maps of what an experiment found, drawn the same way every time.

Every experiment in this repository ends in numbers. This layer turns those
numbers into a picture, so that "Dijkstra routes HNL→BDL in three legs and BFS
does it in two" can be seen rather than reconstructed from a printout.

The layer sits at the top of the package's stack, depending on `flights/` and
`geo/` and depended on by nothing. It is also the only layer that reaches
outside the package's declared dependencies: **`folium` and `pyproj` are not
`flight_planner` dependencies**, and nothing about them appears in
`pyproject.toml`. The wheel's contract is pandas and nothing else; mapping is
a notebook concern, and `folium`/`pyproj` live in the `notebooks` dependency
group where the repository keeps notebook concerns.

So importing this module always works, and building a map is what fails if
folium is missing -- with a message written for someone sitting in a notebook
cell. See `docs/visualization.md` for the full design and the measurements
behind it.

Structure, mirroring how `geo/` keeps `DistanceFormula` in `formula.py` and
each formula in its own file:

- `layer.py` -- the `MapLayer` interface every drawable thing implements.
- `airports.py`, `network.py`, `path.py` -- the three concrete layers.
- `geodesic.py` -- great-circle interpolation and antimeridian unwrapping.
- `palette.py` -- colours, keyed by what a layer means.
- `routemap.py` -- composes layers and owns the folium map.
- `export.py` -- HTML and PNG output, for the report and the deck.
"""

from .airports import AirportLayer
from .export import MapExporter
from .geodesic import Geodesic
from .layer import MapLayer
from .network import NetworkLayer
from .palette import Palette
from .path import PathLayer
from .routemap import RouteMap

__all__ = [
    "AirportLayer",
    "Geodesic",
    "MapExporter",
    "MapLayer",
    "NetworkLayer",
    "Palette",
    "PathLayer",
    "RouteMap",
]
