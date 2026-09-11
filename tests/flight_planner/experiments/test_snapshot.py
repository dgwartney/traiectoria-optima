import json

import pytest

from flight_planner.experiments import Snapshot, SnapshotIntegrityError


class TestOpening:
    def test_reads_the_manifest(self, snapshot_dir):
        snapshot = Snapshot.open(snapshot_dir)

        assert snapshot.snapshot_id == "2026-09-11-abc123"
        assert snapshot.criteria == {"airline": "UA"}
        assert snapshot.source_commit == "abc123"

    def test_path_resolves_a_file_in_the_snapshot(self, snapshot_dir):
        assert Snapshot.open(snapshot_dir).path("routes.csv") == snapshot_dir / "routes.csv"

    def test_unknown_file_is_rejected(self, snapshot_dir):
        # Only what the manifest vouches for can be reached.
        with pytest.raises(KeyError):
            Snapshot.open(snapshot_dir).path("secrets.csv")

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Snapshot.open(tmp_path / "nope")

    def test_missing_manifest_raises(self, tmp_path, sample_csv):
        directory = tmp_path / "bare"
        directory.mkdir()
        (directory / "airports.csv").write_text(sample_csv["airports.csv"])

        with pytest.raises(FileNotFoundError):
            Snapshot.open(directory)

    def test_malformed_manifest_raises(self, tmp_path, make_snapshot):
        directory = make_snapshot(tmp_path / "broken")
        (directory / "manifest.json").write_text("{not json")

        with pytest.raises(SnapshotIntegrityError):
            Snapshot.open(directory)

    def test_manifest_without_files_section_raises(self, tmp_path, make_snapshot):
        directory = make_snapshot(tmp_path / "nofiles")
        payload = json.loads((directory / "manifest.json").read_text())
        del payload["files"]
        (directory / "manifest.json").write_text(json.dumps(payload))

        with pytest.raises(SnapshotIntegrityError):
            Snapshot.open(directory)


class TestIntegrity:
    """The point of the manifest: data cannot change without being noticed."""

    def test_tampered_file_is_detected(self, snapshot_dir):
        path = snapshot_dir / "routes.csv"
        path.write_text(path.read_text().replace("4341.0", "9999.0"))

        with pytest.raises(SnapshotIntegrityError) as error:
            Snapshot.open(snapshot_dir)
        assert "routes.csv" in str(error.value)

    def test_a_single_byte_is_enough(self, snapshot_dir):
        path = snapshot_dir / "airports.csv"
        path.write_bytes(path.read_bytes() + b" ")

        with pytest.raises(SnapshotIntegrityError):
            Snapshot.open(snapshot_dir)

    def test_file_listed_but_absent_is_detected(self, snapshot_dir):
        (snapshot_dir / "routes.csv").unlink()

        with pytest.raises(SnapshotIntegrityError) as error:
            Snapshot.open(snapshot_dir)
        assert "routes.csv" in str(error.value)

    def test_verification_can_be_skipped_explicitly(self, snapshot_dir):
        # Large snapshots make hashing every file on open expensive; opting
        # out has to be a deliberate, visible act.
        path = snapshot_dir / "routes.csv"
        path.write_text(path.read_text().replace("4341.0", "9999.0"))

        snapshot = Snapshot.open(snapshot_dir, verify=False)

        assert snapshot.snapshot_id == "2026-09-11-abc123"


class TestLoading:
    def test_load_planner_builds_the_network(self, snapshot_dir):
        planner = Snapshot.open(snapshot_dir).load_planner()

        assert len(planner.vertices) == 2
        assert len(planner.edges) == 1

    def test_loaded_airports_carry_the_enriched_fields(self, snapshot_dir):
        planner = Snapshot.open(snapshot_dir).load_planner()

        sfo = planner.find_airport("SFO")
        assert sfo.city == "San Francisco"
        assert sfo.icao_code == "KSFO"
        assert sfo.type == "large_airport"

    def test_loaded_routes_carry_their_flight_number(self, snapshot_dir):
        planner = Snapshot.open(snapshot_dir).load_planner()

        assert planner.edges[0].flight_number == "UA1876"


class TestAgainstTheCommittedSnapshot:
    """The real snapshot in the repository must verify and load."""

    def test_legacy_snapshot_verifies_and_loads(self, legacy_snapshot_dir):
        planner = Snapshot.open(legacy_snapshot_dir).load_planner()

        assert len(planner.vertices) == 88
        assert len(planner.edges) == 861
