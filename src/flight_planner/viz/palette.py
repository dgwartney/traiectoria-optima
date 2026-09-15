"""Colours for map layers, keyed by what a layer means."""

from __future__ import annotations

from typing import Dict, Optional

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

# Carrier colours are a separate family from series colours, not an extension
# of them. A figure shows algorithms or it shows airlines; none shows both, so
# the two tables cannot disagree with each other and the hues are free to
# repeat across families.
#
# Twelve simultaneously distinguishable hues do not exist under the
# colour-blind constraint SERIES_MARKERS exists to satisfy, so identity here is
# hue *and* stroke: four hues x three dash patterns. That is the same trick as
# a chart series carrying both a colour and a marker.
#
# WHY FOUR HUES AND NOT SIX. The first attempt used six Okabe-Ito hues with two
# dash patterns, and measuring it refuted it: under tritanopia the three warm
# hues collapse together -- vermillion against reddish purple came out at CIE76
# dE 0.9, orange against reddish purple 13.9, orange against vermillion 14.9.
# Six hues over two dash classes puts every hue in every class, so those three
# warm hues always land in the same class as one another and no dash can
# separate them. Dropping to four hues that survive all three dichromacies, and
# spending a third dash pattern instead, makes every same-stroke pair separable
# by construction.
#
# The four are Okabe-Ito's blue, sky blue, bluish green and vermillion -- only
# one warm hue, so no dash class ever holds two. Measured worst case among the
# four hues is dE 19.6 (sky blue against bluish green, under tritanopia), and
# since each dash class holds each hue exactly once, no same-stroke pair falls
# below that. Yellow (#F0E442) and black (#000000) were dropped from the set
# first: both are unreadable as a 1px line over OpenStreetMap's light tiles.
# The dark column is each hue stepped lighter for a dark surface, the way
# SERIES_COLOURS is stepped rather than flipped.
#
# `experiments/us-route-map/plots.py` carries the measurement as
# `palette_contrast()`, and the tests pin its floor -- so this claim is
# reproducible rather than asserted, which the series dE figures above are not,
# having come from an external checker with no script in the repository.
#
# Assignment is deliberate, not alphabetical:
#
#   - The four legacy majors (AA, DL, UA, US) take the four hues, all solid,
#     because they are what a reader compares first and solid is the clearest
#     stroke.
#   - Every comparison `experiments/us-route-map/experiment.toml` names under
#     `[parameters.focus]` differs in hue, not merely in dash: WN against AA is
#     bluish green against blue, AS against HA is sky blue against vermillion.
#   - Four hues cannot cover twelve carriers without repeats, so each hue names
#     a family of three distinguished by stroke, and the layer control names
#     every member in full. Hue is the family; stroke is the member.
CARRIER_COLOURS: Dict[str, Dict[str, str]] = {
    "light": {
        # solid -- the legacy majors
        "AA": "#0072b2",  # blue
        "DL": "#d55e00",  # vermillion
        "UA": "#009e73",  # bluish green
        "US": "#56b4e9",  # sky blue
        # dashed
        "WN": "#009e73",  # bluish green
        "AS": "#56b4e9",  # sky blue
        "B6": "#0072b2",  # blue
        "FL": "#d55e00",  # vermillion
        # dotted
        "G4": "#56b4e9",  # sky blue
        "NK": "#009e73",  # bluish green
        "F9": "#0072b2",  # blue
        "HA": "#d55e00",  # vermillion
    },
    # Stepped for a dark surface, and stepped by measurement rather than by
    # eye: lightening all four uniformly pulled blue and bluish green to dE
    # 12.6 under tritanopia, below the light surface's floor. These four were
    # chosen by searching the lightening steps for the best worst-case, which
    # lands at dE 30.4 -- blue is left unlightened because lifting it is what
    # collapsed it into green. All four clear the 3:1 contrast against black
    # that the series colours are held to: 4.05, 7.30, 7.42 and 11.77 to 1.
    #
    # No figure in this repository uses it yet. Every map here is light,
    # because OpenStreetMap is the only basemap available without an API key
    # and it is light -- but `Palette(mode="dark")` is a supported surface, so
    # shipping an unmeasured table for it would be shipping a trap.
    "dark": {
        # solid
        "AA": "#0072b2",  # blue
        "DL": "#de8138",  # vermillion
        "UA": "#26ad88",  # bluish green
        "US": "#89caf0",  # sky blue
        # dashed
        "WN": "#26ad88",
        "AS": "#89caf0",
        "B6": "#0072b2",
        "FL": "#de8138",
        # dotted
        "G4": "#89caf0",
        "NK": "#26ad88",
        "F9": "#0072b2",
        "HA": "#de8138",
    },
}

# Leaflet `dashArray` per carrier. Absent means solid, which is why the
# accessor returns `None` rather than a "solid" sentinel -- a solid layer's
# style dict should not carry the key at all.
#
# Three classes, and they have to stay distinct at the 1.6px weight the carrier
# layers are drawn with: solid, a long dash, and a dot. Anything finer than
# "1,5" stops reading as a line at continental zoom.
CARRIER_DASHES: Dict[str, str] = {
    "WN": "6,4",
    "AS": "6,4",
    "B6": "6,4",
    "FL": "6,4",
    "G4": "1,5",
    "NK": "1,5",
    "F9": "1,5",
    "HA": "1,5",
}

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

    def carrier(self, code: str) -> str:
        """Return the colour for an airline.

        A separate family from `series`: carrier layers and algorithm layers
        never appear on the same figure, so the two tables are independent and
        a hue may belong to an airline here and an algorithm there.

        Args:
            code: IATA airline code, e.g. `"AA"`. Case-sensitive, matching
                `Route.airline` as the data carries it.

        Returns:
            A hex colour string.

        Raises:
            KeyError: If the airline has no assigned colour. Refused rather
                than cycled, for the same reason `series` refuses: a cycled
                colour silently repaints every other layer when a thirteenth
                carrier is added.
        """
        try:
            return CARRIER_COLOURS[self.mode][code]
        except KeyError:
            known = ", ".join(sorted(CARRIER_COLOURS[self.mode]))
            raise KeyError(
                f"no colour assigned to airline {code!r}; known carriers are "
                f"{known}. Add it to CARRIER_COLOURS rather than passing a "
                "colour here, so every figure in the project agrees."
            ) from None

    def carrier_dash(self, code: str) -> Optional[str]:
        """Return the Leaflet `dashArray` for an airline, or `None` if solid.

        Six hues cover twelve carriers, so the dash is half of a carrier's
        identity rather than decoration -- see `CARRIER_COLOURS`.

        Args:
            code: IATA airline code.

        Returns:
            A `dashArray` string such as `"6,4"`, or `None` for a solid line.

        Raises:
            KeyError: If the airline is not in `CARRIER_COLOURS`. Checked
                against the colour table, not the dash table, because a solid
                carrier is legitimately absent from the dash table and an
                unknown one must not be reported as solid.
        """
        if code not in CARRIER_COLOURS[self.mode]:
            known = ", ".join(sorted(CARRIER_COLOURS[self.mode]))
            raise KeyError(
                f"no colour assigned to airline {code!r}; known carriers are "
                f"{known}. Add it to CARRIER_COLOURS rather than passing a "
                "colour here, so every figure in the project agrees."
            )
        return CARRIER_DASHES.get(code)

    def context(self) -> str:
        """Return the recessive colour for the whole-network layer."""
        return SCENERY[self.mode]["context"]

    def airports(self) -> str:
        """Return the colour for airport markers."""
        return SCENERY[self.mode]["airports"]
