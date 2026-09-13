"""Great-circle interpolation between two geographic points."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..geo.point import Point


class Geodesic:
    """Great-circle interpolation between two Points, as `[lat, lon]` pairs.

    A two-point line between coordinates is a straight line in Web Mercator,
    which is neither the path an aircraft flies nor the distance
    `Route.distance_km` reports. `docs/distance_formulas.md` makes that point
    for distance; a map has to make it too, or the picture contradicts the
    number printed beside it.

    Longitudes are *unwrapped* past ±180 rather than normalized into it, so a
    route crossing the antimeridian draws as one continuous line instead of
    jumping back across the whole map. That means the output is deliberately
    allowed outside `[-180, 180]`, which is why `MapLayer` reports the points
    it drew instead of letting the map infer bounds from airport positions.

    Attributes:
        ellipsoid: Name of the pyproj ellipsoid used, e.g. `"WGS84"`.
        segments: Interpolated points between the endpoints. Higher is
            smoother and larger; 6 is indistinguishable from 24 at the weight
            the context network is drawn with.
    """

    def __init__(self, ellipsoid: str = "WGS84", segments: int = 6) -> None:
        """Create an interpolator.

        Args:
            ellipsoid: pyproj ellipsoid name.
            segments: Number of points to interpolate between the endpoints.

        Raises:
            ValueError: If `segments` is negative.
        """
        if segments < 0:
            raise ValueError(f"segments must not be negative, got {segments}")
        self.ellipsoid = ellipsoid
        self.segments = segments

    def between(self, origin: "Point", destination: "Point") -> List[List[float]]:
        """Interpolate the great circle from `origin` to `destination`.

        Args:
            origin: Point to start from.
            destination: Point to end at.

        Returns:
            `segments + 2` `[lat, lon]` pairs, starting at `origin` and ending
            at `destination`, with longitudes unwrapped so that consecutive
            values never differ by more than 180°.

        Raises:
            ModuleNotFoundError: If pyproj is not installed. Deliberately not
                a straight-line fallback -- a wrong picture beside a correct
                number is worse than a missing picture.
        """
        geod = self._geod()
        interpolated = geod.npts(
            origin.longitude,
            origin.latitude,
            destination.longitude,
            destination.latitude,
            self.segments,
        )
        points = (
            [(origin.latitude, origin.longitude)]
            + [(lat, lon) for lon, lat in interpolated]
            + [(destination.latitude, destination.longitude)]
        )
        return self._unwrap(points)

    def _geod(self):
        """Return a pyproj `Geod`, or explain how to install pyproj.

        Imported here rather than at module scope: the package does not depend
        on pyproj, and nothing should fail until a caller asks for geometry.
        """
        try:
            from pyproj import Geod
        except ModuleNotFoundError as error:  # pragma: no cover - env specific
            raise ModuleNotFoundError(
                "Drawing maps needs pyproj, which is not part of the "
                "flight_planner package.\n"
                "  In a notebook (Colab or Jupyter), run in a cell:\n"
                "      %pip install folium pyproj\n"
                "  In a checkout of this repository:\n"
                "      uv sync --group notebooks\n"
                "Then restart the kernel and re-run this cell."
            ) from error
        return Geod(ellps=self.ellipsoid)

    @staticmethod
    def _unwrap(points) -> List[List[float]]:
        """Make a longitude sequence continuous across the antimeridian.

        `Geod.npts` normalizes longitudes into `[-180, 180]`, so a Pacific
        crossing arrives as `... 177, -170 ...`. Leaflet draws that as a line
        straight back across the map. Adding or subtracting 360° whenever
        consecutive values differ by more than 180° keeps the run monotonic.

        Args:
            points: Sequence of `(lat, lon)` pairs in order.

        Returns:
            The same points as `[lat, lon]` lists, longitudes unwrapped.
        """
        unwrapped: List[List[float]] = []
        previous = None
        for latitude, longitude in points:
            if previous is not None:
                if longitude - previous > 180:
                    longitude -= 360
                elif previous - longitude > 180:
                    longitude += 360
            previous = longitude
            unwrapped.append([latitude, longitude])
        return unwrapped
