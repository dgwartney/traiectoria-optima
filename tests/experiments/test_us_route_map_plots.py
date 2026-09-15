"""The us-route-map experiment's map builder and its colour measurement.

`plots.py` lives beside its notebook rather than in `flight_planner`, because
the wheel depends on `pandas` alone and folium is a `notebooks`-group
dependency. That keeps it out of the package's own test tree, so it is covered
here with the other committed-experiment artifacts, following
`test_search_cost_plots.py`.

The colour measurement gets more attention than the rest of the module, and
deliberately: it is the evidence behind a design decision -- four hues and
three dash classes rather than six and two -- and a measurement nobody checks
is an assertion with extra steps. The dichromat simulation is therefore tested
against properties that must hold for *any* correct implementation, not
against numbers this implementation happens to produce.

What is not tested is what the maps look like. That is a human step, the same
position `test_search_cost_plots.py` takes.
"""

import importlib.util

import pytest

folium = pytest.importorskip("folium")

from flight_planner.experiments import Experiment  # noqa: E402
from flight_planner.viz import NetworkLayer  # noqa: E402

SLUG = "us-route-map"


@pytest.fixture(scope="module")
def plots(repo_root):
    """Import the experiment's `plots.py` by path.

    `experiments/us-route-map/` is a data directory, not a package -- and its
    name is not a legal identifier -- so it cannot be imported by name.

    Args:
        repo_root: The repository root.

    Returns:
        The imported `plots` module.
    """
    path = repo_root / "experiments" / SLUG / "plots.py"
    spec = importlib.util.spec_from_file_location("us_route_map_plots", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def experiment(repo_root):
    return Experiment.open(repo_root / "experiments" / SLUG)


@pytest.fixture(scope="module")
def catalog(experiment):
    return experiment.catalog()


@pytest.fixture(scope="module")
def carriers(experiment):
    return experiment.parameters["carriers"]


class TestTheFacetedMap:
    def test_it_builds_one_layer_per_carrier_plus_the_extras(
        self, plots, catalog, carriers
    ):
        route_map = plots.faceted_map(
            catalog, carriers, other_label="All other carriers"
        )

        # Twelve carriers, the airport markers, and the bucket.
        assert len(route_map.layers) == len(carriers) + 2

    def test_every_carrier_layer_starts_switched_on(
        self, plots, catalog, carriers
    ):
        route_map = plots.faceted_map(catalog, carriers)
        carrier_layers = [
            layer
            for layer in route_map.layers
            if isinstance(layer, NetworkLayer)
        ]

        assert carrier_layers
        assert all(layer.show() for layer in carrier_layers)

    def test_the_airport_layer_starts_switched_off(
        self, plots, catalog, carriers
    ):
        # 473 markers bury the arcs they sit on, and the arcs are the finding.
        route_map = plots.faceted_map(catalog, carriers)

        assert route_map.layers[0].show() is False

    def test_the_bucket_starts_switched_off(self, plots, catalog, carriers):
        route_map = plots.faceted_map(
            catalog, carriers, other_label="All other carriers"
        )

        assert route_map.layers[-1].show() is False

    def test_carriers_are_drawn_largest_first(self, plots, catalog, carriers):
        # Leaflet paints in insertion order, so the smallest carrier has to go
        # last or it is buried. Southwest's 570 arcs were invisible under
        # American's 718 until this was ordered rather than left to dict order.
        route_map = plots.faceted_map(catalog, carriers)
        counts = [
            len(layer.distinct_pairs())
            for layer in route_map.layers
            if isinstance(layer, NetworkLayer)
        ]

        assert counts == sorted(counts, reverse=True)

    def test_only_draws_just_the_named_carriers(self, plots, catalog, carriers):
        route_map = plots.faceted_map(
            catalog, carriers, only=["AS", "HA"], airports=False
        )

        assert len(route_map.layers) == 2

    def test_only_suppresses_the_bucket(self, plots, catalog, carriers):
        # A two-carrier still is about those two carriers; a grey layer of
        # everything else would be answering a different question.
        route_map = plots.faceted_map(
            catalog,
            carriers,
            only=["B6"],
            other_label="All other carriers",
            airports=False,
        )

        assert len(route_map.layers) == 1

    def test_the_layer_labels_carry_the_route_counts(
        self, plots, catalog, carriers
    ):
        # The layer control is this map's only legend, so the label states the
        # finding rather than naming a colour.
        route_map = plots.faceted_map(catalog, carriers, only=["HA"],
                                      airports=False)

        assert route_map.layers[0].name() == "Hawaiian (HA) - 25 routes"

    def test_defunct_carriers_are_marked(self, plots, catalog, carriers):
        route_map = plots.faceted_map(
            catalog, carriers, only=["US"], defunct=["US"], airports=False
        )

        assert "[defunct]" in route_map.layers[0].name()

    def test_lower_48_drops_the_offshore_arcs(self, plots, catalog, carriers):
        whole = plots.faceted_map(catalog, carriers, only=["AS"],
                                  airports=False)
        continental = plots.faceted_map(
            catalog, carriers, only=["AS"], lower_48=True, airports=False
        )

        assert len(continental.layers[0].distinct_pairs()) < len(
            whole.layers[0].distinct_pairs()
        )

    def test_lower_48_reframes_the_map(self, plots, catalog, carriers):
        # No bounds override anywhere: `RouteMap` frames itself on what was
        # drawn, so dropping the offshore arcs is the whole mechanism.
        continental = plots.faceted_map(
            catalog, carriers, lower_48=True, airports=False
        )
        continental.finish()
        (_south, west), (_north, _east) = continental.bounds()

        assert west > -130, "the Aleutians are still in frame"


class TestThePartition:
    def test_the_bucket_holds_only_pairs_no_named_carrier_serves(
        self, plots, catalog, carriers
    ):
        covered = set()
        for code in carriers:
            covered |= plots.carrier_pairs(catalog, code)

        for route in plots.uncovered_routes(catalog, carriers):
            assert plots.pair_key(route) not in covered

    def test_the_bucket_holds_one_route_per_pair(
        self, plots, catalog, carriers
    ):
        others = plots.uncovered_routes(catalog, carriers)
        keys = [plots.pair_key(route) for route in others]

        assert len(keys) == len(set(keys))

    def test_together_they_cover_the_whole_network(
        self, plots, catalog, carriers
    ):
        covered = set()
        for code in carriers:
            covered |= plots.carrier_pairs(catalog, code)
        bucket = {
            plots.pair_key(route)
            for route in plots.uncovered_routes(catalog, carriers)
        }
        network = {plots.pair_key(route) for route in catalog.routes}

        assert covered | bucket == network
        assert not covered & bucket


class TestTheDichromatSimulation:
    """Properties any correct implementation must have, not this one's numbers.

    The measurement earned its keep by refuting the palette's first design, so
    it has to be trustworthy enough to have done that.
    """

    def test_grey_is_unchanged_by_every_deficiency(self, plots):
        # Dichromacy loses a colour axis, so a colour with no chroma to lose
        # must come through untouched. A simulation that moves grey is wrong.
        for deficiency in ("protanopia", "deuteranopia", "tritanopia"):
            simulated = plots.simulate("#808080", deficiency)
            original = plots._hex_to_linear("#808080")

            for channel, expected in zip(simulated, original):
                assert channel == pytest.approx(expected, abs=0.02)

    def test_red_and_green_converge_under_deuteranopia(self, plots):
        # The defining property of red-green colour blindness. If this does
        # not hold, the simulation is not simulating anything.
        def delta(first, second, view):
            return plots._delta_e(
                plots._to_lab(view(first)), plots._to_lab(view(second))
            )

        normal = delta("#d55e00", "#009e73", plots._hex_to_linear)
        impaired = delta(
            "#d55e00",
            "#009e73",
            lambda colour: plots.simulate(colour, "deuteranopia"),
        )

        assert impaired < normal

    def test_a_colour_is_no_different_from_itself(self, plots):
        assert plots._delta_e(
            plots._to_lab(plots._hex_to_linear("#0072b2")),
            plots._to_lab(plots._hex_to_linear("#0072b2")),
        ) == pytest.approx(0.0)

    def test_black_and_white_are_maximally_apart_in_lightness(self, plots):
        black = plots._to_lab(plots._hex_to_linear("#000000"))
        white = plots._to_lab(plots._hex_to_linear("#ffffff"))

        assert black[0] == pytest.approx(0.0, abs=0.5)
        assert white[0] == pytest.approx(100.0, abs=0.5)

    def test_an_unknown_deficiency_is_refused(self, plots):
        with pytest.raises(KeyError):
            plots.simulate("#0072b2", "tetrachromacy")

    def test_a_named_css_colour_is_refused_rather_than_guessed(self, plots):
        # The scenery colour in the palette is the named `cadetblue`, and it
        # is not part of any measured set. Silently skipping it would make a
        # floor look better than it is.
        with pytest.raises(ValueError):
            plots._hex_to_linear("cadetblue")


class TestThePaletteMeasurement:
    # Deliberately below the measured floors (19.6 light, 30.4 dark) so this
    # pins the guarantee rather than the exact numbers -- which would fail on
    # any harmless re-tuning.
    FLOOR = 19.0

    def test_every_same_stroke_pair_clears_the_floor(self, plots):
        for mode in ("light", "dark"):
            measured = plots.palette_contrast(mode)["worst_same_stroke"]

            for view, entry in measured.items():
                assert entry["delta_e"] >= self.FLOOR, (mode, view, entry)

    def test_it_measures_normal_vision_and_three_deficiencies(self, plots):
        measured = plots.palette_contrast()["worst_same_stroke"]

        assert set(measured) == {
            "normal",
            "protanopia",
            "deuteranopia",
            "tritanopia",
        }

    def test_it_groups_the_carriers_by_stroke(self, plots):
        # Carriers sharing a hue are told apart by stroke, so the pairs worth
        # measuring are the same-stroke ones. Three classes of four.
        strokes = plots.palette_contrast()["strokes"]

        assert sorted(strokes) == ["1,5", "6,4", "solid"]
        assert all(len(members) == 4 for members in strokes.values())

    def test_it_reports_which_pair_was_worst(self, plots):
        # A floor with no attribution cannot be acted on when it drops.
        entry = plots.palette_contrast()["worst_same_stroke"]["tritanopia"]

        assert len(entry["pair"]) == 2

    def test_an_unknown_surface_is_refused(self, plots):
        with pytest.raises(KeyError):
            plots.palette_contrast("chartreuse")
