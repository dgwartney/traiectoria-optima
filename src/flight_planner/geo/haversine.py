"""Haversine great-circle distance formula."""

from __future__ import annotations
from math import radians, sin, cos, asin, sqrt
from typing import TYPE_CHECKING

from .formula import DistanceFormula

if TYPE_CHECKING:
    from .point import Point

_EARTH_RADIUS_KM = 6371.0


class Haversine(DistanceFormula):
    """Great-circle distance assuming a perfect sphere.

    ~0.5% error versus the real oblate-ellipsoid Earth, but simple and
    numerically stable. Never overestimates true geodesic distance, so it
    is a safe (admissible) heuristic for A* when edge weights are real-world
    travel distances.
    """

    def calculate(self, a: "Point", b: "Point") -> float:
        """Compute the great-circle distance between two points.

        Args:
            a: First point.
            b: Second point.

        Returns:
            Distance in kilometers, assuming a spherical Earth.
        """
        lat1, lon1 = radians(a.latitude), radians(a.longitude)
        lat2, lon2 = radians(b.latitude), radians(b.longitude)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return _EARTH_RADIUS_KM * 2 * asin(sqrt(h))
