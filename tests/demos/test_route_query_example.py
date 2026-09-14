"""The demo module `notebooks/demo.ipynb` is built on.

Of the fourteen modules in `src/demos/`, this is the one that matters most
(#87): the committed demo notebook imports `open_catalog`, `compare_modes`
and `format_result` from it rather than reimplementing them, so a regression
here breaks the graded notebook rather than a console script nobody runs.

These run against the real pinned snapshot, which is the point -- the demo's
claim is about the delivered network, not a fixture. `open_catalog` is
module-scoped because opening a snapshot re-hashes every file.
"""

import pytest

from flight_planner import COST_HOPS, COST_WEIGHT
from flight_planner.errors import AirportNotFoundError
from route_query_example import (
    SNAPSHOT_ID,
    compare_modes,
    format_result,
    open_catalog,
)

#: The pair the notebook opens with. `HNL -> BDL` is the clearest case of the
#: three modes disagreeing: BFS saves a leg and spends 544.7 km for it.
ORIGIN, DESTINATION = "HNL", "BDL"

#: What the three modes return on it, from the committed world snapshot.
FEWEST_STOPS_HOPS = 2.0
SHORTEST_KM = 8071.513690777907

MODES = ("fewest stops", "shortest distance", "shortest distance (A*)")


@pytest.fixture(scope="module")
def catalog():
    return open_catalog()


@pytest.fixture(scope="module")
def planner(catalog):
    return catalog.planner()


@pytest.fixture(scope="module")
def results(planner):
    return compare_modes(planner, ORIGIN, DESTINATION)


class TestOpenCatalog:
    def test_it_opens_the_pinned_world_snapshot(self, catalog):
        assert len(catalog.airports) == 3387
        assert len(catalog.routes) == 66332

    def test_it_names_the_snapshot_the_report_cites(self):
        assert SNAPSHOT_ID == "2026-09-11-bb90a8"

    def test_an_unknown_snapshot_raises_rather_than_returning_empty(self):
        with pytest.raises((FileNotFoundError, NotADirectoryError, ValueError)):
            open_catalog("9999-99-99-nosuch")


class TestCompareModes:
    def test_it_runs_all_three_modes(self, results):
        assert tuple(results) == MODES

    def test_bfs_reports_hops_and_the_others_report_weight(self, results):
        assert results["fewest stops"].unit == COST_HOPS
        assert results["shortest distance"].unit == COST_WEIGHT
        assert results["shortest distance (A*)"].unit == COST_WEIGHT

    def test_bfs_finds_the_fewest_stops(self, results):
        assert results["fewest stops"].cost == FEWEST_STOPS_HOPS

    def test_astar_returns_exactly_dijkstras_answer(self, results):
        """The project's central claim, as an assertion on raw floats."""
        dijkstra = results["shortest distance"]
        astar = results["shortest distance (A*)"]
        assert astar.cost == dijkstra.cost == SHORTEST_KM
        assert [leg.flight_number for leg in astar.path] == [
            leg.flight_number for leg in dijkstra.path
        ]

    def test_astar_expands_far_fewer_airports_than_dijkstra(self, results):
        dijkstra = results["shortest distance"]
        astar = results["shortest distance (A*)"]
        assert astar.nodes_expanded < dijkstra.nodes_expanded / 50

    def test_bfs_pays_distance_for_the_stop_it_saves(self, results):
        """The trade the notebook's first finding is about."""
        bfs = results["fewest stops"]
        dijkstra = results["shortest distance"]
        assert len(bfs.path) < len(dijkstra.path)
        assert sum(leg.distance_km for leg in bfs.path) > dijkstra.cost

    def test_an_unknown_airport_raises(self, planner):
        with pytest.raises(AirportNotFoundError):
            compare_modes(planner, "ZZZ", DESTINATION)


class TestFormatResult:
    def test_it_labels_hops_and_kilometres_differently(self, results):
        assert " hops " in format_result(ORIGIN, results["fewest stops"])
        assert " km " in format_result(ORIGIN, results["shortest distance"])

    def test_it_renders_the_itinerary_from_the_origin(self, results):
        line = format_result(ORIGIN, results["shortest distance"])
        assert line.endswith("HNL -> SLC -> DTW -> BDL")

    def test_an_unreachable_pair_says_so_rather_than_printing_inf(self, planner):
        unreachable = compare_modes(planner, "SPI", "JFK")["shortest distance"]
        line = format_result("SPI", unreachable)
        assert "no route" in line
        assert "inf" not in line
