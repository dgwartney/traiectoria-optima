"""The admissible A* heuristic for flight networks, and why it is admissible.

A* scores each candidate vertex `f = g + h`: `g` is the cost already
accumulated reaching it, `h` is an estimate of the cost still to go. For the
returned path to be optimal, `h` must never *overestimate* the true remaining
cost — the property called *admissibility*. An overestimate makes A* believe
routes through a vertex are worse than they are, so it may never expand that
vertex; if the optimal route ran through it, A* returns a longer path and
reports it as optimal. The failure is silent.

**Why great-circle distance is admissible here, precisely.** Not because
haversine is a universal lower bound on geodesic distance — it is not. Measured
over real airport pairs, haversine *exceeds* the WGS-84 geodesic on 1,905 of
5,000 pairs, by up to 35.07 km.

It is admissible because the edge weights are themselves haversine numbers.
`src/data/flight_network.py` generates the `distance_km` column with
`Haversine().calculate(...)` for exactly this reason, and `Haversine` uses a
single earth radius, so the heuristic and the weights are the same measurement.
A great-circle arc is never longer than a chain of great-circle arcs between
the same endpoints, so `h` can never exceed the true remaining cost. Measured
on the world snapshot: **0 of 66,332 edges violate it**, worst excess
0.000000000 km — exact, not approximate.

**So admissibility rests on an invariant between the data pipeline and the
heuristic, not on geometry.** `tests/flight_planner/geo/test_heuristic.py`
enforces it against real routes; if the pipeline's formula or radius ever
changes, that test fails rather than A* quietly degrading.

**Why not Vincenty.** `Vincenty` measures on the WGS-84 ellipsoid (semi-major
axis 6378.137 km) rather than a 6371.0 km sphere, and is more physically
accurate. That accuracy is the problem: its distances usually come out slightly
larger while the edge weights remain haversine, so the estimate exceeds the
truth on **3,095 of 5,000 edges**, by up to 23.73 km. A more accurate formula
produces a *less correct* A*. Precision and admissibility are different
properties, and improving the first can break the second.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from .formula import DistanceFormula
from .haversine import Haversine
from .memoized import Memoized

if TYPE_CHECKING:
    from .point import Point


def haversine_heuristic(
    *, memoize: bool = True
) -> Callable[["Point", "Point"], float]:
    """Return an admissible A* heuristic over great-circle distance.

    Use this rather than building a heuristic by hand. Hand-rolled heuristics
    are how the wrong formula gets in, and the wrong formula is not a precision
    difference — it is a correctness one (see the module docstring).

        >>> from flight_planner import AStar
        >>> algorithm = AStar(haversine_heuristic())

    Args:
        memoize: Whether to cache distances by coordinate value. Defaults to
            `True`, which is the right choice for a search — A* asks for the
            same vertex-to-goal distance repeatedly. Pass `False` where a cold
            cache is wanted, such as a benchmark measuring one query in
            isolation.

    Returns:
        A callable taking `(origin, goal)` and returning the great-circle
        distance between them in kilometers. Each call to this function returns
        a fresh callable with its own cache, so two heuristics never share
        state.
    """
    formula: DistanceFormula = Memoized(Haversine()) if memoize else Haversine()

    def heuristic(origin: "Point", goal: "Point") -> float:
        return formula.calculate(origin, goal)

    return heuristic
