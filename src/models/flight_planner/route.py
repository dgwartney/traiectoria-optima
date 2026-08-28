"""Flight route graph edge."""

from __future__ import annotations

from edge import Edge
from airport import Airport


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
        super().__init__(source=origin, target=destination, weight=distance_km)
        self._airline = airline
        self._flight_number = flight_number

    @property
    def origin(self) -> Airport:
        return self.source

    @property
    def destination(self) -> Airport:
        return self.target

    @property
    def distance_km(self) -> float:
        return self.weight

    @property
    def airline(self) -> str:
        return self._airline

    @property
    def flight_number(self) -> str:
        return self._flight_number

    def __repr__(self) -> str:
        return (
            f"Route({self.origin.iata_code} -> {self.destination.iata_code}, "
            f"{self.distance_km} km, flight={self._flight_number!r})"
        )
