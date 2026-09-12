"""The snapshots and experiments in the repository must keep working.

Everything else in the suite tests the machinery against data it makes up.
This tests the actual committed artifacts: that the snapshots still verify,
and that the recorded results are still the results the data produces. If the
pipeline, the catalog or the loaders drift, this is what notices.
"""

import json

import pytest

from flight_planner import BFS, Dijkstra
from flight_planner.experiments import Experiment, Snapshot

FULL_SNAPSHOT_ID = "2026-09-11-bb90a8"
EXPERIMENT_SLUG = "sfo-bos-dijkstra"

# The experiment docs/tutorial.md walks the reader through building. Its
# snapshot is the US large-airport slice, narrowed at freeze time rather than
# in the notebook -- the opposite choice from sfo-bos-dijkstra above.
TUTORIAL_SNAPSHOT_ID = "2026-09-12-3e4f9d"
TUTORIAL_SLUG = "shortest-vs-fewest"


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
