"""Re-derive the cleaning figures §2.3 states, and the snapshot's provenance.

`experiments/data-cleaning` is the only experiment that checks the *pipeline*
rather than a property of its output, so this file checks two different kinds
of thing: that the recorded drop figures are internally coherent, and that the
committed snapshot really is what the current cleaning code produces.

The second is the one that matters. Every other experiment reads a snapshot
and trusts that it was built correctly; this is what makes that trust
checkable. Re-running the full build takes about two seconds, which is cheap
enough to do here rather than assert from the record.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from flight_planner.experiments import Experiment

SLUG = "data-cleaning"
SNAPSHOT_ID = "2026-09-11-bb90a8"


@pytest.fixture(scope="module")
def recorded(repo_root):
    """Return the committed `results.json` payload."""
    path = repo_root / "experiments" / SLUG / "results.json"
    return json.loads(path.read_text(encoding="utf-8"))["results"]


@pytest.fixture(scope="module")
def rebuilt(repo_root):
    """Re-run the cleaning over the committed raw sources.

    Returns:
        The `NetworkBuild` the current pipeline produces.
    """
    sys.path.insert(0, str(repo_root / "src" / "data"))
    from flight_network import FlightNetworkBuilder

    builder = FlightNetworkBuilder()
    return builder, builder.build(
        builder.read_airports(repo_root / "data" / "raw" / "our_airports" / "airports.csv"),
        builder.read_routes(repo_root / "data" / "raw" / "open_flights" / "routes.dat"),
        international=repo_root / "data" / "processed" / "international_airports.csv",
    )


class TestTheRecordIsCoherent:
    """Checks between recorded figures, which catch a measurement that is
    wrong in more than one place at once."""

    def test_the_drop_breakdown_sums_to_the_drop_count(self, recorded):
        routes = recorded["routes"]
        assert sum(routes["by_reason"].values()) == routes["dropped"] == 1331

    def test_kept_plus_dropped_is_every_raw_row(self, recorded):
        routes = recorded["routes"]
        assert routes["kept"] + routes["dropped"] == routes["raw_rows"] == 67663

    def test_every_dropped_row_is_listed_not_just_counted(self, recorded):
        """A count is a claim; the rows are evidence.

        The pipeline used to print `len(skipped)` and persist nothing, which
        is the gap this experiment exists to close.
        """
        assert len(recorded["dropped_rows"]) == recorded["routes"]["dropped"]

    def test_every_dropped_row_names_one_of_the_known_categories(self, repo_root, recorded):
        sys.path.insert(0, str(repo_root / "src" / "data"))
        from flight_network import DROP_CATEGORIES

        for entry in recorded["dropped_rows"]:
            category = entry["reason"].split(":", 1)[0]
            assert category in DROP_CATEGORIES, entry

    def test_the_near_symmetry_the_report_reads_as_a_signal(self, recorded):
        """663 against 660.

        §2.3 argues this is what you would expect if the cause is airports
        missing from OurAirports rather than a directional bug in endpoint
        resolution. A lopsided split would mean the opposite, so the
        symmetry is worth pinning rather than merely observing.
        """
        by_reason = recorded["routes"]["by_reason"]
        origin = by_reason["origin does not resolve"]
        destination = by_reason["destination does not resolve"]

        assert origin == 663
        assert destination == 660
        assert abs(origin - destination) / max(origin, destination) < 0.02

    def test_the_survival_rate_the_report_quotes(self, recorded):
        assert round(100 * recorded["routes"]["survival_rate"], 1) == 98.0

    def test_the_raw_inputs_are_digested(self, repo_root, recorded):
        """The raw files belong to no snapshot, so nothing else verifies them.

        Recording their checksums is what lets a drop count name the bytes it
        was measured over.
        """
        assert recorded["inputs"]
        for entry in recorded["inputs"]:
            path = repo_root / entry["path"]
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


class TestTheAirportFilterDoesWhatTheReportSays:
    """§2.3 was corrected by this experiment, so the correction gets a test."""

    def test_the_iata_test_removes_every_row_the_report_credits_it_with(self, rebuilt, recorded):
        _, build = rebuilt
        airports = recorded["airports"]

        assert airports["raw_rows"] == 85884
        assert airports["failed"]["iata_code_not_three_characters"] == 76831
        assert airports["raw_rows"] - airports["failed"][
            "iata_code_not_three_characters"
        ] == airports["usable_rows"] == 9053

    def test_the_coordinate_and_duplicate_guards_never_fire(self, recorded):
        """They are defensive, not load-bearing, and §2.3 now says so.

        Worth keeping and worth reporting honestly: a source that begins
        publishing a coordinate-less airport should lose that row rather than
        acquire a vertex at (0, 0). If this test ever fails, the claim in
        §2.3 needs rewriting -- which is the point of asserting a zero.
        """
        airports = recorded["airports"]

        assert airports["failed"]["missing_latitude"] == 0
        assert airports["failed"]["missing_longitude"] == 0
        assert airports["duplicate_iata_codes_collapsed"] == 0

    def test_only_airports_a_route_touches_are_written_out(self, rebuilt):
        """9,053 usable, 3,387 referenced. The second filter is the graph's."""
        _, build = rebuilt
        referenced = set(build.routes["source_airport_code"]) | set(
            build.routes["destination_airport_code"]
        )

        assert len(build.airports) == 3387
        assert set(build.airports["iata_code"]) == referenced


class TestTheSnapshotIsWhatThePipelineProduces:
    """The check that earns this experiment its snapshot pin.

    Every other experiment reads a snapshot and trusts it was built
    correctly. This is what makes that trust a measurement.
    """

    def test_the_rebuild_matches_the_frozen_row_counts(self, rebuilt, repo_root):
        _, build = rebuilt
        experiment = Experiment.open(repo_root / "experiments" / SLUG)
        catalog = experiment.snapshot.catalog()

        assert experiment.snapshot.snapshot_id == SNAPSHOT_ID
        assert len(build.airports) == len(catalog.airports)
        assert len(build.routes) == len(catalog.routes)

    def test_the_rebuild_matches_the_frozen_airports_code_for_code(self, rebuilt, repo_root):
        """Counts agreeing while contents differ would be the worse failure."""
        _, build = rebuilt
        experiment = Experiment.open(repo_root / "experiments" / SLUG)
        frozen = {airport.iata_code for airport in experiment.snapshot.catalog().airports}

        assert set(build.airports["iata_code"]) == frozen

    def test_the_recorded_agreement_says_so_too(self, recorded):
        agreement = recorded["snapshot_agreement"]

        assert agreement["airports_agree"]
        assert agreement["routes_agree"]
        assert agreement["only_in_rebuild"] == []
        assert agreement["only_in_snapshot"] == []


def test_the_na_trap_did_not_reopen(recorded):
    """`NA` read as null would blank a whole continent and a whole country.

    `CsvRecordLoader.TEXT_COLUMNS` exists because pandas reads the string
    `NA` as a missing value. Without it every North American airport loses
    its continent and every Namibian one its country. Coverage is how that
    would show up -- as a column quietly falling toward zero.
    """
    coverage = recorded["coverage"]["airports"]

    assert coverage["continent"] == 1.0
    assert coverage["iso_country"] == 1.0
    assert coverage["iata_code"] == 1.0
    assert coverage["latitude_deg"] == 1.0
    assert coverage["longitude_deg"] == 1.0
