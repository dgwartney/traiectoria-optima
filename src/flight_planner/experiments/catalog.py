"""Look up and narrow the airports and routes an experiment works with.

A `Catalog` sits between frozen data and a `FlightPlanner`. It answers the
questions an experiment asks of a network before building a graph from it --
*which airport is BOS*, *which route is UA1876*, *give me only United's large
US airports* -- and then materializes whatever scope is left.

Narrowing is permissive by design. No combination of filters is refused and no
ordering is forbidden; instead every narrowing records what it did, and
`summary()` hands that record back so an experiment can state exactly how its
graph was derived. The one thing the catalog insists on is that the
experimenter is *told*: a scope with routes pointing outside its own airport
set reports those dangling edges rather than quietly building a graph whose
vertices arrived by accident.

Narrowings that act on airports take an `endpoints` mode:

| Mode | Route kept when | Notes |
| --- | --- | --- |
| `"both"` | both endpoints match | closed; filters commute; nothing dangles |
| `"either"` | one endpoint matches | keeps hub-to-regional legs |
| `"airports"` | always -- routes untouched | narrows lookups only; order matters |

`"both"` is the default because it is the only mode under which the order of
two narrowings cannot change the result.
"""

from __future__ import annotations

import warnings
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from ..flights.airport import Airport
from ..flights.planner import FlightPlanner
from ..flights.route import Route

#: The endpoint modes `airport_type`, `country` and `international` accept.
ENDPOINT_MODES = ("both", "either", "airports")

#: Sizes OurAirports records as `<size>_airport`, so an experimenter can write
#: `airport_type("large")` and mean the obvious thing.
_SIZE_ALIASES = ("large", "medium", "small")


class Narrowing:
    """One narrowing step and the effect it had.

    Recorded rather than merely applied: an experiment's results are only
    reproducible next to the derivation that produced its graph.

    Attributes:
        operation: Name of the narrowing method that ran.
        arguments: Normalized arguments it ran with.
        endpoints: Endpoint mode used, or `None` for route-level narrowings.
        routes_before: Route count before the step.
        routes_after: Route count after it.
        airports_before: Airport count before the step.
        airports_after: Airport count after it.
        dangling: Routes left with an endpoint outside the airport set.
    """

    def __init__(
        self,
        operation: str,
        arguments: Sequence[Any],
        endpoints: Optional[str],
        routes_before: int,
        routes_after: int,
        airports_before: int,
        airports_after: int,
        dangling: int,
    ) -> None:
        """Record a narrowing step.

        Args:
            operation: Name of the narrowing method that ran.
            arguments: Normalized arguments it ran with.
            endpoints: Endpoint mode used, or `None` if the step was
                route-level and took no mode.
            routes_before: Route count before the step.
            routes_after: Route count after it.
            airports_before: Airport count before the step.
            airports_after: Airport count after it.
            dangling: Routes left with an endpoint outside the airport set.
        """
        self.operation = operation
        self.arguments = tuple(arguments)
        self.endpoints = endpoints
        self.routes_before = routes_before
        self.routes_after = routes_after
        self.airports_before = airports_before
        self.airports_after = airports_after
        self.dangling = dangling

    def as_dict(self) -> Dict[str, Any]:
        """Return the step as plain JSON-serializable data.

        Experiments embed this in `results.json`, so it must survive
        `json.dumps` without help.

        Returns:
            Mapping of field name to value, with arguments as a list.
        """
        return {
            "operation": self.operation,
            "arguments": list(self.arguments),
            "endpoints": self.endpoints,
            "routes": [self.routes_before, self.routes_after],
            "airports": [self.airports_before, self.airports_after],
            "dangling": self.dangling,
        }

    def __repr__(self) -> str:
        """Return a debugging representation of the step and its effect.

        Returns:
            String of the form `Narrowing(airline('UA'): 5 -> 4 routes)`.
        """
        arguments = ", ".join(repr(argument) for argument in self.arguments)
        return (
            f"Narrowing({self.operation}({arguments}): "
            f"{self.routes_before} -> {self.routes_after} routes)"
        )


