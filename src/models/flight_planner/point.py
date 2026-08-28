"""Geographic point on Earth's surface."""

from __future__ import annotations
from typing import Optional

from distance.formula import DistanceFormula
from distance.haversine import Haversine


class Point:
    """A geographic coordinate (latitude, longitude in decimal degrees).

    Deliberately has no graph awareness and no __eq__/__hash__ override,
    so classes that mix it in (e.g. Airport(Vertex, Point)) can keep their
    own identity semantics unaffected by coordinates.
    """

    def __init__(self, latitude: float = 0.0, longitude: float = 0.0) -> None:
        self._latitude = float(latitude)
        self._longitude = float(longitude)

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    def distance_to(self, other: "Point", formula: Optional[DistanceFormula] = None) -> float:
        """Distance in km to another Point, using the given DistanceFormula
        (defaults to Haversine)."""
        return (formula if formula is not None else Haversine()).calculate(self, other)

    def __repr__(self) -> str:
        return f"Point(lat={self._latitude}, lon={self._longitude})"
