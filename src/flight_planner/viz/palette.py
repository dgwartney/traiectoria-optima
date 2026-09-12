"""Colours for map layers, keyed by what a layer means."""

from __future__ import annotations

from typing import Dict

# Shared with experiments/search-cost/plots.py, which validated these slots
# for colour-vision deficiency against both surfaces: worst all-pairs CVD
# dE 9.4, normal-vision dE 20.9, contrast >= 3:1 on the dark surface. Slot 1
# blue, slot 2 orange, slot 3 aqua -- stepped per surface, not flipped.
SERIES_COLOURS: Dict[str, Dict[str, str]] = {
    "dark": {"BFS": "#3987e5", "Dijkstra": "#d95926", "A*": "#199e70"},
    "light": {"BFS": "#2a78d6", "Dijkstra": "#eb6834", "A*": "#1baf7a"},
}

# Identity must survive greyscale printing and colour-blind readers, so each
# series carries a shape as well as a hue.
SERIES_MARKERS: Dict[str, str] = {"BFS": "o", "Dijkstra": "s", "A*": "^"}

# Not series colours. The context network and the airport markers are scenery,
# not findings, and must not be drawn from a categorical slot -- doing so would
# make them compete with an algorithm for meaning.
SCENERY: Dict[str, Dict[str, str]] = {
    "dark": {"context": "#6b7480", "airports": "#9fb3c8"},
    "light": {"context": "#8899aa", "airports": "cadetblue"},
}


class Palette:
    """Colours for map layers, by what the layer means rather than its order.

    Series colours are shared with `experiments/search-cost/plots.py`, so a
    chart and a map on the same slide agree about which colour is Dijkstra.
    Assignment is by name and never cycled, so adding a fourth algorithm
    cannot repaint the three already on screen.

    Attributes:
        mode: Either `"dark"` (the reveal.js deck) or `"light"` (the PDF
            report and GitHub).
    """

    def __init__(self, mode: str = "light") -> None:
        """Create a palette for one surface.

        Args:
            mode: `"dark"` or `"light"`.

        Raises:
            ValueError: If `mode` is not a known surface. Refused rather than
                defaulted, matching what `plots.py` does.
        """
        if mode not in SERIES_COLOURS:
            raise ValueError(f"mode must be 'dark' or 'light', not {mode!r}")
        self.mode = mode

    def series(self, name: str) -> str:
        """Return the colour for an algorithm.

        Args:
            name: Algorithm label, e.g. `"Dijkstra"`. Case-sensitive, and the
                same strings the charts use.

        Returns:
            A hex colour string.

        Raises:
            KeyError: If the algorithm has no assigned colour. Guessing one is
                how two figures end up disagreeing.
        """
        try:
            return SERIES_COLOURS[self.mode][name]
        except KeyError:
            known = ", ".join(sorted(SERIES_COLOURS[self.mode]))
            raise KeyError(
                f"no colour assigned to {name!r}; known series are {known}. "
                "Add it to SERIES_COLOURS rather than passing a colour here, "
                "so every figure in the project agrees."
            ) from None

    def marker(self, name: str) -> str:
        """Return the matplotlib marker shape for an algorithm.

        Carried here so a map legend and a chart legend can agree, and so that
        identity is never colour alone.

        Args:
            name: Algorithm label.

        Returns:
            A matplotlib marker code.

        Raises:
            KeyError: If the algorithm has no assigned marker.
        """
        try:
            return SERIES_MARKERS[name]
        except KeyError:
            known = ", ".join(sorted(SERIES_MARKERS))
            raise KeyError(
                f"no marker assigned to {name!r}; known series are {known}"
            ) from None

    def context(self) -> str:
        """Return the recessive colour for the whole-network layer."""
        return SCENERY[self.mode]["context"]

    def airports(self) -> str:
        """Return the colour for airport markers."""
        return SCENERY[self.mode]["airports"]
