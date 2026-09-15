"""Re-derive what `manhattan-heuristic` found, and keep the finding true.

The experiment's claim is a trade: the taxicab heuristic expands about half the
vertices the admissible one does, and returns a suboptimal route on close to
three fifths of random queries. Both halves are load-bearing, and both are
properties of `AStar` and `Manhattan` together rather than of either alone --
so a change to the search, the formula, or the data pipeline could quietly
turn the recorded numbers into fiction.

What is re-derived versus asserted follows `test_heuristic_admissibility.py`:
the cheap full-edge comparison is recomputed from the snapshot, the 6.6 million
consistency checks are not, and the per-pair sweep is spot-checked on the one
pair the experiment named as its worst rather than re-run over all 300.
"""

import json

import pytest

from flight_planner import AStar, Dijkstra
from flight_planner.experiments import Experiment
from flight_planner.geo import Manhattan, haversine_heuristic, manhattan_heuristic

SLUG = "manhattan-heuristic"
SNAPSHOT_ID = "2026-09-11-bb90a8"
EPSILON_KM = 1e-9


@pytest.fixture(scope="module")
def experiment(repo_root):
    """Open the committed experiment, verifying its snapshot on the way."""
    return Experiment.open(repo_root / "experiments" / SLUG)


@pytest.fixture(scope="module")
def recorded(repo_root):
    """Return the committed `results.json` payload."""
    path = repo_root / "experiments" / SLUG / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))["results"]


@pytest.fixture(scope="module")
def catalog(experiment):
    """The whole world, unnarrowed, as the experiment uses it."""
    return experiment.snapshot.catalog()


def test_it_pins_the_world_snapshot(experiment, recorded):
    assert experiment.snapshot.snapshot_id == SNAPSHOT_ID
    assert recorded["graph"] == {"airports": 3387, "routes": 66332}


def test_its_notebook_carries_no_stored_output(experiment):
    """results.json is the recorded answer, not the rendered notebook."""
    for path in experiment.notebook_paths:
        for cell in json.loads(path.read_text(encoding="utf-8"))["cells"]:
            assert not cell.get("outputs")


class TestPerEdge:
    """Re-derived, because it is cheap and it is what the argument starts from."""

    def test_the_violation_count_is_still_every_edge_but_one(
        self, catalog, recorded
    ):
        formula = Manhattan()
        routes = catalog.routes

        violations = sum(
            1
            for route in routes
            if formula.calculate(route.origin, route.destination)
            > route.distance_km + EPSILON_KM
        )

        assert violations == recorded["per_edge"]["violations"]
        assert violations == len(routes) - 1

    def test_the_worst_edge_is_still_the_worst_edge(self, catalog, recorded):
        formula = Manhattan()
        worst = max(
            catalog.routes,
            key=lambda route: formula.calculate(route.origin, route.destination)
            - route.distance_km,
        )

        expected = recorded["per_edge"]["worst_edge"]
        assert worst.origin.iata_code == expected["origin"]
        assert worst.destination.iata_code == expected["destination"]
        assert formula.calculate(worst.origin, worst.destination) == pytest.approx(
            expected["estimate_km"]
        )

    def test_the_ratio_bounds_what_the_search_can_lose(self, recorded):
        """The two sections have to agree, or the bound argument is broken.

        A heuristic that never exceeds the truth by more than a factor of `r`
        cannot return a path costing more than `r x` optimal. If the measured
        cost excess ever exceeded the measured ratio, one of the two
        measurements would be wrong.
        """
        ratio = recorded["per_edge"]["ratio"]["max"]
        excess = recorded["sample"]["excess"]["max"]

        assert 1.0 < ratio < 2.0
        assert excess < ratio - 1.0

    def test_the_single_clean_edge_is_the_zero_length_self_loop(self, recorded):
        assert recorded["per_edge"]["zero_weight_edges"] == 1
        assert recorded["per_edge"]["largest_understatement_km"] == pytest.approx(0.0)


class TestConsistency:
    """Asserted rather than re-derived -- 6.6 million checks is the experiment's job."""

    def test_it_breaches_the_triangle_inequality(self, recorded):
        consistency = recorded["consistency"]

        assert consistency["checks"] == 6_633_200
        assert consistency["goals_sampled"] == 100
        assert consistency["violations"] > 0
        assert consistency["worst_violation_km"] > 1000.0


class TestTheTrade:
    """Both halves of the finding, each with a live check behind it."""

    def test_the_recorded_rate_is_a_majority_of_pairs(self, recorded):
        sample = recorded["sample"]

        assert sample["pairs_with_a_route"] + sample["pairs_unreachable"] == (
            sample["pairs_requested"]
        )
        assert sample["suboptimal"] == 172
        assert sample["suboptimal_rate"] > 0.5

    def test_it_expands_fewer_vertices_than_the_admissible_heuristic(self, recorded):
        expanded = recorded["sample"]["mean_expanded"]

        assert expanded["manhattan"] < expanded["haversine"] < expanded["dijkstra"]
        assert recorded["sample"]["mean_expansion_ratio"][
            "manhattan_over_haversine"
        ] < 1.0

    def test_the_worst_pair_is_still_worse_and_still_longer(self, catalog, recorded):
        """The one pair re-run live, because a rate is not a demonstration.

        Asserts the shape of the failure as well as its size: the optimal route
        is both cheaper and shorter in legs, which is what an overestimate
        pulling the search off the good path looks like.
        """
        worst = recorded["sample"]["worst_pair"]
        planner = catalog.planner()
        origin, destination = worst["origin"], worst["destination"]

        optimal = planner.search_route(origin, destination, algorithm=Dijkstra())
        admissible = planner.search_route(
            origin, destination, algorithm=AStar(haversine_heuristic())
        )
        taxicab = planner.search_route(
            origin, destination, algorithm=AStar(manhattan_heuristic())
        )

        # The control: an admissible, consistent heuristic returns Dijkstra's
        # answer. If this fails, the comparison is broken rather than the
        # finding being interesting.
        assert admissible.cost == pytest.approx(optimal.cost)

        assert taxicab.cost > optimal.cost
        assert taxicab.cost == pytest.approx(worst["manhattan_km"])
        assert optimal.cost == pytest.approx(worst["optimal_km"])
        assert len(taxicab.path) > len(optimal.path)

    def test_the_hand_picked_pairs_understate_it(self, recorded):
        """Why the headline number comes from a random sample.

        Three of the five long-haul pairs are a single direct flight, which no
        heuristic can get wrong. A list like that would report this heuristic
        as very nearly free and very nearly correct.
        """
        pairs = recorded["long_haul"]["pairs"]

        assert len(pairs) == 5
        clean = [pair for pair in pairs if pair["excess"] <= EPSILON_KM]
        assert len(clean) == 3
        assert all(pair["legs_optimal"] == 1 for pair in clean)
