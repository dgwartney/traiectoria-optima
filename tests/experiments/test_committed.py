"""The snapshots and experiments in the repository must keep working.

Everything else in the suite tests the machinery against data it makes up.
This tests the actual committed artifacts: that the snapshots still verify,
and that the recorded results are still the results the data produces. If the
pipeline, the catalog or the loaders drift, this is what notices.
"""

import json

import pytest

from flight_planner.experiments import Experiment, Snapshot

FULL_SNAPSHOT_ID = "2026-09-11-bb90a8"
EXPERIMENT_SLUG = "sfo-bos-dijkstra"


@pytest.fixture(scope="module")
def full_snapshot(repo_root):
    return Snapshot.open(repo_root / "data" / "snapshots" / FULL_SNAPSHOT_ID)


@pytest.fixture(scope="module")
def experiment(repo_root):
    return Experiment.open(repo_root / "experiments" / EXPERIMENT_SLUG)


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
        # the recorded answer, not the rendered notebook.
        for path in experiment.notebook_paths:
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
