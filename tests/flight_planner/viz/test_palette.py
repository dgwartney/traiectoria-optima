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
