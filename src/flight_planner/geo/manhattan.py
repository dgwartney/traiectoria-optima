"""Manhattan (taxicab) distance, and why it is the wrong A* heuristic here.

This formula is committed as a **measured counterexample**, not as an option.
It is the textbook grid heuristic — the L1 norm, one axis-aligned leg per
dimension — and on a grid of unit moves it is both admissible and excellent.
An airline route network is not a grid: the vertices carry coordinates but the
moves between them are arbitrary flight legs, and the edge weights are
great-circle kilometres. Applied here, the formula walks a meridian and then a
parallel to reach a goal the search will actually reach along an arc, so the
estimate comes in high almost everywhere.

**How high, measured.** Over every edge of the world snapshot the estimate
exceeds the edge's own weight on **66,331 of 66,332 edges (99.998%)**, by up to
6,453.15 km, with a median `estimate / weight` ratio of **1.316** and a maximum
of **1.541**. That makes it inadmissible, and A* — which closes a vertex on
first expansion and never reopens it — is then free to return a longer route
and report it as optimal. It does: of 300 seeded random pairs, 290 have a
route at all and **172 of those (59.3%)** come back suboptimal — by a fraction
of a percent at the median, 2.6% on average, and **24.6%** at worst.

**It is not useless, and that is the interesting part.** An overestimate makes
A* greedier, so it expands roughly **half** the vertices the admissible
heuristic does and about a twentieth of Dijkstra's. The trade is real and
bounded — a worst-case ratio of `r` bounds the returned cost at `r x` optimal —
which is why this is worth measuring rather than merely warning about.
`experiments/manhattan-heuristic/` is where the numbers above come from and
where the trade is quantified.

**For real work use `flight_planner.geo.heuristic.haversine_heuristic()`.**
It is the project's one admissible heuristic, and
`flight_planner.geo.heuristic`'s module docstring explains the invariant it
rests on.

**Relationship to the other approximations.** This is
`src/demos/custom_distance_formula_example.py`'s `Equirectangular` with the L1
norm in place of L2. Since `|x| + |y| >= sqrt(x**2 + y**2)`, Manhattan is never
below that flat-plane approximation and so is at least as inadmissible — the
demo's formula is a precision trade, this one is a correctness one.
"""

from __future__ import annotations
from math import cos, radians
from typing import Callable, TYPE_CHECKING

from .formula import DistanceFormula
from .haversine import _EARTH_RADIUS_KM
from .memoized import Memoized

if TYPE_CHECKING:
    from .point import Point


class Manhattan(DistanceFormula):
    """Taxicab distance on the sphere: one meridian leg plus one parallel leg.

    Inadmissible as an A* heuristic on this project's graphs. See the module
    docstring for what that costs and what it buys; use `Haversine` unless you
    are deliberately reproducing the counterexample.
    """

    def calculate(self, a: "Point", b: "Point") -> float:
        """Compute the taxicab distance between two points.

        The latitude leg is exact — a difference in latitude is an arc of a
        meridian, which is a great circle. The longitude leg is not: a
        difference in longitude is an arc of a *parallel*, a small circle
        whose radius shrinks with latitude. Scaling it by the cosine of the
        mean latitude is the standard approximation to that, and it is an
        approximation twice over, since the two points sit at different
        latitudes and the path between them at neither.

        Args:
            a: First point.
            b: Second point.

        Returns:
            Distance in kilometers, on the same sphere `Haversine` uses so
            that the two differ in shape rather than in radius.
        """
        lat1, lat2 = radians(a.latitude), radians(b.latitude)
        # Fold the longitude difference to the short way round. Without this
        # an antimeridian pair -- SYD-JFK, which experiments/route-map draws --
        # is estimated going the long way, and the overestimate stops being a
        # property of the L1 norm and becomes a bug. The demo's
        # `Equirectangular` has this same gap and is left alone; the
        # divergence is deliberate.
        dlon = abs(b.longitude - a.longitude)
        dlon = radians(min(dlon, 360.0 - dlon))
        return _EARTH_RADIUS_KM * (
            abs(lat2 - lat1) + dlon * cos((lat1 + lat2) / 2)
        )


def manhattan_heuristic(
    *, memoize: bool = True
) -> Callable[["Point", "Point"], float]:
    """Return the inadmissible Manhattan A* heuristic.

    Provided so the counterexample can be searched with rather than only
    described. **This is not the heuristic to plan routes with** — it returns
    suboptimal paths and reports them as optimal. Use
    `flight_planner.geo.heuristic.haversine_heuristic()`.

        >>> from flight_planner import AStar
        >>> algorithm = AStar(manhattan_heuristic())

    Args:
        memoize: Whether to cache distances by coordinate value. Defaults to
            `True`, matching `haversine_heuristic` so that a comparison
            between the two measures the formulas and not their caching.

    Returns:
        A callable taking `(origin, goal)` and returning the taxicab distance
        between them in kilometers. Each call returns a fresh callable with
        its own cache, so two heuristics never share state.
    """
    formula: DistanceFormula = Memoized(Manhattan()) if memoize else Manhattan()

    def heuristic(origin: "Point", goal: "Point") -> float:
        return formula.calculate(origin, goal)

    return heuristic
