"""Airport graph vertex."""

from __future__ import annotations

from typing import Optional

from ..core.vertex import Vertex
from ..geo.point import Point


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
        region: str = "",
        continent: str = "",
        elevation_ft: Optional[float] = None,
        type: str = "",
        icao_code: str = "",
        has_scheduled_service: bool = False,
        is_international: bool = False,
        wikipedia_link: str = "",
    ) -> None:
        """Create an airport vertex.

        Only `iata_code` is required; every other field defaults to empty, so
        an airport can be hand-built for a small example without supplying
        data it does not need. The descriptive fields exist for reporting and
        for `Catalog` filtering, and never participate in graph identity.

        Args:
            iata_code: 3-letter IATA code. Stripped and upper-cased, and used
                as the graph identity key.
            name: Full airport name.
            city: City the airport serves.
            country: ISO country code.
            latitude: Latitude in decimal degrees, positive north.
            longitude: Longitude in decimal degrees, positive east.
            region: ISO region (state or province), such as `US-CA`.
            continent: Two-letter continent code, such as `NA`.
            elevation_ft: Elevation in feet, or `None` when unknown. `None`
                rather than `0.0` because sea level is a real elevation.
            type: OurAirports size classification, such as `large_airport`.
            icao_code: 4-letter ICAO code, for cross-referencing other data.
            has_scheduled_service: Whether scheduled commercial flights serve
                this airport.
            is_international: Whether the airport appears on Wikipedia's list
                of international airports. Independent of `type`: 116 large
                airports are absent from that list and 364 medium ones are on
                it.
            wikipedia_link: URL of the airport's Wikipedia article.
        """
        normalized_iata = iata_code.strip().upper()
        Vertex.__init__(self, key=normalized_iata)
        Point.__init__(self, latitude=latitude, longitude=longitude)
        self._iata_code = normalized_iata
        self._name = name
        self._city = city
        self._country = country
        self._region = region
        self._continent = continent
        self._elevation_ft = elevation_ft
        self._type = type
        self._icao_code = icao_code
        self._has_scheduled_service = has_scheduled_service
        self._is_international = is_international
        self._wikipedia_link = wikipedia_link

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

    @property
    def region(self) -> str:
        """Return the ISO region (state or province) code.

        Returns:
            Region code such as `US-CA`, or `""` if none was supplied.
        """
        return self._region

    @property
    def continent(self) -> str:
        """Return the two-letter continent code.

        Returns:
            Continent code such as `NA`, or `""` if none was supplied.
        """
        return self._continent

    @property
    def elevation_ft(self) -> Optional[float]:
        """Return the airport's elevation in feet.

        Returns:
            Elevation in feet, or `None` when unknown. Distinct from `0.0`,
            which means sea level.
        """
        return self._elevation_ft

    @property
    def type(self) -> str:
        """Return the OurAirports size classification.

        Returns:
            One of `large_airport`, `medium_airport`, `small_airport`,
            `heliport` or `seaplane_base`, or `""` if none was supplied.
        """
        return self._type

    @property
    def icao_code(self) -> str:
        """Return the 4-letter ICAO code.

        Returns:
            ICAO code, or `""` if none was supplied.
        """
        return self._icao_code

    @property
    def has_scheduled_service(self) -> bool:
        """Return whether scheduled commercial flights serve this airport.

        Returns:
            `True` if the airport has scheduled service.
        """
        return self._has_scheduled_service

    @property
    def is_international(self) -> bool:
        """Return whether the airport is listed as international.

        The source is Wikipedia's list of international airports by country,
        which is editorially maintained rather than authoritative -- absence
        is not proof that an airport has no international service. Every other
        field on this class comes from OurAirports.

        Returns:
            `True` if the airport appears on that list.
        """
        return self._is_international

    @property
    def wikipedia_link(self) -> str:
        """Return the URL of the airport's Wikipedia article.

        Returns:
            Article URL, or `""` if none was supplied.
        """
        return self._wikipedia_link

    def __repr__(self) -> str:
        """Return a debugging representation with code, city, and coordinates.

        Returns:
            String of the form `Airport('XXX', city=..., lat=..., lon=...)`.
        """
        return (
            f"Airport({self._iata_code!r}, city={self._city!r}, "
            f"lat={self.latitude}, lon={self.longitude})"
        )