class Catalog:
    """A set of airports and routes, narrowable and materializable.

    Instances are immutable: every narrowing returns a new `Catalog` sharing
    the same `Airport` and `Route` objects. Sharing matters -- `FlightPlanner`
    resolves airports by identity, so a catalog-built graph and a
    catalog-looked-up airport must be the same object.
    """

    def __init__(
        self,
        airports: Iterable[Airport],
        routes: Iterable[Route],
        chain: Sequence[Narrowing] = (),
    ) -> None:
        """Build a catalog over already-loaded domain objects.

        Prefer `Snapshot.catalog()`, which loads a frozen dataset. This
        constructor is for hand-assembled networks and for internal use by the
        narrowing methods.

        Args:
            airports: Airports in scope. Later duplicates of an IATA code
                replace earlier ones.
            routes: Routes in scope, in the order they should be reported.
            chain: Narrowing steps that produced this scope.
        """
        self._airports: Dict[str, Airport] = {
            airport.iata_code: airport for airport in airports
        }
        self._routes: Tuple[Route, ...] = tuple(routes)
        self._chain: Tuple[Narrowing, ...] = tuple(chain)
        self._by_flight_number = {
            route.flight_number: route
            for route in self._routes
            if route.flight_number
        }

    # ---------------------------------------------------------------- scope

    @property
    def airports(self) -> Tuple[Airport, ...]:
        """Return the airports in scope.

        Returns:
            Tuple of `Airport`, in the order they were added.
        """
        return tuple(self._airports.values())

    @property
    def iata_codes(self) -> Tuple[str, ...]:
        """Return the IATA codes in scope.

        Returns:
            Tuple of codes, in the order their airports were added.
        """
        return tuple(self._airports)

    @property
    def routes(self) -> Tuple[Route, ...]:
        """Return the routes in scope.

        Returns:
            Tuple of `Route`, in file order.
        """
        return self._routes

    @property
    def dangling(self) -> Tuple[Route, ...]:
        """Return routes with an endpoint outside this catalog's airports.

        Non-empty only under the `"airports"` endpoint mode, which narrows
        lookups without touching routes. These are not an error -- building a
        planner from them is allowed, and reported.

        Returns:
            Tuple of `Route` whose origin or destination is out of scope.
        """
        return tuple(
            route
            for route in self._routes
            if route.origin.iata_code not in self._airports
            or route.destination.iata_code not in self._airports
        )

    # --------------------------------------------------------------- lookup

    def airport(self, iata_code: str) -> Airport:
        """Return the airport with the given IATA code.

        Args:
            iata_code: 3-letter code; whitespace and case are ignored.

        Returns:
            The `Airport` in scope.

        Raises:
            KeyError: If no airport in scope carries that code.
        """
        code = iata_code.strip().upper()
        try:
            return self._airports[code]
        except KeyError:
            raise KeyError(
                f"no airport {code!r} in this catalog "
                f"({len(self._airports)} airports in scope)"
            ) from None

    def flight(self, flight_number: str) -> Route:
        """Return the single route carrying a flight number.

        Flight numbers are the only unique handle on a route: SFO to BOS is
        flown by several carriers over the same distance, so the endpoint pair
        does not identify a leg.

        Args:
            flight_number: Assigned flight number, such as `UA1876`.

        Returns:
            The `Route`.

        Raises:
            KeyError: If no route in scope carries that number.
        """
        number = flight_number.strip().upper()
        try:
            return self._by_flight_number[number]
        except KeyError:
            raise KeyError(
                f"no flight {number!r} in this catalog "
                f"({len(self._routes)} routes in scope)"
            ) from None

    def routes_between(
        self, origin: str, destination: str, airline: Optional[str] = None
    ) -> Tuple[Route, ...]:
        """Return every route flying one ordered airport pair.

        Args:
            origin: Departure IATA code.
            destination: Arrival IATA code.
            airline: Restrict to one carrier, or `None` for all of them.

        Returns:
            Tuple of matching `Route`, possibly empty. Direction matters: a
            one-way pair has no match in reverse.
        """
        source = origin.strip().upper()
        target = destination.strip().upper()
        code = airline.strip().upper() if airline else None
        return tuple(
            route
            for route in self._routes
            if route.origin.iata_code == source
            and route.destination.iata_code == target
            and (code is None or route.airline.upper() == code)
        )

    def route(
        self, origin: str, destination: str, airline: Optional[str] = None
    ) -> Route:
        """Return the one route flying an ordered airport pair.

        Args:
            origin: Departure IATA code.
            destination: Arrival IATA code.
            airline: Restrict to one carrier, which is how an endpoint pair
                served by several is disambiguated.

        Returns:
            The single matching `Route`.

        Raises:
            LookupError: If nothing matches, or if more than one route does.
                The message names the flight numbers to choose between, since
                `flight()` is the unambiguous way to ask.
        """
        matches = self.routes_between(origin, destination, airline)
        pair = f"{origin.strip().upper()} -> {destination.strip().upper()}"
        if not matches:
            carrier = f" on {airline}" if airline else ""
            raise LookupError(f"no route {pair}{carrier} in this catalog")
        if len(matches) > 1:
            numbers = ", ".join(route.flight_number for route in matches)
            raise LookupError(
                f"{len(matches)} routes fly {pair}: {numbers}. "
                f"Pass airline=, or use flight() with one of those numbers."
            )
        return matches[0]

    def routes_from(self, iata_code: str) -> Tuple[Route, ...]:
        """Return the routes departing an airport.

        Args:
            iata_code: Departure IATA code.

        Returns:
            Tuple of outgoing `Route`, possibly empty. Arrivals are not
            included; routes are directed.
        """
        code = iata_code.strip().upper()
        return tuple(
            route for route in self._routes if route.origin.iata_code == code
        )

    # ------------------------------------------------------------ narrowing

    def airline(self, *codes: str) -> "Catalog":
        """Narrow to the routes flown by one or more carriers.

        Airline is a property of the route rather than the airport, so this
        takes no endpoint mode: matching routes are kept and the airports are
        re-derived from them.

        Args:
            *codes: Airline codes, such as `UA`. Case is ignored.

        Returns:
            A new `Catalog` holding only those carriers' routes.
        """
        wanted = tuple(code.strip().upper() for code in codes)
        kept = [route for route in self._routes if route.airline.upper() in wanted]
        return self._replace(
            operation="airline",
            arguments=wanted,
            endpoints=None,
            routes=kept,
            airports=self._referenced(kept),
        )

    def airport_type(self, *types: str, endpoints: str = "both") -> "Catalog":
        """Narrow by OurAirports size classification.

        Args:
            *types: Classifications such as `large_airport`, `heliport`, or
                `seaplane_base`. The bare sizes `large`, `medium` and `small`
                are accepted as shorthand.
            endpoints: One of `"both"`, `"either"` or `"airports"`.

        Returns:
            A new `Catalog` narrowed to those airport types.

        Raises:
            ValueError: If `endpoints` is not a known mode.
        """
        wanted = tuple(self._normalize_type(value) for value in types)
        return self._narrow_by_airport(
            operation="airport_type",
            arguments=wanted,
            matches=lambda airport: airport.type in wanted,
            endpoints=endpoints,
        )

    def country(self, *codes: str, endpoints: str = "both") -> "Catalog":
        """Narrow by the airports' ISO country code.

        Args:
            *codes: ISO country codes, such as `US`. Case is ignored.
            endpoints: One of `"both"`, `"either"` or `"airports"`.

        Returns:
            A new `Catalog` narrowed to airports in those countries.

        Raises:
            ValueError: If `endpoints` is not a known mode.
        """
        wanted = tuple(code.strip().upper() for code in codes)
        return self._narrow_by_airport(
            operation="country",
            arguments=wanted,
            matches=lambda airport: airport.country.upper() in wanted,
            endpoints=endpoints,
        )

    def international(
        self, value: bool = True, endpoints: str = "both"
    ) -> "Catalog":
        """Narrow by whether airports are listed as international.

        The flag is independent of `type`: 116 large airports are absent from
        the list and 364 medium ones appear on it, so this is a different
        question from `airport_type("large")`.

        Args:
            value: `True` for listed airports, `False` for the rest.
            endpoints: One of `"both"`, `"either"` or `"airports"`. Note that
                under `"both"`, `international(False)` keeps only routes whose
                *two* endpoints are unlisted, which is usually not the
                question -- `"airports"` is.

        Returns:
            A new `Catalog` narrowed accordingly.

        Raises:
            ValueError: If `endpoints` is not a known mode.
        """
        return self._narrow_by_airport(
            operation="international",
            arguments=(value,),
            matches=lambda airport: airport.is_international is bool(value),
            endpoints=endpoints,
        )

    # -------------------------------------------------------- materializing

    def planner(self) -> FlightPlanner:
        """Build a `FlightPlanner` over everything in scope.

        Every airport becomes a vertex and every route a directed edge. A
        route pointing at an airport outside the scope still becomes an edge --
        `Graph.add_edge` registers the missing endpoint -- so the graph is
        built as asked and a warning says how many edges did that.

        Returns:
            A planner holding this catalog's airports and routes.

        Warns:
            UserWarning: If any route has an endpoint outside the scope.
        """
        dangling = self.dangling
        if dangling:
            codes = sorted(
                {
                    endpoint.iata_code
                    for route in dangling
                    for endpoint in (route.origin, route.destination)
                    if endpoint.iata_code not in self._airports
                }
            )
            warnings.warn(
                f"{len(dangling)} route(s) reach {len(codes)} airport(s) outside "
                f"this catalog ({', '.join(codes[:5])}"
                f"{', ...' if len(codes) > 5 else ''}); they are included as "
                f"vertices. Narrow with endpoints='both' to avoid this.",
                UserWarning,
                stacklevel=2,
            )

        planner = FlightPlanner()
        for airport in self._airports.values():
            planner.add_vertex(airport)
        for route in self._routes:
            planner.add_edge(route)
        return planner

    def subgraph(self, legs: Iterable[Union[Route, str]]) -> FlightPlanner:
        """Build a planner holding only the named legs.

        For hand-assembling a small network out of real entities -- an example
        with three flights rather than the whole scope.

        Args:
            legs: `Route` objects, or flight numbers to resolve in this
                catalog.

        Returns:
            A planner holding those routes and their endpoints, and nothing
            else.

        Raises:
            KeyError: If a flight number is not in scope.
        """
        planner = FlightPlanner()
        for leg in legs:
            route = leg if isinstance(leg, Route) else self.flight(leg)
            planner.add_vertex(route.origin)
            planner.add_vertex(route.destination)
            planner.add_edge(route)
        return planner

    def summary(self) -> Mapping[str, Any]:
        """Return how this scope was derived and what it cost.

        Returns:
            Mapping with `chain` (the narrowing steps as plain data), `routes`
            and `airports` (counts before the first step and after each one),
            and `dangling` (routes currently reaching outside the scope).
        """
        routes = [step.routes_after for step in self._chain]
        airports = [step.airports_after for step in self._chain]
        first = self._chain[0] if self._chain else None
        return {
            "chain": [step.as_dict() for step in self._chain],
            "routes": [first.routes_before if first else len(self._routes)] + routes,
            "airports": [
                first.airports_before if first else len(self._airports)
            ]
            + airports,
            "dangling": len(self.dangling),
        }

    # ------------------------------------------------------------ internals

    def _narrow_by_airport(
        self,
        operation: str,
        arguments: Sequence[Any],
        matches: Callable[[Airport], bool],
        endpoints: str,
    ) -> "Catalog":
        """Apply an airport-level predicate under one of the endpoint modes.

        Args:
            operation: Narrowing name, for the provenance record.
            arguments: Normalized arguments, for the provenance record.
            matches: Predicate deciding whether one airport qualifies.
            endpoints: One of `ENDPOINT_MODES`.

        Returns:
            The narrowed `Catalog`.

        Raises:
            ValueError: If `endpoints` is not a known mode.
        """
        if endpoints not in ENDPOINT_MODES:
            raise ValueError(
                f"unknown endpoints mode {endpoints!r}; "
                f"expected one of {', '.join(ENDPOINT_MODES)}"
            )

        if endpoints == "airports":
            kept_airports = [
                airport for airport in self._airports.values() if matches(airport)
            ]
            return self._replace(
                operation=operation,
                arguments=arguments,
                endpoints=endpoints,
                routes=self._routes,
                airports=kept_airports,
            )

        # In "both" and "either" the airport set is re-derived from whatever
        # routes survive, so an earlier "airports" narrowing is not undone:
        # an endpoint already out of scope can never make a route qualify.
        def qualifies(airport: Airport) -> bool:
            return airport.iata_code in self._airports and matches(airport)

        require_all = endpoints == "both"
        kept_routes = []
        for route in self._routes:
            origin = qualifies(route.origin)
            destination = qualifies(route.destination)
            if (origin and destination) if require_all else (origin or destination):
                kept_routes.append(route)

        return self._replace(
            operation=operation,
            arguments=arguments,
            endpoints=endpoints,
            routes=kept_routes,
            airports=self._referenced(kept_routes),
        )

    def _referenced(self, routes: Sequence[Route]) -> List[Airport]:
        """Return the in-scope airports the given routes touch.

        Membership is checked against this catalog rather than taken from the
        routes themselves, so re-deriving never widens the scope.

        Args:
            routes: Routes whose endpoints should be collected.

        Returns:
            List of `Airport`, in first-seen order.
        """
        seen: Dict[str, Airport] = {}
        for route in routes:
            for endpoint in (route.origin, route.destination):
                code = endpoint.iata_code
                if code in self._airports and code not in seen:
                    seen[code] = self._airports[code]
        return list(seen.values())

    def _replace(
        self,
        operation: str,
        arguments: Sequence[Any],
        endpoints: Optional[str],
        routes: Sequence[Route],
        airports: Sequence[Airport],
    ) -> "Catalog":
        """Return a narrowed catalog with the step appended to its chain.

        Args:
            operation: Narrowing name.
            arguments: Normalized arguments.
            endpoints: Endpoint mode, or `None` for a route-level narrowing.
            routes: Routes surviving the step.
            airports: Airports surviving the step.

        Returns:
            The new `Catalog`.
        """
        narrowed = Catalog(airports, routes, self._chain)
        step = Narrowing(
            operation=operation,
            arguments=arguments,
            endpoints=endpoints,
            routes_before=len(self._routes),
            routes_after=len(narrowed._routes),
            airports_before=len(self._airports),
            airports_after=len(narrowed._airports),
            dangling=len(narrowed.dangling),
        )
        narrowed._chain = self._chain + (step,)
        return narrowed

    @staticmethod
    def _normalize_type(value: str) -> str:
        """Expand a bare size into the classification the data uses.

        Args:
            value: Type name, such as `large` or `seaplane_base`.

        Returns:
            The OurAirports classification, such as `large_airport`.
        """
        cleaned = value.strip().lower()
        if cleaned in _SIZE_ALIASES:
            return f"{cleaned}_airport"
        return cleaned

    def __repr__(self) -> str:
        """Return a debugging representation of the scope and its derivation.

        Returns:
            String of the form `Catalog(N airports, M routes, via ...)`.
        """
        chain = " -> ".join(step.operation for step in self._chain) or "unnarrowed"
        return (
            f"Catalog({len(self._airports)} airports, "
            f"{len(self._routes)} routes, {chain})"
        )
