"""The flight domain: airports, routes, and the planner that connects them.

This is the layer that composes everything below it. `Airport` is both a
`Vertex` and a `Point`; `Route` is an `Edge` between two airports; and
`FlightPlanner` is a `Graph` of the two with IATA-code lookup on top.
"""

from .airport import Airport
from .planner import FlightPlanner
from .route import Route

__all__ = ["Airport", "FlightPlanner", "Route"]
