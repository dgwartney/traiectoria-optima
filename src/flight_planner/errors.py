"""Exceptions the package raises when a lookup does not resolve.

Before these existed, one mistake — a mistyped IATA code — surfaced three
different ways depending on which method you called: `KeyError` from
`Catalog.airport`, `None` from `FlightPlanner.find_airport`, and `ValueError`
from `FlightPlanner.search_route`. A caller wanting to handle that one mistake
had to write `except (LookupError, ValueError)`, and `ValueError` is raised
across this package for at least six unrelated reasons — an unknown endpoint
mode, a Vincenty convergence failure, a malformed experiment TOML — so
catching it to handle a typo also swallowed real defects.

The classes here have **deliberately wide bases** so that adopting them broke
nothing. `AirportNotFoundError` derives from `KeyError`, `ValueError` *and*
`LookupError` (via `KeyError`), which is a strict superset of every convention
that was previously in use: existing code catching any one of those still
works, and new code can catch `FlightPlannerError` and mean exactly "a lookup
in this package did not resolve".

Each class also overrides `__str__`. `KeyError` alone renders its message with
`repr`, so `print(error)` emits a message wrapped in stray double quotes —
visible and wrong in any script or notebook that reports the failure.

`SnapshotIntegrityError` predates this module and stays where it is, in
`flight_planner.experiments.snapshot`: it reports corrupted data rather than an
unresolved lookup, and nothing is gained by moving it.
"""

from __future__ import annotations


class FlightPlannerError(Exception):
    """Base class for lookups this package could not resolve.

    Catch this to mean "the thing asked for is not here", without also
    catching the unrelated `ValueError`s raised for bad arguments, unparseable
    files and numerical non-convergence.
    """

    def __str__(self) -> str:
        """Return the message as written, without `KeyError`'s added quotes.

        Returns:
            The first argument, or the empty string if there is none.
        """
        return str(self.args[0]) if self.args else ""


class AirportNotFoundError(FlightPlannerError, KeyError, ValueError):
    """No airport in scope carries the requested IATA code.

    Derives from `KeyError` and `ValueError` so that code written against
    either of the two conventions this replaced keeps working unchanged.
    """


class RouteNotFoundError(FlightPlannerError, KeyError):
    """No route in scope matches the requested flight number or airport pair.

    Note that routes are directed: a pair with no match may still have one in
    reverse.

    Derives from `KeyError` — and so from `LookupError` — because the two
    methods this replaced disagreed: `flight()` raised `KeyError` and `route()`
    raised a bare `LookupError`. Taking the narrower of the two as the base
    keeps both callers working.
    """


class AmbiguousRouteError(RouteNotFoundError):
    """Several routes fly the requested pair, so the pair does not identify one.

    Raised instead of guessing. The message names the flight numbers to choose
    between, since a flight number is the only unique handle on a leg. Narrow
    with the `airline` argument, or ask by flight number.
    """
