"""Strategy interface for computing distance between two geographic points."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .point import Point


class DistanceFormula(ABC):
    """Strategy interface for computing distance in km between two Points.

    Concrete formulas implemented here: Haversine (default, spherical-Earth
    approximation), Vincenty (WGS-84 ellipsoid, higher precision), and
    Manhattan (taxicab L1, committed as a measured counterexample rather than
    as a choice — see `flight_planner.geo.manhattan`, and do not search with
    it).

    Other formulas fit this same interface but are not implemented here —
    left as extension points:
      - Spherical Law of Cosines: mathematically equivalent to Haversine,
        simpler single-line formula, but loses precision for very close points.
      - Equirectangular: flat-plane approximation, very fast, accurate only
        for local/city-scale distances. `Manhattan` is this formula with the
        L1 norm in place of L2; `src/demos/custom_distance_formula_example.py`
        implements it as a worked example of adding a formula.
      - Karney's algorithm: modern gold-standard ellipsoidal geodesic,
        millimeter precision including antipodal points, complex to implement.
      - Projected coordinates (UTM): fast Euclidean distance after projecting
        to a local 2D grid; inaccurate across UTM zone boundaries.
    """

    @abstractmethod
    def calculate(self, a: "Point", b: "Point") -> float:
        """Returns the distance in kilometers between two Points."""
        raise NotImplementedError
