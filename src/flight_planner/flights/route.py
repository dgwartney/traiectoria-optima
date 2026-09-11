"""Flight route graph edge."""

from __future__ import annotations

from ..core.edge import Edge
from .airport import Airport


class Route(Edge[Airport]):
    """Flight route edge between two Airport instances."""

    def __init__(
        self,
        origin: Airport,
        destination: Airport,
        distance_km: float,
        airline: str = "",
        flight_number: str = "",
    ) -> None:
        """Create a flight leg between two airports.

        Args:
            origin: Departure airport.
            destination: Arrival airport.
            distance_km: Leg distance in kilometers, used as the edge weight.
            airline: Operating airline code.
            flight_number: Flight number for this leg.
        """
        super().__init__(source=origin, target=destination, weight=distance_km)
        self._airline = airline
        self._flight_number = flight_number

    @property
    def origin(self) -> Airport:
        """Return the departure airport.

        Returns:
            The source vertex, named for the flight domain.
        """
        return self.source

    @property
    def destination(self) -> Airport:
        """Return the arrival airport.

        Returns:
            The target vertex, named for the flight domain.
        """
        return self.target

    @property
    def distance_km(self) -> float:
        """Return the leg distance in kilometers.

        This is the edge weight every pathfinding algorithm accumulates. It is
        supplied as domain data, so it may differ from the great-circle
        distance a `DistanceFormula` would compute between the two airports.

        Returns:
            Distance in kilometers.
        """
        return self.weight

    @property
    def airline(self) -> str:
        """Return the operating airline.

        Returns:
            Airline code, or `""` if none was supplied.
        """
        return self._airline

    @property
    def flight_number(self) -> str:
        """Return the flight number for this leg.

        Returns:
            Flight number, or `""` if none was supplied.
        """
        return self._flight_number

    def __repr__(self) -> str:
        """Return a debugging representation of the leg.

        Returns:
            String of the form `Route(AAA -> BBB, N km, flight=...)`.
        """
        return (
            f"Route({self.origin.iata_code} -> {self.destination.iata_code}, "
            f"{self.distance_km} km, flight={self._flight_number!r})"
        )
