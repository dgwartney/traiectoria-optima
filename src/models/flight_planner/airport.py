"""Airport graph vertex."""

from __future__ import annotations

from vertex import Vertex


class Airport(Vertex):
    """Airport vertex identified by its 3-letter IATA code."""

    def __init__(
        self,
        iata_code: str,
        name: str = "",
        city: str = "",
        country: str = "",
    ) -> None:
        normalized_iata = iata_code.strip().upper()
        super().__init__(key=normalized_iata)
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
        return f"Airport({self._iata_code!r}, city={self._city!r})"
