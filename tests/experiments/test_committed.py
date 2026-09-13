"""The snapshots and experiments in the repository must keep working.

Everything else in the suite tests the machinery against data it makes up.
This tests the actual committed artifacts: that the snapshots still verify,
and that the recorded results are still the results the data produces. If the
pipeline, the catalog or the loaders drift, this is what notices.
"""

import json

import pytest

from flight_planner import AStar, BFS, Dijkstra
from flight_planner.experiments import Experiment, Snapshot

FULL_SNAPSHOT_ID = "2026-09-11-bb90a8"
EXPERIMENT_SLUG = "sfo-bos-dijkstra"

# The experiment docs/tutorial.md walks the reader through building. Its
# snapshot is the US large-airport slice, narrowed at freeze time rather than
# in the notebook -- the opposite choice from sfo-bos-dijkstra above.
TUTORIAL_SNAPSHOT_ID = "2026-09-12-3e4f9d"
TUTORIAL_SLUG = "shortest-vs-fewest"

# The experiment that demonstrates flight_planner.viz. Unnarrowed world data,
# because one of its three pairs crosses the antimeridian and a US slice has
# no such route.
ROUTE_MAP_SLUG = "route-map"


def notebooks_only(experiment):
    """Return the experiment's `.ipynb` files.

    `notebooks` in `experiment.toml` is a list of filenames, not necessarily
    notebooks -- an experiment may be a plain script instead. Only real
    notebooks can carry stored output.

    Args:
        experiment: The experiment to inspect.

    Returns:
        Tuple of `Path` to the declared `.ipynb` files.
    """
    return tuple(
        path for path in experiment.notebook_paths if path.suffix == ".ipynb"
    )


@pytest.fixture(scope="module")
def full_snapshot(repo_root):
    return Snapshot.open(repo_root / "data" / "snapshots" / FULL_SNAPSHOT_ID)


@pytest.fixture(scope="module")
def experiment(repo_root):
    return Experiment.open(repo_root / "experiments" / EXPERIMENT_SLUG)


@pytest.fixture(scope="module")
def tutorial_experiment(repo_root):
    return Experiment.open(repo_root / "experiments" / TUTORIAL_SLUG)


@pytest.fixture(scope="module")
def route_map_experiment(repo_root):
    return Experiment.open(repo_root / "experiments" / ROUTE_MAP_SLUG)


class TestTheFullSnapshot:
    def test_it_verifies(self, full_snapshot):
        full_snapshot.verify()  # raises if any file has changed

    def test_it_is_the_whole_network(self, full_snapshot):
        catalog = full_snapshot.catalog()
        assert len(catalog.routes) == 66332
        assert len(catalog.airports) == 3387

    def test_it_records_no_criteria(self, full_snapshot):
        assert full_snapshot.criteria == {}


class TestTheLegacySnapshot:
    """Pinned before the pipeline went global, and deliberately not re-frozen."""

    def test_it_still_verifies(self, legacy_snapshot_dir):
        Snapshot.open(legacy_snapshot_dir).verify()

    def test_it_predates_is_international_and_still_loads(self, legacy_snapshot_dir):
        # The column was added after this snapshot was frozen. Absent columns
        # read as their default rather than raising, which is what lets an old
        # snapshot keep working.
        airports = Snapshot.open(legacy_snapshot_dir).catalog().airports
        assert len(airports) == 88
        assert all(airport.is_international is False for airport in airports)


class TestTheCommittedExperiment:
    def test_it_opens_and_pins_its_data(self, experiment):
        assert experiment.slug == EXPERIMENT_SLUG
        assert experiment.snapshot.snapshot_id == FULL_SNAPSHOT_ID

    def test_the_snapshot_path_is_relative(self, experiment):
        assert experiment.snapshot_reference.startswith("../../")

    def test_its_notebook_exists(self, experiment):
        assert experiment.notebooks
        assert all(path.is_file() for path in experiment.notebook_paths)

    def test_its_notebook_carries_no_stored_output(self, experiment):
        # Outputs are re-derivable and make diffs unreadable; results.json is
        # the recorded answer, not the rendered notebook. `notebooks` may also
        # name a plain script, which has no outputs to carry.
        for path in notebooks_only(experiment):
            for cell in json.loads(path.read_text())["cells"]:
                assert not cell.get("outputs")

    def test_it_has_been_run(self, experiment):
        recorded = experiment.results()
        assert recorded is not None
        assert recorded["snapshot"]["id"] == FULL_SNAPSHOT_ID

    def test_the_recorded_narrowing_still_narrows_the_same_way(self, experiment):
        recorded = experiment.results()
        parameters = experiment.parameters

        narrowed = (
            experiment.catalog()
            .airline(parameters["airline"])
            .airport_type(parameters["airport_type"])
            .country(parameters["country"])
        )

        assert narrowed.summary()["routes"] == recorded["catalog"]["routes"]
        assert narrowed.summary()["airports"] == recorded["catalog"]["airports"]

    def test_the_recorded_answer_is_still_the_answer(self, experiment):
        recorded = experiment.results()["results"]
        parameters = experiment.parameters

        narrowed = (
            experiment.catalog()
            .airline(parameters["airline"])
            .airport_type(parameters["airport_type"])
            .country(parameters["country"])
        )
        distance_km, legs = narrowed.planner().find_shortest_route(
            parameters["origin"], parameters["destination"]
        )

        assert distance_km == pytest.approx(recorded["narrowed_km"])
        assert [leg.flight_number for leg in legs] == recorded["narrowed_flights"]


