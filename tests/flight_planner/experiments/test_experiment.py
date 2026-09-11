import json

import pytest

from flight_planner.experiments import Experiment


def write_experiment(directory, snapshot="../../snapshots/2026-09-11-abc123", **keys):
    """Write an experiment.toml by hand, pinning the on-disk contract."""
    directory.mkdir(parents=True, exist_ok=True)
    lines = [f'snapshot = "{snapshot}"']
    for key, value in keys.items():
        lines.append(f"{key} = {json.dumps(value)}")
    (directory / "experiment.toml").write_text("\n".join(lines) + "\n")
    return directory


@pytest.fixture
def bench(tmp_path, make_snapshot):
    """A snapshot and an experiment pointing at it, in sibling directories."""
    make_snapshot(tmp_path / "snapshots" / "2026-09-11-abc123")
    directory = write_experiment(
        tmp_path / "experiments" / "sfo-bos",
        description="Shortest path from SFO to BOS",
        notebooks=["explore.ipynb"],
    )
    return directory


class TestOpening:
    def test_reads_the_declared_fields(self, bench):
        experiment = Experiment.open(bench)

        assert experiment.slug == "sfo-bos"
        assert experiment.description == "Shortest path from SFO to BOS"
        assert experiment.notebooks == ("explore.ipynb",)

    def test_slug_defaults_to_the_directory_name(self, bench):
        assert Experiment.open(bench).slug == "sfo-bos"

    def test_explicit_slug_wins(self, tmp_path, make_snapshot):
        make_snapshot(tmp_path / "snapshots" / "2026-09-11-abc123")
        directory = write_experiment(tmp_path / "experiments" / "dir-name", slug="chosen")

        assert Experiment.open(directory).slug == "chosen"

    def test_notebook_paths_resolve_against_the_experiment(self, bench):
        assert Experiment.open(bench).notebook_paths == (bench / "explore.ipynb",)

    def test_parameters_are_optional(self, bench):
        assert Experiment.open(bench).parameters == {}

    def test_parameters_are_read_when_present(self, tmp_path, make_snapshot):
        make_snapshot(tmp_path / "snapshots" / "2026-09-11-abc123")
        directory = tmp_path / "experiments" / "parameterized"
        write_experiment(directory)
        path = directory / "experiment.toml"
        path.write_text(path.read_text() + '\n[parameters]\norigin = "SFO"\n')

        assert Experiment.open(directory).parameters == {"origin": "SFO"}

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Experiment.open(tmp_path / "nope")

    def test_missing_toml_raises_naming_the_file(self, tmp_path):
        directory = tmp_path / "bare"
        directory.mkdir()

        with pytest.raises(FileNotFoundError, match="experiment.toml"):
            Experiment.open(directory)

    def test_malformed_toml_raises_naming_the_file(self, tmp_path):
        directory = tmp_path / "broken"
        directory.mkdir()
        (directory / "experiment.toml").write_text("snapshot = [unclosed")

        with pytest.raises(ValueError, match="experiment.toml"):
            Experiment.open(directory)

    def test_toml_without_a_snapshot_raises(self, tmp_path):
        directory = tmp_path / "unpinned"
        directory.mkdir()
        (directory / "experiment.toml").write_text('description = "no data"\n')

        with pytest.raises(ValueError, match="snapshot"):
            Experiment.open(directory)


class TestResolvingTheSnapshot:
    def test_relative_path_resolves_against_the_toml(self, bench):
        experiment = Experiment.open(bench)

        assert experiment.snapshot.snapshot_id == "2026-09-11-abc123"

    def test_resolution_does_not_depend_on_the_working_directory(
        self, bench, tmp_path, monkeypatch
    ):
        # The package must never assume it is run from a repository root --
        # this is the `parents[3]` bug, guarded.
        elsewhere = tmp_path / "somewhere-else"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        assert Experiment.open(bench).snapshot.snapshot_id == "2026-09-11-abc123"

    def test_relative_path_is_reported_verbatim(self, bench):
        assert Experiment.open(bench).snapshot_reference == (
            "../../snapshots/2026-09-11-abc123"
        )

    def test_absolute_path_is_honoured(self, tmp_path, make_snapshot):
        snapshot = make_snapshot(tmp_path / "elsewhere" / "2026-09-11-abc123")
        directory = write_experiment(tmp_path / "experiments" / "absolute", snapshot=str(snapshot))

        assert Experiment.open(directory).snapshot.snapshot_id == "2026-09-11-abc123"

    def test_missing_snapshot_names_the_experiment_and_the_path(self, tmp_path):
        directory = write_experiment(tmp_path / "experiments" / "dangling")

        with pytest.raises(FileNotFoundError) as error:
            Experiment.open(directory).snapshot
        message = str(error.value)
        assert "dangling" in message
        assert "2026-09-11-abc123" in message

    def test_snapshot_is_opened_once(self, bench):
        experiment = Experiment.open(bench)

        assert experiment.snapshot is experiment.snapshot

    def test_opening_does_not_touch_the_snapshot(self, tmp_path):
        # Verification hashes every file, so it waits until the data is asked
        # for -- an experiment with a missing snapshot still parses.
        directory = write_experiment(tmp_path / "experiments" / "lazy")

        assert Experiment.open(directory).slug == "lazy"


