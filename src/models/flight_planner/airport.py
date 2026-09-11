"""Airport graph vertex."""

from __future__ import annotations

from vertex import Vertex
from point import Point


class Airport(Vertex, Point):
    """Airport vertex identified by its IATA code and geographic location.

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
        """Create an airport vertex.

        Args:
            iata_code: 3-letter IATA code. Stripped and upper-cased, and used
                as the graph identity key.
            name: Full airport name.
            city: City the airport serves.
            country: Country code or name.
            latitude: Latitude in decimal degrees, positive north.
            longitude: Longitude in decimal degrees, positive east.
        """
        normalized_iata = iata_code.strip().upper()
        Vertex.__init__(self, key=normalized_iata)
        Point.__init__(self, latitude=latitude, longitude=longitude)
        self._iata_code = normalized_iata
        self._name = name
        self._city = city
        self._country = country

    @property
    def iata_code(self) -> str:
        """Return the normalized IATA code identifying this airport.

        Returns:
            Upper-cased 3-letter code, the same value used as the graph key.
        """
        return self._iata_code

    @property
    def name(self) -> str:
        """Return the airport's full name.

        Returns:
            Airport name, or `""` if none was supplied.
        """
        return self._name

    @property
    def city(self) -> str:
        """Return the city the airport serves.

        Returns:
            City name, or `""` if none was supplied.
        """
        return self._city

    @property
    def country(self) -> str:
        """Return the airport's country.

        Returns:
            Country code or name, or `""` if none was supplied.
        """
        return self._country

    def __repr__(self) -> str:
        """Return a debugging representation with code, city, and coordinates.

        Returns:
            String of the form `Airport('XXX', city=..., lat=..., lon=...)`.
        """
        return (
            f"Airport({self._iata_code!r}, city={self._city!r}, "
            f"lat={self.latitude}, lon={self.longitude})"
        )