class TestTheTutorialExperiment:
    """`docs/tutorial.md` builds this one, and quotes its numbers verbatim.

    The tutorial's lesson is that BFS returns *a* minimum-hop route rather than
    the shortest one among them, so these assertions cover the finding itself,
    not just that the files parse.
    """

    def test_it_opens_and_pins_its_data(self, tutorial_experiment):
        assert tutorial_experiment.slug == TUTORIAL_SLUG
        assert tutorial_experiment.snapshot.snapshot_id == TUTORIAL_SNAPSHOT_ID

    def test_the_snapshot_path_is_relative(self, tutorial_experiment):
        assert tutorial_experiment.snapshot_reference.startswith("../../")

    def test_its_snapshot_is_the_us_large_slice(self, tutorial_experiment):
        snapshot = tutorial_experiment.snapshot
        snapshot.verify()

        # Narrowed at freeze time, so the scope is stated in the manifest and
        # the notebook does not narrow anything.
        assert snapshot.criteria == {
            "airport_type": "large_airport",
            "country": "US",
        }

        catalog = tutorial_experiment.catalog()
        assert len(catalog.routes) == 7005
        assert len(catalog.airports) == 94

    def test_its_notebook_carries_no_stored_output(self, tutorial_experiment):
        for path in notebooks_only(tutorial_experiment):
            for cell in json.loads(path.read_text())["cells"]:
                assert not cell.get("outputs")

    def test_the_recorded_answers_are_still_the_answers(self, tutorial_experiment):
        planner = tutorial_experiment.catalog().planner()

        for row in tutorial_experiment.results()["results"]["pairs"]:
            origin, destination = row["pair"].split("-")

            by_km, km_legs = planner.find_shortest_route(
                origin, destination, Dijkstra()
            )
            hops, hop_legs = planner.find_shortest_route(
                origin, destination, BFS()
            )

            assert by_km == pytest.approx(row["dijkstra_km"])
            assert len(km_legs) == row["dijkstra_legs"]
            assert int(hops) == row["bfs_legs"]
            assert sum(leg.distance_km for leg in hop_legs) == pytest.approx(
                row["bfs_km"]
            )

    def test_bfs_still_overshoots_on_one_pair_and_not_the_other(
        self, tutorial_experiment
    ):
        # The tutorial turns on this contrast: BFS lands on the best two-leg
        # route for BOI-CHS and misses it by ~540 km for HNL-BDL. If a data
        # refresh ever erases that, the document is stale.
        overshoot = {
            row["pair"]: row["bfs_overshoot_km"]
            for row in tutorial_experiment.results()["results"]["pairs"]
            if "bfs_overshoot_km" in row
        }

        assert overshoot["BOI-CHS"] == 0.0
        assert overshoot["HNL-BDL"] > 500.0

    def test_the_overshoot_is_still_what_the_data_says(self, tutorial_experiment):
        catalog = tutorial_experiment.catalog()
        planner = catalog.planner()

        for row in tutorial_experiment.results()["results"]["pairs"]:
            if "best_at_bfs_legs_km" not in row:
                continue

            origin, destination = row["pair"].split("-")
            best_km = min(
                first.distance_km + second.distance_km
                for first in catalog.routes_from(origin)
                for second in catalog.routes_from(first.destination.iata_code)
                if second.destination.iata_code == destination
            )
            _, hop_legs = planner.find_shortest_route(origin, destination, BFS())

            assert best_km == pytest.approx(row["best_at_bfs_legs_km"])
            assert sum(
                leg.distance_km for leg in hop_legs
            ) - best_km == pytest.approx(row["bfs_overshoot_km"], abs=1e-3)


