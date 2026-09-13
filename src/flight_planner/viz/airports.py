"""Airports as markers, with consistent popups."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence

from .layer import MapLayer
from .palette import Palette


class AirportLayer(MapLayer):
    """Airports as circle markers in one toggleable group.

    `CircleMarker` rather than `Marker`: a teardrop pin is unreadable at 3,387
    airports and considerably heavier in the saved HTML, while a 4-pixel circle
    still reads as a point at continental zoom.

    Attributes:
        name: Label for the layer control.
    """

    def __init__(
        self,
        airports: Iterable,
        palette: Optional[Palette] = None,
        *,
        name: str = "Airports",
        radius: float = 4,
    ) -> None:
        """Create an airport layer.

        Args:
            airports: `Airport` objects to draw. Consumed once, so a generator
                is materialised here rather than at build time.
            palette: Colours to draw with. Defaults to the light surface.
            name: Label for the layer control.
            radius: Marker radius in pixels.
        """
        self._airports = tuple(airports)
        self._palette = palette or Palette()
        self._name = name
        self._radius = radius
        self._drawn: List[List[float]] = []

    def name(self) -> str:
        """Return the label shown in the layer control."""
        return self._name

    def drawn_points(self) -> Sequence[Sequence[float]]:
        """Return the `[lat, lon]` of every airport drawn."""
        return self._drawn

    def build(self, folium: Any) -> Any:
        """Build a feature group of one circle marker per airport.

        Args:
            folium: The folium module.

        Returns:
            A `folium.FeatureGroup`.
        """
        group = folium.FeatureGroup(name=self.name(), show=self.show())
        colour = self._palette.airports()
        self._drawn = []

        for airport in self._airports:
            position = [airport.latitude, airport.longitude]
            self._drawn.append(position)
            folium.CircleMarker(
                location=position,
                radius=self._radius,
                color=colour,
                fill=True,
                fill_opacity=0.9,
                tooltip=self._tooltip(airport),
                popup=folium.Popup(self._popup(airport), max_width=250),
            ).add_to(group)

        return group

    @staticmethod
    def _tooltip(airport) -> str:
        """Return the hover label: code and name, which is what identifies it."""
        return f"{airport.iata_code} - {airport.name}".rstrip(" -")

    @staticmethod
    def _popup(airport) -> str:
        """Return the click label.

        Capped at 250px by the caller because long airport names otherwise
        stretch the popup off the edge of the map.
        """
        where = ", ".join(part for part in (airport.city, airport.country) if part)
        return f"<b>{airport.iata_code}</b><br>{where}" if where else (
            f"<b>{airport.iata_code}</b>"
        )
