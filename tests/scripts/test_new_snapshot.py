import json

import new_snapshot
from flight_planner.experiments import Snapshot


def only_snapshot(root):
    """Return the single snapshot the script wrote."""
    directories = [path for path in root.iterdir() if path.is_dir()]
    assert len(directories) == 1
    return directories[0]


def manifest_of(root):
    return json.loads((only_snapshot(root) / "manifest.json").read_text())


class TestFreezingEverything:
    def test_writes_the_whole_dataset(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args)

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert len(planner.vertices) == 4
        assert len(planner.edges) == 5

    def test_records_no_criteria(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args)

        manifest = manifest_of(tmp_path / "snapshots")
        assert manifest["criteria"] == {}
        assert "narrowing" not in manifest

    def test_names_the_script_that_wrote_it(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args)

        assert manifest_of(tmp_path / "snapshots")["generator"] == (
            "scripts/new_snapshot.py"
        )

    def test_rows_are_carried_across_verbatim(self, snapshot_args, tmp_path, processed):
        # No re-formatted floats: the snapshot's bytes are the processed
        # file's bytes for the rows that survived.
        new_snapshot.main(snapshot_args)

        frozen = only_snapshot(tmp_path / "snapshots") / "routes.csv"
        assert frozen.read_bytes() == (processed / "routes.csv").read_bytes()

    def test_the_snapshot_verifies(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args)

        Snapshot.open(only_snapshot(tmp_path / "snapshots"))  # raises if not

    def test_identical_data_lands_on_the_same_id(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args)
        first = only_snapshot(tmp_path / "snapshots").name

        new_snapshot.main(snapshot_args)

        assert only_snapshot(tmp_path / "snapshots").name == first


class TestNarrowing:
    def test_airline_narrows_the_routes(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--airline", "AA"])

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert len(planner.edges) == 1
        assert len(planner.vertices) == 2

    def test_closed_narrowing_drops_the_odd_endpoint(self, snapshot_args, tmp_path):
        # PWM is a medium airport, so BOS -> PWM goes when large is required.
        new_snapshot.main(snapshot_args + ["--airport-type", "large"])

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert planner.find_airport("PWM") is None
        assert len(planner.edges) == 4

    def test_criteria_record_the_normalized_value(self, snapshot_args, tmp_path):
        # "large" and "large_airport" are the same slice and must not produce
        # two different-looking manifests.
        new_snapshot.main(snapshot_args + ["--airport-type", "large"])

        assert manifest_of(tmp_path / "snapshots")["criteria"] == {
            "airport_type": "large_airport"
        }

    def test_the_two_spellings_agree(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--airport-type", "large"])
        short = only_snapshot(tmp_path / "snapshots").name

        new_snapshot.main(snapshot_args + ["--airport-type", "large_airport"])

        assert only_snapshot(tmp_path / "snapshots").name == short

    def test_records_the_chain_step_by_step(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--airline", "UA", "--airport-type", "large"])

        chain = manifest_of(tmp_path / "snapshots")["narrowing"]
        assert [step["operation"] for step in chain] == ["airline", "airport_type"]
        assert chain[0]["routes"] == [5, 4]
        assert chain[1]["routes"] == [4, 3]

    def test_several_values_are_recorded_as_a_list(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--country", "US", "CA"])

        assert manifest_of(tmp_path / "snapshots")["criteria"]["country"] == ["US", "CA"]

    def test_country_narrows_to_domestic(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--country", "US"])

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert planner.find_airport("YVR") is None

    def test_international_flag(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--international"])

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert planner.find_airport("PWM") is None

    def test_endpoints_mode_is_recorded_when_it_is_not_the_default(
        self, snapshot_args, tmp_path
    ):
        new_snapshot.main(
            snapshot_args + ["--airport-type", "large", "--endpoints", "either"]
        )

        assert manifest_of(tmp_path / "snapshots")["criteria"]["endpoints"] == "either"

    def test_either_keeps_the_regional_leg(self, snapshot_args, tmp_path):
        new_snapshot.main(
            snapshot_args + ["--airport-type", "large", "--endpoints", "either"]
        )

        planner = Snapshot.open(only_snapshot(tmp_path / "snapshots")).load_planner()
        assert planner.find_airport("PWM") is not None

    def test_ordering_of_narrowings_does_not_matter(self, snapshot_args, tmp_path):
        new_snapshot.main(snapshot_args + ["--airline", "UA", "--country", "US"])
        forward = (only_snapshot(tmp_path / "snapshots") / "routes.csv").read_bytes()

        new_snapshot.main(snapshot_args + ["--country", "US", "--airline", "UA"])

        frozen = (only_snapshot(tmp_path / "snapshots") / "routes.csv").read_bytes()
        assert frozen == forward


class TestReporting:
    def test_prints_what_each_step_cost(self, snapshot_args, capsys):
        new_snapshot.main(snapshot_args + ["--airline", "UA"])

        assert "airline(UA) -> 4 routes / 4 airports" in capsys.readouterr().out

    def test_warns_about_dangling_routes(self, snapshot_args, capsys):
        new_snapshot.main(
            snapshot_args + ["--airport-type", "large", "--endpoints", "airports"]
        )

        assert "reach airports outside the slice" in capsys.readouterr().out
