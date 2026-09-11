"""Geographic point on Earth's surface."""

from __future__ import annotations
from typing import Optional

from .formula import DistanceFormula
from .haversine import Haversine


class Point:
    """A geographic coordinate (latitude, longitude in decimal degrees).

    Deliberately has no graph awareness and no __eq__/__hash__ override,
    so classes that mix it in (e.g. Airport(Vertex, Point)) can keep their
    own identity semantics unaffected by coordinates.
    """

    def __init__(self, latitude: float = 0.0, longitude: float = 0.0) -> None:
        """Create a geographic coordinate.

        Args:
            latitude: Latitude in decimal degrees, positive north.
            longitude: Longitude in decimal degrees, positive east.
        """
        self._latitude = float(latitude)
        self._longitude = float(longitude)

    @property
    def latitude(self) -> float:
        """Return the latitude in decimal degrees.

        Returns:
            Latitude, positive north.
        """
        return self._latitude

    @property
    def longitude(self) -> float:
        """Return the longitude in decimal degrees.

        Returns:
            Longitude, positive east.
        """
        return self._longitude

    def distance_to(self, other: "Point", formula: Optional[DistanceFormula] = None) -> float:
        """Compute the distance to another point.

        The formula is a Strategy supplied by the caller; `Point` itself knows
        nothing about how the distance is derived.

        Args:
            other: Point to measure to.
            formula: `DistanceFormula` to apply. Defaults to `Haversine`.

        Returns:
            Distance in kilometers.
        """
        return (formula if formula is not None else Haversine()).calculate(self, other)

    def __repr__(self) -> str:
        """Return a debugging representation showing both coordinates.

        Returns:
            String of the form `Point(lat=..., lon=...)`.
        """
        return f"Point(lat={self._latitude}, lon={self._longitude})"
