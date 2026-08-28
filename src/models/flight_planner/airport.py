"""Airport graph vertex."""

from __future__ import annotations

from vertex import Vertex
from point import Point


class Airport(Vertex, Point):
    """Airport vertex identified by its 3-letter IATA code, located at a
    geographic Point.

    Multiple inheritance combines two independent concerns: Vertex (graph
    identity: key/hash/eq) and Point (geography: latitude/longitude/distance).
    Vertex is listed first so Airport inherits its __eq__/__hash__ — graph
    identity stays keyed on iata_code only, never on coordinates.
    """

    def __init__(
        self,
        iata_code: str,
        name: str = "",
        city: str = "",
        country: str = "",
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> None:
        normalized_iata = iata_code.strip().upper()
        Vertex.__init__(self, key=normalized_iata)
        Point.__init__(self, latitude=latitude, longitude=longitude)
        self._iata_code = normalized_iata
        self._name = name
        self._city = city
        self._country = country

    @property
    def iata_code(self) -> str:
        return self._iata_code

    @property
    def name(self) -> str:
        return self._name

    @property
    def city(self) -> str:
        return self._city

    @property
    def country(self) -> str:
        return self._country

    def __repr__(self) -> str:
        return (
            f"Airport({self._iata_code!r}, city={self._city!r}, "
            f"lat={self.latitude}, lon={self.longitude})"
        )