class TestRecording:
    def test_writes_results_json(self, bench):
        experiment = Experiment.open(bench)

        path = experiment.record({"shortest_km": 4341.0, "legs": 1})

        assert path == bench / "results.json"
        assert json.loads(path.read_text())["results"] == {
            "shortest_km": 4341.0,
            "legs": 1,
        }

    def test_records_which_data_produced_them(self, bench):
        Experiment.open(bench).record({"shortest_km": 4341.0})

        recorded = json.loads((bench / "results.json").read_text())
        assert recorded["snapshot"]["id"] == "2026-09-11-abc123"
        assert recorded["snapshot"]["criteria"] == {"airline": "UA"}
        assert recorded["snapshot"]["source_commit"] == "abc123"
        assert recorded["experiment"] == "sfo-bos"
        assert recorded["recorded"]

    def test_records_the_parameters(self, tmp_path, make_snapshot):
        make_snapshot(tmp_path / "snapshots" / "2026-09-11-abc123")
        directory = write_experiment(tmp_path / "experiments" / "parameterized")
        path = directory / "experiment.toml"
        path.write_text(path.read_text() + '\n[parameters]\norigin = "SFO"\n')

        Experiment.open(directory).record({"legs": 1})

        recorded = json.loads((directory / "results.json").read_text())
        assert recorded["parameters"] == {"origin": "SFO"}

    def test_records_the_narrowing_chain(self, bench):
        experiment = Experiment.open(bench)
        catalog = experiment.snapshot.catalog().airline("UA")

        experiment.record({"legs": 1}, catalog=catalog)

        recorded = json.loads((bench / "results.json").read_text())
        assert [step["operation"] for step in recorded["catalog"]["chain"]] == ["airline"]
        assert recorded["catalog"]["routes"] == [1, 1]

    def test_omits_the_chain_when_no_catalog_is_given(self, bench):
        Experiment.open(bench).record({"legs": 1})

        assert "catalog" not in json.loads((bench / "results.json").read_text())

    def test_recording_verifies_the_snapshot(self, bench):
        from flight_planner.experiments import SnapshotIntegrityError

        routes = bench.parent.parent / "snapshots" / "2026-09-11-abc123" / "routes.csv"
        routes.write_text(routes.read_text().replace("4341.0", "9999.0"))

        with pytest.raises(SnapshotIntegrityError):
            Experiment.open(bench).record({"legs": 1})

    def test_rerecording_replaces_the_previous_run(self, bench):
        experiment = Experiment.open(bench)
        experiment.record({"legs": 1})
        experiment.record({"legs": 2})

        assert experiment.results()["results"] == {"legs": 2}

    def test_results_are_json_serializable_or_it_says_so(self, bench):
        with pytest.raises(TypeError):
            Experiment.open(bench).record({"planner": object()})


class TestReadingResults:
    def test_returns_none_before_any_run(self, bench):
        assert Experiment.open(bench).results() is None

    def test_reads_back_what_was_recorded(self, bench):
        experiment = Experiment.open(bench)
        experiment.record({"shortest_km": 4341.0})

        assert experiment.results()["results"]["shortest_km"] == 4341.0

    def test_results_path_is_exposed(self, bench):
        assert Experiment.open(bench).results_path == bench / "results.json"


class TestTheColabFlow:
    """The three lines an experiment notebook actually runs."""

    def test_open_load_record(self, bench, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        experiment = Experiment.open(bench)
        planner = experiment.snapshot.load_planner()
        distance, legs = planner.find_shortest_route("SFO", "BOS")
        path = experiment.record({"shortest_km": distance, "legs": len(legs)})

        assert json.loads(path.read_text())["results"] == {
            "shortest_km": 4341.0,
            "legs": 1,
        }