class TestTheRouteMapExperiment:
    """The experiment that demonstrates `flight_planner.viz`.

    Its recorded answers are checked the same way every other committed
    experiment's are -- by re-deriving them -- and its figures are checked for
    existing and being real PNGs. What the map *looks* like is not asserted;
    that is a human step, the same position `plots.py`'s tests take.
    """

    def test_it_opens_and_pins_the_world_snapshot(self, route_map_experiment):
        assert route_map_experiment.slug == ROUTE_MAP_SLUG
        assert route_map_experiment.snapshot.snapshot_id == FULL_SNAPSHOT_ID

    def test_the_snapshot_path_is_relative(self, route_map_experiment):
        assert route_map_experiment.snapshot_reference.startswith("../../")

    def test_its_notebook_exists(self, route_map_experiment):
        assert route_map_experiment.notebooks
        assert all(path.is_file() for path in route_map_experiment.notebook_paths)

    def test_its_notebook_carries_no_stored_output(self, route_map_experiment):
        # A rendered folium map is megabytes of inline HTML, so this matters
        # more here than anywhere else in the suite.
        for path in notebooks_only(route_map_experiment):
            for cell in json.loads(path.read_text())["cells"]:
                assert not cell.get("outputs")

    def test_it_has_been_run(self, route_map_experiment):
        recorded = route_map_experiment.results()
        assert recorded is not None
        assert recorded["snapshot"]["id"] == FULL_SNAPSHOT_ID

    def test_the_recorded_routes_are_still_the_routes(self, route_map_experiment):
        planner = route_map_experiment.catalog().planner()
        recorded = route_map_experiment.results()["results"]["comparison"]

        for pair, found in recorded.items():
            origin, destination = pair.split("-")
            for label, algorithm in (("Dijkstra", Dijkstra()), ("BFS", BFS())):
                _cost, legs = planner.find_shortest_route(
                    origin, destination, algorithm
                )
                codes = "-".join(
                    [legs[0].origin.iata_code]
                    + [leg.destination.iata_code for leg in legs]
                )

                assert codes == found[label]["route"]
                assert sum(
                    leg.distance_km for leg in legs
                ) == pytest.approx(found[label]["km"], abs=0.1)

    def test_the_recorded_deduplication_still_holds(self, route_map_experiment):
        # The 3.5-to-1 collapse from route rows to airport pairs is the whole
        # reason NetworkLayer batches the way it does.
        from flight_planner.viz import NetworkLayer

        catalog = route_map_experiment.catalog()
        recorded = route_map_experiment.results()["results"]["network"]

        assert len(catalog.routes) == recorded["route_rows"]
        assert len(NetworkLayer(catalog.routes).distinct_pairs()) == (
            recorded["distinct_pairs"]
        )

    def test_its_figures_are_committed_pngs(self, route_map_experiment, repo_root):
        # An inline map cannot be committed, so the figure file is the durable
        # artifact -- and the report and the deck both reference it.
        recorded = route_map_experiment.results()["results"]["figures"]
        assert recorded

        for filename in recorded:
            for directory in ("docs/images", "slides/images"):
                path = repo_root / directory / filename
                assert path.is_file(), f"{path} is missing"
                assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
# The benchmark behind the BFS/Dijkstra/A* comparison table and the
# runtime-vs-input-size plot. It runs on the full world network rather than a
# narrowing, because the catalogue asks the comparison to run on long-haul
# queries and those only exist if the graph has long hauls in it.
SEARCH_COST_SLUG = "search-cost"


@pytest.fixture(scope="module")
def search_cost(repo_root):
    return Experiment.open(repo_root / "experiments" / SEARCH_COST_SLUG)


