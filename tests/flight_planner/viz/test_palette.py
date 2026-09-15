"""Colours are shared with the committed charts, or the deck contradicts itself.

`experiments/search-cost/plots.py` already renders BFS, Dijkstra and A* in a
palette validated for colour-vision deficiency on both surfaces. A map drawn
in different colours beside those charts would swap two of its three series,
so `Palette` is the single source and these tests pin the contract it has to
keep.
"""

import pytest

from flight_planner.viz import Palette


class TestSeriesColours:
    def test_every_algorithm_has_a_colour_on_both_surfaces(self):
        for mode in ("dark", "light"):
            palette = Palette(mode)
            for name in ("BFS", "Dijkstra", "A*"):
                assert palette.series(name).startswith("#")

    def test_the_two_surfaces_differ(self):
        assert Palette("dark").series("BFS") != Palette("light").series("BFS")

    def test_an_unknown_series_is_refused_rather_than_guessed(self):
        # Guessing a colour is how two figures end up disagreeing, which is
        # the entire failure this class exists to prevent.
        with pytest.raises(KeyError):
            Palette().series("Bellman-Ford")

    def test_an_unknown_surface_is_refused_rather_than_guessed(self):
        with pytest.raises(ValueError):
            Palette("chartreuse")

    def test_it_matches_the_committed_chart_colours(self):
        # Pinned to plots.py. If that file's palette moves, this fails and the
        # two have to be reconciled deliberately.
        assert Palette("dark").series("Dijkstra") == "#d95926"
        assert Palette("light").series("Dijkstra") == "#eb6834"
        assert Palette("dark").series("BFS") == "#3987e5"
        assert Palette("light").series("A*") == "#1baf7a"


class TestMarkers:
    def test_every_algorithm_has_a_marker_shape(self):
        # Identity must survive greyscale printing and colour-blind readers,
        # so colour is never the only channel.
        palette = Palette()

        assert {palette.marker(name) for name in ("BFS", "Dijkstra", "A*")} == {
            "o",
            "s",
            "^",
        }


class TestLayerColours:
    def test_the_context_colour_is_not_one_of_the_series_slots(self):
        # The network layer is not a series; drawing it from a categorical
        # slot would make it compete with an algorithm for meaning.
        palette = Palette()
        series = {palette.series(n) for n in ("BFS", "Dijkstra", "A*")}

        assert palette.context() not in series

    def test_it_offers_an_airport_colour(self):
        assert Palette().airports()

    def test_assignment_is_by_name_not_by_order(self):
        # Adding a fourth algorithm must not repaint the three already drawn.
        first = Palette().series("Dijkstra")
        Palette().series("BFS")

        assert Palette().series("Dijkstra") == first


class TestCarrierColours:
    """The faceted map in `experiments/us-route-map` draws twelve carriers.

    Four hues over three dash classes, so a carrier's identity is hue *and*
    stroke. The property that matters is about same-stroke pairs: two carriers
    a reader has to separate by colour alone are two carriers drawn with the
    same dash. `experiments/us-route-map/plots.py` measures the separation;
    these tests pin the structure that makes the measurement meaningful.
    """

    CARRIERS = (
        "AA",
        "US",
        "DL",
        "UA",
        "WN",
        "FL",
        "AS",
        "G4",
        "B6",
        "NK",
        "F9",
        "HA",
    )

    def test_every_carrier_has_a_colour_on_both_surfaces(self):
        for mode in ("dark", "light"):
            palette = Palette(mode)
            for code in self.CARRIERS:
                assert palette.carrier(code).startswith("#")

    def test_an_unknown_carrier_is_refused_rather_than_cycled(self):
        # Cycling a colour would silently repaint every other layer when a
        # thirteenth carrier arrives, which is the same failure the series
        # table refuses.
        with pytest.raises(KeyError):
            Palette().carrier("ZZ")

    def test_an_unknown_carrier_is_refused_by_the_dash_accessor_too(self):
        # A solid carrier is legitimately absent from the dash table, so the
        # accessor must check the colour table or it would report an unknown
        # airline as solid.
        with pytest.raises(KeyError):
            Palette().carrier_dash("ZZ")

    def test_solid_carriers_report_no_dash(self):
        assert Palette().carrier_dash("AA") is None

    def test_dashed_carriers_report_a_dash_array(self):
        assert Palette().carrier_dash("AS") == "6,4"
        assert Palette().carrier_dash("HA") == "1,5"

    def test_there_are_three_dash_classes(self):
        strokes = {
            Palette().carrier_dash(code) for code in self.CARRIERS
        }

        assert strokes == {None, "6,4", "1,5"}

    def test_no_two_carriers_share_both_hue_and_stroke(self):
        # Hue is the family, stroke is the member. If a pair collided on both
        # they would be indistinguishable on the map and in the legend only.
        for mode in ("dark", "light"):
            palette = Palette(mode)
            identities = [
                (palette.carrier(code), palette.carrier_dash(code))
                for code in self.CARRIERS
            ]

            assert len(set(identities)) == len(self.CARRIERS)

    def test_each_dash_class_uses_each_hue_at_most_once(self):
        # This is what makes the palette's guarantee structural rather than
        # lucky: the measured floor is the worst pair among four distinct
        # hues, and it only holds if no class repeats a hue.
        for mode in ("dark", "light"):
            palette = Palette(mode)
            by_stroke = {}
            for code in self.CARRIERS:
                stroke = palette.carrier_dash(code)
                by_stroke.setdefault(stroke, []).append(palette.carrier(code))

            for stroke, hues in by_stroke.items():
                assert len(set(hues)) == len(hues), stroke

    def test_the_four_legacy_majors_are_solid_and_differently_coloured(self):
        # They are what a reader compares first, so they get the clearest
        # stroke and four distinct hues rather than one hue dashed four ways.
        palette = Palette()
        majors = ("AA", "DL", "UA", "US")

        assert all(palette.carrier_dash(code) is None for code in majors)
        assert len({palette.carrier(code) for code in majors}) == 4

    def test_the_focus_comparisons_differ_in_hue_not_only_in_stroke(self):
        # experiment.toml names these pairs as the ones worth a still image,
        # so they must be separable by colour and not rely on the dash.
        palette = Palette()
        for first, second in (("WN", "AA"), ("AS", "HA")):
            assert palette.carrier(first) != palette.carrier(second)

    def test_carrier_colours_are_a_separate_family_from_series_colours(self):
        # A figure shows algorithms or airlines, never both, so the tables are
        # independent -- but they must not be the *same* table, or adding a
        # carrier could repaint Dijkstra.
        palette = Palette()

        with pytest.raises(KeyError):
            palette.series("AA")
        with pytest.raises(KeyError):
            palette.carrier("Dijkstra")
