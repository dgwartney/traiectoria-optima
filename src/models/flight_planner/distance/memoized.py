"""Caching decorator for any DistanceFormula strategy."""

from __future__ import annotations
from typing import Dict, Tuple, TYPE_CHECKING

from distance.formula import DistanceFormula

if TYPE_CHECKING:
    from point import Point


class Memoized(DistanceFormula):
    """Wraps another DistanceFormula and caches results by coordinate value.

    Keyed on (latitude, longitude) pairs rather than object identity, so
    repeated calls for the same coordinates hit the cache even across
    distinct Point instances. Correct only if the wrapped formula is a
    pure function of the two points' coordinates (true for Haversine and
    Vincenty).
    """

    def __init__(self, formula: DistanceFormula) -> None:
        self._formula = formula
        self._cache: Dict[Tuple[float, float, float, float], float] = {}

    def calculate(self, a: "Point", b: "Point") -> float:
        key = (a.latitude, a.longitude, b.latitude, b.longitude)
        if key not in self._cache:
            self._cache[key] = self._formula.calculate(a, b)
        return self._cache[key]