class TestTheSearchCostExperiment:
    def test_it_opens_and_pins_its_data(self, search_cost):
        assert search_cost.slug == SEARCH_COST_SLUG
        assert search_cost.snapshot.snapshot_id == FULL_SNAPSHOT_ID

    def test_the_snapshot_path_is_relative(self, search_cost):
        assert search_cost.snapshot_reference.startswith("../../")

    def test_its_notebook_carries_no_stored_output(self, search_cost):
        for path in notebooks_only(search_cost):
            for cell in json.loads(path.read_text())["cells"]:
                assert not cell.get("outputs")

    def test_it_has_been_run(self, search_cost):
        recorded = search_cost.results()
        assert recorded is not None
        assert recorded["snapshot"]["id"] == FULL_SNAPSHOT_ID

    def test_every_query_pair_survives_every_narrowing(self, search_cost):
        # If a pair vanished partway down the size series, the runtime curve
        # would be comparing different questions at different sizes.
        parameters = search_cost.parameters
        base = search_cost.catalog()

        for spec in parameters["sizes"]:
            narrowed = base
            if "airline" in spec:
                narrowed = narrowed.airline(*spec["airline"])
            if "country" in spec:
                narrowed = narrowed.country(*spec["country"])
            if "airport_type" in spec:
                narrowed = narrowed.airport_type(*spec["airport_type"])

            codes = set(narrowed.iata_codes)
            for origin, destination in parameters["pairs"]:
                assert origin in codes, f"{origin} missing from {spec['label']}"
                assert destination in codes, f"{destination} missing from {spec['label']}"

    def test_the_recorded_expansion_counts_are_still_what_the_search_costs(
        self, search_cost
    ):
        recorded = search_cost.results()["results"]["comparison"]
        planner = search_cost.catalog().planner()
        heuristic = AStar(lambda origin, goal: origin.distance_to(goal))

        for row in recorded:
            origin, destination = row["pair"].split("-")
            for name, algorithm in (
                ("BFS", BFS()),
                ("Dijkstra", Dijkstra()),
                ("A*", heuristic),
            ):
                result = planner.search_route(origin, destination, algorithm)
                assert result.nodes_expanded == row["expanded"][name], (
                    f"{row['pair']} {name}"
                )

    def test_astar_still_matches_dijkstra_on_every_recorded_query(self, search_cost):
        # The project's central claim, re-checked against real data rather
        # than a hand-built test graph.
        for row in search_cost.results()["results"]["comparison"]:
            assert row["cost"]["Dijkstra"] == pytest.approx(row["cost"]["A*"])
            assert row["expanded"]["A*"] < row["expanded"]["Dijkstra"]

    def test_the_recorded_sizes_are_still_the_sizes(self, search_cost):
        recorded = {row["label"]: row for row in
                    search_cost.results()["results"]["runtime_series"]}
        base = search_cost.catalog()

        for spec in search_cost.parameters["sizes"]:
            narrowed = base
            if "airline" in spec:
                narrowed = narrowed.airline(*spec["airline"])
            if "country" in spec:
                narrowed = narrowed.country(*spec["country"])
            if "airport_type" in spec:
                narrowed = narrowed.airport_type(*spec["airport_type"])

            row = recorded[spec["label"]]
            assert len(narrowed.airports) == row["vertices"]
            assert len(narrowed.routes) == row["edges"]


class TestWhatTheSearchCostExperimentMeasuredAboutScaling:
    """The empirical side of the complexity write-up.

    These read the recorded file rather than re-timing anything, so they are
    assertions about what was published, not a benchmark that can flake on a
    loaded machine.
    """

    def test_every_size_reports_a_build_time(self, search_cost):
        for row in search_cost.results()["results"]["runtime_series"]:
            assert row["build_ms"] > 0, row["label"]

    def test_graph_construction_is_linear_in_the_graph_size(self, search_cost):
        # The one O(V + E) claim in this project that is directly testable:
        # building an adjacency list cannot stop early the way a search can.
        build = search_cost.results()["results"]["scaling"]["build"]
        assert 0.85 < build["exponent"] < 1.15, build
        assert build["r_squared"] > 0.99, build

    def test_every_search_is_sublinear_because_it_stops_at_the_goal(
        self, search_cost
    ):
        # A goal-directed search never does the work its worst-case bound
        # describes, so the measured exponents come in well under
        # construction's. If one ever matched it, the search would have stopped
        # being goal-directed.
        scaling = search_cost.results()["results"]["scaling"]
        for name in ("BFS", "Dijkstra", "A*"):
            assert scaling[name]["exponent"] < scaling["build"]["exponent"], name
            assert scaling[name]["exponent"] < 0.8, name

    def test_astar_is_the_least_sensitive_to_graph_size(self, search_cost):
        # A* expands a handful of nodes whether the graph has 2,000 edges or
        # 66,000, so its exponent is the closest to zero of the three.
        scaling = search_cost.results()["results"]["scaling"]
        assert scaling["A*"]["exponent"] < scaling["Dijkstra"]["exponent"]
        assert scaling["A*"]["exponent"] < scaling["BFS"]["exponent"]

    def test_it_records_the_machine_that_produced_the_timings(self, search_cost):
        # Absolute milliseconds are only interpretable if the run says what it
        # ran on -- and in Colab that becomes a configuration someone else can
        # select and reproduce.
        machine = search_cost.results()["results"]["environment"]
        assert machine["cpu"]
        assert machine["cores"] >= 1
        assert machine["platform"]
        assert machine["python"]
        assert isinstance(machine["colab"], bool)
